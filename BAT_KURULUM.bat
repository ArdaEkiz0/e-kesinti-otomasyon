@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title SGK E-Kesinti Otomasyon - Kurulum

echo ============================================================
echo    SGK BOT - OTOMATIK KURULUM ARACI
echo    Python ve gerekli paketler kontrol edilir/kurulur
echo    Developer: Arda M. Ekiz
echo ============================================================
echo.

REM ---------- 1/3: Python kontrolu ----------
echo [1/3] Python kontrol ediliyor...

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PY (
    if exist "%ProgramFiles%\Python312\python.exe" set "PY=%ProgramFiles%\Python312\python.exe"
)

if defined PY (
    echo    OK - Python bulundu.
    goto PAKETLER
)

echo    Python bulunamadi! Otomatik kuruluyor (biraz surebilir)...
winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements >nul 2>nul
if errorlevel 1 (
    echo    HATA: Python otomatik kurulamadi!
    echo    Lutfen https://www.python.org/downloads adresinden Python kurun.
    echo    Kurulumda "Add python.exe to PATH" kutusunu isaretleyin.
    goto SON
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
    where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
    echo    HATA: Python kuruldu ama bulunamadi. Bilgisayari yeniden baslatip tekrar deneyin.
    goto SON
)
echo    OK - Python kuruldu.

:PAKETLER
REM ---------- 2/3: Paketler ----------
echo.
echo [2/3] Gerekli paketler yukleniyor/kontrol ediliyor (selenium, pandas, openpyxl, webdriver-manager)...
%PY% -m pip install --quiet --disable-pip-version-check selenium pandas openpyxl webdriver-manager
if errorlevel 1 (
    echo    HATA: Paket kurulumu basarisiz! Internet baglantinizi kontrol edin.
    goto SON
)
echo    OK - Paketler hazir.

REM ---------- 3/3: Excel sablonu ----------
echo.
echo [3/3] Excel sablonu kontrol ediliyor...
if exist "çalışmaaaa.xlsx" (
    echo    OK - calismaaaa.xlsx zaten mevcut.
) else (
    %PY% -c "import sgk_bot; sgk_bot.SGKBot.excel_sablonu_hazirla('çalışmaaaa.xlsx')" >nul 2>nul
    if exist "çalışmaaaa.xlsx" (
        echo    OK - Sablon olusturuldu (calismaaaa.xlsx^).
        echo    NOT: Sablonu Excel'de acip Unvan, TC Kimlik No, Matrah, Bag-Kur sutunlarini doldurun.
    ) else (
        echo    UYARI: Sablon olusturulamadi ama bot calisir - Excel dosyasini kendiniz hazirlayabilirsiniz.
    )
)

REM Chrome kontrolu
echo.
echo Chrome kontrol ediliyor...
set "CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=var"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=var"
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME=var"
if defined CHROME (
    echo    OK - Chrome bulundu. (chromedriver ilk calistirmada otomatik indirilir^)
) else (
    echo    UYARI: Chrome bulunamadi! Bot icin Google Chrome gerekiyor.
    echo    https://www.google.com/chrome adresinden kurun.
)

echo.
echo ============================================================
echo    KURULUM TAMAMLANDI!
echo    Botu baslatmak icin: BAT_BASLAT.bat dosyasina cift tiklayin
echo ============================================================
echo Developer: Arda M. Ekiz

:SON
echo.
pause
