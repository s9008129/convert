"""
MeetingScribe 系統配置
v2.1 - 完整參數化設計
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator, SecretStr
from pydantic import Field

from backend.core.prompts import DEFAULT_MEETING_RECORD_PROMPT
from backend.core.asr_model_resolver import DEFAULT_BREEZE_ASR_26_REVISION


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
        default="http://host.docker.internal:11434",
        description="Ollama 服務端點"
    )
    LOCAL_LLM_MODEL: str = Field(
        default="gemma4:31b",
        description="本地 LLM 模型名稱（預設 gemma4 家族；必要時可由環境變數覆蓋為較小或量化變體）"
    )
    
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
    GEMINI_MODEL: str = Field(default="gemini-3.1-flash-lite", description="Gemini 模型名稱")
    DEFAULT_MODE: str = Field(default="local", description="預設處理模式 (local/cloud)")
    LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS: int = Field(
        default=8192,
        description="本地 LLM 實際可穩定使用的上下文 token 預算"
    )
    LOCAL_LLM_RESERVED_OUTPUT_TOKENS: int = Field(
        default=3072,
        description="本地 LLM 保留給最終輸出與修補的 token 預算"
    )
    LOCAL_LLM_CHUNK_OVERLAP_LINES: int = Field(
        default=4,
        description="長逐字稿切塊時保留的重疊行數"
    )
    LOCAL_LLM_MAX_REFINEMENT_ROUNDS: int = Field(
        default=2,
        description="本地摘要品質驗證後的最大補強輪數"
    )
    
    # ========================================
    # Whisper / ASR 設定
    # ========================================
    ASR_BACKEND: str = Field(
        default="auto",
        description="ASR 後端 (auto/transformers/faster_whisper)"
    )
    WHISPER_MODEL: str = Field(
        default="MediaTek-Research/Breeze-ASR-26",
        description="Whisper / ASR 模型名稱（支援 HuggingFace repo 或本地路徑）"
    )
    WHISPER_MODEL_REVISION: Optional[str] = Field(
        default=None,
        description="模型 revision / commit SHA（未指定時會自動鎖定 Breeze-ASR-26 官方預設版本）"
    )
    WHISPER_LANGUAGE: str = Field(
        default="auto",
        description="ASR 語言提示（auto/zh/en/...）"
    )
    WHISPER_DEVICE: str = Field(default="auto", description="Whisper 運算裝置 (auto/cuda/cpu)")
    WHISPER_COMPUTE_TYPE: str = Field(
        default="int8_float16",
        description="Whisper 計算精度 (int8/int8_float16/float16)"
    )
    
    # ========================================
    # ASR VAD 設定 (v4.0.0 新增)
    # ========================================
    ASR_VAD_ENABLED: bool = Field(
        default=True,
        description="是否啟用 VAD（語音活動偵測）"
    )
    ASR_VAD_THRESHOLD: float = Field(
        default=0.5,
        description="VAD 語音偵測閾值 (0.0-1.0)"
    )
    ASR_VAD_MIN_SPEECH_MS: int = Field(
        default=250,
        description="最短語音持續時間（毫秒）"
    )
    ASR_VAD_MIN_SILENCE_MS: int = Field(
        default=2000,
        description="觸發分割的最短靜音時間（毫秒）"
    )
    ASR_VAD_SPEECH_PAD_MS: int = Field(
        default=400,
        description="語音前後保留緩衝（毫秒）"
    )
    ASR_BEAM_SIZE: int = Field(
        default=5,
        description="Beam Search 大小"
    )
    ASR_RETURN_TIMESTAMPS: bool = Field(
        default=True,
        description="是否回傳可供驗證使用的 timestamps/chunks"
    )
    ASR_CHUNK_LENGTH_SECONDS: int = Field(
        default=30,
        description="Transformers ASR pipeline chunk length"
    )
    ASR_LOCAL_FILES_ONLY: bool = Field(
        default=False,
        description="是否只使用本地快取模型檔"
    )
    ASR_SAFE_ALLOW_PATTERNS: str = Field(
        default="config.json,generation_config.json,preprocessor_config.json,tokenizer_config.json,special_tokens_map.json,normalizer.json,merges.txt,vocab.json,added_tokens.json,model.safetensors.index.json,model-*.safetensors",
        description="允許下載的模型檔案模式"
    )
    ASR_SAFE_DENY_PATTERNS: str = Field(
        default="*.bin,*.pt,*.pth,*.ckpt,training_args.bin",
        description="禁止下載的模型檔案模式"
    )
    ASR_TRANSFORMERS_MIN_VRAM_MB: int = Field(
        default=6000,
        description="Transformers ASR 最低建議可用 VRAM（MB）"
    )
    ASR_INITIAL_PROMPT: str = Field(
        default="以下是台灣繁體中文的會議記錄。",
        description="轉錄初始提示詞"
    )
    
    # ========================================
    # 系統設定
    # ========================================
    LOG_LEVEL: str = Field(default="INFO", description="日誌等級")
    DATA_DIR: str = Field(default="/app/data", description="資料目錄")
    
    # ========================================
    # System Prompt 設定
    # v4.3.0：統一為臺灣公務機關正式會議紀錄格式提示詞
    # ========================================
    DEFAULT_SYSTEM_PROMPT: str = Field(
        default=DEFAULT_MEETING_RECORD_PROMPT,
        description="臺灣公務機關會議紀錄系統提示詞（正式公務欄位格式）"
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

    @property
    def asr_safe_allow_patterns_list(self) -> List[str]:
        return [pattern.strip() for pattern in self.ASR_SAFE_ALLOW_PATTERNS.split(",") if pattern.strip()]

    @property
    def asr_safe_deny_patterns_list(self) -> List[str]:
        return [pattern.strip() for pattern in self.ASR_SAFE_DENY_PATTERNS.split(",") if pattern.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全域設定實例
settings = Settings()
