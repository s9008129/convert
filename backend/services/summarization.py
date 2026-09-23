"""
LLM 摘要服務
支援本地模式（Ollama/LM Studio）和雲端模式（Ollama Cloud／Gemini API）

v3.5.0 改進：
- 支援平台自動偵測和配置（macOS 使用 LM Studio，Windows 使用 Ollama）
- 實現 Ollama 模型 VRAM 釋放機制（keep_alive=0）
- 優化本地模型摘要品質：改善參數和提示詞策略
"""

import asyncio
import json
import os
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx
from openai import OpenAI, AsyncOpenAI, APIConnectionError, APITimeoutError

from backend.core.config import settings
from backend.core.errors import (
    LMSTUDIO_MODEL_NOT_LOADED,
    LMSTUDIO_MULTIPLE_LOADED_LLMS,
    LMSTUDIO_NO_FINAL_CONTENT,
    LMSTUDIO_NO_LOADED_LLM,
    LMSTUDIO_UNREACHABLE,
    LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED,
    LOCAL_LLM_MERGE_NOT_CONVERGED,
    StableServiceError,
    describe_exception,
)
from backend.core.logger import log
from backend.core.platform_config import (
    get_lmstudio_openai_base_url,
    normalize_lmstudio_base_url,
    resolve_local_llm_provider,
)
from backend.core.templates import MeetingTemplate, get_template
from backend.models.schemas import ProcessingMode


class OllamaStreamRetryable(RuntimeError):
    """串流層可重試失敗（v4.7.0）。

    情況（皆源自參考專案 D:\\dev\\local 的量產經驗）：
    1. 串流中途收到 {"error": ...} chunk（模型卸載／runner 崩潰）
    2. 串流結束卻沒有 done:true（連線中斷）
    3. done_reason 非 stop 且非 length 的其他異常結束原因

    注意：done_reason=length（撞到 num_predict 上限被截斷）不屬於可重試情境——
    這是確定性結果，重試必然得到同樣的截斷點，v4.7.1 起改為在呼叫端接受內容
    並記錄警告（見 _stream_ollama_chat_once 結尾與 _post_ollama_chat）。
    """


@dataclass
class LocalContextPlan:
    """本地摘要流程的上下文規劃結果。"""

    context_window_tokens: int
    estimated_transcript_tokens: int
    chunk_input_budget_tokens: int
    # T20260827-1127-01 RC-1：merge 預算語意分離——「來源分組上限」「合併後
    # 可見目標」「provider completion cap」是三個不同契約，不得共用單一欄位
    # （舊 notes_merge_budget_tokens 同時承擔三種語意，使 hidden reasoning
    # 吃光 provider completion 預算後無法產出 final content）。
    merge_input_budget_tokens: int
    merge_visible_target_tokens: int
    merge_provider_output_tokens: int
    needs_chunking: bool
    estimated_chunk_count: int
    # T20260922-1349-01 RC-1b：整併結果「硬性」下游可承接上限（最終生成階段
    # 輸入預算）。`merge_visible_target_tokens` 是壓縮的軟性目標，本欄位是
    # 「單一 note 已無法再分組壓縮時，是否仍可安全交給最終生成」的判斷依據。
    # 預設 None＝退回 merge_visible_target_tokens（維持既有呼叫端語意）。
    merge_feasible_input_tokens: Optional[int] = None


@dataclass(frozen=True)
class LMStudioModelSelection:
    """一次摘要工作固定使用的 LM Studio loaded instance 選擇。"""

    provider: str
    model_identifier: str
    loaded_instance_id: str
    context_length: Optional[int]
    inventory_timestamp: datetime


@dataclass(frozen=True)
class _LoadedLMStudioInstance:
    model_key: str
    instance_id: str
    context_length: Optional[int]


class SummarizationService:
    """
    LLM 摘要生成服務
    支援本地模式（Ollama/LM Studio）和雲端模式（Ollama Cloud／Gemini API）
    """

    # 雲端生成階段的發言來源標註規則（2026-09-14 使用者需求）。
    # 背景（實測根因）：逐字稿帶「發言者N」標籤、萃取筆記也保留標籤，但生成
    # 階段原本只被要求「發言者N 不是姓名、不得當人名寫入」，沒有任何一處要求
    # 保留發言歸屬——Gemini 因此把來源資訊整段省略（實測 0 處；Ollama 只是
    # 沒完全遵守規則才殘留 5~10 處，屬不穩定行為）。
    # 改為「不得當人名使用，但必須以固定格式保留為回溯依據」；
    # A/B 實測：模糊版要求 0/2 生效、本版 2/2 生效（每次 15~19 個來源標註）。
    # 僅套用於雲端生成；地端生成流程維持原樣（使用者指示：地端不動）。
    CLOUD_SPEAKER_TRACEABILITY_RULE = (
        "- 發言來源標註（強制）：正文的每一項指示、裁示、交辦與他人意見／建議，"
        "句末必須加註來源，格式固定為「（發言者N，00:12:04）」，N 與時間照逐字稿填寫；"
        "若該處能由內容確定身分（如科長、股別、單位或姓名），則寫成「（科長，00:12:04）」。"
        "發言者N 只是回溯依據、不是姓名，不得當人名使用，"
        "也不得為版面簡潔而整體省略發言來源標註；"
        "除句末來源標註外，不得在開頭欄位（時間、地點、主持人、出席人員）"
        "與彙整表內出現「發言者N」。"
    )

    # 地端專用的來源標註位置導引（W2；T20260922-1930-01）。
    # 背景（實測根因）：地端模型把「（發言者N，HH:MM:SS）」寫進四欄的
    # 「決議事項辦理情形彙整表」列內，違反 section_meeting 模板契約，且會原樣
    # 流入列管資料附件（基線 13/13 列都帶標註）；既有提示詞只說「不得在彙整表
    # 內出現發言者N」，少了「標註只能寫在正文句末」的位置規範與正例。
    # 僅在 mode="local" 時注入；雲端呼叫端不傳 mode ⇒ 雲端提示詞 byte 級不變。
    LOCAL_SOURCE_TAG_PLACEMENT_RULE = (
        "- 來源標註位置（強制）：時間戳來源標註「（發言者1，00:05:12）」只能寫在正文句末，"
        "如「各股配合辦理（發言者1，00:05:12）。」\n"
        "- 四欄的「決議事項辦理情形彙整表」內不得出現任何來源標註；表格列只寫案由、"
        "承辦單位與辦理情形（列內出現「發言者1」或時間戳即為格式錯誤）"
    )

    # 來源標註偵測樣式：句末「（…HH:MM(:SS)…）」形式，供確定性檢查使用；
    # 同時涵蓋「（發言者1，00:00:00）」與「（科長，00:00:00）」兩種寫法。
    # 補強訊息列出具體遺漏待辦時的最大顯示數量（避免提示詞被長清單淹沒）
    ACTION_ISSUE_PREVIEW_LIMIT = 12

    # P3 波（R23）：待辦召回比對門檻——「滑窗最長共同子序列（LCS）比例」。
    # 以 0903 場 27B 真實輸出校準：**確實已涵蓋**的待辦（含被舊版「整條連續子字串」
    # 比對誤判為遺漏的假陽性）落點 0.69–1.00；逐字稿裡**真的沒寫**的對照句落點
    # 0.27–0.42。取 0.6 為門檻，兩側都留有餘裕；調高會回到假陽性（補強白燒），
    # 調低會讓真遺漏不再觸發補強（false negative，比白燒更糟）。
    ACTION_MATCH_MIN_LCS_RATIO = 0.6

    # P3 波（R2 守衛）：LCS 近似比對會把「改寫」與「失真」混為一談的兩個盲區。
    # 兩條守衛都是確定性、無 LLM，且方向一律**往更嚴**（寧可多補強一輪，
    # 不可把失真當成已涵蓋）：
    # ①否定詞——否定是語意反轉，字面重疊度卻很高（實測「嚴禁…外流」對照句
    #   LCS 0.917 會被誤判已涵蓋）。標籤內的否定詞若沒出現在紀錄中，一律判遺漏。
    # ②數字——金額／數量／日期是紀錄最不能錯、也最容易被改寫稀釋的資訊
    #   （實測 0.818；真實缺口例：800×17＝13600 元的算式被寫成「約一萬多元」）。
    #   標籤內 **≥2 位**數字串必須原樣出現（正規化已折疊全形/半形與千分位逗號，
    #   兩側對稱）。為什麼從 3 位放寬到 2 位：獨立審查 attempt-07 的 R2 反例——
    #   「9月30日」被改寫成「9月20日」時，數字串 `30`（2 位）是唯一可辨識的差異，
    #   LCS 0.9333 會被洗白成「已涵蓋」。方向一律往更嚴（寧可多一輪補強）。
    ACTION_NEGATION_TERMS = ("嚴禁", "禁止", "不得", "勿", "避免", "不可")
    _ACTION_NUMBER_PATTERN = re.compile(r"\d{2,}")

    _SOURCE_TAG_PATTERN = re.compile(r"（[^）]{0,24}?\d{1,2}:\d{2}(?::\d{2})?[^）]{0,12}?）")
    _RECORD_HEADER_FIELD_PATTERN = re.compile(r"^(?:時間|地點|主持人|出席人員|紀錄)[:：]")

    # P4 波（T20260922-2037-02 §9.3）：逐條對帳（覆蓋率）由「只查待辦」擴為
    # 議題／決議／數字／日期＋既有待辦。設計要點（實測校準）：
    # ①議題／決議取萃取筆記「議題與決議」區塊條列（逐字稿關鍵詞法已被否證：
    #   真實逐字稿「決議／裁示／結論」出現 0 次）；②數字／日期取逐字稿段落列、
    #   單位錨定；③比對重用既有比對器（對稱正規化＋滑窗 LCS 0.6＋否定詞／數字守衛）；
    # ④數字比對前必須先剝來源標註（`_SOURCE_TAG_PATTERN`）＋NFKC＋去千分位逗號，
    #   否則「（科長，00:17:52）」的「17」會把逐字稿真數字洗成已涵蓋（實測）；
    # ⑤日期等價展開（`11月1日 ≡ 11/1`、`下週一 ≡ 下個禮拜一`）；⑥空期望集合一律
    #   log.warning＋cov_* 指標（不得靜默 no-op）。
    RECORD_COVERAGE_MIN_ITEM_CHARS = 6
    # fallback 值；實際預覽上限讀 settings.LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT
    RECORD_COVERAGE_ITEM_PREVIEW_LIMIT = ACTION_ISSUE_PREVIEW_LIMIT
    # 「數字緊鄰單位」錨定（單位白名單；含千分位寫法如 13,600）
    _RECORD_COVERAGE_NUMBER_UNIT_PATTERN = re.compile(
        r"(\d{1,3}(?:,\d{3})+|\d{2,6})\s*(?:元|塊|萬元|個人|人|％|%|個|孔|樓)"
    )
    _RECORD_COVERAGE_ANY_NUMBER_PATTERN = re.compile(r"\d{1,3}(?:,\d{3})+|\d{2,6}")
    _RECORD_COVERAGE_DATE_MD_PATTERN = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})(?:\s*[日號号])?")
    _RECORD_COVERAGE_DATE_END_PATTERN = re.compile(r"(\d{1,2})\s*月\s*底")
    _RECORD_COVERAGE_DATE_SLASH_PATTERN = re.compile(r"(?<![\d/])(\d{1,2})\s*/\s*(\d{1,2})(?![\d/])")
    _RECORD_COVERAGE_WEEKDAY_PATTERN = re.compile(r"下\s*(?:個)?\s*(?:週|周|星期|禮拜)\s*([一二三四五六日天])")
    _RECORD_COVERAGE_SENTENCE_SPLIT_PATTERN = re.compile(r"[。！？!?；;]")
    # 筆記佔位語（空骨架 `_empty_extraction_notes` 就是「逐字稿未提及／（待確認）」；
    # 佔位若未濾除會產生假期望集合）
    _RECORD_COVERAGE_PLACEHOLDER_TERMS = ("逐字稿未提及", "（待確認）", "未於本段確認", "未明確")
    _RECORD_COVERAGE_NUMBER_ALL_ZERO_PATTERN = re.compile(r"^0+$")

    # P4-C（§9.5／W-1）：Ollama 取樣參數與 LM Studio 同源——實際值讀 settings
    # （LOCAL_LLM_SAMPLING_TOP_P／TOP_K／LOCAL_LLM_SAMPLING_REPEAT_PENALTY，
    # None＝不送、沿用端點預設）。下列常數只是**一行 rollback 路徑**：本波前
    # Ollama 寫死 top_p=0.95／top_k=64／repeat_penalty=1.08，要回退舊行為時把
    # `_ollama_sampling_options()` 改成 `return dict(self.LEGACY_OLLAMA_SAMPLING_OPTIONS)`。
    LEGACY_OLLAMA_SAMPLING_OPTIONS = {"top_p": 0.95, "top_k": 64, "repeat_penalty": 1.08}

    # 日期依據規則（2026-09-14）：實測 Gemini 會把逐字稿的「今年」自行換算成民國年份
    # ——逐字稿全篇沒有任何年份，正式紀錄卻寫「中華民國113年…」「生效日期為113年11月1日」，
    # 這是最後一道防線守不到、卻會直接印成公文的事實錯誤。年份是逐字稿唯一無法事後查證、
    # 又最容易由「今年／明年／去年」推算出來的欄位，因此以提示詞（本常數）＋確定性絆索
    # （_validate_cloud_date_grounding）雙重把關；月份與日期同受提示詞約束，但不做硬攔，
    # 以免把逐字稿有寫的合法月日表達誤判。僅套用於雲端生成；地端生成流程維持原樣。
    CLOUD_DATE_GROUNDING_RULE = (
        "- 日期與年份依據（強制）：紀錄中的年份（如「113年」「2026年」）必須是逐字稿"
        "真的出現過的內容，直接照抄；逐字稿只用「今年／明年／去年／今年度」等相對說法、"
        "或完全沒提到年份時，年份一律寫「（待確認）」，不得自行推算或填入。"
        "月份與日期同理：逐字稿沒提到就寫「（待確認）」，不得臆測"
        "（例：逐字稿說「今年的 11 月 1 號」→ 年份寫「（待確認）」，月日寫「11月1日」）。"
        "查不到的日期、月份、次別等開頭欄位，一律保留系統預設的「（待確認）」字樣，"
        "不得改寫成「（年）」「（月）」「（日）」這類沒有資訊的空括號佔位。"
    )

    # v4.8.0：這兩條規則原本只套用在雲端生成。2026-09-22 三方比對顯示，雲端紀錄與
    # 地端紀錄差距最大的維度正是「可回溯性」與「年份依據」——出處標註 25 處 vs
    # 地端 0 處（100% 缺口），且逐字稿只有「今年」時雲端寫「（待確認）」、地端曾寫死
    # 年份。因此改為地端與雲端共用的紀錄契約；CLOUD_* 舊名保留為別名（既有呼叫端
    # 與文件引用不得改動）。
    RECORD_SPEAKER_TRACEABILITY_RULE = CLOUD_SPEAKER_TRACEABILITY_RULE
    RECORD_DATE_GROUNDING_RULE = CLOUD_DATE_GROUNDING_RULE

    # 年份偵測樣式（供日期依據絆索使用）：阿拉伯數字（113年／2026年度）與國字
    # （一一三年／一百一十三年度）兩種寫法；「年代」（如 90 年代）不算年份，故排除。
    _ARABIC_YEAR_PATTERN = re.compile(r"(?<!\d)(\d{2,4})\s*年(?!代)")
    _CHINESE_YEAR_PATTERN = re.compile(r"([〇○零一二三四五六七八九十百兩]{2,4})\s*年(?!代)")
    _CHINESE_DIGITS = {
        "〇": 0, "○": 0, "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    }

    LOCAL_EXTRACTION_PROMPT = """你是會議逐字稿資訊萃取助理。你的任務只有一個：盡量完整抽取事實，不要直接寫成最終會議記錄。

請直接輸出以下 Markdown：

# 萃取筆記

## 1. 會議資訊
- **日期**：...
- **參與者**：...
- **會議主題**：...

## 2. 議題與決議
- **議題**：...
  - *討論重點*：...
  - *決議*：...

## 3. 待辦清單
| 待辦事項 | 負責人 | 期限 | 依據 |
| :--- | :--- | :--- | :--- |
| ... | ... | ... | ... |

若這一段沒有明確交辦，仍要輸出表格並填入：
| （未於本段確認） | — | — | — |

## 4. 待確認資訊
- ...

規則：
- 寧可多保留明確資訊，也不要漏掉交辦、期限、數字或責任人。
- 待辦清單要盡量拆細；設備、人力、場勘、新聞稿、餐盒、飲料、拍照流程等可獨立追蹤的工作請分列，不要合併成籠統大項。
- 專有名詞、產品名、英文縮寫若影響準確性可保留。
- 不要加入逐字稿未提及的內容，不要輸出前言。
- 只輸出繁體中文 Markdown，不要輸出 <think>、<thought>、<details>、XML/HTML 標籤或 code fence。"""

    # v4.3.3：雲端萃取在本地規則之上追加「豐富度」規則。
    # 根因：雲端模型對長輸入有強烈壓縮傾向，單句帶過實質討論；
    # 本地提示詞聚焦待辦完整性即可（豐富度由分塊結構保證），
    # 雲端則必須明文要求保留立場、理由、數據與案例。
    CLOUD_EXTRACTION_PROMPT = LOCAL_EXTRACTION_PROMPT + """

雲端豐富度補充規則（同樣具強制力）：
- 「議題與決議」每一議題除決議外，必須記錄：各發言者／單位的立場與理由、提出的數據、舉的實例、爭點、以及最後如何收斂。
- 發言中出現的統一口徑、應對策略、疑慮與反對意見都是重要事實，必須完整保留，不同立場並列記錄。
- 筆記長度沒有上限：寧可過度詳細，嚴禁把多句實質討論壓縮成一句籠統敘述。"""

    LOCAL_NOTES_MERGE_PROMPT = """你要合併多份「萃取筆記」，產出一份資訊最完整、去除重複的整合版筆記。

規則：
- 保留所有明確議題、決議、待辦、數字、日期、責任人。
- 同一待辦若重複出現可合併，但不同工作項目不可硬併成一列。
- 若資訊互相矛盾，請保留在「待確認資訊」。
- 仍然使用原本的「# 萃取筆記」Markdown 結構輸出。
- 不要寫成最終會議記錄。
- 只輸出繁體中文 Markdown，不要輸出 <think>、<thought>、<details>、XML/HTML 標籤或 code fence。"""

    # T20260827-1127-01 RC-1：合併後 notes 的可見收斂目標（final-stage fit）。
    # 這是「orchestration 可見輸出」契約，與 provider completion cap 是不同
    # 預算；超出可見目標的回應交由下一輪 compaction 處理，不得壓縮 provider
    # max_tokens，也不得用字串截斷修正。
    #
    # T20260922-1349-01 RC-1b：900 由「固定值」降為「歷史下限」。固定 900 是在
    # num_ctx=8192 假設下校準的常數；當 provider 實際視窗遠大於設定值（LM
    # Studio loaded instance 實測 32K/128K）時，900 變成與真實預算無關的硬性
    # gate：整併一旦收斂到單一 note，就再無分組可依賴（merge prompt 要求保留
    # 全部事實，模型不保證縮小），必然在輪數上限拋
    # LOCAL_LLM_MERGE_NOT_CONVERGED，整份會議紀錄被 veto 成逐字稿 fallback。
    # 正確語意：可見目標由「最終生成階段可承接的輸入預算」推導（見
    # `_build_local_context_plan` / `_resolve_merge_targets`），900 僅為下限，
    # `LOCAL_LLM_MERGE_VISIBLE_TARGET_CEILING_TOKENS` 為維持最終生成聚焦的品質
    # 上限。
    LOCAL_LLM_MERGE_VISIBLE_TARGET_TOKENS = 900
    LOCAL_LLM_MERGE_VISIBLE_TARGET_CEILING_TOKENS = 4096

    # T20260827-1127-01 RC-4：chunk 邊界重疊的 token 上限，同時供 context
    # planner 的 effective step 估算與 chunk assembler 的 carry 封頂使用，
    # 消除「planner 假設 220、assembler 放行半個 chunk」的模型錯位
    # （19 chunks vs 粗估 12 的呼叫放大）。
    LOCAL_LLM_CHUNK_OVERLAP_BUDGET_TOKENS = 220

    def __init__(self):
        """準備各種 LLM 客戶端與健康檢查快取，減少重複連線成本。"""
        self._ollama_client: Optional[httpx.AsyncClient] = None
        # T20260827-1127-01 CHANGE_MAP 4：有界呼叫的 structured metrics
        #（pipeline 起始重置；local pipeline 為循序執行，無併發競態）
        self._lmstudio_logical_generations = 0
        self._lmstudio_semantic_attempts = 0
        self._lmstudio_network_retries = 0
        self._merge_rounds_used = 0
        self._merge_groups_last_round = 0
        self._lmstudio_client: Optional[AsyncOpenAI] = None
        self._lmstudio_client_base_url: Optional[str] = None
        self._lmstudio_http_client: Optional[httpx.AsyncClient] = None
        self._lmstudio_http_base_url: Optional[str] = None
        self._gemini_client: Optional[OpenAI] = None
        self._gemini_async_client: Optional[AsyncOpenAI] = None

        # 分層智能檢查快取（減少API調用成本）
        self._gemini_health_check_cache = {
            "last_check_time": None,
            "status": None,
            "ttl_seconds": 86400  # 24 小時快取
        }

        # v4.1.0: 模型解析結果與錯誤暫存
        self._resolved_model: Optional[str] = None
        self._ollama_model_error: Optional[str] = None

        # v4.7.0: warmup 自我修復失敗時的本任務降級 num_ctx
        # （None＝使用 settings 預設；每次 warmup 開頭重設，防跨任務殘留）
        self._active_context_tokens: Optional[int] = None
        self._active_lmstudio_selection: Optional[LMStudioModelSelection] = None
        self._lmstudio_health: dict = {
            "provider": "auto",
            "server_reachable": False,
            "selection_status": "not_checked",
            "loaded_llm_count": 0,
            "selected_model": None,
            "context_length": None,
        }

    async def _get_ollama_client(self) -> httpx.AsyncClient:
        """取得 Ollama HTTP 客戶端"""
        if not self._ollama_client:
            self._ollama_client = httpx.AsyncClient(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=settings.LOCAL_LLM_REQUEST_TIMEOUT
            )
        return self._ollama_client

    def _get_lmstudio_root_url(self) -> str:
        """取得 normalized LM Studio root；不把 OpenAI `/v1` 當 native API root。"""
        return normalize_lmstudio_base_url(settings.LMSTUDIO_BASE_URL)

    def _get_lmstudio_api_key(self) -> str:
        return str(os.getenv("LM_API_TOKEN") or "lm-studio")

    def _get_lmstudio_model_override(self) -> Optional[str]:
        """只讀取 explicit override；不以任何固定模型名稱作 fallback。"""
        if settings.LMSTUDIO_MODEL is None:
            return None
        normalized = settings.LMSTUDIO_MODEL.strip()
        return normalized or None

    def _set_lmstudio_health(
        self,
        *,
        server_reachable: bool,
        selection_status: str,
        loaded_instances: list[_LoadedLMStudioInstance],
        selected: Optional[LMStudioModelSelection] = None,
    ) -> None:
        self._lmstudio_health = {
            "provider": resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER),
            "server_reachable": server_reachable,
            "selection_status": selection_status,
            "loaded_llm_count": len(loaded_instances),
            "selected_model": selected.model_identifier if selected else None,
            "context_length": selected.context_length if selected else None,
        }

    async def _get_lmstudio_http_client(self) -> httpx.AsyncClient:
        """取得查詢 native `/api/v1/models` 的 async client。"""
        base_url = self._get_lmstudio_root_url()
        if self._lmstudio_http_client is None or self._lmstudio_http_base_url != base_url:
            if self._lmstudio_http_client is not None:
                await self._lmstudio_http_client.aclose()
            self._lmstudio_http_client = httpx.AsyncClient(
                base_url=base_url,
                headers={"Authorization": f"Bearer {self._get_lmstudio_api_key()}"},
                # Inventory is a health/readiness probe, not a generation
                # request; keep a dead server from blocking health for 30m.
                timeout=max(1.0, min(float(settings.LOCAL_LLM_REQUEST_TIMEOUT), 10.0)),
            )
            self._lmstudio_http_base_url = base_url
        return self._lmstudio_http_client

    def _get_lmstudio_client(self) -> AsyncOpenAI:
        """取得 LM Studio OpenAI-compatible async client。"""
        base_url = get_lmstudio_openai_base_url(self._get_lmstudio_root_url())
        if self._lmstudio_client is None or self._lmstudio_client_base_url != base_url:
            self._lmstudio_client = AsyncOpenAI(
                base_url=base_url,
                api_key=self._get_lmstudio_api_key(),
                timeout=settings.LOCAL_LLM_REQUEST_TIMEOUT,
                max_retries=0,
            )
            self._lmstudio_client_base_url = base_url
            log.info("LM Studio async 客戶端初始化完成 (base_url={})", base_url)
        return self._lmstudio_client

    def _get_gemini_api_key(self) -> str:
        """安全地取得目前雲端 provider 的 API Key。

        方法名保留為向後相容 alias（v4.7.1 起雲端 provider 可為 Ollama Cloud
        或 Gemini）；實際來源一律由 settings.cloud_llm_* 決定。
        """
        api_key = settings.cloud_llm_api_key
        if not api_key:
            raise ValueError(
                f"未設定 {settings.cloud_llm_api_key_env_name} 環境變數"
                f"（雲端 provider={settings.cloud_llm_provider_label}）"
            )
        return api_key

    def _get_gemini_client(self) -> OpenAI:
        """取得雲端 LLM 客戶端（OpenAI 相容介面；provider 由 settings 決定）"""
        if not self._gemini_client:
            api_key = self._get_gemini_api_key()
            self._gemini_client = OpenAI(
                api_key=api_key,
                base_url=settings.cloud_llm_base_url,
                timeout=settings.CLOUD_LLM_REQUEST_TIMEOUT,
                max_retries=settings.CLOUD_LLM_MAX_RETRIES,
            )
        return self._gemini_client

    def _get_gemini_async_client(self) -> AsyncOpenAI:
        """取得雲端 LLM 異步客戶端（OpenAI 相容介面；provider 由 settings 決定）"""
        if not self._gemini_async_client:
            api_key = self._get_gemini_api_key()
            self._gemini_async_client = AsyncOpenAI(
                api_key=api_key,
                base_url=settings.cloud_llm_base_url,
                timeout=settings.CLOUD_LLM_REQUEST_TIMEOUT,
                max_retries=settings.CLOUD_LLM_MAX_RETRIES,
            )
        return self._gemini_async_client

    async def summarize(
        self,
        transcript: str,
        mode: ProcessingMode = ProcessingMode.LOCAL,
        user_prompt: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        template_id: str = "general",
    ) -> str:
        """
        生成會議摘要

        Args:
            transcript: 逐字稿文字
            mode: 處理模式（local/cloud）
            user_prompt: 已淘汰（保留以相容舊版本，但無作用）
            progress_callback: 進度回調函數
            template_id: 會議模板 id（v4.4.0；預設 general 與舊行為一致）

        Returns:
            會議摘要（Markdown 格式）
        """
        transcript = transcript.strip()
        if not transcript:
            raise ValueError("逐字稿為空")

        self._emit_progress(progress_callback, 65.0, "生成摘要中...")

        # v4.4.0：格式由會議模板驅動（general＝原系統預設格式）
        template = get_template(template_id)
        system_prompt = template.resolve_system_prompt()
        log.info(f"使用會議模板生成會議記錄: {template.id}（{template.display_name}）")

        if user_prompt:
            log.info("偵測到 user_prompt；摘要結構仍以系統格式為主，額外偏好將僅隨結果一併保存")

        try:
            if mode == ProcessingMode.CLOUD:
                summary = await self._summarize_with_gemini(system_prompt, transcript, progress_callback, template=template)
            else:
                summary = await self._summarize_with_local_pipeline(transcript, system_prompt, progress_callback, template=template)

            self._emit_progress(progress_callback, 95.0, "摘要生成完成")

            return summary

        except Exception as e:
            log.exception(f"摘要生成失敗: {describe_exception(e)}")
            raise

    @staticmethod
    def _emit_progress(
        progress_callback: Optional[callable],
        progress: float,
        message: str
    ) -> None:
        """安全地回報進度。"""
        if progress_callback:
            progress_callback(progress, message)

    def _estimate_tokens(self, text: str) -> int:
        """以保守方式估算中英混合文字的 token 數。"""
        if not text:
            return 0

        latin_pattern = re.compile(r"[A-Za-z0-9_]+(?:[-/:.][A-Za-z0-9_]+)*")
        latin_matches = list(latin_pattern.finditer(text))
        latin_words = len(latin_matches)
        latin_chars = sum(len(match.group(0)) for match in latin_matches)
        cjk_chars = len(re.findall(r"[\u3400-\u9fff]", text))
        other_chars = max(len(text) - cjk_chars - latin_chars, 0)
        return max(1, cjk_chars + int(latin_words * 1.2) + other_chars // 4)

    def _local_extraction_prompt(self, template: Optional[MeetingTemplate] = None) -> str:
        """本地萃取提示詞（共用基底＋模板增補；v4.4.0）。"""
        extra = template.extraction_prompt_extra if template else ""
        return self.LOCAL_EXTRACTION_PROMPT + extra

    def _cloud_extraction_prompt(self, template: Optional[MeetingTemplate] = None) -> str:
        """雲端萃取提示詞（共用基底＋模板增補；v4.4.0）。"""
        extra = template.extraction_prompt_extra if template else ""
        return self.CLOUD_EXTRACTION_PROMPT + extra

    def _build_local_context_plan(
        self,
        transcript: str,
        system_prompt: str,
        template: Optional[MeetingTemplate] = None,
        context_window_tokens: Optional[int] = None,
    ) -> LocalContextPlan:
        """根據有效上下文視窗估算是否需要分塊。

        P0-6 延伸（v4.4.0）：萃取 prompt 須以「模板增補後」的實際文字估算，
        否則採購等較長模板會讓輸入超出 num_ctx 被 Ollama 靜默截斷。
        v4.7.0：視窗可由 warmup 降級結果覆蓋（offload 自我修復失敗時）。
        """
        transcript_tokens = self._estimate_tokens(transcript)
        context_window = context_window_tokens or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS
        output_budget = settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS
        extraction_overhead = (
            self._estimate_tokens(system_prompt)
            + self._estimate_tokens(self._local_extraction_prompt(template))
            + 250
        )
        chunk_input_budget = max(1200, context_window - output_budget - extraction_overhead)
        # v4.8.0（T20260922-1930-01）：3200 過去是與 context 無關的固定常數——在
        # 128000 的 loaded instance 上只用掉可承載量的 2.6%，把 11,712 est 的逐字稿
        # 硬切成 4 塊，跨塊關聯（前段提議、後段定案）在萃取階段就註定對不起來。
        # 改為預設依 context 推導；設定明確給上限時才夾住（可回復旋鈕）。
        chunk_ceiling = int(settings.LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING or 0)
        if chunk_ceiling > 0:
            chunk_input_budget = min(chunk_input_budget, chunk_ceiling)
        # P0-6：合併後筆記會進入「最終生成」步驟；merge 可見目標（約 900 tokens）
        # 保證最終步驟輸入（完整公務紀錄 System Prompt 約 1,200 tokens＋補強輪
        # 附帶的當前摘要）遠低於 context window，不會被 num_ctx 靜默截斷。
        merge_overhead = self._estimate_tokens(self.LOCAL_NOTES_MERGE_PROMPT) + 250
        # T20260827-1127-01 RC-1：merge 預算語意分離（CHANGE_MAP 1）。
        # - merge_provider_output_tokens：LM Studio 初始 completion cap，使用
        #   既有 LOCAL_LLM_RESERVED_OUTPUT_TOKENS；hidden reasoning 吃掉預算時
        #   由有界 semantic recovery 依 headroom/configured-cap 公式有限增加，
        #   不以可見目標壓縮 provider cap。
        # - merge_visible_target_tokens：合併後 notes 的可見收斂目標（約 900，
        #   final-stage fit 目的），只在 merge prompt 明示，不進入 max_tokens。
        # - merge_input_budget_tokens：一組來源 notes 的上限，由 context window
        #   扣除 merge prompt overhead 與 provider completion reserve 計算。
        merge_provider_output_tokens = output_budget
        merge_visible_target_tokens, merge_feasible_input_tokens = self._resolve_merge_targets(
            system_prompt=system_prompt,
            template=template,
            context_window=context_window,
            output_budget=output_budget,
        )
        merge_feasible_input = context_window - merge_provider_output_tokens - merge_overhead
        # Preflight：context 必須同時容納 merge prompt、至少兩份目標大小 notes
        # 與 provider completion reserve；不可行時在 provider I/O 前 fail loudly。
        if merge_feasible_input < 2 * merge_visible_target_tokens:
            raise StableServiceError(
                LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED,
                f"merge 階段 context 預算不足：context window {context_window} tokens 無法"
                f"同時容納 merge prompt 開銷（約 {merge_overhead} tokens）、兩份目標大小"
                f"notes（{2 * merge_visible_target_tokens} tokens）與 provider completion "
                f"reserve（{merge_provider_output_tokens} tokens）；請調大 context window"
                "或降低 LOCAL_LLM_RESERVED_OUTPUT_TOKENS",
            )
        merge_input_budget_tokens = max(
            merge_visible_target_tokens,
            merge_feasible_input,
        )
        effective_chunk_step = max(
            chunk_input_budget - self.LOCAL_LLM_CHUNK_OVERLAP_BUDGET_TOKENS, 1
        )
        estimated_chunk_count = max(1, (transcript_tokens + effective_chunk_step - 1) // effective_chunk_step)

        return LocalContextPlan(
            context_window_tokens=context_window,
            estimated_transcript_tokens=transcript_tokens,
            chunk_input_budget_tokens=chunk_input_budget,
            merge_input_budget_tokens=merge_input_budget_tokens,
            merge_visible_target_tokens=merge_visible_target_tokens,
            merge_provider_output_tokens=merge_provider_output_tokens,
            needs_chunking=transcript_tokens > chunk_input_budget,
            estimated_chunk_count=estimated_chunk_count,
            merge_feasible_input_tokens=merge_feasible_input_tokens,
        )

    def _resolve_local_output_tokens(
        self,
        *,
        context_window: Optional[int],
        prompt_tokens: int,
        minimum: Optional[int] = None,
    ) -> int:
        """依 context 餘裕推導單次生成輸出上限（v4.8.0）。

        根因：三階段（萃取／最終生成／補強）過去共用固定的
        ``LOCAL_LLM_RESERVED_OUTPUT_TOKENS``（3072）。在 128K instance 上這等於把
        紀錄長度鎖在約 3,000 繁中字——已與雲端的「下限」相同（雲端路徑完全不傳
        max_tokens）。此處比照 Ollama 路徑既有的 ``expand_output_budget`` 語意，把
        沒用完的 context 讓給輸出，並以 ``LOCAL_LLM_OUTPUT_TOKENS_CEILING`` 設天花板
        避免無界生成。

        ``minimum`` 保留歷史保留量（3072）：即使 context 很小也不會比舊行為更嚴格；
        真正的可行性由 provider I/O 前的 preflight 把關。
        """
        floor = int(minimum if minimum is not None else settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS)
        floor = max(floor, 1)
        window = int(context_window or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS)
        available = (
            window
            - max(int(prompt_tokens or 0), 0)
            - int(settings.LOCAL_LLM_CONTEXT_SAFETY_MARGIN_TOKENS)
        )
        budget = max(floor, available)
        ceiling = int(settings.LOCAL_LLM_OUTPUT_TOKENS_CEILING or 0)
        if ceiling > 0:
            budget = min(budget, max(floor, ceiling))
        return budget

    def _resolve_merge_targets(
        self,
        *,
        system_prompt: str,
        template: Optional[MeetingTemplate],
        context_window: int,
        output_budget: int,
    ) -> tuple[int, int]:
        """推導整併的可見目標與下游可承接上限（T20260922-1349-01 RC-1b）。

        契約（取代固定 900）：
        - 最終生成步驟的輸入＝系統提示詞＋整併後筆記；補強輪會再把「當前摘要」
          帶回 prompt，故需額外保留一份輸出預算。
        - ``final_stage_input_budget``＝context window 扣除最終輸出保留、補強輪
          回饋保留與最終提示詞開銷後，仍可容納的筆記量。
        - ``merge_feasible_input_tokens``（硬性上限）＝max(900, 上式)：不得低於
          歷史下限 900，否則會比既有行為更嚴格（ctx=8192 時與舊行為完全相同）。
        - ``merge_visible_target_tokens``（軟性目標）＝min(上式, 4096)：保留
          「整併要收斂」的壓力，同時不讓超大 context 把整併放寬到失去聚焦。
        """
        # 補強輪的提示詞骨架（問題清單＋「目前版本」＋「萃取筆記」段落標題）與
        # 最終生成提示詞不同，必須一併保留；否則單一 note 剛好貼齊硬性上限時，
        # 補強輪的 `available_output` 會略低於 provider completion cap，反而以
        # LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED fail loudly（等於把剛打開的成功出口
        # 又關上）。只取「相對最終生成提示詞的邊際開銷」，避免與上方已計入的
        # generation_message_extra 重複計算。
        refinement_overhead = max(
            0,
            self._estimate_tokens(
                self._build_refinement_message("", "", [], template=template)
            )
            - self._estimate_tokens(self._template_generation_extra(template)),
        )
        final_prompt_overhead = (
            self._estimate_tokens(system_prompt)
            + self._estimate_tokens(self._template_generation_extra(template))
            + refinement_overhead
            + 250
        )
        final_stage_input_budget = (
            context_window
            - output_budget
            - output_budget
            - final_prompt_overhead
        )
        merge_feasible_input_tokens = max(
            self.LOCAL_LLM_MERGE_VISIBLE_TARGET_TOKENS, final_stage_input_budget
        )
        merge_visible_target_tokens = min(
            merge_feasible_input_tokens,
            self.LOCAL_LLM_MERGE_VISIBLE_TARGET_CEILING_TOKENS,
        )
        return merge_visible_target_tokens, merge_feasible_input_tokens

    # 單行逐字稿超過此字數時，先插入段落換行（只改 whitespace）
    PARAGRAPH_LINE_MAX_CHARS = 600
    _SENTENCE_BOUNDARY_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])")
    # fragment 內回退切點可用的標點與空白界線
    _FRAGMENT_BOUNDARY_CHARS = "。！？!?；;，、, \t\n"

    def _insert_paragraph_breaks(self, line: str) -> str:
        """對超長單行逐字稿插入段落換行：優先句尾標點、其次空白、最後硬界線。

        只插入換行符（whitespace），不改任何非空白內容。此為 best-effort
        可讀性處理，即使無法理想切分也會以硬界線收斂，不得成為 gate。
        """
        if len(line) <= self.PARAGRAPH_LINE_MAX_CHARS:
            return line

        max_chars = self.PARAGRAPH_LINE_MAX_CHARS

        def _wrap_segment(segment: str) -> list[str]:
            parts: list[str] = []
            rest = segment
            while len(rest) > max_chars:
                window = rest[:max_chars]
                boundary = max(window.rfind(" "), window.rfind("\t"))
                if boundary <= 0:
                    parts.append(rest[:max_chars])
                    rest = rest[max_chars:]
                else:
                    parts.append(rest[:boundary])
                    rest = rest[boundary + 1 :]
            parts.append(rest)
            return [part for part in parts if part]

        wrapped: list[str] = []
        for segment in self._SENTENCE_BOUNDARY_SPLIT_RE.split(line):
            if not segment:
                continue
            if len(segment) <= max_chars:
                wrapped.append(segment)
            else:
                wrapped.extend(_wrap_segment(segment))
        return "\n".join(wrapped)

    def _largest_prefix_index_within_budget(self, text: str, max_input_tokens: int) -> int:
        """二分搜尋最大的 index c，使 estimated_tokens(text[:c]) <= max_input_tokens。"""
        lo, hi = 1, len(text)
        best = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._estimate_tokens(text[:mid]) <= max_input_tokens:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    def _latest_boundary_cut(self, text: str, limit: int) -> Optional[int]:
        """找出 text[:limit] 內最後一個標點／空白界線，回傳界線字元之後的切點。"""
        latest = -1
        for char in self._FRAGMENT_BOUNDARY_CHARS:
            index = text.rfind(char, 0, limit)
            if index > latest:
                latest = index
        if latest < 0:
            return None
        return latest + 1

    def _split_oversized_fragment(self, fragment: str, max_input_tokens: int) -> list[str]:
        """將超過 token 預算的 fragment 以二分搜尋切到合法大小。

        超過 max_input_tokens 時以二分搜尋找出最大合法 prefix；當該 prefix
        仍至少保留 60% budget 時，優先回退到最近的標點／空白界線切（避免
        切半個詞）；否則硬切。每個產出 fragment 都保證 <= max_input_tokens。
        """
        results: list[str] = []
        rest = fragment
        while rest:
            if self._estimate_tokens(rest) <= max_input_tokens:
                results.append(rest)
                break
            cut = self._largest_prefix_index_within_budget(rest, max(1, max_input_tokens - 1))
            if cut <= 0:
                # 單一字元即超過預算（極小 max_input_tokens）——硬切 1 字避免死迴圈
                results.append(rest[:1])
                rest = rest[1:]
                continue
            if self._estimate_tokens(rest[:cut]) >= int(max_input_tokens * 0.6):
                boundary = self._latest_boundary_cut(rest, cut)
                if boundary is not None and 0 < boundary < cut:
                    cut = boundary
            results.append(rest[:cut].strip())
            rest = rest[cut:]
        return [part for part in results if part]

    def _split_oversized_line(self, line: str, max_input_tokens: int) -> list[str]:
        """將單行過長的逐字稿切成較小片段（token-aware）。

        先依句尾標點切句，每個 fragment 再重新檢查 estimated tokens；
        超過 max_input_tokens 的 fragment 交給 _split_oversized_fragment
        以二分搜尋切分，確保每個片段都在 input budget 內。
        """
        fragments = [
            fragment.strip()
            for fragment in re.split(r"(?<=[。！？!?；;])\s*", line)
            if fragment.strip()
        ]
        if len(fragments) <= 1:
            fragments = [line.strip()] if line.strip() else []
        results: list[str] = []
        for fragment in fragments:
            if self._estimate_tokens(fragment) <= max_input_tokens:
                results.append(fragment)
            else:
                results.extend(self._split_oversized_fragment(fragment, max_input_tokens))
        return [fragment for fragment in results if fragment]

    def _assemble_chunks_from_lines(
        self, lines: list[str], max_input_tokens: int, overlap_lines: int
    ) -> tuple[list[str], list[int]]:
        """將已合法化的 lines 依序組成 chunks，並以 overlap 豐富上下文。

        Invariant：每個 chunk 的 estimated tokens 不得超過 max_input_tokens。
        overlap 是 best-effort：先以 budget 一半封頂，再持續移除最舊 carry
        line 直到 `carry_tokens + next_line_tokens <= max_input_tokens`；
        overlap 可降為零，絕不保留會讓 chunk 超出預算的超大 carry。

        回傳（chunks, 每個 chunk 與前一 chunk 共用的重疊行數）。
        """
        chunks: list[str] = []
        overlaps: list[int] = []
        current_lines: list[str] = []
        current_tokens = 0
        current_overlap = 0

        for line in lines:
            line_tokens = self._estimate_tokens(line) + 1
            if current_lines and current_tokens + line_tokens > max_input_tokens:
                chunks.append("\n".join(current_lines).strip())
                overlaps.append(current_overlap)

                carry_lines = current_lines[-overlap_lines:]
                carry_tokens = sum(self._estimate_tokens(item) + 1 for item in carry_lines)
                # RC-4：carry 同時受共享 220-token 常數與 max_input_tokens 一半
                # 封頂（極小 budget 時保留 12-token 下限行為）；overlap 可降為零。
                max_overlap_tokens = max(
                    12,
                    min(
                        self.LOCAL_LLM_CHUNK_OVERLAP_BUDGET_TOKENS,
                        max_input_tokens // 2,
                    ),
                )
                while len(carry_lines) > 1 and carry_tokens > max_overlap_tokens:
                    removed = carry_lines.pop(0)
                    carry_tokens -= self._estimate_tokens(removed) + 1
                while carry_lines and carry_tokens + line_tokens > max_input_tokens:
                    removed = carry_lines.pop(0)
                    carry_tokens -= self._estimate_tokens(removed) + 1

                current_lines = carry_lines[:]
                current_tokens = carry_tokens
                current_overlap = len(carry_lines)

            current_lines.append(line)
            current_tokens += line_tokens

        if current_lines:
            chunks.append("\n".join(current_lines).strip())
            overlaps.append(current_overlap)

        return chunks, overlaps

    def _validate_chunk_postcondition(
        self,
        transcript: str,
        chunks: list[str],
        chunk_overlaps: list[int],
        max_input_tokens: int,
    ) -> None:
        """chunking postcondition（provider I/O 前檢查，違反即 fail loudly）。

        檢查：chunks 非空、每塊 estimated tokens <= max_input_tokens、
        去除重疊後串接等於原文的 whitespace 正規化版本（順序涵蓋、不遺失內容）。
        違反時在 provider I/O 前拋出穩定的 context budget 錯誤碼，
        讓 task fallback 以可診斷方式呈現（T20260827-1127-01）。
        """

        def _norm(text: str) -> str:
            return re.sub(r"\s+", "", text)

        if not chunks:
            raise StableServiceError(
                LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED,
                "chunking 後無任何區塊（輸入非空）",
            )

        for index, chunk in enumerate(chunks):
            chunk_tokens = self._estimate_tokens(chunk)
            if chunk_tokens > max_input_tokens:
                raise StableServiceError(
                    LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED,
                    f"chunk {index} estimated tokens {chunk_tokens} "
                    f"超過 input budget {max_input_tokens}",
                )

        merged: list[str] = []
        for chunk, overlap in zip(chunks, chunk_overlaps):
            chunk_lines = [line.strip() for line in chunk.split("\n") if line.strip()]
            skip = min(overlap, len(chunk_lines) - 1, len(merged))
            if skip > 0 and merged[-skip:] != chunk_lines[:skip]:
                raise StableServiceError(
                    LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED,
                    "chunk 重疊行與前一 chunk 尾端不一致",
                )
            merged.extend(chunk_lines[skip:])

        if "".join(_norm(line) for line in merged) != _norm(transcript):
            raise StableServiceError(
                LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED,
                "chunk 切塊未完整涵蓋原始逐字稿（遺失或改動內容）",
            )

    def _split_transcript_into_chunks(self, transcript: str, max_input_tokens: int) -> list[str]:
        """依 speaker line 與自然斷點切塊，並保留少量重疊內容。

        Invariant（provider 呼叫前強制）：chunks 非空、每塊
        estimated tokens <= max_input_tokens、順序涵蓋原始內容。
        段落換行只改 whitespace 且不構成 gate（失敗退回硬切）。
        """
        raw_lines = [line.strip() for line in transcript.splitlines() if line.strip()]
        if not raw_lines:
            return []

        normalized_lines: list[str] = []
        for raw_line in raw_lines:
            if len(raw_line) > self.PARAGRAPH_LINE_MAX_CHARS:
                candidate_lines = [
                    part
                    for part in self._insert_paragraph_breaks(raw_line).split("\n")
                    if part.strip()
                ]
            else:
                candidate_lines = [raw_line]
            for line in candidate_lines:
                if self._estimate_tokens(line) <= max_input_tokens:
                    normalized_lines.append(line)
                else:
                    normalized_lines.extend(self._split_oversized_line(line, max_input_tokens))

        overlap_lines = max(1, settings.LOCAL_LLM_CHUNK_OVERLAP_LINES)
        chunks, chunk_overlaps = self._assemble_chunks_from_lines(
            normalized_lines, max_input_tokens, overlap_lines
        )
        self._validate_chunk_postcondition(
            transcript, chunks, chunk_overlaps, max_input_tokens
        )
        return chunks

    @staticmethod
    def _normalize_action_key(text: str) -> str:
        """將待辦事項文字正規化，方便比對是否遺漏。

        P3 波（R23）：正規化必須**對稱**。紀錄側在驗證之前已走過
        `_finalize_record_text(mode="local")`（OpenCC 台灣正體＋模板詞彙修正，
        例如「征收股」→「徵收股」），但比對基準 `merged_notes`／萃取筆記完全
        沒過同一條。只折半邊的實測後果：同一件事被誤判成遺漏。

        真實案例（0903 場、27B）：待辦標籤「了解房屋稅系統業務調整（稽查股/征收股）」
        在紀錄中寫成「徵收股」→ 舊版逐條比對判為遺漏，而 `merged_notes` 在補強
        迴圈中固定不變，假陽性集合逐輪相同 → 補強註定不收斂（實測 2 輪白燒 710 s，
        佔總時長 42%），且每輪都是整份紀錄重生成，對品質是負向風險。

        如實界線：這裡處理的是**同一條管線能折疊的差異**（全形/半形、標點、
        可偵測的簡體字）；「征收 vs 徵收」這種**模板詞彙修正**造成的差異不在這裡
        折疊（`to_taiwan_traditional` 刻意只轉含簡體字的行，避免誤傷正體用字，
        見 `backend/core/text_postprocess.py`），而是由 `_action_key_best_lcs_ratio`
        的近似比對吸收——實測該案例 LCS 0.94。
        """
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKC", text)
        try:  # 與紀錄側同一條簡繁折疊；缺 OpenCC 時原樣（仍對稱）
            from backend.core.text_postprocess import to_taiwan_traditional

            normalized = to_taiwan_traditional(normalized)
        except Exception:  # noqa: BLE001
            pass
        return re.sub(r"[\s\t\r\n:：,，。；;（）()「」『』【】\[\]／/\\-]+", "", normalized).lower()

    @staticmethod
    def _lcs_length(left: str, right: str) -> int:
        """最長共同子序列長度（滾動陣列，純確定性、無第三方依賴）。"""
        if not left or not right:
            return 0
        previous = [0] * (len(right) + 1)
        for char in left:
            current = [0] * (len(right) + 1)
            for index, other in enumerate(right, 1):
                if char == other:
                    current[index] = previous[index - 1] + 1
                else:
                    current[index] = max(previous[index], current[index - 1])
            previous = current
        return previous[-1]

    @classmethod
    def _action_key_best_window(
        cls, key: str, haystack: str, bigram_index: dict
    ) -> tuple[float, str]:
        """待辦標籤在紀錄中「最佳連續視窗」的（LCS 覆蓋比例, 該視窗文字）。

        只看**連續視窗**（長度＝標籤長 + 4）而非整份紀錄：整份紀錄比對會讓
        「同一個字恰好散落在不同段落」被誤判成已涵蓋（false negative）。
        候選視窗由標籤自身的字元 bigram 在紀錄中的出現位置反推，因此不需要
        全文掃描；比對語意是「順序大致保留的改寫」，比集合式比對更貼近人眼。

        一併回傳視窗文字，供守衛做**局部**判定（審查 attempt-07 R2：否定詞若只
        檢查「整份紀錄有沒有出現」，目標句被反轉、而否定詞出現在其他段落時仍會
        被洗白成已涵蓋）。
        """
        if len(key) < 4:
            # 太短的標籤（例：「設備調整」）不做近似比對：改寫空間太大，
            # 任何近似都會變成雜訊。保留舊行為（需完整子字串命中）。
            return 0.0, ""
        candidates = set()
        for offset in range(len(key) - 1):
            for position in bigram_index.get(key[offset : offset + 2], ()):
                candidates.add(position - offset)
        window_length = len(key) + 4
        best = 0.0
        best_window = ""
        for start in candidates:
            if start < 0:
                continue
            window = haystack[start : start + window_length]
            if not window:
                continue
            ratio = cls._lcs_length(key, window) / len(key)
            if ratio > best:
                best = ratio
                best_window = window
                if best >= cls.ACTION_MATCH_MIN_LCS_RATIO:
                    return best, best_window
        return best, best_window

    @classmethod
    def _action_key_best_lcs_ratio(cls, key: str, haystack: str, bigram_index: dict) -> float:
        """`_action_key_best_window` 的純比例包裝（供日誌與外部呼叫使用）。"""
        return cls._action_key_best_window(key, haystack, bigram_index)[0]

    @classmethod
    def _split_record_sentences(cls, text: str) -> tuple:
        """把紀錄切成句子並套用同一條正規化（守衛的「最相近一句話」判定用）。

        為什麼不能用「整份紀錄」或單純的固定長度視窗：正規化會把換行與標點折疊掉，
        於是別的子句（甚至別的段落）的否定詞可能落進視窗內，讓「目標句被反轉」
        誤判成已涵蓋（獨立審查 attempt-07 的 R2 反例）。切句後只認「與標籤最相近
        的那一句」，語意上就是「這件事被寫在哪一句」，比全文或視窗都更貼近正確範圍。
        """
        sentences = []
        for piece in re.split(r"[。！？!?；;\n]+", text or ""):
            normalized = cls._normalize_action_key(piece)
            if normalized:
                sentences.append(normalized)
        return tuple(sentences)

    @classmethod
    def _find_missing_action_keys(
        cls, expected_actions, normalized_summary: str, local_sentences=None
    ) -> tuple[set, dict]:
        """回傳（未涵蓋的待辦 key 集合, {key: 最佳 LCS 比例}）。

        判定規則（P3 波 R23，兩條都是確定性、無 LLM）：
        1. 正規化後的標籤本身是紀錄的連續子字串 → 已涵蓋（改寫幅度小）。
        2. 否則取滑窗 LCS 比例 ≥ `ACTION_MATCH_MIN_LCS_RATIO` → 已涵蓋
           （順序大致保留的改寫，例：「嚴禁轉傳科內群組訊息至外部」寫成
           「嚴禁將科內群組訊息（含照片）外流至任何外部渠道」）。
        未達門檻者才計入遺漏，並回傳比例供日誌與調校使用。

        3. 近似比對通過後，仍要過兩道「語意不能被近似吸收」的守衛（R2）：
           標籤內的**否定詞**（`ACTION_NEGATION_TERMS`）與 **≥2 位數字串**必須
           原樣出現在**局部比對範圍**內，否則一律判遺漏。理由：LCS 是字面量尺，
           否定詞（實測 0.917）與數字（實測 0.818）恰好是它最不敏感、
           而正式紀錄最不允許失真的兩類資訊。方向刻意**往更嚴**——
           代價是可能多一輪補強（已有不收斂保護上限），收益是不會把
           失真當成已涵蓋而靜默放行。
           「局部比對範圍」＝**最佳比對視窗**（標籤長＋4 的連續區段）與
           **最相近的一句話**（`local_sentences`，由呼叫端提供）的交集：
           只檢查「整份紀錄有沒有出現」不夠——獨立審查 attempt-07 的反例顯示，
           同一個否定詞出現在別的子句時，目標句反轉（LCS 0.8571）會被放行；
           只檢查視窗也不夠，因為正規化會消掉換行，「別句的否定詞」可能落進視窗。
           `local_sentences=None`（未提供）時退化成只檢查視窗。
        """
        bigram_index: dict[str, list[int]] = {}
        for index in range(len(normalized_summary) - 1):
            bigram_index.setdefault(normalized_summary[index : index + 2], []).append(index)
        missing: set = set()
        ratios: dict = {}
        for key in expected_actions:
            if not key or key in normalized_summary:
                continue
            ratio, window = cls._action_key_best_window(key, normalized_summary, bigram_index)
            ratios[key] = ratio
            if ratio < cls.ACTION_MATCH_MIN_LCS_RATIO:
                missing.add(key)
                continue
            local_texts = [window] if window else []
            if local_sentences:
                local_texts.append(
                    max(local_sentences, key=lambda sentence: cls._lcs_length(key, sentence))
                )
            if not local_texts:
                local_texts = [normalized_summary]
            missing_negations = [
                term
                for term in cls.ACTION_NEGATION_TERMS
                if term in key and any(term not in text for text in local_texts)
            ]
            missing_numbers = [
                token
                for token in cls._ACTION_NUMBER_PATTERN.findall(key)
                if any(token not in text for text in local_texts)
            ]
            if missing_negations or missing_numbers:
                missing.add(key)
                log.info(
                    "待辦召回守衛攔下（LCS {:.2f} 已達門檻，但語意資訊缺失）："
                    "{}｜缺否定詞 {}｜缺數字 {}",
                    ratio,
                    key[:24],
                    missing_negations or "無",
                    missing_numbers or "無",
                )
        return missing, ratios

    def _extract_action_table_labels(self, markdown: str) -> list[str]:
        """只從萃取筆記的『待辦清單』Markdown 表格列抽取待辦「原始標籤」。

        與 `_extract_action_table_keys` 使用完全相同的過濾規則（僅第一欄、
        排除表頭與「未於本段確認」佔位列）；差別只在這裡保留人類可讀文字，
        讓補強訊息可以指名「哪幾項待辦沒被寫進紀錄」，而不是只回報一個數量。
        實測舊行為：地端兩份紀錄分別遺漏 8／11 項待辦，但補強輪只拿到數字，
        重寫後輸出逐字相同（兩輪無效）——問題清單必須帶具體項目才有作用。
        """
        labels: list[str] = []
        for line in markdown.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("|") and stripped.endswith("|")):
                continue
            if ":---" in stripped or re.fullmatch(r"\|\s*-+\s*(\|\s*-+\s*)+\|", stripped):
                continue

            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) < 3:
                continue
            if cells[0] in {"待辦事項", "事項說明"}:
                continue
            if "本次會議未明確指派待辦事項" in cells[0] or "未於本段確認" in cells[0]:
                continue

            labels.append(cells[0])

        return labels

    def _extract_action_table_keys(self, markdown: str) -> set[str]:
        """只從萃取筆記的『待辦清單』Markdown 表格列抽取待辦關鍵字。

        僅取表格第一欄（待辦事項本身），刻意忽略議題、日期、參與者等非待辦
        條列，避免把會議資訊誤判成待辦而造成假性「遺漏」。
        """
        keys = {
            self._normalize_action_key(label)
            for label in self._extract_action_table_labels(markdown)
        }
        return {key for key in keys if key}

    # P1-8：欄位驗證改為容錯 regex（允許空格數量與全半形冒號差異），
    # 驗證「欄位存在性」而非字面完全一致；欄位標準化交由記錄級後處理。
    # v4.4.0：驗證樣式改由會議模板驅動；本常數保留為 general 模板別名
    # （測試與舊呼叫端相容）。
    _REQUIRED_SECTION_PATTERNS = list(get_template("general").required_section_patterns)

    def _validate_summary_quality(
        self,
        summary: str,
        extracted_notes: str,
        min_chars: int = 250,
        template: Optional[MeetingTemplate] = None,
    ) -> list[str]:
        """針對最終摘要做結構與召回檢查（v4.4.0 起依會議模板驅動）。

        min_chars 預設 250（防空輸出的底線）；雲端流程會依逐字稿規模
        傳入動態下限（v4.3.3 豐富度閘門），過薄的紀錄才會觸發補強輪。
        """
        if template is None:
            template = get_template(None)

        issues: list[str] = []
        cleaned = self._clean_ollama_output(summary)

        for label, pattern in template.required_section_patterns:
            if not pattern.search(cleaned):
                issues.append(f"缺少區塊：{label}")

        for label, pattern in template.extra_field_patterns:
            if not pattern.search(cleaned):
                issues.append(f"缺少{label}資訊")

        # 機敏洩漏檢查（採購評選會等模板）：命中即要求重寫遮蔽
        for label, pattern in template.forbidden_patterns:
            if pattern.search(cleaned):
                issues.append(f"疑似機敏資訊洩漏：{label}")

        if len(cleaned) < min_chars:
            issues.append(
                f"摘要內容過短（{len(cleaned)} 字，最低要求 {min_chars} 字）："
                "請補充各單位意見的理由與數據、決議與裁示的具體細節，不得以單句帶過"
            )

        if self._contains_simplified_chinese(cleaned):
            issues.append("出現簡體中文漂移")

        if self._contains_non_markdown_leakage(summary) or self._contains_non_markdown_leakage(cleaned):
            issues.append("包含思考標籤或非 Markdown 洩漏內容")

        if self._contains_english_or_rubric_leakage(summary) or self._contains_english_or_rubric_leakage(cleaned):
            issues.append("包含英文前言、英文整句或回吐的評估標準")

        # 待辦召回採「包含」比對：待辦清單中的事項只要其文字出現在最終摘要任一處
        # 即視為已涵蓋，容許摘要改寫或補充字詞（如「完成整合測試」→「請於下週三前完成整合測試」），
        # 避免逐字不符就誤判遺漏而觸發不必要的補強輪次。
        expected_actions = self._extract_action_table_keys(extracted_notes)
        normalized_summary = self._normalize_action_key(cleaned)
        # P3 波（R23）：整條連續子字串比對換成「對稱正規化 ＋ 滑窗 LCS 比例」。
        # 舊行為要求待辦標籤**逐字連續**出現才算涵蓋，於是任何改寫（「的」→「之」、
        # 「征收」→「徵收」、「轉傳…至外部」→「外流至任何外部渠道」、加上
        # 「請於下週三前」等修飾語）都被判成遺漏；配合 `merged_notes` 在補強迴圈中
        # 固定不變，問題集合逐輪相同 → 迴圈不收斂。
        # 新判定仍要求「同一段連續文字」，只是容許順序保留的改寫，因此
        # 「真的沒寫」的待辦照樣會被判遺漏（實測對照句 LCS 0.27–0.42 < 0.6）。
        missing_actions, missing_ratios = self._find_missing_action_keys(
            expected_actions,
            normalized_summary,
            local_sentences=self._split_record_sentences(cleaned),
        )
        # P4-A（§2.1-①）：期望集合空集合不得再是靜默 no-op——零告警會讓「筆記沒有
        # 待辦表格／只剩佔位列／走了 _empty_extraction_notes 骨架」永遠無人發現。
        # 只加 log、不改 issues（雲端共用本方法亦不受影響）；mode=off 時完全靜音
        # （維持「off＝回本波前 byte 級行為」）。
        if not expected_actions and (
            getattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "enforce") or ""
        ).strip().lower() != "off":
            log.warning(
                "紀錄覆蓋率檢查：待辦期望集合為空（來源：萃取筆記待辦表格）→ "
                "本類別不產生補強問題；請確認筆記有無待辦表格／是否只剩佔位列／"
                "是否走 _empty_extraction_notes 骨架"
            )
        if missing_actions:
            # 校準用觀察值：把「未被判定涵蓋」的項目與其最佳覆蓋比例寫進日誌，
            # 讓下一次調門檻有真實分布可以看（不影響判定本身）。
            log.info(
                "待辦召回比對（P3，門檻 {}）：未涵蓋 {} 項，最佳 LCS 比例 {}",
                self.ACTION_MATCH_MIN_LCS_RATIO,
                len(missing_actions),
                ", ".join(
                    f"{key[:18]}…={ratio:.2f}"
                    if len(key) > 18
                    else f"{key}={ratio:.2f}"
                    for key, ratio in list(missing_ratios.items())[: self.ACTION_ISSUE_PREVIEW_LIMIT]
                ),
            )
        if missing_actions:
            # v4.8.0：問題清單帶「具體遺漏項目」。舊行為只回報數量，模型無從得知
            # 少了什麼，補強輪因此空轉（實測兩輪輸出逐字相同、遺漏數不變）。
            label_by_key: dict[str, str] = {}
            for label in self._extract_action_table_labels(extracted_notes):
                key = self._normalize_action_key(label)
                if key:
                    label_by_key.setdefault(key, label)
            missing_labels = [
                label_by_key.get(key, key) for key in sorted(missing_actions)
            ]
            preview = "、".join(missing_labels[:self.ACTION_ISSUE_PREVIEW_LIMIT])
            remainder = len(missing_labels) - self.ACTION_ISSUE_PREVIEW_LIMIT
            suffix = f"…（其餘 {remainder} 項）" if remainder > 0 else ""
            issues.append(
                f"待辦事項遺漏 {len(missing_actions)} 項：{preview}{suffix}"
                "；這些待辦都出現在萃取筆記中，請逐列補進待辦事項表格，"
                "不得只以概括敘述帶過或省略"
            )

        return issues

    # ------------------------------------------------------------------
    # P4-A（T20260922-2037-02 §9.3）：逐條對帳（覆蓋率）擴類
    # 議題／決議（取萃取筆記）＋數字／日期（取逐字稿）＋既有待辦（不動）
    # ------------------------------------------------------------------

    # E1 實測（0903 場 gemma-4-31B-it-MLX-4bit 真實筆記）新增的兩種形式：
    # ①議題＝整行粗體標題（頂層條列，`- **組織規程與編制變動（11月1日生效）**`）；
    # ②決議條目＝逐字稿引用標頭（`[00:04:35] 發言者 1（主席）裁示：…`）＋正文。
    # 兩者都是「筆記格式知識」，不是模型名分支（任何模型寫出同格式即生效）。
    _NOTES_ITEM_BOLD_TITLE_PATTERN = re.compile(r"^[-*+]\s+\*\*([^*]+?)\*\*\s*$")
    _NOTES_ITEM_TIME_PREFIX_PATTERN = re.compile(
        r"^\[\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[-–~]\s*\d{1,2}:\d{2}(?::\d{2})?)?\s*\]\s*"
    )
    _NOTES_ITEM_SPEAKER_PREFIX_PATTERN = re.compile(
        r"^(?:發言者|與會者|發言人)\s*\d+(?:[（(][^）)]{0,12}[）)])?\s*[：:，,]?\s*"
    )
    _NOTES_ITEM_ROLE_PREFIX_PATTERN = re.compile(
        r"^(?:(?:主席|科長|主持人|主席裁示)\s*)?"
        r"(?:裁示|指示|決議|結論|說明|表示|補充|報告|提醒)\s*[：:，,]\s*"
    )

    @classmethod
    def _strip_notes_item_quote_prefix(cls, item: str) -> str:
        """剝掉萃取筆記條目開頭的「逐字稿引用標頭」（E1 實測修補）。

        真實實例：`[00:04:35] 發言者 1（主席）裁示：資管股及系統相關人員需…`
        → `資管股及系統相關人員需…`；`[00:21:01] 發言者 1（主席裁示）：`
        → ``（空，該條決議的內容寫在下一層條列，必須整條丟棄）。

        只剝「時間戳／發言者標籤／角色動詞（各自最多一次）」三種前綴，其餘
        原樣；沒有標頭時輸出＝輸入。純函式、無 I/O、無模型名分支。
        """
        text = (item or "").strip()
        for pattern in (
            cls._NOTES_ITEM_TIME_PREFIX_PATTERN,
            cls._NOTES_ITEM_SPEAKER_PREFIX_PATTERN,
            cls._NOTES_ITEM_ROLE_PREFIX_PATTERN,
        ):
            text = pattern.sub("", text, count=1).strip()
        return text

    @classmethod
    def _parse_notes_items(
        cls, notes: str, heading_keywords, marker_keywords, include_bold_titles: bool = False
    ) -> list:
        """從萃取筆記抽取指定標記（議題／決議）的條目文字（P4-A）。

        來源格式＝`LOCAL_EXTRACTION_PROMPT`「## 2. 議題與決議」區塊的
        `- **議題**：…`／`- *決議*：…` 條列。先以「標題行是否含關鍵詞」限定
        區塊（無此類標題＝退化為全篇掃描）；佔位列（逐字稿未提及／（待確認）／
        未於本段確認／未明確）與過短條目一律濾除——`_empty_extraction_notes`
        骨架就是「逐字稿未提及／（待確認）」，不濾會產生假期望集合。最後以
        `_normalize_action_key` 去重（保留首現）。

        E1 實測修補（`include_bold_titles`，真實 gemma-4-31B-it-MLX-4bit 筆記）：
        真實輸出的議題不是 `- **議題**：X`，而是把議題寫成**整行粗體標題**
        （`- **組織規程與編制變動（11月1日生效）**`），於是議題期望集合恆為 0
        → 該類別永遠 no-op（E1 log：`cov_expected_topic=0`）。開啟本參數後，
        區塊內「整行只有粗體標題」的頂層條列也算議題；決議維持只認 `*決議*`
        標記（同一行的粗體標題是議題、不是決議）。
        """
        heading_keywords = tuple(heading_keywords)
        marker_pattern = re.compile(
            r"^\s*(?:[-*+]\s*)?(?:\*{1,2})?(?:"
            + "|".join(re.escape(marker) for marker in marker_keywords)
            + r")(?:\*{1,2})?\s*[:：]\s*(.+?)\s*$"
        )
        heading_pattern = re.compile(r"^\s*#{1,6}\s")
        lines = (notes or "").splitlines()
        scoped = any(
            heading_pattern.match(line) and any(keyword in line for keyword in heading_keywords)
            for line in lines
        )
        in_scope = not scoped
        items: list = []
        seen_keys: set = set()
        for line in lines:
            if heading_pattern.match(line):
                in_scope = any(keyword in line for keyword in heading_keywords)
                continue
            if not in_scope:
                continue
            match = marker_pattern.match(line)
            if match:
                item = match.group(1).strip()
            elif include_bold_titles:
                title_match = cls._NOTES_ITEM_BOLD_TITLE_PATTERN.match(line)
                if not title_match:
                    continue
                item = title_match.group(1).strip()
            else:
                continue
            if not item or len(item) < cls.RECORD_COVERAGE_MIN_ITEM_CHARS:
                continue
            # E1 實測修補：條目常以逐字稿引用開頭（`[00:04:35] 發言者 1（主席）裁示：…`）。
            # 引用標頭不是事實本身，卻在 LCS 比對裡吃掉一半長度，讓「紀錄早就寫進去」
            # 被誤判成遺漏（E1 離線重播：11 項決議全被判遺漏，其中 7 項其實已在紀錄中）
            # → 補強迴圈註定不收斂（實測白燒 2 輪 ≈ 970 s）。比對 key 與顯示文字一律用
            # 剝除標頭後的正文；剝完只剩空殼者（`…裁示：` 後面沒內容，決議寫在下一層
            # 條列）整條丟棄——空條目無法被滿足，只會讓補強永遠不收斂、白燒每一輪。
            body = cls._strip_notes_item_quote_prefix(item)
            if len(body) < cls.RECORD_COVERAGE_MIN_ITEM_CHARS:
                continue
            if any(term in body for term in cls._RECORD_COVERAGE_PLACEHOLDER_TERMS):
                continue
            key = cls._normalize_action_key(body)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            items.append(body)
        return items

    @classmethod
    def _extract_notes_topic_items(cls, notes: str) -> list:
        """議題期望集合（來源：萃取筆記「議題與決議」區塊）。

        `include_bold_titles=True`：真實地端筆記把議題寫成整行粗體標題
        （E1 實證），不放寬這個形式＝議題類別永遠 no-op。
        """
        return cls._parse_notes_items(
            notes,
            heading_keywords=("議題", "決議"),
            marker_keywords=("議題",),
            include_bold_titles=True,
        )

    @classmethod
    def _extract_notes_decision_items(cls, notes: str) -> list:
        """決議期望集合（來源同上）；`*討論重點*` 刻意不列入。"""
        return cls._parse_notes_items(notes, heading_keywords=("議題", "決議"), marker_keywords=("決議",))

    @classmethod
    def _fold_record_for_number_matching(cls, record_markdown: str) -> str:
        """數字／日期比對用的紀錄折疊（覆蓋率契約）：
        `_SOURCE_TAG_PATTERN.sub("")`（先剝來源標註）→ NFKC（全形→半形）→
        去千分位逗號 → 去所有空白。

        為什麼必須先剝來源標註（實測）：B2 紀錄唯一的「17」在
        「麻煩則改發禮券（科長，00:17:52）。」，折疊後成 `…科長001752`，
        會把逐字稿真有的「17」判成已涵蓋（假陰性）；剝除後「17」正確判缺。
        候選 literal 亦以同規則折疊後做子字串判定，因此 `13,600 ≡ 13600`。
        """
        folded = cls._SOURCE_TAG_PATTERN.sub("", record_markdown or "")
        folded = unicodedata.normalize("NFKC", folded)
        folded = folded.replace(",", "")
        return re.sub(r"\s+", "", folded)

    @classmethod
    def _iter_transcript_segment_bodies(cls, transcript: str):
        """逐字稿段落列（`[start-end] 發言者：`）正文迭代（已切掉行首時間戳）。

        只認 `TRANSCRIPT_SEGMENT_PATTERN` 的段落列——「發言者統計」等非段落列
        天然不認（格式知識沿用 text_postprocess 單一模組，與吸附/統計同源）。
        """
        from backend.core.text_postprocess import TRANSCRIPT_SEGMENT_PATTERN

        for raw_line in (transcript or "").splitlines():
            stripped = raw_line.strip()
            match = TRANSCRIPT_SEGMENT_PATTERN.match(stripped)
            if not match:
                continue
            body = stripped[match.end():].strip()
            if body:
                yield body

    @staticmethod
    def _snippet_around_span(text: str, start: int, end: int, limit: int = 40) -> str:
        """取問題字串用的原文片段（≤limit 字；截斷端以「…」標示）。"""
        if len(text) <= limit:
            return text
        center = (start + end) // 2
        half = max(1, limit // 2)
        window_start = max(0, min(len(text) - limit, center - half))
        window = text[window_start:window_start + limit]
        prefix = "…" if window_start > 0 else ""
        suffix = "…" if window_start + limit < len(text) else ""
        return f"{prefix}{window}{suffix}"

    @classmethod
    def _scan_transcript_number_items(cls, transcript: str) -> list:
        """數字期望集合：逐字稿段落列 ×「單位錨定＋同句收集」（literal, snippet）。

        規格（實測校準）：只掃段落列；以 `[。！？!?；;]` 切 clause；clause 內需有
        「數字緊鄰單位（元|塊|萬元|個人|人|％|%|個|孔|樓）」才啟用（避免把時間戳、
        編號等誤收）；啟用後收集 clause 內所有 ≥2 位數字（含千分位寫法，
        如 `13,600`），去全 0、折疊後同值去重（保留首現 literal）。
        """
        items: list = []
        seen: set = set()
        for body in cls._iter_transcript_segment_bodies(transcript):
            for clause in cls._RECORD_COVERAGE_SENTENCE_SPLIT_PATTERN.split(body):
                if not cls._RECORD_COVERAGE_NUMBER_UNIT_PATTERN.search(clause):
                    continue
                for number_match in cls._RECORD_COVERAGE_ANY_NUMBER_PATTERN.finditer(clause):
                    literal = number_match.group(0)
                    folded = unicodedata.normalize("NFKC", literal).replace(",", "")
                    if not folded or cls._RECORD_COVERAGE_NUMBER_ALL_ZERO_PATTERN.match(folded):
                        continue
                    if folded in seen:
                        continue
                    seen.add(folded)
                    items.append(
                        (literal, cls._snippet_around_span(clause, number_match.start(), number_match.end()))
                    )
        return items

    @classmethod
    def _scan_transcript_date_items(cls, transcript: str) -> list:
        """日期期望集合：逐字稿段落列 × 四樣式（canonical, snippet）。

        樣式依序：月日（後綴 日／號／号 可省）、月底、斜線 M/D、下+(個)?+
        週/周/星期/禮拜+X（週幾）。範圍檢查（月 1–12、日 1–31）＋同值去重
        （保留首現）避免長會議重複佔額。canonical＝`M/D`、`M月底`、`週X`——
        覆蓋判定含等價展開（`_date_canonical_is_covered`）。
        """
        items: list = []
        seen: set = set()

        def add(canonical: str, snippet: str) -> None:
            if canonical in seen:
                return
            seen.add(canonical)
            items.append((canonical, snippet))

        for body in cls._iter_transcript_segment_bodies(transcript):
            for match in cls._RECORD_COVERAGE_DATE_MD_PATTERN.finditer(body):
                month, day = int(match.group(1)), int(match.group(2))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    add(f"{month}/{day}", cls._snippet_around_span(body, match.start(), match.end()))
            for match in cls._RECORD_COVERAGE_DATE_END_PATTERN.finditer(body):
                month = int(match.group(1))
                if 1 <= month <= 12:
                    add(f"{month}月底", cls._snippet_around_span(body, match.start(), match.end()))
            for match in cls._RECORD_COVERAGE_DATE_SLASH_PATTERN.finditer(body):
                month, day = int(match.group(1)), int(match.group(2))
                if 1 <= month <= 12 and 1 <= day <= 31:
                    add(f"{month}/{day}", cls._snippet_around_span(body, match.start(), match.end()))
            for match in cls._RECORD_COVERAGE_WEEKDAY_PATTERN.finditer(body):
                add(f"週{match.group(1)}", cls._snippet_around_span(body, match.start(), match.end()))
        return items

    @staticmethod
    def _date_canonical_is_covered(canonical: str, folded_record: str) -> bool:
        """日期候選的等價覆蓋判定（折疊後紀錄；設計 §3 等價展開）。

        `11月1日 ≡ 11月1號 ≡ 11/1`（實測 B2/B1 寫月日式、C1/D1 寫斜線式，
        不展開必產生假陽性）、`10月14日 ≡ 10/14`、月底＝`M月底`、
        週幾＝`下週一 ≡ 下星期一 ≡ 下個禮拜一`（`日↔天` 為對稱保險展開，
        本語料無實例）。lookaround 保證數字邊界（`11/1` 不得被 `11月10日` 洗白）。
        """
        if not canonical or not folded_record:
            return False
        if canonical.endswith("月底"):
            month = re.escape(canonical[: -len("月底")])
            return re.search(rf"(?<!\d){month}\s*月\s*底", folded_record) is not None
        if canonical.startswith("週"):
            day = canonical[1:]
            day_class = "[日天]" if day in ("日", "天") else re.escape(day)
            return (
                re.search(
                    rf"(?:下\s*(?:個)?\s*)?(?:週|周|星期|禮拜)\s*{day_class}",
                    folded_record,
                )
                is not None
            )
        if "/" in canonical:
            month, day = (re.escape(part) for part in canonical.split("/", 1))
            slash_hit = re.search(
                rf"(?<![\d/]){month}\s*/\s*{day}(?![\d/])", folded_record
            )
            month_day_hit = re.search(
                rf"(?<!\d){month}\s*月\s*{day}\s*[日號号]?(?!\d)", folded_record
            )
            return slash_hit is not None or month_day_hit is not None
        return canonical in folded_record

    def _coverage_categories(self) -> set:
        """本波生效的對帳類別（settings.LOCAL_LLM_RECORD_COVERAGE_CATEGORIES；交集過濾）。"""
        raw = getattr(settings, "LOCAL_LLM_RECORD_COVERAGE_CATEGORIES", "topic,decision,number,date") or ""
        requested = {part.strip().lower() for part in raw.split(",") if part.strip()}
        return requested & {"topic", "decision", "number", "date"}

    def _validate_record_source_coverage(
        self,
        summary: str,
        notes: str,
        transcript: str,
        template: Optional[MeetingTemplate] = None,
    ) -> list:
        """P4-A：逐條對帳（議題／決議／數字／日期）→ 補強問題清單（只回報、不改寫、不刪句）。

        mode 語意（`settings.LOCAL_LLM_RECORD_COVERAGE_MODE`）：
        - `off`：完全不跑（不記 log／不記 metrics）＝一行回本波前 byte 級行為；
        - `observe`：照算＋log＋metrics，但 issues 不 append（品質零變化）；
        - `enforce`（預設）：issues append 進既有補強迴圈（不收斂保護不變）。
        每類別最多一條問題字串（首現序、每項附原文片段 ≤40 字、超出以
        「其餘 N 項」帶過）；空期望集合一律 log.warning ＋ `cov_expected_*=0`。
        """
        mode = (getattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "enforce") or "enforce").strip().lower()
        if mode == "off":
            # off＝完全不跑：連 metrics 欄位都不得出現（byte 級回本波前）。
            self._record_coverage_stats = {}
            return []

        stats: dict = {}
        self._record_coverage_stats = stats
        categories = self._coverage_categories()
        cleaned = self._clean_ollama_output(summary)
        normalized_summary = self._normalize_action_key(cleaned)
        local_sentences = self._split_record_sentences(cleaned)
        folded_record = self._fold_record_for_number_matching(cleaned)
        try:
            item_limit = int(
                getattr(settings, "LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT", None)
                or self.RECORD_COVERAGE_ITEM_PREVIEW_LIMIT
            )
        except (TypeError, ValueError):
            item_limit = self.RECORD_COVERAGE_ITEM_PREVIEW_LIMIT
        issues: list = []

        def _assemble_issue(category_label: str, missing_items: list, tail: str) -> str:
            preview = "、".join(missing_items[:item_limit])
            remainder = len(missing_items) - item_limit
            suffix = f"…（其餘 {remainder} 項）" if remainder > 0 else ""
            return f"{category_label}遺漏 {len(missing_items)} 項：{preview}{suffix}；{tail}"

        # 類別一／二：議題、決議（取萃取筆記；重用既有比對器與兩道守衛）
        for category, label, extractor, tail in (
            (
                "topic",
                "議題",
                self._extract_notes_topic_items,
                "這些議題都出現在萃取筆記的「議題與決議」中，請在紀錄正文逐項補寫"
                "（保留立場與理由），不得只以概括敘述帶過",
            ),
            (
                "decision",
                "決議",
                self._extract_notes_decision_items,
                "請把對應決議寫進紀錄正文並保留原文的單位、期限與數字，不得只以概括敘述帶過",
            ),
        ):
            if category not in categories:
                continue
            expected_items = extractor(notes)
            stats[f"expected_{category}"] = len(expected_items)
            label_by_key: dict = {}
            ordered_keys: list = []
            for item in expected_items:
                key = self._normalize_action_key(item)
                if not key:
                    continue
                label_by_key.setdefault(key, item)
                ordered_keys.append(key)
            missing_keys, _ratios = self._find_missing_action_keys(
                set(ordered_keys), normalized_summary, local_sentences=local_sentences
            )
            missing_labels = [label_by_key[key] for key in ordered_keys if key in missing_keys]
            stats[f"missing_{category}"] = len(missing_labels)
            if not expected_items:
                log.warning(
                    "紀錄覆蓋率檢查：{}期望集合為空（來源：萃取筆記「議題與決議」區塊）→ "
                    "本類別不產生補強問題；請確認筆記格式，或是否只剩佔位列",
                    label,
                )
            elif missing_labels:
                log.info(
                    "紀錄覆蓋率比對（{}）：未涵蓋 {} 項：{}",
                    label,
                    len(missing_labels),
                    "、".join(missing_labels[:item_limit]),
                )
                issues.append(_assemble_issue(label, missing_labels, tail))

        # 類別三：數字（取逐字稿；比對前先剝來源標註＋NFKC＋去千分位逗號）
        if "number" in categories:
            expected_numbers = self._scan_transcript_number_items(transcript)
            stats["expected_number"] = len(expected_numbers)
            missing_numbers = []
            for literal, snippet in expected_numbers:
                folded_literal = unicodedata.normalize("NFKC", literal).replace(",", "").replace(" ", "")
                if folded_literal and folded_literal in folded_record:
                    continue
                missing_numbers.append((literal, snippet))
            stats["missing_number"] = len(missing_numbers)
            if not expected_numbers:
                log.warning(
                    "紀錄覆蓋率檢查：數字期望集合為空（來源：逐字稿段落列）→ "
                    "本類別不產生補強問題；請確認逐字稿為「[start-end] 發言者：」段落列格式"
                )
            elif missing_numbers:
                log.info(
                    "紀錄覆蓋率比對（數字）：未涵蓋 {} 項：{}",
                    len(missing_numbers),
                    "、".join(literal for literal, _ in missing_numbers[:item_limit]),
                )
                issues.append(
                    _assemble_issue(
                        "數字",
                        [f"{literal}（原文「{snippet}」）" for literal, snippet in missing_numbers],
                        "請依逐字稿原文把數字補進對應段落，不得改寫為概數或省略",
                    )
                )

        # 類別四：日期（取逐字稿；覆蓋判定含等價展開）
        if "date" in categories:
            expected_dates = self._scan_transcript_date_items(transcript)
            stats["expected_date"] = len(expected_dates)
            missing_dates = [
                (canonical, snippet)
                for canonical, snippet in expected_dates
                if not self._date_canonical_is_covered(canonical, folded_record)
            ]
            stats["missing_date"] = len(missing_dates)
            if not expected_dates:
                log.warning(
                    "紀錄覆蓋率檢查：日期期望集合為空（來源：逐字稿段落列）→ "
                    "本類別不產生補強問題；請確認逐字稿為「[start-end] 發言者：」段落列格式"
                )
            elif missing_dates:
                log.info(
                    "紀錄覆蓋率比對（日期）：未涵蓋 {} 項：{}",
                    len(missing_dates),
                    "、".join(canonical for canonical, _ in missing_dates[:item_limit]),
                )
                issues.append(
                    _assemble_issue(
                        "日期",
                        [f"{canonical}（原文「{snippet}」）" for canonical, snippet in missing_dates],
                        "請依逐字稿原文寫入對應段落，年份未提及時寫「（待確認）」",
                    )
                )

        # enforce 時本數即實際併入數；observe 時為「若 enforce 會併入的數量」（觀測值）——
        # 兩種模式都照算，observe 只是不把 issues 交給呼叫端（品質零變化）。
        stats["issues_added"] = len(issues)
        return issues if mode == "enforce" else []

    def _record_coverage_metrics_fields(self) -> str:
        """pipeline metrics 行的 `cov_*` 欄位（供 run_owned_e2e 解析）。

        `off` 或未執行＝空字串（呼叫端用 f-string 串接，空字串＝byte 級不變）；
        `observe`／`enforce` 一律附上三鍵 legacy 之外的觀測欄位（新鍵為 additive，
        既有三鍵與解析樣式不動）。
        """
        stats = getattr(self, "_record_coverage_stats", None) or {}
        keys = (
            "expected_topic",
            "missing_topic",
            "expected_decision",
            "missing_decision",
            "expected_number",
            "missing_number",
            "expected_date",
            "missing_date",
            "issues_added",
        )
        if not any(key in stats for key in keys):
            return ""
        return " ".join(f"cov_{key}={int(stats.get(key, 0))}" for key in keys) + " "

    def _validate_record_fidelity(
        self,
        summary: str,
        transcript: str,
        template: Optional[MeetingTemplate] = None,
    ) -> list:
        """P4-B 忠實度絆索接線（A 自創專名／B 無依據歸屬／C 數字單位）。

        凍結介面（§4.1）＝`backend.core.fidelity_checks.analyze_fidelity(
        record_text, transcript_text, template_id)`；回傳 `problems` **原樣**併入
        既有補強問題清單（不改寫、不刪句、不新增提示詞）。fail-soft 契約：
        - `LOCAL_FIDELITY_TRIPWIRES=False` 時完全不呼叫（byte 級回本波前）；
        - 檢查模組尚未落地（W2 平行開發中）或任何例外 → log.warning ＋ 回 []，
          絕不影響主流程（lazy import，避免 import 期耦合）。
        """
        if not getattr(settings, "LOCAL_FIDELITY_TRIPWIRES", True):
            return []
        if not transcript:
            return []
        try:
            from backend.core import fidelity_checks
        except Exception as exc:  # pragma: no cover - 取決於 W2 是否已落地
            log.warning(
                "忠實度絆索已啟用但檢查模組不可用（{}；fail-soft，不影響主流程）",
                describe_exception(exc),
            )
            return []
        try:
            report = fidelity_checks.analyze_fidelity(
                summary, transcript, template_id=getattr(template, "id", None)
            )
        except Exception:
            log.exception("忠實度檢查器異常（fail-soft，不影響主流程）")
            return []
        problems = report.get("problems") if isinstance(report, dict) else None
        if not problems:
            return []
        return [problem for problem in problems if isinstance(problem, str) and problem.strip()]

    def _validate_cloud_speaker_traceability(
        self, summary: str, template: Optional[MeetingTemplate] = None
    ) -> list[str]:
        """確定性檢查：雲端最終紀錄是否保留了發言來源（2026-09-14）。

        設計立場：發言歸屬的保證不能只靠提示詞、更不能靠第二個 LLM 判定
        （研究設計文件 §4.2 的 V1/V3 原則）。本檢查是最輕量的絆索
        （tripwire）：只要正文出現任一「（來源，HH:MM:SS）」標註即通過，
        完全沒有才回報問題並觸發既有補強輪——用來攔住「模型把來源資訊
        整段省略」這種實測確實發生過的失效模式。

        刻意排除開頭欄位（時間／地點／主持人／出席人員）與彙整表列：
        前者本來就不該出現發言者標籤，後者是四欄固定表格；
        模型只把標籤寫在這些地方不算數（實測 Gemini 對照組就是如此）。

        v4.8.0 起地端流程亦套用（同一份契約）：雲端紀錄的發言來源標註 25 處、
        地端兩版各 0 處，是三方比對中最大的單一缺口，且它同時是防止「無出處
        內容」被寫進正式紀錄的最後一道確定性絆索。旗標未開啟的模板（如 general）
        與未提供逐字稿的路徑行為不變。
        """
        if template is None or not template.speaker_traceability:
            return []

        cleaned = self._clean_ollama_output(summary)
        for line in cleaned.splitlines():
            stripped = line.strip()
            if not stripped or "|" in stripped:
                continue
            if self._RECORD_HEADER_FIELD_PATTERN.match(stripped):
                continue
            if self._SOURCE_TAG_PATTERN.search(stripped):
                return []
        return [
            "缺少發言來源標註：正文各項指示、裁示、交辦與他人意見必須在句末加註"
            "「（發言者N，00:12:04）」或「（科長，00:12:04）」，不得整體省略發言歸屬"
        ]

    @classmethod
    def _extract_year_tokens(cls, text: str) -> set[str]:
        """抽取文字中的年份數字（阿拉伯數字＋國字）並正規化，供日期依據絆索比對。

        「年」後面接著「代」時不算年份：「90 年代」是年代敘述，排除後才不會把逐字稿與
        紀錄對同一件事的不同寫法（90 年代／九〇年代）誤判成杜撰。國字年份
        （一一三年／一百一十三年度）換算成數字後與阿拉伯數字等價比對。
        """
        years: set[str] = set()
        if not text:
            return years
        years.update(match.group(1) for match in cls._ARABIC_YEAR_PATTERN.finditer(text))
        for match in cls._CHINESE_YEAR_PATTERN.finditer(text):
            digits = cls._chinese_year_to_digits(match.group(1))
            if digits:
                years.add(digits)
        return years

    @classmethod
    def _chinese_year_to_digits(cls, token: str) -> Optional[str]:
        """國字年份轉數字：支援逐位唸法（一一三／二〇二六）與單位唸法（一百一十三）。"""
        if all(char in cls._CHINESE_DIGITS for char in token):
            return "".join(str(cls._CHINESE_DIGITS[char]) for char in token)
        total = 0
        section = 0
        for char in token:
            if char in cls._CHINESE_DIGITS:
                section = cls._CHINESE_DIGITS[char]
            elif char == "十":
                total += (section or 1) * 10
                section = 0
            elif char == "百":
                total += (section or 1) * 100
                section = 0
            else:
                return None
        total += section
        return str(total) if total else None

    def _validate_cloud_date_grounding(self, summary: str, transcript: str) -> list[str]:
        """確定性絆索：紀錄裡的年份必須在逐字稿出現過（2026-09-14）。

        實測失效模式：逐字稿只說「生效日期是今年的 11 月 1 號」、全篇沒有任何年份，
        Gemini 仍在正式紀錄寫入「中華民國113年…」與「生效日期為113年11月1日」——
        這是公文等級的事實錯誤，也不是提示詞能保證的（同一支音檔當日多次實測 7/8 次
        出現同類現象）。比對方式：兩份文字各自抽出年份數字後取差集，逐字稿沒有、
        紀錄卻出現的年份即回報問題並觸發既有補強輪（fail-soft：輪數用盡僅記 log）。

        只檢查年份：月份與日期在逐字稿裡常以相對說法出現（「這個月」「月底」），
        硬攔會誤判合法表達，因此交由 RECORD_DATE_GROUNDING_RULE 要求標「（待確認）」。
        v4.8.0 起地端流程亦套用（同一份契約）。
        """
        fabricated = sorted(
            self._extract_year_tokens(summary) - self._extract_year_tokens(transcript)
        )
        if not fabricated:
            return []
        return [
            "紀錄出現逐字稿沒有依據的年份："
            + "、".join(f"{year}年" for year in fabricated)
            + "；逐字稿未提到的年份一律寫「（待確認）」，不得由「今年／明年／去年」推算"
        ]

    @staticmethod
    def _contains_simplified_chinese(text: str) -> bool:
        """偵測簡體字漂移（P1-2：改用 OpenCC 全字覆蓋，取代 45 字硬編碼表）。"""
        from backend.core.text_postprocess import contains_simplified_chinese

        return contains_simplified_chinese(text)

    @staticmethod
    def _contains_non_markdown_leakage(text: str) -> bool:
        """偵測思考標籤、HTML/XML 或多餘 code fence。"""
        if not text:
            return False

        leakage_patterns = [
            r"<(?:think|thought|details)\b",
            r"</(?:think|thought|details)>",
            r"<[/!]?[A-Za-z][^>]*>",
            r"```",
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in leakage_patterns)

    @staticmethod
    def _contains_english_or_rubric_leakage(text: str) -> bool:
        """偵測英文前言/分析、回吐的評估標準、方括號模板殘留與整行英文。

        會議紀錄應為純繁體中文公文；模型若輸出英文推理段（如
        "Analysis of the Transcript"）、原樣回吐提示詞的「評估標準」，或殘留
        「[請從文本中提取…]」模板，皆視為洩漏，交由 refine 流程要求重寫。
        """
        if not text:
            return False

        leakage_patterns = [
            # 英文分析/前言慣用語
            r"\bAnalysis of the Transcript\b",
            r"\bEvaluation Criteria\b",
            r"\bMeeting (?:Name|Time|Location)\s*[:：]",
            r"\bLet'?s\s+(?:infer|name|call|assume)\b",
            r"\bA suitable name\b",
            r"\bNot (?:explicitly )?stated\b",
            # 回吐本提示詞的評估標準小節
            r"評估標準",
            r"法制合規性",
            r"權責明確度",
            r"意見真實性",
            # 方括號模板殘留（提示詞改寫後不應再出現）
            r"\[請從文本中提取",
            r"\[請填寫",
        ]
        if any(re.search(p, text, flags=re.IGNORECASE) for p in leakage_patterns):
            return True

        # 啟發式：整行英文（單行英文單字 >= 6 且幾乎無中日韓字），用以攔截
        # 提示詞未列舉到的英文敘述段；標題/清單/表格/引言行先排除以免誤殺技術名詞。
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("|", "-", "*", "#", ">")):
                continue
            english_words = len(re.findall(r"[A-Za-z]+", stripped))
            cjk_chars = len(re.findall(r"[㐀-鿿]", stripped))
            if english_words >= 6 and cjk_chars <= 2:
                return True
        return False

    @staticmethod
    def _empty_extraction_notes() -> str:
        """回傳最小可用的萃取筆記骨架。"""
        return """# 萃取筆記

## 1. 會議資訊
- **日期**：逐字稿未提及
- **參與者**：逐字稿未提及
- **會議主題**：逐字稿未提及

## 2. 議題與決議
- **議題**：逐字稿未提及
  - *討論重點*：逐字稿未提及
  - *決議*：（待確認）

## 3. 待辦清單
| 待辦事項 | 負責人 | 期限 | 依據 |
| :--- | :--- | :--- | :--- |
| （未於本段確認） | — | — | — |

## 4. 待確認資訊
- 無"""

    def _build_chunk_extraction_message(self, chunk: str, chunk_index: int, total_chunks: int) -> str:
        """建立單塊逐字稿的萃取訊息。"""
        return f"""以下是會議逐字稿第 {chunk_index}/{total_chunks} 段。

請特別留意：
- 任何明確交辦（例如：請、需要、要、應、麻煩、負責、於某日前完成）
- 日期、期限、數字、責任人、決議與後續追蹤
- 設備、人力、新聞稿、餐盒、飲料、拍照流程、場地借用、場勘等籌備工作都要視為獨立待辦
- 若同一事項在多段重複出現，先照實記錄，不要提前刪除

逐字稿內容：
{chunk}"""

    def _build_notes_merge_message(
        self,
        notes_group: list[str],
        round_index: int,
        total_groups: int,
        visible_target_tokens: Optional[int] = None,
    ) -> str:
        """建立多份萃取筆記的合併訊息（明示 merge 可見 token 目標，RC-1）。"""
        combined = "\n\n---\n\n".join(
            f"### 筆記 {index}\n{notes}"
            for index, notes in enumerate(notes_group, start=1)
        )
        target_line = (
            f"\n本次整併的可見長度目標：整合結果約 {visible_target_tokens} tokens 以內，"
            "請在不遺漏任何決議／待辦的前提下壓縮重複內容。"
            if visible_target_tokens
            else ""
        )
        return f"""以下是第 {round_index} 輪整併要處理的 {len(notes_group)} 份萃取筆記（本輪共 {total_groups} 組）：

{combined}

請輸出單一份整合後的「# 萃取筆記」Markdown，保留所有重要待辦與決議。{target_line}"""

    @staticmethod
    def _template_generation_extra(template: Optional[MeetingTemplate]) -> str:
        """模板的生成階段增補要求（無模板或無增補時回空字串）。"""
        if template and template.generation_message_extra:
            return template.generation_message_extra
        return ""

    @classmethod
    def _speaker_traceability_rule(cls, template: Optional[MeetingTemplate]) -> str:
        """發言來源標註規則行（模板未開啟時回空字串）。

        雲端與地端（v4.8.0 起）共用同一份規則；是否注入只由
        template.speaker_traceability 決定。地端生成／補強訊息另於 mode="local"
        時追加來源標註位置導引（LOCAL_SOURCE_TAG_PLACEMENT_RULE），雲端不變。
        """
        if template is not None and template.speaker_traceability:
            return cls.CLOUD_SPEAKER_TRACEABILITY_RULE
        return ""

    @classmethod
    def _local_tag_placement_rule(cls, mode: str, speaker_rule: str) -> str:
        """地端專用的來源標註位置導引列（W2）；雲端（mode 非 local）回空字串。

        只在發言來源標註契約已注入（speaker_rule 非空）時追加；前後各補一個
        換行，讓導引自成完整行，不會黏在既有規則行或「萃取筆記：」標籤上。
        """
        if mode != "local" or not speaker_rule:
            return ""
        return "\n" + cls.LOCAL_SOURCE_TAG_PLACEMENT_RULE + "\n"

    def _build_record_generation_message(
        self,
        extracted_notes: str,
        transcript: Optional[str] = None,
        template: Optional[MeetingTemplate] = None,
        mode: str = "cloud",
    ) -> str:
        """最終會議記錄生成訊息（地端與雲端共用；v4.8.0）。

        transcript 有值時＝「萃取筆記（涵蓋檢查表）＋原始逐字稿（細節來源）」雙輸入，
        與雲端既有行為同構；transcript 為 None／空字串時＝只餵筆記，是地端在
        context 餘裕不足時的降級路徑（內容與 v4.7.4 的地端路徑相同）。

        mode="local"（僅地端呼叫端傳入）追加來源標註位置導引；預設 "cloud" 的
        輸出與 v4.8.0 完全相同。

        背景（實測對照雲端 Gemini 基準）：雲端生成階段同時看到逐字稿，各單位立場、
        理由、數據、案例與專有名詞都能回原文核對；地端原本只看到被整併壓縮過的
        筆記，在生成之前就已永久丟掉未進筆記的細節。
        """
        has_transcript = bool(transcript and transcript.strip())
        speaker_rule = self._speaker_traceability_rule(template)
        tag_placement_rule = self._local_tag_placement_rule(mode, speaker_rule)
        detail_rule = (
            "- 原始逐字稿是細節來源：各單位意見、決議與裁示須保留具體理由、數據、"
            "案例、統一口徑與執行方式，嚴禁把多句實質討論壓縮成一句籠統敘述\n"
            if has_transcript
            else ""
        )
        source_label = "萃取筆記與原始逐字稿" if has_transcript else "萃取筆記"
        transcript_block = f"\n\n原始逐字稿：\n{transcript}" if has_transcript else ""
        return f"""請根據以下「{source_label}」，輸出最終版本的會議記錄。

要求：
- 萃取筆記是涵蓋度檢查表：筆記中的每個議題、決議、待辦都必須出現在會議記錄中
{detail_rule}- 所有明確待辦都必須出現在待辦事項中；不要把多個不同待辦合併成單一籠統項目，可分列追蹤者請拆成多列
- 若資訊不足，請標示「（待確認）」或「逐字稿未提及」
- 只輸出最終 Markdown，不要附加說明
- 全文必須使用繁體中文（台灣用語），不要輸出簡體中文或任何  thinking / <thought> / <details> / XML / HTML 標籤{self._template_generation_extra(template)}
{self.RECORD_DATE_GROUNDING_RULE}
{speaker_rule}{tag_placement_rule}萃取筆記：
{extracted_notes}{transcript_block}"""

    def _build_summary_from_notes_message(
        self,
        extracted_notes: str,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """建立最終會議記錄生成訊息（只餵筆記的降級路徑）。"""
        return self._build_record_generation_message(extracted_notes, None, template=template)

    def _build_record_refinement_message(
        self,
        current_summary: str,
        extracted_notes: str,
        issues: list[str],
        transcript: Optional[str] = None,
        template: Optional[MeetingTemplate] = None,
        mode: str = "cloud",
    ) -> str:
        """摘要補強訊息（地端與雲端共用；v4.8.0）。

        補強的目的是補回缺漏的細節；沒有逐字稿的補強只能就筆記改寫措辭
        （雲端已於 v4.3.3 用逐字稿解決同一問題，地端 v4.8.0 對齊）。
        transcript 為 None／空字串時即為過去地端／雲端的筆記限定補強。

        mode="local"（僅地端呼叫端傳入）追加來源標註位置導引；預設 "cloud" 的
        輸出與 v4.8.0 完全相同。
        """
        has_transcript = bool(transcript and transcript.strip())
        speaker_rule = self._speaker_traceability_rule(template)
        tag_placement_rule = self._local_tag_placement_rule(mode, speaker_rule)
        transcript_block = (
            f"\n原始逐字稿（補充細節時以此為準）：\n{transcript}" if has_transcript else ""
        )
        issue_lines = "\n".join(f"- {issue}" for issue in issues)
        return f"""你剛剛輸出的會議記錄仍有缺口，請根據問題清單重新輸出完整版本，不要只輸出修補片段。

問題清單：
{issue_lines}

目前版本：
{current_summary}

請重新參考以下萃取筆記，完整重寫最終會議記錄：
{extracted_notes}

額外要求：
- 全文必須使用繁體中文（台灣用語）
- 只能輸出最終 Markdown
- 不要輸出  thinking、<thought>、<details>、XML/HTML 標籤或 code fence
- 條列編號須依系統提示詞規定之階層（一、→（一）→1、……）由上而下使用，不得用「-」「•」或跳層{self._template_generation_extra(template)}
{self.RECORD_DATE_GROUNDING_RULE}
{speaker_rule}{tag_placement_rule}{transcript_block}"""

    def _build_refinement_message(
        self,
        current_summary: str,
        extracted_notes: str,
        issues: list[str],
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """建立摘要補強訊息（只餵筆記的降級路徑）。"""
        return self._build_record_refinement_message(
            current_summary, extracted_notes, issues, None, template=template
        )

    def _build_cloud_summary_message(
        self,
        extracted_notes: str,
        transcript: str,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """雲端最終生成訊息（v4.3.3 契約；v4.8.0 起與地端共用同一 builder）。"""
        return self._build_record_generation_message(extracted_notes, transcript, template=template)

    def _build_cloud_refinement_message(
        self,
        current_summary: str,
        extracted_notes: str,
        issues: list[str],
        transcript: str,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """雲端補強訊息（v4.3.3 契約；v4.8.0 起與地端共用同一 builder）。"""
        return self._build_record_refinement_message(
            current_summary, extracted_notes, issues, transcript, template=template
        )

    def _group_texts_by_budget(self, texts: list[str], budget_tokens: int) -> list[list[str]]:
        """將多段文字依 token 預算分組。"""
        groups: list[list[str]] = []
        current_group: list[str] = []
        current_tokens = 0

        for text in texts:
            text_tokens = self._estimate_tokens(text)
            if current_group and current_tokens + text_tokens > budget_tokens:
                groups.append(current_group)
                current_group = [text]
                current_tokens = text_tokens
            else:
                current_group.append(text)
                current_tokens += text_tokens

        if current_group:
            groups.append(current_group)

        return groups

    async def _merge_notes_until_fit(
        self,
        engine: str,
        extracted_notes: list[str],
        merge_visible_target_tokens: int,
        progress_callback: Optional[callable] = None,
        context_window_tokens: Optional[int] = None,
        lmstudio_selection: Optional[LMStudioModelSelection] = None,
        merge_input_budget_tokens: Optional[int] = None,
        merge_provider_output_tokens: Optional[int] = None,
        merge_feasible_input_tokens: Optional[int] = None,
    ) -> str:
        """反覆整併 chunk 筆記，直到可被最終摘要步驟安全承接（RC-1/RC-3）。

        merge 預算語意分離（CHANGE_MAP 1）：
        - ``merge_input_budget_tokens``：一組可攜帶的來源 notes 上限（分組用）。
        - ``merge_visible_target_tokens``：合併後 notes 必須收斂到的可見目標；
          merge prompt 明示此目標，provider ``max_tokens`` 不使用它。
        - ``merge_provider_output_tokens``：provider 初始 completion cap；
          hidden reasoning 吃掉預算時由有界 semantic recovery 依
          headroom/configured-cap 公式有限增加（allow_reasoning_retry 單獨決定）。

        回應超過可見目標時視為下一輪待壓縮 note（單份 oversized note 允許單獨
        compaction）；每輪必須減少 note 數或 estimated total tokens；達輪數上限
        或無實質進度時拋 ``LOCAL_LLM_MERGE_NOT_CONVERGED``。CORE merge path
        不使用 hard truncation——不得省略尾端來源內容偽造成功。

        終止條件（T20260922-1349-01 RC-1b）：整併的真正契約是「merge 後的筆記
        能被最終生成階段安全承接」，不是「縮到某個與 context 無關的常數」。因此
        除了可見目標外，另接受 ``merge_feasible_input_tokens``（下游可承接的硬性
        上限）：當只剩單一 note、已無分組可再壓縮，而該 note 仍在下游預算內時即
        視為已收斂並回傳（僅記錄 warning），不因未達軟性目標而 veto 整份紀錄。
        真正超出下游預算時仍 fail loudly 拋 ``LOCAL_LLM_MERGE_NOT_CONVERGED``。
        """
        current_notes = [self._clean_ollama_output(note) for note in extracted_notes if note and note.strip()]
        if not current_notes:
            return self._empty_extraction_notes()

        provider_output_cap = merge_provider_output_tokens or settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS
        if merge_input_budget_tokens is None:
            context_budget = context_window_tokens or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS
            merge_input_budget_tokens = max(
                merge_visible_target_tokens,
                context_budget
                - provider_output_cap
                - (self._estimate_tokens(self.LOCAL_NOTES_MERGE_PROMPT) + 250),
            )

        # 收斂保護（RC-3）：整併必須確定性收斂。三重防線：輪數上限、
        # 「note 數或總 tokens 必須減少」的進度證明、非收斂時拋 stable error
        # 走既有逐字稿 fallback。禁止以 hard truncation 偽造成功。
        feasible_input_tokens = (
            merge_feasible_input_tokens
            if merge_feasible_input_tokens is not None
            else merge_visible_target_tokens
        )
        round_index = 1
        previous_total_tokens: Optional[int] = None
        previous_note_count: Optional[int] = None
        while True:
            total_tokens = sum(self._estimate_tokens(note) for note in current_notes)
            if len(current_notes) == 1 and total_tokens <= merge_visible_target_tokens:
                break
            if len(current_notes) == 1 and total_tokens <= feasible_input_tokens:
                # 不可再分組，且下游仍可承接 → 視為已收斂（不得以此 veto 整份紀錄）
                log.warning(
                    "整併筆記未達可見目標但下游可承接，停止整併：{} tokens > 目標 {} tokens"
                    "（下游可承接上限 {} tokens，context window {} tokens）",
                    total_tokens,
                    merge_visible_target_tokens,
                    feasible_input_tokens,
                    context_window_tokens or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS,
                )
                break
            if round_index > settings.LOCAL_LLM_MAX_MERGE_ROUNDS:
                raise StableServiceError(
                    LOCAL_LLM_MERGE_NOT_CONVERGED,
                    f"萃取筆記整併在 {settings.LOCAL_LLM_MAX_MERGE_ROUNDS} 輪內未收斂到下游可承接的"
                    f"輸入預算（目前 {len(current_notes)} 份筆記、{total_tokens} tokens > 可見目標 "
                    f"{merge_visible_target_tokens} tokens 且 > 下游可承接上限 "
                    f"{feasible_input_tokens} tokens）。為保留全部來源事實（含尾端決議／待辦），"
                    "已停止整併並回退為明示逐字稿 fallback；請調大 context window 或提高 "
                    "LOCAL_LLM_MAX_MERGE_ROUNDS 後重試",
                )
            if previous_total_tokens is not None:
                notes_reduced = (
                    previous_note_count is not None and len(current_notes) < previous_note_count
                )
                tokens_reduced = total_tokens < previous_total_tokens
                if not notes_reduced and not tokens_reduced:
                    raise StableServiceError(
                        LOCAL_LLM_MERGE_NOT_CONVERGED,
                        f"萃取筆記整併無實質進度（{previous_total_tokens} → {total_tokens} tokens，"
                        f"{previous_note_count} → {len(current_notes)} 份），於第 {round_index} 輪前"
                        "停止。為保留全部來源事實（含尾端決議／待辦），已回退為明示逐字稿 "
                        "fallback；請確認模型輸出品質或調大 context window",
                    )
            previous_total_tokens = total_tokens
            previous_note_count = len(current_notes)

            note_groups = self._group_texts_by_budget(current_notes, merge_input_budget_tokens)
            self._merge_rounds_used = round_index
            self._merge_groups_last_round = len(note_groups)
            merged_round: list[str] = []
            for group_index, note_group in enumerate(note_groups, start=1):
                self._emit_progress(
                    progress_callback,
                    min(84.0, 75.0 + group_index),
                    f"整併萃取筆記 第{round_index}輪 {group_index}/{len(note_groups)}..."
                )
                merged = await self._generate_with_local_engine(
                    engine,
                    self.LOCAL_NOTES_MERGE_PROMPT,
                    self._build_notes_merge_message(
                        note_group,
                        round_index,
                        len(note_groups),
                        visible_target_tokens=merge_visible_target_tokens,
                    ),
                    temperature=0.1,
                    # provider completion cap 與可見目標分離（RC-1）：初始 cap 為
                    # merge_provider_output_tokens（reserved output），超出可見目標
                    # 的輸出交由下一輪 compaction，不以可見目標壓縮 max_tokens。
                    num_predict=provider_output_cap,
                    context_window_tokens=context_window_tokens,
                    lmstudio_selection=lmstudio_selection,
                    # Ollama 路徑維持不自動擴大 num_predict；LM Studio 的 semantic
                    # recovery 由 allow_reasoning_retry（預設 True）單獨決定。
                    expand_output_budget=False,
                )
                merged_round.append(self._clean_ollama_output(merged))

            current_notes = merged_round
            round_index += 1

        # 全量收斂或顯式失敗：不合併截斷路徑，尾端來源內容一律保留。
        return current_notes[0] if len(current_notes) == 1 else "\n\n".join(current_notes)

    async def _consolidate_notes(
        self,
        engine: str,
        extracted_notes: list[str],
        plan: "LocalContextPlan",
        progress_callback: Optional[callable] = None,
        context_window_tokens: Optional[int] = None,
        lmstudio_selection: Optional[LMStudioModelSelection] = None,
    ) -> str:
        """把多份萃取筆記收斂成最終生成階段可承接的一份（v4.8.0）。

        契約：**能不整併就不要整併**。整併是一次 LLM 改寫、必然有損——實測
        task `b20c90a7` 的 4 份筆記合計 8,176 tokens 在整併關卡被 3,072 的輸出上限
        截斷（`finish_reason=length`），最壞損失 62.4%，而流程把它視為「已收斂」
        靜默接受。既然該任務的 loaded instance 提供 128K context、下游可承接上限
        遠大於筆記總量，壓縮就沒有必要——改用零損串接（與雲端分段模式的
        `\n\n---\n\n` 串接同構；唯一的差別是少了跨塊去重，但重複只來自分塊
        overlap 的 220 tokens 邊界，代價遠小於整併截斷）。

        只有當筆記總量真的超出下游可承接上限（小 context 的 Ollama 路徑）時，
        才沿用既有 `_merge_notes_until_fit` 與它的收斂保護。
        """
        cleaned = [
            self._clean_ollama_output(note) for note in extracted_notes if note and note.strip()
        ]
        if not cleaned:
            return self._empty_extraction_notes()

        joined = "\n\n---\n\n".join(cleaned)
        total_tokens = self._estimate_tokens(joined)
        feasible = plan.merge_feasible_input_tokens or plan.merge_visible_target_tokens
        if settings.LOCAL_LLM_ZERO_LOSS_NOTES_PASSTHROUGH and total_tokens <= feasible:
            log.info(
                "萃取筆記零損串接（略過有損整併）：{} 份、{} tokens ≤ 下游可承接上限 {} tokens，"
                "context window {} tokens",
                len(cleaned),
                total_tokens,
                feasible,
                context_window_tokens or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS,
            )
            return joined

        log.info(
            "萃取筆記需整併：{} 份、{} tokens > 下游可承接上限 {} tokens",
            len(cleaned),
            total_tokens,
            feasible,
        )
        return await self._merge_notes_until_fit(
            engine,
            extracted_notes,
            plan.merge_visible_target_tokens,
            progress_callback,
            context_window_tokens=context_window_tokens,
            lmstudio_selection=lmstudio_selection,
            merge_input_budget_tokens=plan.merge_input_budget_tokens,
            merge_provider_output_tokens=plan.merge_provider_output_tokens,
            merge_feasible_input_tokens=plan.merge_feasible_input_tokens,
        )

    def _final_message_fits(
        self,
        system_prompt: str,
        user_message: str,
        context_window: Optional[int],
        minimum: Optional[int] = None,
    ) -> bool:
        """判斷某個生成訊息是否能在 context 內留下足夠的輸出空間（v4.8.0）。"""
        window = int(context_window or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS)
        reserve = int(
            minimum if minimum is not None else settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS
        )
        prompt_tokens = (
            self._estimate_tokens(system_prompt)
            + self._estimate_tokens(user_message)
            + 64
        )
        available = window - prompt_tokens - int(settings.LOCAL_LLM_CONTEXT_SAFETY_MARGIN_TOKENS)
        return available >= reserve

    def _resolve_final_generation_message(
        self,
        notes: str,
        transcript: str,
        system_prompt: str,
        context_window: Optional[int],
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """最終生成訊息：context 夠就附逐字稿（雙輸入），不夠就退回只餵筆記。

        本路徑只服務地端流程，兩條分支都帶 mode="local"（W2 來源標註位置導引）。
        """
        notes_only = self._build_record_generation_message(
            notes, None, template=template, mode="local"
        )
        if not settings.LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION or not transcript.strip():
            return notes_only
        dual = self._build_record_generation_message(
            notes, transcript, template=template, mode="local"
        )
        if self._final_message_fits(system_prompt, dual, context_window):
            return dual
        log.warning(
            "context window {} tokens 不足以在最終生成階段附上完整逐字稿，本次退回只餵萃取筆記"
            "（雙輸入需約 {} tokens 的 prompt）",
            context_window or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS,
            self._estimate_tokens(system_prompt) + self._estimate_tokens(dual),
        )
        return notes_only

    def _resolve_final_refinement_message(
        self,
        current_summary: str,
        notes: str,
        issues: list[str],
        transcript: str,
        system_prompt: str,
        context_window: Optional[int],
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """補強訊息：context 夠就附逐字稿（才能回原文補細節），不夠就退回只餵筆記。

        本路徑只服務地端流程，兩條分支都帶 mode="local"（W2 來源標註位置導引）。
        """
        notes_only = self._build_record_refinement_message(
            current_summary, notes, issues, None, template=template, mode="local"
        )
        if not settings.LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION or not transcript.strip():
            return notes_only
        dual = self._build_record_refinement_message(
            current_summary, notes, issues, transcript, template=template, mode="local"
        )
        if self._final_message_fits(system_prompt, dual, context_window):
            return dual
        log.warning(
            "context window {} tokens 不足以在補強階段附上完整逐字稿，本次退回只餵萃取筆記"
            "（雙輸入需約 {} tokens 的 prompt）",
            context_window or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS,
            self._estimate_tokens(system_prompt) + self._estimate_tokens(dual),
        )
        return notes_only

    def _truncate_to_token_budget(self, text: str, budget_tokens: int) -> str:
        """最後保底：仍超出預算時依行硬截斷（保留前段，行界不切半句）。"""
        if self._estimate_tokens(text) <= budget_tokens:
            return text

        kept_lines: list[str] = []
        used = 0
        for line in text.splitlines():
            line_tokens = self._estimate_tokens(line) + 1
            if used + line_tokens > budget_tokens:
                break
            kept_lines.append(line)
            used += line_tokens
        truncated = "\n".join(kept_lines).strip()
        log.warning(
            "整併筆記硬截斷：{} → {} tokens（預算 {}）；後段內容未進入最終生成",
            self._estimate_tokens(text), self._estimate_tokens(truncated), budget_tokens,
        )
        return truncated or text[: budget_tokens * 2]

    @staticmethod
    def _parse_lmstudio_loaded_instances(payload: object) -> list[_LoadedLMStudioInstance]:
        """解析 LM Studio native models response，只保留 loaded LLM instances。"""
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise StableServiceError(
                LMSTUDIO_UNREACHABLE,
                "LM Studio /api/v1/models 回應缺少 models 陣列",
            )

        loaded: list[_LoadedLMStudioInstance] = []
        for model in payload["models"]:
            if not isinstance(model, dict) or model.get("type") not in {"llm", "embedding"}:
                # 無法區分 model type 時停止，避免把未知類型誤當成可用 LLM。
                raise StableServiceError(
                    LMSTUDIO_UNREACHABLE,
                    "LM Studio /api/v1/models 含無法辨識的 model type",
                )
            if model.get("type") == "embedding":
                # embedding 永久排除，不參與 LLM 選擇。
                continue

            model_key = str(model.get("key") or "").strip()
            if not model_key:
                raise StableServiceError(
                    LMSTUDIO_UNREACHABLE,
                    "LM Studio /api/v1/models 的 LLM 缺少 key，無法安全選模",
                )

            raw_instances = model.get("loaded_instances")
            if raw_instances is None:
                raise StableServiceError(
                    LMSTUDIO_UNREACHABLE,
                    f"LM Studio model {model_key!r} 缺少 loaded_instances，無法安全選模",
                )
            if not isinstance(raw_instances, list):
                raise StableServiceError(
                    LMSTUDIO_UNREACHABLE,
                    f"LM Studio model {model_key!r} 的 loaded_instances 不是陣列",
                )

            for instance in raw_instances:
                if not isinstance(instance, dict):
                    raise StableServiceError(
                        LMSTUDIO_UNREACHABLE,
                        f"LM Studio model {model_key!r} 的 loaded instance 格式無法解析",
                    )
                instance_id = str(instance.get("id") or "").strip()
                if not instance_id:
                    raise StableServiceError(
                        LMSTUDIO_UNREACHABLE,
                        f"LM Studio model {model_key!r} 的 loaded instance 缺少 id",
                    )

                config = instance.get("config")
                if not isinstance(config, dict):
                    config = {}
                context_length = (
                    config.get("context_length")
                    or instance.get("context_length")
                    or model.get("max_context_length")
                )
                try:
                    context_length = int(context_length) if context_length is not None else None
                except (TypeError, ValueError):
                    context_length = None
                if context_length is not None and context_length <= 0:
                    context_length = None

                loaded.append(
                    _LoadedLMStudioInstance(
                        model_key=model_key,
                        instance_id=instance_id,
                        context_length=context_length,
                    )
                )
        return loaded

    @staticmethod
    def _make_lmstudio_selection(
        instance: _LoadedLMStudioInstance,
        inventory_timestamp: Optional[datetime] = None,
    ) -> LMStudioModelSelection:
        return LMStudioModelSelection(
            provider="lmstudio",
            # OpenAI-compatible LM Studio requests use the model key; the
            # loaded instance id remains available for deterministic diagnostics.
            model_identifier=instance.model_key,
            loaded_instance_id=instance.instance_id,
            context_length=instance.context_length,
            inventory_timestamp=inventory_timestamp or datetime.now(),
        )

    @staticmethod
    def _format_lmstudio_candidates(instances: list[_LoadedLMStudioInstance]) -> str:
        return ", ".join(
            f"{instance.model_key} (instance={instance.instance_id})"
            for instance in instances
        )

    def _selection_status_for_instances(
        self,
        instances: list[_LoadedLMStudioInstance],
        override: Optional[str],
    ) -> tuple[str, Optional[_LoadedLMStudioInstance]]:
        if override:
            matches = [
                instance
                for instance in instances
                if override in {instance.model_key, instance.instance_id}
            ]
            return ("ready", matches[0]) if len(matches) == 1 else (LMSTUDIO_MODEL_NOT_LOADED, None)
        if not instances:
            return LMSTUDIO_NO_LOADED_LLM, None
        if len(instances) != 1:
            return LMSTUDIO_MULTIPLE_LOADED_LLMS, None
        return "ready", instances[0]

    async def _fetch_lmstudio_loaded_instances(self) -> list[_LoadedLMStudioInstance]:
        """以有限重試讀取 LM Studio inventory；不呼叫 load/unload/JIT API。"""
        retries = max(int(settings.LOCAL_LLM_TRANSIENT_RETRIES), 0)
        for attempt in range(retries + 1):
            try:
                client = await self._get_lmstudio_http_client()
                response = await client.get("/api/v1/models")
                status_code = getattr(response, "status_code", None)
                if status_code != 200:
                    if status_code is not None and status_code >= 500 and attempt < retries:
                        await asyncio.sleep((attempt + 1) * settings.LOCAL_LLM_RETRY_BACKOFF_SECONDS)
                        continue
                    raise StableServiceError(
                        LMSTUDIO_UNREACHABLE,
                        f"LM Studio /api/v1/models 回應 HTTP {status_code}",
                    )
                instances = self._parse_lmstudio_loaded_instances(response.json())
                return instances
            except StableServiceError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                if attempt < retries:
                    await asyncio.sleep((attempt + 1) * settings.LOCAL_LLM_RETRY_BACKOFF_SECONDS)
                    continue
                raise StableServiceError(
                    LMSTUDIO_UNREACHABLE,
                    f"無法連線至 LM Studio：{describe_exception(exc)}",
                ) from exc
            except Exception as exc:  # noqa: BLE001 — malformed/transport boundary 統一失敗
                raise StableServiceError(
                    LMSTUDIO_UNREACHABLE,
                    f"LM Studio models API 失敗：{describe_exception(exc)}",
                ) from exc

        raise StableServiceError(LMSTUDIO_UNREACHABLE, "LM Studio models API 重試邏輯異常")

    async def _resolve_lmstudio_selection(self) -> LMStudioModelSelection:
        """在摘要工作開始時選模，並回傳 immutable selection。"""
        try:
            instances = await self._fetch_lmstudio_loaded_instances()
        except StableServiceError as exc:
            self._set_lmstudio_health(
                server_reachable=False,
                selection_status=exc.code,
                loaded_instances=[],
            )
            raise

        override = self._get_lmstudio_model_override()
        status, instance = self._selection_status_for_instances(instances, override)
        if status != "ready" or instance is None:
            self._set_lmstudio_health(
                server_reachable=True,
                selection_status=status,
                loaded_instances=instances,
            )
            if status == LMSTUDIO_NO_LOADED_LLM:
                raise StableServiceError(
                    status,
                    "LM Studio 目前沒有已載入的 LLM（embedding 不列入）；請載入恰一個 LLM",
                )
            if status == LMSTUDIO_MULTIPLE_LOADED_LLMS:
                raise StableServiceError(
                    status,
                    "LM Studio 有多個已載入 LLM，未任意選擇："
                    f"{self._format_lmstudio_candidates(instances)}；請設定 LMSTUDIO_MODEL 或只保留一個",
                )
            raise StableServiceError(
                LMSTUDIO_MODEL_NOT_LOADED,
                f"LMSTUDIO_MODEL override {override!r} 未唯一匹配已載入 LLM；"
                f"候選：{self._format_lmstudio_candidates(instances) or '無'}",
            )

        selection = self._make_lmstudio_selection(instance)
        self._active_lmstudio_selection = selection
        self._set_lmstudio_health(
            server_reachable=True,
            selection_status="ready",
            loaded_instances=instances,
            selected=selection,
        )
        return selection

    async def _select_local_engine(self) -> str:
        """選擇可用的本地 LLM 引擎，Mac auto 只走 LM Studio。"""
        self._active_lmstudio_selection = None
        provider = resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER)
        if provider == "lmstudio":
            selection = await self._resolve_lmstudio_selection()
            log.info(
                "使用 LM Studio 本地模式 (model={}, instance={})",
                selection.model_identifier,
                selection.loaded_instance_id,
            )
            return "lmstudio"

        if provider == "ollama":
            if await self.check_ollama_health():
                log.info("使用 Ollama 本地模式")
                return "ollama"
            if self._ollama_model_error:
                raise RuntimeError(self._ollama_model_error)
            raise RuntimeError("Ollama 服務不可用，請確認 Ollama 是否正在運行")

        # 非 Mac 的 auto 保留既有 Ollama 優先順序；LM Studio 只在 Ollama
        # 不可用時嘗試，且其 selection ambiguity 直接回報，不任意 fallback。
        if await self.check_ollama_health():
            log.info("使用 Ollama 本地模式")
            return "ollama"
        if self._ollama_model_error:
            raise RuntimeError(self._ollama_model_error)

        selection = await self._resolve_lmstudio_selection()
        log.info(
            "使用 LM Studio 本地模式 (model={}, instance={})",
            selection.model_identifier,
            selection.loaded_instance_id,
        )
        return "lmstudio"

    async def _generate_with_local_engine(
        self,
        engine: str,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None,
        temperature: float = 0.2,
        num_predict: Optional[int] = None,
        context_window_tokens: Optional[int] = None,
        expand_output_budget: bool = True,
        lmstudio_selection: Optional[LMStudioModelSelection] = None,
        allow_reasoning_retry: bool = True,
    ) -> str:
        """對選定的本地引擎執行一次生成。

        allow_reasoning_retry 僅作用於 LM Studio 路徑（Ollama 路徑忽略此
        參數，維持既有行為）；merge call（expand_output_budget=False）一律
        禁止 reasoning retry，維持整併輸出的物理上限＝caller cap（ADR-7/8）。
        """
        if engine == "ollama":
            return await self._summarize_with_ollama(
                system_prompt,
                user_message,
                progress_callback=progress_callback,
                temperature=temperature,
                num_predict=num_predict,
                context_window_tokens=context_window_tokens,
                expand_output_budget=expand_output_budget,
            )

        if engine == "lmstudio":
            return await self._summarize_with_lmstudio(
                system_prompt,
                user_message,
                progress_callback=progress_callback,
                temperature=temperature,
                max_tokens=num_predict,
                context_window_tokens=context_window_tokens,
                selection=lmstudio_selection,
                expand_output_budget=expand_output_budget,
                allow_reasoning_retry=allow_reasoning_retry,
            )

        raise RuntimeError(f"未知的本地引擎: {engine}")

    async def _summarize_with_local_pipeline(
        self,
        transcript: str,
        system_prompt: str,
        progress_callback: Optional[callable] = None,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """本地模式的 extraction-first + chunk-merge + refine 流程。"""
        engine = await self._select_local_engine()
        # LM Studio 選模只在工作開始時做一次；整個摘要工作沿用 immutable
        # selection，避免中途 inventory 變化導致不同階段偷偷換模型。
        lmstudio_selection = self._active_lmstudio_selection
        # CHANGE_MAP 4：structured metrics 起點（pipeline 級彙總於結束時輸出）
        self._lmstudio_logical_generations = 0
        self._lmstudio_semantic_attempts = 0
        self._lmstudio_network_retries = 0
        self._merge_rounds_used = 0
        self._merge_groups_last_round = 0
        pipeline_started = time.monotonic()
        # v4.7.0：任務級 num_ctx——warmup 自我修復失敗時降級，一次讀取、全程顯式傳遞
        context_tokens = self._effective_context_tokens()
        context_window_source = "settings"
        if lmstudio_selection and lmstudio_selection.context_length:
            # T20260922-1349-01 RC-3：LM Studio 的權威視窗是「本次選定 loaded
            # instance 的 context_length」——那是使用者已在 LM Studio 載入、伺服器
            # 實際提供的實體上限（本 app 不負責 load/unload，96e6e74 已立此方向）。
            # 舊行為的 min() 讓 settings 預設 8192 在模型提供 32K/128K 時反向成為
            # 瓶頸：規劃過度切塊、merge 分組預算過小 → 呼叫放大，並把整併推進
            # 輪數上限。instance context 較小（< settings）時結果與舊行為相同。
            context_tokens = lmstudio_selection.context_length
            context_window_source = "lmstudio_instance"
        # P4-C（W-2）：context 預算來源登錄於實例，供引擎層 log 對帳
        # （LM Studio＝instance context_length／Ollama＝settings，同一把尺）。
        self._context_window_source = context_window_source
        plan = self._build_local_context_plan(
            transcript, system_prompt, template=template,
            context_window_tokens=context_tokens,
        )
        log.info(
            "本地摘要上下文規劃："
            f"context_window={context_tokens}({context_window_source}), "
            f"estimated_tokens={plan.estimated_transcript_tokens}, "
            f"chunk_budget={plan.chunk_input_budget_tokens}, "
            f"merge_input_budget={plan.merge_input_budget_tokens}, "
            f"merge_visible_target={plan.merge_visible_target_tokens}, "
            f"merge_feasible_input={plan.merge_feasible_input_tokens}, "
            f"merge_provider_output={plan.merge_provider_output_tokens}, "
            f"needs_chunking={plan.needs_chunking}"
        )

        chunks = (
            self._split_transcript_into_chunks(transcript, plan.chunk_input_budget_tokens)
            if plan.needs_chunking
            else [transcript]
        )
        if not chunks:
            chunks = [transcript]

        extracted_notes: list[str] = []
        total_chunks = len(chunks)
        extraction_started = time.monotonic()
        for chunk_index, chunk in enumerate(chunks, start=1):
            progress = 68.0 + ((chunk_index - 1) / max(total_chunks, 1)) * 12.0
            self._emit_progress(progress_callback, progress, f"萃取逐字稿重點 {chunk_index}/{total_chunks}...")
            extraction_message = self._build_chunk_extraction_message(chunk, chunk_index, total_chunks)
            # v4.8.0：輸出上限改由 context 推導。固定 3072 在 128K instance 上等於
            # 「一塊最多只能留下 3,072 tokens 的筆記」，是把逐字稿壓成薄紀錄的第一個
            # 天花板（實測四塊合計只剩 8,176 tokens，而逐字稿是 11,712）。
            extraction_prompt = self._local_extraction_prompt(template)
            extraction_output_tokens = self._resolve_local_output_tokens(
                context_window=context_tokens,
                prompt_tokens=(
                    self._estimate_tokens(extraction_prompt)
                    + self._estimate_tokens(extraction_message)
                ),
            )
            notes = await self._generate_with_local_engine(
                engine,
                extraction_prompt,
                extraction_message,
                temperature=settings.LOCAL_LLM_EXTRACTION_TEMPERATURE,
                num_predict=extraction_output_tokens,
                context_window_tokens=context_tokens,
                lmstudio_selection=lmstudio_selection,
            )
            extracted_notes.append(self._clean_ollama_output(notes))

        extraction_duration = time.monotonic() - extraction_started
        merged_notes = await self._consolidate_notes(
            engine,
            extracted_notes,
            plan,
            progress_callback,
            context_window_tokens=context_tokens,
            lmstudio_selection=lmstudio_selection,
        )

        merge_duration = time.monotonic() - extraction_duration - extraction_started
        self._emit_progress(progress_callback, 86.0, "整理最終會議記錄...")
        # v4.8.0：地端最終生成改為「筆記＋逐字稿」雙輸入（比照雲端）。只餵筆記等於
        # 在生成前就丟掉所有沒進筆記的細節，是覆蓋率與專有名詞正確性的最大缺口；
        # context 餘裕不足時（例如 num_ctx=8192 的 Ollama）自動退回只餵筆記。
        final_message = self._resolve_final_generation_message(
            merged_notes, transcript, system_prompt, context_tokens, template=template
        )
        final_output_tokens = self._resolve_local_output_tokens(
            context_window=context_tokens,
            prompt_tokens=(
                self._estimate_tokens(system_prompt) + self._estimate_tokens(final_message)
            ),
        )
        summary = await self._generate_with_local_engine(
            engine,
            system_prompt,
            final_message,
            temperature=settings.LOCAL_LLM_GENERATION_TEMPERATURE,
            num_predict=final_output_tokens,
            context_window_tokens=context_tokens,
            lmstudio_selection=lmstudio_selection,
        )
        # P1-9：記錄級後處理（英文清理/結構補全）一律在「驗證前」執行，
        # 驗證是最後一關，通過後不得再被任何流程改寫。
        summary = self._finalize_record_text(
            self._clean_ollama_output(summary),
            template=template,
            mode="local",
            transcript=transcript,
        )

        # v4.8.0：地端套用與雲端相同的紀錄契約——動態長度閘門（依逐字稿規模）、
        # 發言來源標註絆索、年份依據絆索。三者都是確定性檢查，不靠第二個 LLM 判定。
        min_chars = self._estimate_cloud_min_summary_chars(transcript)
        issues = self._validate_summary_quality(
            summary, merged_notes, min_chars=min_chars, template=template
        )
        issues += self._validate_cloud_speaker_traceability(summary, template)
        issues += self._validate_cloud_date_grounding(summary, transcript)
        # P4-A（§9.3）：逐條對帳擴類（議題／決議／數字／日期；只回報不改寫）；
        # P4-B（§4.3）：忠實度絆索 problems 原樣併入同一份補強問題清單。
        issues += self._validate_record_source_coverage(
            summary, merged_notes, transcript, template=template
        )
        issues += self._validate_record_fidelity(summary, transcript, template)
        attempts = 0
        # P3 波（R23）：不收斂保護。補強是「整份紀錄重生成」，若上一輪之後問題集合
        # 完全沒變，代表再跑一輪只會白燒算力、還有把已正確段落改壞的風險
        # （實測 27B：第 2 輪與第 1 輪問題集合相同、輸出逐字相同，白燒 710 s）。
        previous_issue_signature: Optional[tuple] = None
        while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS:
            issue_signature = tuple(sorted(issues))
            if issue_signature == previous_issue_signature:
                log.warning(
                    "本地摘要補強未收斂（問題集合與上一輪相同，共 {} 項）→ 停止再補強，"
                    "避免白燒與重生成造成的品質退化：{}",
                    len(issues),
                    "; ".join(issues)[:400],
                )
                break
            previous_issue_signature = issue_signature
            attempts += 1
            self._emit_progress(progress_callback, 88.0 + attempts, f"補強摘要完整性（第 {attempts} 輪）...")
            log.info(f"本地摘要品質補強（第 {attempts} 輪），問題：{'; '.join(issues)}")
            refinement_message = self._resolve_final_refinement_message(
                summary, merged_notes, issues, transcript, system_prompt, context_tokens,
                template=template,
            )
            refinement_output_tokens = self._resolve_local_output_tokens(
                context_window=context_tokens,
                prompt_tokens=(
                    self._estimate_tokens(system_prompt)
                    + self._estimate_tokens(refinement_message)
                ),
            )
            summary = await self._generate_with_local_engine(
                engine,
                system_prompt,
                refinement_message,
                temperature=settings.LOCAL_LLM_REFINEMENT_TEMPERATURE,
                num_predict=refinement_output_tokens,
                context_window_tokens=context_tokens,
                lmstudio_selection=lmstudio_selection,
            )
            # 每一輪補強都必須走同一條地端後處理（mode="local"），否則補強輪會把
            # 已清掉的表格出處標註與 ASR 誤辨字再寫回來。
            summary = self._finalize_record_text(
                self._clean_ollama_output(summary),
                template=template,
                mode="local",
                transcript=transcript,
            )
            issues = self._validate_summary_quality(
                summary, merged_notes, min_chars=min_chars, template=template
            )
            issues += self._validate_cloud_speaker_traceability(summary, template)
            issues += self._validate_cloud_date_grounding(summary, transcript)
            # 每一輪補強後重算覆蓋率與忠實度（與首輪同一組檢查；只回報不改寫）。
            issues += self._validate_record_source_coverage(
                summary, merged_notes, transcript, template=template
            )
            issues += self._validate_record_fidelity(summary, transcript, template)

        if issues:
            log.warning(f"本地摘要仍有待補強問題: {'; '.join(issues)}")

        # CHANGE_MAP 4：bounded-call structured metrics 彙總（不虛構 wall-time SLO，
        # 僅呈現呼叫放大與階段耗時事實，供驗收與除錯使用）
        log.info(
            "本地摘要 pipeline metrics："
            f"chunk_count={total_chunks}, "
            f"logical_generations={self._lmstudio_logical_generations}, "
            f"semantic_attempts={self._lmstudio_semantic_attempts}, "
            f"network_retries={self._lmstudio_network_retries}, "
            f"merge_rounds={self._merge_rounds_used}, "
            f"merge_groups_last_round={self._merge_groups_last_round}, "
            f"duration_seconds={{'extraction': {extraction_duration:.1f}, "
            f"'merge': {merge_duration:.1f}, "
            f"'final_and_refine': {time.monotonic() - pipeline_started - extraction_duration - merge_duration:.1f}, "
            f"'total': {time.monotonic() - pipeline_started:.1f}}}"
            # P4-A 觀測欄位（off／未執行＝空字串 → 與本波前 byte 級相同）
            f"{self._record_coverage_metrics_fields()}"
        )

        return summary

    @staticmethod
    def _finalize_record_text(
        summary: str,
        template: Optional[MeetingTemplate] = None,
        *,
        mode: str = "cloud",
        transcript: Optional[str] = None,
    ) -> str:
        """會議紀錄記錄級後處理（自 task_processor 移入，P1-9）。

        v4.8.0：加入範本骨架佔位符修復（原先只有雲端後處理有這一道）。
        實測地端紀錄的未填佔位符數量是雲端的 3 倍以上（27 vs 14），並出現空白
        欄位與「（發言者1）」洩漏到開頭欄位；這些都是模型照抄提示詞骨架造成的
        格式債，必須用確定性後處理收斂，不能留給使用者手動修。

        T20260922-1930-01（P1 品質波）：`mode` 區分兩條路徑，順序固定不得互換。

        - `mode="cloud"`（預設）：與 v4.8.0 完全相同
          （`finalize_record` → `normalize_unfilled_placeholders`），雲端輸出 byte 級不變。
        - `mode="local"`：地端紀錄契約 —— `finalize_record` → 術語修正
          （`apply_record_term_fixes`）→ 表格出處標註清除
          （`strip_source_tags_from_table_rows`）→ 佔位符修復
          （`normalize_unfilled_placeholders`）→ 跨節重複抑制
          （`dedupe_cross_section_items`，**嚴格最後一步**；提前去重會被後續
          改寫破壞「切除尾端括號後完全相等」的判重前提）。

        T20260922-2037-02（P2 可查核性波）：地端再插入一步「出處標註真實性」
        （`snap_source_tags_to_transcript`），順序為
        `finalize_record` → 術語修正 → **標註吸附** → 表格標註清除 → 佔位符修復
        → 跨節重複抑制。此步與引擎、模型無關（LM Studio／Ollama 共用同一條
        `_summarize_with_local_pipeline`，見 `_generate_with_local_engine` 分派），
        只依賴「逐字稿段落時間表」這個模型無關的事實來源；`transcript` 缺席時
        完全不作用（雲端路徑與舊呼叫端行為 byte 級不變）。
        """
        from backend.core.glossary import english_protected_terms
        from backend.core.text_postprocess import finalize_record, normalize_unfilled_placeholders

        try:
            protected = english_protected_terms()
        except Exception:  # noqa: BLE001
            protected = set()
        text = finalize_record(summary, protected_terms=protected, template=template)
        if mode != "local":
            return normalize_unfilled_placeholders(text, template=template)

        # 地端專屬階段（軌 A 介面，T20260922-1930-01）；延遲 import 讓雲端路徑
        # 完全不依賴這些成員，任何一項缺席都不影響雲端輸出。
        from backend.core.text_postprocess import (
            apply_record_term_fixes,
            dedupe_cross_section_items,
            snap_source_tags_to_transcript,
            strip_source_tags_from_table_rows,
        )

        term_fixes = getattr(template, "record_term_fixes", ()) if template is not None else ()
        text, applied_fixes = apply_record_term_fixes(text, term_fixes)
        text, tag_snap_stats = snap_source_tags_to_transcript(text, transcript or "", template)
        text, stripped_tags = strip_source_tags_from_table_rows(text, template)
        text = normalize_unfilled_placeholders(text, template=template)
        text, deduped_items = dedupe_cross_section_items(text, template)
        if applied_fixes or stripped_tags or deduped_items or tag_snap_stats["snapped"]:
            log.info(
                "[品質] 地端紀錄後處理：術語修正 {} 處、出處標註吸附 {} 處"
                "（段落內 {}／最近段落 {}／跨發言者 {}；全域段首保護 {} 筆不動；"
                "精度保護 {} 筆不動；往前收 {} 筆／最大 {} s；不可回溯保留 {}）、"
                "表格出處標註移除 {} 處、跨節重複移除 {} 條",
                len(applied_fixes),
                tag_snap_stats["snapped"],
                tag_snap_stats["snapped_exact"],
                tag_snap_stats["snapped_nearest"],
                tag_snap_stats["snapped_speaker_mismatch"],
                tag_snap_stats["kept_on_start"],
                tag_snap_stats["kept_precision"],
                tag_snap_stats["backward_moves"],
                tag_snap_stats["max_backward_seconds"],
                tag_snap_stats["untraceable"],
                stripped_tags,
                deduped_items,
            )
        return text

    def _finalize_cloud_record_text(
        self, summary: str, template: Optional[MeetingTemplate] = None
    ) -> str:
        """雲端紀錄收尾（v4.7.3 契約；v4.8.0 起與地端共用同一後處理）。

        歷史：雲端原本多一道「模型照抄範本骨架」修復，地端沒有；實測顯示地端
        反而更需要它（未填佔位符 27 vs 14、且出現空白欄位）。因此兩條路徑統一
        走 `_finalize_record_text`（＝ finalize_record ＋ 佔位符修復）。
        """
        return self._finalize_record_text(summary, template=template)

    async def generate_local(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.0,
        num_predict: Optional[int] = None,
        allow_reasoning_retry: bool = True,
    ) -> str:
        """以本地引擎執行單次生成（供逐字稿語意校正等模組共用，P1-3）。

        allow_reasoning_retry 僅作用於 LM Studio 路徑；correction 呼叫端
        （WAVE-04）會明確傳 False。
        """
        engine = await self._select_local_engine()
        lmstudio_selection = self._active_lmstudio_selection
        return await self._generate_with_local_engine(
            engine,
            system_prompt,
            user_message,
            temperature=temperature,
            num_predict=num_predict,
            lmstudio_selection=lmstudio_selection,
            allow_reasoning_retry=allow_reasoning_retry,
        )

    async def _stream_ollama_chat_once(
        self,
        client: httpx.AsyncClient,
        body: dict,
    ) -> tuple[str, dict]:
        """單次串流 /api/chat（v4.7.0）。

        stream:false 在長生成期間零位元組回傳，會讓 read timeout 變成
        「總時長硬上限」而誤殺合法長會議（本次空白紀錄事故根因之一）。
        改為串流後：
        - httpx read timeout ＝ chunk 間「閒置」逾時（快速偵測真正卡死）
        - asyncio.timeout ＝ 總時長上限（寧可等待、不截斷）

        回傳 (累積內容, 最終 done chunk——含 load_duration/eval_count 等指標)。
        """
        timeout = httpx.Timeout(
            connect=10.0,
            read=settings.LOCAL_LLM_STREAM_IDLE_TIMEOUT,
            write=30.0,
            pool=10.0,
        )
        content_parts: list[str] = []
        final_chunk: Optional[dict] = None

        async with asyncio.timeout(settings.LOCAL_LLM_REQUEST_TIMEOUT):
            async with client.stream("POST", "/api/chat", json=body, timeout=timeout) as response:
                if response.status_code != 200:
                    await response.aread()
                    response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        raise OllamaStreamRetryable(f"串流回應非 JSON: {line[:120]}")

                    if chunk.get("error"):
                        raise OllamaStreamRetryable(f"串流中途錯誤: {chunk['error']}")

                    message_content = (chunk.get("message") or {}).get("content")
                    if message_content:
                        content_parts.append(message_content)

                    if chunk.get("done"):
                        final_chunk = chunk
                        break

        if final_chunk is None:
            raise OllamaStreamRetryable("串流結束但未收到 done chunk（連線中斷）")

        done_reason = final_chunk.get("done_reason")
        # v4.7.1：done_reason=length（撞到 num_predict 上限）不可重試——
        # 這是確定性結果，內容已完整累積於 content_parts，重試 2 次必然停在
        # 同一個截斷點，徒然浪費時間並讓整份會議紀錄失敗（v4.7.0 迴歸根因）。
        # 交由呼叫端（_post_ollama_chat）記錄警告後接受這份「內容完整但被截斷」的輸出。
        if done_reason not in (None, "stop", "length"):
            raise OllamaStreamRetryable(f"done_reason={done_reason}（輸出異常結束）")

        return "".join(content_parts), final_chunk

    @staticmethod
    def _log_generation_metrics(final_chunk: dict) -> None:
        """記錄單次生成的載入時間與吞吐（v4.7.0 觀測——參考專案經驗：
        load_duration 能區分「冷啟動慢」與「推理慢」，tokens/s 過低＝offload 直接證據。"""
        load_seconds = (final_chunk.get("load_duration") or 0) / 1e9
        eval_count = final_chunk.get("eval_count") or 0
        eval_seconds = (final_chunk.get("eval_duration") or 0) / 1e9
        tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
        # v4.7.1：加入 prompt_eval_count，觀測本次呼叫實際佔用多少 context——
        # 用來驗證「context plan 是否保守」「num_predict 擴大是否合理」。
        prompt_eval_count = final_chunk.get("prompt_eval_count") or 0

        log.info(
            f"Ollama 生成完成：load={load_seconds:.1f}s, "
            f"tokens/s={tokens_per_second:.1f}, eval_count={eval_count}, "
            f"prompt_eval_count={prompt_eval_count}"
        )
        if 0 < tokens_per_second < settings.LOCAL_LLM_MIN_TOKENS_PER_SECOND:
            log.warning(
                f"生成吞吐僅 {tokens_per_second:.1f} tokens/s"
                f"（門檻 {settings.LOCAL_LLM_MIN_TOKENS_PER_SECOND}）——"
                "疑似模型部分卸載至 CPU，請檢查 warmup log 與主機 VRAM 佔用"
            )

    async def _post_ollama_chat(
        self,
        client: httpx.AsyncClient,
        payload: dict,
        send_think_field: bool,
    ) -> tuple[str, dict, bool]:
        """送出一次 /api/chat：串流＋think 相容降級＋瞬時錯誤重試（v4.7.0）。

        瞬時錯誤（閒置逾時／連線中斷／串流層可重試失敗）重試
        LOCAL_LLM_TRANSIENT_RETRIES 次；HTTP 4xx/5xx 與總時長超限非瞬時，不重試。
        回傳 (內容, done chunk 指標, 可能已降級的 send_think_field)。
        """
        retries = settings.LOCAL_LLM_TRANSIENT_RETRIES
        for attempt in range(retries + 1):
            body = dict(payload, think=False) if send_think_field else payload
            try:
                try:
                    content, final_chunk = await self._stream_ollama_chat_once(client, body)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 400 and send_think_field:
                        log.info("模型不支援 think 參數，改以相容模式重送")
                        send_think_field = False
                        content, final_chunk = await self._stream_ollama_chat_once(
                            client, payload
                        )
                    else:
                        raise
                self._log_generation_metrics(final_chunk)
                if final_chunk.get("done_reason") == "length":
                    # v4.7.1：不重試，接受已截斷但完整累積的內容——下游驗證/
                    # 補強迴圈（P1-9）會把關格式，此為 v4.6.x 時代已驗證可用的行為。
                    log.warning(
                        "Ollama 輸出達 num_predict 上限被截斷（eval_count={}, num_predict={}）——內容已保留，接受並繼續",
                        final_chunk.get("eval_count"),
                        (payload.get("options") or {}).get("num_predict"),
                    )
                return content, final_chunk, send_think_field
            except TimeoutError:
                # asyncio.timeout 總時長超限：重跑同樣 30 分鐘無望，直接失敗並講清楚
                raise RuntimeError(
                    f"Ollama 生成超過總時長上限 {settings.LOCAL_LLM_REQUEST_TIMEOUT:.0f} 秒"
                    "（串流仍有進展但過慢）——請檢查模型是否部分卸載至 CPU"
                )
            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                OllamaStreamRetryable,
            ) as exc:
                if attempt >= retries:
                    raise
                wait_seconds = (attempt + 1) * settings.LOCAL_LLM_RETRY_BACKOFF_SECONDS
                log.warning(
                    f"Ollama 請求瞬時失敗（第 {attempt + 1}/{retries + 1} 次）："
                    f"{describe_exception(exc)}，{wait_seconds:.0f} 秒後重試"
                )
                await asyncio.sleep(wait_seconds)

        raise RuntimeError("Ollama 請求重試邏輯異常（不應執行到此）")

    def _effective_context_tokens(self, override: Optional[int] = None) -> int:
        """本任務生效的 num_ctx：顯式覆蓋 > warmup 降級值 > settings 預設（v4.7.0）。"""
        return (
            override
            or self._active_context_tokens
            or settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS
        )

    def _ollama_sampling_options(self) -> dict:
        """P4-C（§9.5／W-1）：Ollama options 的取樣參數——與 LM Studio 讀同一份 config。

        本波前此三鍵在 Ollama 路徑寫死（top_p=0.95／top_k=64／repeat_penalty=1.08），
        導致在 Mac 調出的參數於 Windows／Ollama 不生效（兩引擎不同把尺）。None＝
        不送該鍵、沿用端點預設，與 `_lmstudio_extra_body` 對
        LOCAL_LLM_SAMPLING_TOP_P／TOP_K 的語意一致（同一份 config、同一種 None 語意）。
        僅供 Ollama 使用：LM Studio Splash 引擎對 penalty 類欄位回 HTTP 400。
        一行 rollback＝`return dict(self.LEGACY_OLLAMA_SAMPLING_OPTIONS)`。
        """
        options: dict = {}
        top_p = getattr(settings, "LOCAL_LLM_SAMPLING_TOP_P", None)
        top_k = getattr(settings, "LOCAL_LLM_SAMPLING_TOP_K", None)
        repeat_penalty = getattr(settings, "LOCAL_LLM_SAMPLING_REPEAT_PENALTY", None)
        if top_p is not None:
            options["top_p"] = float(top_p)
        if top_k is not None:
            options["top_k"] = int(top_k)
        if repeat_penalty is not None:
            options["repeat_penalty"] = float(repeat_penalty)
        return options

    async def _summarize_with_ollama(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None,
        temperature: float = 0.2,
        num_predict: Optional[int] = None,
        context_window_tokens: Optional[int] = None,
        expand_output_budget: bool = True,
    ) -> str:
        """
        使用 Ollama 本地模式生成摘要

        v4.7.1 改進：
        - 依 context 餘裕自動擴大 num_predict（治本修復 done_reason=length 誤殺整份紀錄）

        v4.7.0 改進：
        - 串流生成（閒置逾時／總時長分離）＋每呼叫 tokens/s 觀測
        - num_ctx 依 warmup 自我修復結果可任務級降級

        v4.2.1 改進：
        - Gemma4 預設參數：top_k 64、top_p 0.95、repeat_penalty 1.08

        P4-C（W-1）：上述三鍵改讀同一份 config（與 LM Studio 同源）；
        舊寫死值保留為 LEGACY_OLLAMA_SAMPLING_OPTIONS（一行 rollback）。
        """
        client = await self._get_ollama_client()

        # v4.7.1：context plan 已保證輸入在預算內，prompt 用不完的 context
        # 全數讓給輸出，降低撞到 num_predict 上限被截斷的機率。估算誤差無害——
        # num_predict 超過實際餘裕時，Ollama 只會在 ctx 滿時以 done_reason=length
        # 停止，仍會落入上面已修復的「接受內容＋警告」路徑，不會整份失敗。
        requested_predict = num_predict or settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS
        if expand_output_budget:
            n_ctx = self._effective_context_tokens(context_window_tokens)
            est_prompt = self._estimate_tokens(system_prompt) + self._estimate_tokens(user_message) + 64
            requested_predict = max(requested_predict, n_ctx - est_prompt - 256)
        # P4-C（W-1／W-2）：取樣參數與 context 預算的實際來源登錄（對帳用）。
        sampling_options = self._ollama_sampling_options()
        log.info(
            "Ollama 取樣參數（P4-C 同源 config）：top_p={}, top_k={}, repeat_penalty={}；"
            "num_ctx={}（context_window_source={}）",
            sampling_options.get("top_p", "不送"),
            sampling_options.get("top_k", "不送"),
            sampling_options.get("repeat_penalty", "不送"),
            self._effective_context_tokens(context_window_tokens),
            getattr(self, "_context_window_source", "settings"),
        )

        try:
            # 進度更新：開始生成摘要
            self._emit_progress(progress_callback, 65.0, "載入 Ollama 模型...")

            effective_model = self._get_effective_model()
            log.info(f"使用模型: {effective_model}")

            # 空回應偶發 → 自動重試一次。
            # 根因（E2E 實測）：gemma4 為思考型模型，thinking 會吃光 num_predict
            # 導致正文為空，故預設以 think:false 關閉思考；不支援該參數的模型
            # 會回 400，此時降級為不帶 think 欄位重送。
            summary = ""
            send_think_field = settings.LOCAL_LLM_DISABLE_THINKING
            for attempt in range(2):
                payload = {
                    "model": effective_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    # v4.7.0：串流生成——閒置逾時偵測卡死、總時長上限放寬
                    "stream": True,
                    # P0-7：三階段流程會連續呼叫十數次，keep_alive=0 會導致每階段
                    # 重載 20GB 模型。改為可設定（預設 30m），流程結束後自然逾時釋放。
                    "keep_alive": settings.LOCAL_LLM_KEEP_ALIVE,
                    "options": {
                        # 重試時略升溫度以跳出空回應狀態
                        "temperature": temperature if attempt == 0 else max(temperature, 0.3),
                        # P4-C（W-1）：top_p／top_k／repeat_penalty 一律讀同一份
                        # config（None＝不送；舊寫死值為 LEGACY 常數＝一行 rollback）。
                        **sampling_options,
                        "num_ctx": self._effective_context_tokens(context_window_tokens),
                        "num_predict": requested_predict,
                        "stop": ["</think>", "</thought>", "</details>", "---\n\n---"]  # 停止標記
                    }
                }
                raw_content, _metrics, send_think_field = await self._post_ollama_chat(
                    client, payload, send_think_field
                )

                self._emit_progress(progress_callback, 85.0, "處理摘要結果...")

                summary = self._clean_ollama_output(raw_content)

                # 清理後為空但原始輸出非空 → 用原始輸出（後續驗證/補強會把關格式）
                if (not summary or not summary.strip()) and raw_content.strip():
                    log.warning(
                        "清理後為空但模型原始輸出非空（{} 字元），改用原始輸出", len(raw_content)
                    )
                    summary = raw_content.strip()

                if summary and summary.strip():
                    break
                log.warning("Ollama 回傳空內容（第 {} 次），{}", attempt + 1, "重試中" if attempt == 0 else "放棄")

            # 檢查摘要是否為空
            if not summary or not summary.strip():
                raise RuntimeError("摘要生成失敗：結果為空")

            log.info(f"Ollama 摘要生成成功，模型: {effective_model}")
            return summary

        except httpx.ConnectError:
            log.error("無法連接到 Ollama 服務，請確認 Ollama 是否正在運行")
            raise RuntimeError("Ollama 服務不可用，請確認 Ollama 是否正在運行")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # 模型未找到 - 提供詳細錯誤訊息
                effective_model = self._get_effective_model()
                error_msg = f"模型 '{effective_model}' 未找到。"

                # 嘗試取得可用模型列表
                try:
                    tags_response = await client.get("/api/tags")
                    if tags_response.status_code == 200:
                        data = tags_response.json()
                        available_models = [model.get("name") for model in data.get("models", [])]
                        if available_models:
                            error_msg += f"\n\n可用模型: {', '.join(available_models)}"
                            error_msg += f"\n\n建議執行: {self._build_ollama_pull_command(settings.LOCAL_LLM_MODEL)}"
                        else:
                            error_msg += "\n\n目前沒有已安裝的模型。"
                            error_msg += f"\n\n建議執行: {self._build_ollama_pull_command(settings.LOCAL_LLM_MODEL)}"
                except:
                    pass

                log.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                log.error(f"Ollama API 錯誤: HTTP {e.response.status_code}")
                raise
        except Exception as e:
            log.exception(f"Ollama 摘要生成失敗: {describe_exception(e)}")
            raise

    def _clean_ollama_output(self, summary: str) -> str:
        """
        清理模型輸出中的常見問題
        - 移除 LLM 常加的前綴（「好的，我來整理...」）
        - 移除 Gemma4 可能輸出的 thought blocks / HTML 標籤
        - 移除 Markdown code fence
        - 若模型在前面加了解釋，嘗試定位到第一個標題
        """
        if not summary:
            return ""

        prefixes_to_remove = [
            r"^```(?:markdown)?\s*",
            r"^好的[，,]?\s*我[來来][整幫]理.*?[：:。\n]",
            r"^以下是.*?會議記錄[：:。\n]",
            r"^以下是.*?整理結果[：:。\n]",
            r"^我[來来]為[您你]整理.*?[：:。\n]",
            r"^根據逐字稿[，,]?\s*",
            r"^OK[,，]?\s*",
            r"^Sure[,，]?\s*",
        ]

        cleaned = summary.strip()
        cleaned = re.sub(
            r"<(?:think|thought|details)\b[^>]*>.*?</(?:think|thought|details)>",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
        cleaned = re.sub(
            r"^\s*</?(?:think|thought|details)[^>]*>\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        for pattern in prefixes_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"^\s*```(?:markdown)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n?```$", "", cleaned.strip(), flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"</?(?:think|thought|details)[^>]*>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 會議紀錄正式格式以「會議名稱：」開頭（並非 Markdown 標題），萃取筆記則以「# 萃取筆記」開頭。
        # 兩種錨點都要支援，才能裁掉模型可能加在前面的英文分析/前言或評估標準回吐。
        # 取兩者中最靠前者，避免英文前言內含 # 而誤切到垃圾文字中段。
        record_anchor = re.search(r"^會議名稱[：:]", cleaned, re.MULTILINE)
        md_anchor = re.search(r"^#\s", cleaned, re.MULTILINE)
        anchor_starts = [m.start() for m in (record_anchor, md_anchor) if m]
        if anchor_starts:
            first = min(anchor_starts)
            if first > 0:
                cleaned = cleaned[first:]

        return cleaned.strip()

    async def _summarize_with_lmstudio(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        context_window_tokens: Optional[int] = None,
        selection: Optional[LMStudioModelSelection] = None,
        expand_output_budget: bool = True,
        allow_reasoning_retry: bool = True,
    ) -> str:
        """
        使用已選定的 LM Studio loaded instance 生成摘要。

        selection 必須由摘要工作開始時建立；直接呼叫此方法的舊呼叫端則
        會在這裡補做一次 selection。整個請求只使用 model key，不觸發 JIT
        load，也不在生成失敗時改選其他 instance。

        semantic recovery 僅由 ``allow_reasoning_retry`` 決定（RC-2）：correction
        等 BEST_EFFORT 呼叫端傳 False 即停用；CORE 生成（含 merge）預設啟用，
        merge 的可見目標由 orchestration 的 compaction 收斂，不再透過禁止
        provider recovery 實現。``expand_output_budget`` 僅作用於 Ollama
        num_predict 擴張，不再參與 LM Studio recovery 決策。
        """
        self._lmstudio_logical_generations += 1
        selection = selection or self._active_lmstudio_selection
        if selection is None:
            selection = await self._resolve_lmstudio_selection()

        if max_tokens is None:
            requested_max_tokens = settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS
        else:
            try:
                requested_max_tokens = max(1, int(max_tokens))
            except (TypeError, ValueError):
                requested_max_tokens = settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS

        # caller temperature/max_tokens 為權威（H-5）：後端不再讀 config*.yaml
        # 的 llm.lmstudio.*，legacy YAML 僅供舊版 CLI 參考。
        if selection.context_length:
            # request/retry headroom 以 selected instance 的 context_length 為準，
            # 缺失時才退回保守 planning context。
            context_budget = selection.context_length
        else:
            context_budget = self._effective_context_tokens(context_window_tokens)
        prompt_tokens = self._estimate_tokens(system_prompt) + self._estimate_tokens(user_message) + 64
        available_output_tokens = context_budget - prompt_tokens - 64
        if requested_max_tokens > available_output_tokens:
            # preflight fail loudly：不得把 caller budget 靜默壓成 1（observed log max_tokens=1）
            raise StableServiceError(
                LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED,
                f"LM Studio request budget 不足：caller max_tokens {requested_max_tokens}"
                f" + prompt {prompt_tokens} tokens 超過 context budget {context_budget}"
                f"（available output {available_output_tokens}，model={selection.model_identifier}）；"
                "請縮短輸入或降低 max_tokens",
            )
        client = self._get_lmstudio_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        self._emit_progress(
            progress_callback,
            65.0,
            f"使用已載入 LM Studio 模型（{selection.model_identifier}）...",
        )
        log.info(
            "使用 LM Studio 生成摘要 (model={}, instance={}, temperature={}, max_tokens={}, "
            "context_budget={}, prompt_tokens={}, allow_reasoning_retry={})",
            selection.model_identifier,
            selection.loaded_instance_id,
            temperature,
            requested_max_tokens,
            context_budget,
            prompt_tokens,
            allow_reasoning_retry,
        )

        response = await self._lmstudio_chat_request(
            client, selection, messages, temperature, requested_max_tokens
        )

        self._emit_progress(progress_callback, 85.0, "處理摘要結果...")
        content, reasoning_text, finish_reason, usage_tokens = (
            self._parse_lmstudio_response_payload(response)
        )
        self._log_lmstudio_response_diagnostics(
            selection, finish_reason, content, reasoning_text,
            usage_tokens, requested_max_tokens, attempt_type="initial",
        )
        summary = self._clean_ollama_output(str(content))
        if summary and summary.strip():
            log.info("LM Studio 摘要生成成功，模型: {}", selection.model_identifier)
            return summary.strip()

        # RC-2：有界 semantic recovery state machine（allow_reasoning_retry 單獨
        # 決定；每個 logical generation 最多三次 completed provider calls）。
        reasoning_evidence = bool(reasoning_text and reasoning_text.strip())
        if not allow_reasoning_retry:
            log.warning("LM Studio 摘要生成結果為空（本次呼叫停用 semantic recovery）")
            raise StableServiceError(
                LMSTUDIO_NO_FINAL_CONTENT,
                self._describe_empty_lmstudio_response(finish_reason, reasoning_evidence, False),
            )

        return await self._recover_lmstudio_empty_response(
            client, selection, messages, temperature,
            requested_max_tokens, context_budget, prompt_tokens,
            reasoning_text, finish_reason, usage_tokens,
        )

    async def _recover_lmstudio_empty_response(
        self,
        client,
        selection: LMStudioModelSelection,
        messages: list[dict],
        temperature: float,
        initial_max_tokens: int,
        context_budget: int,
        prompt_tokens: int,
        reasoning_text: Optional[str],
        finish_reason: Optional[str],
        usage_tokens: dict,
    ) -> str:
        """空回應的有界 semantic recovery state machine（RC-2 / CHANGE_MAP 2）。

        每個 CORE logical generation 最多三次 completed provider calls：
        1. initial：caller 指定的初始 provider completion cap（已於呼叫端完成）。
        2. growth retry：僅 initial 為 ``length + reasoning + empty content`` 時，
           以既有 headroom/configured-cap 公式提高一次 max_tokens。
        3. stop replay：僅 growth retry 為 ``stop + reasoning + empty content`` 時，
           以同 model/instance/prompt/temperature 與目前 cap replay 一次。

        initial 直接 ``stop + reasoning + empty`` → 只做一次同 cap replay（總計
        兩次），不接續 growth retry。growth retry 再度 ``length + empty``、
        stop replay 仍空、無 reasoning evidence、無可增加 headroom → 立即拋
        ``LMSTUDIO_NO_FINAL_CONTENT``，不再呼叫 provider。network transient
        retries 於 ``_lmstudio_chat_request`` 內另行計數，與 semantic attempts
        分開、互不重置上限。
        """
        reasoning_evidence = bool(reasoning_text and reasoning_text.strip())
        if not reasoning_evidence:
            log.warning("LM Studio 回應無 final content 且無 reasoning 證據，不進行 semantic retry")
            raise StableServiceError(
                LMSTUDIO_NO_FINAL_CONTENT,
                self._describe_empty_lmstudio_response(finish_reason, False, True),
            )

        if finish_reason == "stop":
            # initial 直接 stop + reasoning + empty → 一次同 cap replay（總計兩次）。
            return await self._replay_lmstudio_stop_empty(
                client, selection, messages, temperature,
                initial_max_tokens, finish_reason,
            )

        if finish_reason != "length":
            log.warning("LM Studio 空回應 finish_reason={} 不支援 semantic retry", finish_reason)
            raise StableServiceError(
                LMSTUDIO_NO_FINAL_CONTENT,
                self._describe_empty_lmstudio_response(finish_reason, True, True),
            )

        # growth retry：以既有 headroom/configured-cap 公式提高一次 cap。
        retry_cap, observed_reasoning_tokens = self._compute_lmstudio_growth_cap(
            initial_max_tokens, context_budget, prompt_tokens,
            reasoning_text, usage_tokens,
        )
        if retry_cap <= initial_max_tokens:
            raise StableServiceError(
                LMSTUDIO_NO_FINAL_CONTENT,
                "LM Studio 僅輸出 reasoning 即達 max_tokens 上限"
                f"（finish_reason={finish_reason}, reasoning_tokens≈{observed_reasoning_tokens}），"
                f"且 provider headroom 無法提高 max_tokens（{initial_max_tokens}→{retry_cap}）；"
                "請縮短輸入或調低 max_tokens",
            )

        log.warning(
            "LM Studio 回應僅含 reasoning（finish_reason={}, reasoning_tokens≈{}），"
            "提高 max_tokens {}→{} 執行一次 growth retry（model/instance/prompt/temperature 不變）",
            finish_reason,
            observed_reasoning_tokens,
            initial_max_tokens,
            retry_cap,
        )
        self._lmstudio_semantic_attempts += 1
        growth_response = await self._lmstudio_chat_request(
            client, selection, messages, temperature, retry_cap
        )
        growth_content, growth_reasoning, growth_finish_reason, growth_usage = (
            self._parse_lmstudio_response_payload(growth_response)
        )
        self._log_lmstudio_response_diagnostics(
            selection, growth_finish_reason, growth_content, growth_reasoning,
            growth_usage, retry_cap, attempt_type="growth retry",
        )
        summary = self._clean_ollama_output(str(growth_content))
        if summary and summary.strip():
            return summary.strip()

        growth_reasoning_evidence = bool(growth_reasoning and growth_reasoning.strip())
        if growth_finish_reason == "stop" and growth_reasoning_evidence:
            # growth retry 停止於 reasoning-only 空回應 → 一次同 cap stop replay。
            return await self._replay_lmstudio_stop_empty(
                client, selection, messages, temperature,
                retry_cap, growth_finish_reason,
            )

        # growth retry 再度 length+empty、無 reasoning 或其他 finish reason：
        # budget 增長無效，立即拋錯，不再有第三次呼叫。
        raise StableServiceError(
            LMSTUDIO_NO_FINAL_CONTENT,
            f"LM Studio growth retry（max_tokens={retry_cap}）後仍無 final content"
            f"（finish_reason={growth_finish_reason}，reasoning_evidence="
            f"{growth_reasoning_evidence}）",
        )

    def _compute_lmstudio_growth_cap(
        self,
        initial_max_tokens: int,
        context_budget: int,
        prompt_tokens: int,
        reasoning_text: Optional[str],
        usage_tokens: dict,
    ) -> tuple[int, int]:
        """Revision-1 growth retry cap 公式（含 observed reasoning tokens 估算）。"""
        observed_reasoning_tokens = usage_tokens.get("reasoning_tokens")
        if not observed_reasoning_tokens and reasoning_text:
            # usage 未提供 reasoning tokens 時以文字 token 估算代替（不記錄文字）
            observed_reasoning_tokens = self._estimate_tokens(reasoning_text)
        observed_reasoning_tokens = int(observed_reasoning_tokens or 0)

        configured_cap = max(1, int(settings.LMSTUDIO_REASONING_RETRY_MAX_TOKENS))
        provider_headroom = context_budget - prompt_tokens - 64
        retry_cap = min(
            provider_headroom,
            configured_cap,
            max(initial_max_tokens * 2, observed_reasoning_tokens + initial_max_tokens + 256),
        )
        return max(1, int(retry_cap)), observed_reasoning_tokens

    async def _replay_lmstudio_stop_empty(
        self,
        client,
        selection: LMStudioModelSelection,
        messages: list[dict],
        temperature: float,
        replay_max_tokens: int,
        stop_finish_reason: Optional[str],
    ) -> str:
        """``stop + reasoning + empty content`` 的最終同 cap replay：恰好一次。

        同 model/instance/prompt/temperature 與目前 token cap replay，不再提高
        cap；replay 仍無 final content → ``LMSTUDIO_NO_FINAL_CONTENT``。
        """
        log.warning(
            "LM Studio 回應僅含 reasoning 且 finish_reason={}，以相同 cap={} 、"
            "同 model/instance/prompt/temperature 執行最終 stop replay 一次",
            stop_finish_reason,
            replay_max_tokens,
        )
        self._lmstudio_semantic_attempts += 1
        replay_response = await self._lmstudio_chat_request(
            client, selection, messages, temperature, replay_max_tokens
        )
        replay_content, replay_reasoning, replay_finish_reason, replay_usage = (
            self._parse_lmstudio_response_payload(replay_response)
        )
        self._log_lmstudio_response_diagnostics(
            selection, replay_finish_reason, replay_content, replay_reasoning,
            replay_usage, replay_max_tokens, attempt_type="stop replay",
        )
        summary = self._clean_ollama_output(str(replay_content))
        if summary and summary.strip():
            return summary.strip()
        raise StableServiceError(
            LMSTUDIO_NO_FINAL_CONTENT,
            f"LM Studio stop replay（max_tokens={replay_max_tokens}）後仍無 final content"
            f"（finish_reason={replay_finish_reason}）",
        )

    def _describe_empty_lmstudio_response(
        self,
        finish_reason: Optional[str],
        reasoning_evidence: bool,
        reasoning_retry_allowed: bool,
    ) -> str:
        """空回應的 actionable detail（只含狀態與對策，不含回應內容）。"""
        if finish_reason == "length" and reasoning_evidence:
            if not reasoning_retry_allowed:
                return (
                    "LM Studio 僅輸出 reasoning 即達 max_tokens 上限"
                    "（finish_reason=length），且本次呼叫已停用 semantic recovery"
                    "（BEST_EFFORT 呼叫）：請調高 caller max_tokens 或縮短輸入"
                )
            return (
                "LM Studio 僅輸出 reasoning 即達 max_tokens 上限"
                "（finish_reason=length），且 retry headroom 不足以提高 max_tokens；"
                "請調高 caller max_tokens 或 LMSTUDIO_REASONING_RETRY_MAX_TOKENS"
            )
        if reasoning_evidence:
            return (
                f"LM Studio 回應無 final content（finish_reason={finish_reason}，"
                "有 reasoning 證據但 semantic recovery 已用罄或不可用）；"
                "請確認模型是否正常輸出，或改用其他已載入 LLM"
            )
        return (
            f"LM Studio 回應無 final content（finish_reason={finish_reason}，"
            "無 reasoning 證據）；請確認模型是否正常輸出，或改用其他已載入 LLM"
        )

    @staticmethod
    def _downgrade_extra_body(extra_body: Optional[dict]) -> Optional[dict]:
        """HTTP 400 相容降級順序：先丟取樣欄位、再丟關閉思考欄位（v4.8.0）。"""
        current = dict(extra_body or {})
        sampling_keys = [key for key in ("top_p", "top_k") if key in current]
        if sampling_keys:
            for key in sampling_keys:
                current.pop(key)
            return current or None
        return None

    @staticmethod
    def _lmstudio_extra_body() -> Optional[dict]:
        """LM Studio 請求的 extra_body（v4.8.0）。

        兩類欄位：
        1. `reasoning_effort="none"`——關閉思考（v4.7.4 契約，維持不變）。
        2. `top_p`／`top_k`——官方 Qwen3.6／3.8 model card 對非思考模式建議
           `top_p=0.80`、`top_k=20`；舊行為完全不送，等於把分佈控制交給端點預設
           （本機 Splash 引擎的預設是 `top_p=0.95`，比官方建議更寬）。

        刻意不送 `min_p`／`presence_penalty`／`frequency_penalty`：Splash 引擎對
        這些欄位非 0 值直接回 HTTP 400（官方建議的 `presence_penalty=1.5` 在此
        不可用），因此重複抑制改用溫度與 top_p/top_k 控制。
        """
        extra: dict = {}
        if settings.LOCAL_LLM_DISABLE_THINKING:
            extra["reasoning_effort"] = "none"
        if settings.LOCAL_LLM_SAMPLING_TOP_P is not None:
            extra["top_p"] = float(settings.LOCAL_LLM_SAMPLING_TOP_P)
        if settings.LOCAL_LLM_SAMPLING_TOP_K is not None:
            extra["top_k"] = int(settings.LOCAL_LLM_SAMPLING_TOP_K)
        return extra or None

    async def _lmstudio_chat_request(
        self,
        client,
        selection: LMStudioModelSelection,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> object:
        """單次 chat.completions.create（含 transient/HTTP 錯誤映射與思考關閉降級）。

        network transient retry 維持既有 LOCAL_LLM_TRANSIENT_RETRIES 上限；
        semantic（reasoning）retry 由呼叫端另行計數，兩者分開、各自有界。
        """
        retries = max(int(settings.LOCAL_LLM_TRANSIENT_RETRIES), 0)
        transient_errors = (
            APIConnectionError,
            APITimeoutError,
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        )
        # T20260922-1349-01 RC-2：LM Studio 路徑先前完全沒有套用
        # LOCAL_LLM_DISABLE_THINKING（該開關只實作在 Ollama 路徑），於是推理型
        # 模型（實測 qwen3.8-27b-splash，capabilities.reasoning 預設 on）每次呼叫
        # 都先產生 233～4852 reasoning tokens：單場會議 11 次呼叫中即有 1 次
        # finish_reason=length 且 content 為 0 字元，並把生成階段拖長到整體
        # 87.5%（1246s／1422s）。LM Studio 為 OpenAI 相容端點，關閉思考的正確
        # 欄位是 `reasoning_effort: "none"`（實測 reasoning_tokens=0）。openai
        # 1.12.0 無此具名參數，僅能經 extra_body 傳遞。
        extra_body: Optional[dict] = self._lmstudio_extra_body()

        async def _create(extra: Optional[dict]):
            kwargs = {
                "model": selection.model_identifier,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if extra:
                kwargs["extra_body"] = extra
            return await client.chat.completions.create(**kwargs)

        for attempt in range(retries + 1):
            try:
                # 相容降級迴圈（v4.8.0）：伺服器不認識某個欄位時逐級降級重送
                # （先丟 top_p／top_k 保留關閉思考，再全丟），不得讓整份紀錄失敗。
                while True:
                    try:
                        return await _create(extra_body)
                    except Exception as exc:  # noqa: BLE001 — 相容降級需先讀 status code
                        status_code = getattr(getattr(exc, "response", None), "status_code", None)
                        if status_code == 400 and extra_body:
                            downgraded = self._downgrade_extra_body(extra_body)
                            log.warning(
                                "LM Studio 端點拒絕 extra_body {}（HTTP 400），改以 {} 相容模式重送",
                                sorted(extra_body),
                                sorted(downgraded) if downgraded else "無額外欄位",
                            )
                            extra_body = downgraded
                            continue
                        raise
            except transient_errors as exc:
                if attempt >= retries:
                    raise StableServiceError(
                        LMSTUDIO_UNREACHABLE,
                        f"LM Studio chat 請求失敗：{describe_exception(exc)}",
                    ) from exc
                wait_seconds = (attempt + 1) * settings.LOCAL_LLM_RETRY_BACKOFF_SECONDS
                self._lmstudio_network_retries += 1
                log.warning(
                    "LM Studio 請求瞬時失敗（第 %s/%s 次）：%s，%.0f 秒後重試",
                    attempt + 1,
                    retries + 1,
                    describe_exception(exc),
                    wait_seconds,
                )
                await asyncio.sleep(wait_seconds)
            except Exception as exc:  # noqa: BLE001 — map stable provider boundary errors
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code == 404:
                    raise StableServiceError(
                        LMSTUDIO_MODEL_NOT_LOADED,
                        f"LM Studio loaded instance {selection.loaded_instance_id!r} 已不可用",
                    ) from exc
                if isinstance(status_code, int) and status_code >= 500:
                    if attempt < retries:
                        wait_seconds = (attempt + 1) * settings.LOCAL_LLM_RETRY_BACKOFF_SECONDS
                        self._lmstudio_network_retries += 1
                        log.warning(
                            "LM Studio server error HTTP {}（第 {}/{} 次），{:.0f} 秒後重試",
                            status_code,
                            attempt + 1,
                            retries + 1,
                            wait_seconds,
                        )
                        await asyncio.sleep(wait_seconds)
                        continue
                    raise StableServiceError(
                        LMSTUDIO_UNREACHABLE,
                        f"LM Studio chat 回應 HTTP {status_code}",
                    ) from exc
                log.exception("LM Studio 摘要生成失敗: %s", describe_exception(exc))
                raise
        raise StableServiceError(LMSTUDIO_UNREACHABLE, "LM Studio chat 重試邏輯異常")

    @staticmethod
    def _parse_lmstudio_response_payload(
        response: object,
    ) -> tuple[str, Optional[str], Optional[str], dict]:
        """解析 chat 回應：final content、reasoning 證據、finish_reason、usage token counts。

        只回傳數值與狀態；reasoning 文字與 prompt 內容不得進入 log（呼叫端
        僅記錄字元數）。
        """
        try:
            choice = response.choices[0]
            message = choice.message
            content = message.content or ""
            reasoning = getattr(message, "reasoning_content", None)
            if reasoning is None:
                reasoning = getattr(message, "reasoning", None)
            finish_reason = getattr(choice, "finish_reason", None)
        except (AttributeError, IndexError, TypeError) as exc:
            raise RuntimeError("LM Studio 摘要生成失敗：回應格式無法解析") from exc

        usage = getattr(response, "usage", None)
        details = getattr(usage, "completion_tokens_details", None)
        usage_tokens: dict = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "reasoning_tokens": (
                getattr(details, "reasoning_tokens", None) if details is not None else None
            ),
        }
        reasoning_text = str(reasoning) if reasoning is not None else None
        return str(content), reasoning_text, finish_reason, usage_tokens

    def _log_lmstudio_response_diagnostics(
        self,
        selection: LMStudioModelSelection,
        finish_reason: Optional[str],
        content: str,
        reasoning_text: Optional[str],
        usage_tokens: dict,
        max_tokens: int,
        attempt_type: str = "initial",
    ) -> None:
        """記錄回應診斷（只記 counts，禁止記錄 reasoning 文字或 prompt 內容）。"""
        log.info(
            "LM Studio 回應診斷（{}）：model={}, instance={}, finish_reason={}, "
            "max_tokens={}, content_chars={}, reasoning_chars={}, "
            "prompt_tokens={}, completion_tokens={}, reasoning_tokens={}",
            attempt_type,
            selection.model_identifier,
            selection.loaded_instance_id,
            finish_reason,
            max_tokens,
            len(content),
            len(reasoning_text) if reasoning_text else 0,
            usage_tokens.get("prompt_tokens"),
            usage_tokens.get("completion_tokens"),
            usage_tokens.get("reasoning_tokens"),
        )

    def _estimate_cloud_min_summary_chars(self, transcript: str) -> int:
        """依逐字稿規模估算雲端紀錄的動態長度下限（v4.3.3 豐富度閘門）。

        校準依據（0708 實測）：103 分鐘會議逐字稿約 1.8 萬 tokens，
        雲端曾產出僅 8 百餘字、遺漏大量實質討論的過薄紀錄。
        係數 1/15 使該規模的下限落在約 1,200 字，恰可攔截過薄輸出；
        上限 2000 避免對模型提出不合理的灌水要求，下限 250 維持原防空底線。
        """
        transcript_tokens = self._estimate_tokens(transcript)
        return max(250, min(2000, transcript_tokens // 15))

    async def _extract_notes_with_gemini(
        self,
        transcript: str,
        progress_callback: Optional[callable] = None,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """雲端萃取筆記（v4.7.3 起預設「單次呼叫」，分段改為可選回退路徑）。

        2026-09-14 使用者決策：選雲端模型時不再分段萃取——地端分段的
        原始動機（記憶體不足、小模型注意力集中度低）在雲端不存在，且
        逐字稿規模遠低於雲端上下文上限，單次呼叫即可完成萃取。
        v4.3.3 的分段併發萃取（LLM 輸出長度不隨輸入等比放大的對策）
        保留為回退路徑：settings.CLOUD_LLM_SEGMENTED_EXTRACTION=true
        即恢復分段，此時分塊密度沿用地端實證值
        （settings.CLOUD_LLM_CHUNK_TOKENS），分段筆記零損串接。
        """
        if settings.CLOUD_LLM_SEGMENTED_EXTRACTION:
            chunks = self._split_transcript_into_chunks(
                transcript, settings.CLOUD_LLM_CHUNK_TOKENS
            ) or [transcript]
        else:
            chunks = [transcript]
        total_chunks = len(chunks)
        stage_label = f"共 {total_chunks} 段" if total_chunks > 1 else "單次呼叫"
        self._emit_progress(
            progress_callback, 68.0, f"萃取逐字稿重點（雲端，{stage_label}）..."
        )

        semaphore = asyncio.Semaphore(max(1, settings.CLOUD_LLM_MAX_CONCURRENT_REQUESTS))
        completed_count = 0

        extraction_prompt = self._cloud_extraction_prompt(template)

        async def extract_chunk(chunk_index: int, chunk: str) -> str:
            nonlocal completed_count
            async with semaphore:
                message = self._build_chunk_extraction_message(chunk, chunk_index, total_chunks)
                try:
                    notes = await self._gemini_chat(extraction_prompt, message, 0.1)
                except Exception as exc:  # noqa: BLE001 — 單次重試後仍失敗則向外拋出
                    log.warning(
                        "雲端萃取第 {}/{} 段失敗（{}），重試一次",
                        chunk_index,
                        total_chunks,
                        describe_exception(exc),
                    )
                    notes = await self._gemini_chat(extraction_prompt, message, 0.1)
                completed_count += 1
                self._emit_progress(
                    progress_callback,
                    68.0 + (completed_count / total_chunks) * 14.0,
                    f"萃取逐字稿重點（雲端）{completed_count}/{total_chunks}...",
                )
                return self._clean_ollama_output(notes)

        # return_exceptions=True：任一段失敗時等其餘段收尾再拋出首個例外，
        # 避免手足協程被遺留在背景（unretrieved exception 警告＋浪費 API 配額）
        results = await asyncio.gather(
            *(extract_chunk(index, chunk) for index, chunk in enumerate(chunks, start=1)),
            return_exceptions=True,
        )
        failures = [result for result in results if isinstance(result, BaseException)]
        if failures:
            raise failures[0]
        merged = "\n\n---\n\n".join(note for note in results if note.strip())
        return merged if merged.strip() else self._empty_extraction_notes()

    async def _summarize_with_gemini(
        self,
        system_prompt: str,
        transcript: str,
        progress_callback: Optional[callable] = None,
        temperature: float = 0.2,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """使用 Gemini API 雲端模式生成摘要（v4.3.3 分段萃取＋雙輸入生成）。

        歷史根因（v4.3.2 實測仍輸給地端）：整份逐字稿「單發萃取」會被
        模型壓成一頁筆記——輸出長度不隨輸入等比放大；第二段生成又只看
        筆記，第一段丟失的立場、理由、數據與案例永遠救不回來。
        地端品質勝出正是因為 context 限制迫使分塊萃取，每段筆記密度
        有結構保證。v4.3.3 根治：
        1. 萃取比照地端分塊密度，分段併發呼叫（_extract_notes_with_gemini）
        2. 生成與補強同時餵「筆記（涵蓋檢查表）＋原始逐字稿（細節來源）」
        3. 驗證新增依逐字稿規模的動態長度下限——過薄輸出觸發補強而非靜默通過
        """
        # 第一段：分段結構化萃取（豐富度的結構保證）
        notes = await self._extract_notes_with_gemini(transcript, progress_callback, template=template)

        # 第二段：筆記＋逐字稿雙輸入生成正式紀錄
        self._emit_progress(progress_callback, 84.0, "整理最終會議記錄...")
        summary = self._finalize_cloud_record_text(
            self._clean_ollama_output(
                await self._gemini_chat(
                    system_prompt,
                    self._build_cloud_summary_message(notes, transcript, template=template),
                    temperature,
                    progress_callback,
                )
            ),
            template=template,
        )

        min_chars = self._estimate_cloud_min_summary_chars(transcript)
        issues = self._validate_summary_quality(summary, notes, min_chars=min_chars, template=template)
        issues += self._validate_cloud_speaker_traceability(summary, template)
        issues += self._validate_cloud_date_grounding(summary, transcript)
        attempts = 0
        # P3 波（R23）：雲端路徑共用同一個不收斂保護（同一份驗證、同一類白燒）。
        previous_issue_signature: Optional[tuple] = None
        while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS:
            issue_signature = tuple(sorted(issues))
            if issue_signature == previous_issue_signature:
                log.warning(
                    "雲端摘要補強未收斂（問題集合與上一輪相同，共 {} 項）→ 停止再補強：{}",
                    len(issues),
                    "; ".join(issues)[:400],
                )
                break
            previous_issue_signature = issue_signature
            attempts += 1
            # 進度固定 94%（生成串流已推進至 94），補強輪不再回傳串流進度，
            # 避免進度條在補強期間倒退（審查建議）
            self._emit_progress(
                progress_callback,
                94.0,
                f"補強雲端摘要品質（第 {attempts} 輪）...",
            )
            log.info(
                f"{settings.cloud_llm_provider_label} 摘要品質補強"
                f"（第 {attempts} 輪），問題：{'; '.join(issues)}"
            )
            summary = self._finalize_cloud_record_text(
                self._clean_ollama_output(
                    await self._gemini_chat(
                        system_prompt,
                        self._build_cloud_refinement_message(summary, notes, issues, transcript, template=template),
                        0.15,
                    )
                ),
                template=template,
            )
            issues = self._validate_summary_quality(summary, notes, min_chars=min_chars, template=template)
            issues += self._validate_cloud_speaker_traceability(summary, template)
            issues += self._validate_cloud_date_grounding(summary, transcript)

        if issues:
            log.warning(
                f"{settings.cloud_llm_provider_label} 摘要仍有待補強問題: {'; '.join(issues)}"
            )

        return summary

    async def _gemini_chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2,
        progress_callback: Optional[callable] = None,
    ) -> str:
        """對 Gemini 發出單次（異步流式）對話請求並回傳清理後的內容。

        v4.6.2：串流中途斷線／逾時不在 SDK max_retries 涵蓋範圍，
        改由本層對瞬時錯誤重試——最終生成與補強輪呼叫因此自動受保護。
        """
        retries = settings.CLOUD_LLM_MAX_RETRIES
        for attempt in range(retries + 1):
            try:
                return await self._gemini_chat_once(
                    system_prompt, user_message, temperature, progress_callback
                )
            except (
                APITimeoutError,
                APIConnectionError,
                httpx.TimeoutException,
                httpx.RemoteProtocolError,
            ) as exc:
                if attempt >= retries:
                    log.exception(
                        f"{settings.cloud_llm_provider_label} 摘要生成失敗: {describe_exception(exc)}"
                    )
                    raise
                wait_seconds = (attempt + 1) * settings.LOCAL_LLM_RETRY_BACKOFF_SECONDS
                log.warning(
                    f"{settings.cloud_llm_provider_label} 請求瞬時失敗"
                    f"（第 {attempt + 1}/{retries + 1} 次）："
                    f"{describe_exception(exc)}，{wait_seconds:.0f} 秒後重試"
                )
                await asyncio.sleep(wait_seconds)
            except Exception as e:
                log.exception(
                    f"{settings.cloud_llm_provider_label} 摘要生成失敗: {describe_exception(e)}"
                )
                raise

        raise RuntimeError("雲端請求重試邏輯異常（不應執行到此）")

    async def _gemini_chat_once(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        progress_callback: Optional[callable],
    ) -> str:
        """單次雲端流式請求（由 _gemini_chat 負責重試與錯誤記錄）。"""
        client = self._get_gemini_async_client()
        model_name = settings.cloud_llm_model
        provider_label = settings.cloud_llm_provider_label

        # 使用異步流式響應以獲得實時進度更新
        summary_parts = []
        # 推理模型（Ollama Cloud deepseek-v4.1-flash 等）會把思考過程放在
        # content 以外的 reasoning/reasoning_content 欄位；只讀 content 時
        # 必須能分辨「真的空回應」與「只有 reasoning」，否則錯誤訊息會誤導。
        reasoning_chars = 0
        chunk_count = 0

        # 創建異步流式請求
        async with await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=temperature,
            stream=True  # 啟用流式響應
        ) as response:
            async for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    summary_parts.append(content)
                    chunk_count += 1

                    # 定期更新進度（每 5 個 chunk 更新一次；訊息一律中文）
                    # v4.3.3：區間改為 86-94%——萃取階段（68-84%）已有自己的
                    # 進度回報，串流進度從 65% 起算會讓進度條倒退
                    if progress_callback and chunk_count % 5 == 0:
                        progress = 86.0 + min(chunk_count / 10, 8.0)
                        progress_callback(progress, "雲端回應接收中...")
                else:
                    reasoning = getattr(delta, "reasoning", None) or getattr(
                        delta, "reasoning_content", None
                    )
                    if reasoning:
                        reasoning_chars += len(reasoning)

        summary = "".join(summary_parts)

        # 檢查摘要是否為空
        if not summary or not summary.strip():
            if reasoning_chars:
                log.warning(
                    f"{provider_label} 回應只有 reasoning（{reasoning_chars} 字）沒有正文，"
                    f"模型={model_name}"
                )
                raise RuntimeError(
                    f"摘要生成失敗：{provider_label} 模型 {model_name} 只回傳 reasoning 沒有正文"
                    "（推理預算用盡；請調整模型或輸出上限後重試）"
                )
            log.warning(f"{provider_label} 摘要生成結果為空")
            raise RuntimeError("摘要生成失敗：結果為空")

        summary = self._clean_ollama_output(summary)
        log.info(
            f"{provider_label} 摘要生成成功，模型: {model_name}，接收 {chunk_count} 個 chunks"
        )
        return summary

    async def check_ollama_health(self) -> bool:
        """
        檢查 Ollama 服務是否可用
        v4.1.0: 增強檢查 - 同時驗證配置的模型是否存在
        """
        # Apple Silicon auto 的 provider contract 是 LM Studio；不要因為
        # health endpoint 同時展示兩個 legacy 欄位而對 Ollama 發出探測。
        if resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER) == "lmstudio":
            self._ollama_model_error = None
            return False

        try:
            client = await self._get_ollama_client()
            response = await client.get("/api/tags")
            if response.status_code != 200:
                self._ollama_model_error = None
                return False

            # v4.1.0: 驗證配置的模型是否真實存在
            data = response.json()
            models = data.get("models", [])

            # 取得可用模型名稱列表
            available_models = [model.get("name") for model in models if model.get("name")]

            # 檢查配置的模型是否存在
            configured_model = settings.LOCAL_LLM_MODEL
            if configured_model not in available_models:
                log.warning(f"配置的模型 '{configured_model}' 未找到")
                log.info(f"可用模型: {', '.join(available_models)}")

                # 嘗試自動解析相容模型
                resolved_model = self._resolve_compatible_model(configured_model, available_models)
                if resolved_model:
                    log.info(f"自動解析到相容模型: {resolved_model}")
                    # 暫存解析結果（不修改配置文件）
                    self._resolved_model = resolved_model
                    self._ollama_model_error = None
                    return True
                else:
                    self._resolved_model = None
                    self._ollama_model_error = self._build_missing_model_message(
                        configured_model,
                        available_models
                    )
                    log.error(self._ollama_model_error)
                    return False

            # 模型存在，清除任何舊的解析結果
            self._resolved_model = None
            self._ollama_model_error = None
            return True

        except Exception as e:
            log.error(f"Ollama 健康檢查失敗: {describe_exception(e)}")
            self._ollama_model_error = None
            return False

    @staticmethod
    def _canonicalize_ollama_model_name(model_name: str) -> str:
        """將舊別名或常見變體正規化為較穩定的模型名稱。"""
        model_name = model_name.strip()
        if not model_name:
            return model_name

        if model_name.endswith(":latest"):
            model_name = model_name[:-7]

        if ":" not in model_name:
            return model_name

        family, variant = model_name.split(":", 1)
        variant = re.sub(r"-it-(?:qat|q\d+(?:[_A-Za-z0-9]+)*)$", "", variant, flags=re.IGNORECASE)
        variant = re.sub(r"-(?:q\d+(?:[_A-Za-z0-9]+)*|fp\d+)$", "", variant, flags=re.IGNORECASE)
        return f"{family}:{variant}"

    def _select_preferred_model(self, configured_model: str, candidates: list[str]) -> Optional[str]:
        """在候選模型中挑選最接近設定、且對 Gemma4 友善的變體。"""
        if not candidates:
            return None

        configured_model = configured_model.strip()
        normalized_configured = self._canonicalize_ollama_model_name(configured_model)
        normalized_family = normalized_configured.split(":", 1)[0]

        def score(model_name: str) -> tuple[int, int]:
            normalized_model = self._canonicalize_ollama_model_name(model_name)
            score = 0
            if model_name == configured_model:
                score += 1000
            if normalized_model == normalized_configured:
                score += 700
            if normalized_model.startswith(normalized_configured):
                score += 400
            if normalized_model.startswith(f"{normalized_family}:"):
                score += 200
            if model_name.endswith(":latest"):
                score -= 50
            if normalized_family == "gemma4" and normalized_configured == "gemma4:31b":
                lowered = model_name.lower()
                if lowered == "gemma4:31b-it-q4_k_m":
                    score += 180
                elif re.search(r"^gemma4:31b(?:-it)?-q4", lowered):
                    score += 120
            return score, -len(model_name)

        return max(candidates, key=score)

    def _resolve_compatible_model(self, configured_model: str, available_models: list) -> Optional[str]:
        """
        智能解析相容模型

        規則：
        1. 先正規化量化/別名後綴（例如 gemma4:31b-it-q4_K_M → gemma4:31b）
        2. 優先選擇同一基礎模型；Gemma4 31B 若有 q4 變體則優先採用
        3. 其次回退到同家族 latest 或其他同家族變體

        Args:
            configured_model: 配置的模型名稱
            available_models: 可用模型列表

        Returns:
            解析到的模型名稱，若無則返回 None
        """
        configured_model = configured_model.strip()
        actual_models = [model.strip() for model in available_models if model]
        if not configured_model or not actual_models:
            return None

        normalized_configured = self._canonicalize_ollama_model_name(configured_model)
        canonical_matches = [
            model for model in actual_models
            if self._canonicalize_ollama_model_name(model) == normalized_configured
        ]
        if canonical_matches:
            resolved = self._select_preferred_model(configured_model, canonical_matches)
            log.info(f"解析策略 1 成功: {configured_model} → {resolved}")
            return resolved

        if ":" in normalized_configured:
            family, variant = normalized_configured.split(":", 1)
        else:
            family, variant = normalized_configured, ""

        # 策略 2: 相同家族 + 相同基礎模型前綴
        base_candidate = f"{family}:{variant}" if variant else family
        prefix_matches = [
            model for model in actual_models
            if self._canonicalize_ollama_model_name(model).startswith(base_candidate)
        ]
        if prefix_matches:
            resolved = self._select_preferred_model(configured_model, prefix_matches)
            log.info(f"解析策略 2 成功: {configured_model} → {resolved}")
            return resolved

        # 策略 3: 同家族 latest 是安全的通用回退
        latest_candidate = f"{family}:latest"
        if latest_candidate in actual_models:
            log.info(f"解析策略 3 成功: {configured_model} → {latest_candidate}")
            return latest_candidate

        # 策略 4: 找到任何同家族的模型（優先選擇參數接近的）
        family_models = [m for m in actual_models if self._canonicalize_ollama_model_name(m).startswith(f"{family}:")]
        if family_models:
            preferred = self._select_preferred_model(configured_model, family_models)
            log.info(f"解析策略 4 成功: {configured_model} → {preferred}")
            return preferred

        # 無法解析
        log.warning(f"無法解析 {configured_model}，無相容模型")
        return None

    def _build_ollama_pull_command(self, configured_model: str) -> str:
        """為錯誤訊息提供較安全、可執行的模型安裝指令。"""
        canonical_model = self._canonicalize_ollama_model_name(configured_model)
        if canonical_model.startswith("gemma4:"):
            return "ollama pull gemma4:31b"
        return f"ollama pull {canonical_model}"

    def _build_missing_model_message(self, configured_model: str, available_models: list[str]) -> str:
        """建立清楚的模型不存在錯誤訊息。"""
        lines = [f"設定的 Ollama 模型 '{configured_model}' 不存在。"]
        if available_models:
            lines.append("")
            lines.append(f"可用模型: {', '.join(available_models)}")
            lines.append("")
            lines.append("建議處理方式：")
            lines.append(f"1. 將 LOCAL_LLM_MODEL 改為現有模型（例如 {available_models[0]}）")
            lines.append(f"2. 或在主機執行：{self._build_ollama_pull_command(configured_model)}")
        else:
            lines.append("")
            lines.append("目前 Ollama 尚未安裝任何模型。")
            lines.append(f"建議先在主機執行：{self._build_ollama_pull_command(configured_model)}")
        return "\n".join(lines)

    def _get_effective_model(self) -> str:
        """
        取得有效的模型名稱（Ollama 解析結果或 LM Studio 工作選擇）。
        """
        if resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER) == "lmstudio":
            selection = self._active_lmstudio_selection
            if selection:
                return selection.model_identifier
            selected_model = self._lmstudio_health.get("selected_model")
            if selected_model:
                return selected_model
            return self._get_lmstudio_model_override() or "LM Studio（依已載入模型）"
        return getattr(self, '_resolved_model', None) or settings.LOCAL_LLM_MODEL

    def get_effective_local_model(self) -> str:
        """公開查詢目前生效的本地模型名稱（供 /api/config 前端顯示，v4.3.1）。"""
        return self._get_effective_model()

    async def check_lmstudio_health(self) -> bool:
        """檢查 LM Studio server 與 loaded-LLM selection 狀態。"""
        provider = resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER)
        if provider == "ollama":
            self._lmstudio_health = {
                "provider": provider,
                "server_reachable": False,
                "selection_status": "not_selected",
                "loaded_llm_count": 0,
                "selected_model": None,
                "context_length": None,
            }
            return False

        try:
            instances = await self._fetch_lmstudio_loaded_instances()
        except StableServiceError as exc:
            self._set_lmstudio_health(
                server_reachable=False,
                selection_status=exc.code,
                loaded_instances=[],
            )
            return False

        status, instance = self._selection_status_for_instances(
            instances,
            self._get_lmstudio_model_override(),
        )
        selected = self._make_lmstudio_selection(instance) if status == "ready" and instance else None
        self._set_lmstudio_health(
            server_reachable=True,
            selection_status=status,
            loaded_instances=instances,
            selected=selected,
        )
        # Reachability and readiness are intentionally separate: a reachable
        # server with zero/multiple loaded LLMs is still useful health data.
        return True

    def get_local_llm_health(self) -> dict:
        """回傳 additive local-LLM health snapshot，不暴露本機路徑。"""
        snapshot = dict(self._lmstudio_health)
        # Settings can be monkeypatched/reloaded after service construction;
        # expose the current effective provider rather than a stale `auto`.
        snapshot["provider"] = resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER)
        return snapshot

    def check_gemini_available(self) -> bool:
        """檢查目前雲端 provider 的 API 是否已配置（方法名為相容 alias）"""
        try:
            self._get_gemini_api_key()
            return True
        except ValueError:
            return False

    async def check_gemini_health(self, force_refresh: bool = False) -> bool:
        """
        層級2：每日 Gemini API 健康檢查（輕量級，1次API調用/天）

        特點：
        - 自動快取24小時，避免重複調用
        - 使用最輕量的API端點（models.list()）
        - 多用戶共用快取結果（節省成本）
        - force_refresh=True 強制重新檢查

        Args:
            force_refresh: 是否強制刷新快取

        Returns:
            bool: API 是否可用
        """
        now = datetime.now()
        cache = self._gemini_health_check_cache

        # 檢查快取是否仍有效
        if not force_refresh and cache["last_check_time"]:
            age_seconds = (now - cache["last_check_time"]).total_seconds()
            if age_seconds < cache["ttl_seconds"] and cache["status"] is not None:
                log.debug(
                    f"使用快取 {settings.cloud_llm_provider_label} 健康檢查結果"
                    f"（緩存年齡: {age_seconds:.0f}秒）"
                )
                return cache["status"]

        # 執行實際的 API 檢查
        log.info(f"執行 {settings.cloud_llm_provider_label} API 健康檢查...")
        try:
            if not self.check_gemini_available():
                cache["status"] = False
                cache["last_check_time"] = now
                return False

            # 使用最輕量的 API 呼叫：列出可用模型
            client = self._get_gemini_client()
            response = client.models.list()

            # OpenAI SDK 的 SyncPage 本身即為可迭代物件；舊寫法 response.models
            # 在此 SDK 版本會 AttributeError，害健康檢查永遠回 false（v4.7.1 修）。
            # 注意：Ollama Cloud 的 /v1/models 是公開端點，200 只證明端點可達，
            # 不代表金鑰有效（金鑰錯誤的 401 只會在第一次 chat 呼叫時出現）。
            result = len(list(response)) > 0

            cache["status"] = result
            cache["last_check_time"] = now
            log.info(
                f"{settings.cloud_llm_provider_label} 健康檢查完成："
                f"{'✓ 可用' if result else '✗ 不可用'}"
            )
            return result

        except Exception as e:
            log.warning(
                f"{settings.cloud_llm_provider_label} 健康檢查失敗: {describe_exception(e)}"
            )
            cache["status"] = False
            cache["last_check_time"] = now
            return False

    def reset_gemini_health_cache(self):
        """
        重置 Gemini 健康檢查快取
        用於環境變數更新或配置變更時
        """
        self._gemini_health_check_cache = {
            "last_check_time": None,
            "status": None,
            "ttl_seconds": 86400
        }
        log.info("已重置雲端健康檢查快取")

    async def _load_model_and_check_offload(
        self, client: httpx.AsyncClient, model: str, context_tokens: int
    ) -> Optional[tuple[int, int]]:
        """load-only 載入模型並回傳 (/api/ps 的 size, size_vram)；查詢失敗回 None。

        必須帶與後續 /api/chat 相同的 options.num_ctx——Ollama runner 依 num_ctx
        載入，ctx 不一致會觸發整顆模型重載（參考專案實證教訓），warmup 就白做了。
        """
        start = asyncio.get_event_loop().time()
        response = await client.post(
            "/api/generate",
            json={
                "model": model,
                "keep_alive": settings.LOCAL_LLM_KEEP_ALIVE,
                "options": {"num_ctx": context_tokens},
            },
            timeout=settings.LOCAL_LLM_WARMUP_TIMEOUT,
        )
        response.raise_for_status()
        elapsed = asyncio.get_event_loop().time() - start
        log.info(f"本地模型預熱完成：{model}，耗時 {elapsed:.1f} 秒")

        ps = await client.get("/api/ps", timeout=10.0)
        if ps.status_code != 200:
            return None
        for loaded in ps.json().get("models", []):
            if loaded.get("name") != model and loaded.get("model") != model:
                continue
            return loaded.get("size", 0), loaded.get("size_vram", 0)
        return None

    async def _get_model_disk_size(self, client: httpx.AsyncClient, model: str) -> int:
        """從 /api/tags 取模型磁碟大小（≈權重），供 KV 量化生效 heuristic 使用。"""
        try:
            tags = await client.get("/api/tags", timeout=10.0)
            if tags.status_code != 200:
                return 0
            for item in tags.json().get("models", []):
                if item.get("name") == model or item.get("model") == model:
                    return item.get("size", 0)
        except Exception:  # noqa: BLE001
            pass
        return 0

    def _check_kv_quantization_heuristic(self, loaded_size: int, disk_size: int) -> None:
        """KV 量化生效 heuristic（best-effort 近似，v4.7.0）。

        載入大小 − 磁碟大小 ≈ KV cache＋compute buffer。正式機實測校準
        （2026-08-19）：q8 生效時 @16384 overhead ≈ 2.7GB（22.6−19.9），
        f16 特徵應 ≥ ~3.5GB。門檻依 num_ctx 線性縮放；介於兩者間不下判斷，
        避免誤報（gemma4 compute buffer 佔比大，估算誤差高）。
        """
        if not loaded_size or not disk_size or loaded_size <= disk_size:
            return
        overhead = loaded_size - disk_size
        ctx = self._effective_context_tokens()
        scale = ctx / 16384
        if overhead >= 3.5e9 * scale:
            log.warning(
                f"KV cache overhead ≈ {overhead / 1e9:.1f}GB（f16 特徵）——"
                "OLLAMA_KV_CACHE_TYPE=q8_0 可能未生效；請用 scripts/diagnose_ollama_host.ps1 "
                "檢查主機環境變數是否真的作用於 Ollama 程序（setx 常因 tray app 未重啟而無效）"
            )
        elif overhead <= 3.0e9 * scale:
            log.info(f"KV 量化已生效：overhead ≈ {overhead / 1e9:.1f}GB（q8 特徵）")

    async def warmup_local_model(self) -> None:
        """預熱本地 Ollama 模型：載入＋offload 驗證＋自我修復＋降級（v4.7.0）。

        背景：ASR 前會強制卸載模型（VRAM 交接），ASR 後第一個生成呼叫必為
        冷啟動；且 Ollama scheduler 只在載入當下依可用 VRAM 決定 layer 配置
        （offload 一旦發生就持續到下次重載）。因此這裡：
        1. load-only 載入（專屬逾時，把冷載入成本從生成呼叫拆出）
        2. /api/ps 驗證是否 offload；offload → 卸載→等待→重載（自我修復一次）
        3. 仍 offload → 本任務降級 num_ctx（LOCAL_LLM_DEGRADED_CONTEXT_TOKENS），
           確保即使主機環境（KV 量化）不可控也能全 VRAM 完成任務
        4. KV 量化生效 heuristic：提示主機 OLLAMA_KV_CACHE_TYPE 是否真的作用

        任何失敗都不上拋：warmup 只是把載入成本前移，生成呼叫自身已有重試。
        """
        # 防跨任務殘留：每個任務的 warmup 都從預設 ctx 重新出發
        self._active_context_tokens = None

        if resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER) != "ollama":
            return

        try:
            if not await self.check_ollama_health():
                return

            client = await self._get_ollama_client()
            model = self._get_effective_model()
            configured_ctx = settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS

            sizes = await self._load_model_and_check_offload(client, model, configured_ctx)
            if sizes is None:
                return
            size, size_vram = sizes

            if size and size_vram < size:
                if size_vram == 0:
                    # 正式機實測（2026-08-19）：長駐一個月的 Ollama 程序因驅動
                    # 更新/睡眠喚醒失去 GPU，之後所有載入 100% 走 CPU（GPU 明明
                    # 有 21.9GB 可用）——這種情況重載無效，必須重啟 Ollama 程序
                    log.warning(
                        "本地模型 100% 在 CPU（size_vram=0）——Ollama 程序疑已失去 GPU"
                        "（常見於驅動更新/睡眠喚醒後的長駐程序），自我修復可能無效；"
                        "請在主機執行 scripts/start_ollama_optimized.ps1 重啟 Ollama"
                    )
                log.warning(
                    f"本地模型部分卸載至 CPU：size={size}, size_vram={size_vram}"
                    f"（{size_vram / size:.0%} 在 VRAM）——嘗試自我修復（卸載後重載）"
                )
                # 自我修復：卸載（含 /api/ps 輪詢確認）→ 短暫等待 → 重載
                await self.release_local_model()
                await asyncio.sleep(2.0)
                try:
                    from backend.services.device_detector import device_detector
                    device_detector.detect_best_device()
                    log.info(f"重載前可用 VRAM：{device_detector.gpu_memory_mb} MB")
                except Exception:  # noqa: BLE001
                    pass

                sizes = await self._load_model_and_check_offload(client, model, configured_ctx)
                if sizes is not None:
                    size, size_vram = sizes

                if size and size_vram < size:
                    self._active_context_tokens = settings.LOCAL_LLM_DEGRADED_CONTEXT_TOKENS
                    log.warning(
                        f"自我修復後仍部分卸載（{size_vram / size:.0%} 在 VRAM）——"
                        f"本任務降級 num_ctx={self._active_context_tokens}；"
                        "若持續發生，請將 LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS 永久調為 8192，"
                        "或在主機啟用 OLLAMA_FLASH_ATTENTION=1 + OLLAMA_KV_CACHE_TYPE=q8_0"
                    )
                    # 以降級 ctx 重載一次，把 runner 重載成本吸收在 warmup 內
                    # （否則第一個 chat 呼叫會因 ctx 改變觸發整顆模型重載）
                    degraded_sizes = await self._load_model_and_check_offload(
                        client, model, self._active_context_tokens
                    )
                    if degraded_sizes is not None:
                        size, size_vram = degraded_sizes
                        if size and size_vram >= size:
                            log.info("降級 num_ctx 後模型已完全載入 VRAM")
                else:
                    log.info("自我修復成功：模型已完全載入 VRAM")
            else:
                log.info(f"本地模型完全載入 VRAM：size={size}, size_vram={size_vram}")

            disk_size = await self._get_model_disk_size(client, model)
            self._check_kv_quantization_heuristic(size, disk_size)
        except Exception as exc:  # noqa: BLE001
            log.warning(f"本地模型預熱失敗（不影響流程，生成呼叫自帶重試）: {describe_exception(exc)}")

    async def release_local_model(self) -> None:
        """立即請 Ollama 卸載本地模型釋放 VRAM。

        單卡（24GB）上 ASR 與 LLM 會競爭 VRAM：keep_alive 讓模型在
        多階段流程間常駐（P0-7），但下一個任務的 ASR 開跑前應主動釋放，
        否則 ASR 會因可用 VRAM 不足而降級 CPU。
        """
        if resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER) != "ollama":
            return

        try:
            client = await self._get_ollama_client()
            await client.post(
                "/api/generate",
                json={"model": self._get_effective_model(), "keep_alive": 0},
                timeout=30.0,
            )
            # v4.3.2：Ollama 卸載是非同步的——若不等它真的卸完，緊接著的
            # ASR 裝置偵測會看到 VRAM 仍被佔用而誤降級 CPU（實測根因）。
            # 輪詢 /api/ps 直到已載入模型清空，最多等 15 秒。
            for _ in range(15):
                try:
                    ps = await client.get("/api/ps", timeout=5.0)
                    if ps.status_code == 200 and not ps.json().get("models"):
                        break
                except Exception:  # noqa: BLE001
                    break
                await asyncio.sleep(1.0)
            log.info("已請求 Ollama 釋放模型 VRAM（供 ASR 使用），並確認卸載狀態")
        except Exception as exc:  # noqa: BLE001
            log.debug("釋放 Ollama 模型失敗（不影響流程）: {}", describe_exception(exc))

    async def close(self):
        """關閉客戶端連接"""
        if self._ollama_client:
            await self._ollama_client.aclose()
            self._ollama_client = None
        if self._lmstudio_http_client:
            await self._lmstudio_http_client.aclose()
            self._lmstudio_http_client = None
            self._lmstudio_http_base_url = None
        if self._lmstudio_client:
            await self._lmstudio_client.close()
            self._lmstudio_client = None
            self._lmstudio_client_base_url = None


# 全域摘要服務實例
summarization_service = SummarizationService()
