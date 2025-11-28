@echo off
setlocal EnableDelayedExpansion

REM =====================================================
REM Meeting Transcription Tool - Windows Startup Script
REM 
REM Version: 1.1.0
REM Date: 2025-11-27
REM =====================================================

REM Set window title
title Meeting Transcription Tool - Windows

REM Clear screen
cls

echo.
echo  ============================================
echo       Meeting Transcription Tool
echo       Local AI Speech-to-Text Transcription
echo  ============================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM ===== Check 1: Ollama Service =====
echo [1/5] Checking Ollama service...

powershell -Command "try { $null = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [!] Ollama is not running
    echo       [*] Attempting to start Ollama...
    start "" /min cmd /c "ollama serve" 2>nul
    echo       [*] Waiting for Ollama to start...
    timeout /t 8 /nobreak >nul
    powershell -Command "try { $null = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [ERROR] Unable to start Ollama!
        echo.
        echo  Please start Ollama manually:
        echo    1. Open Start menu
        echo    2. Search and run "Ollama"
        echo    3. Confirm Ollama icon appears in system tray
        echo    4. Re-run this script
        echo.
        pause
        goto :eof
    )
)
echo       [OK] Ollama service is running

REM ===== Check 2: GPU Status =====
echo [2/5] Checking GPU status...
nvidia-smi >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [!] Warning: Cannot detect NVIDIA GPU
    echo       [!] Will use CPU mode ^(slower^)
    set "DEVICE=cpu"
) else (
    for /f "tokens=*" %%i in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do (
        echo       [OK] Detected GPU: %%i
    )
    set "DEVICE=cuda"
)

REM ===== Check 3: Python Environment =====
echo [3/5] Checking Python environment...

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "PORTABLE_PY=%CD%\python\python.exe"
set "PYTHON_PATH="

if exist "%VENV_PY%" (
    set "PYTHON_PATH=%VENV_PY%"
    echo       [OK] Using project virtual environment ^(.venv^)
    goto :python_found
)

if exist "%PORTABLE_PY%" (
    set "PYTHON_PATH=%PORTABLE_PY%"
    echo       [OK] Using portable Python ^(python\python.exe^)
    goto :python_found
)

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Python not found!
    echo.
    echo  Please do one of the following:
    echo    1. Create a virtual environment ^(.venv^) in this folder
    echo    2. Place a portable Python under python\
    echo    3. Install Python 3.11+ and add to PATH
    echo.
    echo  Download link: https://www.python.org/downloads/windows/
    echo.
    pause
    goto :eof
)

for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PYTHON_PATH set "PYTHON_PATH=%%P"
)
if not defined PYTHON_PATH set "PYTHON_PATH=python"
echo       [OK] Using system Python

:python_found

REM Add NVIDIA CUDA libraries to PATH for GPU acceleration
set "NVIDIA_LIB_PATH="
if exist "%CD%\.venv\Lib\site-packages\nvidia\cudnn\bin" (
    set "NVIDIA_LIB_PATH=%CD%\.venv\Lib\site-packages\nvidia\cudnn\bin"
)
if exist "%CD%\.venv\Lib\site-packages\nvidia\cublas\bin" (
    if defined NVIDIA_LIB_PATH (
        set "NVIDIA_LIB_PATH=!NVIDIA_LIB_PATH!;%CD%\.venv\Lib\site-packages\nvidia\cublas\bin"
    ) else (
        set "NVIDIA_LIB_PATH=%CD%\.venv\Lib\site-packages\nvidia\cublas\bin"
    )
)
if defined NVIDIA_LIB_PATH (
    set "PATH=!NVIDIA_LIB_PATH!;%PATH%"
    echo       [OK] Added CUDA libraries to PATH
)

REM Check required Python packages
echo       [*] Verifying Python dependencies...
"%PYTHON_PATH%" -c "import yaml, httpx, faster_whisper" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [!] Installing Python dependencies...
    "%PYTHON_PATH%" -m pip install --upgrade pip >nul 2>&1
    if exist "%CD%\requirements.txt" (
        "%PYTHON_PATH%" -m pip install -r "%CD%\requirements.txt"
    ) else (
        "%PYTHON_PATH%" -m pip install pyyaml httpx faster-whisper
    )
)
echo       [OK] Python dependencies are ready

REM ===== Check 4: Whisper backend (Python) =====
echo [4/5] Verifying Whisper backend...
"%PYTHON_PATH%" -c "import faster_whisper" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] faster-whisper is not installed.
    echo  Please run: "%PYTHON_PATH%" -m pip install faster-whisper
    echo.
    pause
    goto :eof
)
echo       [OK] faster-whisper Python backend detected

REM ===== Check 5: Input Files =====
echo [5/5] Scanning input files...

if not exist "input" mkdir "input"
if not exist "output" mkdir "output"
if not exist "temp" mkdir "temp"
if not exist "logs" mkdir "logs"

set "FILE_COUNT=0"
for %%f in (input\*.mp3 input\*.mp4 input\*.wav input\*.m4a input\*.mkv input\*.webm input\*.flac input\*.ogg input\*.wma input\*.aac input\*.avi input\*.mov input\*.opus) do (
    set /a FILE_COUNT+=1
)

if %FILE_COUNT%==0 (
    echo.
    echo  [INFO] No audio/video files in input folder
    echo.
    echo  Please place files to transcribe in the input folder:
    echo    %CD%\input
    echo.
    echo  Supported formats:
    echo    Audio: .mp3 .wav .m4a .flac .ogg .wma .aac .opus
    echo    Video: .mp4 .mkv .webm .avi .mov
    echo.
    pause
    goto :eof
)

echo       [OK] Found %FILE_COUNT% file^(s^) to process
echo.

echo  Files to process:
for %%f in (input\*.mp3 input\*.mp4 input\*.wav input\*.m4a input\*.mkv input\*.webm input\*.flac input\*.ogg input\*.wma input\*.aac input\*.avi input\*.mov input\*.opus) do (
    echo    * %%~nxf
)
echo.

REM ===== Confirm Execution =====
echo  ============================================
echo  Ready to process %FILE_COUNT% file^(s^)
echo  ============================================
echo.
echo  Press any key to start, or Ctrl+C to cancel...
pause >nul

REM ===== Run Main Program =====
echo.
echo  [START] Running transcription and summarization...
echo  ============================================
echo.

"%PYTHON_PATH%" main.py
set "MAIN_EXITCODE=%ERRORLEVEL%"

if %MAIN_EXITCODE% NEQ 0 (
    echo.
    echo  [WARNING] Some files failed to process, check error messages above
) else (
    echo.
    echo  ============================================
    echo  [DONE] All files processed successfully!
    echo  ============================================
)

echo.
echo  Output files are in: %CD%\output
echo.

choice /c YN /n /m "Open output folder? (Y/N) "
if %ERRORLEVEL%==1 start "" "%CD%\output"

echo.
echo  Thank you for using Meeting Transcription Tool!
echo.
pause

endlocal
exit /b %MAIN_EXITCODE%
