# -*- coding: utf-8 -*-
"""T20260922-1930-01 W6 — 紀錄品質量測儀（deterministic metrics）單元測試。

權威來源：plan.md W6／§5（CORE-1、CORE-2 的儀器）；handoff 軌 C 要求：
- 彙整表標註與正文標註分開計數；
- 開頭欄位（時間／地點／主持人／出席人員／紀錄）的標註排除於正文計數；
- tagged_item_ratio 以正文條目為分母；
- 已知誤辨左側（錯形）與右側（修正）命中分開回報；
- DOCX 輸入一律 SKIP（段落合併使計數不可信）。

本檔 fixture 全部為內嵌字面，**不得**讀 data/cache/*（該樹 gitignored）。
量測儀以 importlib 載入（scripts/ 非 package），與 test_owned_e2e_acceptance.py 同慣例。
"""

import importlib.util
import json
import os
import tempfile
from pathlib import Path

# backend import 會建立 DATA_DIR/logs；先備妥隔離目錄（同 test_t20260922_record_quality.py）。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-record-metrics-"))

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_PATH = REPO_ROOT / "scripts" / "e2e" / "measure_record_quality.py"


def _load_metrics_module():
    spec = importlib.util.spec_from_file_location(
        "measure_record_quality_under_test", METRICS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


metrics = _load_metrics_module()

EXPECTED_KEYS = {
    "char_count",
    "body_source_tag_count",
    "table_source_tag_count",
    "non_prefixed_tableish_source_tag_count",
    "instruction_item_count",
    "tagged_item_ratio",
    "cross_section_duplicate_pairs",
    "known_term_fix_hits",
    "unsupported_entities",
    "notes",
}

# 表格列標註只算 table；正文條目標註只算 body（（科長，00:05:36）為標註形式）。
FIXTURE_TABLE_AND_BODY = """# 科務會議紀錄

時間：中華民國115年9月3日
主持人：科長

| 案由及承辦單位 | 辦理情形 |
| --- | --- |
| 組織異動調整（科長，00:05:36）| 資管股： |

一、科長轉知局務會議工作報告及相關注意事項：
1. 土地稅科配合辦理交接。（科長，00:09:55）
"""

# 開頭欄位（時間／主持人／紀錄）帶標註：一筆都不得計入正文；表格列另計。
FIXTURE_HEADER_FIELD_TAGS = """# 科務會議紀錄

時間：115年9月3日（科長，00:00:10）
主持人：科長（發言者1，00:01:00）
紀錄：AI 會議助理（系統，00:00:10）

| 案由 | 辦理情形 |
| --- | --- |
| 組織異動（科長，00:05:36）| 資管股： |

1. 正文一句。（科長，00:05:36）
"""

# 條目比率：2 個 leaf item 中 1 個帶標註＝0.5；非條目的正文標註不進分母。
FIXTURE_ITEM_RATIO = """# 科務會議紀錄

1. 有標註的條目。（科長，00:05:36）
2. 無標註的條目。

補述句。（科長，00:06:48）
"""


def test_table_tags_counted_separately_from_body_tags():
    result = metrics.measure_record_quality(FIXTURE_TABLE_AND_BODY)

    assert result["table_source_tag_count"] == 1, "表格列標註必須計入 table 計數"
    assert result["body_source_tag_count"] == 1, "正文標註必須與表格標註分開計數"


def test_inline_pipe_in_body_line_counted_as_body_not_table():
    fixture = """# 科務會議紀錄

1. 統計數字 | 備註說明。（科長，00:05:36）
"""
    result = metrics.measure_record_quality(fixture)

    assert result["table_source_tag_count"] == 0, (
        "正文行內單一 '|' 不符表格列定義（TABLE_ROW_PATTERN＝^\\s*\\|），"
        "不得計為表格標註（軌 D 稽核 §6 的 false-FAIL 形狀）"
    )
    assert result["body_source_tag_count"] == 1, "該標註必須計入正文計數"
    assert result["non_prefixed_tableish_source_tag_count"] == 0, (
        "單一管線字元夾在正文句子中不算表格樣態，觀察值不得計入"
    )


def test_fullwidth_tableish_row_tag_visible_only_in_observation():
    fixture = """# 科務會議紀錄

｜ 組織異動（科長，00:05:36）｜ 資管股： ｜
"""
    result = metrics.measure_record_quality(fixture)

    assert result["table_source_tag_count"] == 0, (
        "全形 '｜' 列不符 TABLE_ROW_PATTERN（ASCII ^\\s*\\|），不得計為表格標註"
    )
    assert result["non_prefixed_tableish_source_tag_count"] == 1, (
        "全形表格樣態列的標註必須在新觀察值中可見（永不閘門）"
    )
    assert result["body_source_tag_count"] == 1, (
        "不符表格列定義者依語意仍屬正文計數；觀察值只加可視化、不改計數語意"
    )


def test_header_field_tags_excluded_from_body_count():
    result = metrics.measure_record_quality(FIXTURE_HEADER_FIELD_TAGS)

    assert result["body_source_tag_count"] == 1, (
        "時間／主持人／紀錄等開頭欄位的標註不得計入正文（同 summarization.py 排除語意）"
    )
    assert result["table_source_tag_count"] == 1, "表格列標註仍須獨立計數"
    assert result["notes"]["observed"]["excluded_header_field_tag_count"] == 3, (
        "排除的開頭欄位標註數必須記錄在 notes.observed"
    )


def test_tag_ratio_computed_on_body_items():
    result = metrics.measure_record_quality(FIXTURE_ITEM_RATIO)

    assert result["tagged_item_ratio"] == 0.5, (
        f"比率分母必須是正文 leaf item（2 中 1 帶標註＝0.5）：{result['tagged_item_ratio']}"
    )
    assert result["body_source_tag_count"] == 2, "正文標註計數含非條目補述句"
    assert result["instruction_item_count"] == 2, "找不到指示及提醒章節時以全文 leaf item 計"


def test_instruction_item_count_scoped_to_instruction_section():
    fixture = """# 科務會議紀錄

一、科長轉知局務會議工作報告：
1. 轉知事項一。（科長，00:05:36）
2. 轉知事項二。（科長，00:06:48）

二、科長指示及提醒事項：
1. 指示一。（科長，00:30:33）
2. 指示二。（科長，00:31:34）
3. 指示三。（科長，00:32:33）

散會：下午五時。
"""
    result = metrics.measure_record_quality(fixture)

    assert result["instruction_item_count"] == 3, (
        "指示及提醒章節的條目數不得把「科長轉知」章節的條目算進來"
    )


def test_known_term_fix_hits_report_left_and_right_separately():
    fixture = "本次提及增收股與征收股，正確名稱為徵收股；另瑞裏與瑞里並存。"
    hits = metrics.count_known_term_fix_hits(fixture)

    assert hits["left_hits"] == 3, f"左側（錯形）命中：增收股／征收股／瑞裏＝3：{hits}"
    assert hits["right_hits"] == 2, f"右側（修正）命中：徵收股／瑞里＝2（同一 replacement 不重複累加）：{hits}"
    assert any("征收股" in pattern for pattern in hits["left_by_form"]), (
        "逐條左側命中必須以 SECTION_MEETING_RECORD_TERM_FIXES 的 pattern 為 key"
    )
    assert hits["right_by_form"].get("徵收股") == 1


def test_docx_input_prints_skip_and_exits_zero(capsys, tmp_path):
    docx_path = tmp_path / "meeting_record.docx"
    docx_path.write_bytes(b"PK\x03\x04fake-docx-bytes")

    exit_code = metrics.main(["--record", str(docx_path)])
    captured = capsys.readouterr()

    assert exit_code == 0, "DOCX 輸入必須優雅 SKIP（exit 0），不得假裝量測"
    assert "SKIP" in captured.out, f"必須明講段落合併使 DOCX 計數不可信：{captured.out!r}"
    assert "char_count" not in captured.out, "SKIP 時不得輸出任何指標 JSON"


def test_json_output_has_exact_keys_and_observation_only_note(capsys, tmp_path):
    record_path = tmp_path / "record.md"
    record_path.write_text(FIXTURE_TABLE_AND_BODY, encoding="utf-8")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("組織異動調整，資管股配合辦理。", encoding="utf-8")

    exit_code = metrics.main(
        ["--record", str(record_path), "--transcript", str(transcript_path), "--template", "section_meeting"]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(captured.out)
    assert set(payload) == EXPECTED_KEYS, f"輸出 schema 必須固定：{sorted(payload)}"
    assert payload["unsupported_entities"] is None or isinstance(payload["unsupported_entities"], list)
    assert "永不作為閘門" in payload["notes"]["unsupported_entities"], (
        "unsupported_entities 必須在 notes 明訂為觀察值（永不閘門）"
    )
    assert "永不作為閘門" in payload["notes"]["non_prefixed_tableish_source_tag_count"], (
        "non_prefixed_tableish_source_tag_count 必須在 notes 明訂為觀察值（永不閘門）"
    )
    assert "P1-13" in payload["notes"]["non_prefixed_tableish_source_tag_count"], (
        "notes 必須說明殘餘缺口的層級（P1-13）與不閘門理由"
    )
    assert isinstance(payload["known_term_fix_hits"]["transcript"], dict), (
        "提供 --transcript 時必須附逐字稿的同規則命中"
    )


def test_unsupported_entities_is_observation_only_list():
    record = "股別調整為「煙酒業務股」與「土雞股」。"
    transcript = "煙酒業務股需盤點。"
    result = metrics.measure_record_quality(record, transcript_text=transcript)

    assert result["unsupported_entities"] == ["土雞股"], (
        "僅輸出逐字稿未出現的組織型專名，且純為觀察值："
        f"{result['unsupported_entities']}"
    )
