# -*- coding: utf-8 -*-
"""P4-B（T20260922-2037-02）：忠實度絆索 A／B／C＋registry-aware 量尺 —— 契約測試。

對應計畫 §9.4（P4-B）與 handoff §4.1 凍結介面：

- **A 自創專名**：高訊號位置（P1 引號／P2 命名動詞）→ 支援測試（fold 變體／
  stem 正確改寫／registry 白名單／同後綴 Dice 備援）→ 未支持者進問題清單（上限 3）。
- **B 無依據歸屬**：標註身分（tag_owner）／固定欄位指名（header_speaker_id）／
  欄位自創（header_selfinvent）／角色詞（role_word）／表格發言者編號
  （table_speaker_id）／承辦單位欄（cell_unit）→ 上限 3 條訊息。
- **C 數字單位**：剝【發言者統計】＋時間戳、NFKC、去千分位、ASR 口吃與前導零守衛；
  捏造（紀錄有、逐字稿無）與漏寫（逐字稿實質視圖有、紀錄全量視圖無）雙向；
  MONEY／RATIO≥2、PERSON／COUNT≥10、BARE≥4 位且 ±2 字無其他數字、DATE 雙向排除；
  上限 6 筆、類別優先排序。
- **量尺**：``unsupported_entities``（raw）保留、**新增**
  ``unsupported_entities_registry_aware`` 與 ``fidelity`` 摘要；產品與量尺共用
  ``backend.core.fidelity_checks`` 同一支函式。
- **off／關閉開關＝函式級 golden byte 不變**：``measure_record_quality`` 既有欄位與
  notes 舊條目在改動前後 byte 級相同（golden sha256 由 HEAD 6e12931 的舊版儀器
  求得、改動後重驗相同）；``LOCAL_FIDELITY_TRIPWIRES=false`` 時產品完全不呼叫檢查器。
- **import 期零副作用**：白名單與詞彙表皆 lazy 讀取（import 期不得有檔案 I/O；
  亦不得預先載入 glossary／templates 模組）。
"""

import os
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 故在 import backend 前備妥隔離目錄（同 test_t20260922_2037_p3_parity.py 慣例）。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-p4b-"))

import builtins  # noqa: E402
import hashlib  # noqa: E402
import importlib  # noqa: E402
import importlib.util  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from backend.core import fidelity_checks  # noqa: E402
from backend.core.fidelity_checks import (  # noqa: E402
    FIDELITY_METRIC_VERSION,
    analyze_fidelity,
    is_supported_entity,
    load_entity_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = PROJECT_ROOT / "scripts" / "e2e" / "measure_record_quality.py"

# 改動前（HEAD 6e12931）儀器對下方 fixture 的 legacy payload（去掉 P4-B 新增鍵與
# 新增 notes 條目後）canonical JSON sha256；改動後必須完全相同。
GOLDEN_LEGACY_SHA256 = "435e2727758e9a4568bfcfc57d825d7d10eff4cc1c2b012fded41e5b69dcf9dd"
GOLDEN_RECORD = """# 科務會議紀錄

時間：中華民國115年9月3日
主持人：科長

| 案由及承辦單位 | 辦理情形 |
| --- | --- |
| 組織異動調整（資管股） | 資管股： |

一、科長轉知局務會議工作報告及相關注意事項：
1. 土地稅科配合辦理交接（科長，00:05:36）。
"""
GOLDEN_TRANSCRIPT = """[00:05:30-00:05:40] 發言者1：土地稅科配合辦理交接。
"""


def _load_metrics_module():
    spec = importlib.util.spec_from_file_location(
        "measure_record_quality_p4b", METRICS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


metrics = _load_metrics_module()


def _header(body: str) -> str:
    return (
        "# 科務會議紀錄\n\n時間：中華民國115年9月3日\n主持人：科長\n\n"
        "一、報告事項：\n" + body
    )


# ---------------------------------------------------------------------------
# A：自創專名
# ---------------------------------------------------------------------------

TRANSCRIPT_A = "[00:00:00-00:00:20] 發言者1：土地稅科業務報告，欠稅管理股負責清查。\n"


def test_A_引號與命名動詞位置回報自創專名():
    """正例：P2「消耗稅科更名為…」與 P1「煙酒分管股」皆無逐字稿依據 → 回報。"""
    record = _header(
        "1. 消耗稅科更名為「使用牌照稅科」（科長，00:00:00）。\n"
        "2. 分設「煙酒分管股」與「欠稅管理股」（科長，00:00:00）。\n"
    )
    report = analyze_fidelity(record, TRANSCRIPT_A, "section_meeting")

    assert set(report["fabricated_entities"]) == {"消耗稅科", "煙酒分管股"}, report
    assert report["failed_checks"] == []
    assert all(token in "".join(report["problems"]) for token in report["fabricated_entities"])
    assert "（待確認）" in "".join(report["problems"]), "問題字串必須是人類可讀回查指令"


def test_A_回報上限3且輸出穩定():
    """正例：4 個無依據專名 → 只回報 3 筆（設計 §2.5），且同輸入 byte 級相同。"""
    record = _header(
        "1. 「土雞股」「土狗股」「土牛股」「土馬股」皆完成（科長，00:00:00）。\n"
    )
    transcript = "[00:00:00-00:00:10] 發言者1：測試。\n"
    first = analyze_fidelity(record, transcript, "section_meeting")
    second = analyze_fidelity(record, transcript, "section_meeting")

    assert len(first["fabricated_entities"]) == 3
    assert len([p for p in first["problems"] if "專名" in p or "具名單位" in p]) == 3
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True
    )


def test_A_官方白名單不報():
    """反例：逐字稿沒出現、但為官方股名的「稽查股」「徵收股」不得回報。"""
    record = _header("1. 「稽查股」與「徵收股」自 11 月起生效（科長，00:00:00）。\n")
    transcript = "[00:00:00-00:00:10] 發言者1：房稅股調整。\n"
    report = analyze_fidelity(record, transcript, "section_meeting")

    assert report["fabricated_entities"] == []
    assert report["registry_aware_unsupported_entities"] == []


def test_A_正確改寫與變體折疊不報():
    """反例：逐字稿「內稽／瑞裏」→ 紀錄「內稽科／瑞里村」（stem 與 fold 規則放行）。"""
    record = _header("1. 「內稽科」與「瑞里村」納入本年度工作（科長，00:00:00）。\n")
    transcript = "[00:00:00-00:00:10] 發言者1：內稽與瑞裏社區配合。\n"
    report = analyze_fidelity(record, transcript, "section_meeting")

    assert report["fabricated_entities"] == []


def test_A_一般複合詞與限定詞不報():
    """反例：後綴複合詞（財管科搬入處／煙酒及稅管科一股）不得當成專名。"""
    record = _header(
        "1. 「財管科搬入處」與「煙酒及稅管科一股」皆已完成（科長，00:00:00）。\n"
    )
    transcript = "[00:00:00-00:00:10] 發言者1：搬遷作業。\n"
    report = analyze_fidelity(record, transcript, "section_meeting")

    assert report["fabricated_entities"] == []


# ---------------------------------------------------------------------------
# B：無依據歸屬
# ---------------------------------------------------------------------------

TRANSCRIPT_B = (
    "[00:00:00-00:00:20] 發言者1：科長裁示業務報告。\n"
    "[00:00:20-00:00:40] 發言者2：資管股經費說明。\n"
)


def test_B_固定欄位出現發言者編號_回報():
    """正例：實測真缺陷「主持人：科長（發言者1）」（B1 場）。"""
    record = (
        "# 科務會議紀錄\n\n時間：中華民國115年9月3日\n"
        "主持人：科長（發言者1）\n紀錄：AI 會議助理\n\n"
        "一、報告事項：\n1. 事項（科長，00:00:00）。\n"
    )
    report = analyze_fidelity(record, TRANSCRIPT_B, "section_meeting")

    assert "header_speaker_id" in report["attribution_kinds"]
    assert "發言者1" in "".join(report["problems"])
    assert "AI 會議助理" not in "".join(report["problems"]), "既有例外（AI 會議助理）不得回報"


def test_B_表格列出現發言者編號_回報():
    """正例：彙整表「辦理情形」欄寫「發言者3：」（B2 場真缺陷；現行 forbidden_patterns 漏網）。"""
    record = (
        "# 科務會議紀錄\n\n時間：中華民國115年9月3日\n主持人：科長\n\n"
        "| 案由及承辦單位 | 辦理情形 |\n| --- | --- |\n| 報告事項一（資管股） | 發言者3： |\n"
    )
    report = analyze_fidelity(record, TRANSCRIPT_B, "section_meeting")

    assert "table_speaker_id" in report["attribution_kinds"]
    assert "發言者3" in "".join(report["problems"])


def test_B_標註落在他人段落_回報():
    """正例：（發言者2，00:00:10）落在發言者1 的段落內（[00:00:00-00:00:20]）。"""
    record = _header("1. 業務移交（發言者2，00:00:10）。\n")
    report = analyze_fidelity(record, TRANSCRIPT_B, "section_meeting")

    assert "tag_owner" in report["attribution_kinds"]


def test_B_待確認與簽到表與正確承辦單位不報():
    """反例：契約允許的填法（（待確認）／如後附簽到表）與逐字稿有的承辦股不得回報。"""
    record = (
        "# 科務會議紀錄\n\n時間：中華民國115年9月3日\n"
        "主持人：科長\n出席人員：如後附簽到表\n紀錄：（待確認）\n\n"
        "| 案由及承辦單位 | 辦理情形 |\n| --- | --- |\n| 報告事項一（資管股） | 資管股： |\n"
    )
    report = analyze_fidelity(record, TRANSCRIPT_B, "section_meeting")

    assert report["attribution_violations"] == []


def test_B_標註落空隙不報():
    """反例：時間戳落在段落空隙（非任何段落內）＝不可回溯，不得當成歸屬錯誤。"""
    transcript = (
        "[00:00:00-00:00:20] 發言者1：科長裁示業務報告。\n"
        "[00:00:40-00:01:00] 發言者3：資管股經費說明。\n"
    )
    record = _header("1. 業務移交（發言者1，00:00:30）。\n")
    report = analyze_fidelity(record, transcript, "section_meeting")

    assert report["attribution_violations"] == []


def test_B_上限3條訊息():
    """正例＋上限：4 種歸屬問題 → 訊息只出 3 條（優先序固定）。"""
    record = (
        "# 科務會議紀錄\n\n時間：中華民國115年9月3日\n"
        "主持人：科長（發言者1）\n\n一、報告事項：\n1. 局長提示（科長，00:00:00）。\n\n"
        "| 案由及承辦單位 | 辦理情形 |\n| --- | --- |\n"
        "| 報告事項一（資管股） | 發言者3： |\n| 報告事項二（資管股） | 土雞股： |\n"
    )
    report = analyze_fidelity(record, TRANSCRIPT_B, "section_meeting")

    assert len(report["attribution_violations"]) >= 4
    messages = [p for p in report["problems"] if p in _attribution_only(report)]
    assert len(messages) == 3


def _attribution_only(report: dict) -> list:
    """從報告回推歸屬訊息（同一份字串；供上限斷言使用）。"""
    known = (
        "紀錄固定欄位歸屬待確認",
        "彙整表欄位歸屬待確認",
        "來源標註歸屬待確認",
        "紀錄欄位依據待確認",
        "角色依據待確認",
        "承辦單位依據待確認",
    )
    return [p for p in report["problems"] if p.startswith(known)]


# ---------------------------------------------------------------------------
# C：數字／單位
# ---------------------------------------------------------------------------

TRANSCRIPT_C = (
    "[00:00:00-00:00:20] 發言者1：發放 800塊，總計 17個人，比例 15%，另編列 13600 元。\n"
)


def test_C_逐字稿有而紀錄未見_回報漏寫():
    """正例：800塊／17個／15%／13600元（F024／F025 類缺口）→ 依類別優先排序。"""
    record = _header("1. 經費發放（科長，00:00:00）。\n")
    report = analyze_fidelity(record, TRANSCRIPT_C, "section_meeting")

    assert report["missing_numbers"] == ["13600元", "800塊", "15%", "17個"], report["missing_numbers"]
    assert "800塊" in "".join(report["problems"])
    assert report["fabricated_numbers"] == []


def test_C_紀錄有而逐字稿無_回報捏造():
    """正例：紀錄「3張」逐字稿沒有 → 疑似捏造。"""
    record = _header("1. 決議購買 3張 桌子（科長，00:00:00）。\n")
    report = analyze_fidelity(record, TRANSCRIPT_C, "section_meeting")

    assert report["fabricated_numbers"] == ["3張"]
    assert "疑似捏造" in "".join(report["problems"])


def test_C_單位等價不報():
    """反例：紀錄「800 元」 vs 逐字稿「800塊」＝同值 → 不得回報漏寫。"""
    record = _header("1. 發放 800 元（科長，00:00:00）。\n")
    report = analyze_fidelity(record, TRANSCRIPT_C, "section_meeting")

    assert "800塊" not in report["missing_numbers"]
    assert "800" not in [token.rstrip("元塊") for token in report["missing_numbers"]]


def test_C_口吃前導零日期與統計前言不報():
    """反例：四四個／000塊／11月1日／6000的00／【發言者統計】皆不得進漏寫清單。"""
    transcript = (
        "【發言者統計】\n- 發言者1：00:37:28（85%）\n- 發言者2：00:05:00（0 人）\n\n"
        "[00:00:00-00:00:20] 發言者1：四四個、000塊、11月1日、6000的00。\n"
    )
    record = _header("1. 概況說明（科長，00:00:00）。\n")
    report = analyze_fidelity(record, transcript, "section_meeting")

    assert report["missing_numbers"] == []
    assert report["fabricated_numbers"] == []


def test_C_上限6與類別優先排序():
    """正例＋上限：8 筆實質數字 → 只取 6 筆、MONEY→BARE→RATIO→PERSON 排序。"""
    transcript = (
        "[00:00:00-00:00:20] 發言者1：800塊、600塊、5000、25%、15%、40個人、17個、13600。\n"
    )
    record = _header("1. 概況說明（科長，00:00:00）。\n")
    report = analyze_fidelity(record, transcript, "section_meeting")

    assert report["missing_numbers"] == ["800塊", "600塊", "13600", "25%", "15%", "40個"], report[
        "missing_numbers"
    ]


# ---------------------------------------------------------------------------
# 不變量：off 開關／golden byte／確定性／fail-soft／import 零副作用
# ---------------------------------------------------------------------------


def test_off開關_關閉時產品完全不呼叫檢查器(monkeypatch):
    """I-3：``LOCAL_FIDELITY_TRIPWIRES=false`` → 不呼叫檢查器（輸出與本波前相同）。"""
    from backend.core.config import settings
    from backend.core.templates import get_template
    from backend.services.summarization import SummarizationService

    called = {"count": 0}

    def _boom(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("關閉開關時不得呼叫忠實度檢查器")

    monkeypatch.setattr(settings, "LOCAL_FIDELITY_TRIPWIRES", False)
    monkeypatch.setattr(fidelity_checks, "analyze_fidelity", _boom)

    service = SummarizationService()
    issues = service._validate_record_fidelity(
        GOLDEN_RECORD, GOLDEN_TRANSCRIPT, get_template("section_meeting")
    )

    assert issues == []
    assert called["count"] == 0


def test_量尺既有欄位byte級golden不變():
    """off 等價：P4-B 與 P7-B 都只新增鍵；把新鍵與新 notes 條目移除後必須等於改動前 payload。

    P7-B（T20260923-1810-01，`ac181be`）在量尺上另加了模板無關的觀測欄位
    （`full_document_item_count`／`full_document_avg_item_chars`／`near_duplicate_items`）
    與兩條 `notes.definitions` 說明。它們同樣是 **additive、observation-only**，
    故一併列入本測試的「新鍵」清單——既有欄位與舊 notes 條目仍必須 byte 級不變
    （把新增項全部剝除後，digest 必須回到 P4-B 之前的 golden）。
    """
    p7b_top_level = ("full_document_item_count", "full_document_avg_item_chars", "near_duplicate_items")
    p7b_notes = ("full_document_item_stats", "near_duplicate_items")
    payload = metrics.measure_record_quality(
        GOLDEN_RECORD, transcript_text=GOLDEN_TRANSCRIPT, template_id="section_meeting"
    )
    stripped = dict(payload)
    for key in ("unsupported_entities_registry_aware", "fidelity", *p7b_top_level):
        stripped.pop(key)
    stripped["notes"] = {
        key: value
        for key, value in payload["notes"].items()
        if key not in ("unsupported_entities_registry_aware", "fidelity", *p7b_notes)
    }
    stripped["notes"]["definitions"] = {
        key: value
        for key, value in payload["notes"]["definitions"].items()
        if key not in p7b_notes
    }
    canonical = json.dumps(stripped, ensure_ascii=False, sort_keys=True, indent=2)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    assert digest == GOLDEN_LEGACY_SHA256, "既有量測欄位與 notes 舊條目必須 byte 級不變"


def test_量尺新增欄位與產品共用同一支函式():
    """量尺的 registry-aware／fidelity 必須與 fidelity_checks 同一份結果。"""
    record = _header(
        "1. 「稽查股」與「徵收股」生效，另「煙酒分管股」分設（科長，00:00:00）。\n"
    )
    report = analyze_fidelity(record, TRANSCRIPT_A, "section_meeting")
    payload = metrics.measure_record_quality(
        record, transcript_text=TRANSCRIPT_A, template_id="section_meeting"
    )

    assert payload["unsupported_entities"] == report["raw_unsupported_entities"]
    assert (
        payload["unsupported_entities_registry_aware"]
        == report["registry_aware_unsupported_entities"]
    )
    assert payload["fidelity"]["entity_names"] == report["fabricated_entities"]
    assert payload["fidelity"]["metric_version"] == FIDELITY_METRIC_VERSION
    assert "煙酒分管股" in payload["unsupported_entities_registry_aware"]
    assert "稽查股" not in payload["unsupported_entities_registry_aware"]
    assert "稽查股" in payload["unsupported_entities"], "raw 欄位語意凍結，不得被過濾"


def test_量尺未提供逐字稿時新欄位為None():
    """schema：未提供 --transcript 時，新欄位與 raw 欄位同為 null。"""
    payload = metrics.measure_record_quality(GOLDEN_RECORD, transcript_text=None)

    assert payload["unsupported_entities"] is None
    assert payload["unsupported_entities_registry_aware"] is None
    assert payload["fidelity"] is None
    note = payload["notes"]["unsupported_entities_registry_aware"]
    assert "P4-B" in note and "is_supported_entity" in note


def test_檢查器不改寫輸入且輸出可重現():
    """確定性：同輸入 byte 級相同；輸入字串不得被改寫（只回報、不改寫）。"""
    record = _header("1. 消耗稅科更名為「使用牌照稅科」（科長，00:00:00）。\n")
    record_before, transcript_before = record, TRANSCRIPT_A
    first = analyze_fidelity(record, TRANSCRIPT_A, "section_meeting")
    second = analyze_fidelity(record, TRANSCRIPT_A, "section_meeting")

    assert record == record_before and TRANSCRIPT_A == transcript_before
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True
    )
    assert "消耗稅科" in record, "紀錄內容不得被檢查器改寫"


def test_failsoft_逐字稿缺席與非字串輸入不拋出():
    assert analyze_fidelity(GOLDEN_RECORD, None)["problems"] == []
    assert analyze_fidelity(GOLDEN_RECORD, "")["problems"] == []
    assert analyze_fidelity(None, GOLDEN_TRANSCRIPT)["problems"] == []
    assert analyze_fidelity(123, 456)["problems"] == []
    report = analyze_fidelity(GOLDEN_RECORD, None)
    assert report["metric_version"] == FIDELITY_METRIC_VERSION
    assert report["registry_aware_unsupported_entities"] == []


def test_failsoft_子檢查異常只縮小範圍不拋出(monkeypatch):
    monkeypatch.setattr(
        fidelity_checks, "_candidate_names", lambda *args, **kwargs: 1 / 0
    )
    report = analyze_fidelity(
        _header("1. 經費發放（科長，00:00:00）。\n"), TRANSCRIPT_C, "section_meeting"
    )

    assert "entity" in report["failed_checks"]
    assert report["fabricated_entities"] == []
    assert report["missing_numbers"], "其餘子檢查（C）不得因 A 異常而停擺"


def test_模組匯入期零檔案IO(monkeypatch):
    """import 期不得讀檔（白名單與詞彙表皆 lazy）：以 builtins.open 攔截 reload。"""
    monkeypatch.setattr(fidelity_checks, "_REGISTRY_CACHE", {"key": None, "names": frozenset()})
    real_open = builtins.open

    def _deny(file, *args, **kwargs):  # noqa: ANN001, ARG001
        raise AssertionError("模組匯入期不得讀取檔案：%s" % (file,))

    try:
        monkeypatch.setattr(builtins, "open", _deny)
        importlib.reload(fidelity_checks)
    finally:
        monkeypatch.undo()
    importlib.reload(fidelity_checks)
    assert fidelity_checks.FIDELITY_METRIC_VERSION == FIDELITY_METRIC_VERSION


def test_模組匯入不預載glossary與templates():
    """import 期零副作用：glossary／templates 為 lazy import（子行程驗證）。"""
    code = (
        "import json, sys\n"
        "import backend.core.fidelity_checks as fc\n"
        "print(json.dumps({\n"
        "  'glossary_loaded': 'backend.core.glossary' in sys.modules,\n"
        "  'templates_loaded': 'backend.core.templates' in sys.modules,\n"
        "  'registry_preloaded': fc._REGISTRY_CACHE['key'] is not None,\n"
        "}))\n"
    )
    env = dict(os.environ)
    env["DATA_DIR"] = tempfile.mkdtemp(prefix="p4b-import-")
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=str(PROJECT_ROOT), env=env,
        capture_output=True, text=True, timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload == {
        "glossary_loaded": False,
        "templates_loaded": False,
        "registry_preloaded": False,
    }, payload


def test_白名單載入與fold變體():
    """白名單為 fold 正規化（徵→征、菸→煙、裏／裡→里）；放行判定須 fold 不敏感。"""
    registry = load_entity_registry()

    assert "稽查股" in registry
    assert "征收股" in registry, "徵→征 fold：白名單一律正規化"
    assert is_supported_entity("徵收股", "", registry)[0] is True
    assert "煙酒稽征股" in registry, "fold 菸→煙／徵→征 必須涵蓋紀錄常見寫法"
    assert "瑞里" in registry
    assert isinstance(registry, set)


def test_四場真實產物回歸_校準值():
    """設計期校準（0903 四場）：A＝0／0／1／2；C 捏造＝0；registry-aware＝0／0／0／1。"""
    base = PROJECT_ROOT / "data" / "cache" / "e2e"
    cases = {
        "B2": base / "p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a",
        "B1": base / "p2-moe-fix-01/backend_data/outputs/0903-科務會議_0cc199da",
        "C1": base / "p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec",
        "D1": base / "p3-gemma31b-d1/backend_data/outputs/0903-科務會議_ab5571ea",
    }
    expected_flags = {
        "B2": [],
        "B1": [],
        "C1": ["消耗稅科"],
        "D1": ["消耗稅科", "煙酒分管股"],
    }
    expected_aware = {"B2": [], "B1": [], "C1": [], "D1": ["煙酒分管股"]}
    for name, stem in cases.items():
        record = Path(str(stem) + ".md")
        transcript = Path(str(stem) + "_逐字稿.txt")
        if not record.exists() or not transcript.exists():
            pytest.skip("校準語料不在本機：%s" % record)
        report = analyze_fidelity(
            record.read_text(encoding="utf-8"),
            transcript.read_text(encoding="utf-8"),
            "section_meeting",
        )
        assert report["fabricated_entities"] == expected_flags[name], name
        assert report["registry_aware_unsupported_entities"] == expected_aware[name], name
        assert report["fabricated_numbers"] == [], name
        assert report["missing_numbers"][:2] == ["800塊", "600塊"], name
