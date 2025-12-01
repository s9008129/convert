"""
MeetingScribe 系統配置
v2.1 - 完整參數化設計
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator, SecretStr
from pydantic import Field


class Settings(BaseSettings):
    """
    系統配置 - 所有參數都可透過環境變數覆蓋
    """
    
    # ========================================
    # 檔案上傳限制（v2.1 新增）
    # ========================================
    MAX_FILE_SIZE_MB: int = Field(default=100, description="單檔大小上限（MB）")
    ENABLE_BATCH_UPLOAD: bool = Field(default=False, description="是否允許批次上傳")
    ALLOWED_EXTENSIONS: str = Field(
        default=".mp3,.mp4,.wav,.m4a,.mkv,.webm,.ogg,.flac,.avi,.mov",
        description="允許的檔案副檔名"
    )
    
    # ========================================
    # 排隊系統設定（v2.1 新增）
    # ========================================
    MAX_CONCURRENT_TASKS: int = Field(default=1, description="最大同時處理任務數")
    QUEUE_MAX_SIZE: int = Field(default=50, description="排隊佇列最大長度")
    TASK_TIMEOUT_SECONDS: int = Field(default=3600, description="單一任務超時時間（秒）")
    ESTIMATED_MINUTES_PER_TASK: int = Field(default=4, description="預估每個任務處理時間（分鐘）")
    
    # ========================================
    # LLM 設定
    # ========================================
    OLLAMA_BASE_URL: str = Field(
        default="http://host.docker.internal:11434",
        description="Ollama 服務端點"
    )
    LOCAL_LLM_MODEL: str = Field(default="gemma3:12b", description="本地 LLM 模型名稱")
    
    # LM Studio 設定（OpenAI 相容 API）
    LMSTUDIO_BASE_URL: str = Field(
        default="http://host.docker.internal:1234/v1",
        description="LM Studio 服務端點（OpenAI 相容）"
    )
    LMSTUDIO_MODEL: str = Field(default="gpt-oss-20b", description="LM Studio 模型名稱")
    
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Gemini API 金鑰")
    
    @field_validator('GEMINI_API_KEY')
    @classmethod
    def validate_gemini_api_key(cls, v):
        """驗證 Gemini API Key 不應包含危險字符"""
        if v and not isinstance(v, str):
            raise ValueError("GEMINI_API_KEY 必須是字串")
        if v and len(v) < 10:
            raise ValueError("GEMINI_API_KEY 格式無效（長度過短）")
        # 檢查是否包含特殊字符（API Key 應該只包含英數字符和連字號/底線）
        if v:
            import re
            if not re.match(r'^[A-Za-z0-9_-]+$', v):
                raise ValueError("GEMINI_API_KEY 格式無效（包含不允許的字符）")
        return v
    GEMINI_BASE_URL: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="Gemini API 端點"
    )
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash-lite", description="Gemini 模型名稱")
    DEFAULT_MODE: str = Field(default="local", description="預設處理模式 (local/cloud)")
    
    # ========================================
    # Whisper 設定
    # ========================================
    WHISPER_MODEL: str = Field(default="large-v3", description="Whisper 模型名稱")
    WHISPER_DEVICE: str = Field(default="auto", description="Whisper 運算裝置 (auto/cuda/cpu)")
    WHISPER_COMPUTE_TYPE: str = Field(default="float16", description="Whisper 計算精度")
    
    # ========================================
    # 系統設定
    # ========================================
    LOG_LEVEL: str = Field(default="INFO", description="日誌等級")
    DATA_DIR: str = Field(default="/app/data", description="資料目錄")
    
    # ========================================
    # System Prompt 設定
    # COSTAR-X 框架：融合 COSTAR-A 與 Phil Schmid 的 Gemini 提示實踐指南
    # 優化目標：本地 Gemma 3 12B/27B 模型
    # ========================================
    DEFAULT_SYSTEM_PROMPT: str = Field(
        default="""<system_instruction>
<role>
你是一位專業的行政秘書與專案經理。你擅長從雜亂的會議逐字稿中提取關鍵資訊，並轉化為結構清晰、商業風格的繁體中文會議記錄。你的風格是客觀、精準且簡練。
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
- **Tone**：專業商務 (Professional Business)，不帶情緒色彩。
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
</final_instruction>""",
        description="預設系統 Prompt (COSTAR-X 框架，針對 Gemma 3 優化)"
    )
    
    @property
    def max_file_size_bytes(self) -> int:
        """取得檔案大小上限（bytes）"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """取得允許的副檔名列表"""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    @property
    def uploads_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "uploads")
    
    @property
    def outputs_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "outputs")
    
    @property
    def cache_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "cache")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全域設定實例
settings = Settings()
