#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""真 helper 缺席情境的端到端語意驗證（WAVE-05b；SI-02／SI-03）。

本檔只測「真 helper 缺席」下的引擎鏈語意，且缺席**不是** fake script 冒充的錯誤：
``apple_cli.resolve_executable`` 本體不被 monkeypatch，三階搜尋（設定路徑 → repo
release 產物 → PATH）落空後由真函式丟出 ``APPLE_UNAVAILABLE``。

缺習條件（全部由真實條件構成）：

- 設定路徑不存在：``settings.APPLE_SPEECH_CLI_PATH`` 指向 tmp 內不存在路徑。
- repo release 產物缺席：``apple_cli.REPO_ROOT`` 指到空 tmp（實機可能已
  ``swift build`` 出 ``apple_speech_cli/.build/release/apple-speech-cli``，若不移出
  就會真的找到 helper 並 spawn 它；此注入縫與 ``resolve_executable(repo_root=...)``
  關鍵字同義）。
- PATH 內無 ``apple-speech-cli``：``PATH`` 指到空 tmp 目錄，真 ``shutil.which``
  真的找不到（見 ``test_real_helper_absence_is_natural_not_faked``）。

覆蓋的四條紅線：

1. REAL-ABSENT-01：顯式 ``apple`` ＋ 真 helper 缺席 → ``APPLE_UNAVAILABLE`` 直接
   向上拋（鏈長 1），錯誤訊息含「未 fallback」與精確建置指令；legacy 引擎路徑
   （``_transcribe_with_legacy_engine``／``_load_model``）以計數器證明未被呼叫。
2. REAL-ABSENT-02：Mac ``auto`` 鏈為 ``("apple", "mlx_whisper")``；真 helper 缺席
   （``APPLE_UNAVAILABLE``）允許換手 → fallback 到 mlx_whisper，最終結果來自 mlx
   分支（legacy 引擎以可控 fake 回傳已知 ``DetailedTranscriptionResult``），
   metadata 欄位符合現行 ``transcription.py`` 實作。
3. REAL-ABSENT-03：``APPLE_CANCELLED``（helper 離場碼 7）在 ``auto`` 下亦不 fallback。
   真 helper 缺席只會產生 ``APPLE_UNAVAILABLE``，離場碼 7 只能由真實子行程產生，
   故本案例是**注入式**：argv 導向真子行程（python 以 7 結束），``run_helper``
   與 ``error_from_helper_result`` 都是真的 → 真離場碼 7 → 真分類表 → 取消不換手。
4. REAL-ABSENT-04：缺席條件本身是自然構成的（真 ``shutil.which`` 找不到、
   resolver 未被替換），非 fake script。

平台一律以 ``monkeypatch`` 固定 ``platform.system/machine``（darwin + arm64），
不依賴執行主機；不載入 mlx/torch 真模型、不連網、不 spawn 真 helper。
"""

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ["DATA_DIR"] = tempfile.mkdtemp()  # 必須在 import backend 之前（logger 匯入即寫 log）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import platform  # noqa: E402
import shutil  # noqa: E402

import pytest  # noqa: E402

from backend.core.asr_model_resolver import resolve_engine_chain  # noqa: E402
from backend.core.config import settings  # noqa: E402
from backend.services.asr_apple import apple as apple_provider  # noqa: E402
from backend.services.asr_apple import apple_cli  # noqa: E402
from backend.services.asr_apple.contract import (  # noqa: E402
    APPLE_CANCELLED,
    APPLE_UNAVAILABLE,
    AppleSpeechError,
)
from backend.services.transcription import (  # noqa: E402
    DetailedTranscriptionResult,
    TranscriptionChunk,
    TranscriptionService,
)

#: import 當下的真 resolver 參照：用來證明測試期間 resolver 沒有被替換。
REAL_RESOLVE_EXECUTABLE = apple_cli.resolve_executable

HELPER_BUILD_COMMAND = "swift build -c release --package-path apple_speech_cli"


# ---------------------------------------------------------------------------
# Fixtures：固定平台、真實缺席環境、legacy 引擎計數器
# ---------------------------------------------------------------------------


@pytest.fixture
def apple_platform(monkeypatch):
    """把平台固定成 darwin + arm64（自我一致，不依賴執行主機）。

    直接 monkeypatch ``platform.system``／``platform.machine``：所有真判定點
    （``platform_config.is_darwin_arm64``、``apple_provider._current_platform``、
    ``asr_model_resolver`` 的延後引用）會同時看到同一個平台。
    """

    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")


@pytest.fixture
def uploads_audio(tmp_path, monkeypatch):
    """建立 ``uploads_dir`` 內的短音檔（原生 m4a：不觸發 ffmpeg 轉檔）。"""

    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    audio_path = uploads_dir / "meeting.m4a"
    audio_path.write_bytes(b"fake-m4a-bytes")

    monkeypatch.setattr(settings, "APPLE_LOCALE", "zh-Hant-TW")
    monkeypatch.setattr(settings, "APPLE_PRESET", "time-indexed")
    monkeypatch.setattr(settings, "APPLE_ENABLE_PREFLIGHT", True)
    return audio_path


@pytest.fixture
def real_helper_absent(tmp_path, monkeypatch):
    """以真實條件造成 helper 缺席（非 fake script）；回傳 spawn 守衛計數器。

    ``apple_cli.resolve_executable`` 不被替換：三階搜尋與 ``APPLE_UNAVAILABLE``
    全部由真函式產生。``probe_executable``／``run_helper`` 換成守衛，若缺席路徑
    竟然走到 spawn 就會立刻失敗（本檔案禁止 spawn 真 helper）。
    """

    monkeypatch.setattr(
        settings,
        "APPLE_SPEECH_CLI_PATH",
        str(tmp_path / "configured" / "apple-speech-cli"),
    )
    monkeypatch.setattr(apple_cli, "REPO_ROOT", tmp_path / "empty-repo")
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))

    guards = SimpleNamespace(probe_calls=0, run_calls=0)

    def forbidden_probe(*args, **kwargs):
        guards.probe_calls += 1
        raise AssertionError("真 helper 缺席不得 spawn helper（probe）")

    def forbidden_run(*args, **kwargs):
        guards.run_calls += 1
        raise AssertionError("真 helper 缺席不得 spawn helper（run_helper）")

    monkeypatch.setattr(apple_cli, "probe_executable", forbidden_probe)
    monkeypatch.setattr(apple_cli, "run_helper", forbidden_run)
    return guards


def _spy_legacy_engine(monkeypatch, calls, result=None):
    """把 legacy 引擎執行邊界（``_transcribe_with_legacy_engine``）換成可控 fake。

    ``calls`` 記錄 ``(engine, audio_path)``；被呼叫時回傳 ``result``（預設為已知
    的 mlx 形狀結果），不被呼叫時可斷言清單為空。不載入任何真模型。
    """

    fallback_result = result or DetailedTranscriptionResult(
        text="mlx fallback 逐字稿",
        duration_seconds=12.5,
        language="zh",
        chunks=[TranscriptionChunk(start=0.0, end=12.5, text="mlx fallback 逐字稿")],
        backend="mlx_whisper",
    )

    def fake(self, engine, audio_path, progress_callback, max_retries, force_cpu):
        calls.append((engine, audio_path))
        return fallback_result

    monkeypatch.setattr(TranscriptionService, "_transcribe_with_legacy_engine", fake)
    return fallback_result


# ---------------------------------------------------------------------------
# REAL-ABSENT-04：缺席是自然構成，不是 fake script
# ---------------------------------------------------------------------------


def test_real_helper_absence_is_natural_not_faked(apple_platform, real_helper_absent, tmp_path):
    """真 helper 缺席由「設定路徑不存在 ＋ PATH 無 apple-speech-cli」自然造成。"""

    # resolver 本體未被替換（缺席不是被 mock 出來的）。
    assert apple_cli.resolve_executable is REAL_RESOLVE_EXECUTABLE

    # 三個搜尋位置都是真的落空：設定路徑不存在、repo release 產物位置為空、PATH 找不到。
    configured = Path(settings.APPLE_SPEECH_CLI_PATH)
    assert configured.exists() is False
    assert not (Path(apple_cli.REPO_ROOT) / apple_cli.HELPER_PACKAGE_RELEASE_PATH).exists()
    assert shutil.which(apple_cli.HELPER_EXECUTABLE_NAME) is None

    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.resolve_executable(settings.APPLE_SPEECH_CLI_PATH)

    error = excinfo.value
    assert error.code == APPLE_UNAVAILABLE
    assert error.context.get("stage") == "helper_resolve"
    assert HELPER_BUILD_COMMAND in error.user_message  # 真 helper_missing_message
    assert "設定的 helper 路徑不存在或不可執行" in error.user_message  # configured_rejected：真搜尋證明
    assert real_helper_absent.probe_calls == 0 and real_helper_absent.run_calls == 0


# ---------------------------------------------------------------------------
# REAL-ABSENT-01：顯式 apple ＋ 真 helper 缺席 → fail-closed，不碰 legacy 引擎
# ---------------------------------------------------------------------------


def test_explicit_apple_real_helper_absence_fails_closed(
    apple_platform, uploads_audio, real_helper_absent, monkeypatch
):
    """SI-02：顯式 ``apple`` 鏈嚴格 ``("apple",)``，Apple 失敗直接向上拋、不換手。"""

    monkeypatch.setattr(settings, "ASR_BACKEND", "apple")
    assert resolve_engine_chain(settings.ASR_BACKEND, settings.WHISPER_MODEL) == ("apple",)

    legacy_calls = []
    _spy_legacy_engine(monkeypatch, legacy_calls)
    load_calls = []
    monkeypatch.setattr(
        TranscriptionService,
        "_load_model",
        lambda self, force_cpu=False: load_calls.append(force_cpu),
    )

    service = TranscriptionService()
    with pytest.raises(AppleSpeechError) as excinfo:
        service.transcribe_detailed(str(uploads_audio))

    error = excinfo.value
    assert error.code == APPLE_UNAVAILABLE
    # 真 resolver 的分類與訊息（含建置指令、configured_rejected 註記）。
    assert error.context.get("stage") == "helper_resolve"
    assert "找不到 Apple Speech 命令列工具 apple-speech-cli" in error.user_message
    assert HELPER_BUILD_COMMAND in error.user_message
    assert "設定的 helper 路徑不存在或不可執行" in error.user_message
    # 未 fallback 語意（transcription.py::_apple_failure）與不碰 legacy 引擎。
    assert "未 fallback" in error.user_message
    assert legacy_calls == []
    assert load_calls == []
    assert service._model is None
    assert real_helper_absent.probe_calls == 0 and real_helper_absent.run_calls == 0


# ---------------------------------------------------------------------------
# REAL-ABSENT-02：Mac auto ＋ 真 helper 缺席 → fallback mlx_whisper（可控 fake）
# ---------------------------------------------------------------------------


def test_auto_mac_real_helper_absence_falls_back_to_mlx_whisper(
    apple_platform, uploads_audio, real_helper_absent, monkeypatch
):
    """SI-01／SI-02：Mac ``auto`` 鏈 ``("apple", "mlx_whisper")``；Apple 失敗換手一次。"""

    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")
    assert resolve_engine_chain(settings.ASR_BACKEND, settings.WHISPER_MODEL) == (
        "apple",
        "mlx_whisper",
    )

    legacy_calls = []
    fake_result = _spy_legacy_engine(monkeypatch, legacy_calls)

    progress = []
    service = TranscriptionService()
    result = service.transcribe_detailed(
        str(uploads_audio),
        progress_callback=lambda percent, message: progress.append((percent, message)),
    )

    # 換手恰好一次、進到 mlx_whisper 分支、同一份 abs 路徑。
    assert legacy_calls == [("mlx_whisper", str(uploads_audio))]
    assert result.backend == "mlx_whisper"
    assert result.text == "mlx fallback 逐字稿"
    assert result.duration_seconds == 12.5
    assert result.language == "zh"
    assert [(chunk.start, chunk.end, chunk.text) for chunk in result.chunks] == [
        (0.0, 12.5, "mlx fallback 逐字稿")
    ]

    # 現行 transcription.py：fallback 原樣回傳 legacy 引擎結果；Apple 專屬 metadata
    # （resolved_engine／engine_chain／helper_invocations 等）只在 Apple 成功路徑注入，
    # fallback 結果不得被標成 apple。既有三後端 metadata 維持空 dict。
    assert result.metadata == {}
    assert "resolved_engine" not in result.metadata

    # 換手由真 APPLE_UNAVAILABLE（真 resolver 的分類）驅動，且 Apple 先試。
    assert (25.0, "Apple 引擎失敗（APPLE_UNAVAILABLE），改用 mlx_whisper…") in progress
    assert progress[0][1].startswith("Apple 語音辨識")
    assert real_helper_absent.probe_calls == 0 and real_helper_absent.run_calls == 0
    # 真 provider 的平台閘門看到的就是本檔固定的 darwin（無 fake 模組）。
    assert apple_provider.apple_platform_supported() is True


# ---------------------------------------------------------------------------
# REAL-ABSENT-03：APPLE_CANCELLED（離場碼 7）＋ auto → 永不 fallback
# ---------------------------------------------------------------------------


def test_auto_cancelled_exit_code_7_never_falls_back(
    apple_platform, uploads_audio, tmp_path, monkeypatch
):
    """SI-03：``APPLE_CANCELLED``（離場碼 7）在 ``auto`` 下亦不 fallback。

    注入式（明示）：真 helper 缺席只會產生 ``APPLE_UNAVAILABLE``；離場碼 7 只有
    helper 二進位或真實子行程能產生。因此替換 ``resolve_executable``／
    ``probe_executable``／``build_transcribe_argv``（argv 指向真子行程：python 以 7
    結束），但 ``run_helper`` 與 ``error_from_helper_result`` 都是真的——
    ``HelperResult.returncode`` 是真的 7，分類走真離場碼表。不 spawn 真 helper。
    """

    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")
    assert resolve_engine_chain(settings.ASR_BACKEND, settings.WHISPER_MODEL) == (
        "apple",
        "mlx_whisper",
    )

    legacy_calls = []
    _spy_legacy_engine(monkeypatch, legacy_calls)

    monkeypatch.setattr(
        apple_cli,
        "resolve_executable",
        lambda configured=None, **kwargs: str(tmp_path / "stub-apple-speech-cli"),
    )
    monkeypatch.setattr(
        apple_cli,
        "probe_executable",
        lambda executable, **kwargs: {"schema_version": "1.0", "engine": "apple", "command": "probe"},
    )
    # 注入 argv：真子行程以離場碼 7 結束（非 helper、非假 script、stdout 乾淨）。
    monkeypatch.setattr(
        apple_cli,
        "build_transcribe_argv",
        lambda executable, **kwargs: [sys.executable, "-c", "import sys; sys.exit(7)"],
    )
    # duration 走 600s 下限（PATH 無 ffprobe），m4a 原生不轉檔：無 ffmpeg 副作用。
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))

    progress = []
    service = TranscriptionService()
    with pytest.raises(AppleSpeechError) as excinfo:
        service.transcribe_detailed(
            str(uploads_audio),
            progress_callback=lambda percent, message: progress.append((percent, message)),
        )

    error = excinfo.value
    assert error.code == APPLE_CANCELLED
    # 真離場碼 7 的分類證據（真 failure_context；非 cancelled/timed_out 旗標）。
    assert error.context.get("helper_exit_code") == "7"
    assert error.context.get("helper_cancelled") == "false"
    assert error.context.get("helper_timed_out") == "false"
    assert "Apple 語音辨識已取消" in error.user_message
    assert "未 fallback" in error.user_message
    assert legacy_calls == []
    # 沒有換手提示：鏈不曾被喚醒。
    assert not any("改用" in message for _, message in progress)
