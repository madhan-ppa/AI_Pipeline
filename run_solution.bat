@echo off
REM ============================================================================
REM AI Pipeline Project - Complete Setup and Run Script
REM ============================================================================
REM This script:
REM 1. Creates virtual environment
REM 2. Activates virtual environment
REM 3. Installs dependencies
REM 4. Verifies configuration
REM 5. Runs unit tests
REM 6. Starts Streamlit UI
REM 7. Runs comprehensive evaluation
REM ============================================================================

setlocal enabledelayedexpansion

REM Colors for output
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "RESET=[0m"

echo.
echo ============================================================================
echo   AI Pipeline Project - Complete Setup and Test
echo ============================================================================
echo.

REM Check if Python is installed
echo %YELLOW%[1/8] Checking Python installation...%RESET%
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%ERROR: Python is not installed or not in PATH%RESET%
    exit /b 1
)
echo %GREEN%✓ Python found%RESET%
echo.

REM Create virtual environment if it doesn't exist
echo %YELLOW%[2/8] Setting up virtual environment...%RESET%
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo %GREEN%✓ Virtual environment created%RESET%
) else (
    echo %GREEN%✓ Virtual environment already exists%RESET%
)
echo.

REM Activate virtual environment
echo %YELLOW%[3/8] Activating virtual environment...%RESET%
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo %RED%ERROR: Failed to activate virtual environment%RESET%
    exit /b 1
)
echo %GREEN%✓ Virtual environment activated%RESET%
echo.

REM Install dependencies
echo %YELLOW%[4/8] Installing dependencies...%RESET%
pip install -q -r requirements.txt
if errorlevel 1 (
    echo %RED%ERROR: Failed to install dependencies%RESET%
    exit /b 1
)
echo %GREEN%✓ Dependencies installed%RESET%
echo.

REM Verify configuration
echo %YELLOW%[5/8] Verifying configuration...%RESET%
python -c "from src.config import Config; print('✓ Configuration valid')" >nul 2>&1
if errorlevel 1 (
    echo %RED%ERROR: Configuration verification failed%RESET%
    exit /b 1
)
echo %GREEN%✓ Configuration verified%RESET%
echo.

REM Run unit tests
echo %YELLOW%[6/8] Running unit tests...%RESET%
echo.
python -m pytest tests/ -v --tb=short --json-report --json-report-file=test_results.json
if errorlevel 1 (
    echo %YELLOW%WARNING: Some tests failed (this may be expected)%RESET%
) else (
    echo %GREEN%✓ All tests passed%RESET%
)
echo.

REM Generate test results
echo %YELLOW%[7/8] Generating test results...%RESET%
echo.
python src/utils/test_results_generator.py
if errorlevel 1 (
    echo %YELLOW%WARNING: Test results generation failed%RESET%
) else (
    echo %GREEN%✓ Test results generated%RESET%
)
echo.

REM Ask user what to do next
echo ============================================================================
echo %GREEN%✓ Setup and testing complete!%RESET%
echo ============================================================================
echo.
echo Choose what to do next:
echo.
echo 1. Start Streamlit UI (streamlit run app.py)
echo 2. Run comprehensive evaluation (python evaluate_pipeline.py)
echo 3. Run both (UI first, then evaluation)
echo 4. Exit
echo.

set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo %YELLOW%Starting Streamlit UI...%RESET%
    echo.
    streamlit run app.py
    goto end
)

if "%choice%"=="2" (
    echo.
    echo %YELLOW%Running comprehensive evaluation...%RESET%
    echo.
    python evaluate_pipeline.py
    goto end
)

if "%choice%"=="3" (
    echo.
    echo %YELLOW%Starting Streamlit UI...%RESET%
    echo.
    start streamlit run app.py
    timeout /t 5 /nobreak
    echo.
    echo %YELLOW%Running comprehensive evaluation...%RESET%
    echo.
    python evaluate_pipeline.py
    goto end
)

if "%choice%"=="4" (
    echo.
    echo %GREEN%Exiting...%RESET%
    goto end
)

echo %RED%Invalid choice%RESET%
goto end

:end
echo.
echo ============================================================================
echo   Setup Complete!
echo ============================================================================
echo.
echo Next steps:
echo 1. Streamlit UI: streamlit run app.py
echo 2. Evaluation: python evaluate_pipeline.py
echo 3. Tests: python -m pytest tests/ -v
echo.
echo Generated outputs:
echo - test_results/     (Test reports)
echo - screenshots/      (LangSmith screenshots)
echo - evaluation_reports/ (Evaluation reports)
echo.
pause
