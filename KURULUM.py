"""KURULUM - SGK Bot Otomatik Kurulum Aracı (v2.1)
Bu program bilgisayardaki gereksinimleri kontrol eder, eksikleri otomatik kurar:
  0. GitHub'da yeni sürüm olup olmadığını kontrol eder (varsa kendini günceller)
  1. Python  (yoksa indirir + sessiz kurar)
  2. Gerekli Python paketleri (selenium, pandas, openpyxl, webdriver-manager)
  3. Google Chrome (yoksa indirir + kurar)
  4. chrome sürümüne uygun chromedriver.exe
  5. çalışmaaaa.xlsx şablonu (yoksa oluşturur)
Kurulumdan sonra bot BOT_BAŞLAT.bat ile başlatılır.
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

BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))

PYTHON_INDIR = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
CHROME_INDIR = "https://dl.google.com/chrome/install/latest/chrome_installer.exe"
PAKETLER = ["selenium", "pandas", "openpyxl", "webdriver-manager"]

SURUM = "1.0.0"  # bu kurulum aracının sürümü (GitHub release etiketiyle karşılaştırılır)
GITHUB_REPO = "ArdaEkiz0/sgk-bot"
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
    """Dosyayı ilerleme göstergesiyle indirir."""
    yaz(f"   ⬇️  İndiriliyor: {url.split('/')[-1]}", Renk.SARI)
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
        if a.get("name", "").lower() == "kurulum.exe":
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
    """Yeni KURULUM.exe'yi indirir ve eski dosyayla değiştirir."""
    if not getattr(sys, "frozen", False):
        yaz("   📄 Kaynaktan çalışıyorsunuz — güncel dosyaları (KURULUM.py ve KURULUM.exe)"
            " elle değiştirmeniz gerekir.", Renk.SARI)
        return
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


# ---------- 1. Python kontrolü ve kurulumu ----------

def python_adaylari():
    """Sistemdeki Python adaylarını bulur: py launcher, PATH, ortak kurulum yolları."""
    adaylar = []
    for ad, komut in (("py launcher", ["py", "-3"]), ("PATH'teki python", ["python"])):
        try:
            cikti = subprocess.run(komut + ["--version"], capture_output=True, text=True, timeout=30)
            if cikti.returncode == 0:
                adaylar.append((ad, komut[0], komut[1:]))
        except Exception:
            pass
    for kok in (os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python"),
                "C:\\Python313", "C:\\Python312", "C:\\Python311", "C:\\Python310"):
        if os.path.isdir(kok):
            for alt in os.listdir(kok):
                py = os.path.join(kok, alt, "python.exe")
                if os.path.exists(py):
                    adaylar.append((py, py, []))
    return adaylar


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
    kurucu = os.path.join(BASE_DIR, "python-kurucu.exe")
    indir(PYTHON_INDIR, kurucu)
    yaz("   🛠️  Python kuruluyor (sessiz kurulum, biraz sürebilir)...", Renk.SARI)
    r = subprocess.run([kurucu, "/quiet", "InstallAllUsers=0", "PrependPath=1",
                        "Include_launcher=1", "Include_test=0", "Include_doc=0",
                        "Include_pip=1", "Shortcuts=0"], timeout=900)
    if r.returncode != 0:
        raise RuntimeError("Python kurulumu başarısız oldu!")
    try:
        os.remove(kurucu)
    except OSError:
        pass
    yeni = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe")
    if os.path.exists(yeni):
        return yeni
    raise RuntimeError("Python kuruldu ama bulunamadı! Bilgisayarı yeniden başlatıp tekrar deneyin.")


def python_hazirla():
    yaz("\n📦 1/5 ADIM - Python kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
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
    return [python_kur()]


# ---------- 2. Python paketleri ----------

def paketleri_kur(py):
    yaz("\n📦 2/5 ADIM - Python paketleri yükleniyor/kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    subprocess.run([py, "-m", "pip", "install", "--upgrade", "pip", "--quiet", "--disable-pip-version-check"],
                   capture_output=True, timeout=600)
    r = subprocess.run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + PAKETLER,
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
    yaz("\n🌐 3/5 ADIM - Google Chrome kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    chrome = chrome_bul()
    if chrome:
        surum = dosya_surumu(chrome)
        yaz(f"   ✅ Chrome bulundu (sürüm: {surum or 'bilinmiyor'})", Renk.YESIL)
        return surum
    yaz("   Chrome bulunamadı! Otomatik kuruluyor...", Renk.SARI)
    kurucu = os.path.join(BASE_DIR, "chrome-kurucu.exe")
    indir(CHROME_INDIR, kurucu)
    yaz("   🛠️  Chrome kuruluyor (sessiz kurulum)...", Renk.SARI)
    subprocess.run([kurucu, "/silent", "/install"], timeout=900)
    try:
        os.remove(kurucu)
    except OSError:
        pass
    time.sleep(5)
    chrome = chrome_bul()
    if not chrome:
        raise RuntimeError("Chrome kurulamadı! https://www.google.com/chrome adresinden manuel kurun.")
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
    if not url:
        url = f"https://edgedl.me/chrome-for-testing/{chrome_surum}/win64/chromedriver-win64.zip"
    hedef = os.path.join(BASE_DIR, "chromedriver.exe")
    zip_yol = os.path.join(BASE_DIR, "chromedriver.zip")
    indir(url, zip_yol)
    with zipfile.ZipFile(zip_yol) as z:
        for ad in z.namelist():
            if ad.endswith("chromedriver.exe"):
                with z.open(ad) as kaynak, open(hedef, "wb") as cikti:
                    cikti.write(kaynak.read())
                break
    os.remove(zip_yol)
    return hedef


def chromedriver_hazirla(chrome_surum):
    yaz("\n🚗 4/5 ADIM - chromedriver kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    if not chrome_surum:
        yaz("   ⚠️  Chrome sürümü okunamadı, en güncel chromedriver indiriliyor...", Renk.SARI)
        hedef = os.path.join(BASE_DIR, "chromedriver.exe")
        if not os.path.exists(hedef):
            chromedriver_indir(chrome_surum or "LATEST")
        yaz(f"   ✅ chromedriver hazır: {hedef}", Renk.YESIL)
        return
    hedef = os.path.join(BASE_DIR, "chromedriver.exe")
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

def excel_sablonu_hazirla(py):
    yaz("\n📁 5/5 ADIM - Excel şablonu kontrol ediliyor...", Renk.TURKUAZ, kalin=True)
    yol = os.path.join(BASE_DIR, "çalışmaaaa.xlsx")
    if os.path.exists(yol):
        yaz("   ✅ çalışmaaaa.xlsx zaten mevcut", Renk.YESIL)
        return
    r = subprocess.run(
        [py, "-c", "import sys; sys.path.insert(0, '.'); import sgk_bot; sgk_bot.SGKBot.excel_sablonu_hazirla('çalışmaaaa.xlsx')"],
        cwd=BASE_DIR, capture_output=True, text=True, timeout=120)
    if os.path.exists(yol):
        yaz("   ✅ Standart şablon oluşturuldu (çalışmaaaa.xlsx)", Renk.YESIL)
        yaz("   ⚠️  Şablonu Excel'de açıp Ünvan, TC Kimlik No, Matrah, Bağ-Kur sütunlarını doldurun.", Renk.SARI)
    else:
        yaz("   ❌ Şablon oluşturulamadı: " + (r.stderr or "").strip()[-300:], Renk.KIRMIZI)


# ---------- Bot doğrulama ----------

def botu_dogrula(py):
    yaz("\n🔍 Bot dosyası doğrulanıyor...", Renk.TURKUAZ, kalin=True)
    r = subprocess.run([py, "-m", "py_compile", os.path.join(BASE_DIR, "sgk_bot.py")],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"sgk_bot.py hatalı!\n{r.stderr[-300:]}")
    yaz("   ✅ Bot dosyası sorunsuz", Renk.YESIL)


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
        py = python_hazirla()
        paketleri_kur(py[0])
        chrome_surum = chrome_hazirla()
        chromedriver_hazirla(chrome_surum)
        excel_sablonu_hazirla(py[0])
        botu_dogrula(py[0])

        print("\n" + "=" * 60)
        yaz("🎉 KURULUM TAMAMLANDI!", Renk.YESIL, kalin=True)
        yaz("   Şimdi 'BOT_BAŞLAT.bat' dosyasına çift tıklayarak botu başlatabilirsiniz.", Renk.TURKUAZ)
        yaz("   (İlk kurulumda Python yeni kurulduysa önce bilgisayarı yeniden başlatın)", Renk.SARI)
        print("=" * 60)
        print(renkli("Developer: Arda M. Ekiz", Renk.MOR, kalin=True))
    except Exception as e:
        print("\n" + "=" * 60)
        yaz(f"❌ KURULUM BAŞARISIZ: {e}", Renk.KIRMIZI, kalin=True)
        yaz("   İnternet bağlantınızı kontrol edip tekrar deneyin.", Renk.SARI)
        print("=" * 60)
    try:
        input("\nKapatmak için ENTER'a basınız...")
    except EOFError:
        pass


if __name__ == "__main__":
    ana()
