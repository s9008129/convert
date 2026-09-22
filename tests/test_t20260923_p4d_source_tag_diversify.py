# -*- coding: utf-8 -*-
"""P4-D（T20260922-2037-02）產品側：吸附「規則 6：同標籤同時戳去重複化」契約測試。

對應 `plan.md` §9.6 產品側與 `handoff.md` §4.5；設計全文＝設計期 `/tmp/p4d_design.md`
§3（非持久來源，語意已內化於 `backend/core/text_postprocess.py` 的實作與 docstring）：

- **正例**：同一（發言者, 時間）出現多次時，保留前 `TAG_DIVERSIFY_MAX_PER_TIME`（cap=2）
  筆；其餘改指到「同標籤、±120 s 內、該標籤未使用過」的真實段落起點（bigram 重疊
  優先 → |Δ| 小 → 秒數小）。
- **冪等**：`f(f(x)) == f(x)`（第二輪 `diversified == 0`）。
- **fail-soft**：無候選／逐字稿缺段落／標註格式異常 → 原樣保留、不拋錯、不新增／
  不刪除標註。
- **不變式**：規則 0（段首保護）／規則 4（精度保護，`HH:MM` 只落整分鐘）語意不變；
  回退開關 `LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED=false`＝本波之前 byte 級不變
  （函式級 golden；handoff §11 N3 同精神）。
- **量尺不退步**：`distinct_tag_time_ratio` 上升、`on_start_tag_ratio`／
  `traceable_tag_ratio`／`tags_total`（body 標註數）不退步；表格標註另由 E2E 契約清除。

測試素材＝合成 fixture ＋ 既有 4 場真實紀錄（`data/cache/e2e/*/backend_data/outputs`；
檔案不存在時 skip，不依賴網路、不啟動後端）。
"""

import os
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 預設 /app/data 在 macOS 讀取失敗，故在 import backend 前備妥隔離目錄。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-p4d-"))

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from backend.core import text_postprocess as tp  # noqa: E402
from backend.core.templates import get_template  # noqa: E402
from backend.core.text_postprocess import (  # noqa: E402
    SOURCE_TAG_PATTERN,
    measure_tag_traceability,
    snap_source_tags_to_transcript,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_RECORDS = {
    "B2": "data/cache/e2e/p2-27b-fix-01",
    "D1": "data/cache/e2e/p3-gemma31b-d1",
    "D2": "data/cache/e2e/p3-gemma31b-d2",
}


def _load_real_record(key: str):
    """讀既有真實紀錄（md＋逐字稿）；不存在時回 None（呼叫端 skip）。"""
    out_dir = REPO_ROOT / REAL_RECORDS[key] / "backend_data" / "outputs"
    if not out_dir.is_dir():
        return None
    mds = sorted(out_dir.glob("*.md"))
    transcripts = sorted(out_dir.glob("*逐字稿.txt"))
    if not mds or not transcripts:
        return None
    return mds[0].read_text(encoding="utf-8"), transcripts[0].read_text(encoding="utf-8")


def _labels(text: str) -> list:
    """取所有標註的發言者標籤（規則 6 只准改時間戳、不准改標籤文字）。"""
    result = []
    for match in SOURCE_TAG_PATTERN.finditer(text):
        inner = match.group()[1:-1]
        time_match = tp.SOURCE_TAG_TIME_PATTERN.search(inner)
        label = inner[: time_match.start()] if time_match else inner
        result.append(label.strip("，,、;；:： \t　"))
    return result


def _disable_switch(monkeypatch):
    """把 config 的 LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED 以 stub settings 關閉。"""
    stub = type("_OffSettings", (), {"LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED": False})()
    monkeypatch.setattr("backend.core.config.settings", stub)


# ---------------------------------------------------------------------------
# 合成 fixture
# ---------------------------------------------------------------------------

# 四個真實段首（0／30／60／90 s），同一發言者。
DUP_TRANSCRIPT = (
    "[00:00:00-00:00:30] 科長：甲。\n"
    "[00:00:30-00:01:00] 科長：乙。\n"
    "[00:01:00-00:01:30] 科長：丙。\n"
    "[00:01:30-00:02:00] 科長：丁。\n"
)


def test_規則6_同標籤同時戳_保留首筆其餘搬到未使用的真實段首():
    template = get_template("section_meeting")
    text = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
    )

    out, stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)

    assert out == (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:30）。\n"
    ), "cap=2：前兩筆保留、第三筆搬到 ±120 s 內未使用的真實段首（|Δ| 最小）"
    assert stats["diversified"] == 1
    assert stats["diversify_skipped_no_candidate"] == 0
    assert stats["diversify_max_shift_seconds"] == 30
    assert stats["changed"] == 0, "規則 0-5 的 changed 定義不變（規則 6 另計 diversified）"


def test_規則6_冪等_二次套用byte相同():
    template = get_template("section_meeting")
    text = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
    )

    once, first_stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)
    twice, second_stats = snap_source_tags_to_transcript(once, DUP_TRANSCRIPT, template)

    assert first_stats["diversified"] == 1
    assert twice == once, "冪等：第二次套用不得再改動任何字元"
    assert second_stats["diversified"] == 0
    assert second_stats["diversify_skipped_no_candidate"] == 0


def test_規則6_cap上限_同一時間戳最多保留兩筆(monkeypatch):
    template = get_template("section_meeting")
    text = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
    )

    # cap=2（預設）：3 筆 → 搬 1 筆；cap=3：3 筆全數保留 → 0 筆搬移。
    _, cap2_stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)
    assert cap2_stats["diversified"] == 1

    monkeypatch.setattr(tp, "TAG_DIVERSIFY_MAX_PER_TIME", 3)
    out_cap3, cap3_stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)
    assert out_cap3 == text
    assert cap3_stats["diversified"] == 0


def test_規則6_無候選時原樣保留_fail_soft():
    template = get_template("section_meeting")
    # ±120 s 內除原時間戳外沒有其他段首（下一段在 345 s）→ 無候選。
    transcript = (
        "[00:00:00-00:05:45] 科長：甲。\n"
        "[00:05:45-00:06:00] 科長：乙。\n"
    )
    text = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
    )

    out, stats = snap_source_tags_to_transcript(text, transcript, template)

    assert out == text, "找不到候選 → 原樣保留（不刪、不改寫）"
    assert stats["diversified"] == 0
    assert stats["diversify_skipped_no_candidate"] == 1


def test_規則6_逐字稿缺段落_noop():
    template = get_template("section_meeting")
    text = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
    )

    out, stats = snap_source_tags_to_transcript(text, "沒有段落格式的逐字稿。\n", template)

    assert out == text
    assert stats["segments"] == 0
    assert stats["diversified"] == 0


def test_規則6_空標籤_永不改動():
    template = get_template("section_meeting")
    text = (
        "1.甲（00:00:00）。\n"
        "2.乙（00:00:00）。\n"
        "3.（10:30）不是標註格式，也不得被動。\n"
    )

    out, stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)

    assert out == text, "空標籤（無發言者）一律不碰（含正文的「（10:30）」）"
    assert stats["diversified"] == 0
    assert stats["diversify_skipped_no_candidate"] == 0


def test_規則6_時間戳非真實段首的重複群組不動_且格式異常不拋錯():
    template = get_template("section_meeting")
    # 05:00:00 不在任何真實段落內（規則 0-5 判不可回溯、原樣保留）；
    # 99:99:99 為異常值。兩者即使同標籤同戳成組，也不得被規則 6 搬動。
    text = (
        "1.甲（科長，05:00:00）。\n"
        "2.乙（科長，05:00:00）。\n"
        "3.丙（科長，99:99:99）。\n"
        "4.丁（科長，99:99:99）。\n"
    )

    out, stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)

    assert out == text, "非真實段首的重複群組（含異常時間值）一律原樣保留、不拋錯"
    assert stats["diversified"] == 0
    assert stats["untraceable"] == 4, "既有規則 0-5 的不可回溯計數不變"


def test_規則6_與規則0不衝突_已受保護的單筆不動():
    template = get_template("section_meeting")
    text = (
        "1.甲（科長，00:01:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
        "4.丁（科長，00:00:00）。\n"
    )

    out, stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)

    assert "（科長，00:01:00）" in out, "不在重複群組的段首標註一律不動（規則 0 語意）"
    assert stats["kept_on_start"] == 4, "規則 0-5 的計數只反映吸附階段（4 筆全在段首）"
    assert stats["diversified"] == 1


def test_規則6_無秒標註_只落整分鐘候選():
    template = get_template("section_meeting")
    text = (
        "1.甲（科長，00:01）。\n"
        "2.乙（科長，00:01）。\n"
        "3.丙（科長，00:01）。\n"
    )

    out, stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)

    # 候選 00:00:30 距 60 s（最小 |Δ|）但非整分鐘 → 不可用；
    # 00:00:00 與 00:01:00... 原時間戳不可用 → 落 00:00（|Δ| 同為 60、秒數小者勝）。
    assert out == (
        "1.甲（科長，00:01）。\n"
        "2.乙（科長，00:01）。\n"
        "3.丙（科長，00:00）。\n"
    )
    assert "00:00:30" not in out, "無秒標註的落點必須是整分鐘（沿用規則 4 可逆性）"
    assert stats["diversified"] == 1


def test_規則6_開關關閉_byte級golden(monkeypatch):
    template = get_template("section_meeting")
    transcript = (
        "[00:00:00-00:00:30] 科長：甲。\n"
        "[00:00:30-00:01:00] 科長：乙。\n"
        "[00:01:00-00:02:30] 科長：丙。\n"
    )
    text = (
        "1.甲（科長，00:00:20）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
    )
    # golden＝本波之前（HEAD 模組）對同一輸入的輸出：規則 1 吸附 + 規則 0 保護，
    # 無規則 6（三筆同戳 00:00:00 原樣保留）。
    golden = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
    )

    _disable_switch(monkeypatch)
    out_off, stats_off = snap_source_tags_to_transcript(text, transcript, template)

    assert out_off == golden, "關閉開關＝與本波之前 byte 級相同（函式級 golden）"
    assert stats_off["diversified"] == 0

    monkeypatch.undo()
    out_on, _ = snap_source_tags_to_transcript(text, transcript, template)
    assert out_on == (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:30）。\n"
    ), "開啟時，規則 1 吸附後形成的同戳群組會被規則 6 去重複化"


def test_規則6_不新增不刪除標註_也不改發言者文字():
    template = get_template("section_meeting")
    loaded = _load_real_record("B2")
    if loaded is None:
        pytest.skip("既有 B2 真實紀錄不存在")
    text, transcript = loaded

    out, stats = snap_source_tags_to_transcript(text, transcript, template)

    assert len(SOURCE_TAG_PATTERN.findall(out)) == len(SOURCE_TAG_PATTERN.findall(text))
    assert _labels(out) == _labels(text), "標籤（發言者文字）不得被改寫"
    assert stats["diversified"] > 0


def test_規則6_模板不支援或未提供_noop():
    text = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
    )

    out_none, stats_none = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, None)

    assert out_none == text
    assert stats_none["diversified"] == 0


def test_規則6_開關容錯_小寫欄位名也生效(monkeypatch):
    """handoff §4.2 凍結名為小寫；config 實際欄位為大寫——兩種寫法都要認。"""
    template = get_template("section_meeting")
    text = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
    )
    stub = type("_LowercaseSettings", (), {"local_source_tag_diversify_enabled": False})()
    monkeypatch.setattr("backend.core.config.settings", stub)

    out, stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)

    assert out == text
    assert stats["diversified"] == 0


def test_規則6_settings缺少欄位時預設開啟(monkeypatch):
    template = get_template("section_meeting")
    text = (
        "1.甲（科長，00:00:00）。\n"
        "2.乙（科長，00:00:00）。\n"
        "3.丙（科長，00:00:00）。\n"
    )
    stub = type("_BareSettings", (), {})()
    monkeypatch.setattr("backend.core.config.settings", stub)

    out, stats = snap_source_tags_to_transcript(text, DUP_TRANSCRIPT, template)

    assert stats["diversified"] == 1, "欄位未落地（getattr 容錯）時預設開啟"
    assert "（科長，00:00:30）" in out


# ---------------------------------------------------------------------------
# 真實素材（B2／D1）：量尺不退步、冪等、off＝既有產物 byte 不變
# ---------------------------------------------------------------------------


def test_規則6_真實B2_辨別力達標且各項量尺不退步():
    template = get_template("section_meeting")
    loaded = _load_real_record("B2")
    if loaded is None:
        pytest.skip("既有 B2 真實紀錄不存在")
    text, transcript = loaded

    before = measure_tag_traceability(text, transcript)
    once, stats = snap_source_tags_to_transcript(text, transcript, template)
    after = measure_tag_traceability(once, transcript)
    twice, second_stats = snap_source_tags_to_transcript(once, transcript, template)

    assert before["tags_total"] == 52 and before["distinct_tag_time_ratio"] == pytest.approx(0.288, abs=0.001)
    assert after["distinct_tag_time_ratio"] >= 0.5, "plan §9.6 驗收：B2 ≥0.5"
    assert after["on_start_tag_ratio"] >= before["on_start_tag_ratio"]
    assert after["on_start_tag_ratio_excluding_zero"] >= before["on_start_tag_ratio_excluding_zero"]
    assert after["traceable_tag_ratio"] >= before["traceable_tag_ratio"]
    assert after["tags_total"] == before["tags_total"]
    assert twice == once and second_stats["diversified"] == 0, "冪等"
    assert stats["diversify_max_shift_seconds"] <= tp.TAG_SNAP_MAX_SHIFT_SECONDS


def test_規則6_真實D1_不退步且冪等():
    template = get_template("section_meeting")
    loaded = _load_real_record("D1")
    if loaded is None:
        pytest.skip("既有 D1 真實紀錄不存在")
    text, transcript = loaded

    before = measure_tag_traceability(text, transcript)
    once, stats = snap_source_tags_to_transcript(text, transcript, template)
    after = measure_tag_traceability(once, transcript)
    twice, second_stats = snap_source_tags_to_transcript(once, transcript, template)

    assert before["distinct_tag_time_ratio"] == pytest.approx(0.667, abs=0.001)
    assert after["distinct_tag_time_ratio"] >= before["distinct_tag_time_ratio"], "plan §9.6：D1 ≥0.667 不退步"
    assert after["on_start_tag_ratio"] >= before["on_start_tag_ratio"]
    assert after["traceable_tag_ratio"] >= before["traceable_tag_ratio"]
    assert after["tags_total"] == before["tags_total"]
    assert twice == once and second_stats["diversified"] == 0
    assert stats["diversified"] >= 1


def test_規則6_真實四場_off模式等於既有產物byte不變(monkeypatch):
    """B2／D1／D2 為 P3 修正後的產物（其吸附已是本波前的不動點）→ off 必 byte 相同。"""
    template = get_template("section_meeting")
    checked = 0
    for key in ("B2", "D1", "D2"):
        loaded = _load_real_record(key)
        if loaded is None:
            continue
        text, transcript = loaded
        _disable_switch(monkeypatch)
        out_off, stats_off = snap_source_tags_to_transcript(text, transcript, template)
        monkeypatch.undo()
        assert out_off == text, f"{key}：關閉開關必須 byte 級等於既有產物"
        assert stats_off["diversified"] == 0
        checked += 1
    if checked == 0:
        pytest.skip("既有真實紀錄不存在")
