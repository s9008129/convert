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


# 預設系統提示詞
DEFAULT_SYSTEM_PROMPT = """你是一位專業的政府機關資深承辦人員，擅長整理會議紀錄。

請根據以下逐字稿，整理出結構化的會議摘要。

## 輸出要求

1. 使用台灣繁體中文
2. 語氣正式專業
3. 重點摘要，避免冗長
4. 保留重要的人名、日期、數字
5. 不要虛構或添加逐字稿中沒有的內容

## 輸出格式

### 一、會議概要
- 會議主題（根據內容推斷）
- 主要與會者（如有提及）
- 會議時長（如有提及）

### 二、議題與決議（約 400 字）
- 列出主要討論議題
- 說明最終決議或共識
- 標註表決結果（如有）

### 三、問題與解決方案（約 300 字）
- 列出會議中提出的問題
- 說明對應的解決方案或處理方式
- 標註待解決的問題

### 四、追蹤事項（約 300 字）
- 列出需要追蹤的事項
- 標註負責人（如有提及）
- 標註預計完成時間（如有提及）

### 五、其他備註
- 其他重要但不屬於上述分類的內容
- 特殊情況說明"""


# 簡潔版系統提示詞
CONCISE_SYSTEM_PROMPT = """你是專業的會議記錄整理專家。請將以下逐字稿整理成結構化摘要。

要求：
1. 使用繁體中文
2. 精簡扼要
3. 保留重要資訊

格式：
## 會議重點
（3-5 個要點）

## 決議事項
（列表形式）

## 待辦追蹤
（負責人、期限）"""


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
