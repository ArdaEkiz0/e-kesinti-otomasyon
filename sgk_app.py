"""
SGK E-Kesinti Otomasyon v1.8.0
Arda Yazilim - Profesyonel PyQt5 GUI (modern arayuz revizyonu)
"""

import sys
import os
import io
import math
import hashlib
import uuid
import platform
import subprocess
import threading
import time
import json
import re
import urllib.request
import urllib.error
import zipfile
import base64
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QLineEdit, QAbstractButton,
    QProgressBar, QTextEdit, QFileDialog, QSpacerItem, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QButtonGroup, QScrollArea, QComboBox
)

# API Client import (opsiyonel - Worker entegrasyonu icin)
try:
    from api_client import register_and_check, check_authorization, WORKER_URL
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QRectF, QPointF,
    QPropertyAnimation, QEasingCurve, pyqtProperty
)
from PyQt5.QtGui import (
    QFont, QColor, QIcon, QPixmap, QPainter, QPen, QBrush,
    QPainterPath, QPolygonF, QLinearGradient
)

# --- Sabitler ---
SURUM = "1.8.0"
UYGULAMA_ADI = "SGK E-Kesinti Otomasyon"
SIRKET = "Arda M. Ekiz"

# --- DPI scale faktoru (yuksek cozunurluklu ekranlarda arayuzu buyutmek icin) ---
try:
    import ctypes
    _scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0 if hasattr(ctypes, "windll") else 1.0
except Exception:
    _scale = 1.0
SC = lambda v: int(round(v * _scale))
SF = lambda v: int(round(v * _scale))



def _taban_dizin():
    """PyInstaller EXE'sinde exe'nin yanindaki klasor, kaynakta dosyanin klasoru."""
    import sys as _sys
    import os as _os
    if getattr(_sys, "frozen", False):
        return _os.path.dirname(_sys.executable)
    return _os.path.dirname(_os.path.abspath(__file__))


class _LisansSorgu(QThread):
    bitti = pyqtSignal(object)

    def __init__(self, hardware_id, parent=None):
        super().__init__(parent)
        self.hardware_id = hardware_id

    def run(self):
        try:
            from api_client import register_and_check
            sonuc = register_and_check(self.hardware_id)
        except Exception as e:  # noqa: BLE001
            sonuc = {"_hata": str(e)}
        self.bitti.emit(sonuc)


# --- Renkler (yeni "Kesinti Konsolu" paleti - siyah zemin + inceltilmis altin vurgu) ---
BG_MAIN = "#14130f"
BG_SIDEBAR = "#0d0c0a"
BG_CARD = "#1b1914"
BG_CARD_HOVER = "#211e18"
BORDER_COLOR = "#2c2820"
BORDER_SOFT = "#211d17"

ACCENT_PRIMARY = "#c9a15a"
ACCENT_PRIMARY_DIM = "rgba(201,161,90,36)"
ACCENT_PRIMARY_BORDER = "rgba(201,161,90,71)"
ACCENT_SECONDARY = "#8a6f45"

SUCCESS = "#5fb488"
SUCCESS_DIM = "rgba(95,180,136,36)"
SUCCESS_BORDER = "rgba(95,180,136,82)"

WARNING = "#d99a4e"
WARNING_DIM = "rgba(217,154,78,36)"
WARNING_BORDER = "rgba(217,154,78,82)"

ERROR = "#d16255"
ERROR_DIM = "rgba(209,98,85,36)"
ERROR_BORDER = "rgba(209,98,85,82)"

TEXT_PRIMARY = "#f3ede1"
TEXT_SECONDARY = "#a89d8a"
TEXT_FAINT = "#6f6555"

INPUT_BG = BG_MAIN
UI_FONT = "Segoe UI"
MONO_FONT = "Consolas"

# --- Demo Lisans ---
DEMO_LISANS = "SGK-DEMO0001-2025-ARDA-2026"
DEMO_TOPLAM_GUN = 14  # gosterge cubugu icin varsayilan deneme suresi

# --- GitHub Guncelleme ---
GITHUB_REPO = "ArdaEkiz0/e-kesinti-otomasyon"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_hardware_id():
    try:
        cpu_id = platform.processor() or "unknown"
        node = uuid.getnode()
        mac = ':'.join(('%012x' % node)[i:i+2] for i in range(0, 12, 2))
        raw = f"{cpu_id}-{mac}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
        parts = [digest[i:i+4] for i in range(0, 16, 4)]
        return f"SGK-{parts[0]}-{parts[1]}-{parts[2]}-{parts[3]}"
    except Exception:
        return "SGK-0000-0000-0000-0000"


def _surum_karsilastir(a, b):
    """Surum karsilastir: pozitif ise a > b, sifir ise esit, negatif ise a < b."""
    ra = [int(x) for x in re.findall(r"\d+", a)]
    rb = [int(x) for x in re.findall(r"\d+", b)]
    uzunluk = max(len(ra), len(rb))
    ra += [0] * (uzunluk - len(ra))
    rb += [0] * (uzunluk - len(rb))
    if ra > rb:
        return 1
    if ra < rb:
        return -1
    return 0


def _guncelleme_var_mi():
    """GitHub'da daha yeni surum varsa (surum, zip_url) doner; yoksa (None, None)."""
    try:
        istek = urllib.request.Request(
            GITHUB_API, headers={"User-Agent": "SGK-App", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(istek, timeout=10) as r:
            veri = json.loads(r.read().decode("utf-8"))
        uzak_surum = str(veri.get("tag_name", "")).lstrip("v")
        if not uzak_surum:
            return None, None
        if _surum_karsilastir(SURUM, uzak_surum) >= 0:
            return None, None
        for a in veri.get("assets", []):
            if a.get("name", "").lower() == "sgk_e_kesinti_otomasyon.zip":
                return uzak_surum, a.get("browser_download_url")
    except Exception:
        pass
    return None, None


def _otomatik_guncelle(zip_url, progress_callback=None):
    """Yeni ZIP paketini indirip uygulama klasorune acar."""
    hedef_klasor = _taban_dizin()
    zip_yol = os.path.join(hedef_klasor, "_guncelleme.zip")
    istek = urllib.request.Request(zip_url, headers={"User-Agent": "SGK-App"})
    with urllib.request.urlopen(istek, timeout=180) as r:
        toplam = int(r.headers.get("Content-Length", 0))
        yazilan = 0
        with open(zip_yol, "wb") as f:
            while True:
                parca = r.read(65536)
                if not parca:
                    break
                f.write(parca)
                yazilan += len(parca)
                if progress_callback and toplam:
                    progress_callback(yazilan * 100 // toplam)
    if os.path.getsize(zip_yol) < 1000:
        raise RuntimeError("ZIP indirilemedi (dosya eksik)")
    with zipfile.ZipFile(zip_yol) as z:
        z.extractall(hedef_klasor)
    try:
        os.remove(zip_yol)
    except OSError:
        pass


# --- Yerel Sifreli Kimlik Bilgileri Yonetimi ---
_CRED_FILE = "sgk_credentials.dat"


def _get_machine_key():
    """Makineye ozel sifreleme anahtari uretir (HWID tabanli)."""
    hwid = get_hardware_id()
    return hashlib.sha256(f"SGK-CRED-{hwid}-2026".encode()).digest()


def _xor_crypt(data, key):
    """XOR tabanli sifreleme/cozme (simetrik)."""
    key_len = len(key)
    return bytes([b ^ key[i % key_len] for i, b in enumerate(data)])


def _save_credentials(credentials):
    """Kimlik bilgilerini makineye ozel sifreli dosyaya kaydeder."""
    key = _get_machine_key()
    raw = json.dumps(credentials, ensure_ascii=False).encode("utf-8")
    encrypted = _xor_crypt(raw, key)
    b64 = base64.b64encode(encrypted).decode("ascii")
    cred_path = os.path.join(_taban_dizin(), _CRED_FILE)
    with open(cred_path, "w", encoding="utf-8") as f:
        f.write(b64)


def _load_credentials():
    """Sifreli dosyadan kimlik bilgilerini okur. Dosya yoksa veya bozuksa bos doner."""
    cred_path = os.path.join(_taban_dizin(), _CRED_FILE)
    if not os.path.exists(cred_path):
        return []
    try:
        with open(cred_path, "r", encoding="utf-8") as f:
            b64 = f.read().strip()
        if not b64:
            return []
        encrypted = base64.b64decode(b64)
        key = _get_machine_key()
        raw = _xor_crypt(encrypted, key)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return []


def _add_credential(name, tc_no, password):
    """Yeni kimlik bilgisi ekler (ayni isim varsa uzerine yazar)."""
    creds = _load_credentials()
    creds = [c for c in creds if c.get("name") != name]
    creds.append({"name": name, "tc": tc_no, "password": password})
    _save_credentials(creds)


def _delete_credential(name):
    """Belirli bir kimlik bilgisini siler."""
    creds = _load_credentials()
    creds = [c for c in creds if c.get("name") != name]
    _save_credentials(creds)


# ============================================================================
#  Ikon cizimi (harici dosya/kutuphane gerektirmez - QPainter ile vektor cizim)
# ============================================================================

_ICON_CACHE = {}


def _paint_icon_24(p, kind, color):
    """24x24 mantiksal koordinat uzayinda basit, cizgisel bir ikon cizer."""
    pen = QPen(QColor(color))
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if kind == "home":
        p.drawPolyline(QPolygonF([QPointF(4, 11.5), QPointF(12, 4), QPointF(20, 11.5)]))
        path = QPainterPath(QPointF(6, 10.2))
        path.lineTo(6, 19)
        path.lineTo(10, 19)
        path.lineTo(10, 13)
        path.lineTo(14, 13)
        path.lineTo(14, 19)
        path.lineTo(18, 19)
        path.lineTo(18, 10.2)
        p.drawPath(path)

    elif kind == "grid":
        p.drawRoundedRect(QRectF(3.5, 3.5, 17, 17), 2, 2)
        p.drawLine(QPointF(3.5, 9.5), QPointF(20.5, 9.5))
        p.drawLine(QPointF(3.5, 15), QPointF(20.5, 15))
        p.drawLine(QPointF(9.5, 3.5), QPointF(9.5, 20.5))
        p.drawLine(QPointF(15, 3.5), QPointF(15, 20.5))

    elif kind == "gear":
        p.drawEllipse(QPointF(12, 12), 3.2, 3.2)
        for i in range(8):
            ang = math.radians(i * 45)
            x1, y1 = 12 + 6.2 * math.cos(ang), 12 + 6.2 * math.sin(ang)
            x2, y2 = 12 + 9.3 * math.cos(ang), 12 + 9.3 * math.sin(ang)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    elif kind == "shield":
        path = QPainterPath(QPointF(12, 3))
        path.lineTo(19, 6)
        path.lineTo(19, 11.5)
        path.cubicTo(19, 16, 16, 19.3, 12, 20.8)
        path.cubicTo(8, 19.3, 5, 16, 5, 11.5)
        path.lineTo(5, 6)
        path.closeSubpath()
        p.drawPath(path)
        check = QPainterPath(QPointF(8.7, 12.2))
        check.lineTo(11, 14.5)
        check.lineTo(15.3, 9.8)
        p.drawPath(check)

    elif kind == "key":
        p.drawEllipse(QPointF(8, 15), 4, 4)
        p.drawLine(QPointF(11, 12), QPointF(19, 4))
        p.drawLine(QPointF(15.5, 7.5), QPointF(17.5, 9.5))
        p.drawLine(QPointF(18.3, 4.7), QPointF(19.7, 6.1))

    elif kind == "info":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawLine(QPointF(12, 10.5), QPointF(12, 16.5))
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(12, 7.6), 1.0, 1.0)

    elif kind == "copy":
        p.drawRoundedRect(QRectF(9, 9, 11, 11), 2, 2)
        path = QPainterPath(QPointF(5, 15))
        path.lineTo(5, 6.5)
        path.lineTo(6.5, 5)
        path.lineTo(15, 5)
        p.drawPath(path)

    elif kind == "folder":
        path = QPainterPath(QPointF(3.5, 6.5))
        path.lineTo(9.5, 6.5)
        path.lineTo(11.5, 8.5)
        path.lineTo(20.5, 8.5)
        path.lineTo(20.5, 17.5)
        path.lineTo(3.5, 17.5)
        path.closeSubpath()
        p.drawPath(path)

    elif kind == "play":
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([QPointF(7, 4.5), QPointF(20, 12), QPointF(7, 19.5)]))

    elif kind == "stop":
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)

    elif kind == "plus":
        p.drawLine(QPointF(12, 5), QPointF(12, 19))
        p.drawLine(QPointF(5, 12), QPointF(19, 12))

    elif kind == "trash":
        p.drawLine(QPointF(4, 7), QPointF(20, 7))
        path = QPainterPath(QPointF(9, 7))
        path.lineTo(9, 4.8)
        path.lineTo(15, 4.8)
        path.lineTo(15, 7)
        p.drawPath(path)
        body = QPainterPath(QPointF(6.6, 7))
        body.lineTo(7.3, 19)
        body.lineTo(16.7, 19)
        body.lineTo(17.4, 7)
        p.drawPath(body)

    elif kind == "save":
        path = QPainterPath(QPointF(5, 4))
        path.lineTo(16, 4)
        path.lineTo(19, 7)
        path.lineTo(19, 20)
        path.lineTo(5, 20)
        path.closeSubpath()
        p.drawPath(path)
        p.drawRect(QRectF(8, 4, 6.5, 4.5))
        p.drawRect(QRectF(7.5, 14, 9, 6))

    elif kind == "check-circle":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        path = QPainterPath(QPointF(8, 12.4))
        path.lineTo(10.5, 15)
        path.lineTo(16, 9.3)
        p.drawPath(path)

    elif kind == "x-circle":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawLine(QPointF(9, 9), QPointF(15, 15))
        p.drawLine(QPointF(15, 9), QPointF(9, 15))

    elif kind == "alert":
        p.drawPolygon(QPolygonF([QPointF(12, 4), QPointF(2.5, 20), QPointF(21.5, 20)]))
        p.drawLine(QPointF(12, 10), QPointF(12, 14.5))
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(12, 17), 1.0, 1.0)

    elif kind == "clock":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawLine(QPointF(12, 12), QPointF(12, 7))
        p.drawLine(QPointF(12, 12), QPointF(15.5, 14))

    elif kind == "dot":
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(12, 12), 4.2, 4.2)

    elif kind == "lock":
        p.drawRoundedRect(QRectF(5, 10.5, 14, 9), 2, 2)
        path = QPainterPath()
        path.moveTo(8, 10.5)
        path.lineTo(8, 8)
        path.cubicTo(8, 5.8, 9.8, 4, 12, 4)
        path.cubicTo(14.2, 4, 16, 5.8, 16, 8)
        path.lineTo(16, 10.5)
        p.drawPath(path)


def icon(kind, color, size=16):
    """Belirtilen tur/renk/boyut icin bir QIcon uretir (bellek ici onbellekli)."""
    key = (kind, color, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    scale = size / 24.0
    p.scale(scale, scale)
    _paint_icon_24(p, kind, color)
    p.end()
    qi = QIcon(pm)
    _ICON_CACHE[key] = qi
    return qi


class IconGlyph(QWidget):
    """Terminal/log satirlarinda ve durum kartlarinda kullanilan kucuk ikon widget'i."""

    def __init__(self, kind, color, size=14, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.color = color
        self.setFixedSize(size, size)
        self._size = size

    def set_kind(self, kind, color=None):
        self.kind = kind
        if color:
            self.color = color
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        scale = self._size / 24.0
        p.scale(scale, scale)
        _paint_icon_24(p, self.kind, self.color)


# ============================================================================
#  Bot Thread
# ============================================================================

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_EMOJI_PREFIX_RE = re.compile(r"^[\s\U0001F300-\U0001FAFF☀-➿←-⇿️]+")
_PROGRESS_RE = re.compile(r"%\s*(\d{1,3})%\s*\((\d+)/(\d+)\)")
_SUMMARY_RE = re.compile(r"Ba[şs]ar[ıi]l[ıi]\s*:\s*(\d+)\s*/\s*(\d+)")


_DECORATIVE_CHARS = set("█╗╔╝╚║═╦╩╬╠╣▓▒░▄▀■□▌▐▁▂▃▄▅▆▇★☆")
_DECORATIVE_TEXT_RE = re.compile(
    r"^(SGK TARIMSAL KESİNTİ OTOMASYONU BOT|Developer:\s*Arda M\. Ekiz|S[üu]r[üu]m:\s*v[\d.]+)$",
    re.IGNORECASE,
)


def _suslemelik_satir_mi(temiz):
    """ASCII-art banner satirlarini, '='*N/'-'*N ayirici cizgileri ve konsola ozel
    tekrar eden basit tanitim satirlarini tespit eder; bunlar log panelinde
    gosterilmeye deger degildir (arayuzde zaten surum/uygulama adi gosteriliyor)."""
    if not temiz:
        return True
    stripped = temiz.strip()
    if not stripped:
        return True
    # Sadece '=' / '-' / cizgi karakterlerinden olusan ayirici satirlar
    if re.fullmatch(r"[=\-_─━]{5,}", stripped):
        return True
    # Sadece kutu-cizim / blok karakterlerinden olusan ASCII-art satirlari
    harfler = [c for c in stripped if not c.isspace()]
    if harfler and all(c in _DECORATIVE_CHARS for c in harfler):
        return True
    # Konsol icin yazilmis, arayuzde zaten gosterilen tanitim satirlari
    if _DECORATIVE_TEXT_RE.match(stripped):
        return True
    return False


def _temizle_log_satiri(ham):
    """ANSI renk kodlarini ve baştaki emoji/simgeleri temizler, gosterim metnini dondurur.
    Susleme/ASCII-art satirlari icin bos string dondurur (cagiran taraf bunlari atlar)."""
    temiz = _ANSI_RE.sub("", ham)
    temiz = _EMOJI_PREFIX_RE.sub("", temiz)
    temiz = temiz.strip()
    if _suslemelik_satir_mi(temiz):
        return ""
    return temiz


class _StreamToSignal(io.TextIOBase):
    """print() cikislarini satir satir bir Qt sinyaline yonlendiren stdout vekili.
    Boylece log, botun calismasi bitene kadar biriktirilmek yerine GERCEK ZAMANLI
    olarak arayuzde gorunur."""

    def __init__(self, emit_func):
        super().__init__()
        self._emit = emit_func
        self._buf = ""

    def write(self, s):
        if not s:
            return 0
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._emit(line)
        return len(s)

    def flush(self):
        pass


class BotThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    # sgk_bot kullanicidan bir eylemi (login gibi) onaylamasini istediginde
    # (mesaj, evet_hayir_mi) ile yayinlanir - ana thread bir dialog gosterip
    # resolve_prompt() cagirana kadar bot thread'i burada bekler.
    prompt_signal = pyqtSignal(str, bool)

    def __init__(self, excel_path, parent=None, giris_bilgisi=None):
        super().__init__(parent)
        self.excel_path = excel_path
        self.giris_bilgisi = giris_bilgisi
        self._running = True
        self._prompt_event = threading.Event()
        self._prompt_answer = True

    def _ask_continue(self, mesaj):
        """sgk_bot tarafindan cagrilir (konsol yoksa input() yerine): kullanicinin
        bir eylemi (SGK'ya login olmak gibi) tamamladigini onaylamasini bekler."""
        temiz = _temizle_log_satiri(mesaj) or mesaj.strip()
        self._prompt_event.clear()
        self.prompt_signal.emit(temiz, False)
        self._prompt_event.wait()

    def _ask_yesno(self, mesaj):
        """sgk_bot tarafindan cagrilir: Evet/Hayir onayi ister, cevabi dondurur."""
        temiz = _temizle_log_satiri(mesaj) or mesaj.strip()
        self._prompt_event.clear()
        self.prompt_signal.emit(temiz, True)
        self._prompt_event.wait()
        return self._prompt_answer

    def resolve_prompt(self, answer=True):
        """Ana (GUI) thread'den cagrilir: bekleyen bot thread'ini devam ettirir."""
        self._prompt_answer = answer
        self._prompt_event.set()

    def run(self):
        self.log_signal.emit("Bot baslatiliyor...")
        try:
            sys.path.insert(0, _taban_dizin())
            import sgk_bot
            self.log_signal.emit("sgk_bot modulu yuklendi.")

            import contextlib
            stream = _StreamToSignal(self.log_signal.emit)

            bot = sgk_bot.SGKBot(
                test_modu=False,
                devam_callback=self._ask_continue,
                onay_callback=self._ask_yesno,
                giris_bilgisi=self.giris_bilgisi,
            )

            with contextlib.redirect_stdout(stream):
                bot.run(self.excel_path)

        except Exception as e:
            self.log_signal.emit(f"Hata: {str(e)}")
        finally:
            self.finished_signal.emit("Tamamlandi")

    def stop(self):
        self._running = False
        # Bot bir onay bekliyor olabilir - durdurulunca orada sonsuza kadar takili kalmasin
        self._prompt_answer = False
        self._prompt_event.set()


# ============================================================================
#  Ortak bilesenler
# ============================================================================

class CardFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setStyleSheet(f"""
            QFrame#CardFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
            }}
        """)


class StyledButton(QPushButton):
    def __init__(self, text, color=ACCENT_PRIMARY, text_color="#1a1509", ic=None, parent=None):
        super().__init__(text, parent)
        self.base_color = color
        self.text_color = text_color
        self.setMinimumHeight(SC(40))
        if ic:
            self.setIcon(icon(ic, text_color, 14))
            self.setIconSize(QSize(14, 14))
        self._update_style()
        self.setCursor(Qt.PointingHandCursor)

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.base_color};
                color: {self.text_color};
                border: none;
                border-radius: 8px;
                padding: 0 18px;
                font-size: {SF(13)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {ACCENT_SECONDARY}; }}
            QPushButton:pressed {{ background-color: #6d5a3a; }}
            QPushButton:disabled {{ background-color: {BORDER_COLOR}; color: {TEXT_FAINT}; }}
        """)


class GhostButton(QPushButton):
    """Ikincil eylemler icin duz/cerceveli buton."""

    def __init__(self, text, ic=None, parent=None, small=False):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        if ic:
            self.setIcon(icon(ic, TEXT_SECONDARY, 13))
            self.setIconSize(QSize(13, 13))
        h = SC(30) if small else SC(36)
        fs = SF(11.5) if small else SF(12.5)
        self.setMinimumHeight(h)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_CARD_HOVER};
                color: {TEXT_SECONDARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 7px;
                padding: 0 13px;
                font-size: {fs}px;
                font-weight: 600;
            }}
            QPushButton:hover {{ color: {TEXT_PRIMARY}; border-color: #3a3428; }}
            QPushButton:disabled {{ color: {TEXT_FAINT}; }}
        """)


class StatCard(QFrame):
    def __init__(self, title, value, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setObjectName("StatCard")
        self.setMinimumHeight(SC(84))
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-left: 3px solid {color};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SC(16), SC(13), SC(16), SC(13))
        layout.setSpacing(SC(5))

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(10.5)}px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
        layout.addWidget(title_lbl)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setFont(QFont(MONO_FONT, SF(19), QFont.Bold))
        self.value_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        layout.addWidget(self.value_lbl)

    def set_value(self, v):
        self.value_lbl.setText(str(v))


class RingStat(QFrame):
    """Basari oranini halka (donut) grafik ile gosteren istatistik karti."""

    def __init__(self, title, percent, color, parent=None):
        super().__init__(parent)
        self.color = color
        self._percent = percent
        self.setObjectName("StatCard")
        self.setMinimumHeight(SC(84))
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-left: 3px solid {color};
                border-radius: 12px;
            }}
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SC(16), SC(13), SC(16), SC(13))
        outer.setSpacing(SC(6))

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(10.5)}px; font-weight: 700; letter-spacing: 1px; background: transparent; border: none;")
        outer.addWidget(title_lbl)

        row = QHBoxLayout()
        row.setSpacing(SC(10))
        self.ring = _RingWidget(percent, color)
        self.ring.setFixedSize(SC(36), SC(36))
        row.addWidget(self.ring)

        self.value_lbl = QLabel(f"%{percent}")
        self.value_lbl.setFont(QFont(MONO_FONT, SF(16), QFont.Bold))
        self.value_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        row.addWidget(self.value_lbl)
        row.addStretch()
        outer.addLayout(row)

    def set_percent(self, percent):
        self._percent = max(0, min(100, percent))
        self.ring.set_percent(self._percent)
        self.value_lbl.setText(f"%{self._percent}")


class _RingWidget(QWidget):
    def __init__(self, percent, color, parent=None):
        super().__init__(parent)
        self._percent = percent
        self._color = color

    def set_percent(self, p):
        self._percent = p
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad = 4
        rect = QRectF(pad, pad, w - 2 * pad, h - 2 * pad)

        pen_bg = QPen(QColor(BORDER_COLOR))
        pen_bg.setWidthF(4)
        pen_bg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_bg)
        p.drawArc(rect, 0, 360 * 16)

        pen_fg = QPen(QColor(self._color))
        pen_fg.setWidthF(4)
        pen_fg.setCapStyle(Qt.RoundCap)
        p.setPen(pen_fg)
        span = int(360 * 16 * (self._percent / 100.0))
        p.drawArc(rect, 90 * 16, -span)


class NavButton(QPushButton):
    def __init__(self, text, ic, parent=None):
        super().__init__(text, parent)
        self.kind = ic
        self.setCheckable(True)
        self.setFixedHeight(SC(38))
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(icon(ic, TEXT_SECONDARY, 15))
        self.setIconSize(QSize(15, 15))
        self.setLayoutDirection(Qt.LeftToRight)
        self._apply()
        self.toggled.connect(self._apply)

    def _apply(self):
        checked = self.isChecked()
        color = ACCENT_PRIMARY if checked else TEXT_SECONDARY
        self.setIcon(icon(self.kind, color, 15))
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    background-color: {ACCENT_PRIMARY_DIM};
                    color: {ACCENT_PRIMARY};
                    border: 1px solid {ACCENT_PRIMARY_BORDER};
                    border-radius: 8px;
                    padding-left: 11px;
                    font-size: {SF(12.5)}px;
                    font-weight: 700;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    background-color: transparent;
                    color: {TEXT_SECONDARY};
                    border: 1px solid transparent;
                    border-radius: 8px;
                    padding-left: 11px;
                    font-size: {SF(12.5)}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background-color: {BG_CARD_HOVER}; color: {TEXT_PRIMARY}; }}
            """)


class ToggleSwitch(QAbstractButton):
    """Ayarlar sayfasinda kullanilan animasyonlu acik/kapali dugmesi."""

    def __init__(self, parent=None, checked=True):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(SC(40), SC(22))
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def getPos(self):
        return self._pos

    def setPos(self, v):
        self._pos = v
        self.update()

    pos = pyqtProperty(float, getPos, setPos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        track_off = QColor(BORDER_COLOR)
        track_on = QColor(ACCENT_PRIMARY)
        track_off.setAlpha(255)
        r = h / 2
        track_color = QColor(
            int(track_off.red() + (track_on.red() - track_off.red()) * self._pos),
            int(track_off.green() + (track_on.green() - track_off.green()) * self._pos),
            int(track_off.blue() + (track_on.blue() - track_off.blue()) * self._pos),
        )
        p.setPen(Qt.NoPen)
        p.setBrush(track_color if self._pos > 0.02 else QColor(BORDER_COLOR))
        if self._pos <= 0.02:
            p.setOpacity(1.0)
        else:
            p.setOpacity(0.28 + 0.0 * self._pos)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        p.setOpacity(1.0)
        if self._pos > 0.02:
            pen = QPen(QColor(ACCENT_PRIMARY))
            pen.setWidthF(1)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        thumb_d = h - 6
        x = 3 + (w - thumb_d - 6) * self._pos
        thumb_color = QColor(ACCENT_PRIMARY) if self._pos > 0.5 else QColor(TEXT_FAINT)
        p.setPen(Qt.NoPen)
        p.setBrush(thumb_color)
        p.drawEllipse(QRectF(x, 3, thumb_d, thumb_d))


class Stepper(QWidget):
    """Sayisal bekleme suresi gibi degerler icin +/- adim kontrolu."""

    def __init__(self, minimum=1, maximum=120, value=3, suffix=" sn", parent=None):
        super().__init__(parent)
        self._min = minimum
        self._max = maximum
        self._val = value
        self._suffix = suffix

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.dec_btn = QPushButton("–")
        self.inc_btn = QPushButton("+")
        self.val_lbl = QLabel()
        self.val_lbl.setAlignment(Qt.AlignCenter)

        for b in (self.dec_btn, self.inc_btn):
            b.setFixedSize(SC(30), SC(34))
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{ background-color: {BG_MAIN}; color: {TEXT_SECONDARY};
                    border: none; font-size: {SF(15)}px; font-weight: 700; }}
                QPushButton:hover {{ background-color: {BG_CARD_HOVER}; color: {ACCENT_PRIMARY}; }}
            """)
        self.val_lbl.setFixedSize(SC(64), SC(34))
        self.val_lbl.setStyleSheet(f"""
            background-color: {BG_MAIN}; color: {TEXT_PRIMARY};
            font-family: '{MONO_FONT}'; font-size: {SF(12.5)}px; font-weight: 600;
            border-left: 1px solid {BORDER_COLOR}; border-right: 1px solid {BORDER_COLOR};
        """)

        layout.addWidget(self.dec_btn)
        layout.addWidget(self.val_lbl)
        layout.addWidget(self.inc_btn)

        self.setStyleSheet(f"border: 1.5px solid {BORDER_COLOR}; border-radius: 8px;")
        self.setFixedHeight(SC(34))

        self.dec_btn.clicked.connect(lambda: self.set_value(self._val - 1))
        self.inc_btn.clicked.connect(lambda: self.set_value(self._val + 1))
        self._refresh()

    def _refresh(self):
        self.val_lbl.setText(f"{self._val}{self._suffix}")

    def value(self):
        return self._val

    def set_value(self, v):
        v = max(self._min, min(self._max, v))
        self._val = v
        self._refresh()


class SegmentedControl(QWidget):
    """Dil secimi gibi az sayida secenek arasinda gecis icin segment kontrolu."""

    def __init__(self, options, current=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        for i, opt in enumerate(options):
            b = QPushButton(opt)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(SC(34))
            b.setMinimumWidth(SC(96))
            radius_l = "8px" if i == 0 else "0px"
            radius_r = "8px" if i == len(options) - 1 else "0px"
            border_l = f"1.5px solid {BORDER_COLOR}" if i == 0 else "none"
            b.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_MAIN}; color: {TEXT_FAINT};
                    border-top: 1.5px solid {BORDER_COLOR}; border-bottom: 1.5px solid {BORDER_COLOR};
                    border-right: 1.5px solid {BORDER_COLOR}; border-left: {border_l};
                    border-top-left-radius: {radius_l}; border-bottom-left-radius: {radius_l};
                    border-top-right-radius: {radius_r}; border-bottom-right-radius: {radius_r};
                    font-size: {SF(12)}px; font-weight: 700;
                }}
                QPushButton:checked {{ background-color: {ACCENT_PRIMARY_DIM}; color: {ACCENT_PRIMARY}; }}
                QPushButton:hover:!checked {{ color: {TEXT_PRIMARY}; }}
            """)
            layout.addWidget(b)
            self.group.addButton(b, i)
            self.buttons[opt] = b
        if current in self.buttons:
            self.buttons[current].setChecked(True)
        elif options:
            self.buttons[options[0]].setChecked(True)

    def current_text(self):
        b = self.group.checkedButton()
        return b.text() if b else ""

    def set_current_text(self, text):
        if text in self.buttons:
            self.buttons[text].setChecked(True)


# ============================================================================
#  Ana Pencere
# ============================================================================

NAV_ITEMS = [
    ("home", "home", "Ana Sayfa", "Bot durumu ve işlem özeti"),
    ("excel", "grid", "Excel Düzenleyici", "Kesinti verilerini görüntüleyin ve düzenleyin"),
    ("settings", "gear", "Ayarlar", "Uygulama tercihlerini yönetin"),
    ("license", "shield", "Lisans", "Donanım kimliği ve lisans durumu"),
    ("creds", "key", "Şifreler", "SGK giriş bilgilerini yönetin"),
    ("about", "info", "Hakkında", "Sürüm ve özellik bilgisi"),
]


class SGKApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{UYGULAMA_ADI} v{SURUM}")
        self.setMinimumSize(SC(1040), SC(700))
        self.resize(SC(1140), SC(780))
        base = _taban_dizin()
        for icon_candidate in ["app_logo.ico", os.path.join("docs", "app_logo.ico")]:
            icon_path = os.path.join(base, icon_candidate)
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                break
        self.hardware_id = get_hardware_id()
        self.bot_thread = None
        self.is_authorized = False
        self._stat_total = 0
        self._stat_success = 0
        self._stat_error = 0
        self._apply_global_style()

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._create_sidebar())

        main_col = QVBoxLayout()
        main_col.setContentsMargins(0, 0, 0, 0)
        main_col.setSpacing(0)
        main_col.addWidget(self._create_topbar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_home_page())
        self.pages.addWidget(self._create_excel_editor_page())
        self.pages.addWidget(self._create_settings_page())
        self.pages.addWidget(self._create_license_page())
        self.pages.addWidget(self._create_credentials_page())
        self.pages.addWidget(self._create_about_page())
        main_col.addWidget(self.pages, 1)

        root.addLayout(main_col, 1)

        self._navigate_to(0)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        self._load_settings()
        self._startup_license_check()
        QTimer.singleShot(2000, self._check_for_updates)

    # ---------------- global style ----------------
    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {BG_MAIN}; }}
            QWidget {{ background-color: transparent; color: {TEXT_PRIMARY}; font-family: '{UI_FONT}'; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: {BG_SIDEBAR}; width: 12px; border-radius: 6px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {BORDER_COLOR}; border-radius: 5px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {ACCENT_PRIMARY}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar:horizontal {{ background: {BG_SIDEBAR}; height: 12px; border-radius: 6px; margin: 2px; }}
            QScrollBar::handle:horizontal {{ background: {BORDER_COLOR}; border-radius: 5px; min-width: 30px; }}
            QScrollBar::handle:horizontal:hover {{ background: {ACCENT_PRIMARY}; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
            QLineEdit {{
                background-color: {INPUT_BG}; color: {TEXT_PRIMARY};
                border: 1.5px solid {BORDER_COLOR}; border-radius: 8px;
                padding: 10px 12px; font-size: {SF(13)}px;
                selection-background-color: {ACCENT_PRIMARY}; selection-color: #1a1509;
            }}
            QLineEdit:focus {{ border: 1.5px solid {ACCENT_PRIMARY}; }}
            QLineEdit:read-only {{ background-color: {BG_SIDEBAR}; color: {ACCENT_SECONDARY}; }}
            QTextEdit {{
                background-color: {BG_SIDEBAR}; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR}; border-radius: 9px; padding: 10px;
                font-family: '{MONO_FONT}'; font-size: {SF(12)}px;
            }}
            QTableWidget {{
                background-color: {BG_SIDEBAR}; color: {TEXT_PRIMARY};
                border: none; gridline-color: {BORDER_SOFT}; font-size: {SF(12.5)}px;
                selection-background-color: {ACCENT_PRIMARY_DIM}; selection-color: {TEXT_PRIMARY};
            }}
            QTableWidget::item {{ padding: 5px 12px; border-bottom: 1px solid {BORDER_SOFT}; }}
            QTableWidget::item:selected {{ background-color: {ACCENT_PRIMARY_DIM}; }}
            QHeaderView::section {{
                background-color: {BG_MAIN}; color: {ACCENT_PRIMARY};
                border: none; border-bottom: 2px solid {ACCENT_PRIMARY};
                padding: 8px 12px; font-size: {SF(12)}px; font-weight: 700;
            }}
            QMessageBox {{ background-color: {BG_CARD}; }}
            QMessageBox QLabel {{ color: {TEXT_PRIMARY}; font-size: {SF(13)}px; }}
            QMessageBox QPushButton {{
                background-color: {ACCENT_PRIMARY}; color: #1a1509; border: none;
                border-radius: 6px; padding: 8px 18px; font-size: {SF(13)}px; min-width: 76px; font-weight: 700;
            }}
            QMessageBox QPushButton:hover {{ background-color: {ACCENT_SECONDARY}; color: {TEXT_PRIMARY}; }}
        """)

    # ---------------- sidebar ----------------
    def _create_sidebar(self):
        bar = QFrame()
        bar.setFixedWidth(SC(216))
        bar.setStyleSheet(f"background-color: {BG_SIDEBAR}; border-right: 1px solid {BORDER_SOFT};")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(SC(12), SC(18), SC(12), SC(14))
        layout.setSpacing(SC(2))

        brand = QHBoxLayout()
        brand.setSpacing(SC(10))
        mark = QLabel()
        mark.setFixedSize(SC(32), SC(32))
        mark.setAlignment(Qt.AlignCenter)
        mark.setStyleSheet(f"""
            background-color: {ACCENT_PRIMARY}; border-radius: 9px;
        """)
        mark_icon = QLabel(mark)
        mark_icon.setPixmap(icon("shield", "#171310", 17).pixmap(17, 17))
        mark_icon.move(SC(8), SC(8))
        brand.addWidget(mark)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        name_lbl = QLabel("E-Kesinti")
        name_lbl.setStyleSheet(f"font-weight: 700; font-size: {SF(13.5)}px; background: transparent;")
        ver_lbl = QLabel(f"Geliştirici: {SIRKET}")
        ver_lbl.setStyleSheet(f"font-size: {SF(10)}px; color: {TEXT_FAINT}; background: transparent;")
        brand_text.addWidget(name_lbl)
        brand_text.addWidget(ver_lbl)
        brand.addLayout(brand_text)
        brand.addStretch()

        brand_wrap = QWidget()
        brand_wrap.setLayout(brand)
        layout.addWidget(brand_wrap)
        layout.addSpacing(SC(14))

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = {}
        for i, (key, ic, label, _sub) in enumerate(NAV_ITEMS):
            btn = NavButton(label, ic)
            btn.clicked.connect(lambda checked, idx=i: self._navigate_to(idx))
            self.nav_group.addButton(btn, i)
            layout.addWidget(btn)
            self.nav_buttons[key] = btn

        layout.addStretch()

        self.license_chip = QFrame()
        self.license_chip.setObjectName("LicenseChip")
        self.license_chip.setStyleSheet(f"""
            QFrame#LicenseChip {{ background-color: {WARNING_DIM}; border: 1px solid {WARNING_BORDER}; border-radius: 9px; }}
        """)
        chip_layout = QHBoxLayout(self.license_chip)
        chip_layout.setContentsMargins(SC(10), SC(9), SC(10), SC(9))
        chip_layout.setSpacing(SC(8))
        self.license_chip_icon = IconGlyph("alert", WARNING, 14)
        chip_layout.addWidget(self.license_chip_icon)
        chip_text = QVBoxLayout()
        chip_text.setSpacing(0)
        self.license_chip_t1 = QLabel("Lisans kontrol ediliyor…")
        self.license_chip_t1.setStyleSheet(f"font-size: {SF(11)}px; font-weight: 700; color: {WARNING}; background: transparent;")
        self.license_chip_t1.setWordWrap(True)
        self.license_chip_t2 = QLabel(" ")
        self.license_chip_t2.setStyleSheet(f"font-size: {SF(9.5)}px; color: {TEXT_FAINT}; background: transparent;")
        chip_text.addWidget(self.license_chip_t1)
        chip_text.addWidget(self.license_chip_t2)
        chip_layout.addLayout(chip_text, 1)
        layout.addWidget(self.license_chip)

        return bar

    # ---------------- topbar ----------------
    def _create_topbar(self):
        bar = QFrame()
        bar.setFixedHeight(SC(56))
        bar.setStyleSheet(f"background-color: {BG_MAIN}; border-bottom: 1px solid {BORDER_SOFT};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(SC(24), 0, SC(24), 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        self.pt_title = QLabel("Ana Sayfa")
        self.pt_title.setStyleSheet(f"font-weight: 700; font-size: {SF(15.5)}px; background: transparent;")
        self.pt_sub = QLabel("Bot durumu ve işlem özeti")
        self.pt_sub.setStyleSheet(f"font-size: {SF(11)}px; color: {TEXT_FAINT}; background: transparent;")
        title_col.addWidget(self.pt_title)
        title_col.addWidget(self.pt_sub)
        layout.addLayout(title_col)
        layout.addStretch()

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setFont(QFont(MONO_FONT, SF(12), QFont.Bold))
        self.clock_label.setStyleSheet(f"""
            color: {ACCENT_PRIMARY}; background-color: {ACCENT_PRIMARY_DIM};
            border: 1px solid {ACCENT_PRIMARY_BORDER}; border-radius: 7px; padding: 5px 12px;
        """)
        layout.addWidget(self.clock_label)
        return bar

    def _navigate_to(self, index):
        self.pages.setCurrentIndex(index)
        _key, _ic, title, sub = NAV_ITEMS[index]
        self.pt_title.setText(title)
        self.pt_sub.setText(sub)
        for i, (key, *_r) in enumerate(NAV_ITEMS):
            self.nav_buttons[key].setChecked(i == index)

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    # ---------------- Ana Sayfa ----------------
    def _create_home_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(SC(24), SC(18), SC(24), SC(16))
        outer.setSpacing(SC(14))

        stat_row = QHBoxLayout()
        stat_row.setSpacing(SC(12))
        self.stat_total = StatCard("Toplam Kayıt", "0", ACCENT_PRIMARY)
        self.stat_success = StatCard("Başarılı", "0", SUCCESS)
        self.stat_error = StatCard("Hatalı", "0", ERROR)
        self.stat_ratio = RingStat("Başarı Oranı", 0, SUCCESS)
        for w in (self.stat_total, self.stat_success, self.stat_error, self.stat_ratio):
            stat_row.addWidget(w, 1)
        outer.addLayout(stat_row)

        grid = QHBoxLayout()
        grid.setSpacing(SC(14))

        left_col = QVBoxLayout()
        left_col.setSpacing(SC(14))

        card_excel = CardFrame()
        ce = QVBoxLayout(card_excel)
        ce.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        ce.setSpacing(SC(10))
        ce.addWidget(self._section_title("folder", "Excel Dosyası"))

        filerow = QFrame()
        filerow.setObjectName("FileRow")
        filerow.setStyleSheet(f"QFrame#FileRow {{ background-color: {BG_MAIN}; border: 1.5px dashed {BORDER_COLOR}; border-radius: 9px; }}")
        fr = QHBoxLayout(filerow)
        fr.setContentsMargins(SC(12), SC(10), SC(12), SC(10))
        fr.setSpacing(SC(8))
        fr.addWidget(IconGlyph("grid", TEXT_FAINT, 15))
        self.excel_path_input = QLineEdit()
        self.excel_path_input.setPlaceholderText("Excel dosyasını seçin veya sürükleyip bırakın…")
        self.excel_path_input.setStyleSheet(f"border: none; background: transparent; font-family:'{MONO_FONT}'; font-size:{SF(12)}px;")
        fr.addWidget(self.excel_path_input, 1)
        ce.addWidget(filerow)

        self.browse_btn = StyledButton("Gözat / Sürükle-Bırak", ACCENT_PRIMARY, "#1a1509", ic="folder")
        self.browse_btn.clicked.connect(self._browse_file)
        ce.addWidget(self.browse_btn)
        left_col.addWidget(card_excel)

        card_login = CardFrame()
        cg = QVBoxLayout(card_login)
        cg.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        cg.setSpacing(SC(10))
        cg.addWidget(self._section_title("key", "SGK Girişi"))

        self.login_combo = QComboBox()
        self.login_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {BG_MAIN}; border: 1.5px solid {BORDER_COLOR}; border-radius: 9px;
                padding: 8px 10px; font-size: {SF(12)}px; color: {TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {BG_MAIN}; color: {TEXT_PRIMARY}; selection-background-color: {ACCENT_PRIMARY_DIM};
            }}
        """)
        cg.addWidget(self.login_combo)

        login_hint = QLabel("Seçilen kullanıcı kodu/şifre SGK giriş sayfasına otomatik yazılır — Güvenlik Anahtarını (resimdeki kodu) siz gireceksiniz.")
        login_hint.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(10.5)}px; background: transparent;")
        login_hint.setWordWrap(True)
        cg.addWidget(login_hint)

        left_col.addWidget(card_login)
        QTimer.singleShot(100, self._refresh_login_combo)

        card_action = CardFrame()
        ca = QVBoxLayout(card_action)
        ca.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        ca.setSpacing(SC(10))
        ca.addWidget(self._section_title("play", "İşlem Kontrol"))

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(SC(26))
        self.progress_bar.setFormat("Hazır")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {BORDER_COLOR}; border-radius: 7px; text-align: center;
                background-color: {BG_MAIN}; color: {TEXT_PRIMARY}; font-size: {SF(11)}px; font-weight: 700;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {ACCENT_SECONDARY}, stop:1 {ACCENT_PRIMARY});
                border-radius: 6px;
            }}
        """)
        ca.addWidget(self.progress_bar)

        self.progress_caption = QLabel("Bot bekleniyor")
        self.progress_caption.setStyleSheet(f"font-size: {SF(11)}px; color: {TEXT_FAINT}; background: transparent;")
        ca.addWidget(self.progress_caption)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SC(10))
        self.start_btn = StyledButton("Botu Başlat", SUCCESS, "#0d1e16", ic="play")
        self.start_btn.clicked.connect(self._start_bot)
        self.stop_btn = StyledButton("Durdur", ERROR, "#22100c", ic="stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_bot)
        btn_row.addWidget(self.start_btn, 1)
        btn_row.addWidget(self.stop_btn, 1)
        ca.addLayout(btn_row)
        left_col.addWidget(card_action)
        left_col.addStretch()

        grid.addLayout(left_col, 11)

        card_log = CardFrame()
        cl = QVBoxLayout(card_log)
        cl.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        cl.setSpacing(SC(10))
        log_head = QHBoxLayout()
        log_head.addWidget(self._section_title("clock", "İşlem Logu"))
        log_head.addStretch()
        clear_btn = GhostButton("Temizle", ic="trash", small=True)
        clear_btn.clicked.connect(self._clear_log)
        log_head.addWidget(clear_btn)
        cl.addLayout(log_head)

        self.log_scroll = QScrollArea()
        self.log_scroll.setWidgetResizable(True)
        self.log_scroll.setStyleSheet(f"background-color: {BG_SIDEBAR}; border: 1px solid {BORDER_COLOR}; border-radius: 9px;")
        self.log_inner = QWidget()
        self.log_inner.setStyleSheet("background: transparent;")
        self.log_layout = QVBoxLayout(self.log_inner)
        self.log_layout.setContentsMargins(SC(6), SC(8), SC(6), SC(8))
        self.log_layout.setSpacing(SC(2))
        self.log_layout.addStretch()
        self.log_scroll.setWidget(self.log_inner)
        cl.addWidget(self.log_scroll, 1)

        grid.addWidget(card_log, 9)
        outer.addLayout(grid, 1)

        return page

    def _section_title(self, ic, text):
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SC(8))
        lay.addWidget(IconGlyph(ic, ACCENT_PRIMARY, 14))
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-weight: 700; font-size: {SF(13.5)}px; background: transparent;")
        lay.addWidget(lbl)
        lay.addStretch()
        return wrap

    # ---------------- Excel Düzenleyici ----------------
    def _create_excel_editor_page(self):
        page = QWidget()
        page.setAcceptDrops(True)
        page.dragEnterEvent = self._excel_drag_enter
        page.dropEvent = self._excel_drop_event
        layout = QVBoxLayout(page)
        layout.setContentsMargins(SC(24), SC(18), SC(24), SC(16))
        layout.setSpacing(SC(12))

        info = QFrame()
        info.setObjectName("InfoBanner")
        info.setStyleSheet(f"QFrame#InfoBanner {{ background-color: {ACCENT_PRIMARY_DIM}; border: 1px solid {ACCENT_PRIMARY_BORDER}; border-radius: 9px; }}")
        il = QHBoxLayout(info)
        il.setContentsMargins(SC(14), SC(11), SC(14), SC(11))
        il.setSpacing(SC(10))
        il.addWidget(IconGlyph("info", ACCENT_PRIMARY, 15))
        info_lbl = QLabel("Sütun düzeni: Ünvan · Kullanıcı Kodu · Matrah · Kesinti. Dosyayı bu pencereye sürükleyip bırakabilir "
                           "ya da doğrudan tablodan düzenleyebilirsiniz.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {SF(11.5)}px; background: transparent;")
        il.addWidget(info_lbl, 1)
        layout.addWidget(info)

        file_card = CardFrame()
        fc = QHBoxLayout(file_card)
        fc.setContentsMargins(SC(16), SC(12), SC(16), SC(12))
        self.excel_file_label = QLabel("Dosya seçin veya sürükleyip bırakın")
        self.excel_file_label.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(12.5)}px; background: transparent;")
        fc.addWidget(self.excel_file_label, 1)
        self.excel_open_btn = StyledButton("Dosya Aç", ACCENT_PRIMARY, "#1a1509", ic="folder")
        self.excel_open_btn.clicked.connect(self._excel_open_file)
        fc.addWidget(self.excel_open_btn)
        layout.addWidget(file_card)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(SC(8))
        self.excel_addrow_btn = GhostButton("Satır Ekle", ic="plus", small=True)
        self.excel_addrow_btn.setEnabled(False)
        self.excel_addrow_btn.clicked.connect(self._excel_add_row)
        self.excel_delrow_btn = GhostButton("Seçili Satırı Sil", ic="trash", small=True)
        self.excel_delrow_btn.setEnabled(False)
        self.excel_delrow_btn.clicked.connect(self._excel_del_row)
        self.excel_save_btn = StyledButton("Kaydet", SUCCESS, "#0d1e16", ic="save")
        self.excel_save_btn.setMinimumHeight(SC(30))
        self.excel_save_btn.setEnabled(False)
        self.excel_save_btn.clicked.connect(self._excel_save_file)
        self.excel_saveas_btn = GhostButton("Farklı Kaydet", small=True)
        self.excel_saveas_btn.setEnabled(False)
        self.excel_saveas_btn.clicked.connect(self._excel_saveas_file)
        toolbar.addWidget(self.excel_addrow_btn)
        toolbar.addWidget(self.excel_delrow_btn)
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background-color: {BORDER_COLOR};")
        toolbar.addWidget(sep)
        toolbar.addWidget(self.excel_save_btn)
        toolbar.addWidget(self.excel_saveas_btn)
        toolbar.addStretch()
        self.excel_status_label = QLabel("0 satır")
        self.excel_status_label.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(11.5)}px; background: transparent;")
        toolbar.addWidget(self.excel_status_label)
        layout.addLayout(toolbar)

        table_card = CardFrame()
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(SC(10), SC(10), SC(10), SC(10))
        self.excel_table = QTableWidget()
        self.excel_table.setColumnCount(4)
        self.excel_table.setHorizontalHeaderLabels(["Ünvan", "Kullanıcı Kodu", "Matrah", "Kesinti"])
        self.excel_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.excel_table.verticalHeader().setDefaultSectionSize(SC(32))
        self.excel_table.verticalHeader().setStyleSheet(f"""
            QHeaderView::section {{ background-color: {BG_MAIN}; color: {TEXT_FAINT}; border: none;
                border-right: 1px solid {BORDER_COLOR}; font-size: {SF(10.5)}px; }}
        """)
        self.excel_table.setAlternatingRowColors(False)
        self.excel_table.setRowCount(0)
        self.excel_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.excel_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        tcl.addWidget(self.excel_table)
        layout.addWidget(table_card, 1)

        self._excel_current_path = None
        self._excel_modified = False
        self.excel_table.itemChanged.connect(self._excel_on_modified)
        return page

    def _excel_drag_enter(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(('.xlsx', '.xls')):
                    event.acceptProposedAction()
                    return

    def _excel_drop_event(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.xlsx', '.xls')):
                self._excel_load_file(path)
                return

    def _excel_open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyası Aç", "", "Excel Dosyaları (*.xlsx *.xls);;Tüm Dosyalar (*)")
        if path:
            self._excel_load_file(path)

    def _excel_load_file(self, path):
        try:
            import pandas as pd
            df = pd.read_excel(path, header=None)
            self.excel_table.blockSignals(True)
            self.excel_table.setRowCount(0)
            self.excel_table.setColumnCount(max(df.shape[1], 4))

            default_headers = ["Ünvan", "Kullanıcı Kodu", "Matrah", "Kesinti"]
            headers = list(default_headers)
            if df.shape[0] > 0:
                row0 = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[0]]
                known = {"unvan", "tc", "tc kimlik", "tc kimlik no", "kullanici kodu", "kullanici", "matrah", "kesinti", "bag-kur", "bagkur"}
                if any(v.lower() in known for v in row0 if v):
                    for c in range(min(df.shape[1], 4)):
                        if row0[c]:
                            headers[c] = row0[c]
            self.excel_table.setHorizontalHeaderLabels(headers[:4])

            start_row = 1 if df.shape[0] > 0 else 0
            for r in range(start_row, df.shape[0]):
                self.excel_table.insertRow(self.excel_table.rowCount())
                row_idx = self.excel_table.rowCount() - 1
                for c in range(min(df.shape[1], 4)):
                    val = df.iloc[r, c]
                    if pd.notna(val):
                        txt = str(int(val)) if isinstance(val, float) and val == int(val) else str(val)
                    else:
                        txt = ""
                    item = QTableWidgetItem(txt)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.excel_table.setItem(row_idx, c, item)

            self.excel_table.blockSignals(False)
            self._excel_current_path = path
            self._excel_modified = False
            self._excel_update_labels()
            self.excel_save_btn.setEnabled(True)
            self.excel_saveas_btn.setEnabled(True)
            self.excel_addrow_btn.setEnabled(True)
            self.excel_delrow_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel okunamadı:\n{str(e)}")

    def _excel_update_labels(self):
        name = os.path.basename(self._excel_current_path) if self._excel_current_path else "Yeni"
        mod = " *" if self._excel_modified else ""
        self.excel_file_label.setText(f"{name}{mod}")
        self.excel_file_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 700; font-size: {SF(12.5)}px; background: transparent;")
        self.excel_status_label.setText(f"{self.excel_table.rowCount()} satır · {self.excel_table.columnCount()} sütun")

    def _excel_save_file(self):
        if not self._excel_current_path:
            return
        self._excel_write_to(self._excel_current_path)

    def _excel_saveas_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Farklı Kaydet", "", "Excel Dosyaları (*.xlsx);;Tüm Dosyalar (*)")
        if not path:
            return
        self._excel_write_to(path)
        self._excel_current_path = path
        self._excel_update_labels()

    def _excel_write_to(self, path):
        try:
            import pandas as pd
            headers = []
            for c in range(self.excel_table.columnCount()):
                h = self.excel_table.horizontalHeaderItem(c)
                headers.append(h.text() if h else f"Col{c}")
            data = []
            for r in range(self.excel_table.rowCount()):
                row = []
                for c in range(self.excel_table.columnCount()):
                    item = self.excel_table.item(r, c)
                    row.append(item.text() if item else "")
                data.append(row)
            df = pd.DataFrame(data, columns=headers)
            df.to_excel(path, index=False, engine='openpyxl')
            self._excel_modified = False
            self._excel_update_labels()
            QMessageBox.information(self, "Kaydedildi", f"Dosya kaydedildi:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydedilemedi:\n{str(e)}")

    def _excel_add_row(self):
        row = self.excel_table.rowCount()
        self.excel_table.insertRow(row)
        for c in range(self.excel_table.columnCount()):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignCenter)
            self.excel_table.setItem(row, c, item)
        self._excel_update_labels()

    def _excel_del_row(self):
        rows = self.excel_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Uyarı", "Silinecek satır seçin.")
            return
        for idx in sorted(rows, reverse=True):
            self.excel_table.removeRow(idx.row())
        self._excel_update_labels()

    def _excel_on_modified(self):
        if not self._excel_modified:
            self._excel_modified = True
            self._excel_update_labels()

    # ---------------- Ayarlar ----------------
    def _create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(SC(24), SC(18), SC(24), SC(16))
        layout.setSpacing(SC(14))

        card1 = CardFrame()
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(SC(18), SC(14), SC(18), SC(14))
        c1.setSpacing(0)

        row1 = self._setting_row("Otomatik güncelleme", "Uygulama başlangıcında yeni sürüm kontrol edilir")
        self.auto_update_sw = ToggleSwitch(checked=True)
        row1.layout().addWidget(self.auto_update_sw)
        c1.addWidget(row1)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background-color: {BORDER_SOFT};")
        c1.addWidget(sep)

        row2 = self._setting_row("Bildirimler", "İşlem tamamlanma bildirimleri gösterilir")
        self.notif_sw = ToggleSwitch(checked=True)
        row2.layout().addWidget(self.notif_sw)
        c1.addWidget(row2)
        layout.addWidget(card1)

        card2 = CardFrame()
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        c2.setSpacing(SC(12))
        c2.addWidget(self._section_title("clock", "Bekleme Süresi"))
        self.wait_stepper = Stepper(1, 120, 3, " sn")
        step_row = QHBoxLayout(); step_row.addWidget(self.wait_stepper); step_row.addStretch()
        c2.addLayout(step_row)
        layout.addWidget(card2)

        card3 = CardFrame()
        c3 = QVBoxLayout(card3)
        c3.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        c3.setSpacing(SC(12))
        c3.addWidget(self._section_title("info", "Dil"))
        self.lang_segmented = SegmentedControl(["Türkçe", "English"], current="Türkçe")
        lang_row = QHBoxLayout(); lang_row.addWidget(self.lang_segmented); lang_row.addStretch()
        c3.addLayout(lang_row)
        layout.addWidget(card3)

        save_btn = StyledButton("Ayarları Kaydet", ACCENT_PRIMARY, "#1a1509", ic="save")
        save_btn.setFixedWidth(SC(220))
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()
        return page

    def _setting_row(self, title, sub):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, SC(11), 0, SC(11))
        col = QVBoxLayout()
        col.setSpacing(2)
        t1 = QLabel(title)
        t1.setStyleSheet(f"font-size: {SF(13)}px; font-weight: 600; background: transparent;")
        t2 = QLabel(sub)
        t2.setStyleSheet(f"font-size: {SF(11)}px; color: {TEXT_FAINT}; background: transparent;")
        col.addWidget(t1)
        col.addWidget(t2)
        lay.addLayout(col, 1)
        return row

    # ---------------- Lisans ----------------
    def _create_license_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(SC(24), SC(18), SC(24), SC(16))
        layout.setSpacing(SC(14))

        card1 = CardFrame()
        c1 = QVBoxLayout(card1)
        c1.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        c1.setSpacing(SC(10))
        c1.addWidget(self._section_title("shield", "Donanım Kimliği (HWID)"))
        hw_row = QHBoxLayout()
        hw_row.setSpacing(SC(10))
        self.hw_id_display = QLineEdit(self.hardware_id)
        self.hw_id_display.setReadOnly(True)
        self.hw_id_display.setFont(QFont(MONO_FONT, SF(12), QFont.Bold))
        hw_row.addWidget(self.hw_id_display, 1)
        self.copy_hw_btn = StyledButton("Kopyala", ACCENT_SECONDARY, TEXT_PRIMARY, ic="copy")
        self.copy_hw_btn.setFixedWidth(SC(120))
        self.copy_hw_btn.clicked.connect(self._copy_hw_id)
        hw_row.addWidget(self.copy_hw_btn)
        c1.addLayout(hw_row)
        layout.addWidget(card1)

        card2 = CardFrame()
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        c2.setSpacing(SC(10))
        c2.addWidget(self._section_title("key", "Lisans Anahtarı"))
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("SGK-XXXX-XXXX-XXXX-XXXX formatında girin…")
        c2.addWidget(self.license_input)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SC(10))
        self.verify_btn = StyledButton("Lisans Doğrula", SUCCESS, "#0d1e16", ic="check-circle")
        self.verify_btn.clicked.connect(self._verify_license)
        self.demo_btn = StyledButton("Demo Lisans Al", WARNING, "#241505", ic="alert")
        self.demo_btn.clicked.connect(self._get_demo_license)
        btn_row.addWidget(self.verify_btn)
        btn_row.addWidget(self.demo_btn)
        btn_row.addStretch()
        c2.addLayout(btn_row)
        layout.addWidget(card2)

        self.license_status_banner = QFrame()
        self.license_status_banner.setObjectName("StatusBanner")
        self.license_status_banner.setStyleSheet(f"QFrame#StatusBanner {{ background-color: {WARNING_DIM}; border: 1px solid {WARNING_BORDER}; border-radius: 10px; }}")
        sb = QHBoxLayout(self.license_status_banner)
        sb.setContentsMargins(SC(16), SC(14), SC(16), SC(14))
        sb.setSpacing(SC(12))
        self.license_status_icon = IconGlyph("alert", WARNING, 20)
        sb.addWidget(self.license_status_icon)
        sb_text = QVBoxLayout()
        sb_text.setSpacing(3)
        self.license_info = QLabel("Lisans durumu kontrol ediliyor…")
        self.license_info.setStyleSheet(f"font-weight: 700; font-size: {SF(13.5)}px; color: {WARNING}; background: transparent;")
        self.license_info.setWordWrap(True)
        self.license_sub = QLabel(" ")
        self.license_sub.setStyleSheet(f"font-size: {SF(11)}px; color: {TEXT_FAINT}; background: transparent;")
        self.license_sub.setWordWrap(True)
        sb_text.addWidget(self.license_info)
        sb_text.addWidget(self.license_sub)
        self.days_track = QProgressBar()
        self.days_track.setRange(0, 100)
        self.days_track.setValue(0)
        self.days_track.setTextVisible(False)
        self.days_track.setFixedHeight(6)
        self.days_track.setStyleSheet(f"""
            QProgressBar {{ background-color: {BORDER_COLOR}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {WARNING}; border-radius: 3px; }}
        """)
        sb_text.addWidget(self.days_track)
        sb.addLayout(sb_text, 1)
        layout.addWidget(self.license_status_banner)
        layout.addStretch()
        return page

    # ---------------- Şifreler ----------------
    def _create_credentials_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(SC(24), SC(18), SC(24), SC(16))
        layout.setSpacing(SC(12))

        desc = QLabel("SGK giriş bilgileriniz yalnızca bu bilgisayarda, makineye özel şifrelenmiş olarak saklanır — başka bir yere gönderilmez.")
        desc.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(11.5)}px; background: transparent;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        card_add = CardFrame()
        add_l = QVBoxLayout(card_add)
        add_l.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        add_l.setSpacing(SC(10))
        add_l.addWidget(self._section_title("plus", "Yeni Şifre Ekle"))

        form = QHBoxLayout()
        form.setSpacing(SC(10))
        self.cred_name_input = QLineEdit()
        self.cred_name_input.setPlaceholderText("İsim (örn: Arda)")
        self.cred_tc_input = QLineEdit()
        self.cred_tc_input.setPlaceholderText("Kullanıcı Kodu (12 haneli)")
        self.cred_tc_input.setMaxLength(12)
        self.cred_pass_input = QLineEdit()
        self.cred_pass_input.setPlaceholderText("Şifre")
        self.cred_pass_input.setEchoMode(QLineEdit.Password)
        form.addWidget(self.cred_name_input, 1)
        form.addWidget(self.cred_tc_input, 1)
        form.addWidget(self.cred_pass_input, 1)
        add_l.addLayout(form)

        save_cred_btn = StyledButton("Kaydet", SUCCESS, "#0d1e16", ic="save")
        save_cred_btn.setFixedWidth(SC(140))
        save_cred_btn.clicked.connect(self._save_credential)
        add_l.addWidget(save_cred_btn)
        layout.addWidget(card_add)

        card_list = CardFrame()
        list_l = QVBoxLayout(card_list)
        list_l.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        list_l.setSpacing(SC(8))
        head = QHBoxLayout()
        head.addWidget(self._section_title("key", "Kayıtlı Şifreler"))
        self.cred_count_lbl = QLabel("")
        self.cred_count_lbl.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(11)}px; background: transparent;")
        head.addWidget(self.cred_count_lbl)
        head.addStretch()
        refresh_btn = GhostButton("Yenile", small=True)
        refresh_btn.clicked.connect(self._refresh_credentials_list)
        head.addWidget(refresh_btn)
        list_l.addLayout(head)

        # Kayit sayisi arttikca (10+) sabit pencere yuksekligine sigmayip
        # satirlarin ust uste binmesini onlemek icin liste kendi ic
        # kaydirma alanina sarilir (log paneliyle ayni desen).
        self.cred_scroll = QScrollArea()
        self.cred_scroll.setWidgetResizable(True)
        self.cred_scroll.setMaximumHeight(SC(360))
        self.cred_scroll.setStyleSheet(f"background-color: {BG_MAIN}; border: 1px solid {BORDER_SOFT}; border-radius: 9px;")
        cred_inner = QWidget()
        cred_inner.setStyleSheet("background: transparent;")
        self.cred_list_layout = QVBoxLayout(cred_inner)
        self.cred_list_layout.setContentsMargins(SC(8), SC(8), SC(8), SC(8))
        self.cred_list_layout.setSpacing(SC(7))
        self.cred_list_layout.addStretch()
        self.cred_scroll.setWidget(cred_inner)
        list_l.addWidget(self.cred_scroll)
        layout.addWidget(card_list)
        layout.addStretch()

        QTimer.singleShot(100, self._refresh_credentials_list)
        return page

    def _refresh_login_combo(self):
        """Kontrol Paneli'ndeki 'SGK Girişi' acilir listesini kayitli sifrelerle gunceller.
        Secili isim varsa korunmaya calisilir (liste yeniden doldurulurken kaybolmasin)."""
        onceki = self.login_combo.currentData() if self.login_combo.count() else None
        self.login_combo.blockSignals(True)
        self.login_combo.clear()
        creds = _load_credentials()
        if not creds:
            self.login_combo.addItem("Kayıtlı şifre yok — manuel giriş yapılacak", None)
        else:
            self.login_combo.addItem("Manuel giriş (otomatik doldurma)", None)
            for cred in creds:
                self.login_combo.addItem(cred.get("name", "?"), cred.get("name"))
            if onceki is not None:
                idx = self.login_combo.findData(onceki)
                if idx >= 0:
                    self.login_combo.setCurrentIndex(idx)
                else:
                    self.login_combo.setCurrentIndex(1)  # ilk kayitli sifreyi sec
            else:
                self.login_combo.setCurrentIndex(1)
        self.login_combo.blockSignals(False)

    def _secili_giris_bilgisi(self):
        """Kontrol Paneli'nde secili SGK giris bilgisini (kullanici kodu + sifre)
        dondurur; 'Manuel giriş' seciliyse veya hic kayit yoksa None doner."""
        secili_isim = self.login_combo.currentData()
        if not secili_isim:
            return None
        for cred in _load_credentials():
            if cred.get("name") == secili_isim:
                return {"kullanici_kodu": cred.get("tc", ""), "sifre": cred.get("password", "")}
        return None

    def _refresh_credentials_list(self):
        while self.cred_list_layout.count():
            item = self.cred_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        creds = _load_credentials()
        self.cred_count_lbl.setText(f"({len(creds)} kayıt)" if creds else "")

        if not creds:
            lbl = QLabel("Henüz kayıtlı şifre yok.")
            lbl.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(12)}px; padding: 6px 2px; background: transparent;")
            self.cred_list_layout.addWidget(lbl)
            self.cred_list_layout.addStretch()
            return

        for cred in creds:
            row = QFrame()
            row.setObjectName("CredRow")
            row.setMinimumHeight(SC(48))
            row.setStyleSheet(f"QFrame#CredRow {{ background-color: {BG_MAIN}; border: 1px solid {BORDER_SOFT}; border-radius: 9px; }}")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(SC(10), SC(8), SC(10), SC(8))
            rl.setSpacing(SC(12))

            name = cred.get("name", "?")
            initials = "".join([p[0].upper() for p in name.split()[:2]]) or "?"
            avatar = QLabel(initials)
            avatar.setFixedSize(SC(30), SC(30))
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet(f"background-color: {ACCENT_PRIMARY_DIM}; color: {ACCENT_PRIMARY}; border-radius: 8px; font-weight: 700; font-size: {SF(11)}px;")
            rl.addWidget(avatar)

            name_lbl = QLabel()
            name_lbl.setFixedWidth(SC(160))
            name_lbl.setStyleSheet(f"font-weight: 700; font-size: {SF(12.5)}px; background: transparent;")
            name_metrics = name_lbl.fontMetrics()
            name_lbl.setText(name_metrics.elidedText(name, Qt.ElideRight, SC(160)))
            if name_lbl.text() != name:
                name_lbl.setToolTip(name)
            rl.addWidget(name_lbl)

            # Maskeli TC ve sifre noktalari aralarinda bosluk olmadan yan yana
            # dizilince kucuk mono fontta birlesip alt cizgi/karisik gorunuyordu.
            # Noktalari bosluklu yazip sifre uzunlugunu de sabitleyerek
            # (uzunluk bilgisi sizdirmadan) hem okunakli hem guvenli hale getirir.
            tc = cred.get("tc", "")
            dots4 = "• • • •"
            masked_tc = (tc[:6] + " " + dots4 + " " + tc[-2:]) if len(tc) >= 8 else tc
            dots_pw = "• • • • • •"
            meta_lbl = QLabel(f"{masked_tc}     şifre: {dots_pw}")
            meta_lbl.setFont(QFont(MONO_FONT, SF(11)))
            meta_lbl.setStyleSheet(f"color: {TEXT_FAINT}; background: transparent;")
            rl.addWidget(meta_lbl, 1)

            del_btn = GhostButton("", ic="trash", small=True)
            del_btn.setFixedWidth(SC(34))
            del_btn.setStyleSheet(del_btn.styleSheet() + f"QPushButton {{ color: {ERROR}; }}")
            del_btn.clicked.connect(lambda _, n=name: self._delete_credential(n))
            rl.addWidget(del_btn)

            self.cred_list_layout.addWidget(row)

        self.cred_list_layout.addStretch()

    def _save_credential(self):
        name = self.cred_name_input.text().strip()
        tc = self.cred_tc_input.text().strip()
        pw = self.cred_pass_input.text().strip()

        if not name or not tc or not pw:
            QMessageBox.warning(self, "Uyarı", "Tüm alanları doldurun (İsim, Kullanıcı Kodu, Şifre).")
            return
        if len(tc) != 12 or not tc.isdigit():
            QMessageBox.warning(self, "Uyarı", "Kullanıcı Kodu 12 haneli ve sadece rakam olmalı.")
            return

        _add_credential(name, tc, pw)
        self.cred_name_input.clear()
        self.cred_tc_input.clear()
        self.cred_pass_input.clear()
        self._refresh_credentials_list()
        self._refresh_login_combo()
        QMessageBox.information(self, "Kaydedildi", f"'{name}' için SGK bilgileri kaydedildi.")

    def _delete_credential(self, name):
        cevap = QMessageBox.question(
            self, "Silme Onayı", f"'{name}' kaydını silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if cevap == QMessageBox.Yes:
            _delete_credential(name)
            self._refresh_credentials_list()
            self._refresh_login_combo()

    # ---------------- Hakkında ----------------
    def _create_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(SC(24), SC(18), SC(24), SC(16))
        layout.setSpacing(SC(14))

        card1 = CardFrame()
        c1 = QHBoxLayout(card1)
        c1.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        c1.setSpacing(SC(14))
        mark = QLabel()
        mark.setFixedSize(SC(46), SC(46))
        mark.setStyleSheet(f"background-color: {ACCENT_PRIMARY}; border-radius: 12px;")
        mark_ic = QLabel(mark)
        mark_ic.setPixmap(icon("shield", "#171310", 24).pixmap(24, 24))
        mark_ic.move(SC(11), SC(11))
        c1.addWidget(mark)
        col = QVBoxLayout()
        col.setSpacing(2)
        t1 = QLabel(UYGULAMA_ADI)
        t1.setStyleSheet(f"font-weight: 700; font-size: {SF(16)}px; background: transparent;")
        t2 = QLabel(f"Sürüm {SURUM} · Geliştirici: {SIRKET} · © 2026")
        t2.setStyleSheet(f"color: {TEXT_FAINT}; font-size: {SF(11.5)}px; background: transparent;")
        col.addWidget(t1)
        col.addWidget(t2)
        c1.addLayout(col, 1)
        layout.addWidget(card1)

        card2 = CardFrame()
        c2 = QVBoxLayout(card2)
        c2.setContentsMargins(SC(18), SC(16), SC(18), SC(16))
        c2.setSpacing(SC(10))
        c2.addWidget(self._section_title("check-circle", "Özellikler"))

        features = [
            "Otomatik SGK E-Kesinti işlemleri",
            "Excel'den toplu veri işleme",
            "Gerçek zamanlı ilerleme takibi",
            "Detaylı işlem loglama",
            "Otomatik güncelleme sistemi",
            "Makineye özel şifreli kimlik saklama",
        ]
        fgrid = QGridLayout()
        fgrid.setSpacing(SC(10))
        for i, feat in enumerate(features):
            item = QFrame()
            item.setObjectName("FeatItem")
            item.setStyleSheet(f"QFrame#FeatItem {{ background-color: {BG_MAIN}; border: 1px solid {BORDER_SOFT}; border-radius: 9px; }}")
            il = QHBoxLayout(item)
            il.setContentsMargins(SC(11), SC(10), SC(11), SC(10))
            il.setSpacing(SC(9))
            il.addWidget(IconGlyph("check-circle", SUCCESS, 14))
            lbl = QLabel(feat)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {SF(11.8)}px; background: transparent;")
            il.addWidget(lbl, 1)
            fgrid.addWidget(item, i // 2, i % 2)
        c2.addLayout(fgrid)
        layout.addWidget(card2)
        layout.addStretch()
        return page

    # ============================================================
    #  Core methods
    # ============================================================
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls);;Tüm Dosyalar (*)")
        if path:
            self.excel_path_input.setText(path)

    def _start_bot(self):
        if not self.is_authorized:
            QMessageBox.warning(self, "Yetkisiz", "Lisans doğrulaması yapılmadı. Önce lisansınızı doğrulayın.")
            return

        path = self.excel_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir Excel dosyası seçin.")
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "Uyarı", "Seçilen dosya bulunamadı.")
            return

        self._stat_total = 0
        self._stat_success = 0
        self._stat_error = 0
        self._update_stat_cards()

        giris_bilgisi = self._secili_giris_bilgisi()
        if giris_bilgisi:
            self._append_log("Bot başlatıldı… (kullanıcı kodu/şifre otomatik doldurulacak)", "info")
        else:
            self._append_log("Bot başlatıldı…", "info")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Çalışıyor… %p%")
        self.progress_caption.setText("Bot başlatılıyor…")

        self.bot_thread = BotThread(path, giris_bilgisi=giris_bilgisi)
        self.bot_thread.log_signal.connect(self._on_log)
        self.bot_thread.progress_signal.connect(self._on_progress)
        self.bot_thread.finished_signal.connect(self._on_bot_finished)
        self.bot_thread.prompt_signal.connect(self._on_bot_prompt)
        self.bot_thread.start()

    def _stop_bot(self):
        if self.bot_thread and self.bot_thread.isRunning():
            self.bot_thread.stop()
            self._append_log("Durduruluyor…", "warning")

    def _on_log(self, message):
        temiz = _temizle_log_satiri(message)
        if not temiz:
            return

        msg_lower = temiz.lower()
        if "hata" in msg_lower or "error" in msg_lower or "bulunamadi" in msg_lower or "bulunamadı" in msg_lower:
            msg_type = "error"
        elif "basari" in msg_lower or "başarı" in msg_lower or "tamamlandi" in msg_lower or "tamamlandı" in msg_lower:
            msg_type = "success"
        elif "uyari" in msg_lower or "uyarı" in msg_lower or "warning" in msg_lower or "bekleniyor" in msg_lower:
            msg_type = "warning"
        else:
            msg_type = "info"

        prog = _PROGRESS_RE.search(temiz)
        if prog:
            pct, cur, tot = int(prog.group(1)), int(prog.group(2)), int(prog.group(3))
            self.progress_bar.setValue(pct)
            self.progress_bar.setFormat(f"Çalışıyor… %p%")
            self.progress_caption.setText(f"Kayıt {cur}/{tot} işleniyor")

        summary = _SUMMARY_RE.search(temiz)
        if summary:
            success, total = int(summary.group(1)), int(summary.group(2))
            self._stat_success = success
            self._stat_total = total
            self._stat_error = max(0, total - success)
            self._update_stat_cards()

        self._append_log(temiz, msg_type)

    def _update_stat_cards(self):
        self.stat_total.set_value(self._stat_total)
        self.stat_success.set_value(self._stat_success)
        self.stat_error.set_value(self._stat_error)
        ratio = int(round(self._stat_success / self._stat_total * 100)) if self._stat_total else 0
        self.stat_ratio.set_percent(ratio)

    def _append_log(self, message, msg_type="info"):
        ts = datetime.now().strftime('%H:%M:%S')
        color_map = {"success": SUCCESS, "error": ERROR, "warning": WARNING, "info": TEXT_FAINT}
        icon_map = {"success": "check-circle", "error": "x-circle", "warning": "alert", "info": "dot"}
        color = color_map.get(msg_type, TEXT_FAINT)

        line = QWidget()
        line.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(line)
        lay.setContentsMargins(SC(8), SC(3), SC(8), SC(3))
        lay.setSpacing(SC(8))
        lay.addWidget(IconGlyph(icon_map.get(msg_type, "dot"), color, 12))
        ts_lbl = QLabel(ts)
        ts_lbl.setFont(QFont(MONO_FONT, SF(10.5)))
        ts_lbl.setStyleSheet(f"color: {TEXT_FAINT}; background: transparent;")
        lay.addWidget(ts_lbl)
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont(MONO_FONT, SF(10.8)))
        msg_lbl.setWordWrap(True)
        text_color = TEXT_PRIMARY if msg_type == "success" else TEXT_SECONDARY
        msg_lbl.setStyleSheet(f"color: {text_color}; background: transparent;")
        lay.addWidget(msg_lbl, 1)

        self.log_layout.insertWidget(self.log_layout.count() - 1, line)
        QTimer.singleShot(0, lambda: self.log_scroll.verticalScrollBar().setValue(self.log_scroll.verticalScrollBar().maximum()))

    def _clear_log(self):
        while self.log_layout.count() > 1:
            item = self.log_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _on_progress(self, value):
        self.progress_bar.setValue(value)

    def _on_bot_finished(self, status):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setFormat("Tamamlandı! %p%")
        self.progress_caption.setText("İşlem tamamlandı")
        self._append_log(status, "success")

    def _on_bot_prompt(self, mesaj, evet_hayir_mi):
        """Bot thread'i bir kullanıcı onayı bekliyor (ör. SGK'ya login olundu mu,
        hatalı kayıtlar tekrar denensin mi). Bu slot ana thread'de çalışır; bir
        dialog gösterip cevabı bot thread'ine geri iletir."""
        if not self.bot_thread:
            return
        if evet_hayir_mi:
            cevap = QMessageBox.question(
                self, "Onay Gerekli", mesaj,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            self.bot_thread.resolve_prompt(cevap == QMessageBox.Yes)
        else:
            QMessageBox.information(self, "Devam Etmek İçin Onay", mesaj)
            self.bot_thread.resolve_prompt(True)

    def _copy_hw_id(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hardware_id)
        self.copy_hw_btn.setText("Kopyalandı!")
        QTimer.singleShot(2000, lambda: self.copy_hw_btn.setText("Kopyala"))

    def _set_license_visual(self, state, title, sub, days_left=None):
        """state: 'success' | 'warning' | 'error'"""
        colors = {"success": (SUCCESS, SUCCESS_DIM, SUCCESS_BORDER, "check-circle"),
                  "warning": (WARNING, WARNING_DIM, WARNING_BORDER, "alert"),
                  "error": (ERROR, ERROR_DIM, ERROR_BORDER, "x-circle")}
        color, dim, border, ic = colors.get(state, colors["warning"])

        self.license_chip.setStyleSheet(f"QFrame#LicenseChip {{ background-color: {dim}; border: 1px solid {border}; border-radius: 9px; }}")
        self.license_chip_icon.set_kind(ic, color)
        self.license_chip_t1.setStyleSheet(f"font-size: {SF(11)}px; font-weight: 700; color: {color}; background: transparent;")
        self.license_chip_t1.setText(title)
        self.license_chip_t2.setText(sub)

        if hasattr(self, "license_status_banner"):
            self.license_status_banner.setStyleSheet(f"QFrame#StatusBanner {{ background-color: {dim}; border: 1px solid {border}; border-radius: 10px; }}")
            self.license_status_icon.set_kind(ic, color)
            self.license_info.setStyleSheet(f"font-weight: 700; font-size: {SF(13.5)}px; color: {color}; background: transparent;")
            self.license_info.setText(title)
            self.license_sub.setText(sub)
            if days_left is not None:
                self.days_track.setVisible(True)
                pct = max(0, min(100, int(days_left / DEMO_TOPLAM_GUN * 100)))
                self.days_track.setValue(pct)
                self.days_track.setStyleSheet(f"""
                    QProgressBar {{ background-color: {BORDER_COLOR}; border: none; border-radius: 3px; }}
                    QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}
                """)
            else:
                self.days_track.setVisible(False)

    def _startup_license_check(self):
        if not API_AVAILABLE:
            self.is_authorized = False
            self._set_license_visual("warning", "Lisans: Çevrimdışı", "İnternet bağlantısı gerekli")
            self.start_btn.setEnabled(False)
            self.start_btn.setText("Yetkisiz - İnternet Bağlantısı Gerekli")
            return

        self._set_license_visual("warning", "Lisans: Kontrol ediliyor...", "Sunucuya baglaniliyor")
        self.start_btn.setEnabled(False)
        self._lisans_thread = _LisansSorgu(self.hardware_id)
        self._lisans_thread.bitti.connect(self._lisans_sonucu_uygula)
        self._lisans_thread.start()

    def _lisans_sonucu_uygula(self, result):
        """Arka plan lisans sorgusu bitince sonucu arayuze uygula (GUI basligi)."""
        try:
            if not isinstance(result, dict):
                raise ValueError("gecersiz lisans yaniti")
            self.is_authorized = result.get("authorized", False)
            admin_ok = result.get("admin_authorized", False)
            days_left = result.get("demo_days_left", 0)

            if self.is_authorized:
                if admin_ok:
                    self._set_license_visual("success", "Lisans: Aktif (Sunucu)", "Sunucu tarafından doğrulandı")
                else:
                    self._set_license_visual("warning", f"Demo · {days_left} gün kaldı", "Süre bitiminde yönetici onayı gerekir", days_left)
                self.start_btn.setEnabled(True)
                self.start_btn.setText("Botu Başlat")
            else:
                msg = result.get("message", "Yetkisiz")
                self._set_license_visual("error", f"Lisans: {msg}", "Admin panelinden yetkilendirme gerekir")
                self.start_btn.setEnabled(False)
                self.start_btn.setText("Yetkisiz - Admin ile İletişime Geçin")
        except Exception:
            self.is_authorized = False
            self._set_license_visual("warning", "Lisans: Bağlantı Hatası", "Sunucuya ulaşılamadı")
            self.start_btn.setEnabled(False)
            self.start_btn.setText("Bağlantı Hatası - Tekrar Deneyin")

    def _check_for_updates(self):
        if not hasattr(self, 'auto_update_sw') or not self.auto_update_sw.isChecked():
            return
        try:
            yeni_surum, zip_url = _guncelleme_var_mi()
            if not yeni_surum or not zip_url:
                return
            cevap = QMessageBox.question(
                self, "Güncelleme Mevcut",
                f"Yeni sürüm bulundu: v{yeni_surum}\nMevcut sürüm: v{SURUM}\n\nŞimdi güncellensin mi?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if cevap == QMessageBox.Yes:
                QMessageBox.information(self, "Güncelleme", "Yeni sürüm indiriliyor... Lütfen bekleyin.")
                _otomatik_guncelle(zip_url)
                QMessageBox.information(self, "Güncelleme Tamamlandı", f"v{yeni_surum} başarıyla yüklendi!\nUygulama yeniden başlatılacak.")
                script_yol = os.path.abspath(__file__)
                subprocess.Popen([sys.executable, script_yol] + sys.argv[1:])
                sys.exit(0)
        except Exception as e:
            QMessageBox.warning(self, "Güncelleme Hatası", f"Güncelleme başarısız: {e}\n\nManuel güncelleme için siteden ZIP indirin.")

    def _verify_license(self):
        key = self.license_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Uyarı", "Lisans anahtarı boş olamaz.")
            return
        if not API_AVAILABLE:
            QMessageBox.warning(self, "Bağlantı Hatası", "Sunucuya ulaşılamıyor. Lisans doğrulaması için internet bağlantısı gerekli.")
            return
        try:
            result = register_and_check(self.hardware_id)
            self.is_authorized = result.get("authorized", False)
            admin_ok = result.get("admin_authorized", False)
            days_left = result.get("demo_days_left", 0)

            if self.is_authorized:
                if admin_ok:
                    self._set_license_visual("success", "Lisans: Aktif (Sunucu)", "Sunucu tarafından doğrulandı")
                    QMessageBox.information(self, "Başarılı", "Lisans doğrulandı!\nTüm özellikler aktif.")
                else:
                    self._set_license_visual("warning", "Lisans: Demo", f"{days_left} gün kaldı — süre bitince admin onayı gerekir", days_left)
                    QMessageBox.information(self, "Demo Lisans", f"Demo lisans aktif!\n\n{days_left} gün kaldı. Süre bitince admin onayı gerekir.")
            else:
                msg = result.get("message", "HWID yetkisiz")
                self._set_license_visual("error", "Lisans: Yetkisiz", msg)
                QMessageBox.warning(self, "Yetkisiz", f"{msg}\n\nDemo süresi doldu veya yetki verilmedi.\nAdmin panelinden yetkilendirme gerektirir.")
        except Exception as e:
            self.is_authorized = False
            QMessageBox.warning(self, "Hata", f"Sunucu bağlantısı hatası:\n{str(e)}")

    def _get_demo_license(self):
        self.license_input.setText(DEMO_LISANS)
        QMessageBox.information(self, "Demo Lisans", f"Demo lisans anahtarı yüklendi:\n\n{DEMO_LISANS}\n\nDoğrulama için 'Lisans Doğrula' butonuna basın.")

    def _save_settings(self):
        settings = {
            "auto_update": self.auto_update_sw.isChecked(),
            "notifications": self.notif_sw.isChecked(),
            "wait_time": self.wait_stepper.value(),
            "language": self.lang_segmented.current_text(),
        }
        settings_path = os.path.join(_taban_dizin(), "settings.json")
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Kaydedildi", "Ayarlar başarıyla kaydedildi.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ayarlar kaydedilemedi:\n{str(e)}")

    def _load_settings(self):
        settings_path = os.path.join(_taban_dizin(), "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.auto_update_sw.setChecked(settings.get("auto_update", True))
                self.notif_sw.setChecked(settings.get("notifications", True))
                self.wait_stepper.set_value(settings.get("wait_time", 3))
                lang = settings.get("language", "Türkçe")
                self.lang_segmented.set_current_text(lang)
            except Exception:
                pass

    def closeEvent(self, event):
        if self.bot_thread and self.bot_thread.isRunning():
            reply = QMessageBox.question(
                self, "Çıkış Onayı", "Bot hâlâ çalışıyor. Çıkmak istediğinize emin misiniz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.bot_thread.stop()
                self.bot_thread.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("sgk.ekiz.otomasyon")
    except Exception:
        pass

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    base = _taban_dizin()
    for icon_candidate in ["app_logo.ico", os.path.join("docs", "app_logo.ico")]:
        icon_path = os.path.join(base, icon_candidate)
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            break

    font = QFont(UI_FONT, int(11 * _scale))
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    window = SGKApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()