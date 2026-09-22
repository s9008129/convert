# -*- coding: utf-8 -*-
"""事實涵蓋率量尺（measure_coverage.py）單元測試。

權威來源：涵蓋率量尺規格（metric_version ``coverage-1.0.0``）。本檔 fixture 全部
內嵌字面，**不得**讀 ``data/cache/*``（該樹 gitignored，且 E2E 正在跑、worktree
必須保持乾淨）。量尺以 importlib 載入（staging 版與 scripts/e2e 版同慣例，見
``tests/test_record_quality_metrics.py``）。

覆蓋要求：
- 全形／半形、大小寫與 CRLF；
- 繁體／簡體雙向折疊；
- 標點與換行差異不影響匹配；
- probes 的 group 內 AND／group 間 OR；
- core／supporting 分開統計與漏寫清單；
- 空 checklist；
- OpenCC 不可用的 fallback 路徑（monkeypatch）＋雙向對稱；
- 確定性（同輸入兩次結果相同；CLI 亦同）；
- CLI 輸出檔（JSON／Markdown）與退出碼。
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# 量尺 import 時會 setdefault DATA_DIR（同既有測試慣例）：先備妥隔離目錄。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-coverage-"))

# 量尺本體在 scripts/e2e/（與 scripts/e2e/measure_record_quality.py 同層）；
# 測試檔路徑與它不同層，因此以 repo root 為基準解析。
REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts/e2e/measure_coverage.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("measure_coverage_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


metrics = _load_module()

REQUIRED_KEYS = {
    "metric_version",
    "label",
    "record_path",
    "record_sha256",
    "checklist_path",
    "checklist_sha256",
    "fact_total",
    "fact_core_total",
    "fact_supporting_total",
    "covered_total",
    "covered_core",
    "covered_supporting",
    "coverage_all",
    "coverage_core",
    "coverage_supporting",
    "missing_core_ids",
    "missing_core_statements",
    "missing_supporting_ids",
    "by_category",
    "record_char_count",
    "record_normalized_char_count",
    "normalization",
    "warnings",
    "transcript",
    "facts",
    "notes",
}


def _fact(fact_id, statement="一句話事實", *, tier="core", category="decision", probes=None):
    return {
        "id": fact_id,
        "category": category,
        "tier": tier,
        "statement": statement,
        "evidence": "（測試用 fixture）",
        "probes": probes if probes is not None else [[fact_id]],
    }


def _checklist(facts, **extra):
    payload = {"checklist_version": "1.0.0", "meeting": "測試會議", "facts": facts}
    payload.update(extra)
    return payload


def _measure(record, facts, **kwargs):
    return metrics.measure_coverage(record, _checklist(facts), **kwargs)


def _opencc_available():
    return metrics.create_opencc_fold()[0] is not None


def test_report_schema_and_metric_version():
    report = _measure("決議：採用人工智慧輔助紀錄。", [_fact("F001", probes=[["人工智慧"]])])
    assert REQUIRED_KEYS <= set(report)
    assert report["metric_version"] == "coverage-1.0.0"
    assert report["notes"]["definitions"]["coverage_all"]
    assert "generated_at" not in report  # 預設不寫時間戳（確定性）


def test_full_width_casefold_and_crlf_are_normalized():
    record = "決議：全面採用 ＡＩ 輔助（Ｑｗｅｎ 模型）\r\n\r\n後續由資管股追蹤。"
    report = _measure(record, [_fact("F001", probes=[["ai輔助"], ["Qwen模型"]])])
    assert report["covered_total"] == 1
    detail = report["facts"][0]
    assert detail["covered"] is True
    assert detail["matched_group_index"] == 0
    assert detail["matched_positions"] == [6]
    assert detail["reason"] is None


@pytest.mark.skipif(not _opencc_available(), reason="OpenCC 不可用（環境缺依賴）")
def test_simplified_traditional_fold_is_symmetric():
    simplified_record = "会议决议：组织规程调整，土地税科分拆。"
    traditional_record = "會議決議：組織規程調整，土地稅科分拆。"
    # 簡體紀錄 × 繁體 token。
    report = _measure(simplified_record, [_fact("F001", probes=[["組織規程"]])])
    assert report["covered_total"] == 1
    assert report["normalization"]["opencc_available"] is True
    # 繁體紀錄 × 簡體 token（反向）。
    report = _measure(traditional_record, [_fact("F001", probes=[["组织规程"]])])
    assert report["covered_total"] == 1


def test_punctuation_and_newline_differences_do_not_break_matching():
    record = "因颱風導致倉庫漏水，\r\n部分土地稅卡損毀；本單位配合重新列印。"
    report = _measure(record, [_fact("F001", probes=[["土地稅卡", "重新列印"]])])
    assert report["covered_total"] == 1
    assert report["facts"][0]["covered"] is True


def test_probe_group_internal_and_between_group_or():
    record = "會中僅提到人事調整與資訊安全。"
    report = _measure(
        record,
        [
            _fact("AND_FAIL", probes=[["人事調整", "資安演練"]]),  # 只中一半 → group 不成立
            _fact("OR_HIT", probes=[["預算編列"], ["資訊安全"]]),  # 第 1 組命中
            _fact("ALL_MISS", probes=[["環境"], ["設備"]]),
        ],
    )
    by_id = {fact["id"]: fact for fact in report["facts"]}
    assert by_id["AND_FAIL"]["covered"] is False
    assert by_id["AND_FAIL"]["reason"] == "no_probe_group_matched"
    assert by_id["OR_HIT"]["covered"] is True
    assert by_id["OR_HIT"]["matched_group_index"] == 1
    assert by_id["ALL_MISS"]["covered"] is False
    assert report["covered_total"] == 1


def test_core_and_supporting_are_counted_separately():
    record = "決議：採用人工智慧輔助紀錄。"
    missing_statement = "量子電腦採購案尚未決議"
    facts = [
        _fact("C1", probes=[["人工智慧"]]),
        _fact("C2", statement=missing_statement, probes=[["量子電腦"]]),
        _fact("S1", tier="supporting", category="topic", probes=[["區塊鏈"]]),
    ]
    report = _measure(record, facts)
    assert report["fact_total"] == 3
    assert report["fact_core_total"] == 2
    assert report["fact_supporting_total"] == 1
    assert report["covered_total"] == 1
    assert report["covered_core"] == 1
    assert report["covered_supporting"] == 0
    assert report["coverage_all"] == round(1 / 3, 4)
    assert report["coverage_core"] == 0.5
    assert report["coverage_supporting"] == 0.0
    assert report["missing_core_ids"] == ["C2"]
    assert report["missing_core_statements"] == [missing_statement]
    assert report["missing_supporting_ids"] == ["S1"]
    assert report["by_category"]["decision"] == {"total": 2, "covered": 1, "coverage": 0.5}
    assert report["by_category"]["topic"] == {"total": 1, "covered": 0, "coverage": 0.0}


def test_empty_checklist_yields_zero_coverage_and_warning():
    report = _measure("任何紀錄內容。", [])
    assert report["fact_total"] == 0
    assert report["coverage_all"] == 0.0
    assert report["coverage_core"] == 0.0
    assert report["coverage_supporting"] == 0.0
    assert report["by_category"] == {}
    assert any("空清單" in warning for warning in report["warnings"])


def test_opencc_unavailable_fallback_is_marked_and_symmetric(monkeypatch):
    monkeypatch.setattr(metrics, "create_opencc_fold", lambda: (None, "none"))
    record = "會議決議：組織規程調整。"
    facts = [
        _fact("T1", probes=[["組織規程"]]),
        _fact("S1", probes=[["组织规程"]]),
    ]
    report = _measure(record, facts)
    assert report["normalization"]["opencc_available"] is False
    assert report["normalization"]["opencc_source"] == "none"
    assert any("OpenCC 不可用" in warning for warning in report["warnings"])
    by_id = {fact["id"]: fact for fact in report["facts"]}
    assert by_id["T1"]["covered"] is True  # 同寫法仍可比
    assert by_id["S1"]["covered"] is False  # 簡繁不再互通：誠實降級，不假裝能折疊


def test_matched_positions_capped_at_three():
    record = "阿甲、阿乙、阿丙、阿丁。"
    report = _measure(record, [_fact("F001", probes=[["阿甲", "阿乙", "阿丙", "阿丁"]])])
    detail = report["facts"][0]
    assert detail["covered"] is True
    assert len(detail["matched_positions"]) == 3


def test_short_token_duplicate_id_and_empty_normalized_token_warnings():
    facts = [
        _fact("F001", probes=[["的"], ["：", "決議"]]),
        _fact("F001", probes=[["決議通過"]]),
    ]
    report = _measure("決議通過。", facts)
    warnings = report["warnings"]
    assert any("少於 2 字" in warning for warning in warnings)
    assert any("重複" in warning for warning in warnings)
    assert any("正規化後為空" in warning for warning in warnings)


def test_transcript_block_is_observational_only():
    record = "決議：僅記錄甲案。"
    checklist = _checklist([_fact("F001", probes=[["乙案"]])])
    transcript = "[00:01:00-00:02:00] 發言者1：乙案先處理。"
    report = metrics.measure_coverage(
        record,
        checklist,
        transcript_text=transcript,
        transcript_path="逐字稿.txt",
        transcript_sha256="0" * 64,
    )
    assert report["covered_total"] == 0
    assert report["transcript"]["covered_total"] == 1
    assert report["transcript"]["missing_core_ids"] == []
    assert "觀察值" in report["transcript"]["note"]


def test_same_inputs_produce_identical_json():
    record = "決議：採用人工智慧輔助紀錄，並於下週一前完成。"
    facts = [
        _fact("F001", probes=[["人工智慧"]]),
        _fact("F002", category="date", tier="supporting", probes=[["下週一"]]),
    ]
    kwargs = {"label": "x", "record_path": "r.md", "checklist_path": "c.json"}
    first = metrics.measure_coverage(record, _checklist(facts), **kwargs)
    second = metrics.measure_coverage(record, _checklist(facts), **kwargs)
    assert json.dumps(first, ensure_ascii=False, indent=2) == json.dumps(
        second, ensure_ascii=False, indent=2
    )


@pytest.mark.skipif(not metrics._pinyin_available(), reason="pypinyin 不可用（環境缺依賴）")
def test_fuzzy_homophone_is_opt_in_and_deterministic():
    record = "決議：由睡務股負責後續作業。"
    facts = [_fact("F001", probes=[["稅務股"]])]
    exact = _measure(record, facts)
    assert exact["normalization"]["fuzzy"] is False
    assert exact["facts"][0]["covered"] is False  # 預設純字面
    fuzzy_first = _measure(record, facts, fuzzy=True)
    fuzzy_second = _measure(record, facts, fuzzy=True)
    assert fuzzy_first["normalization"]["fuzzy"] is True
    assert fuzzy_first["normalization"]["fuzzy_mode"] == "pinyin_per_char_near_syllable"
    assert fuzzy_first["facts"][0]["covered"] is True
    assert json.dumps(fuzzy_first, ensure_ascii=False) == json.dumps(
        fuzzy_second, ensure_ascii=False
    )


def _cli_env():
    # 子行程以同一支 Python 執行；PYTHONPATH 保留呼叫端設定即可。
    return os.environ.copy()


def test_cli_is_deterministic_and_writes_outputs(tmp_path):
    record = tmp_path / "record.md"
    record.write_text("決議：全面採用 ＡＩ 輔助（下週一啟用）。", encoding="utf-8")
    checklist = tmp_path / "checklist.json"
    checklist.write_text(
        json.dumps(
            _checklist(
                [
                    _fact("F001", probes=[["ai輔助"]]),
                    _fact("F002", category="date", tier="supporting", probes=[["下週一"]]),
                ]
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    json_out = tmp_path / "out.json"
    md_out = tmp_path / "out.md"
    command = [
        sys.executable,
        str(MODULE_PATH),
        "--record",
        str(record),
        "--checklist",
        str(checklist),
        "--label",
        "cli-test",
        "--json-out",
        str(json_out),
        "--md-out",
        str(md_out),
    ]
    first = subprocess.run(command, capture_output=True, env=_cli_env())
    second = subprocess.run(command, capture_output=True, env=_cli_env())
    assert first.returncode == 0, first.stderr.decode("utf-8")
    assert first.stdout == second.stdout  # 同輸入 → byte 相同 stdout
    assert json_out.read_bytes() == first.stdout
    payload = json.loads(first.stdout.decode("utf-8"))
    assert payload["label"] == "cli-test"
    assert payload["covered_total"] == 2
    assert payload["record_sha256"] and payload["checklist_sha256"]
    markdown = md_out.read_text(encoding="utf-8")
    assert markdown.startswith("# 事實涵蓋率報告：cli-test")
    assert "coverage_all" in markdown


def test_cli_rejects_missing_files_and_docx(tmp_path):
    checklist = tmp_path / "checklist.json"
    checklist.write_text(json.dumps(_checklist([])), encoding="utf-8")

    missing = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--record",
            str(tmp_path / "nope.md"),
            "--checklist",
            str(checklist),
        ],
        capture_output=True,
        env=_cli_env(),
    )
    assert missing.returncode == 2

    docx = tmp_path / "record.docx"
    docx.write_bytes(b"PK\x03\x04")
    rejected = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--record",
            str(docx),
            "--checklist",
            str(checklist),
        ],
        capture_output=True,
        env=_cli_env(),
    )
    assert rejected.returncode == 2
    assert b"Markdown" in rejected.stderr
