@echo off
setlocal EnableDelayedExpansion

REM =====================================================
REM 會議轉錄工具 - Windows 版啟動腳本
REM 
REM 注意：此檔案必須以「UTF-8 with BOM」編碼儲存
REM       否則中文將顯示亂碼
REM 
REM 版本：1.0.0
REM 日期：2025-11-27
REM =====================================================

REM 設定控制台為 UTF-8
chcp 65001 >nul 2>&1

REM 設定視窗標題
title 會議轉錄工具 - Windows 版

REM 清除畫面
cls

echo.
echo  ============================================
echo       會議轉錄工具 - Windows 版
echo       本地 AI 語音轉逐字稿轉會議紀錄
echo  ============================================
echo.

REM 切換到腳本所在目錄
cd /d "%~dp0"

REM ===== 檢查 1：Ollama 服務 =====
echo [1/5] 檢查 Ollama 服務...

REM 使用 PowerShell 檢查 Ollama（更可靠）
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo       [!] Ollama 未運行
    echo       [*] 嘗試啟動 Ollama...
    
    REM 嘗試啟動 Ollama（背景執行）
    start "" /min cmd /c "ollama serve" 2>nul
    
    REM 等待 Ollama 啟動
    echo       [*] 等待 Ollama 啟動...
    timeout /t 8 /nobreak >nul
    
    REM 再次檢查
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
    
    if errorlevel 1 (
        echo.
        echo  [錯誤] 無法啟動 Ollama！
        echo.
        echo  請手動啟動 Ollama：
        echo    1. 開啟「開始」選單
        echo    2. 搜尋並執行「Ollama」
        echo    3. 確認 Ollama 圖示出現在系統匣
        echo    4. 重新執行此腳本
        echo.
        pause
        exit /b 1
    )
)
echo       [OK] Ollama 服務正常

REM ===== 檢查 2：GPU 狀態 =====
echo [2/5] 檢查 GPU 狀態...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo       [!] 警告：無法偵測 NVIDIA GPU
    echo       [!] 將使用 CPU 模式（較慢）
    set DEVICE=cpu
) else (
    REM 顯示 GPU 資訊
    for /f "tokens=*" %%i in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do (
        echo       [OK] 偵測到 GPU: %%i
    )
    set DEVICE=cuda
)

REM ===== 檢查 3：Python 環境 =====
echo [3/5] 檢查 Python 環境...

REM 優先使用可攜式 Python
if exist "python\python.exe" (
    set PYTHON_PATH=python\python.exe
    echo       [OK] 使用可攜式 Python
) else (
    REM 檢查系統 Python
    where python >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [錯誤] 找不到 Python！
        echo.
        echo  請執行以下任一操作：
        echo    1. 下載可攜式 Python 到 python\ 資料夾
        echo    2. 安裝 Python 3.11+ 並加入 PATH
        echo.
        echo  下載連結：
        echo    https://www.python.org/downloads/windows/
        echo    選擇「Windows embeddable package (64-bit)」
        echo.
        pause
        exit /b 1
    )
    set PYTHON_PATH=python
    echo       [OK] 使用系統 Python
)

REM 檢查必要的 Python 套件
%PYTHON_PATH% -c "import yaml" >nul 2>&1
if errorlevel 1 (
    echo       [!] 安裝必要套件...
    %PYTHON_PATH% -m pip install pyyaml httpx --quiet
)

REM ===== 檢查 4：Whisper 執行檔 =====
echo [4/5] 檢查 Whisper 轉錄引擎...
if exist "faster-whisper-xxl.exe" (
    echo       [OK] faster-whisper-xxl.exe 已就緒
) else (
    REM 檢查是否在子目錄
    for /r %%f in (faster-whisper-xxl.exe) do (
        if exist "%%f" (
            echo       [OK] 找到 faster-whisper-xxl.exe
            goto :whisper_found
        )
    )
    echo       [!] 警告：找不到 faster-whisper-xxl.exe
    echo       [!] 請從以下連結下載：
    echo       [!] https://github.com/Purfview/whisper-standalone-win/releases
)
:whisper_found

REM ===== 檢查 5：輸入檔案 =====
echo [5/5] 掃描輸入檔案...

REM 確保資料夾存在
if not exist "input" mkdir "input"
if not exist "output" mkdir "output"
if not exist "temp" mkdir "temp"
if not exist "logs" mkdir "logs"

REM 計算檔案數量
set FILE_COUNT=0
set TOTAL_SIZE=0

for %%f in (input\*.mp3 input\*.mp4 input\*.wav input\*.m4a input\*.mkv input\*.webm input\*.flac input\*.ogg) do (
    set /a FILE_COUNT+=1
)

if %FILE_COUNT%==0 (
    echo.
    echo  [提示] input 資料夾沒有音訊/視訊檔案
    echo.
    echo  請將需要轉錄的檔案放入 input 資料夾：
    echo    %CD%\input
    echo.
    echo  支援的格式：
    echo    音訊：.mp3 .wav .m4a .flac .ogg
    echo    視訊：.mp4 .mkv .webm .avi .mov
    echo.
    pause
    exit /b 1
)

echo       [OK] 找到 %FILE_COUNT% 個待處理檔案
echo.

REM 列出檔案
echo  待處理檔案：
for %%f in (input\*.mp3 input\*.mp4 input\*.wav input\*.m4a input\*.mkv input\*.webm input\*.flac input\*.ogg) do (
    echo    * %%~nxf
)
echo.

REM ===== 確認執行 =====
echo  ============================================
echo  準備開始處理 %FILE_COUNT% 個檔案
echo  ============================================
echo.
echo  按任意鍵開始處理，或按 Ctrl+C 取消...
pause >nul

REM ===== 執行主程式 =====
echo.
echo  [開始] 執行轉錄與摘要...
echo  ============================================
echo.

%PYTHON_PATH% main.py

REM 檢查執行結果
if errorlevel 1 (
    echo.
    echo  [警告] 部分檔案處理失敗，請查看上方錯誤訊息
) else (
    echo.
    echo  ============================================
    echo  [完成] 所有檔案處理成功！
    echo  ============================================
)

echo.
echo  輸出檔案位於：%CD%\output
echo.

REM 詢問是否開啟輸出資料夾
choice /c YN /n /m "是否開啟輸出資料夾？(Y/N) "
if errorlevel 2 goto :end
if errorlevel 1 start "" "%CD%\output"

:end
echo.
echo  感謝使用會議轉錄工具！
echo.
pause

endlocal
