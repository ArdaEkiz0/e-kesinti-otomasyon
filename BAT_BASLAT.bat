@echo off
chcp 65001 > nul
rem Calisan gercek Python bul (Windows Store sahte python.exe taklidini otomatik atlar)
set "PY="
for %%C in ("py -3" "python") do (
    if not defined PY (
        %%~C --version >nul 2>nul && set "PY=%%~C"
    )
)
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PY if exist "%ProgramFiles%\Python312\python.exe" set "PY=%ProgramFiles%\Python312\python.exe"
if not defined PY if exist "%ProgramFiles%\Python313\python.exe" set "PY=%ProgramFiles%\Python313\python.exe"
if not defined PY (
    echo HATA: Python bulunamadi! Once BAT_KURULUM.bat calistirin.
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