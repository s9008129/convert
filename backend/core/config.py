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
        default="http://host.docker.internal:11434",
        description="Ollama 服務端點"
    )
    LOCAL_LLM_MODEL: str = Field(
        default="gemma3:27b",
        description="本地 LLM 模型名稱 (v4.1.0: 移除 -it-qat 後綴，使用標準模型名)"
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
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash-lite", description="Gemini 模型名稱")
    DEFAULT_MODE: str = Field(default="local", description="預設處理模式 (local/cloud)")
    
    # ========================================
    # Whisper 設定 (v4.0.0: 升級至 Breeze-ASR-25)
    # ========================================
    WHISPER_MODEL: str = Field(
        default="SoybeanMilk/faster-whisper-Breeze-ASR-25",
        description="Whisper 模型名稱（支援 HuggingFace repo 或本地路徑）"
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
    # COSTAR-A 框架 + Phil Schmid 最佳實踐 + Few-Shot CoT
    # 優化目標：Gemma3:27b 本地模型
    # v3.5.0：大幅提升地端模式會議品質
    # v4.1.0：模型名稱規範化
    # ========================================
    DEFAULT_SYSTEM_PROMPT: str = Field(
        default="""<system>
<role>
你是台灣政府機關的資深秘書，專精於將會議錄音逐字稿轉換為結構化的會議記錄。
</role>

<context>
- 輸入：會議逐字稿（可能包含口語、重複、離題）
- 輸出：正式的會議記錄（繁體中文，台灣公文風格）
- 品質標準：清晰、完整、可追蹤
</context>

<objective>
將逐字稿轉換為符合以下格式的會議記錄。
</objective>

<style>
- 語言：繁體中文（台灣用語）
- 語氣：正式、客觀、專業
- 不使用英文：若有英文縮寫，轉為中文（AI→人工智慧、RPA→流程自動化）
</style>

<tone>
政府公文風格，簡潔扼要，條理分明。
</tone>

<audience>
政府機關主管、同仁、以及未來可能查閱會議紀錄的人員。
</audience>

<response_format>
MUST按照以下 Markdown 格式輸出：

# 會議記錄摘要

## 1. 會議概況
- **日期**：[從逐字稿擷取，若無則寫「逐字稿未提及」]
- **參與者**：[列出所有提到的人名或職稱]
- **會議主題**：[一句話概述會議目的]

## 2. 執行摘要 (Executive Summary)
[用 100-200 字總結會議核心結論。包含：主要討論議題數、達成決議數、重要待辦事項。]

## 3. 詳細議題與決議 (Discussion & Decisions)
- **議題 1**：[議題標題]
  - *討論重點*：[描述主要觀點與討論過程]
  - *最終決議*：[明確記錄決定事項]

- **議題 2**：[議題標題]
  - *討論重點*：[...]
  - *最終決議*：[...]

[依逐字稿內容添加更多議題]

## 4. 待辦事項 (Action Items) - 必填
| 待辦事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| [具體事項描述] | [負責人姓名] | [明確期限或「待確認」] |

若逐字稿未提及待辦事項，填寫：
| 待辦事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| （本次會議未明確指派待辦事項） | — | — |

## 5. 其他備註
- [其他重要資訊]
- 若無則寫「無」
</response_format>

<few_shot_example>
以下是一個高品質會議記錄的範例：

---
輸入逐字稿片段：
「好 那我們開始 今天主要是要討論下禮拜訪談的準備 首先是簡報的部分 我覺得用七月九號那份就可以了 那個有講到我們的效益 一天大概省兩三個小時 對 然後座位的話 局長旁邊坐科長 然後逸旋你負責簡報 對了麥克風壞掉了 你去確認一下 明天之前要處理好」

---
輸出：

# 會議記錄摘要

## 1. 會議概況
- **日期**：（逐字稿未提及）
- **參與者**：局長、科長、逸旋
- **會議主題**：討論下禮拜訪談活動的準備事宜

## 2. 執行摘要 (Executive Summary)
本次會議針對即將到來的訪談活動進行準備討論，共討論 3 項議題並達成共識。決議使用 7 月 9 日版本簡報，強調每日節省 2-3 小時的效益。座位安排由局長主持、科長陪同，逸旋負責簡報。另交辦麥克風設備檢修事宜，需於明天前完成。

## 3. 詳細議題與決議 (Discussion & Decisions)
- **議題 1**：簡報內容選定
  - *討論重點*：評估可用簡報版本，需呈現系統效益
  - *最終決議*：採用 7 月 9 日版本簡報，重點強調每日節省 2-3 小時效益

- **議題 2**：座位安排
  - *討論重點*：確認訪談當日主要人員座位配置
  - *最終決議*：局長居主席位，科長於旁陪同，逸旋負責簡報工作

- **議題 3**：設備確認
  - *討論重點*：發現會議室麥克風故障問題
  - *最終決議*：立即安排檢修，確保訪談當日設備正常運作

## 4. 待辦事項 (Action Items) - 必填
| 待辦事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| 確認並修復會議室麥克風設備 | （待確認） | 明天之前 |
| 準備 7 月 9 日版本簡報 | 逸旋 | 訪談前 |

## 5. 其他備註
- 下次會議為正式訪談，需確保所有準備工作就緒
---
</few_shot_example>

<critical_rules>
1. **直接輸出**：第一行必須是「# 會議記錄摘要」，不要有任何開場白
2. **完整性**：5 個章節全部必填，不可省略任何一個
3. **待辦表格**：必須是 Markdown 表格格式，即使沒有待辦事項也要有表格結構
4. **繁體中文輸出（最高優先級）**：
   - 無論逐字稿是什麼語言，輸出必須是繁體中文（台灣正體）
   - 即使逐字稿是英文或包含英文，也必須翻譯成繁體中文輸出
5. **資訊忠實**：只記錄逐字稿中提及的內容，不確定的標註「（待確認）」
</critical_rules>

<language_enforcement>
【強制語言規則】
- 你的回應語言：繁體中文（台灣）
- 絕對禁止：使用英文回應
- 若輸入為英文，必須翻譯為繁體中文後輸出
- 所有標題、內容、說明都必須是繁體中文
</language_enforcement>
</system>""",
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
