@echo off
chcp 65001 > nul
title SGK E-Kesinti Otomasyon
echo.
echo   ███████╗ ██████╗ ██╗  ██╗
echo   ██╔════╝██╔════╝ ██║ ██╔╝
echo   ███████╗██║  ███╗█████╔╝
echo   ╚════██║██║   ██║██╔═██╗
echo   ███████║╚██████╔╝██║  ██╗
echo   ╚══════╝ ╚═════╝ ╚═╝  ╚═╝
echo   ─────────────────────────────
echo   SGK E-Kesinti Otomasyon
echo   Developer: Arda M. Ekiz
echo.
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
rem Masaustune logolu kisayol olustur (sessizce, her calistirmada guncel tutulur)
if not exist "%~dp0app_logo.ico" goto KISAYOL_OK
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell;$d=[Environment]::GetFolderPath('Desktop');$s=$w.CreateShortcut($d+'\SGK Bot.lnk');$s.TargetPath='%~dp0BAT_BASLAT.bat';$s.WorkingDirectory='%~dp0';$s.IconLocation='%~dp0app_logo.ico';$s.Description='SGK E-Kesinti Otomasyon';$s.Save()" >nul 2>nul
:KISAYOL_OK
if "%~1"=="" (
    %PY% "%~dp0sgk_app.py"
) else (
    echo Secilen Excel: %~nx1
    %PY% "%~dp0sgk_app.py" "%~1"
)
pause