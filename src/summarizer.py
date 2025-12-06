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
from backend.core.config import settings

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


DEFAULT_SYSTEM_PROMPT = settings.DEFAULT_SYSTEM_PROMPT


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
        
        # 檢查語言合規性：計算英文詞的比例
        english_words = self._count_english_words(summary)
        total_words = len(summary.split())
        english_ratio = english_words / total_words if total_words > 0 else 0
        
        # 如果英文比例 > 10%，則警告（Critical）
        if english_ratio > 0.1:
            logger.error(
                "[品質警告] 英文混入比例過高：%.1f%%（檢測到 %d 個英文詞）",
                english_ratio * 100,
                english_words
            )
            return False
        
        return has_structure and not has_error
    
    def _count_english_words(self, text: str) -> int:
        """計算文本中的英文單詞數量"""
        import re
        # 匹配英文單詞（連續的英文字母）
        english_pattern = r'\b[a-zA-Z]+\b'
        matches = re.findall(english_pattern, text)
        return len(matches)
    
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
    
    # 常見英文詞彙黑名單（如果在正體中文會議記錄中出現，應視為錯誤）
    ENGLISH_BLACKLIST = {
        'Okay', 'okay', 'Let', 'let', 'Recap', 'recap', 'action', 'Action',
        'items', 'Items', 'discussion', 'Discussion', 'core', 'Core',
        'challenges', 'Challenges', 'talking', 'Talking', 'points', 'Points',
        'preparation', 'Preparation', 'Director', 'director', 'Meeting', 'meeting',
        'AI', 'Human', 'Control', 'Intervention', 'Problem', 'Explanation',
        'Blame', 'Focus', 'Preparation', 'Example', 'Scenarios', 'Case',
        'Document', 'Collection', 'Retraining', 'Strategy', 'Demonstration',
        'Performance', 'Report', 'Contextual', 'Analysis', 'Message', 'Key',
        'Message', 'Automatic', 'Manual', 'Routing', 'Context', 'Nuances',
        'Language', 'Categorization', 'Tend', 'Miscategorize', 'Documents',
        'Approach', 'Oversight', 'Correction', 'Prevent', 'Errors', 'Frame',
        'Dynamic', 'Nature', 'Model', 'Monitor', 'Refinement', 'Accuracy',
        'Reliability', 'Committed', 'Ensure', 'Proactive', 'System', 'Require'
    }
    
    @staticmethod
    def _remove_english_segments(text: str) -> str:
        """
        移除或修復包含過多英文的段落
        
        策略：
        1. 檢測以英文字母開頭的段落
        2. 如果段落中英文詞比例 > 50%，則移除
        3. 如果混合中英，則提取中文部分
        """
        import re
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 檢查行的第一個非空字符
            stripped = line.lstrip()
            
            if stripped and stripped[0].isascii() and stripped[0].isalpha():
                # 如果行以英文字母開頭，檢查是否應該保留
                # 保留 Markdown 標題和特殊符號開頭的行
                if stripped.startswith('#') or stripped.startswith('*') or \
                   stripped.startswith('|') or stripped.startswith('-') or \
                   stripped.startswith('>'):
                    cleaned_lines.append(line)
                else:
                    # 檢查英文詞的比例
                    english_words = len(re.findall(r'\b[a-zA-Z]+\b', line))
                    total_words = len(line.split())
                    
                    if total_words > 0 and english_words / total_words > 0.5:
                        # 英文比例過高，跳過此行
                        logger.warning("[清理] 移除高英文比例行: %s...", line[:50])
                        continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def _sanitize_text_language(text: str) -> str:
        """
        淨化文本中的英文詞彙
        
        用中文替代常見英文詞彙，用於應急修正
        """
        import re
        
        replacements = {
            r'\bOkay\b': '好',
            r'\bokay\b': '好',
            r'\bLet\b': '讓',
            r'\blet\b': '讓',
            r'\bRecap\b': '總結',
            r'\brecap\b': '總結',
            r'\bAI\b': '人工智慧',
            r'\bRPA\b': '流程自動化',
            r'\bPOC\b': '概念驗證',
            r'\bKPI\b': '關鍵績效指標',
            r'\bCEO\b': '首席執行官',
            r'\bEdge\b': '邊緣',
            r'\bOllama\b': '本地模型系統',
            r'\bCPU\b': '中央處理器',
            r'\bGPU\b': '圖形處理器',
            r'\bAPI\b': '應用介面',
            r'\bJSON\b': '資料格式',
            r'\bSQL\b': '結構化查詢',
            r'\bURL\b': '網址',
            r'\bID\b': '識別碼',
            r'\bDI\b': '數位身份',
        }
        
        result = text
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result)
        
        return result
    
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
        
        # 步驟 1：淨化英文
        cleaned_summary = MarkdownFormatter._remove_english_segments(summary)
        
        # 步驟 2：應急修正英文詞彙
        if MarkdownFormatter._has_excessive_english(cleaned_summary):
            logger.warning("[修正] 偵測到英文混入，執行詞彙替換...")
            cleaned_summary = MarkdownFormatter._sanitize_text_language(cleaned_summary)
        
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
            summary=cleaned_summary,
            transcript_len=len(transcript),
            transcript=transcript
        )
        return md
    
    @staticmethod
    def _has_excessive_english(text: str) -> bool:
        """檢查文本中是否有過多英文"""
        import re
        
        # 計算英文詞比例
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        total_words = len(text.split())
        
        if total_words == 0:
            return False
        
        english_ratio = english_words / total_words
        
        # 如果英文比例 > 15%，判定為過多
        if english_ratio > 0.15:
            logger.warning(
                "[品質] 檢測到高英文比例: %.1f%% (%d/%d 詞)",
                english_ratio * 100, 
                english_words, 
                total_words
            )
            return True
        
        return False
    
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
