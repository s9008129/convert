# -*- coding: utf-8 -*-
"""P4-A 逐條對帳剩餘假陽性修補（T20260922-2037-02；E2 真實音檔實證）。

背景（E2 場 app log 09:56:57＋最終紀錄人工核對）：議題／決議明明已寫進紀錄，
比對器仍判缺 → 補強輪空轉、不收斂。本檔逐一釘住三類可證明的假陽性：

  T-30 議題：標題被改寫／重排（詞都在、順序或段落不同）→ 詞級覆蓋接受
  T-31 決議：條目含 `；`／多句 `。`（紀錄分兩句寫）→ 子句 AND 判定
  T-32 數字守衛：標籤 `10/14`／`11/1` 被折疊串成 `1014`／`111` 的假陽性 →
       日期正規化（雙方同一條規則）後，數字群組各自出現即算命中
  T-33 負向對照（必須一律維持）：真的沒寫進紀錄的議題／子句／數字仍判缺；
       詞級覆蓋不得變成「必涵蓋」（切不出詞 → 回原 LCS 規則）

全部純函式／payload 級，不依賴 LM Studio／Ollama／網路。
"""

import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-t20260923-p4a-fp-"))

from backend.services.summarization import SummarizationService  # noqa: E402


# --- T-30 議題：E2 最終紀錄的「縮樣」節錄（逐字取自 0903-科務會議_7bf495fe.md）---
TOPIC_RECORD = (
    "| 整理並重新列印損毀之土地稅卡（本科/相關承辦） | （待確認）： | | |\n"
    "（二）資安與紀律：\n"
    "1. 近期有逼真之社交工程釣魚郵件，要求所有人員將電子郵件設定為"
    "「純文字模式」，避免點擊超連結或附件（科長，00:27:03）。\n"
    "2. 土地稅科倉庫因颱風漏水導致部分土地卡損毀，待其整理出清單後，"
    "由本科配合重新列印（科長，00:08:15）。\n"
    "3. 瑞理村發放活動確認於 10月14日排程……同意以發放宣導單替代"
    "（科長，00:05:45）。\n"
)

TOPIC_NOTES = (
    "## 2. 議題與決議\n"
    "- **議題**：土地稅卡重新列印\n"
    "- **議題**：資安宣導（社交工程）\n"
)


def test_T30_議題詞級覆蓋_改寫與重排仍視為已涵蓋():
    """整串 LCS 判缺（「土地稅卡重新列印」詞序被調換；「資安宣導（社交工程）」
    兩詞分落不同段落），但詞都在紀錄中 → 第二條接受規則必須接受。"""
    service = SummarizationService()
    issues = service._validate_record_source_coverage(TOPIC_RECORD, TOPIC_NOTES, "")

    assert not [issue for issue in issues if issue.startswith("議題遺漏")], (
        "詞都在紀錄中（不限順序／段落）就不得判缺："
        f"{service._record_coverage_stats}"
    )
    assert service._record_coverage_stats["expected_topic"] == 2
    assert service._record_coverage_stats["missing_topic"] == 0

    normalize = SummarizationService._normalize_action_key
    haystack = normalize(TOPIC_RECORD)
    assert SummarizationService._topic_terms_cover(normalize("土地稅卡重新列印"), haystack)
    assert SummarizationService._topic_terms_cover(normalize("資安宣導（社交工程）"), haystack)


def test_T30b_詞級覆蓋_切不出詞時不得變成必涵蓋():
    """標題與紀錄完全無關（連 2 字詞都切不出）→ 回 False；覆蓋率路徑照樣判缺。"""
    assert not SummarizationService._topic_terms_cover("疫苗接種與快篩安排", "本次會議討論文康活動。")

    service = SummarizationService()
    notes = "## 2. 議題與決議\n- **議題**：疫苗接種與快篩安排\n"
    service._validate_record_source_coverage("一、文康活動：發禮券（科長，00:11:52）。", notes, "")
    assert service._record_coverage_stats["missing_topic"] == 1, "切不出詞必須回原 LCS 規則判缺"


# --- T-31 決議：複合句（`；`）在紀錄中被寫成兩句／兩個段落 ---------------

CLAUSE_RECORD_BOTH = (
    "（四）廉政與公務紀律（局長指示）：\n"
    "1. 關於出差（拆勤）時間管理，費用報支應照實報，不可浮報（科長，00:19:06）。\n"
    "2. 小額採購需避免與廠商利益交換，嚴禁收受廠商贈品（科長，00:17:47）。\n"
)
CLAUSE_NOTES = "## 2. 議題與決議\n- *決議*：費用報支應照實報，不可浮報；小額採購需避免與廠商利益交換。\n"


def test_T31_複合決議_子句分寫兩個段落仍視為已涵蓋():
    service = SummarizationService()
    issues = service._validate_record_source_coverage(CLAUSE_RECORD_BOTH, CLAUSE_NOTES, "")

    assert not [issue for issue in issues if issue.startswith("決議遺漏")], (
        f"兩個子句都已寫進紀錄（不同段落）就不得判缺：{service._record_coverage_stats}"
    )
    assert service._record_coverage_stats["missing_decision"] == 0


def test_T31b_子句AND_缺任一句仍判缺():
    """AND 是**加嚴**：只寫了第一句、第二句沒寫 → 仍必須判缺。"""
    record = "1. 關於出差（拆勤）時間管理，費用報支應照實報，不可浮報（科長，00:19:06）。\n"
    service = SummarizationService()
    issues = service._validate_record_source_coverage(record, CLAUSE_NOTES, "")

    assert [issue for issue in issues if issue.startswith("決議遺漏")], "缺一子句不得洗白"
    assert service._record_coverage_stats["missing_decision"] == 1


# --- T-32 數字守衛：斜線日期折疊後的假陽性 --------------------------------

DATE_NOTES = "## 2. 議題與決議\n- *決議*：將先公告預佈缺，避免 11/1 才找人過晚。\n"


def test_T32_斜線日期_正規化雙方同一條規則_數字群組各自出現即命中():
    normalize = SummarizationService._normalize_action_key
    assert normalize("確認 10/14 排程") == normalize("確認 10月14日排程"), (
        "同一個日期在兩側必須折疊成同一條正規化（M/D → M月D日）"
    )

    record = "科內缺位改為「電子作業管理師」，將先公告預佈缺，避免 11月1日才找人過晚（科長，00:00:00）。\n"
    service = SummarizationService()
    issues = service._validate_record_source_coverage(record, DATE_NOTES, "")

    assert not [issue for issue in issues if issue.startswith("決議遺漏")], (
        "紀錄寫「11月1日」、標籤寫「11/1」是同一件事，不得判缺"
        f"（舊版會因要求字面命中『111』而誤判）：{service._record_coverage_stats}"
    )
    assert service._record_coverage_stats["missing_decision"] == 0


def test_T32b_日期數字守衛_真的寫錯日仍判缺():
    """守衛本意不變：紀錄把 11/1 寫成 11月2日、10/14 寫成 10月15日 → 判缺。"""
    record = "將先公告預佈缺，避免 11月2日才找人過晚（科長，00:00:00）。\n"
    missing, ratios = SummarizationService._find_missing_action_keys(
        {SummarizationService._normalize_action_key("將先公告預佈缺，避免 11/1 才找人過晚。")},
        SummarizationService._normalize_action_key(record),
        local_sentences=SummarizationService._split_record_sentences(record),
    )
    assert len(missing) == 1, f"寫錯日期仍要判缺：{ratios}"

    date_notes = "## 2. 議題與決議\n- *決議*：確認 10/14 排程，預計發放人數 100 多戶。\n"
    service = SummarizationService()
    service._validate_record_source_coverage(
        "瑞理村發放活動確認於 10月15日排程，預計發放人數 100 多戶（科長，00:05:45）。",
        date_notes,
        "",
    )
    assert service._record_coverage_stats["missing_decision"] == 1, "10/14 寫成 10月15日必須判缺"


# --- T-33 負向對照：真缺口（D1 場型）仍一律判缺 ---------------------------

D1_LIKE_TRANSCRIPT = (
    "[00:10:00-00:10:20] 甲：一個人 800 塊嘛，那 17 個人。\n"
    "[00:15:00-00:15:20] 乙：有 17 個人所以 13600。\n"
    "[00:10:00-00:10:20] 丙：發禮券 600 元。\n"
)


def test_T33_負向對照_紀錄真的缺的議題與數字仍判缺():
    notes = (
        "## 2. 議題與決議\n"
        "- **議題**：疫苗接種與快篩安排\n"
        "- *決議*：清查公務車輛油耗與維修紀錄。\n"
    )
    record = (
        "一、文康活動：發禮券（科長，00:11:52）。\n"
        "二、土地稅科倉庫因颱風漏水導致部分土地卡損毀，配合重新列印（科長，00:08:15）。\n"
    )
    service = SummarizationService()
    issues = service._validate_record_source_coverage(record, notes, D1_LIKE_TRANSCRIPT)
    stats = service._record_coverage_stats

    assert stats["missing_topic"] == 1, f"無關議題不得被詞級規則洗白：{stats}"
    assert stats["missing_decision"] == 1, f"無關決議必須判缺：{stats}"
    assert stats["missing_number"] >= 3, f"600／17／13600 沒寫進紀錄必須判缺：{stats}"
    assert [issue for issue in issues if issue.startswith("數字遺漏")], "數字問題必須進補強清單"
