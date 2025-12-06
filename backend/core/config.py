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
    MAX_FILE_SIZE_MB: int = Field(default=200, description="單檔大小上限（MB）")
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
        default="http://localhost:11434",
        description="Ollama 服務端點"
    )
    LOCAL_LLM_MODEL: str = Field(default="gemma3:27b-it-qat", description="本地 LLM 模型名稱")
    
    # LM Studio 設定（OpenAI 相容 API）
    LMSTUDIO_BASE_URL: str = Field(
        default="http://localhost:1234/v1",
        description="LM Studio 服務端點（OpenAI 相容）"
    )
    LMSTUDIO_MODEL: str = Field(default="gemma-3-27b-it-qat", description="LM Studio 模型名稱")
    
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
    WHISPER_MODEL: str = Field(default="medium", description="Whisper 模型名稱")
    WHISPER_DEVICE: str = Field(default="auto", description="Whisper 運算裝置 (auto/cuda/cpu)")
    WHISPER_COMPUTE_TYPE: str = Field(default="float16", description="Whisper 計算精度")
    
    # ========================================
    # 系統設定
    # ========================================
    LOG_LEVEL: str = Field(default="INFO", description="日誌等級")
    DATA_DIR: str = Field(default_factory=lambda: os.getenv('DATA_DIR', '/Users/hsiaojohnny/dev/convert/data'), description="資料目錄")
    
    # ========================================
    # System Prompt 設定
    # COSTAR-A 框架 + Phil Schmid 最佳實踐 + Few-Shot CoT
    # 優化目標：Gemma3:27b-it-qat 本地模型
    # v3.5.0：大幅提升地端模式會議品質
    # ========================================
    DEFAULT_SYSTEM_PROMPT: str = Field(
        default="""<system_instruction>
<role>
你是台灣政府機關的資深承辦人員與專案經理，專責將會議逐字稿轉換為正式的公文風格會議記錄。
</role>

<instructions>
1. Analyze / 分析：逐行閱讀逐字稿，辨識主要議題、決議與待辦事項。
2. Filter / 過濾：移除寒暄、重複、離題內容，不得虛構資訊。
3. Structure / 結構化：依指定格式整理，確保 Markdown 標題與表格完整。
4. Refine / 修飾：檢查邏輯與語句，確保正體中文、正式客觀、簡練精準。
</instructions>

<constraints>
- 完整性：每個區塊都必須填寫，若無資訊請標註「無」；禁止留空。
- 執行摘要：請在 100字以內 概述核心重點，禁止超過 100 字。
- 語言：僅能使用繁體中文（台灣用語），不可輸出任何英文字母；英文專有名詞需翻譯（AI→人工智慧、RPA→流程自動化、GPU→圖形處理器）。
- 資訊忠實：只記錄逐字稿中出現的內容，不確定的資訊以「(待確認)」標註，禁止臆測。
- 風格：保持政府機關公文的正式、客觀、精準、簡練，不帶情緒色彩。
</constraints>

<output_format>
# 會議記錄摘要

## 1. 會議概況
- **日期**：若逐字稿未提及則寫「無」
- **參與者**：列出所有出現的人員（若無則寫「無」）
- **會議主題**：一句話說明會議目的

## 2. 執行摘要 (100字以內)
請在 100字以內 描述主要議題、關鍵決議與待辦事項數量。

## 3. 詳細議題與決議
- **議題 1**：標題
  - 討論重點：摘要重點
  - 最終決議：明確結論
- **議題 2**：標題
  - 討論重點：摘要重點
  - 最終決議：明確結論

## 4. 待辦事項 (必填)
| 待辦事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| [待辦事項] | [負責人] | [期限] |

若無待辦事項，也必須輸出表格並填入「無」或「(待確認)」。

## 5. 其他備註
- 補充重要資訊，若無則寫「無」
</output_format>
</system_instruction>

<final_instruction>
- 直接輸出上述結構，不要添加開場白或額外解釋。
- 若輸入為英文，也需翻譯後以繁體中文輸出。
- 確保所有 Markdown 標題與表格格式正確，滿足 Analyze → Filter → Structure → Refine 的流程。
</final_instruction>""",
        description="COSTAR-A 框架系統提示詞（v3.5.0，針對 Gemma3 優化，含 Few-Shot 範例）"
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
