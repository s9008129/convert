@echo off
setlocal EnableDelayedExpansion

REM =====================================================
REM Meeting Transcription Tool - Windows Startup Script
REM 
REM Version: 1.0.0
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

REM Use PowerShell to check Ollama (more reliable)
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo       [!] Ollama is not running
    echo       [*] Attempting to start Ollama...
    
    REM Try to start Ollama (background)
    start "" /min cmd /c "ollama serve" 2>nul
    
    REM Wait for Ollama to start
    echo       [*] Waiting for Ollama to start...
    timeout /t 8 /nobreak >nul
    
    REM Check again
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1
    
    if errorlevel 1 (
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
        exit /b 1
    )
)
echo       [OK] Ollama service is running

REM ===== Check 2: GPU Status =====
echo [2/5] Checking GPU status...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo       [!] Warning: Cannot detect NVIDIA GPU
    echo       [!] Will use CPU mode (slower)
    set DEVICE=cpu
) else (
    REM Display GPU info
    for /f "tokens=*" %%i in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do (
        echo       [OK] Detected GPU: %%i
    )
    set DEVICE=cuda
)

REM ===== Check 3: Python Environment =====
echo [3/5] Checking Python environment...

REM Prefer portable Python
if exist "python\python.exe" (
    set PYTHON_PATH=python\python.exe
    echo       [OK] Using portable Python
) else (
    REM Check system Python
    where python >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [ERROR] Python not found!
        echo.
        echo  Please do one of the following:
        echo    1. Download portable Python to python\ folder
        echo    2. Install Python 3.11+ and add to PATH
        echo.
        echo  Download link:
        echo    https://www.python.org/downloads/windows/
        echo    Choose "Windows embeddable package (64-bit)"
        echo.
        pause
        exit /b 1
    )
    set PYTHON_PATH=python
    echo       [OK] Using system Python
)

REM Check required Python packages
%PYTHON_PATH% -c "import yaml" >nul 2>&1
if errorlevel 1 (
    echo       [!] Installing required packages...
    %PYTHON_PATH% -m pip install pyyaml httpx --quiet
)

REM ===== Check 4: Whisper Executable =====
echo [4/5] Checking Whisper transcription engine...
if exist "faster-whisper-xxl.exe" (
    echo       [OK] faster-whisper-xxl.exe is ready
) else (
    REM Check subdirectories
    for /r %%f in (faster-whisper-xxl.exe) do (
        if exist "%%f" (
            echo       [OK] Found faster-whisper-xxl.exe
            goto :whisper_found
        )
    )
    echo       [!] Warning: faster-whisper-xxl.exe not found
    echo       [!] Please download from:
    echo       [!] https://github.com/Purfview/whisper-standalone-win/releases
)
:whisper_found

REM ===== Check 5: Input Files =====
echo [5/5] Scanning input files...

REM Ensure folders exist
if not exist "input" mkdir "input"
if not exist "output" mkdir "output"
if not exist "temp" mkdir "temp"
if not exist "logs" mkdir "logs"

REM Count files
set FILE_COUNT=0
set TOTAL_SIZE=0

for %%f in (input\*.mp3 input\*.mp4 input\*.wav input\*.m4a input\*.mkv input\*.webm input\*.flac input\*.ogg) do (
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
    echo    Audio: .mp3 .wav .m4a .flac .ogg
    echo    Video: .mp4 .mkv .webm .avi .mov
    echo.
    pause
    exit /b 1
)

echo       [OK] Found %FILE_COUNT% file(s) to process
echo.

REM List files
echo  Files to process:
for %%f in (input\*.mp3 input\*.mp4 input\*.wav input\*.m4a input\*.mkv input\*.webm input\*.flac input\*.ogg) do (
    echo    * %%~nxf
)
echo.

REM ===== Confirm Execution =====
echo  ============================================
echo  Ready to process %FILE_COUNT% file(s)
echo  ============================================
echo.
echo  Press any key to start, or Ctrl+C to cancel...
pause >nul

REM ===== Run Main Program =====
echo.
echo  [START] Running transcription and summarization...
echo  ============================================
echo.

%PYTHON_PATH% main.py

REM Check execution result
if errorlevel 1 (
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

REM Ask to open output folder
choice /c YN /n /m "Open output folder? (Y/N) "
if errorlevel 2 goto :end
if errorlevel 1 start "" "%CD%\output"

:end
echo.
echo  Thank you for using Meeting Transcription Tool!
echo.
pause

endlocal
