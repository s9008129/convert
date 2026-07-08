"""
MeetingScribe 系統配置（版本以根目錄 VERSION 檔為唯一來源）

注意：後端僅讀取「環境變數 / .env」；config.yaml 只供舊版 CLI 使用，
修改 config.yaml 對後端服務無效（詳見系統改善及優化計畫 P0-3）。
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
    LOCAL_LLM_KEEP_ALIVE: str = Field(
        default="10m",
        description="Ollama keep_alive；三階段流程期間保留模型於記憶體，避免每階段重載大模型（P0-7）"
    )
    LOCAL_LLM_MAX_MERGE_ROUNDS: int = Field(
        default=3,
        description="萃取筆記整併的最大輪數；超過或縮減停滯即停止整併改用硬截斷，防止無窮迴圈"
    )
    LOCAL_LLM_DISABLE_THINKING: bool = Field(
        default=True,
        description="關閉思考型模型（如 gemma4）的 thinking 輸出；否則 num_predict 預算會被思考耗盡導致正文極短或為空（E2E 實測根因）"
    )

    # ========================================
    # 逐字稿語意校正（P1-2 ~ P1-4 語意校正機制）
    # ========================================
    ENABLE_TRANSCRIPT_CORRECTION: bool = Field(
        default=True,
        description="是否啟用逐字稿 LLM 語意校正（同音錯字/專有名詞修正，含同音驗證閘門）"
    )
    CORRECTION_SCOPE: str = Field(
        default="auto",
        description="校正範圍：auto=僅詞彙表模糊命中段落（實測建議值）、all=全部段落（長會議耗時極高）、off=停用"
    )
    CORRECTION_MAX_SEGMENT_CHARS: int = Field(
        default=400,
        description="校正分段長度上限（字元）"
    )
    CORRECTION_CONTEXT_CHARS: int = Field(
        default=60,
        description="校正時附帶的前文唯讀上下文長度（字元）"
    )
    CORRECTION_MAX_CHANGE_RATIO: float = Field(
        default=0.10,
        description="單段允許的最大改動比例，超過即整段放棄校正（防過度改寫）"
    )
    GLOSSARY_DIR: str = Field(
        default="",
        description="機關詞彙表目錄（空值 = 專案內 data/glossary）"
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
        default=500,
        description="觸發分割的最短靜音時間（毫秒）；P1-6 依實證由 2000 調降為 500"
    )
    ASR_VAD_SPEECH_PAD_MS: int = Field(
        default=400,
        description="語音前後保留緩衝（毫秒）"
    )
    ASR_BEAM_SIZE: int = Field(
        default=5,
        description="Beam Search 大小"
    )
    # ---- P1-6 實證參數組（faster-whisper 路徑）----
    ASR_CONDITION_ON_PREVIOUS_TEXT: bool = Field(
        default=False,
        description="是否以前段輸出作為後段條件；長檔防重複迴圈第一要務，預設關閉"
    )
    ASR_COMPRESSION_RATIO_THRESHOLD: float = Field(
        default=2.2,
        description="壓縮比幻覺門檻；中文建議 2.2（原預設 2.4）"
    )
    ASR_NO_SPEECH_THRESHOLD: float = Field(
        default=0.5,
        description="無語音判定門檻（原預設 0.6）"
    )
    ASR_REPETITION_PENALTY: float = Field(
        default=1.1,
        description="重複懲罰；中文重複字幻覺抑制"
    )
    ASR_NO_REPEAT_NGRAM_SIZE: int = Field(
        default=3,
        description="禁止重複的 n-gram 長度；0 = 停用"
    )
    ASR_ENABLE_HOTWORDS: bool = Field(
        default=True,
        description="是否將機關詞彙表注入 ASR（faster-whisper hotwords / transformers prompt）"
    )
    ASR_CHUNK_STRIDE_SECONDS: int = Field(
        default=5,
        description="Transformers 長音檔分塊的左右重疊秒數（P0-2 重疊解碼）"
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
        default="config.json,generation_config.json,preprocessor_config.json,tokenizer_config.json,special_tokens_map.json,normalizer.json,merges.txt,vocab.json,added_tokens.json,model.safetensors.index.json,model-*.safetensors,model.safetensors",
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
    ALLOWED_ORIGINS: str = Field(
        default="*",
        description="CORS 允許來源（逗號分隔）；* 時自動停用 credentials（P2-7）"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
    
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
