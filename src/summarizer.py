#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
會議摘要生成器
使用 LLM 將逐字稿轉換為結構化會議記錄

設計原則：
1. 智能分段處理長文本
2. 可自訂提示詞模板
3. 支援多種輸出格式
4. 品質驗證機制
"""
import logging
import re
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime

from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """摘要結果"""
    summary: str
    transcript_length: int
    summary_length: int
    processing_time: float
    model: str
    chunks_processed: int = 1
    
    @property
    def compression_ratio(self) -> float:
        """壓縮比（原文/摘要）"""
        if self.summary_length > 0:
            return self.transcript_length / self.summary_length
        return 0


# 預設系統提示詞 (COSTAR-X 框架)
# 融合 COSTAR-A 與 Phil Schmid 的 Gemini 提示實踐指南
# 優化目標：本地 Gemma 3 12B/27B 模型
DEFAULT_SYSTEM_PROMPT = """<system_instruction>
<role>
你是一位專業的政府機關資深承辦人員與專案經理。你擅長從雜亂的會議逐字稿中提取關鍵資訊，並轉化為結構清晰、符合台灣政府機關公文風格的繁體中文會議記錄。你的風格是客觀、精準且簡練。
</role>

<instructions>
請依照以下步驟處理會議逐字稿：

1. **Analyze (分析)**：閱讀全文，識別會議的「主要議題」、「關鍵決策」與「待辦事項」。
2. **Filter (過濾)**：忽略寒暄、冗言贅字或無關的閒聊。
3. **Structure (結構化)**：將資訊填入指定的輸出格式中。
4. **Refine (修飾)**：確保所有內容皆為流暢的繁體中文 (Traditional Chinese)，並檢查是否有遺漏的人名或期限。
</instructions>

<constraints>
- **Language**：輸出必須是 100% 繁體中文（台灣用語）。
- **Tone**：台灣政府機關公文書寫風格，正式、客觀、不帶情緒色彩。
- **Accuracy**：若逐字稿中有模糊不清的數據，請標註「(待確認)」，不可瞎編。
- **Formatting**：嚴格遵守指定格式，不要輸出多餘的引導語或解釋。
- **Completeness**：每個區塊都必須填寫，若該區塊無相關內容則標註「無」。
</constraints>

<output_format>
請依序輸出以下區塊（使用 Markdown）：

# 會議記錄摘要

## 1. 會議概況
- **日期**：[YYYY/MM/DD]（如有提及）
- **參與者**：[列出人名]（如有提及）
- **會議主題**：[根據內容推斷]

## 2. 執行摘要 (Executive Summary)
[用 100 字以內總結會議核心結論]

## 3. 詳細議題與決議 (Discussion & Decisions)
- **議題 1**：[標題]
  - *討論重點*：...
  - *最終決議*：...
- **議題 2**：...
（依此類推）

## 4. 待辦事項 (Action Items) - 必填
| 待辦事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| [具體事項] | [人名] | [時間] |

## 5. 其他備註
- 其他重要但不屬於上述分類的內容
- 特殊情況說明
</output_format>
</system_instruction>

<final_instruction>
請深呼吸，一步步執行上述分析步驟，確保沒有遺漏任何輸出格式中的欄位。現在開始：
</final_instruction>"""


# 簡潔版系統提示詞 (COSTAR-X 簡化版)
CONCISE_SYSTEM_PROMPT = """<system_instruction>
<role>
你是專業的會議記錄整理專家，擅長快速提取會議重點並產出精簡的繁體中文摘要。
</role>

<instructions>
1. 分析逐字稿，提取核心資訊
2. 過濾非必要內容
3. 依格式輸出結構化摘要
</instructions>

<constraints>
- 輸出必須使用繁體中文（台灣用語）
- 精簡扼要，不要冗言贅字
- 不可添加原文沒有的資訊
</constraints>

<output_format>
## 會議重點
（3-5 個要點，條列式）

## 決議事項
（列出所有已決定的事項）

## 待辦追蹤
| 事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
</output_format>
</system_instruction>

<final_instruction>
請按照上述格式，精簡輸出會議摘要。
</final_instruction>"""


# 通用摘要提示詞
GENERAL_SUMMARY_PROMPT = """請將以下內容整理成簡潔的摘要。

要求：
1. 保留關鍵資訊
2. 使用清晰的段落結構
3. 長度約為原文的 1/5 至 1/3"""


class MeetingSummarizer:
    """
    會議摘要生成器
    
    功能：
    - 智能處理長文本（自動分段）
    - 可自訂提示詞
    - 支援串流輸出
    - 輸出品質驗證
    """
    
    # 估算每個 token 約對應的中文字數
    CHARS_PER_TOKEN = 1.5
    
    # 預設最大輸入長度（留空間給輸出）
    DEFAULT_MAX_INPUT_TOKENS = 24000
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
        temperature: float = 0.7
    ):
        """
        初始化摘要生成器
        
        Args:
            ollama_client: Ollama 客戶端
            system_prompt: 系統提示詞
            max_input_tokens: 最大輸入 token 數
            temperature: 生成溫度
        """
        self.client = ollama_client
        self.system_prompt = system_prompt
        self.max_input_tokens = max_input_tokens
        self.temperature = temperature
        
        logger.info("[摘要] 初始化完成")
        logger.info("[摘要] 最大輸入: ~%d 字元", self._tokens_to_chars(max_input_tokens))
    
    def _estimate_tokens(self, text: str) -> int:
        """估算 token 數量"""
        return self.client.estimate_tokens(text)
    
    def _tokens_to_chars(self, tokens: int) -> int:
        """token 轉換為字元數"""
        return int(tokens * self.CHARS_PER_TOKEN)
    
    def _split_text(self, text: str, max_chars: int) -> List[str]:
        """
        智能分割文本
        
        優先在自然斷點（句號、換行）處分割
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            end_pos = min(current_pos + max_chars, len(text))
            
            if end_pos < len(text):
                # 尋找最近的自然斷點
                best_break = end_pos
                
                # 優先尋找換行
                newline_pos = text.rfind('\n', current_pos, end_pos)
                if newline_pos > current_pos + max_chars // 2:
                    best_break = newline_pos + 1
                else:
                    # 尋找句號
                    for punct in ['。', '！', '？', '.', '!', '?']:
                        punct_pos = text.rfind(punct, current_pos, end_pos)
                        if punct_pos > current_pos + max_chars // 2:
                            best_break = punct_pos + 1
                            break
                
                end_pos = best_break
            
            chunk = text[current_pos:end_pos].strip()
            if chunk:
                chunks.append(chunk)
            
            current_pos = end_pos
        
        return chunks
    
    def summarize(
        self,
        transcript: str,
        stream: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
        custom_prompt: Optional[str] = None
    ) -> SummaryResult:
        """
        生成會議摘要
        
        Args:
            transcript: 逐字稿文字
            stream: 是否串流輸出
            on_token: 串流時的回調函數
            custom_prompt: 自訂提示詞（覆蓋系統提示詞）
        
        Returns:
            摘要結果
        """
        import time
        start_time = time.time()
        
        transcript = transcript.strip()
        if not transcript:
            raise ValueError("逐字稿為空")
        
        logger.info("[摘要] 輸入長度: %d 字元", len(transcript))
        
        # 檢查是否需要分段處理
        estimated_tokens = self._estimate_tokens(transcript)
        system_prompt = custom_prompt or self.system_prompt
        
        if estimated_tokens <= self.max_input_tokens:
            # 單次處理
            summary = self._generate_summary(
                transcript, 
                system_prompt,
                stream, 
                on_token
            )
            chunks_processed = 1
        else:
            # 分段處理
            logger.info("[摘要] 文本過長，啟用分段處理")
            summary = self._summarize_long_text(
                transcript,
                system_prompt,
                stream,
                on_token
            )
            chunks_processed = self._count_chunks(transcript)
        
        elapsed = time.time() - start_time
        
        # 驗證輸出
        if not self._validate_summary(summary):
            logger.warning("[摘要] 輸出品質警告：摘要可能不完整")
        
        result = SummaryResult(
            summary=summary,
            transcript_length=len(transcript),
            summary_length=len(summary),
            processing_time=elapsed,
            model=self.client.model,
            chunks_processed=chunks_processed
        )
        
        logger.info("[摘要] 完成！耗時: %.1f 秒", elapsed)
        logger.info("[摘要] 輸出長度: %d 字元", len(summary))
        logger.info("[摘要] 壓縮比: %.1fx", result.compression_ratio)
        
        return result
    
    def _generate_summary(
        self,
        transcript: str,
        system_prompt: str,
        stream: bool,
        on_token: Optional[Callable[[str], None]]
    ) -> str:
        """生成單段摘要"""
        prompt = f"""請整理以下會議逐字稿：

=== 逐字稿開始 ===
{transcript}
=== 逐字稿結束 ===

請按照指定格式輸出結構化的會議摘要。"""
        
        return self.client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=self.temperature,
            stream=stream,
            on_token=on_token
        )
    
    def _summarize_long_text(
        self,
        transcript: str,
        system_prompt: str,
        stream: bool,
        on_token: Optional[Callable[[str], None]]
    ) -> str:
        """處理長文本（分段摘要後合併）"""
        # 計算每段最大字元數
        max_chars = self._tokens_to_chars(self.max_input_tokens - 2000)  # 預留空間
        chunks = self._split_text(transcript, max_chars)
        
        logger.info("[摘要] 分為 %d 段處理", len(chunks))
        
        # 第一階段：各段摘要
        chunk_summaries = []
        for i, chunk in enumerate(chunks, 1):
            logger.info("[摘要] 處理第 %d/%d 段", i, len(chunks))
            
            chunk_prompt = f"""這是會議逐字稿的第 {i}/{len(chunks)} 部分。
請提取這部分的重點：

{chunk}

請以條列式整理重點，包含：
1. 主要討論內容
2. 提到的決議或結論
3. 待辦事項（如有）"""
            
            summary = self.client.generate(
                prompt=chunk_prompt,
                temperature=self.temperature,
                stream=False
            )
            chunk_summaries.append(summary)
        
        # 第二階段：合併摘要
        logger.info("[摘要] 合併各段摘要")
        
        combined = "\n\n---\n\n".join([
            f"【第 {i+1} 段重點】\n{s}" 
            for i, s in enumerate(chunk_summaries)
        ])
        
        merge_prompt = f"""以下是會議各段的重點摘要，請整合成一份完整的會議記錄：

{combined}

請依照標準格式輸出完整的會議摘要。"""
        
        return self.client.generate(
            prompt=merge_prompt,
            system_prompt=system_prompt,
            temperature=self.temperature,
            stream=stream,
            on_token=on_token
        )
    
    def _count_chunks(self, transcript: str) -> int:
        """計算需要的分段數"""
        max_chars = self._tokens_to_chars(self.max_input_tokens - 2000)
        return (len(transcript) + max_chars - 1) // max_chars
    
    def _validate_summary(self, summary: str) -> bool:
        """驗證摘要品質"""
        if not summary:
            return False
        
        # 去除空白後檢查長度
        summary_stripped = summary.strip()
        if len(summary_stripped) < 100:
            return False
        
        # 檢查是否有結構
        has_structure = any(marker in summary for marker in ['###', '##', '一、', '二、', '1.', '•', '-'])
        
        # 檢查是否包含異常內容（例如錯誤訊息）
        error_indicators = ['error', 'exception', 'traceback', 'failed']
        has_error = any(indicator in summary.lower() for indicator in error_indicators)
        
        return has_structure and not has_error
    
    def quick_summary(
        self,
        transcript: str,
        max_length: int = 500
    ) -> str:
        """
        快速摘要（簡短版本）
        
        Args:
            transcript: 逐字稿
            max_length: 最大輸出長度
        
        Returns:
            簡短摘要
        """
        max_input_chars = self._tokens_to_chars(self.max_input_tokens)
        truncated_transcript = transcript[:max_input_chars]
        
        prompt = "請用 %d 字以內總結以下內容的要點：\n\n%s\n\n重點摘要：" % (max_length, truncated_transcript)
        
        return self.client.generate(
            prompt=prompt,
            temperature=0.5,
            max_tokens=max_length * 2
        )


class MarkdownFormatter:
    """Markdown 格式化工具"""
    
    @staticmethod
    def format_meeting_record(
        summary: str,
        source_file: str,
        transcript: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        格式化為完整的會議記錄 Markdown
        
        Args:
            summary: 會議摘要
            source_file: 來源檔案
            transcript: 原始逐字稿
            metadata: 額外資訊
        
        Returns:
            格式化的 Markdown
        """
        from pathlib import Path
        
        source_name = Path(source_file).stem
        now = datetime.now()
        
        md = """# {source_name} - 會議記錄

> **生成時間**：{timestamp}  
> **原始檔案**：{filename}  
> **轉錄模型**：{whisper_model}  
> **摘要模型**：{llm_model}  
> **處理耗時**：{total_time}

---

{summary}

---

## 📝 原始逐字稿

<details>
<summary>點擊展開完整逐字稿（{transcript_len:,} 字）</summary>

```
{transcript}
```

</details>

---

*本文件由會議轉錄工具自動生成*  
*生成於 {timestamp}*
""".format(
            source_name=source_name,
            timestamp=now.strftime('%Y-%m-%d %H:%M:%S'),
            filename=Path(source_file).name,
            whisper_model=metadata.get('whisper_model', 'N/A'),
            llm_model=metadata.get('llm_model', 'N/A'),
            total_time=metadata.get('total_time', 'N/A'),
            summary=summary,
            transcript_len=len(transcript),
            transcript=transcript
        )
        return md
    
    @staticmethod
    def clean_summary(summary: str) -> str:
        """清理摘要文字"""
        # 移除多餘空行
        summary = re.sub(r'\n{3,}', '\n\n', summary)
        
        # 確保標題格式統一
        summary = re.sub(r'^(#{1,3})\s*', r'\1 ', summary, flags=re.MULTILINE)
        
        return summary.strip()


# 便捷函數
def summarize_transcript(
    transcript: str,
    ollama_client: OllamaClient,
    **kwargs
) -> str:
    """
    快速生成會議摘要
    
    Args:
        transcript: 逐字稿
        ollama_client: Ollama 客戶端
    
    Returns:
        摘要文字
    """
    summarizer = MeetingSummarizer(ollama_client, **kwargs)
    result = summarizer.summarize(transcript)
    return result.summary
