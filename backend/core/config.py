"""
系統配置（版本以根目錄 VERSION 檔為唯一來源）

注意：後端僅讀取「環境變數 / .env」；config.yaml 只供舊版 CLI 使用，
修改 config.yaml 對後端服務無效（詳見系統改善及優化計畫 P0-3）。
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, SecretStr
from pydantic import Field, AliasChoices

from backend.core.prompts import DEFAULT_MEETING_RECORD_PROMPT
from backend.core.asr_model_resolver import DEFAULT_BREEZE_ASR_26_REVISION
from backend.core.platform_config import (
    get_default_lmstudio_base_url,
    normalize_lmstudio_base_url,
)


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
    # v4.6.2：移除從未生效的 TASK_TIMEOUT_SECONDS——整任務 wait_for 對長會議
    # 是合法超時，且無法安全取消 executor 中的 ASR；超時控制改在每次 LLM 請求層級
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
        description="本地 LLM 模型名稱（預設 gemma4 家族；VRAM 吃緊時可一行改 gemma4:26b——~16GB 全 VRAM、快 5.8 倍、品質略降，參考專案實測）"
    )

    LOCAL_LLM_PROVIDER: str = Field(
        default="auto",
        description="本地 LLM provider（auto/lmstudio/ollama）；Apple Silicon auto 使用 LM Studio"
    )
    
    # LM Studio 設定（OpenAI 相容 API）
    LMSTUDIO_BASE_URL: str = Field(
        default_factory=get_default_lmstudio_base_url,
        description="LM Studio root 服務端點；可接受舊設定的 /v1 suffix"
    )
    LMSTUDIO_MODEL: Optional[str] = Field(
        default=None,
        description="LM Studio optional explicit model/instance override；未設定時依 loaded instance 決定"
    )
    
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

    @field_validator("CLOUD_LLM_PROVIDER")
    @classmethod
    def validate_cloud_llm_provider(cls, value: str) -> str:
        normalized = (value or "ollama_cloud").strip().lower().replace("-", "_")
        if normalized in {"ollama", "ollama_cloud", "ollama_cloud_api"}:
            return "ollama_cloud"
        if normalized == "gemini":
            return "gemini"
        raise ValueError("CLOUD_LLM_PROVIDER 必須是 ollama_cloud 或 gemini")

    @field_validator("OLLAMA_API_KEY", mode="before")
    @classmethod
    def normalize_ollama_api_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("OLLAMA_API_KEY 必須是字串")
        normalized = value.strip()
        return normalized or None

    @field_validator("OLLAMA_CLOUD_BASE_URL", mode="before")
    @classmethod
    def normalize_ollama_cloud_url(cls, value: Optional[str]) -> str:
        normalized = (value or "").strip().rstrip("/")
        return normalized or "https://ollama.com/v1"

    @field_validator("OLLAMA_CLOUD_MODEL", mode="before")
    @classmethod
    def normalize_ollama_cloud_model(cls, value: Optional[str]) -> str:
        normalized = (value or "").strip()
        return normalized or "deepseek-v4.1-flash"

    @field_validator("LOCAL_LLM_PROVIDER")
    @classmethod
    def validate_local_llm_provider(cls, value: str) -> str:
        normalized = (value or "auto").strip().lower()
        if normalized not in {"auto", "lmstudio", "ollama"}:
            raise ValueError(
                "LOCAL_LLM_PROVIDER 必須是 auto、lmstudio 或 ollama"
            )
        return normalized

    @field_validator("LMSTUDIO_MODEL", mode="before")
    @classmethod
    def normalize_lmstudio_model(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("LMSTUDIO_MODEL 必須是字串或空值")
        normalized = value.strip()
        return normalized or None

    @field_validator("LMSTUDIO_BASE_URL", mode="before")
    @classmethod
    def normalize_lmstudio_url(cls, value: Optional[str]) -> str:
        return normalize_lmstudio_base_url(value)

    GEMINI_BASE_URL: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="Gemini API 端點"
    )
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash-lite", description="Gemini 模型名稱")

    # ========================================
    # 雲端 LLM provider（v4.7.1，T20260913-1900-01）
    # ========================================
    # 雲端模式預設為 Gemini（使用者日常設定）；Ollama Cloud 保留為可選 provider，
    # 以 CLOUD_LLM_PROVIDER=ollama_cloud 啟用。所有雲端呼叫一律透過下方的
    # cloud_llm_* 屬性取值，不得再直接讀 GEMINI_*。
    CLOUD_LLM_PROVIDER: str = Field(
        default="gemini",
        description="雲端 LLM provider（gemini/ollama_cloud）"
    )
    OLLAMA_API_KEY: Optional[str] = Field(
        default=None,
        description="Ollama Cloud API 金鑰（CLOUD_LLM_PROVIDER=ollama_cloud 時使用）"
    )
    OLLAMA_CLOUD_BASE_URL: str = Field(
        default="https://ollama.com/v1",
        description="Ollama Cloud OpenAI 相容端點"
    )
    OLLAMA_CLOUD_MODEL: str = Field(
        default="deepseek-v4.1-flash",
        description="Ollama Cloud 模型名稱"
    )
    CLOUD_LLM_CHUNK_TOKENS: int = Field(
        default=3200,
        description="雲端萃取分塊大小（tokens）；僅在 CLOUD_LLM_SEGMENTED_EXTRACTION=true 時生效（v4.3.3 沿用地端實證的分塊密度）"
    )
    CLOUD_LLM_MAX_CONCURRENT_REQUESTS: int = Field(
        default=3,
        description="雲端分段萃取的併發請求數上限（避免觸發 API rate limit）"
    )
    CLOUD_LLM_SEGMENTED_EXTRACTION: bool = Field(
        default=False,
        description="雲端萃取是否分段（預設 False＝單次呼叫整份逐字稿；設 True 可回退 v4.3.3 分段併發萃取）"
    )
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
    # ========================================
    # v4.8.0（T20260922-1930-01）：地端深度紀錄品質對齊雲端
    # ========================================
    # 根因（實測 task b20c90a7／836fcae7）：128K context 已載入的情況下，地端仍被
    # 三個「與 context 無關的固定常數」鎖死——分塊輸入 3200、單次輸出 3072、整併
    # 可見目標 4096。逐字稿 11,712 est 被切成 4 塊（每塊只用到可承載量的 2.6%），
    # 4 份萃取筆記合計 8,176 tokens 送進整併後輸出上限 3,072 且 finish_reason=length
    # （被截斷、流程靜默接受），最終紀錄只承載逐字稿的 15.7%。雲端路徑沒有這些上限
    # （逐字稿整份進最終生成），因此品質差距的主因是「管線」而不是「模型」。
    # 以下把上限改為「依 context 推導」，並保留可回復的設定旋鈕。
    LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING: int = Field(
        default=0,
        description="地端萃取分塊的每塊輸入上限（tokens）；0＝依 context 推導"
                    "（移除固定 3200；小 context 的推導值與舊值幾乎相同，行為不變）"
    )
    LOCAL_LLM_OUTPUT_TOKENS_CEILING: int = Field(
        default=8192,
        description="地端單次生成輸出的天花板（tokens）；0＝完全不設上限。"
                    "實際值仍由 context 餘裕推導，且不低於 LOCAL_LLM_RESERVED_OUTPUT_TOKENS"
    )
    LOCAL_LLM_CONTEXT_SAFETY_MARGIN_TOKENS: int = Field(
        default=256,
        description="依 context 推導輸出預算時保留的安全邊界（tokens）"
    )
    LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION: bool = Field(
        default=True,
        description="地端最終生成與補強是否同時餵入原始逐字稿（雙輸入，比照雲端）；"
                    "context 餘裕不足時自動退回只餵萃取筆記"
    )
    LOCAL_LLM_ZERO_LOSS_NOTES_PASSTHROUGH: bool = Field(
        default=True,
        description="當萃取筆記總量已被最終生成階段承接時，略過有損的 LLM 整併，"
                    "改用零損串接（比照雲端分段模式）；筆記超出下游預算時才整併"
    )
    # 取樣參數（v4.8.0）：官方 Qwen3.6／3.8 model card 對「非思考模式」建議
    # temperature=0.7、top_p=0.80、top_k=20，並明文警告勿用 greedy；
    # 舊行為只送 temperature（萃取 0.1／生成 0.2／補強 0.15／校正 0.0 greedy）
    # 且完全不送 top_p／top_k，等於失去官方建議的分佈控制。
    # 注意：本機這兩顆模型走 LM Studio 的 Splash 引擎，該引擎對
    # min_p／presence_penalty／frequency_penalty 非 0 值直接回 HTTP 400，
    # 因此只送 top_p／top_k（官方建議的 presence_penalty 1.5 在此不可用）。
    LOCAL_LLM_SAMPLING_TOP_P: Optional[float] = Field(
        default=0.8,
        description="LM Studio 取樣 top_p（None＝不送，沿用端點預設）"
    )
    LOCAL_LLM_SAMPLING_TOP_K: Optional[int] = Field(
        default=20,
        description="LM Studio 取樣 top_k（None＝不送；Splash 引擎上限 32）"
    )
    LOCAL_LLM_EXTRACTION_TEMPERATURE: float = Field(
        default=0.6,
        description="地端萃取階段 temperature（官方非思考建議 0.7；萃取偏忠實故略低）"
    )
    LOCAL_LLM_GENERATION_TEMPERATURE: float = Field(
        default=0.7,
        description="地端最終生成階段 temperature（官方非思考建議值）"
    )
    LOCAL_LLM_REFINEMENT_TEMPERATURE: float = Field(
        default=0.7,
        description="地端補強階段 temperature（官方非思考建議值）"
    )
    LOCAL_LLM_MERGE_TEMPERATURE: float = Field(
        default=0.6,
        description="地端整併階段 temperature（官方非思考建議 0.7；整併偏忠實故略低）"
    )
    LOCAL_LLM_CORRECTION_TEMPERATURE: float = Field(
        default=0.3,
        description="逐字稿語意校正 temperature；舊值 0.0 會讓 Splash 引擎走 GREEDY"
                    " 解碼（官方明文警告勿用 greedy，易僵化與重複）"
    )
    LOCAL_LLM_MAX_REFINEMENT_ROUNDS: int = Field(
        default=2,
        description="本地摘要品質驗證後的最大補強輪數"
    )
    LOCAL_LLM_KEEP_ALIVE: str = Field(
        default="30m",
        description="Ollama keep_alive；三階段流程期間保留模型於記憶體，避免每階段重載大模型（P0-7；v4.7.0 對齊參考專案調為 30m）"
    )
    LOCAL_LLM_MAX_MERGE_ROUNDS: int = Field(
        default=3,
        description="萃取筆記整併的最大輪數；超過或單輪無實質進度即拋 LOCAL_LLM_MERGE_NOT_CONVERGED（保留全部來源事實，不硬截斷），防止無窮迴圈"
    )
    # LM Studio reasoning-only 空回應（content 空 + finish_reason=length）允許
    # 恰好一次 semantic retry 的 max_tokens 上限（T20260827-1127-01 H-2）
    LMSTUDIO_REASONING_RETRY_MAX_TOKENS: int = Field(
        default=8192,
        description="LM Studio reasoning-only 空回應允許一次 semantic retry 的 max_tokens 上限"
    )
    LOCAL_LLM_DISABLE_THINKING: bool = Field(
        default=True,
        description="關閉思考型模型（如 gemma4）的 thinking 輸出；否則 num_predict 預算會被思考耗盡導致正文極短或為空（E2E 實測根因）"
    )

    # ========================================
    # LLM 請求逾時與重試（v4.6.2）
    # 根因背景：ASR 前強制卸載 Ollama 模型（VRAM 交接），冷載入＋長會議多次
    # 呼叫使單一 /api/chat 逾時（httpx ReadTimeout，str() 為空）即毀掉整份紀錄
    # ========================================
    LOCAL_LLM_REQUEST_TIMEOUT: float = Field(
        default=1800.0,
        description="每次 Ollama /api/chat 總時長上限（秒）；v4.7.0 改 streaming 後卡死由閒置逾時偵測，總上限放寬（寧可等待不截斷）"
    )
    LOCAL_LLM_STREAM_IDLE_TIMEOUT: float = Field(
        default=120.0,
        description="串流回應 chunk 間最大閒置秒數；超過視為連線卡死（可重試）"
    )
    LOCAL_LLM_MIN_TOKENS_PER_SECOND: float = Field(
        default=5.0,
        description="生成吞吐低於此值即警告疑似 CPU offload（v4.7.0 觀測門檻）"
    )
    LOCAL_LLM_DEGRADED_CONTEXT_TOKENS: int = Field(
        default=8192,
        description="warmup 自我修復後仍偵測到 offload 時，本任務降級使用的 num_ctx（f16 KV 下 8192 約 21.5GB，含 scheduler 邊際仍可全載）"
    )
    LOCAL_LLM_WARMUP_TIMEOUT: float = Field(
        default=600.0,
        description="ASR 後預熱（load-only 重載模型）專用逾時（秒）；把冷載入時間從生成呼叫的逾時額度中拆出"
    )
    LOCAL_LLM_TRANSIENT_RETRIES: int = Field(
        default=2,
        description="每次本地 LLM 呼叫對瞬時錯誤（timeout/連線中斷）的額外重試次數"
    )
    LOCAL_LLM_RETRY_BACKOFF_SECONDS: float = Field(
        default=5.0,
        description="瞬時錯誤重試的線性退避基數（第 n 次重試前等待 n×backoff 秒）"
    )
    CLOUD_LLM_REQUEST_TIMEOUT: float = Field(
        default=600.0,
        description="Gemini（OpenAI 相容）請求逾時（秒）"
    )
    CLOUD_LLM_MAX_RETRIES: int = Field(
        default=2,
        description="雲端呼叫重試次數（SDK max_retries＋應用層串流中斷重試共用）"
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
        description=(
            "ASR 後端 (auto/transformers/faster_whisper/mlx_whisper/apple)；"
            "macOS 僅提供 auto/apple（Apple SpeechAnalyzer），apple 不支援非 macOS"
        )
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
    # v4.7.0：ASR 子程序隔離——唯一能保證 CUDA context／分配器殘留完全釋回的方式
    # 是程序退出（faster-whisper#992 實測長駐程序每次殘留 ~312MB，蠶食 Ollama 可用 VRAM）
    ASR_ISOLATION: str = Field(
        default="subprocess",
        description="ASR 執行隔離模式：subprocess=獨立子程序（VRAM 保證歸還）／inprocess=舊行為（回退桿）"
    )
    ASR_WORKER_TIMEOUT_SECONDS: float = Field(
        default=7200.0,
        description="ASR 子程序硬上限（秒）；逾時 kill 並判定任務失敗（超長音檔屬病態輸入，不退回 in-process）"
    )

    # ========================================
    # Apple SpeechAnalyzer 設定（僅 macOS；T20260912-2242-01）
    # ========================================
    APPLE_SPEECH_CLI_PATH: str = Field(
        default="",
        description="apple-speech-cli 執行檔路徑（空=依序搜尋 repo release 產物→PATH；不自動編譯）"
    )
    APPLE_LOCALE: str = Field(
        default="zh-Hant-TW",
        description="Apple SpeechAnalyzer locale（預設繁體中文台灣）"
    )
    APPLE_PRESET: str = Field(
        default="time-indexed",
        description="Apple SpeechAnalyzer preset（time-indexed 才有逐詞時間軸）"
    )
    APPLE_ENABLE_PREFLIGHT: bool = Field(
        default=True,
        description="MP3 等脆弱容器是否先預轉 16k mono WAV（效能關鍵；關閉只影響速度）"
    )

    # ========================================
    # 說話者分離（diarization；T20260913-1900-01）
    # ========================================
    # 定位：加值層（fail-soft）。不可用時主流程與現行版本完全一致，
    # 只有逐字稿少了發言者標籤，不得讓任何任務失敗。
    ENABLE_DIARIZATION: bool = Field(
        default=True,
        description="是否啟用逐字稿發言者自動分群（說話者分離）；停用或失敗時逐字稿維持純文字"
    )
    DIARIZATION_MODEL_DIR: str = Field(
        default="models/diarization",
        description="diarization 模型目錄（Docker 內為 /app/models/diarization；由 scripts/download_diarization_models.py 預載）"
    )
    DIARIZATION_THRESHOLD: float = Field(
        default=0.6,
        description="聚類相似度門檻（僅 num_clusters=-1 時生效）：數值越高越傾向合併為同一發言者；45 分鐘真實會議實測會嚴重碎裂，不建議單獨使用"
    )
    DIARIZATION_NUM_CLUSTERS: int = Field(
        default=8,
        description="固定發言者數（預設 8）；-1=依 threshold 自動分群。實測（45 分鐘科務會議）k=8 得 8 群、0 個 <5 秒碎群、覆蓋率 86.8%；threshold 自動路線得 51~120 群不可用"
    )
    DIARIZATION_MIN_DURATION_ON: float = Field(
        default=0.3,
        description="最短有效發言長度（秒）；低於此長度的區段被併入鄰近發言"
    )
    DIARIZATION_MIN_DURATION_OFF: float = Field(
        default=0.5,
        description="切分發言所需的最短停頓（秒）；越大越傾向把短停頓視為同一段發言"
    )
    DIARIZATION_MERGE_GAP_SECONDS: float = Field(
        default=1.5,
        description="標註逐字稿時，同一發言者相鄰發言合併的時間間隔上限（秒）"
    )
    DIARIZATION_TIMEOUT_SECONDS: float = Field(
        default=900.0,
        description="diarization 整體逾時（秒）；超過即回退無標籤流程（45 分鐘音檔實測約 150 秒）"
    )
    DIARIZATION_MIN_SEGMENT_COVERAGE: float = Field(
        default=0.6,
        description="ASR 片段與單一發言者重疊比例低於此值時，依時間比例拆分該片段（處理一句話內換人說的狀況）"
    )
    
    # ========================================
    # 系統設定
    # ========================================
    LOG_LEVEL: str = Field(default="INFO", description="日誌等級")
    DATA_DIR: str = Field(default="/app/data", description="資料目錄")
    # RC-5 runtime provenance：E2E/local launcher 注入 git rev-parse HEAD。
    # 未設定時 /api/health 的 build_revision 為 null；一般 startup/health
    # 不因 unknown revision 失敗，revision gate 只由 E2E harness 判定。
    MEETINGSCRIBE_BUILD_REVISION: Optional[str] = Field(
        default=None,
        description="執行期 build revision（/api/health build_revision 來源）；local/E2E launcher 注入 git rev-parse HEAD，未設定時為 null"
    )
    # RC-5 actual port logging：startup log 與 uvicorn 實際 --port 必須同一來源；
    # scripts/macos 以 MEETINGSCRIBE_PORT 傳入 uvicorn，故同時接受兩個名稱。
    SERVICE_PORT: int = Field(
        default=9527,
        validation_alias=AliasChoices("SERVICE_PORT", "MEETINGSCRIBE_PORT"),
        description="API 服務監聽端口；啟動 log 與 uvicorn --port 應使用同一來源（scripts 以 MEETINGSCRIBE_PORT 傳入）"
    )
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
    
    # ---- 雲端 LLM provider 解析（單一來源；呼叫端不得直接讀 GEMINI_*）----
    @property
    def cloud_llm_is_ollama(self) -> bool:
        return self.CLOUD_LLM_PROVIDER.strip().lower().replace("-", "_") != "gemini"

    @property
    def cloud_llm_provider_id(self) -> str:
        return "ollama_cloud" if self.cloud_llm_is_ollama else "gemini"

    @property
    def cloud_llm_provider_label(self) -> str:
        return "Ollama Cloud" if self.cloud_llm_is_ollama else "Gemini"

    @property
    def cloud_llm_api_key_env_name(self) -> str:
        return "OLLAMA_API_KEY" if self.cloud_llm_is_ollama else "GEMINI_API_KEY"

    @property
    def cloud_llm_base_url(self) -> str:
        return self.OLLAMA_CLOUD_BASE_URL if self.cloud_llm_is_ollama else self.GEMINI_BASE_URL

    @property
    def cloud_llm_model(self) -> str:
        return self.OLLAMA_CLOUD_MODEL if self.cloud_llm_is_ollama else self.GEMINI_MODEL

    @property
    def cloud_llm_api_key(self) -> Optional[str]:
        return self.OLLAMA_API_KEY if self.cloud_llm_is_ollama else self.GEMINI_API_KEY

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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 全域設定實例
settings = Settings()
