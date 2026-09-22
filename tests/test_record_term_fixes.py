# -*- coding: utf-8 -*-
"""W3：section_meeting 紀錄級確定性詞彙修正（T20260922-1930-01 軌 A）。

釘住的契約（凍結介面，軌 B／C 依此呼叫，名稱不得改）：

* ``SECTION_MEETING_RECORD_TERM_FIXES``：恰 4 條 ``(regex, 取代字串)``，只作用於
  地端最終紀錄；與注入逐字稿校正層（雲端共用）的
  ``SECTION_MEETING_GLOSSARY_CORRECTIONS`` 嚴格分離。
* ``MeetingTemplate.record_term_fixes``：只有 section_meeting 帶規則，其餘模板
  維持空 tuple（預設值 ⇒ 行為不變）。
* ``apply_record_term_fixes``：形狀同 ``apply_official_term_fixes``，
  只回報「實際命中」的規則。

fixture 字面取自 ``data/cache/p1-fixtures/fixtures.py``（該檔已 gitignore，一律內嵌
字面、不得於 runtime 讀檔）；另兩條單行真實語料於常數上方標註來源檔案。
"""

import os
import tempfile

# 必須在 import backend 之前備妥可寫的 DATA_DIR：loguru 於 backend.core.logger
# 匯入時就會建立 DATA_DIR/logs（預設 /app/data 在此環境不可寫）。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-record-terms-"))

import pytest  # noqa: E402

from backend.core.prompt_templates.section_meeting import (  # noqa: E402
    SECTION_MEETING_GLOSSARY_CORRECTIONS,
    SECTION_MEETING_RECORD_TERM_FIXES,
)
from backend.core.templates import get_template, list_templates  # noqa: E402
from backend.core.text_postprocess import apply_record_term_fixes  # noqa: E402

# 來源：fixtures.py FIXTURE_TERM_ERROR_LINES（C 檔行 23–25 逐字，含標籤行）。
FIXTURE_TERM_ERROR_LINES = """# C 檔 data/outputs/0903-科務會議_836fcae7.md:23（命中：煙酒為神穀、潛水管理股）
2.煙酒管理科改名為「煙酒及稅務管理科」，併入法務科，股別改為「煙酒為神穀」與「欠稅管理股」（原潛水管理股改為欠稅管理股，承辦人美聯）。
# C 檔 data/outputs/0903-科務會議_836fcae7.md:24（命中：雞查股、增收股）
3.房屋稅房務稅科股名改為「雞查股」與「增收股」（原一股、二股）。
# C 檔 data/outputs/0903-科務會議_836fcae7.md:25（命中：科原）
4.編製表調整：缺位改為「電子作業管理師」，人事室書記改為「科原」，委任比例由40%降至25%，第一線改為稅務員（透過甄選評分，非原地升）。
# D 檔 data/outputs/0903-科務會議_b20c90a7.md：上列 8 詞全部 0 命中，無行可列"""

# 來源：fixtures.py FIXTURE_TRANSCRIPT_ASR_ERROR_LINES（逐字稿行 15、155 逐字）。
FIXTURE_TRANSCRIPT_ASR_ERROR_LINES = """[00:06:14-00:06:48] 發言者1：多宣導單然發給人家啦，我覺得那段你要再再去那個我覺得你的本那種時間他現在我們是抽到瑞裏嘛對不對啊戶數還不確定戶數就 100多啊總總共 100多嘛他扣掉那個轉賬的還不曉得現金領的不小心他不知道對了嘛啊你們是排 10 月 14嘛好好 OK 好。
[00:27:03-00:29:10] 發言者1：然後最近那個我們課內我們局內的那個社料工程哦，我跟你講那個題目真的很逼真哦，我不要亂點。事情的告訴我對三個中鞦節你想哦人事總數總會記憶mail給你，他怎麼會有你 email啊這裏看就知道是假的這個一看就是有問題的啊啊真的很多人點哦那你點的沒有關係係你重點你一定要設存文字模式你設存文字模式你點進去係統上麵不會知道你點這就是為什麼衛順去幫大家設存文字模式你設除文字模式的時候你點進去係統不會知道你打開那個信的像我們剛剛那個鏡頭去看一下因為很多人都點了真的很多人超多的看到那一封 91號早上中午的時候我看到那封信我知道很多人會點我就知道了因為當初給我們那五個我我那幾個那個那個那個題目其實應該是 AI想出來的題目說很真但是我跟你講社交工程真正社交工程人家駭客要打你的題目一定是逼真的不會是做那種你看都是假的啦所以這個部分就是就自己不要亂點哦你一定要設重文字模式啊你真的不小心點進去的好超廉潔就不要再點了檔案物價檔案就不要再點了就是有人真的會再點這要註意一下哦好這是社交工程好那再來就是我這邊要再重申一下上次上次我跟大家講到說我們那個辦公室的部分啊。辦公室的那個那張照片哦目前還在留在火幣上麵一直沒有砍掉讓我相信啊你們可能自己本身當初傳出去的人傳到哪邊去你可能自己也不知道了你可能是傳到你家族的群主家族群主要再傳出去所以那一個人把他上網丟進去的你可能也不曉得是誰所以那一封那一個留言一直還在上麵不管。這樣"""

# 來源：fixtures.py FIXTURE_TRANSCRIPT_ASR_EXPECTED_FIXED；注意它是以「未錨定」的
# 規則集程式產生（雞查股→稽查股、增收股→徵收股、人事總數→人事總處、瑞裏→瑞里），
# 本波凍結規則刻意較窄（人事總數需 Email／郵件／寄語境），差異由測試釘住。
FIXTURE_TRANSCRIPT_ASR_EXPECTED_FIXED = """[00:06:14-00:06:48] 發言者1：多宣導單然發給人家啦，我覺得那段你要再再去那個我覺得你的本那種時間他現在我們是抽到瑞里嘛對不對啊戶數還不確定戶數就 100多啊總總共 100多嘛他扣掉那個轉賬的還不曉得現金領的不小心他不知道對了嘛啊你們是排 10 月 14嘛好好 OK 好。
[00:27:03-00:29:10] 發言者1：然後最近那個我們課內我們局內的那個社料工程哦，我跟你講那個題目真的很逼真哦，我不要亂點。事情的告訴我對三個中鞦節你想哦人事總處總會記憶mail給你，他怎麼會有你 email啊這裏看就知道是假的這個一看就是有問題的啊啊真的很多人點哦那你點的沒有關係係你重點你一定要設存文字模式你設存文字模式你點進去係統上麵不會知道你點這就是為什麼衛順去幫大家設存文字模式你設除文字模式的時候你點進去係統不會知道你打開那個信的像我們剛剛那個鏡頭去看一下因為很多人都點了真的很多人超多的看到那一封 91號早上中午的時候我看到那封信我知道很多人會點我就知道了因為當初給我們那五個我我那幾個那個那個那個題目其實應該是 AI想出來的題目說很真但是我跟你講社交工程真正社交工程人家駭客要打你的題目一定是逼真的不會是做那種你看都是假的啦所以這個部分就是就自己不要亂點哦你一定要設重文字模式啊你真的不小心點進去的好超廉潔就不要再點了檔案物價檔案就不要再點了就是有人真的會再點這要註意一下哦好這是社交工程好那再來就是我這邊要再重申一下上次上次我跟大家講到說我們那個辦公室的部分啊。辦公室的那個那張照片哦目前還在留在火幣上麵一直沒有砍掉讓我相信啊你們可能自己本身當初傳出去的人傳到哪邊去你可能自己也不知道了你可能是傳到你家族的群主家族群主要再傳出去所以那一個人把他上網丟進去的你可能也不曉得是誰所以那一封那一個留言一直還在上麵不管。這樣"""

# 來源：data/outputs/0903-科務會議_b20c90a7.md:46（真實地端紀錄逐字；
# zh-TW 應為「徵收股」，屬簡體用字誤辨）。
REAL_LINE_SIMPLIFIED_ZHENG_CHARGE = "5. 房屋稅科股別改名：原一股改為「稽查股」，原二股改為「征收股」。"


class TestRecordTermFixRules:
    def test_恰為四條凍結規則(self):
        """名稱／順序／字面即介面：軌 B／C 直接匯入這 4 條。"""
        assert SECTION_MEETING_RECORD_TERM_FIXES == (
            (r"征收股", "徵收股"),
            (r"增收股", "徵收股"),
            (r"人事總數(?=\s*(?:Email|E-mail|電子郵件|郵件|寄|偽造|釣魚))", "人事總處"),
            (r"瑞裏", "瑞里"),
        )

    def test_與逐字稿校正層嚴格分離(self):
        """本波不得改動 SECTION_MEETING_GLOSSARY_CORRECTIONS（逐字稿層，雲端共用）。"""
        assert SECTION_MEETING_GLOSSARY_CORRECTIONS == (
            ("課務會議", "科務會議"),
            ("列冠", "列管"),
            ("裂管", "列管"),
            ("揭除列管", "解除列管"),
            ("會整表", "彙整表"),
            ("成辦", "承辦"),
            ("成核", "陳核"),
            ("前辦", "簽辦"),
        )
        record_patterns = {pattern for pattern, _ in SECTION_MEETING_RECORD_TERM_FIXES}
        glossary_sources = {source for source, _ in SECTION_MEETING_GLOSSARY_CORRECTIONS}
        assert record_patterns.isdisjoint(glossary_sources)

    def test_征收股修正_真實紀錄行(self):
        fixed, changes = apply_record_term_fixes(
            REAL_LINE_SIMPLIFIED_ZHENG_CHARGE, SECTION_MEETING_RECORD_TERM_FIXES
        )
        assert changes == [(r"征收股", "徵收股")]
        assert fixed == "5. 房屋稅科股別改名：原一股改為「稽查股」，原二股改為「徵收股」。"
        # 本波明確不放寬：未經確證的「稽查股」等替換不得順帶寫入。
        assert "稽查股" in fixed

    def test_增收股修正_取自C檔真實語料(self):
        fixed, changes = apply_record_term_fixes(
            FIXTURE_TERM_ERROR_LINES, SECTION_MEETING_RECORD_TERM_FIXES
        )
        assert changes == [(r"增收股", "徵收股")]
        assert "「雞查股」與「徵收股」" in fixed
        # 未確證詞（煙酒為神穀／潛水管理股／科原）一律不動。
        assert "煙酒為神穀" in fixed
        assert "潛水管理股" in fixed
        assert "科原" in fixed

    def test_人事總數語境錨定_正向命中(self):
        fixed, changes = apply_record_term_fixes(
            "人事總數寄 Email 通知各股，請勿點閱。", SECTION_MEETING_RECORD_TERM_FIXES
        )
        assert changes == [
            (r"人事總數(?=\s*(?:Email|E-mail|電子郵件|郵件|寄|偽造|釣魚))", "人事總處")
        ]
        assert fixed == "人事總處寄 Email 通知各股，請勿點閱。"

    def test_人事總數負案例_不得誤改總員額(self):
        text = "本局人事總數為 45 人，另人事總數（待確認）。"
        fixed, changes = apply_record_term_fixes(text, SECTION_MEETING_RECORD_TERM_FIXES)
        assert changes == []
        assert fixed == text

    def test_逐字稿真實ASR行_只修可確證規則(self):
        fixed, changes = apply_record_term_fixes(
            FIXTURE_TRANSCRIPT_ASR_ERROR_LINES, SECTION_MEETING_RECORD_TERM_FIXES
        )
        assert changes == [(r"瑞裏", "瑞里")]
        assert "瑞里" in fixed and "瑞裏" not in fixed
        # fixtures 的 EXPECTED_FIXED 由未錨定規則集產生（人事總數→人事總處不加語境）；
        # 本波凍結規則保留語境錨定，逐字差異僅「人事總數總會記憶mail」這一處
        # （其後沒有 Email／郵件／寄／偽造／釣魚），故以該字面釘住差異。
        assert fixed == FIXTURE_TRANSCRIPT_ASR_EXPECTED_FIXED.replace(
            "人事總處總會記憶mail", "人事總數總會記憶mail"
        )

    def test_未命中與空輸入不回報規則(self):
        text = "完全正常的會議紀錄內容。"
        assert apply_record_term_fixes(text, SECTION_MEETING_RECORD_TERM_FIXES) == (text, [])
        assert apply_record_term_fixes("", SECTION_MEETING_RECORD_TERM_FIXES) == ("", [])
        assert apply_record_term_fixes("瑞裏", ()) == ("瑞裏", [])


class TestTemplateWiring:
    def test_section_meeting帶入四條規則(self):
        assert (
            get_template("section_meeting").record_term_fixes
            == SECTION_MEETING_RECORD_TERM_FIXES
        )

    @pytest.mark.parametrize(
        "template_id", ["general", "procurement_evaluation", "isms_monthly"]
    )
    def test_其他模板維持空tuple(self, template_id):
        assert get_template(template_id).record_term_fixes == ()

    def test_所有模板欄位型別一致(self):
        for template in list_templates():
            assert isinstance(template.record_term_fixes, tuple)
            if template.id != "section_meeting":
                assert template.record_term_fixes == ()
