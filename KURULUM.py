"""KURULUM - SGK Bot Otomatik Kurulum Aracı (v2.2)
Bu program bilgisayardaki gereksinimleri kontrol eder, eksikleri otomatik kurar:
  0. GitHub'da yeni sürüm olup olmadığını kontrol eder (varsa kendini günceller)
  1. Bot dosyaları (sgk_bot.py, BAT_BASLAT.bat — yoksa indirir/oluşturur)
  2. Python  (yoksa indirir + sessiz kurar)
  3. Gerekli Python paketleri (selenium, pandas, openpyxl, webdriver-manager)
  4. Google Chrome (yoksa indirir + kurar)
  5. chrome sürümüne uygun chromedriver.exe
  6. çalışmaaaa.xlsx şablonu (yoksa oluşturur) + bot simülasyon testi
Kurulumdan sonra bot BAT_BASLAT.bat ile başlatılır.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Konsol kod sayfasını UTF-8'e çevir (Türkçe karakterler bozulmasın)
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass

# Cmd penceresi başlığını ayarla
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("Developer Arda M. Ekiz")
    except Exception:
        pass

def _masaustu_yolu():
    """Windows masaüstü yolunu registry'den/varsayılanından bulur."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            yol, _ = winreg.QueryValueEx(k, "Desktop")
            yol = os.path.expandvars(yol)
            if os.path.isdir(yol):
                return yol
    except Exception:
        pass
    aday = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
    return aday if os.path.isdir(aday) else os.path.expanduser("~")


def _kurulum_klasoru():
    """Masaüstünde SGK_E_Kesinti_Otomasyon klasörü oluşturur (yazılamazsa EXE yanını döner)."""
    hedef = os.path.join(_masaustu_yolu(), "SGK_E_Kesinti_Otomasyon")
    try:
        os.makedirs(hedef, exist_ok=True)
        return hedef
    except OSError:
        return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _kurulum_klasoru()

PYTHON_INDIR = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
CHROME_INDIR = "https://dl.google.com/chrome/install/latest/chrome_installer.exe"
PAKETLER = ["selenium", "pandas", "openpyxl", "webdriver-manager"]

SURUM = "1.7.4"  # bu kurulum aracının sürümü (GitHub release etiketiyle karşılaştırılır)
GITHUB_REPO = "ArdaEkiz0/e-kesinti-otomasyon"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# ---------- Renkli çıktı yardımcıları ----------

class Renk:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    KIRMIZI = "\033[31m"
    YESIL   = "\033[32m"
    SARI    = "\033[33m"
    MAVI    = "\033[34m"
    MOR     = "\033[35m"
    TURKUAZ = "\033[36m"


def renk_aktif_mi():
    zorla = os.environ.get("SGK_RENK")
    if zorla == "1":
        return True
    if zorla == "0":
        return False
    if os.name == "nt":
        os.system("")
    return sys.stdout.isatty()


RENK_ACIK = renk_aktif_mi()


def renkli(metin, renk=Renk.RESET, kalin=False):
    if not RENK_ACIK:
        return str(metin)
    oz = (Renk.BOLD if kalin else "") + renk
    return f"{oz}{metin}{Renk.RESET}"


def yaz(metin, renk=Renk.RESET, kalin=False):
    print(renkli(metin, renk, kalin), flush=True)


def baslik():
    print("\n" + "=" * 60)
    yaz("🔧 SGK BOT - OTOMATİK KURULUM ARACI", Renk.MAVI, kalin=True)
    yaz("   Gerekli uygulamalar kontrol edilir ve eksikler otomatik kurulur", Renk.TURKUAZ)
    yaz("   Developer: Arda M. Ekiz", Renk.MOR)
    print("=" * 60)


def indir(url, hedef):
    """Dosyayı ilerleme göstergesiyle indirir (başarısız olursa bir kez tekrar dener)."""
    son_hata = None
    for deneme in (1, 2):
        try:
            yaz(f"   ⬇️  İndiriliyor: {url.split('/')[-1]}" + (" (tekrar deneme)" if deneme == 2 else ""), Renk.SARI)
            istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(istek, timeout=180) as r, open(hedef, "wb") as f:
                toplam = int(r.headers.get("Content-Length", 0))
                yazilan = 0
                while True:
                    parca = r.read(65536)
                    if not parca:
                        break
                    f.write(parca)
                    yazilan += len(parca)
                    if toplam:
                        print(f"\r   %3d%%" % (yazilan * 100 // toplam), end="", flush=True)
            print("")
            return
        except Exception as e:
            son_hata = e
            print("")
            if deneme == 1:
                time.sleep(3)
    raise RuntimeError(f"İndirme başarısız: {url} ({son_hata})")


# ---------- 0. Güncelleme kontrolü ----------

def surum_karsilastir(a, b):
    """Sürüm dizgelerini karşılaştırır: a > b ise 1, a == b ise 0, a < b ise -1."""
    def anahtar(s):
        return [int(x) for x in re.findall(r"\d+", s)]
    ka, kb = anahtar(a), anahtar(b)
    uzunluk = max(len(ka), len(kb))
    ka += [0] * (uzunluk - len(ka))
    kb += [0] * (uzunluk - len(kb))
    return (ka > kb) - (ka < kb)


def guncelleme_kontrol():
    """GitHub'daki en son sürümü kontrol eder.

    Yeni sürüm varsa indirme adresini, yoksa None döner."""
    try:
        istek = urllib.request.Request(
            GITHUB_API, headers={"User-Agent": "KURULUM", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(istek, timeout=15) as r:
            veri = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            yaz("   ℹ️  Henüz yayınlanmış sürüm yok — en güncel sürümdesiniz.", Renk.YESIL)
        else:
            yaz(f"   ⚠️  Güncelleme kontrol edilemedi (HTTP {e.code}).", Renk.SARI)
        return None
    except Exception as e:
        yaz(f"   ⚠️  Güncelleme kontrol edilemedi: {e}", Renk.SARI)
        return None

    uzak_surum = str(veri.get("tag_name", "")).lstrip("v")
    indirme = None
    for a in veri.get("assets", []):
        ad = a.get("name", "").lower()
        # Once yeni ZIP paketi, yoksa eski KURULUM.exe
        if ad == "sgk_e_kesinti_otomasyon.zip":
            indirme = a.get("browser_download_url")
            break
        if ad == "kurulum.exe" and not indirme:
            indirme = a.get("browser_download_url")
    if not uzak_surum or not indirme:
        yaz("   ⚠️  Sürüm bilgisi eksik, güncelleme kontrol edilemedi.", Renk.SARI)
        return None

    if surum_karsilastir(SURUM, uzak_surum) >= 0:
        yaz(f"   ✅ En güncel sürümdesiniz (v{SURUM}).", Renk.YESIL)
        return None

    yaz(f"   🔄 Yeni sürüm bulundu: v{SURUM} -> v{uzak_surum}", Renk.SARI, kalin=True)
    return indirme


def guncelle_uygula(url):
    """Yeni surumu indirip uygular. ZIP ise dosyalari klasore acar, exe ise eskisiyle degistirir."""
    if not getattr(sys, "frozen", False) and not url.lower().endswith(".zip"):
        yaz("   📄 Kaynaktan çalışıyorsunuz — güncel dosyaları (KURULUM.py ve KURULUM.exe)"
            " elle değiştirmeniz gerekir.", Renk.SARI)
        return

    if url.lower().endswith(".zip"):
        # Yeni dagitim sekli: ZIP paketini indir, kurulum klasorune ac
        hedef_zip = os.path.join(BASE_DIR, "_guncelleme.zip")
        indir(url, hedef_zip)
        import zipfile
        try:
            with zipfile.ZipFile(hedef_zip) as z:
                z.extractall(BASE_DIR)
        finally:
            try:
                os.remove(hedef_zip)
            except OSError:
                pass
        yaz("   ✅ Güncelleme uygulandı! Tüm dosyalar en yeni sürüme güncellendi.", Renk.YESIL, kalin=True)
        yaz("   ℹ️  Bundan sonra botu başlatmak için: BAT_BASLAT.bat", Renk.TURKUAZ)
        try:
            os.startfile(BASE_DIR)
        except Exception:
            pass
        sys.exit(0)

    eski = os.path.abspath(sys.argv[0])
    klasor = os.path.dirname(eski)
    yeni = os.path.join(klasor, "KURULUM_yeni.exe")
    indir(url, yeni)
    yaz(f"   ✅ Yeni sürüm indirildi: {yeni}", Renk.YESIL)
    bat = os.path.join(klasor, "_guncelle.bat")
    with open(bat, "w", encoding="utf-8") as f:
        f.write(
            "@echo off\r\n"
            "timeout /t 3 /nobreak >nul\r\n"
            f'del "{eski}"\r\n'
            f'ren "{yeni}" "KURULUM.exe"\r\n'
            'del "%~f0"\r\n'
            f'start "" "{os.path.join(klasor, "KURULUM.exe")}"\r\n'
        )
    yaz("   🚀 Güncelleme uygulanıyor, yeni sürüm açılıyor...", Renk.TURKUAZ)
    os.startfile(bat)
    sys.exit(0)


# ---------- 0.5 Bot dosyaları ----------

SGK_BOT_RAW = "https://raw.githubusercontent.com/ArdaEkiz0/e-kesinti-otomasyon/main/sgk_bot.py"

BOT_BASLAT_ICERIK = r"""@echo off
chcp 65001 > nul
rem Calisan gercek Python bul (Windows Store sahte python.exe taklidini atlar)
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
pause"""


def bot_dosyalari_hazirla():
    """sgk_bot.py ve BAT_BASLAT.bat eksikse gömülü kopyadan/GitHub'dan temin eder."""
    yaz("\n📁 1/6 ADIM - Bot dosyaları kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    bot = os.path.join(BASE_DIR, "sgk_bot.py")

    def bot_icerik(yol=None):
        try:
            with open(yol or bot, encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return ""

    def bot_gecerli(yol=None):
        try:
            return os.path.getsize(yol or bot) > 5000 and "SGKBot" in bot_icerik(yol)
        except OSError:
            return False

    if bot_gecerli():
        yaz("   ✅ sgk_bot.py mevcut", Renk.YESIL)
    else:
        gomulu = os.path.join(getattr(sys, "_MEIPASS", ""), "sgk_bot.py")
        if getattr(sys, "_MEIPASS", None) and bot_gecerli(gomulu):
            yaz("   sgk_bot.py gömülü kopyadan çıkarılıyor...", Renk.SARI)
            with open(gomulu, "rb") as k, open(bot, "wb") as h:
                h.write(k.read())
        else:
            yaz("   sgk_bot.py bulunamadı veya eksik, GitHub'dan indiriliyor...", Renk.SARI)
            indir(SGK_BOT_RAW, bot)
        if not bot_gecerli():
            raise RuntimeError("Bot dosyası hazırlanamadı! İnternet bağlantınızı kontrol edip tekrar deneyin.")
        yaz("   ✅ sgk_bot.py hazır", Renk.YESIL)
    bat = os.path.join(BASE_DIR, "BAT_BASLAT.bat")
    if not os.path.exists(bat):
        with open(bat, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(BOT_BASLAT_ICERIK)
        yaz("   ✅ BAT_BASLAT.bat oluşturuldu", Renk.YESIL)
    else:
        yaz("   ✅ BAT_BASLAT.bat mevcut", Renk.YESIL)


# ---------- 1. Python kontrolü ve kurulumu ----------

def winreg_yolu(kok, alt_anahtar):
    """Registry'den Python kurulum yolunu okur (ör. PythonCore\\3.12\\InstallPath)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE if kok == "HKLM" else winreg.HKEY_CURRENT_USER,
                            alt_anahtar) as k:
            yol, _ = winreg.QueryValueEx(k, "")
            return yol
    except Exception:
        return None


def python_adaylari():
    """Sistemdeki Python adaylarını bulur: py launcher, PATH, registry, ortak kurulum yolları."""
    adaylar = []
    for ad, komut in (("py launcher", ["py", "-3"]),
                      ("PATH'teki python", ["python"]),
                      ("PATH'teki python3", ["python3"])):
        try:
            cikti = subprocess.run(komut + ["--version"], capture_output=True, text=True, timeout=30)
            if cikti.returncode == 0:
                adaylar.append((ad, komut[0], komut[1:]))
        except Exception:
            pass
    # Registry: HKCU + HKLM, tüm PythonCore sürümleri
    for kok in ("HKCU", "HKLM"):
        for surum in ("3.14", "3.13", "3.12", "3.11", "3.10"):
            yol = winreg_yolu(kok, rf"SOFTWARE\Python\PythonCore\{surum}\InstallPath")
            if yol and os.path.exists(os.path.join(yol, "python.exe")):
                py = os.path.join(yol, "python.exe")
                adaylar.append((f"registry {kok} {surum}", py, []))
    # Ortak kurulum dizinleri
    for kok in (os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python"),
                "C:\\Program Files\\Python",
                "C:\\Program Files (x86)\\Python",
                "C:\\Python313", "C:\\Python312", "C:\\Python311", "C:\\Python310"):
        if os.path.isdir(kok):
            for alt in sorted(os.listdir(kok), reverse=True):
                py = os.path.join(kok, alt, "python.exe")
                if os.path.exists(py):
                    adaylar.append((py, py, []))
    # Tekilleştir (aynı exe birden fazla kez bulunabilir)
    gorulen = set()
    sonuc = []
    for ad, taban, ek in adaylar:
        anahtar = (taban, tuple(ek))
        if anahtar not in gorulen:
            gorulen.add(anahtar)
            sonuc.append((ad, taban, ek))
    return sonuc


def python_surumu(komut_taban):
    try:
        cikti = subprocess.run(komut_taban + ["--version"], capture_output=True, text=True, timeout=30)
        es = re.search(r"(\d+)\.(\d+)", cikti.stdout + cikti.stderr)
        if es:
            return tuple(int(x) for x in es.groups())
    except Exception:
        pass
    return None


def python_kur():
    yaz("   Python bulunamadı! Otomatik kuruluyor...", Renk.SARI)
    if os.environ.get("PROCESSOR_ARCHITECTURE", "").lower() == "x86":
        raise RuntimeError(
            "Bu bilgisayar 32-bit! Python'un 64-bit sürümü kurulamıyor. "
            "https://www.python.org/downloads adresinden Python 3.12'yi elle kurun.")
    kurucu = os.path.join(BASE_DIR, "python-kurucu.exe")
    indir(PYTHON_INDIR, kurucu)
    if os.path.getsize(kurucu) < 5_000_000:
        raise RuntimeError("Python indirilemedi (dosya eksik)! İnternet bağlantınızı kontrol edip tekrar deneyin.")
    yaz("   🛠️  Python kuruluyor (sessiz kurulum, biraz sürebilir)...", Renk.SARI)
    r = subprocess.run([kurucu, "/quiet", "InstallAllUsers=0", "PrependPath=1",
                        "Include_launcher=1", "Include_test=0", "Include_doc=0",
                        "Include_pip=1", "Shortcuts=0"], timeout=900)
    # 3010 = "başarılı ama yeniden başlatma gerekebilir" (Windows Installer kodu)
    if r.returncode not in (0, 3010):
        raise RuntimeError(f"Python kurulumu başarısız oldu (kod: {r.returncode})!")
    try:
        os.remove(kurucu)
    except OSError:
        pass
    # Kurulumdan sonra geniş arama: py launcher (registry'ye yazar, hemen çalışır),
    # registry yolları ve %LOCALAPPDATA% taraması
    yaz("   🔍 Kurulan Python aranıyor...", Renk.SARI)
    for ad, taban, ek in python_adaylari():
        surum = python_surumu([taban] + ek)
        if surum and surum >= (3, 9):
            yaz(f"   ✅ Python {'.'.join(map(str, surum))} kuruldu ve bulundu ({ad})", Renk.YESIL)
            return [taban] + ek
    raise RuntimeError(
        "Python kuruldu ama bulunamadı! Bilgisayarı yeniden başlatıp tekrar deneyin. "
        "Olmazsa https://www.python.org/downloads adresinden Python 3.12'yi elle kurun "
        "ve 'Add python.exe to PATH' kutusunu işaretleyin.")


def python_hazirla():
    yaz("\n📦 2/6 ADIM - Python kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    en_iyi = None
    for ad, taban, ek in python_adaylari():
        surum = python_surumu([taban] + ek)
        if surum and surum >= (3, 9):
            yaz(f"   ✅ Python {'.'.join(map(str, surum))} bulundu ({ad})", Renk.YESIL)
            return [taban] + ek
        if surum:
            en_iyi = (ad, surum)
    if en_iyi:
        yaz(f"   ⚠️  Python {'.'.join(map(str, en_iyi[1]))} çok eski ({en_iyi[0]})", Renk.SARI)
    return python_kur()


# ---------- 2. Python paketleri ----------

def paketleri_kur(komut):
    yaz("\n📦 3/6 ADIM - Python paketleri yükleniyor/kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    subprocess.run(komut + ["-m", "pip", "install", "--upgrade", "pip", "--quiet", "--disable-pip-version-check"],
                   capture_output=True, timeout=600)
    r = subprocess.run(komut + ["-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + PAKETLER,
                       capture_output=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f"Paket kurulumu başarısız oldu!\n{r.stderr.decode('utf-8', 'replace')[-500:]}")
    yaz(f"   ✅ Paketler hazır: {', '.join(PAKETLER)}", Renk.YESIL)


# ---------- 3. Chrome kontrolü ve kurulumu ----------

def chrome_yollari():
    return [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]


def chrome_bul():
    for p in chrome_yollari():
        if os.path.exists(p):
            return p
    return None


def dosya_surumu(dosya):
    """Dosyanın versiyon numarasını okur (PowerShell ile)."""
    try:
        cikti = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-Item -LiteralPath '{dosya}').VersionInfo.ProductVersion"],
            capture_output=True, text=True, timeout=30)
        es = re.search(r"\d+\.\d+\.\d+\.\d+", cikti.stdout)
        if es:
            return es.group(0)
    except Exception:
        pass
    return None


def chrome_hazirla():
    yaz("\n🌐 4/6 ADIM - Google Chrome kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    chrome = chrome_bul()
    if chrome:
        surum = dosya_surumu(chrome)
        yaz(f"   ✅ Chrome bulundu (sürüm: {surum or 'bilinmiyor'})", Renk.YESIL)
        return surum
    yaz("   Chrome bulunamadı! Otomatik kuruluyor...", Renk.SARI)
    kurucu = os.path.join(BASE_DIR, "chrome-kurucu.exe")
    indir(CHROME_INDIR, kurucu)
    yaz("   🛠️  Chrome kuruluyor (sessiz kurulum)...", Renk.SARI)
    r = subprocess.run([kurucu, "/silent", "/install"], timeout=900)
    try:
        os.remove(kurucu)
    except OSError:
        pass
    time.sleep(5)
    chrome = chrome_bul()
    if not chrome:
        hata = "" if r.returncode == 0 else f" (kurulum kodu: {r.returncode})"
        raise RuntimeError(f"Chrome kurulamadı{hata}! https://www.google.com/chrome adresinden manuel kurun.")
    surum = dosya_surumu(chrome)
    yaz(f"   ✅ Chrome kuruldu (sürüm: {surum or 'bilinmiyor'})", Renk.YESIL)
    return surum


# ---------- 4. chromedriver kontrolü ----------

def chromedriver_surumu(exe):
    try:
        cikti = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
        es = re.search(r"(\d+\.\d+\.\d+\.\d+)", cikti.stdout + cikti.stderr)
        if es:
            return es.group(1)
    except Exception:
        pass
    return None


def chromedriver_indir(chrome_surum):
    """Chrome sürümüne uygun chromedriver'ı bulur ve indirir."""
    url = None
    if not chrome_surum or chrome_surum == "LATEST":
        try:
            with urllib.request.urlopen(
                    "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE",
                    timeout=60) as r:
                chrome_surum = r.read().decode("utf-8").strip()
        except Exception:
            pass
    try:
        with urllib.request.urlopen(
                "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json",
                timeout=60) as r:
            veriler = json.load(r)
        for kayit in veriler["versions"]:
            if kayit["version"] == chrome_surum:
                for d in kayit["downloads"].get("chromedriver", []):
                    if d["platform"] == "win64":
                        url = d["url"]
                break
    except Exception:
        pass
    if not url and chrome_surum:
        url = (f"https://storage.googleapis.com/chrome-for-testing-public/"
               f"{chrome_surum}/win64/chromedriver-win64.zip")
    if not url:
        raise RuntimeError("chromedriver adresi bulunamadı! İnternet bağlantınızı kontrol edin.")
    hedef = os.path.join(BASE_DIR, "chromedriver.exe")
    zip_yol = os.path.join(BASE_DIR, "chromedriver.zip")
    indir(url, zip_yol)
    if os.path.getsize(zip_yol) < 100_000:
        os.remove(zip_yol)
        raise RuntimeError("chromedriver indirilemedi (dosya eksik)! İnternet bağlantınızı kontrol edin.")
    bulundu = False
    with zipfile.ZipFile(zip_yol) as z:
        for ad in z.namelist():
            if ad.endswith("chromedriver.exe"):
                with z.open(ad) as kaynak, open(hedef, "wb") as cikti:
                    cikti.write(kaynak.read())
                bulundu = True
                break
    os.remove(zip_yol)
    if not bulundu:
        raise RuntimeError("chromedriver.zip içinde sürücü bulunamadı!")
    if not chromedriver_surumu(hedef):
        raise RuntimeError("İndirilen chromedriver çalıştırılamadı! Antivirüs engelliyor olabilir.")
    return hedef


def chromedriver_hazirla(chrome_surum):
    yaz("\n🚗 5/6 ADIM - chromedriver kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    hedef = os.path.join(BASE_DIR, "chromedriver.exe")
    if not chrome_surum:
        yaz("   ⚠️  Chrome sürümü okunamadı, en güncel chromedriver indiriliyor...", Renk.SARI)
        if os.path.exists(hedef) and chromedriver_surumu(hedef):
            yaz(f"   ✅ chromedriver zaten hazır: {hedef}", Renk.YESIL)
            return
        chromedriver_indir(chrome_surum)
        yaz(f"   ✅ chromedriver hazır: {hedef}", Renk.YESIL)
        return
    if os.path.exists(hedef):
        mevcut = chromedriver_surumu(hedef)
        if mevcut == chrome_surum:
            yaz(f"   ✅ chromedriver {mevcut} zaten Chrome ile uyumlu", Renk.YESIL)
            return
        if mevcut:
            yaz(f"   ⚠️  chromedriver {mevcut} ile Chrome {chrome_surum} uyumsuz, doğru sürüm indiriliyor...", Renk.SARI)
        else:
            yaz("   ⚠️  chromedriver çalışmıyor, doğru sürüm indiriliyor...", Renk.SARI)
    else:
        yaz("   chromedriver bulunamadı, indiriliyor...", Renk.SARI)
    chromedriver_indir(chrome_surum)
    yaz(f"   ✅ chromedriver {chrome_surum} hazır", Renk.YESIL)


# ---------- 5. Excel şablonu ----------

def excel_sablonu_hazirla(komut):
    yaz("\n📁 6/6 ADIM - Excel şablonu kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    yol = os.path.join(BASE_DIR, "çalışmaaaa.xlsx")
    if os.path.exists(yol):
        yaz("   ✅ çalışmaaaa.xlsx zaten mevcut", Renk.YESIL)
        return
    r = subprocess.run(
        komut + ["-c", "import sys; sys.path.insert(0, '.'); import sgk_bot; sgk_bot.SGKBot.excel_sablonu_hazirla('çalışmaaaa.xlsx')"],
        cwd=BASE_DIR, capture_output=True, text=True, timeout=120)
    if not os.path.exists(yol):
        raise RuntimeError("Şablon oluşturulamadı: " + (r.stderr or r.stdout or "").strip()[-300:])
    yaz("   ✅ Standart şablon oluşturuldu (çalışmaaaa.xlsx)", Renk.YESIL)
    yaz("   ⚠️  Şablonu Excel'de açıp Ünvan, TC Kimlik No, Matrah, Bağ-Kur sütunlarını doldurun.", Renk.SARI)


# ---------- Bot doğrulama ----------

def botu_dogrula(komut):
    yaz("\n🔍 Bot dosyası doğrulanıyor...", Renk.TURKUAZ, kalin=True)
    r = subprocess.run(komut + ["-m", "py_compile", os.path.join(BASE_DIR, "sgk_bot.py")],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"sgk_bot.py hatalı!\n{r.stderr[-300:]}")
    yaz("   ✅ Bot dosyası sorunsuz", Renk.YESIL)


def botu_test_et(komut):
    """Sayfa açmadan bot akışını simülasyonla dener (şablon boşsa sessizce başarılı olur)."""
    yaz("\n🧪 Son kontrol: bot simülasyonla deneniyor...", Renk.TURKUAZ, kalin=True)
    r = subprocess.run(
        komut + ["sgk_bot.py", "--test", "çalışmaaaa.xlsx"],
        cwd=BASE_DIR, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        yaz("   ⚠️  Bot testi tamamlanamadı (teknik detay: "
            + (r.stderr or r.stdout or "")[-200:].strip() + ")", Renk.SARI)
        yaz("   Bot yine de çalışabilir — hatayı görürseniz bize bildirin.", Renk.SARI)
        return
    yaz("   ✅ Bot testi başarılı (tarayıcı açılmadan tüm akış doğrulandı)", Renk.YESIL)


# ---------- Ana akış ----------

def ana():
    baslik()
    yaz("\n🔄 GÜNCELLEME KONTROLÜ", Renk.TURKUAZ, kalin=True)
    yeni_url = guncelleme_kontrol()
    if yeni_url:
        try:
            cevap = input("   Güncellemeyi şimdi uygula? (E/H): ").strip().lower()
        except EOFError:
            cevap = "h"
        if cevap in ("e", "evet", ""):
            guncelle_uygula(yeni_url)
    try:
        bot_dosyalari_hazirla()
        py = python_hazirla()
        paketleri_kur(py)
        chrome_surum = chrome_hazirla()
        chromedriver_hazirla(chrome_surum)
        excel_sablonu_hazirla(py)
        botu_dogrula(py)
        botu_test_et(py)

        print("\n" + "=" * 60)
        yaz("🎉 KURULUM TAMAMLANDI!", Renk.YESIL, kalin=True)
        yaz(f"   Tüm dosyalar şu klasörde: {BASE_DIR}", Renk.TURKUAZ)
        yaz("   'BAT_BASLAT.bat' dosyasına çift tıklayarak botu başlatabilirsiniz.", Renk.TURKUAZ)
        yaz("   (İlk kurulumda Python yeni kurulduysa önce bilgisayarı yeniden başlatın)", Renk.SARI)
        print("=" * 60)
        print(renkli("Developer: Arda M. Ekiz", Renk.MOR, kalin=True))
        try:
            os.startfile(BASE_DIR)
        except Exception:
            pass
    except Exception as e:
        print("\n" + "=" * 60)
        yaz(f"❌ KURULUM BAŞARISIZ: {e}", Renk.KIRMIZI, kalin=True)
        yaz("   İnternet bağlantınızı kontrol edip tekrar deneyin.", Renk.SARI)
        yaz("   Sorun sürerse hata mesajının tam metnini bize iletin.", Renk.SARI)
        print("=" * 60)
    try:
        input("\nKapatmak için ENTER'a basınız...")
    except EOFError:
        pass


if __name__ == "__main__":
    ana()
