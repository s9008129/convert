# -*- coding: utf-8 -*-
"""P4-A（T20260922-2037-02 §9.3）逐條對帳擴類 —— 契約測試（W1）。

契約來源：handoff §2.1／§4.2／§7.1／§11-C1 與 plan §9.3。

A 類（正反例＋三種模式）：
  T-01 議題抽取：區塊限定、佔位／過短濾除、決議與討論重點不混入
  T-02 決議抽取：`*討論重點*` 不列入（本波不做）
  T-03 無任何標題時退化全篇掃描（仍濾佔位）
  T-04 同鍵去重保留首現
  T-05 數字抽取：單位錨定＋同句收集（`800 塊` 同句收 17／13,600）
  T-06 數字抽取：無單位句不收集（時間／編號不誤收）
  T-07 千分位與純數字同值去重（`13,600`／`13600`）
  T-08 個位數與全零不收集
  T-09【C1 阻斷級反例】數字比對前先剝來源標註：`（科長，00:17:52）` 不得把逐字稿的
       「17」洗成已涵蓋
  T-10 千分位互認：紀錄 `13,600 元` ≡ 逐字稿 `13600`
  T-11 日期抽取：四樣式＋範圍檢查（13／45、40月1日 不收集）
  T-12 日期等價：`11月1日 ≡ 11月1號 ≡ 11/1`、`10月底`、`下週一 ≡ 下個禮拜一`（含反例）
  T-13 enforce（預設）：問題併入清單，每項附逐字稿原文片段
  T-14 observe：只記 log／`cov_*` metrics；issues 為空（品質零變化）
  T-15 off：完全不跑（無覆蓋率 log／無 cov_* metrics）＋與本波前**函式級 golden**
       byte 相同（同一輸入、同一 log，wall-clock 欄位除外）
       T-15b＝地端 pipeline 全鏈 golden；T-15c＝enforce 時 metrics 行實際帶 cov_* 欄位
  T-16 空期望集合：log.warning＋`cov_expected_*=0`（不得靜默 no-op）
  T-17 `LOCAL_LLM_RECORD_COVERAGE_CATEGORIES` 可縮類別（未選類別完全不跑）
  T-18 `LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT`：超出以「其餘 N 項」帶過
  T-19 待辦期望集合為空的 WARNING：off 時完全靜音（不洩漏到本波前行為）

P4-C（W-1／W-2；plan §9.5「本機可執行」層）：
  P-01 Ollama options 讀同一份 config（payload 級；不得寫死 0.95／64）
  P-02 think 欄位 400 降級路徑保留
  P-03 補強階段 context 不足 → WARNING（與生成階段同構）

全部以 fake／payload 級斷言，不依賴 LM Studio／Ollama 服務或網路。
"""

import os
import re
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-t20260923-p4a-"))

from unittest.mock import AsyncMock, Mock  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from loguru import logger as loguru_logger  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.core.templates import get_template  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402


TRANSCRIPT_LINE = "[00:00:10-00:00:40] 發言者1：請各股配合辦理組織規程調整，並於本週五前回報。"

# 萃取筆記 fixture（形狀照 `LOCAL_EXTRACTION_PROMPT`「## 2. 議題與決議」區塊）。
NOTES_FIXTURE = """## 2. 議題與決議

- **議題**：辦公廳舍搬遷時程與經費分攤方式，各股需於期限前完成清冊。
- **議題**：員工文康活動辦理形式（便當與禮券）與經費來源。
- **議題**：逐字稿未提及本項議題之具體內容。
- **議題**：短
- **議題**：員工文康活動辦理形式（便當與禮券）與經費來源。
- *決議*：搬遷案照案通過，請總務股於 10 月底前完成點交。
- *決議*：（待確認）

## 3. 討論重點
- *討論重點*：主席提醒廉政風險與資訊安全。
"""

TOPIC_1 = "辦公廳舍搬遷時程與經費分攤方式，各股需於期限前完成清冊。"
TOPIC_2 = "員工文康活動辦理形式（便當與禮券）與經費來源。"
DECISION_1 = "搬遷案照案通過，請總務股於 10 月底前完成點交。"

NUMBER_TRANSCRIPT = (
    "[00:10:00-00:10:20] 甲：一個人 800 塊嘛，那 17 個人總共要 13,600 元。\n"
    "[00:10:20-00:10:40] 乙：同樣的 13600 元再確認一次。\n"
    "[00:10:40-00:11:00] 丙：下午三點半在會議室開會，請大家準時。\n"
    "[00:11:00-00:11:20] 丁：預算 0 元，另一筆 00 元，發 5 個便當。\n"
)

DATE_TRANSCRIPT = (
    "[00:20:00-00:20:20] 甲：11月1日開始實施，10月31日前完成。\n"
    "[00:20:20-00:20:40] 乙：預計 10 月底搬進去。\n"
    "[00:20:40-00:21:00] 丙：下個禮拜一我們要做內稽。\n"
    "[00:21:00-00:21:20] 丁：13/45 與 40月1日 都不是合法日期。\n"
)

# 覆蓋率端到端 fixture：紀錄只涵蓋決議與 10 月底；議題 2 項、數字 3 項、
# 日期 2 項（11/1、10/31）判缺。實作者以現行 HEAD 實測（見 execution.md 判缺表）。
COVERAGE_RECORD = (
    "會議名稱：科務會議\n"
    "一、文康活動：發禮券（科長，00:11:52）。\n"
    "二、搬遷：搬遷案照案通過，請總務股於 10 月底前完成點交。\n"
)

COVERAGE_TRANSCRIPT = (
    "[00:10:00-00:10:20] 甲：一個人 800 塊嘛，那 17 個人總共要 13,600 元。\n"
    "[00:20:00-00:20:20] 乙：11月1日開始實施，10月31日前完成。\n"
    "[00:20:20-00:20:40] 丙：預計 10 月底搬進去。\n"
)

EXPECTED_COVERAGE_FIELDS = (
    "cov_expected_topic=2 cov_missing_topic=2 cov_expected_decision=1 "
    "cov_missing_decision=0 cov_expected_number=3 cov_missing_number=3 "
    "cov_expected_date=3 cov_missing_date=2 cov_issues_added=3 "
)


def _service() -> SummarizationService:
    return SummarizationService()


def _capture_logs(level: str = "DEBUG") -> tuple:
    messages: list = []
    sink_id = loguru_logger.add(lambda message: messages.append(str(message)), level=level)
    return messages, sink_id


def _without_wall_clock(text: str) -> str:
    """遮罩 wall-clock 欄位（`:.1f` 秒數）——golden 對照唯一允許的非確定性欄位。"""
    return re.sub(r"\d+\.\d+", "<T>", text)


def _warm_glossary_cache() -> None:
    """預熱詞彙表快取：首次載入會多一行 log（模組級副作用，非本波差異）。"""
    from backend.core.glossary import load_glossary

    load_glossary()


# ---------------------------------------------------------------------------
# T-01 ~ T-04：議題／決議抽取（來源＝萃取筆記條列）
# ---------------------------------------------------------------------------


def test_T01_議題抽取_區塊限定與佔位過短濾除():
    """議題＝「議題與決議」區塊的 `- **議題**：` 條列；佔位與過短一律濾除。"""
    items = SummarizationService._extract_notes_topic_items(NOTES_FIXTURE)

    assert items == [TOPIC_1, TOPIC_2], "佔位列與過短條目不得進入期望集合"
    assert DECISION_1 not in items, "決議不得混入議題期望集合"


def test_T02_決議抽取_議題不混入且討論重點不列入():
    """決議只取 `*決議*：`；`*討論重點*` 列入對帳屬本波不做（plan §9.9）。"""
    items = SummarizationService._extract_notes_decision_items(NOTES_FIXTURE)

    assert items == [DECISION_1]
    assert all("討論重點" not in item for item in items)
    assert TOPIC_1 not in items


def test_T03_議題抽取_無任何標題時退化全篇掃描():
    """沒有任何 `#` 標題（無區塊可限定）時退化為全篇掃描，佔位仍濾除。"""
    notes = "- **議題**：電梯施工期間的動線與安全維護安排需再確認。\n- **議題**：（待確認）\n"

    assert SummarizationService._extract_notes_topic_items(notes) == [
        "電梯施工期間的動線與安全維護安排需再確認。"
    ]


def test_T04_議題抽取_同鍵去重保留首現():
    """同鍵（正規化後相同）重複條目只保留首現——重複佔額會虛胖期望集合。"""
    notes = (
        "## 1. 議題與決議\n"
        "- **議題**：辦公室搬遷經費分攤方式需再確認。\n"
        "- **議題**：辦公室搬遷經費分攤方式需再確認。\n"
    )

    assert SummarizationService._extract_notes_topic_items(notes) == [
        "辦公室搬遷經費分攤方式需再確認。"
    ]


# ---------------------------------------------------------------------------
# T-05 ~ T-10：數字抽取與比對（來源＝逐字稿；先剝來源標註＋NFKC＋去千分位逗號）
# ---------------------------------------------------------------------------


def test_T05_數字抽取_單位錨定與同句收集():
    """單位錨定（元／塊／個人…）啟用的句子，收集句中所有 ≥2 位數字。"""
    items = SummarizationService._scan_transcript_number_items(NUMBER_TRANSCRIPT)
    literals = [literal for literal, _ in items]

    assert literals == ["800", "17", "13,600"], "同句收集＋折疊後同值去重（第 2 行 13600 不重複）"
    assert all(snippet for _, snippet in items), "每項必須附原文片段（審查 N1：可 grep 可核）"


def test_T06_數字抽取_無單位句不收集():
    """無單位錨定的句子不得收集（時間、編號等誤收防護）。"""
    transcript = (
        "[00:30:00-00:30:20] 甲：下午三點半在會議室開會，請大家準時。\n"
        "[00:30:20-00:30:40] 乙：這份文件是 2026 年版本，共 30 頁。\n"
    )

    assert SummarizationService._scan_transcript_number_items(transcript) == []


def test_T07_數字抽取_千分位與純數字折疊後同值去重():
    """`13,600`／`13600` 都能被抽取，且折疊後同值只留首現（保留原始 literal）。"""
    literals = [literal for literal, _ in SummarizationService._scan_transcript_number_items(NUMBER_TRANSCRIPT)]

    assert "13,600" in literals, "千分位寫法必須抽得到（C1：候選樣式要涵蓋 13,600）"
    assert "13600" not in literals, "折疊後同值去重（第 2 行的 13600 不重複佔額）"


def test_T08_數字抽取_個位數與全零不收集():
    """個位數（5 個便當）與全零（00 元）不得進入期望集合。"""
    literals = [literal for literal, _ in SummarizationService._scan_transcript_number_items(NUMBER_TRANSCRIPT)]

    assert "5" not in literals
    assert "00" not in literals
    assert "0" not in literals


def test_T09_數字比對_先剝來源標註_17不得被時間戳洗白():
    """C1 阻斷級反例：紀錄唯一的「17」在 `（科長，00:17:52）`，不剝會把逐字稿真有的
    「17」判成已涵蓋（假陰性）；剝除後必須判缺。"""
    record = "麻煩則改發禮券（科長，00:17:52）。"
    transcript = "[00:17:00-00:17:30] 甲：有 17 個人所以 13600。"

    folded = SummarizationService._fold_record_for_number_matching(record)
    assert "17" in record, "來源標註確實含 17（此即洗白來源）"
    assert "17" not in folded, "折疊後必須已剝除來源標註"

    issues = _service()._validate_record_source_coverage(record, "", transcript)
    number_issues = [issue for issue in issues if issue.startswith("數字遺漏")]
    assert number_issues, "逐字稿的 17 必須判缺（不得被來源標註洗白）"
    assert "17" in number_issues[0]


def test_T10_數字比對_千分位互認():
    """紀錄寫 `13,600`、逐字稿寫 `13600`（或反向）都算已涵蓋。"""
    record = "每個人 800 塊，17 個人共 13,600 元。"
    transcript = "[00:17:00-00:17:30] 甲：有 17 個人，總共 13600 元。"

    issues = _service()._validate_record_source_coverage(record, "", transcript)

    assert not [issue for issue in issues if issue.startswith("數字遺漏")], "13,600 ≡ 13600"


# ---------------------------------------------------------------------------
# T-11 ~ T-12：日期抽取與等價展開
# ---------------------------------------------------------------------------


def test_T11_日期抽取_四樣式與範圍檢查():
    """月日／月底／斜線／下週幾四樣式；月 1–12、日 1–31 範圍外的不得收集。"""
    canonicals = [canonical for canonical, _ in SummarizationService._scan_transcript_date_items(DATE_TRANSCRIPT)]

    assert canonicals == ["11/1", "10/31", "10月底", "週一"], "13/45 與 40月1日 必須被範圍檢查擋下"


def test_T12_日期等價展開_月日斜線月底週幾():
    """`11月1日 ≡ 11月1號 ≡ 11/1`；`M月底`；`下週一 ≡ 下星期一 ≡ 下個禮拜一`（含反例）。"""
    fold = SummarizationService._fold_record_for_number_matching
    covered = SummarizationService._date_canonical_is_covered

    assert covered("11/1", fold("預計 11月1日 起實施"))
    assert covered("11/1", fold("預計 11月1號 起實施"))
    assert covered("11/1", fold("預計 11/1 起實施"))
    assert covered("10月底", fold("預計於 10 月底前完成點交"))
    assert covered("週一", fold("下個禮拜一我們要做內稽"))
    assert covered("週一", fold("下星期一我們要做內稽"))

    assert not covered("11/1", fold("11月10日開會")), "數字邊界：11/1 不得被 11月10日 洗白"
    assert not covered("週一", fold("下週二要做內稽"))
    assert not covered("10月底", fold("預計 10 月初搬遷"))


# ---------------------------------------------------------------------------
# T-13 ~ T-15：三種模式
# ---------------------------------------------------------------------------


def test_T13_enforce_問題併入清單且附原文片段():
    """enforce（預設）：每類別一條問題字串、逐項附逐字稿原文片段。"""
    service = _service()

    issues = service._validate_record_source_coverage(COVERAGE_RECORD, NOTES_FIXTURE, COVERAGE_TRANSCRIPT)

    assert [issue.split("遺漏", 1)[0] for issue in issues] == ["議題", "數字", "日期"]
    assert issues[0].startswith("議題遺漏 2 項：" + TOPIC_1)
    assert "原文「" in issues[1] and "800" in issues[1] and "13,600" in issues[1]
    assert "11/1" in issues[2] and "10/31" in issues[2]
    assert not [issue for issue in issues if issue.startswith("決議遺漏")], "決議逐字在紀錄中 → 不得誤報"
    assert service._record_coverage_stats["issues_added"] == 3


def test_T14_observe_只記log與metrics_issues為空(monkeypatch):
    """observe：照算、照記 log 與 `cov_*` metrics，但不得改變補強問題清單。"""
    service = _service()
    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "observe")
    messages, sink_id = _capture_logs(level="INFO")
    try:
        issues = service._validate_record_source_coverage(COVERAGE_RECORD, NOTES_FIXTURE, COVERAGE_TRANSCRIPT)
    finally:
        loguru_logger.remove(sink_id)

    assert issues == [], "observe＝品質零變化（issues 不得 append）"
    assert service._record_coverage_stats["missing_number"] == 3, "觀測值仍必須照算"
    assert service._record_coverage_metrics_fields() == EXPECTED_COVERAGE_FIELDS
    assert any("紀錄覆蓋率比對（數字）" in message for message in messages), "observe 必須留下 log 證據"


def test_T15_off_不跑不記(monkeypatch):
    """off：`_validate_record_source_coverage` 一行回 []、無 log、無 cov_* metrics。"""
    service = _service()
    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "off")
    messages, sink_id = _capture_logs(level="DEBUG")
    try:
        issues = service._validate_record_source_coverage(COVERAGE_RECORD, NOTES_FIXTURE, COVERAGE_TRANSCRIPT)
        fields = service._record_coverage_metrics_fields()
    finally:
        loguru_logger.remove(sink_id)

    assert issues == []
    assert fields == ""
    assert service._record_coverage_stats == {}, "off 不得留下任何統計"
    assert messages == [], "off＝完全不跑：連 log 都不得產生"


@pytest.mark.asyncio
async def test_T15b_off_地端pipeline函式級golden(monkeypatch):
    """off（＋忠實度關閉）vs「本波前」：同一輸入 → 紀錄與 log 逐字相同（函式級 golden）。"""
    _warm_glossary_cache()
    transcript = TRANSCRIPT_LINE * 200
    notes = "## 1. 議題與決議\n- **議題**：辦公廳舍搬遷時程與經費分攤方式需再確認。\n"
    summary = "會議名稱：科務會議\n時間：（待確認）\n地點：（待確認）\n散會：（待確認）\n"

    with monkeypatch.context() as ctx:
        baseline_summary, baseline_logs = await _run_local_pipeline_golden(
            ctx, prewave_stub=True, transcript=transcript, notes=notes, summary=summary
        )
    with monkeypatch.context() as ctx:
        off_summary, off_logs = await _run_local_pipeline_golden(
            ctx, prewave_stub=False, transcript=transcript, notes=notes, summary=summary
        )

    assert off_summary == baseline_summary, "off 模式的紀錄必須與本波前 byte 相同"
    assert _without_wall_clock("\n".join(off_logs)) == _without_wall_clock("\n".join(baseline_logs))
    assert not [line for line in off_logs if "cov_" in line or "紀錄覆蓋率" in line]


@pytest.mark.asyncio
async def test_T15c_pipeline_metrics行帶cov欄位_enforce(monkeypatch):
    """地端 pipeline metrics 行必須實際帶上 `cov_*`（供 runner／驗收解析），
    且既有整數鍵（logical_generations／semantic_attempts／merge_rounds）不得消失。"""
    logs = await _run_pipeline_metrics_probe(
        monkeypatch, notes=NOTES_FIXTURE, summary=COVERAGE_RECORD, transcript=COVERAGE_TRANSCRIPT
    )
    metrics_lines = [line for line in logs if "本地摘要 pipeline metrics" in line]

    assert metrics_lines, "structured metrics 行不得消失"
    metrics_line = metrics_lines[-1]
    for legacy_key in ("chunk_count=", "logical_generations=", "semantic_attempts=", "merge_rounds="):
        assert legacy_key in metrics_line, "既有 metrics 鍵不得被覆蓋率欄位排擠"
    assert "cov_expected_number=3" in metrics_line
    assert "cov_missing_number=3" in metrics_line
    assert "cov_issues_added=" in metrics_line


# ---------------------------------------------------------------------------
# T-16 ~ T-19：空集合告警、類別／長度開關、待辦警告靜音
# ---------------------------------------------------------------------------


def test_T16_空期望集合_warning與cov指標不得靜默():
    """空期望集合 → log.warning ＋ `cov_expected_*=0`（不得靜默 no-op）。"""
    service = _service()
    messages, sink_id = _capture_logs(level="WARNING")
    try:
        issues = service._validate_record_source_coverage("紀錄內容", "", "")
    finally:
        loguru_logger.remove(sink_id)

    assert issues == []
    stats = service._record_coverage_stats
    assert stats["expected_topic"] == 0
    assert stats["expected_number"] == 0
    assert stats["expected_date"] == 0
    warnings = [message for message in messages if "期望集合為空" in message]
    assert len(warnings) >= 3, "議題／數字／日期空集合都必須有 WARNING"
    assert "cov_expected_topic=0" in service._record_coverage_metrics_fields()


def test_T17_類別開關可縮類別(monkeypatch):
    """`LOCAL_LLM_RECORD_COVERAGE_CATEGORIES=number`：未選類別完全不跑（無 stats、無問題）。"""
    service = _service()
    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_CATEGORIES", "number")

    issues = service._validate_record_source_coverage(COVERAGE_RECORD, NOTES_FIXTURE, COVERAGE_TRANSCRIPT)
    stats = service._record_coverage_stats

    assert [issue.split("遺漏", 1)[0] for issue in issues] == ["數字"]
    assert "expected_topic" not in stats and "expected_date" not in stats
    assert stats["expected_number"] == 3

    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_CATEGORIES", "unknown,topic")
    service2 = _service()
    service2._validate_record_source_coverage(COVERAGE_RECORD, NOTES_FIXTURE, COVERAGE_TRANSCRIPT)
    assert set(service2._record_coverage_stats) == {"expected_topic", "missing_topic", "issues_added"}, (
        "未知名稱一律過濾（只留交集類別）"
    )


def test_T18_item_limit超出以其餘N項帶過(monkeypatch):
    """`LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT=1` → 只列 1 項，其餘以「其餘 N 項」帶過。"""
    service = _service()
    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT", 1)

    issues = service._validate_record_source_coverage(COVERAGE_RECORD, NOTES_FIXTURE, COVERAGE_TRANSCRIPT)
    number_issue = [issue for issue in issues if issue.startswith("數字遺漏")][0]

    assert "…（其餘 2 項）" in number_issue
    assert number_issue.count("原文「") == 1


def test_T19_待辦期望集合為空的warning_off時完全靜音(monkeypatch):
    """待辦空集合 WARNING（P4-A §2.1-①）：預設模式必須告警；off 模式必須靜音。"""
    service = _service()
    notes = "## 2. 議題與決議\n- **議題**：辦公廳舍搬遷時程與經費分攤方式需再確認。\n"
    summary = "會議名稱：科務會議\n時間：（待確認）\n散會：（待確認）\n"

    messages, sink_id = _capture_logs(level="WARNING")
    try:
        service._validate_summary_quality(summary, notes, min_chars=1)
        enforce_warnings = [message for message in messages if "待辦期望集合為空" in message]
        messages.clear()
        monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "off")
        service._validate_summary_quality(summary, notes, min_chars=1)
        off_warnings = [message for message in messages if "待辦期望集合為空" in message]
    finally:
        loguru_logger.remove(sink_id)

    assert len(enforce_warnings) == 1, "預設（enforce／observe）不得靜默 no-op"
    assert off_warnings == [], "off＝回本波前 byte 級行為（連 log 都不得新增）"


# ---------------------------------------------------------------------------
# P4-C（W-1／W-2）：引擎同源（payload 級；不連線）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_P01_ollama取樣參數讀同一份config_payload級(monkeypatch):
    """Ollama `options` 的 top_p／top_k／repeat_penalty 必須讀同一份 config
    （與 LM Studio 同源）；不得寫死 0.95／64。"""
    service = _service()
    captured: dict = {}

    async def _fake_post(client, payload, send_think_field):  # noqa: ANN001, ARG001
        captured["payload"] = payload
        return "會議紀錄內容", {"done": True}, send_think_field

    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=object()))
    monkeypatch.setattr(service, "_post_ollama_chat", _fake_post)
    monkeypatch.setattr(service, "_get_effective_model", lambda: "qwen3:32b")
    monkeypatch.setattr(service, "_emit_progress", lambda *args, **kwargs: None)  # noqa: ARG005
    monkeypatch.setattr(settings, "LOCAL_LLM_SAMPLING_TOP_P", 0.8)
    monkeypatch.setattr(settings, "LOCAL_LLM_SAMPLING_TOP_K", 20)
    monkeypatch.setattr(settings, "LOCAL_LLM_SAMPLING_REPEAT_PENALTY", 1.08)

    await service._summarize_with_ollama("系統提示", "使用者訊息", context_window_tokens=8192)
    options = captured["payload"]["options"]

    assert options["top_p"] == 0.8, "不得寫死 0.95"
    assert options["top_k"] == 20, "不得寫死 64"
    assert options["repeat_penalty"] == 1.08
    assert options["num_ctx"] == service._effective_context_tokens(8192)

    monkeypatch.setattr(settings, "LOCAL_LLM_SAMPLING_TOP_P", 0.5)
    monkeypatch.setattr(settings, "LOCAL_LLM_SAMPLING_TOP_K", 10)
    monkeypatch.setattr(settings, "LOCAL_LLM_SAMPLING_REPEAT_PENALTY", None)
    await service._summarize_with_ollama("系統提示", "使用者訊息", context_window_tokens=8192)
    options = captured["payload"]["options"]

    assert options["top_p"] == 0.5 and options["top_k"] == 10, "config 改值 → payload 必須跟著改（同源）"
    assert "repeat_penalty" not in options, "None＝不送（與 LM Studio 對同一份 config 的語意一致）"
    assert service.LEGACY_OLLAMA_SAMPLING_OPTIONS == {"top_p": 0.95, "top_k": 64, "repeat_penalty": 1.08}, (
        "舊寫死值必須保留為 rollback 常數（一行回退）"
    )


@pytest.mark.asyncio
async def test_P02_think欄位400降級路徑保留(monkeypatch):
    """400 降級：第一送帶 think 被拒 → 第二送不得帶 think 欄位（既有行為不得退化）。"""
    service = _service()
    bodies: list = []
    request = httpx.Request("POST", "http://127.0.0.1:11434/api/chat")
    error = httpx.HTTPStatusError("400", request=request, response=httpx.Response(400, request=request))

    async def _fake_stream(client, body):  # noqa: ANN001, ARG001
        bodies.append(body)
        if len(bodies) == 1:
            raise error
        return "內容", {"done": True}

    monkeypatch.setattr(service, "_stream_ollama_chat_once", _fake_stream)
    monkeypatch.setattr(service, "_log_generation_metrics", lambda *args, **kwargs: None)  # noqa: ARG005

    content, _chunk, send_think_field = await service._post_ollama_chat(
        object(), {"options": {"top_p": 0.8}}, True
    )

    assert content == "內容"
    assert send_think_field is False
    assert bodies[0].get("think") is False
    assert "think" not in bodies[1], "降級後不得再帶 think 欄位"


def test_P03_補強階段context不足時有warning(monkeypatch):
    """W-2：補強訊息退回「只餵筆記」時必須有 WARNING（與生成階段同構）。"""
    service = _service()
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION", True)
    monkeypatch.setattr(service, "_final_message_fits", lambda *args, **kwargs: False)  # noqa: ARG005
    transcript = "[00:00:00-00:00:10] 發言者1：請完成水塔清洗。"

    messages, sink_id = _capture_logs(level="WARNING")
    try:
        message = service._resolve_final_refinement_message(
            "現行紀錄", "萃取筆記", ["補強問題"], transcript, "系統提示", 8192
        )
    finally:
        loguru_logger.remove(sink_id)

    assert "原始逐字稿" not in message, "context 不足時退回只餵筆記"
    assert any("補強階段" in m and "逐字稿" in m for m in messages), "補強階段缺『無法附逐字稿』WARNING"


# ---------------------------------------------------------------------------
# golden 用：地端 pipeline 全鏈（fake 引擎；本檔內共用）
# ---------------------------------------------------------------------------


async def _run_local_pipeline_golden(
    monkeypatch,
    *,
    prewave_stub: bool,
    transcript: str,
    notes: str,
    summary: str,
) -> tuple:
    """跑一次地端 pipeline 並回傳（紀錄, log 行）。

    `prewave_stub=True` ＝ 本波前的等效實作（覆蓋率／忠實度方法不存在＝一律 []、
    metrics 欄位不存在）；兩個開關都關閉時，本波實作必須與它逐字相同。
    """
    service = _service()
    generated: list = []
    outputs = [notes, summary]

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated.append(message)
        return outputs[min(len(generated) - 1, len(outputs) - 1)]

    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "off")
    monkeypatch.setattr(settings, "LOCAL_FIDELITY_TRIPWIRES", False)
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", AsyncMock(return_value="MERGED"))
    monkeypatch.setattr(service, "_validate_summary_quality", lambda *args, **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *args, **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *args, **kwargs: [])  # noqa: ARG005
    if prewave_stub:
        monkeypatch.setattr(service, "_validate_record_source_coverage", lambda *args, **kwargs: [])  # noqa: ARG005
        monkeypatch.setattr(service, "_validate_record_fidelity", lambda *args, **kwargs: [])  # noqa: ARG005
        monkeypatch.setattr(service, "_record_coverage_metrics_fields", lambda: "")

    messages, sink_id = _capture_logs(level="DEBUG")
    try:
        result = await service._summarize_with_local_pipeline(
            transcript, settings.DEFAULT_SYSTEM_PROMPT, template=get_template("section_meeting")
        )
    finally:
        loguru_logger.remove(sink_id)
    return result, messages


async def _run_pipeline_metrics_probe(monkeypatch, *, notes: str, summary: str, transcript: str) -> list:
    """跑一次地端 pipeline（覆蓋率＝enforce，其餘驗證器隔離）並回傳 log 行。"""
    service = _service()
    generated: list = []
    outputs = [notes, summary, summary]

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated.append(message)
        return outputs[min(len(generated) - 1, len(outputs) - 1)]

    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "enforce")
    monkeypatch.setattr(settings, "LOCAL_FIDELITY_TRIPWIRES", False)
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", AsyncMock(return_value="MERGED"))
    monkeypatch.setattr(service, "_validate_summary_quality", lambda *args, **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *args, **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *args, **kwargs: [])  # noqa: ARG005

    messages, sink_id = _capture_logs(level="DEBUG")
    try:
        await service._summarize_with_local_pipeline(
            transcript, settings.DEFAULT_SYSTEM_PROMPT, template=get_template("section_meeting")
        )
    finally:
        loguru_logger.remove(sink_id)
    return messages
