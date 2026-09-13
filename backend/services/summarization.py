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
    LOCAL_LLM_MERGE_VISIBLE_TARGET_TOKENS = 900

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
        chunk_input_budget = min(chunk_input_budget, 3200)
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
        merge_visible_target_tokens = self.LOCAL_LLM_MERGE_VISIBLE_TARGET_TOKENS
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
        )

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
        """將待辦事項文字正規化，方便比對是否遺漏。"""
        return re.sub(r"[\s\t\r\n:：,，。；;（）()「」『』【】\[\]／/\\-]+", "", text).lower()

    def _extract_action_table_keys(self, markdown: str) -> set[str]:
        """只從萃取筆記的『待辦清單』Markdown 表格列抽取待辦關鍵字。

        僅取表格第一欄（待辦事項本身），刻意忽略議題、日期、參與者等非待辦
        條列，避免把會議資訊誤判成待辦而造成假性「遺漏」。
        """
        action_keys: set[str] = set()

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

            normalized = self._normalize_action_key(cells[0])
            if normalized:
                action_keys.add(normalized)

        return action_keys

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
        missing_actions = {key for key in expected_actions if key not in normalized_summary}
        if missing_actions:
            issues.append(f"待辦事項遺漏 {len(missing_actions)} 項")

        return issues

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

    def _build_summary_from_notes_message(
        self,
        extracted_notes: str,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """建立最終會議記錄生成訊息。"""
        return f"""請根據以下萃取筆記，輸出最終版本的會議記錄。

要求：
- 所有明確待辦都必須出現在待辦事項表格中
- 不要把多個不同待辦合併成單一籠統項目；可分列追蹤者請拆成多列
- 若資訊不足，請標示「（待確認）」或「逐字稿未提及」
- 只輸出最終 Markdown，不要附加說明
- 全文必須使用繁體中文（台灣用語），不要輸出簡體中文或任何 <think> / <thought> / <details> / XML / HTML 標籤{self._template_generation_extra(template)}

萃取筆記：
{extracted_notes}"""

    def _build_refinement_message(
        self,
        current_summary: str,
        extracted_notes: str,
        issues: list[str],
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """建立摘要補強訊息。"""
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
- 不要輸出 <think>、<thought>、<details>、XML/HTML 標籤或 code fence
- 條列編號須依系統提示詞規定之階層（一、→（一）→1、……）由上而下使用，不得用「-」「•」或跳層{self._template_generation_extra(template)}"""

    def _build_cloud_summary_message(
        self,
        extracted_notes: str,
        transcript: str,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """雲端最終生成訊息（v4.3.3）：筆記當涵蓋檢查表、逐字稿當細節來源。

        本地因 context 有限只能餵筆記；雲端長上下文沒有這個限制——
        逐字稿一併附上，生成時才有細節可以引用，而不是被迫轉寫筆記骨架。
        """
        return f"""請根據以下「萃取筆記」與「原始逐字稿」，輸出最終版本的會議記錄。

要求：
- 萃取筆記是涵蓋度檢查表：筆記中的每個議題、決議、待辦都必須出現在會議記錄中
- 原始逐字稿是細節來源：各單位意見、決議與裁示須保留具體理由、數據、案例、統一口徑與執行方式，嚴禁把多句實質討論壓縮成一句籠統敘述
- 所有明確待辦都必須出現在待辦事項中；不要把多個不同待辦合併成單一籠統項目，可分列追蹤者請拆成多列
- 若資訊不足，請標示「（待確認）」或「逐字稿未提及」
- 只輸出最終 Markdown，不要附加說明
- 全文必須使用繁體中文（台灣用語），不要輸出簡體中文或任何 <think> / <thought> / <details> / XML / HTML 標籤{self._template_generation_extra(template)}

萃取筆記：
{extracted_notes}

原始逐字稿：
{transcript}"""

    def _build_cloud_refinement_message(
        self,
        current_summary: str,
        extracted_notes: str,
        issues: list[str],
        transcript: str,
        template: Optional[MeetingTemplate] = None,
    ) -> str:
        """雲端補強訊息（v4.3.3）：共用補強模板之外附上逐字稿。

        沒有逐字稿的補強只能就筆記改寫措辭；「內容過短」這類豐富度問題
        必須回到原文找細節才補得回來。
        """
        base = self._build_refinement_message(current_summary, extracted_notes, issues, template=template)
        return f"""{base}

原始逐字稿（補充細節時以此為準）：
{transcript}"""

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
        round_index = 1
        previous_total_tokens: Optional[int] = None
        previous_note_count: Optional[int] = None
        while len(current_notes) > 1 or self._estimate_tokens(current_notes[0]) > merge_visible_target_tokens:
            total_tokens = sum(self._estimate_tokens(note) for note in current_notes)
            if round_index > settings.LOCAL_LLM_MAX_MERGE_ROUNDS:
                raise StableServiceError(
                    LOCAL_LLM_MERGE_NOT_CONVERGED,
                    f"萃取筆記整併在 {settings.LOCAL_LLM_MAX_MERGE_ROUNDS} 輪內未收斂到可見目標"
                    f"（目前 {len(current_notes)} 份筆記、{total_tokens} tokens > 目標 "
                    f"{merge_visible_target_tokens} tokens）。為保留全部來源事實（含尾端決議／"
                    "待辦），已停止整併並回退為明示逐字稿 fallback；請調大 context window"
                    "或提高 LOCAL_LLM_MAX_MERGE_ROUNDS 後重試",
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
        if lmstudio_selection and lmstudio_selection.context_length:
            context_tokens = min(context_tokens, lmstudio_selection.context_length)
        plan = self._build_local_context_plan(
            transcript, system_prompt, template=template,
            context_window_tokens=context_tokens,
        )
        log.info(
            "本地摘要上下文規劃："
            f"context_window={context_tokens}, "
            f"estimated_tokens={plan.estimated_transcript_tokens}, "
            f"chunk_budget={plan.chunk_input_budget_tokens}, "
            f"merge_input_budget={plan.merge_input_budget_tokens}, "
            f"merge_visible_target={plan.merge_visible_target_tokens}, "
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
            notes = await self._generate_with_local_engine(
                engine,
                self._local_extraction_prompt(template),
                self._build_chunk_extraction_message(chunk, chunk_index, total_chunks),
                temperature=0.1,
                num_predict=settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
                context_window_tokens=context_tokens,
                lmstudio_selection=lmstudio_selection,
            )
            extracted_notes.append(self._clean_ollama_output(notes))

        extraction_duration = time.monotonic() - extraction_started
        merged_notes = await self._merge_notes_until_fit(
            engine,
            extracted_notes,
            plan.merge_visible_target_tokens,
            progress_callback,
            context_window_tokens=context_tokens,
            lmstudio_selection=lmstudio_selection,
            merge_input_budget_tokens=plan.merge_input_budget_tokens,
            merge_provider_output_tokens=plan.merge_provider_output_tokens,
        )

        merge_duration = time.monotonic() - extraction_duration - extraction_started
        self._emit_progress(progress_callback, 86.0, "整理最終會議記錄...")
        summary = await self._generate_with_local_engine(
            engine,
            system_prompt,
            self._build_summary_from_notes_message(merged_notes, template=template),
            temperature=0.2,
            num_predict=settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
            context_window_tokens=context_tokens,
            lmstudio_selection=lmstudio_selection,
        )
        # P1-9：記錄級後處理（英文清理/結構補全）一律在「驗證前」執行，
        # 驗證是最後一關，通過後不得再被任何流程改寫。
        summary = self._finalize_record_text(self._clean_ollama_output(summary), template=template)

        issues = self._validate_summary_quality(summary, merged_notes, template=template)
        attempts = 0
        while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS:
            attempts += 1
            self._emit_progress(progress_callback, 88.0 + attempts, f"補強摘要完整性（第 {attempts} 輪）...")
            summary = await self._generate_with_local_engine(
                engine,
                system_prompt,
                self._build_refinement_message(summary, merged_notes, issues, template=template),
                temperature=0.15,
                num_predict=settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
                context_window_tokens=context_tokens,
                lmstudio_selection=lmstudio_selection,
            )
            summary = self._finalize_record_text(self._clean_ollama_output(summary), template=template)
            issues = self._validate_summary_quality(summary, merged_notes, template=template)

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
        )

        return summary

    @staticmethod
    def _finalize_record_text(summary: str, template: Optional[MeetingTemplate] = None) -> str:
        """會議紀錄記錄級後處理（自 task_processor 移入，P1-9）。"""
        from backend.core.glossary import english_protected_terms
        from backend.core.text_postprocess import finalize_record

        try:
            protected = english_protected_terms()
        except Exception:  # noqa: BLE001
            protected = set()
        return finalize_record(summary, protected_terms=protected, template=template)


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
                        "top_p": 0.95,
                        "top_k": 64,
                        "repeat_penalty": 1.08,
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

    async def _lmstudio_chat_request(
        self,
        client,
        selection: LMStudioModelSelection,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> object:
        """單次 chat.completions.create（含既有 transient/HTTP 錯誤映射）。

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
        for attempt in range(retries + 1):
            try:
                return await client.chat.completions.create(
                    model=selection.model_identifier,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
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
        """雲端分段併發萃取（v4.3.3）。

        分塊密度沿用地端實證值（settings.CLOUD_LLM_CHUNK_TOKENS）：
        LLM 輸出長度不會隨輸入等比放大，唯有把逐字稿切小段、逼模型
        對每一段都做完整萃取，筆記的資訊密度才有結構性保證。
        雲端上下文充足，分段筆記直接零損串接，不需要地端的有損整併。
        """
        chunks = self._split_transcript_into_chunks(
            transcript, settings.CLOUD_LLM_CHUNK_TOKENS
        ) or [transcript]
        total_chunks = len(chunks)
        self._emit_progress(
            progress_callback, 68.0, f"萃取逐字稿重點（雲端，共 {total_chunks} 段）..."
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
        summary = self._finalize_record_text(
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
        attempts = 0
        while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS:
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
            summary = self._finalize_record_text(
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
