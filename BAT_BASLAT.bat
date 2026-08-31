@echo off
chcp 65001 > nul
title SGK E-Kesinti Otomasyon
rem Calisan gercek Python bul (Windows Store sahte python.exe taklidini otomatik atlar)
set "PY="
set "PYW="
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
rem pythonw bul (konsol penceresiz calistirma icin)
set "PYW=%PY:python=pythonw%"
if "%PYW%"=="%PY%" (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" set "PYW=%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
    if exist "%ProgramFiles%\Python312\pythonw.exe" set "PYW=%ProgramFiles%\Python312\pythonw.exe"
    if exist "%ProgramFiles%\Python313\pythonw.exe" set "PYW=%ProgramFiles%\Python313\pythonw.exe"
)
rem Masaustune logolu kisayol olustur (sessizce, her calistirmada guncel tutulur)
if not exist "%~dp0docs\app_logo.ico" goto KISAYOL_OK
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell;$d=[Environment]::GetFolderPath('Desktop');$s=$w.CreateShortcut($d+'\SGK Bot.lnk');$s.TargetPath='%~dp0BAT_BASLAT.bat';$s.WorkingDirectory='%~dp0';$s.IconLocation='%~dp0docs\app_logo.ico';$s.Description='SGK E-Kesinti Otomasyon';$s.Save()" >nul 2>nul
:KISAYOL_OK
if "%~1"=="" (
    start "" "%PYW%" "%~dp0sgk_app.py"
) else (
    start "" "%PYW%" "%~dp0sgk_app.py" "%~1"
)