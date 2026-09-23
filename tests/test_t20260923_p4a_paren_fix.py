# -*- coding: utf-8 -*-
"""P4-A 收尾修補（T20260922-2037-02；E3 真實音檔實證）：括號複合詞組的子詞全數命中。

背景（E3 場 app log 10:27–10:37，連續三輪同一條）：議題
「廉政宣導（拆勤、採購、公務車使用）」被逐條對帳判缺，但 E3 最終紀錄其實已寫
「廉政宣導」「拆勤」「採購」與「公務車」——補強輪因此白燒、不收斂。
根因＝議題詞級覆蓋的可達性 DP 卡在標題內的分隔符 `、`：`_normalize_action_key`
剝除多數標點，但頓號不在剝除字元集內，也不是停用詞 → DP 過不去、`reachable`
永遠到不了終點 → 整條判缺（離線重播可 0 成本重現）。

本檔釘住四件事：
  T-34  正向：分隔符可略過；`公務車使用` 由 DP 拆成自身子詞「公務車」＋「使用」，
              兩者皆命中（順序不限、可跨段落）→ 接受，不得再判缺。
  T-34b 反向：子詞真的缺（紀錄沒有「公務車」）→ 仍判缺。
  T-34c 反向：只命中部分子詞（有「公務車」、無「使用」）→ 仍判缺；本規則不得
              變成「任一子詞命中就放行」。
  T-34d 反向：E3 真缺的議題（內稽／淹水／Kiosk 跨縣市）自帶分隔符也照樣判缺；
              否定詞／數字兩道守衛不受影響。
純函式／payload 級，不依賴 LM Studio／Ollama／網路。
"""

import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-t20260923-p4a-paren-"))

from backend.services.summarization import SummarizationService  # noqa: E402


# --- 正向 fixture：E3 最終紀錄（0903-科務會議_d48ce298.md）第 40 行的縮樣節錄 ---
# 「使用」僅出現在「使用牌照稅科」一詞（與 E3 紀錄實況相同：全檔 `使用` 只 1 次）。
PAREN_RECORD = (
    "7. 廉政宣導：拆勤時間管理（會議提早結束後的時間屬性）、加班時不要在辦公室外亂跑"
    "（買便當除外）、禁止用公務車洗車或接小孩；小採購需小心，避免與廠商交換利益，"
    "不收廠商飲料；拆勤費用需照時報，不要浮報（發言者1，00:19:49）。\n"
    "2. 土地稅科拆分為「地價稅科」與「土地增值稅科」；校費稅科改名為「使用牌照稅科」"
    "（發言者1，00:00:00）。\n"
)
PAREN_NOTES = "## 2. 議題與決議\n- **議題**：廉政宣導（拆勤、採購、公務車使用）\n"
PAREN_LABEL = "廉政宣導（拆勤、採購、公務車使用）"


def test_T34_括號複合標題_分隔符可略過且子詞全數命中即接受():
    """E3 殘餘假陽性：詞都在紀錄中（不限順序／段落）就不得判缺。"""
    normalize = SummarizationService._normalize_action_key
    haystack = normalize(PAREN_RECORD)
    assert "、" in normalize(PAREN_LABEL), "前提：分隔符會存活到正規化後的 key（本測試才釘得住）"

    service = SummarizationService()
    # 前提檢查：主（LCS）規則單獨判定為缺——本測試釘的是第二條接受規則。
    missing, _ratios = service._find_missing_action_keys(
        {normalize(PAREN_LABEL)}, haystack
    )
    assert missing, "前提：主 LCS 規則單獨會判缺，否則本測試無法證明詞級覆蓋生效"
    assert SummarizationService._topic_terms_cover(normalize(PAREN_LABEL), haystack)

    issues = service._validate_record_source_coverage(PAREN_RECORD, PAREN_NOTES, "")
    assert not [issue for issue in issues if issue.startswith("議題遺漏")], (
        "括號內複合詞組的子詞都在紀錄中，不得再判缺："
        f"{service._record_coverage_stats}"
    )
    assert service._record_coverage_stats["expected_topic"] == 1
    assert service._record_coverage_stats["missing_topic"] == 0


def test_T34b_分隔符略過後_子詞真的缺仍判缺():
    """紀錄沒有「公務車」→ 複合詞組「公務車使用」切不出來，不得放行。"""
    normalize = SummarizationService._normalize_action_key
    record = PAREN_RECORD.replace("禁止用公務車洗車或接小孩", "禁止用交通車洗車或接小孩")
    assert "公務車" not in record and "公務" not in record

    assert not SummarizationService._topic_terms_cover(normalize(PAREN_LABEL), normalize(record))

    service = SummarizationService()
    issues = service._validate_record_source_coverage(record, PAREN_NOTES, "")
    assert service._record_coverage_stats["missing_topic"] == 1, (
        f"缺子詞必須維持判缺：{service._record_coverage_stats}"
    )
    assert [issue for issue in issues if issue.startswith("議題遺漏")], issues


def test_T34c_分隔符略過後_只命中部分子詞仍判缺():
    """有「公務車」、無「使用」→ 子詞未全數命中，不得放行（非「任一命中即通過」）。"""
    normalize = SummarizationService._normalize_action_key
    record = PAREN_RECORD.replace("使用牌照稅科", "牌照稅科")
    assert "使用" not in record

    assert not SummarizationService._topic_terms_cover(normalize(PAREN_LABEL), normalize(record))

    service = SummarizationService()
    service._validate_record_source_coverage(record, PAREN_NOTES, "")
    assert service._record_coverage_stats["missing_topic"] == 1, (
        f"部分子詞命中不得放行：{service._record_coverage_stats}"
    )


# --- 反向 fixture：E3 真缺的議題（語意真缺口；見 coverage.json missing_core F021/F055/F056/F051）---
GAP_RECORD = (
    "7. 廉政宣導：拆勤時間管理、加班時不要在辦公室外亂跑、禁止用公務車洗車或接小孩"
    "（發言者1，00:19:49）。\n"
)
GAP_NOTES = (
    "## 2. 議題與決議\n"
    "- **議題**：內稽檢查（下週一下午受檢）\n"
    "- **議題**：淹水處理（防水層刨除、排水管破損）\n"
    "- **議題**：Kiosk（跨縣市多元服務效益）\n"
)


def test_T34d_真缺議題帶分隔符也照樣判缺():
    """分隔符可略過 ≠ 放行：三個 E3 真缺口（自帶 `、`）仍必須逐項判缺。"""
    service = SummarizationService()
    issues = service._validate_record_source_coverage(GAP_RECORD, GAP_NOTES, "")
    assert service._record_coverage_stats["expected_topic"] == 3
    assert service._record_coverage_stats["missing_topic"] == 3, (
        f"真缺口不得被分隔符規則洗白：{service._record_coverage_stats}"
    )
    topic_issue = [issue for issue in issues if issue.startswith("議題遺漏")]
    assert topic_issue and "內稽" in topic_issue[0] and "淹水" in topic_issue[0]


def test_T34e_否定詞與數字守衛不受分隔符規則影響():
    """子詞規則只新增「可略過的分隔符」；兩道守衛方向不變（缺仍判缺）。"""
    cover = SummarizationService._topic_terms_cover
    assert not cover("廉政宣導、嚴禁浮報", "廉政宣導、浮報")
    assert not cover("拆勤、13600", "拆勤")

