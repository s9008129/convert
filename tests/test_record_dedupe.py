# -*- coding: utf-8 -*-
"""W5：general 紀錄的跨章節重複抑制（T20260922-1930-01 軌 A）。

釘住的契約（凍結介面）：

* 只比對「決議」節與「主席裁示事項」節：正規化＝去行首編號／項目符號→標點統一
  →去空白→切除行尾「（主辦單位…協辦單位…辦理期程…）」metadata→去標點；
  僅在完全相等、留有實詞、且非標題／佔位欄位時判重。
* 保留 donor（主席裁示事項，metadata 較完整）；決議節的重複條目改寫為
  「（與主席裁示事項重複，詳見該節）」，整節皆重複則寫「無」。
* 沒有「主席裁示事項」節／section_meeting 模板 → 原樣回傳；必須冪等。
* 回歸：去重後 ``_validate_summary_quality`` 的問題數不得增加。

fixture 字面取自 ``data/cache/p1-fixtures/fixtures.py``（該檔已 gitignore，一律內嵌
字面、不得於 runtime 讀檔）。
"""

import os
import tempfile

# 必須在 import backend 之前備妥可寫的 DATA_DIR（logger 匯入時即建立 DATA_DIR/logs）。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-dedupe-"))

from backend.core.templates import get_template  # noqa: E402
from backend.core.text_postprocess import dedupe_cross_section_items  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402

# 來源：fixtures.py FIXTURE_A_RECORD（A 檔行 1–2、110–132 逐字節錄）。
FIXTURE_A_RECORD = """# 會議紀錄

決議：
一、 各相關科室（資管股、系統權限、業務承辦人）需配合系統與權限調整，提前預約準備。（主辦單位：（待確認），協辦單位：無）
二、 依照往年經驗，部分民眾下午一點多才到，需提早出發；針對住處特殊或遠距戶數（約 2 戶）需現場分發。（主辦單位：（待確認），協辦單位：無）
三、 待土地稅科提供清單後，配合重新列印。（主辦單位：（待確認），協辦單位：無）
四、 相關物品需整理歸位，配合現場檢查。（主辦單位：（待確認），協辦單位：無）
五、 形式傾向「辦公室下午茶、點心加拍照、發禮券」；需確認現金發放程序是否麻煩，若麻煩則採禮券；需確定主辦人及具體形式。（主辦單位：（待確認），協辦單位：無）
六、 宣導科內人員注意廉政風險，避免違規。（主辦單位：（待確認），協辦單位：無）
七、 提醒全員設為文字模式，勿亂點不明連結。（主辦單位：（待確認），協辦單位：無）
八、 列入會議記錄警告，若再發現將嚴懲。（主辦單位：（待確認），協辦單位：無）
九、 西龍股需於下次課會議報告創新想法與做法。（主辦單位：（待確認），協辦單位：無）
十、 搬遷時程未定，暫維持現況辦公；需關注健康影響與工程進度。（主辦單位：（待確認），協辦單位：無）

三、 主席裁示事項（後續管考與追蹤）：
一、 各相關科室（資管股、系統權限、業務承辦人）需配合系統與權限調整，提前預約準備。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
二、 依照往年經驗，部分民眾下午一點多才到，需提早出發；針對住處特殊或遠距戶數（約 2 戶）需現場分發。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
三、 待土地稅科提供清單後，配合重新列印。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
四、 相關物品需整理歸位，配合現場檢查。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
五、 形式傾向「辦公室下午茶、點心加拍照、發禮券」；需確認現金發放程序是否麻煩，若麻煩則採禮券；需確定主辦人及具體形式。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
六、 宣導科內人員注意廉政風險，避免違規。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
七、 提醒全員設為文字模式，勿亂點不明連結。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
八、 列入會議記錄警告，若再發現將嚴懲。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
九、 西龍股需於下次課會議報告創新想法與做法。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
十、 搬遷時程未定，暫維持現況辦公；需關注健康影響與工程進度。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））"""

# 來源：fixtures.py FIXTURE_A_DECISIONS（A 檔行 111–120 逐字，決議清單 10 條）。
FIXTURE_A_DECISIONS = """一、 各相關科室（資管股、系統權限、業務承辦人）需配合系統與權限調整，提前預約準備。（主辦單位：（待確認），協辦單位：無）
二、 依照往年經驗，部分民眾下午一點多才到，需提早出發；針對住處特殊或遠距戶數（約 2 戶）需現場分發。（主辦單位：（待確認），協辦單位：無）
三、 待土地稅科提供清單後，配合重新列印。（主辦單位：（待確認），協辦單位：無）
四、 相關物品需整理歸位，配合現場檢查。（主辦單位：（待確認），協辦單位：無）
五、 形式傾向「辦公室下午茶、點心加拍照、發禮券」；需確認現金發放程序是否麻煩，若麻煩則採禮券；需確定主辦人及具體形式。（主辦單位：（待確認），協辦單位：無）
六、 宣導科內人員注意廉政風險，避免違規。（主辦單位：（待確認），協辦單位：無）
七、 提醒全員設為文字模式，勿亂點不明連結。（主辦單位：（待確認），協辦單位：無）
八、 列入會議記錄警告，若再發現將嚴懲。（主辦單位：（待確認），協辦單位：無）
九、 西龍股需於下次課會議報告創新想法與做法。（主辦單位：（待確認），協辦單位：無）
十、 搬遷時程未定，暫維持現況辦公；需關注健康影響與工程進度。（主辦單位：（待確認），協辦單位：無）"""

# 來源：fixtures.py FIXTURE_A_CHAIR_RULINGS（A 檔行 123–132 逐字，主席裁示 10 條）。
FIXTURE_A_CHAIR_RULINGS = """一、 各相關科室（資管股、系統權限、業務承辦人）需配合系統與權限調整，提前預約準備。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
二、 依照往年經驗，部分民眾下午一點多才到，需提早出發；針對住處特殊或遠距戶數（約 2 戶）需現場分發。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
三、 待土地稅科提供清單後，配合重新列印。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
四、 相關物品需整理歸位，配合現場檢查。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
五、 形式傾向「辦公室下午茶、點心加拍照、發禮券」；需確認現金發放程序是否麻煩，若麻煩則採禮券；需確定主辦人及具體形式。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
六、 宣導科內人員注意廉政風險，避免違規。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
七、 提醒全員設為文字模式，勿亂點不明連結。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
八、 列入會議記錄警告，若再發現將嚴懲。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
九、 西龍股需於下次課會議報告創新想法與做法。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
十、 搬遷時程未定，暫維持現況辦公；需關注健康影響與工程進度。（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））"""

# 來源：fixtures.py FIXTURE_B_RECORD（B 檔行 1–2、149–272 逐字節錄；決議節與主席裁示節
# 只有標題與「主辦單位／協辦單位／辦理期程」佔位欄位重疊，內文各自不同）。
FIXTURE_B_RECORD = """# 會議紀錄

決議：
一、 組織規程與編制異動：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：（待確認）

二、 局務會議報告：
（一） 防詐騙宣導：
1、 主辦單位：（待確認）
2、 協辦單位：（待確認）
3、 辦理期程：10 月 14 日

（二） 土地稅卡重新列印：
1、 主辦單位：（待確認）
2、 協辦單位：（待確認）
3、 辦理期程：（待確認）

（三） 內機檢查：
1、 主辦單位：（待確認）
2、 協辦單位：（待確認）
3、 辦理期程：下週一

（四） 文康活動規劃：
1、 主辦單位：（待確認）
2、 協辦單位：（待確認）
3、 辦理期程：（待確認）

三、 廉政宣導：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：（待確認）

四、 選舉期間注意事項：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：（待確認）

五、 社交工程資安宣導：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：立即

六、 辦公室資訊安全與群組管理：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：立即

七、 多元支付與資料庫創新：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：（待確認）

八、 辦公環境搬遷與淹水問題：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：（待確認）

三、 主席裁示事項（後續管考與追蹤）：
一、 組織規程與編制異動：
（一） 裁示內容：相關單位（如資管股）需提前預約準備，配合系統與權限調整。
（二） 主辦單位：（待確認）
（三） 協辦單位：（待確認）
（四） 辦理期程：11 月 1 日前

二、 局務會議報告：
（一） 防詐騙宣導：
1、 裁示內容：需確認發放對象與方式，注意偏遠地區（瑞里、瑞吉）需提早出發，部分高齡者（90 幾歲）需現場分送。
2、 主辦單位：（待確認）
3、 協辦單位：（待確認）
4、 辦理期程：10 月 14 日

（二） 土地稅卡重新列印：
1、 裁示內容：待土地稅科提供清單後，由負責單位配合重新列印。
2、 主辦單位：（待確認）
3、 協辦單位：（待確認）
4、 辦理期程：（待確認）

（三） 內機檢查：
1、 裁示內容：下週一有內機檢查，需注意資料擺放。
2、 主辦單位：（待確認）
3、 協辦單位：（待確認）
4、 辦理期程：下週一

（四） 文康活動規劃：
1、 裁示內容：確定主辦人（輪流或自願）、活動形式（建議辦公室點心+拍照+發禮券，以符合規定且簡便）、現金發放之財務程序（若麻煩則改禮券）、計算文康活動總費用（17 人 x 800 元 = 13,600 元）並規劃點心與禮券分配、考慮工程師（3 人）是否納入文康活動範圍。
2、 主辦單位：（待確認）
3、 協辦單位：（待確認）
4、 辦理期程：（待確認）

三、 廉政宣導：
（一） 裁示內容：嚴禁利用公務時間處理私事（洗車、接小孩等）；採購需公正；注意社交工程資安。
（二） 主辦單位：（待確認）
（三） 協辦單位：（待確認）
（四） 辦理期程：（待確認）

四、 選舉期間注意事項：
（一） 裁示內容：謹慎處理涉及政治議題之業務。
（二） 主辦單位：（待確認）
（三） 協辦單位：（待確認）
（四） 辦理期程：（待確認）

五、 社交工程資安宣導：
（一） 裁示內容：全員務必將 Email 設為文字模式；嚴禁點擊不明連結與檔案。
（二） 主辦單位：（待確認）
（三） 協辦單位：（待確認）
（四） 辦理期程：立即

六、 辦公室資訊安全與群組管理：
（一） 裁示內容：嚴禁將科內照片、訊息外傳至外部群組（含家族群組）。
（二） 主辦單位：（待確認）
（三） 協辦單位：（待確認）
（四） 辦理期程：立即

七、 多元支付與資料庫創新：
（一） 裁示內容：西龍股需提出創新方案，於下次課會議報告。
（二） 主辦單位：（待確認）
（三） 協辦單位：（待確認）
（四） 辦理期程：（待確認）

八、 辦公環境搬遷與淹水問題：
（一） 裁示內容：預期搬遷延後，需做好長期在原處辦公準備；原處辦公環境需改善（舒適度、設備）；關注新辦公室除黴工程進度（可能影響預算與時程）。
（二） 主辦單位：（待確認）
（三） 協辦單位：（待確認）
（四） 辦理期程：（待確認）"""

DONOR_HEADING = "三、 主席裁示事項（後續管考與追蹤）："


class TestFixtureRecords:
    def test_FIXTURE_A移除10條(self):
        """fixtures 硬性期望值：決議節 10 條與主席裁示節逐條重複 → 移除 10 條。"""
        cleaned, removed = dedupe_cross_section_items(
            FIXTURE_A_RECORD, get_template("general")
        )
        assert removed == 10

    def test_FIXTURE_A整節皆重複寫無且保留donor(self):
        cleaned, removed = dedupe_cross_section_items(
            FIXTURE_A_RECORD, get_template("general")
        )
        assert removed == 10
        assert cleaned.startswith("# 會議紀錄\n\n決議：\n無\n\n")
        # donor（主席裁示事項，metadata 較完整）逐字保留，含「辦理期程」。
        assert cleaned[cleaned.index(DONOR_HEADING):] == FIXTURE_A_RECORD[
            FIXTURE_A_RECORD.index(DONOR_HEADING):
        ]
        assert cleaned.count("各相關科室") == 1
        assert "（與主席裁示事項重複，詳見該節）" not in cleaned

    def test_FIXTURE_A冪等(self):
        cleaned, removed = dedupe_cross_section_items(
            FIXTURE_A_RECORD, get_template("general")
        )
        assert removed == 10
        assert dedupe_cross_section_items(cleaned, get_template("general")) == (cleaned, 0)

    def test_FIXTURE_B移除0條且原樣回傳(self):
        """fixtures 硬性期望值：B 檔只剩標題與佔位欄位重疊 → 0 條。"""
        cleaned, removed = dedupe_cross_section_items(
            FIXTURE_B_RECORD, get_template("general")
        )
        assert removed == 0
        assert cleaned == FIXTURE_B_RECORD

    def test_決議節與主席裁示節逐條相等時全數移除(self):
        """以 FIXTURE_A_DECISIONS／FIXTURE_A_CHAIR_RULINGS 兩份清單直接組成紀錄。"""
        text = (
            f"# 會議紀錄\n\n決議：\n{FIXTURE_A_DECISIONS}\n\n"
            f"{DONOR_HEADING}\n{FIXTURE_A_CHAIR_RULINGS}"
        )
        cleaned, removed = dedupe_cross_section_items(text, get_template("general"))
        assert removed == 10
        assert "決議：\n無\n" in cleaned
        assert cleaned[cleaned.index(DONOR_HEADING):] == text[text.index(DONOR_HEADING):]

    def test_template省略時走general行為(self):
        assert dedupe_cross_section_items(FIXTURE_A_RECORD) == (
            dedupe_cross_section_items(FIXTURE_A_RECORD, get_template("general"))
        )


class TestDedupeBoundaries:
    def test_部分重複改寫指向文字(self):
        text = """# 會議紀錄

決議：
一、 甲案需於本週完成（主辦單位：（待確認），協辦單位：無）
二、 乙案為決議節獨有內容（主辦單位：（待確認），協辦單位：無）
三、 丙案需於下週完成（主辦單位：（待確認），協辦單位：無）

三、 主席裁示事項（後續管考與追蹤）：
一、 甲案需於本週完成（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））
二、 丙案需於下週完成（主辦單位：（待確認），協辦單位：無，辦理期程：（待確認））"""
        cleaned, removed = dedupe_cross_section_items(text, get_template("general"))
        assert removed == 2
        assert cleaned.count("（與主席裁示事項重複，詳見該節）") == 2
        assert "二、 乙案為決議節獨有內容" in cleaned
        assert "（與主席裁示事項重複，詳見該節）" in cleaned
        assert dedupe_cross_section_items(cleaned, get_template("general")) == (cleaned, 0)

    def test_佔位欄位不算重複(self):
        text = """決議：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：下週一

三、 主席裁示事項（後續管考與追蹤）：
（一） 主辦單位：（待確認）
（二） 協辦單位：（待確認）
（三） 辦理期程：下週一"""
        assert dedupe_cross_section_items(text, get_template("general")) == (text, 0)

    def test_標題行不算重複(self):
        text = """決議：
一、 組織規程與編制異動：

三、 主席裁示事項（後續管考與追蹤）：
一、 組織規程與編制異動："""
        assert dedupe_cross_section_items(text, get_template("general")) == (text, 0)

    def test_沒有主席裁示節即不動(self):
        text = "決議：\n一、 甲案（主辦單位：（待確認），協辦單位：無）\n"
        assert dedupe_cross_section_items(text, get_template("general")) == (text, 0)
        assert dedupe_cross_section_items("", get_template("general")) == ("", 0)

    def test_section_meeting模板防禦性停用(self):
        """科務會議沒有「決議 vs 主席裁示」章節對（該重複只出現在 general）。"""
        assert dedupe_cross_section_items(
            FIXTURE_A_RECORD, get_template("section_meeting")
        ) == (FIXTURE_A_RECORD, 0)

    def test_非general模板一律不處理(self):
        """作用域依 plan §3 W5 限縮為 general-only（2026-09-22 稽核修正）。

        isms_monthly／procurement_evaluation 等模板即使文字含「主席裁示事項」
        也不得被改寫。
        """
        for template_id in ("isms_monthly", "procurement_evaluation"):
            template = get_template(template_id)
            assert template.id == template_id
            assert dedupe_cross_section_items(FIXTURE_A_RECORD, template) == (
                FIXTURE_A_RECORD,
                0,
            )
    def test_去重後驗證問題不增加(self):
        """回歸：dedupe 只刪重複，不得讓 _validate_summary_quality 的問題變多。"""
        service = SummarizationService()
        template = get_template("general")
        before = service._validate_summary_quality(FIXTURE_A_RECORD, "", template=template)
        cleaned, removed = dedupe_cross_section_items(FIXTURE_A_RECORD, template)
        after = service._validate_summary_quality(cleaned, "", template=template)
        assert removed == 10
        assert len(after) <= len(before)
