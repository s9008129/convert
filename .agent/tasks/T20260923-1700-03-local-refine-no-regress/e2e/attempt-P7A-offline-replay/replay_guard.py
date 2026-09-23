# -*- coding: utf-8 -*-
"""P7-A 離線重播：用**真實素材**驗證「不回退守衛」在正式驗證器下的判定。

素材（全部來自真實場次，非合成）：
- 逐字稿：`data/cache/e2e/p6a-gemma31b-e6/transcript.txt`（gemma31B E6 場實際使用的校正後逐字稿）
- 萃取筆記：`/tmp/notes_repro/qwen_e5b_chunk1_notes.txt`（qwen27B E5b 場真實萃取筆記；
  本場 notes 未落檔，故以同素材、同模板的真實筆記替代——已如實標註）
- 紀錄版本：gemma31B E6 場真實交付紀錄（`0903-科務會議_f9fee652.md`）＝**最後一版**
  與其「把 600 元寫回」的變體＝**中途較佳的那一版**（模擬 15:35 第 1 輪的狀態）
  ※ 中途版本本體未落檔（log 只有字元數與未涵蓋集合），故此處以真實紀錄 + 該場
    log 記載的差異（數字 600）重建；其餘內容一字未動。
"""
import json
import os
import sys

os.environ.setdefault("DATA_DIR", "/tmp/p7a_replay_data")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
while not os.path.isdir(os.path.join(REPO_ROOT, "backend")) and REPO_ROOT != "/":
    REPO_ROOT = os.path.dirname(REPO_ROOT)
sys.path.insert(0, REPO_ROOT)
os.chdir(REPO_ROOT)

from backend.core.config import settings  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402

TRANSCRIPT = open("data/cache/e2e/p6a-gemma31b-e6/transcript.txt", encoding="utf-8").read()
NOTES = open("/tmp/notes_repro/qwen_e5b_chunk1_notes.txt", encoding="utf-8").read()
FINAL = open(
    "data/cache/e2e/p6a-gemma31b-e6/backend_data/outputs/0903-科務會議_f9fee652.md",
    encoding="utf-8",
).read()

# 依 E6 log（15:35 第 1 輪曾把 600 補回、15:42 第 2 輪又掉）重建「較佳版本」：
# 在文康禮券相關段落補上 600 元字面（其餘內容與真實交付版一字不差）。
BETTER = FINAL.replace("分發禮券/現金」", "分發禮券/現金，禮券 600 元」", 1)
assert BETTER != FINAL, "重建失敗：找不到可插入 600 的錨點（請改錨點後重跑）"

settings.LOCAL_LLM_RECORD_COVERAGE_MODE = "observe"
service = SummarizationService()


def probe(name: str, record: str) -> dict:
    issues = service._validate_record_source_coverage(record, NOTES, TRANSCRIPT)
    snap = service._core_coverage_snapshot()
    stats = dict(service._record_coverage_stats or {})
    assert issues == [], f"observe 模式不得產生補強問題（{name}）"
    return {
        "version": name,
        "chars": len(record),
        "snapshot_missing_expected": list(snap[:2]),
        "missing_items_core": sorted(snap[2]),
        "missing_by_category": {k: stats.get(f"missing_{k}", 0) for k in ("topic", "decision", "number", "date")},
        "expected_by_category": {k: stats.get(f"expected_{k}", 0) for k in ("topic", "decision", "number", "date")},
    }


better = probe("中途較佳版（600 元已寫回）", BETTER)
final = probe("最後一版（真實交付）", FINAL)

# 用**產品路徑同一份**判定函式重播（不是重寫一份比較邏輯）
snap_better = probe.__wrapped__ if False else None  # noqa: F841
service._validate_record_source_coverage(BETTER, NOTES, TRANSCRIPT)
snap_better = service._core_coverage_snapshot()
service._validate_record_source_coverage(FINAL, NOTES, TRANSCRIPT)
snap_final = service._core_coverage_snapshot()
reason = SummarizationService._refinement_regression_reason(snap_better, snap_final)
print(json.dumps({
    "better": better,
    "final": final,
    "guard_would_revert": bool(reason),
    "guard_reason": reason,
}, ensure_ascii=False, indent=2))
