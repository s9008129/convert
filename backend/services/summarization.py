"""
MeetingScribe LLM 摘要服務
支援本地模式（Ollama/LM Studio）和雲端模式（Gemini API）

v3.5.0 改進：
- 支援平台自動偵測和配置（macOS 使用 LM Studio，Windows 使用 Ollama）
- 實現 Ollama 模型 VRAM 釋放機制（keep_alive=0）
- 優化本地模型摘要品質：改善參數和提示詞策略
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx
from openai import OpenAI, AsyncOpenAI

from backend.core.config import settings
from backend.core.logger import log
from backend.core.platform_config import (
    get_global_config,
    get_config_value,
)
from backend.models.schemas import ProcessingMode


@dataclass
class LocalContextPlan:
    """本地摘要流程的上下文規劃結果。"""

    context_window_tokens: int
    estimated_transcript_tokens: int
    chunk_input_budget_tokens: int
    notes_merge_budget_tokens: int
    needs_chunking: bool
    estimated_chunk_count: int


class SummarizationService:
    """
    LLM 摘要生成服務
    支援本地模式（Ollama + Gemma4）、LM Studio（gpt-oss-20b）和雲端模式（Gemini API）
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

    LOCAL_NOTES_MERGE_PROMPT = """你要合併多份「萃取筆記」，產出一份資訊最完整、去除重複的整合版筆記。

規則：
- 保留所有明確議題、決議、待辦、數字、日期、責任人。
- 同一待辦若重複出現可合併，但不同工作項目不可硬併成一列。
- 若資訊互相矛盾，請保留在「待確認資訊」。
- 仍然使用原本的「# 萃取筆記」Markdown 結構輸出。
- 不要寫成最終會議記錄。
- 只輸出繁體中文 Markdown，不要輸出 <think>、<thought>、<details>、XML/HTML 標籤或 code fence。"""

    def __init__(self):
        """準備各種 LLM 客戶端與健康檢查快取，減少重複連線成本。"""
        self._ollama_client: Optional[httpx.AsyncClient] = None
        self._lmstudio_client: Optional[OpenAI] = None
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

    async def _get_ollama_client(self) -> httpx.AsyncClient:
        """取得 Ollama HTTP 客戶端"""
        if not self._ollama_client:
            self._ollama_client = httpx.AsyncClient(
                base_url=settings.OLLAMA_BASE_URL,
                timeout=300.0
            )
        return self._ollama_client

    def _get_lmstudio_client(self) -> OpenAI:
        """取得 LM Studio 客戶端（OpenAI 相容介面）"""
        if not self._lmstudio_client:
            # 從平台配置獲取 LM Studio 設定
            config = get_global_config()
            base_url = get_config_value(config, 'llm.lmstudio.base_url', settings.LMSTUDIO_BASE_URL)
            api_key = get_config_value(config, 'llm.lmstudio.api_key', 'not-needed')
            
            self._lmstudio_client = OpenAI(
                base_url=base_url,
                api_key=api_key
            )
            log.info(f"LM Studio 客戶端初始化完成 (base_url={base_url})")
        return self._lmstudio_client

    def _get_gemini_api_key(self) -> str:
        """安全地取得 Gemini API Key"""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("未設定 GEMINI_API_KEY 環境變數")
        return api_key

    def _get_gemini_client(self) -> OpenAI:
        """取得 Gemini API 客戶端（OpenAI 相容介面）"""
        if not self._gemini_client:
            api_key = self._get_gemini_api_key()
            self._gemini_client = OpenAI(
                api_key=api_key,
                base_url=settings.GEMINI_BASE_URL
            )
        return self._gemini_client

    def _get_gemini_async_client(self) -> AsyncOpenAI:
        """取得 Gemini API 異步客戶端（OpenAI 相容介面）"""
        if not self._gemini_async_client:
            api_key = self._get_gemini_api_key()
            self._gemini_async_client = AsyncOpenAI(
                api_key=api_key,
                base_url=settings.GEMINI_BASE_URL
            )
        return self._gemini_async_client

    async def summarize(
        self,
        transcript: str,
        mode: ProcessingMode = ProcessingMode.LOCAL,
        user_prompt: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        生成會議摘要

        Args:
            transcript: 逐字稿文字
            mode: 處理模式（local/cloud）
            user_prompt: 已淘汰（保留以相容舊版本，但無作用）
            progress_callback: 進度回調函數

        Returns:
            會議摘要（Markdown 格式）

        v3.4.1 改進：
        - 完全移除自訂格式功能
        - 統一使用系統預設格式
        - 提升本地模式輸出品質
        """
        transcript = transcript.strip()
        if not transcript:
            raise ValueError("逐字稿為空")

        self._emit_progress(progress_callback, 65.0, "生成摘要中...")

        # 統一使用系統預設格式（自訂格式功能已移除）
        system_prompt = settings.DEFAULT_SYSTEM_PROMPT
        log.info("使用系統預設格式生成會議記錄")

        if user_prompt:
            log.info("偵測到 user_prompt；摘要結構仍以系統格式為主，額外偏好將僅隨結果一併保存")

        try:
            if mode == ProcessingMode.CLOUD:
                user_message = self._build_direct_summary_message(transcript)
                summary = await self._summarize_with_gemini(system_prompt, user_message, progress_callback)
            else:
                summary = await self._summarize_with_local_pipeline(transcript, system_prompt, progress_callback)

            self._emit_progress(progress_callback, 95.0, "摘要生成完成")

            return summary

        except Exception as e:
            log.error(f"摘要生成失敗: {e}")
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

    def _build_local_context_plan(
        self,
        transcript: str,
        system_prompt: str
    ) -> LocalContextPlan:
        """根據有效上下文視窗估算是否需要分塊。"""
        transcript_tokens = self._estimate_tokens(transcript)
        context_window = settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS
        output_budget = settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS
        extraction_overhead = (
            self._estimate_tokens(system_prompt)
            + self._estimate_tokens(self.LOCAL_EXTRACTION_PROMPT)
            + 250
        )
        chunk_input_budget = max(1200, context_window - output_budget - extraction_overhead)
        chunk_input_budget = min(chunk_input_budget, 3200)
        # P0-6：合併後筆記會進入「最終生成」步驟，該步驟使用完整公務紀錄
        # System Prompt（約 1,200 tokens）＋補強重寫時還會再附一份當前摘要。
        # 預算必須以「合併 prompt」與「最終生成（含補強）」兩者中較大的
        # 開銷計算，否則最終步驟輸入會超過 num_ctx 被 Ollama 靜默截斷。
        merge_overhead = self._estimate_tokens(self.LOCAL_NOTES_MERGE_PROMPT) + 250
        final_overhead = (
            self._estimate_tokens(system_prompt)
            + output_budget  # 補強輪會把當前摘要附進輸入，以輸出預算上限估計
            + 400  # 最終生成模板與問題清單
        )
        notes_merge_budget = max(
            900,
            context_window - output_budget - max(merge_overhead, final_overhead),
        )
        effective_chunk_step = max(chunk_input_budget - 220, 1)
        estimated_chunk_count = max(1, (transcript_tokens + effective_chunk_step - 1) // effective_chunk_step)

        return LocalContextPlan(
            context_window_tokens=context_window,
            estimated_transcript_tokens=transcript_tokens,
            chunk_input_budget_tokens=chunk_input_budget,
            notes_merge_budget_tokens=notes_merge_budget,
            needs_chunking=transcript_tokens > chunk_input_budget,
            estimated_chunk_count=estimated_chunk_count,
        )

    def _split_oversized_line(self, line: str, max_input_tokens: int) -> list[str]:
        """將單行過長的逐字稿切成較小片段。"""
        fragments = [
            fragment.strip()
            for fragment in re.split(r"(?<=[。！？!?；;])\s*", line)
            if fragment.strip()
        ]
        if len(fragments) <= 1:
            max_chars = max(200, max_input_tokens * 2)
            return [line[index:index + max_chars].strip() for index in range(0, len(line), max_chars) if line[index:index + max_chars].strip()]
        return fragments

    def _split_transcript_into_chunks(self, transcript: str, max_input_tokens: int) -> list[str]:
        """依 speaker line 與自然斷點切塊，並保留少量重疊內容。"""
        raw_lines = [line.strip() for line in transcript.splitlines() if line.strip()]
        if not raw_lines:
            return []

        normalized_lines: list[str] = []
        for line in raw_lines:
            if self._estimate_tokens(line) <= max_input_tokens:
                normalized_lines.append(line)
            else:
                normalized_lines.extend(self._split_oversized_line(line, max_input_tokens))

        chunks: list[str] = []
        current_lines: list[str] = []
        current_tokens = 0
        overlap_lines = max(1, settings.LOCAL_LLM_CHUNK_OVERLAP_LINES)

        for line in normalized_lines:
            line_tokens = self._estimate_tokens(line) + 1
            if current_lines and current_tokens + line_tokens > max_input_tokens:
                chunks.append("\n".join(current_lines).strip())

                carry_lines = current_lines[-overlap_lines:]
                carry_tokens = sum(self._estimate_tokens(item) + 1 for item in carry_lines)
                max_overlap_tokens = max(12, max_input_tokens // 2)
                while len(carry_lines) > 1 and carry_tokens > max_overlap_tokens:
                    removed = carry_lines.pop(0)
                    carry_tokens -= self._estimate_tokens(removed) + 1

                current_lines = carry_lines[:]
                current_tokens = carry_tokens

            current_lines.append(line)
            current_tokens += line_tokens

        if current_lines:
            chunks.append("\n".join(current_lines).strip())

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
    _REQUIRED_SECTION_PATTERNS = [
        ("會議名稱", re.compile(r"會議名稱\s*[:：]")),
        ("會議時間", re.compile(r"會議時間\s*[:：]")),
        ("會議地點", re.compile(r"會議地點\s*[:：]")),
        ("主席", re.compile(r"主\s*席\s*[:：]")),
        ("出席人員", re.compile(r"出席人員\s*[:：]")),
        ("列席人員", re.compile(r"列席人員\s*[:：]")),
        ("記錄", re.compile(r"記\s*錄\s*[:：]")),
        ("一、報告事項", re.compile(r"一、\s*報告事項")),
        ("二、討論事項", re.compile(r"二、\s*討論事項")),
        ("案由", re.compile(r"案由\s*[:：]")),
        ("說明", re.compile(r"說明\s*[:：]")),
        ("各單位意見", re.compile(r"各單位意見")),
        ("決議", re.compile(r"決議\s*[:：]")),
        ("三、主席裁示事項", re.compile(r"三、\s*主席裁示事項")),
    ]

    def _validate_summary_quality(self, summary: str, extracted_notes: str) -> list[str]:
        """針對最終摘要做結構與召回檢查。"""
        issues: list[str] = []
        cleaned = self._clean_ollama_output(summary)

        for label, pattern in self._REQUIRED_SECTION_PATTERNS:
            if not pattern.search(cleaned):
                issues.append(f"缺少區塊：{label}")

        if not re.search(r"主辦單位\s*[:：]", cleaned):
            issues.append("缺少主辦單位資訊")

        if not re.search(r"辦理期程\s*[:：]", cleaned):
            issues.append("缺少辦理期程資訊")

        if len(cleaned) < 250:
            issues.append("摘要內容過短")

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

    def _build_notes_merge_message(self, notes_group: list[str], round_index: int, total_groups: int) -> str:
        """建立多份萃取筆記的合併訊息。"""
        combined = "\n\n---\n\n".join(
            f"### 筆記 {index}\n{notes}"
            for index, notes in enumerate(notes_group, start=1)
        )
        return f"""以下是第 {round_index} 輪整併要處理的 {len(notes_group)} 份萃取筆記（本輪共 {total_groups} 組）：

{combined}

請輸出單一份整合後的「# 萃取筆記」Markdown，保留所有重要待辦與決議。"""

    def _build_summary_from_notes_message(self, extracted_notes: str) -> str:
        """建立最終會議記錄生成訊息。"""
        return f"""請根據以下萃取筆記，輸出最終版本的會議記錄。

要求：
- 所有明確待辦都必須出現在待辦事項表格中
- 不要把多個不同待辦合併成單一籠統項目；可分列追蹤者請拆成多列
- 若資訊不足，請標示「（待確認）」或「逐字稿未提及」
- 只輸出最終 Markdown，不要附加說明
- 全文必須使用繁體中文（台灣用語），不要輸出簡體中文或任何 <think> / <thought> / <details> / XML / HTML 標籤

萃取筆記：
{extracted_notes}"""

    def _build_refinement_message(
        self,
        current_summary: str,
        extracted_notes: str,
        issues: list[str]
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
- 不要輸出 <think>、<thought>、<details>、XML/HTML 標籤或 code fence"""

    def _build_direct_summary_message(self, transcript: str) -> str:
        """雲端模式直接摘要訊息。"""
        return f"""請根據以下逐字稿整理會議記錄。

要求：
- 輸出以繁體中文（台灣用語）為主
- 專有名詞、產品名、英文縮寫若影響準確性可保留
- 不要遺漏明確待辦、日期、責任人、數字與最終決議
- 只輸出最終 Markdown
- 不要輸出簡體中文、<think>、<thought>、<details>、XML/HTML 標籤或 code fence

逐字稿：
{transcript}"""

    def _build_cloud_refinement_message(self, original_user_message: str, issues: list[str]) -> str:
        """雲端模式的補強訊息：重附原逐字稿並列出必須修正的問題。"""
        issue_lines = "\n".join(f"- {issue}" for issue in issues)
        return f"""你剛才輸出的會議記錄不合格，請依問題清單完整重新輸出（不要只補修補片段）。

必須修正的問題：
{issue_lines}

務必遵守：
- 第一行必須以「會議名稱：」開頭，不得有任何前言、分析段、評估說明或英文整句
- 全文使用繁體中文（台灣用語）；不得輸出簡體中文、<think>、<thought>、<details>、XML/HTML 標籤或 code fence
- 未明確提及者填「（待確認）」，不得杜撰或臆測

{original_user_message}"""

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
        notes_merge_budget_tokens: int,
        progress_callback: Optional[callable] = None
    ) -> str:
        """反覆整併 chunk 筆記，直到可被最終摘要步驟安全承接。"""
        current_notes = [self._clean_ollama_output(note) for note in extracted_notes if note and note.strip()]
        if not current_notes:
            return self._empty_extraction_notes()

        # 收斂保護（v4.2）：整併輸出若無法縮到預算內，舊邏輯會無限重壓縮。
        # 三重防線：輪數上限、縮減停滯偵測、最終硬截斷保底。
        round_index = 1
        previous_total_tokens: Optional[int] = None
        merge_predict_cap = min(
            settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
            max(notes_merge_budget_tokens, 512),
        )
        while len(current_notes) > 1 or self._estimate_tokens(current_notes[0]) > notes_merge_budget_tokens:
            total_tokens = sum(self._estimate_tokens(note) for note in current_notes)
            if round_index > settings.LOCAL_LLM_MAX_MERGE_ROUNDS:
                log.warning(
                    "筆記整併達輪數上限（{} 輪）仍超出預算（{} tokens > {}），改用硬截斷",
                    settings.LOCAL_LLM_MAX_MERGE_ROUNDS, total_tokens, notes_merge_budget_tokens,
                )
                break
            if previous_total_tokens is not None and total_tokens >= previous_total_tokens * 0.9:
                log.warning(
                    "筆記整併縮減停滯（{} → {} tokens），停止整併改用硬截斷",
                    previous_total_tokens, total_tokens,
                )
                break
            previous_total_tokens = total_tokens

            note_groups = self._group_texts_by_budget(current_notes, notes_merge_budget_tokens)
            if len(note_groups) == 1 and len(current_notes) == 1:
                break

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
                    self._build_notes_merge_message(note_group, round_index, len(note_groups)),
                    temperature=0.1,
                    # 輸出上限綁定預算：讓整併輸出「物理上」不可能超過預算太多
                    num_predict=merge_predict_cap,
                )
                merged_round.append(self._clean_ollama_output(merged))

            current_notes = merged_round
            round_index += 1

        combined = current_notes[0] if len(current_notes) == 1 else "\n\n".join(current_notes)
        return self._truncate_to_token_budget(combined, notes_merge_budget_tokens)

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

    async def _select_local_engine(self) -> str:
        """選擇可用的本地 LLM 引擎。"""
        if await self.check_ollama_health():
            log.info("使用 Ollama 本地模式")
            return "ollama"

        if await self.check_lmstudio_health():
            log.info("使用 LM Studio 本地模式")
            return "lmstudio"

        if self._ollama_model_error:
            raise RuntimeError(self._ollama_model_error)

        raise RuntimeError("本地 LLM 不可用：請確認 Ollama 或 LM Studio 已啟動")

    async def _generate_with_local_engine(
        self,
        engine: str,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None,
        temperature: float = 0.2,
        num_predict: Optional[int] = None
    ) -> str:
        """對選定的本地引擎執行一次生成。"""
        if engine == "ollama":
            return await self._summarize_with_ollama(
                system_prompt,
                user_message,
                progress_callback=progress_callback,
                temperature=temperature,
                num_predict=num_predict,
            )

        if engine == "lmstudio":
            return await self._summarize_with_lmstudio(
                system_prompt,
                user_message,
                progress_callback=progress_callback,
                temperature=temperature,
                max_tokens=num_predict,
            )

        raise RuntimeError(f"未知的本地引擎: {engine}")

    async def _summarize_with_local_pipeline(
        self,
        transcript: str,
        system_prompt: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """本地模式的 extraction-first + chunk-merge + refine 流程。"""
        engine = await self._select_local_engine()
        plan = self._build_local_context_plan(transcript, system_prompt)
        log.info(
            "本地摘要上下文規劃："
            f"estimated_tokens={plan.estimated_transcript_tokens}, "
            f"chunk_budget={plan.chunk_input_budget_tokens}, "
            f"merge_budget={plan.notes_merge_budget_tokens}, "
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
        for chunk_index, chunk in enumerate(chunks, start=1):
            progress = 68.0 + ((chunk_index - 1) / max(total_chunks, 1)) * 12.0
            self._emit_progress(progress_callback, progress, f"萃取逐字稿重點 {chunk_index}/{total_chunks}...")
            notes = await self._generate_with_local_engine(
                engine,
                self.LOCAL_EXTRACTION_PROMPT,
                self._build_chunk_extraction_message(chunk, chunk_index, total_chunks),
                temperature=0.1,
                num_predict=settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
            )
            extracted_notes.append(self._clean_ollama_output(notes))

        merged_notes = await self._merge_notes_until_fit(
            engine,
            extracted_notes,
            plan.notes_merge_budget_tokens,
            progress_callback,
        )

        self._emit_progress(progress_callback, 86.0, "整理最終會議記錄...")
        summary = await self._generate_with_local_engine(
            engine,
            system_prompt,
            self._build_summary_from_notes_message(merged_notes),
            temperature=0.2,
            num_predict=settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
        )
        # P1-9：記錄級後處理（英文清理/結構補全）一律在「驗證前」執行，
        # 驗證是最後一關，通過後不得再被任何流程改寫。
        summary = self._finalize_record_text(self._clean_ollama_output(summary))

        issues = self._validate_summary_quality(summary, merged_notes)
        attempts = 0
        while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS:
            attempts += 1
            self._emit_progress(progress_callback, 88.0 + attempts, f"補強摘要完整性（第 {attempts} 輪）...")
            summary = await self._generate_with_local_engine(
                engine,
                system_prompt,
                self._build_refinement_message(summary, merged_notes, issues),
                temperature=0.15,
                num_predict=settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
            )
            summary = self._finalize_record_text(self._clean_ollama_output(summary))
            issues = self._validate_summary_quality(summary, merged_notes)

        if issues:
            log.warning(f"本地摘要仍有待補強問題: {'; '.join(issues)}")

        return summary

    @staticmethod
    def _finalize_record_text(summary: str) -> str:
        """會議紀錄記錄級後處理（自 task_processor 移入，P1-9）。"""
        from backend.core.glossary import english_protected_terms
        from backend.core.text_postprocess import finalize_record

        try:
            protected = english_protected_terms()
        except Exception:  # noqa: BLE001
            protected = set()
        return finalize_record(summary, protected_terms=protected)


    async def generate_local(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.0,
        num_predict: Optional[int] = None,
    ) -> str:
        """以本地引擎執行單次生成（供逐字稿語意校正等模組共用，P1-3）。"""
        engine = await self._select_local_engine()
        return await self._generate_with_local_engine(
            engine,
            system_prompt,
            user_message,
            temperature=temperature,
            num_predict=num_predict,
        )

    async def _summarize_with_ollama(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None,
        temperature: float = 0.2,
        num_predict: Optional[int] = None,
    ) -> str:
        """
        使用 Ollama 本地模式生成摘要

        v4.2.1 改進：
        - Gemma4 預設參數：top_k 64、top_p 0.95、repeat_penalty 1.08
        - 維持 8192 context 預設，避免把高風險視窗擴大成全域預設
        - 維持 keep_alive=0 確保 VRAM 釋放

        v3.5.2 改進：
        - 新增 keep_alive=0 參數，使用完畢後立即釋放 VRAM
        - 優化參數以提升長逐字稿處理品質
        - 增加 num_ctx 到 16384 以處理更長的逐字稿
        """
        client = await self._get_ollama_client()

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
                    "stream": False,
                    # P0-7：三階段流程會連續呼叫十數次，keep_alive=0 會導致每階段
                    # 重載 20GB 模型。改為可設定（預設 10m），流程結束後自然逾時釋放。
                    "keep_alive": settings.LOCAL_LLM_KEEP_ALIVE,
                    "options": {
                        # 重試時略升溫度以跳出空回應狀態
                        "temperature": temperature if attempt == 0 else max(temperature, 0.3),
                        "top_p": 0.95,
                        "top_k": 64,
                        "repeat_penalty": 1.08,
                        "num_ctx": settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS,
                        "num_predict": num_predict or settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
                        "stop": ["</think>", "</thought>", "</details>", "---\n\n---"]  # 停止標記
                    }
                }
                if send_think_field:
                    payload["think"] = False

                response = await client.post("/api/chat", json=payload, timeout=600.0)
                if response.status_code == 400 and send_think_field:
                    log.info("模型不支援 think 參數，改以相容模式重送")
                    send_think_field = False
                    response = await client.post(
                        "/api/chat",
                        json={k: v for k, v in payload.items() if k != "think"},
                        timeout=600.0,
                    )
                response.raise_for_status()

                self._emit_progress(progress_callback, 85.0, "處理摘要結果...")

                data = response.json()
                raw_content = data.get("message", {}).get("content", "")
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
            log.error(f"Ollama 摘要生成失敗: {e}")
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
    ) -> str:
        """
        使用 LM Studio（OpenAI 相容）生成摘要
        v3.5.0: 從平台配置讀取模型和參數
        """
        client = self._get_lmstudio_client()
        config = get_global_config()
        model = get_config_value(config, 'llm.lmstudio.model', settings.LMSTUDIO_MODEL)
        temperature = get_config_value(config, 'llm.lmstudio.temperature', temperature)
        max_tokens = get_config_value(
            config,
            'llm.lmstudio.max_tokens',
            max_tokens or settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
        )

        try:
            self._emit_progress(progress_callback, 65.0, f"載入 LM Studio 模型 ({model})...")
            log.info(f"使用 LM Studio 生成摘要 (model={model}, temperature={temperature})")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            self._emit_progress(progress_callback, 85.0, "處理摘要結果...")

            summary = self._clean_ollama_output(response.choices[0].message.content or "")

            # 檢查摘要是否為空
            if not summary or not summary.strip():
                log.warning("LM Studio 摘要生成結果為空")
                raise RuntimeError("摘要生成失敗：結果為空")

            log.info(f"LM Studio 摘要生成成功，模型: {model}")
            return summary.strip()

        except Exception as e:
            log.error(f"LM Studio 摘要生成失敗: {e}")
            raise RuntimeError(f"LM Studio 服務不可用: {e}")

    async def _summarize_with_gemini(
        self,
        system_prompt: str,
        user_message: str,
        progress_callback: Optional[callable] = None,
        temperature: float = 0.2,
    ) -> str:
        """使用 Gemini API 雲端模式生成摘要，並比照本地流程做品質驗證與補強重寫。

        雲端為單次直接摘要（無萃取筆記），故召回類檢查退化處理（傳入空筆記，
        不誤報待辦遺漏），重點放在英文前言/回吐評估標準、簡體漂移、思考標籤
        洩漏與公務欄位結構是否完整——出問題的歷史輸出正是雲端路徑。
        """
        summary = self._finalize_record_text(
            await self._gemini_chat(system_prompt, user_message, temperature, progress_callback)
        )

        issues = self._validate_summary_quality(summary, "")
        attempts = 0
        while issues and attempts < settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS:
            attempts += 1
            self._emit_progress(
                progress_callback,
                min(94.0, 90.0 + attempts),
                f"補強雲端摘要品質（第 {attempts} 輪）...",
            )
            log.info(f"Gemini 摘要品質補強（第 {attempts} 輪），問題：{'; '.join(issues)}")
            summary = self._finalize_record_text(
                await self._gemini_chat(
                    system_prompt,
                    self._build_cloud_refinement_message(user_message, issues),
                    0.15,
                    progress_callback,
                )
            )
            issues = self._validate_summary_quality(summary, "")

        if issues:
            log.warning(f"Gemini 摘要仍有待補強問題: {'; '.join(issues)}")

        return summary

    async def _gemini_chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.2,
        progress_callback: Optional[callable] = None,
    ) -> str:
        """對 Gemini 發出單次（異步流式）對話請求並回傳清理後的內容。"""
        client = self._get_gemini_async_client()

        try:
            # 使用異步流式響應以獲得實時進度更新
            summary_parts = []
            chunk_count = 0

            # 創建異步流式請求
            async with await client.chat.completions.create(
                model=settings.GEMINI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                stream=True  # 啟用流式響應
            ) as response:
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        summary_parts.append(content)
                        chunk_count += 1

                        # 定期更新進度（每 5 個 chunk 更新一次）
                        if progress_callback and chunk_count % 5 == 0:
                            progress = 65.0 + min((chunk_count / 10) * 10, 30)  # 65-95%
                            progress_callback(progress, f"生成摘要中... ({chunk_count} chunks)")

            summary = "".join(summary_parts)

            # 檢查摘要是否為空
            if not summary or not summary.strip():
                log.warning("Gemini 摘要生成結果為空")
                raise RuntimeError("摘要生成失敗：結果為空")

            summary = self._clean_ollama_output(summary)
            log.info(f"Gemini 摘要生成成功，模型: {settings.GEMINI_MODEL}，接收 {chunk_count} 個 chunks")
            return summary

        except Exception as e:
            log.error(f"Gemini 摘要生成失敗: {e}")
            raise

    async def check_ollama_health(self) -> bool:
        """
        檢查 Ollama 服務是否可用
        v4.1.0: 增強檢查 - 同時驗證配置的模型是否存在
        """
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
            log.error(f"Ollama 健康檢查失敗: {e}")
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
        取得有效的模型名稱（若有解析結果則使用解析結果）
        """
        return getattr(self, '_resolved_model', None) or settings.LOCAL_LLM_MODEL

    async def check_lmstudio_health(self) -> bool:
        """檢查 LM Studio 服務是否可用"""
        try:
            client = self._get_lmstudio_client()
            client.models.list()
            return True
        except Exception:
            return False

    def check_gemini_available(self) -> bool:
        """檢查 Gemini API 是否已配置"""
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
                log.debug(f"使用快取 Gemini 健康檢查結果（緩存年齡: {age_seconds:.0f}秒）")
                return cache["status"]

        # 執行實際的 API 檢查
        log.info("執行 Gemini API 健康檢查...")
        try:
            if not self.check_gemini_available():
                cache["status"] = False
                cache["last_check_time"] = now
                return False

            # 使用最輕量的 API 呼叫：列出可用模型
            client = self._get_gemini_client()
            response = client.models.list()

            # 驗證是否能取得模型列表
            result = len(list(response.models)) > 0

            cache["status"] = result
            cache["last_check_time"] = now
            log.info(f"Gemini 健康檢查完成：{'✓ 可用' if result else '✗ 不可用'}")
            return result

        except Exception as e:
            log.warning(f"Gemini 健康檢查失敗: {str(e)}")
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
        log.info("已重置 Gemini 健康檢查快取")

    async def release_local_model(self) -> None:
        """立即請 Ollama 卸載本地模型釋放 VRAM。

        單卡（24GB）上 ASR 與 LLM 會競爭 VRAM：keep_alive 讓模型在
        多階段流程間常駐（P0-7），但下一個任務的 ASR 開跑前應主動釋放，
        否則 ASR 會因可用 VRAM 不足而降級 CPU。
        """
        try:
            client = await self._get_ollama_client()
            await client.post(
                "/api/generate",
                json={"model": self._get_effective_model(), "keep_alive": 0},
                timeout=30.0,
            )
            log.info("已請求 Ollama 釋放模型 VRAM（供 ASR 使用）")
        except Exception as exc:  # noqa: BLE001
            log.debug("釋放 Ollama 模型失敗（不影響流程）: {}", exc)

    async def close(self):
        """關閉客戶端連接"""
        if self._ollama_client:
            await self._ollama_client.aclose()
            self._ollama_client = None


# 全域摘要服務實例
summarization_service = SummarizationService()
