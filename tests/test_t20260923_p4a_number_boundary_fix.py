# -*- coding: utf-8 -*-
"""P4-A 數字對帳器「子字串假命中」修補（T20260922-2037-02；E3 真實音檔實證）。

背景（E3 場 `Qwen3.8-27B-Splash` in-run 指標 `cov_expected_number=9／
cov_missing_number=0`＋獨立驗收逐條 grep）：兩個逐字稿真有的數字被誤判成
「已涵蓋」→ 補強輪不去補（真缺口＝漏檢）：

  T-35 數字邊界：`600`（逐字稿「發 600塊」）命中在紀錄的 `13,600` 內；
       `15`（逐字稿「少了 15%」）命中在紀錄自己的清單編號 `15.` 上
  T-36 不得放寬：真缺口、序號、小數一律仍判缺（方向只加嚴）
  T-37 不得過嚴：`600元`／`15%`／`13600元`／`13,600 ≡ 13600`／`17個人` 仍命中
  T-38 E3 縮樣：同一段逐字稿＋紀錄縮樣，只有那兩個真缺口翻身，其餘不動
  T-39 無副作用：日期用的舊折疊（`_fold_record_for_number_matching`）契約不變

全部純函式／payload 級，不依賴 LM Studio／Ollama／網路。
"""

import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-t20260923-p4a-num-"))

from backend.services.summarization import SummarizationService  # noqa: E402

# E3 逐字稿原文（逐字取自 0903-科務會議_d48ce298_逐字稿.txt 的段落列）
TRANSCRIPT_600 = "[00:11:40-00:11:42] 發言者1：你就發 600塊，然後那個便當還加上飲料。\n"
TRANSCRIPT_15 = "[00:10:20-00:10:40] 發言者2：委任的部分就會少了 15%。\n"
# E3 最終紀錄縮樣（逐字取自 0903-科務會議_d48ce298.md）：`13,600` 與條列序號 `15.`
RECORD_E3 = (
    "（三）文康活動：預算 17人每人800元，總計13,600元（發言者1，00:11:52）。\n"
    "15. 辦公室搬遷與漏水處理：待其整理出清單後續辦（科長，00:31:34）。\n"
)


def _service() -> SummarizationService:
    return SummarizationService()


def _missing_numbers(record: str, transcript: str) -> tuple:
    service = _service()
    issues = service._validate_record_source_coverage(record, "", transcript)
    return service._record_coverage_stats, [i for i in issues if i.startswith("數字遺漏")]


# --- T-35 數字邊界：命中片段不得是更長數字串的一部分 -----------------------


def test_T35_數字邊界_600與15的兩個真實假命中():
    """E3 實證：`600` ⊂ `13,600`、`15` ⊂ 條列序號 `15.` 都不算覆蓋。"""
    stats, issues = _missing_numbers(RECORD_E3, TRANSCRIPT_600 + TRANSCRIPT_15)

    assert stats["expected_number"] == 2, "逐字稿的 600／15 都已進入期望集合"
    assert stats["missing_number"] == 2, f"兩個真缺口都必須判缺：{stats}"
    assert len(issues) == 1, "同類別只出一條問題字串"
    assert "600" in issues[0] and "15" in issues[0], issues[0]
    assert "原文「" in issues[0], "問題字串必須附逐字稿原文片段（可 grep 可核）"


def test_T35b_數字邊界_更長數字串與小數都不得命中():
    """`600` 不得命中 `6000`；`15` 不得命中 `150`／小數 `12.15`／`15.5`。"""
    covered = SummarizationService._number_literal_is_covered

    assert not covered("600", "預算 6000 元。")
    assert not covered("600", "總計 13,600 元。")
    assert not covered("600", "總計 13600 元。")
    assert not covered("600", "編號 1600 元。")
    assert not covered("15", "共 150 人出席。")
    assert not covered("15", "比例 12.15%。")
    assert not covered("15", "比例 15.5%。")
    assert not covered("50", "比例 12.50%。")
    assert covered("600", "每人 600元禮券。"), "正常命中不得退化"
    assert covered("50", "比例 25.0% 與 50% 都出現。")


def test_T35c_清單編號不算覆蓋證據_但正文出現時仍算():
    """行首清單編號（`15.`／`15、`／`15)`／`15）`／`- 15.`）是版面標記，不是內容。"""
    covered = SummarizationService._number_literal_is_covered
    fold = SummarizationService._fold_record_for_number_coverage

    for marker in ("15. 辦公室搬遷", "15、辦公室搬遷", "15) 辦公室搬遷", "15）辦公室搬遷", "- 15. 辦公室搬遷"):
        assert not covered("15", fold(marker)), f"序號 {marker!r} 不得當成 15 的覆蓋證據"
    assert not covered("15", fold("15.委任比例少了 15.5%")), "`15.5` 不是編號，不得被剝掉後再誤命中"
    assert covered("15", fold("15. 委任比例少了 15%。")), "正文真的有 15% 時仍必須算覆蓋"


# --- T-36／T-37 不得放寬、不得過嚴 ---------------------------------------


def test_T36_真缺口仍判缺_序號與來源標註不得當覆蓋():
    stats, issues = _missing_numbers("15. 辦公室搬遷與漏水處理", TRANSCRIPT_15)
    assert stats["missing_number"] == 1 and "15" in issues[0]

    stats, issues = _missing_numbers("改發禮券（科長，00:17:52）。", "[00:17:00-00:17:30] 甲：有 17 個人所以 13600。")
    assert stats["missing_number"] == 2, "來源標註內的 17 仍不得當覆蓋（既有 T-09 契約不變）"


def test_T37_千分位與常見寫法不得過嚴():
    """`600元`／`15%`／`13600元`／`13,600 ≡ 13600`／`17個人` 一律仍算已涵蓋。"""
    cases = (
        ("文康活動：每人發 600元禮券。", "[00:10:00-00:10:20] 甲：那就發 600塊，然後便當加上飲料。"),
        ("委任比例少了 15%。", "[00:10:20-00:10:40] 乙：委任的部分就會少了 15%。"),
        ("預算總計 13,600 元。", "[00:10:40-00:11:00] 丙：總共 13600 元。"),
        ("預算總計 13600 元。", "[00:11:00-00:11:20] 丁：總共 13,600 元。"),
        ("預算 17人每人800元。", "[00:11:20-00:11:40] 戊：有 17個人。"),
    )
    for record, transcript in cases:
        stats, issues = _missing_numbers(record, transcript)
        assert stats["missing_number"] == 0, f"不得過嚴：{record!r}／{transcript!r} → {stats}／{issues}"


def test_T38_E3縮樣_兩個真缺口翻身其餘不動():
    """同一份 E3 縮樣＋逐字稿：`600`／`15` 判缺，`800`／`17`／`13600` 仍算已涵蓋。"""
    transcript = TRANSCRIPT_600 + TRANSCRIPT_15 + "[00:11:52-00:12:00] 發言者3：有 17個人所以 13600。\n"
    service = _service()
    issues = service._validate_record_source_coverage(RECORD_E3, "", transcript)
    stats = service._record_coverage_stats

    assert stats["expected_number"] == 4, [lit for lit, _ in SummarizationService._scan_transcript_number_items(transcript)]
    assert stats["missing_number"] == 2, f"只該有 600／15 兩個真缺口：{stats}"
    issue = [i for i in issues if i.startswith("數字遺漏")][0]
    assert "800" not in issue and "13600" not in issue and "17" not in issue, issue


def test_T39_日期用的舊折疊契約不變():
    """只新增數字專用折疊；日期仍走 `_fold_record_for_number_matching`（行為零變化）。"""
    old_fold = SummarizationService._fold_record_for_number_matching

    assert old_fold("15. 辦公室搬遷") == "15.辦公室搬遷", "舊折疊不得被改動（日期路徑共用）"
    covered = SummarizationService._date_canonical_is_covered
    assert covered("11/1", old_fold("預計 11月1日 起實施"))
    assert not covered("11/1", old_fold("11月10日開會")), "日期邊界契約不得退化"
