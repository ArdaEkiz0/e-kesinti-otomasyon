@echo off
chcp 65001 > nul
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
    where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PY (
    echo HATA: Python bulunamadi! Once KURULUM.exe calistirin.
    pause
    exit /b 1
)
if "%~1"=="" (
    %PY% "%~dp0sgk_bot.py"
) else (
    echo Secilen Excel: %~nx1
    %PY% "%~dp0sgk_bot.py" "%~1"
)
pause
