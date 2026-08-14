@echo off
chcp 65001 > nul
if "%~1"=="" (
    python "%~dp0sgk_bot.py"
) else (
    echo 📂 Seçilen Excel: %~nx1
    python "%~dp0sgk_bot.py" "%~1"
)
pause