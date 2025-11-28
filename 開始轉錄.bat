@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

REM =====================================================
REM 會議轉錄工具 - Windows 啟動腳本
REM Meeting Transcription Tool - Windows Startup Script
REM 
REM Version: 2.0.0
REM Date: 2025-11-28
REM =====================================================

REM 設定視窗標題
title 會議轉錄工具 - Meeting Transcription Tool

REM 清除畫面
cls

echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║                                               ║
echo  ║        會議轉錄工具 Meeting Transcription     ║
echo  ║        ─────────────────────────────────      ║
echo  ║        本地 AI 語音轉文字 + 智慧摘要          ║
echo  ║                                               ║
echo  ╚═══════════════════════════════════════════════╝
echo.

REM 切換到腳本所在目錄
cd /d "%~dp0"
set "PROJECT_DIR=%CD%"

echo  [系統檢查] 正在檢查執行環境...
echo  ─────────────────────────────────────────────────
echo.

REM =====================================================
REM 檢查 1: Python 環境
REM =====================================================
echo  [1/6] 檢查 Python 環境...

set "VENV_PY=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "VENV_PIP=%PROJECT_DIR%\.venv\Scripts\pip.exe"
set "PORTABLE_PY=%PROJECT_DIR%\python\python.exe"
set "PYTHON_PATH="
set "PIP_PATH="
set "NEED_VENV=0"

REM 優先使用專案虛擬環境
if exist "%VENV_PY%" (
    set "PYTHON_PATH=%VENV_PY%"
    set "PIP_PATH=%VENV_PIP%"
    echo        [OK] 使用專案虛擬環境 ^(.venv^)
    goto :python_found
)

REM 其次使用可攜式 Python
if exist "%PORTABLE_PY%" (
    set "PYTHON_PATH=%PORTABLE_PY%"
    for %%I in ("%PORTABLE_PY%") do set "PIP_PATH=%%~dpIScripts\pip.exe"
    echo        [OK] 使用可攜式 Python
    goto :python_found
)

REM 最後檢查系統 Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    goto :python_not_found
)

REM 檢查 Python 版本
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "PY_VERSION=%%V"
echo        [*] 偵測到系統 Python %PY_VERSION%

REM 檢查版本是否 >= 3.10
for /f "tokens=1,2 delims=." %%A in ("%PY_VERSION%") do (
    set "PY_MAJOR=%%A"
    set "PY_MINOR=%%B"
)
if %PY_MAJOR% LSS 3 goto :python_version_error
if %PY_MAJOR%==3 if %PY_MINOR% LSS 10 goto :python_version_error

REM 系統 Python 可用，建立虛擬環境
echo        [*] 正在建立專案虛擬環境...
python -m venv "%PROJECT_DIR%\.venv"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [錯誤] 無法建立虛擬環境！
    echo.
    pause
    goto :eof
)
set "PYTHON_PATH=%VENV_PY%"
set "PIP_PATH=%VENV_PIP%"
set "NEED_VENV=1"
echo        [OK] 虛擬環境建立完成
goto :python_found

:python_not_found
echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║  [錯誤] 找不到 Python！                       ║
echo  ╚═══════════════════════════════════════════════╝
echo.
echo  請安裝 Python 3.10 或更新版本：
echo.
echo    1. 前往 https://www.python.org/downloads/
echo    2. 下載 Python 3.11 或 3.12
echo    3. 安裝時務必勾選「Add Python to PATH」
echo    4. 重新執行此程式
echo.
pause
goto :eof

:python_version_error
echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║  [錯誤] Python 版本過舊！                     ║
echo  ╚═══════════════════════════════════════════════╝
echo.
echo  目前版本: %PY_VERSION%
echo  最低需求: 3.10
echo.
echo  請更新 Python：https://www.python.org/downloads/
echo.
pause
goto :eof

:python_found

REM =====================================================
REM 檢查 2: 安裝 Python 套件
REM =====================================================
echo  [2/6] 檢查 Python 套件...

REM 檢查核心套件
"%PYTHON_PATH%" -c "import yaml" >nul 2>&1
set "NEED_YAML=%ERRORLEVEL%"

"%PYTHON_PATH%" -c "import httpx" >nul 2>&1
set "NEED_HTTPX=%ERRORLEVEL%"

"%PYTHON_PATH%" -c "import faster_whisper" >nul 2>&1
set "NEED_WHISPER=%ERRORLEVEL%"

if %NEED_YAML%==0 if %NEED_HTTPX%==0 if %NEED_WHISPER%==0 (
    echo        [OK] 核心套件已安裝
    goto :packages_ready
)

echo        [*] 正在安裝缺少的套件...
echo.

REM 升級 pip
"%PYTHON_PATH%" -m pip install --upgrade pip -q

REM 安裝套件
if exist "%PROJECT_DIR%\requirements.txt" (
    echo        [*] 使用 requirements.txt 安裝...
    "%PIP_PATH%" install -r "%PROJECT_DIR%\requirements.txt"
) else (
    echo        [*] 安裝核心套件...
    "%PIP_PATH%" install pyyaml httpx faster-whisper
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [錯誤] 套件安裝失敗！請檢查網路連線。
    echo.
    pause
    goto :eof
)

echo.
echo        [OK] 套件安裝完成

:packages_ready

REM =====================================================
REM 檢查 3: CUDA 加速套件
REM =====================================================
echo  [3/6] 檢查 CUDA 加速支援...

set "CUDA_AVAILABLE=0"

REM 檢查 nvidia-smi
nvidia-smi >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo        [!] 未偵測到 NVIDIA GPU，將使用 CPU 模式
    echo        [!] 提示：CPU 模式較慢，但仍可正常運作
    goto :cuda_check_done
)

REM 顯示 GPU 資訊
for /f "tokens=*" %%i in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do (
    echo        [OK] 偵測到 GPU: %%i
)
set "CUDA_AVAILABLE=1"

REM 檢查 CUDA 套件
"%PYTHON_PATH%" -c "import nvidia.cudnn" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo        [*] 正在安裝 CUDA 加速套件...
    "%PIP_PATH%" install nvidia-cudnn-cu12 nvidia-cublas-cu12 -q
    if %ERRORLEVEL% NEQ 0 (
        echo        [!] CUDA 套件安裝失敗，將使用 CPU 模式
        set "CUDA_AVAILABLE=0"
    ) else (
        echo        [OK] CUDA 套件安裝完成
    )
) else (
    echo        [OK] CUDA 加速套件已就緒
)

REM 設定 CUDA 庫路徑
set "NVIDIA_CUDNN=%PROJECT_DIR%\.venv\Lib\site-packages\nvidia\cudnn\bin"
set "NVIDIA_CUBLAS=%PROJECT_DIR%\.venv\Lib\site-packages\nvidia\cublas\bin"

if exist "%NVIDIA_CUDNN%" (
    set "PATH=%NVIDIA_CUDNN%;%PATH%"
)
if exist "%NVIDIA_CUBLAS%" (
    set "PATH=%NVIDIA_CUBLAS%;%PATH%"
)

:cuda_check_done

REM =====================================================
REM 檢查 4: Ollama 服務
REM =====================================================
echo  [4/6] 檢查 Ollama 服務...

REM 檢查 Ollama 是否已安裝
where ollama >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ╔═══════════════════════════════════════════════╗
    echo  ║  [錯誤] 找不到 Ollama！                       ║
    echo  ╚═══════════════════════════════════════════════╝
    echo.
    echo  請安裝 Ollama：
    echo    1. 前往 https://ollama.ai/download
    echo    2. 下載並安裝 Windows 版本
    echo    3. 重新執行此程式
    echo.
    pause
    goto :eof
)

REM 檢查 Ollama 服務是否運行
powershell -Command "try { $null = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo        [*] Ollama 服務未運行，正在啟動...
    start "" /min "ollama" serve
    echo        [*] 等待 Ollama 啟動中...
    timeout /t 5 /nobreak >nul
    
    REM 再次檢查
    powershell -Command "try { $null = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [錯誤] 無法啟動 Ollama 服務！
        echo.
        echo  請手動啟動：
        echo    1. 在開始選單搜尋「Ollama」
        echo    2. 點擊執行
        echo    3. 確認系統匣有 Ollama 圖示
        echo.
        pause
        goto :eof
    )
)
echo        [OK] Ollama 服務運行中

REM =====================================================
REM 檢查 5: LLM 模型
REM =====================================================
echo  [5/6] 檢查 LLM 模型...

REM 從 config.yaml 讀取模型名稱
set "LLM_MODEL=gemma3:12b"
for /f "tokens=2 delims=: " %%M in ('findstr /C:"model:" "%PROJECT_DIR%\config.yaml" 2^>nul ^| findstr /V "#"') do (
    set "LLM_MODEL=%%M"
)
REM 移除引號
set "LLM_MODEL=%LLM_MODEL:"=%"

echo        [*] 設定檔指定模型: %LLM_MODEL%

REM 檢查模型是否存在
ollama list 2>nul | findstr /I "%LLM_MODEL%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo        [!] 模型 %LLM_MODEL% 尚未下載
    echo.
    choice /c YN /n /m "       是否立即下載模型？(Y/N) "
    if !ERRORLEVEL!==1 (
        echo.
        echo        [*] 正在下載 %LLM_MODEL%，請稍候...
        echo        [*] （這可能需要幾分鐘，視網路速度而定）
        echo.
        ollama pull %LLM_MODEL%
        if !ERRORLEVEL! NEQ 0 (
            echo.
            echo  [錯誤] 模型下載失敗！請檢查網路連線。
            echo.
            pause
            goto :eof
        )
        echo.
        echo        [OK] 模型下載完成
    ) else (
        echo.
        echo  [警告] 沒有 LLM 模型，摘要功能將無法使用。
        echo.
        pause
        goto :eof
    )
) else (
    echo        [OK] 模型 %LLM_MODEL% 已就緒
)

REM 檢查模型大小警告
echo %LLM_MODEL% | findstr /I "270m 1b 2b" >nul
if %ERRORLEVEL%==0 (
    echo.
    echo  ╔═══════════════════════════════════════════════╗
    echo  ║  [警告] 您使用的模型可能過小！                ║
    echo  ╚═══════════════════════════════════════════════╝
    echo.
    echo  模型 %LLM_MODEL% 參數量較少，可能無法正確處理長文本摘要。
    echo  建議使用 7B 以上的模型，例如：
    echo    - gemma3:12b
    echo    - qwen2.5:7b
    echo    - llama3.1:8b
    echo.
    choice /c YN /n /m "  是否仍要繼續？(Y/N) "
    if !ERRORLEVEL!==2 (
        echo.
        echo  請在 config.yaml 中修改 model 設定，然後重新執行。
        echo.
        pause
        goto :eof
    )
)

REM =====================================================
REM 檢查 6: 輸入檔案
REM =====================================================
echo  [6/6] 掃描輸入檔案...

REM 建立必要目錄
if not exist "%PROJECT_DIR%\input" mkdir "%PROJECT_DIR%\input"
if not exist "%PROJECT_DIR%\output" mkdir "%PROJECT_DIR%\output"
if not exist "%PROJECT_DIR%\temp" mkdir "%PROJECT_DIR%\temp"
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

REM 計算檔案數量
set "FILE_COUNT=0"
for %%E in (mp3 mp4 wav m4a mkv webm flac ogg wma aac avi mov opus) do (
    for %%F in ("%PROJECT_DIR%\input\*.%%E") do (
        if exist "%%F" set /a FILE_COUNT+=1
    )
)

if %FILE_COUNT%==0 (
    echo.
    echo  ╔═══════════════════════════════════════════════╗
    echo  ║  [提示] input 資料夾中沒有音訊/視訊檔案       ║
    echo  ╚═══════════════════════════════════════════════╝
    echo.
    echo  請將要轉錄的檔案放入：
    echo    %PROJECT_DIR%\input
    echo.
    echo  支援的格式：
    echo    音訊：.mp3 .wav .m4a .flac .ogg .wma .aac .opus
    echo    視訊：.mp4 .mkv .webm .avi .mov
    echo.
    echo  放入檔案後，請重新執行此程式。
    echo.
    start "" "%PROJECT_DIR%\input"
    pause
    goto :eof
)

echo        [OK] 找到 %FILE_COUNT% 個待處理檔案
echo.

REM =====================================================
REM 顯示摘要並確認執行
REM =====================================================
echo  ─────────────────────────────────────────────────
echo  [檢查完成] 系統環境正常
echo  ─────────────────────────────────────────────────
echo.
echo  待處理檔案：
for %%E in (mp3 mp4 wav m4a mkv webm flac ogg wma aac avi mov opus) do (
    for %%F in ("%PROJECT_DIR%\input\*.%%E") do (
        if exist "%%F" echo    • %%~nxF
    )
)
echo.
echo  ─────────────────────────────────────────────────
echo  準備處理 %FILE_COUNT% 個檔案
echo  ─────────────────────────────────────────────────
echo.
echo  按任意鍵開始處理，或按 Ctrl+C 取消...
pause >nul

REM =====================================================
REM 執行主程式
REM =====================================================
echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║  [開始] 執行語音轉錄與摘要生成...             ║
echo  ╚═══════════════════════════════════════════════╝
echo.

"%PYTHON_PATH%" "%PROJECT_DIR%\main.py"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if %EXIT_CODE%==0 (
    echo  ╔═══════════════════════════════════════════════╗
    echo  ║  [完成] 所有檔案處理成功！                    ║
    echo  ╚═══════════════════════════════════════════════╝
) else (
    echo  ╔═══════════════════════════════════════════════╗
    echo  ║  [警告] 部分檔案處理失敗，請查看上方訊息     ║
    echo  ╚═══════════════════════════════════════════════╝
)

echo.
echo  輸出檔案位置：%PROJECT_DIR%\output
echo.

choice /c YN /n /m "  是否開啟輸出資料夾？(Y/N) "
if %ERRORLEVEL%==1 start "" "%PROJECT_DIR%\output"

echo.
echo  感謝使用會議轉錄工具！
echo.
pause

endlocal
exit /b %EXIT_CODE%
