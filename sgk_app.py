"""
SGK E-Kesinti Otomasyon v1.7.3
Arda Yazilim - Profesyonel PyQt5 GUI
"""

import sys
import os
import hashlib
import uuid
import platform
import subprocess
import time
import json
import re
import urllib.request
import urllib.error
import zipfile
import base64
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QLineEdit,
    QProgressBar, QTextEdit, QFileDialog, QCheckBox, QSpinBox,
    QComboBox, QMessageBox, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect,
    QDesktopWidget
)

# API Client import (opsiyonel - Worker entegrasyonu icin)
try:
    from api_client import register_and_check, check_authorization, WORKER_URL
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QPen

# --- Sabitler ---
SURUM = "1.7.22"
UYGULAMA_ADI = "SGK E-Kesinti Otomasyon"
SIRKET = "Arda Yazilim"

# --- DPI scale faktör (yüksek çözünürlüklü ekranlarda arayüzü dogur ogulmesi icin) ---
try:
    import ctypes
    _scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0 if hasattr(ctypes, "windll") else 1.0
except Exception:
    _scale = 1.0
SC = lambda v: int(round(v * _scale))
SF = lambda v: int(round(v * _scale))

# --- Renkler (Resmi Siyah-Bez Palette) ---
BG_MAIN = "#1a1a1a"
BG_CARD = "#2d2d2d"
BG_HEADER = "#111111"
ACCENT_PRIMARY = "#c9a86c"
ACCENT_SECONDARY = "#8b7355"
SUCCESS = "#4caf50"
ERROR = "#f44336"
WARNING = "#ff9800"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#cccccc"
BORDER_COLOR = "#404040"
INPUT_BG = "#1a1a1a"
NAV_BG = "#111111"
NAV_ACTIVE = "#c9a86c"

# --- Demo Lisans ---
DEMO_LISANS = "SGK-DEMO0001-2025-ARDA-2026"

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
    hedef_klasor = os.path.dirname(os.path.abspath(__file__))
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
    """XOR tabanli sifreleme/Cozme (simetrik)."""
    key_len = len(key)
    return bytes([b ^ key[i % key_len] for i, b in enumerate(data)])


def _save_credentials(credentials):
    """Kimlik bilgilerini makineye ozel sifreli dosyaya kaydeder."""
    key = _get_machine_key()
    raw = json.dumps(credentials, ensure_ascii=False).encode("utf-8")
    encrypted = _xor_crypt(raw, key)
    b64 = base64.b64encode(encrypted).decode("ascii")
    cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _CRED_FILE)
    with open(cred_path, "w", encoding="utf-8") as f:
        f.write(b64)


def _load_credentials():
    """Sifreli dosyadan kimlik bilgilerini okur. Dosya yoksa veya bozuksa bos doner."""
    cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), _CRED_FILE)
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
    # Mevcut ayni isimde kaydi kaldir
    creds = [c for c in creds if c.get("name") != name]
    creds.append({"name": name, "tc": tc_no, "password": password})
    _save_credentials(creds)


def _delete_credential(name):
    """Belirli bir kimlik bilgisini siler."""
    creds = _load_credentials()
    creds = [c for c in creds if c.get("name") != name]
    _save_credentials(creds)


# --- Bot Thread ---
class BotThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)

    def __init__(self, excel_path, parent=None):
        super().__init__(parent)
        self.excel_path = excel_path
        self._running = True

    def run(self):
        self.log_signal.emit("Bot baslatiliyor...")
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import sgk_bot
            self.log_signal.emit("sgk_bot modulu yuklendi.")
            if hasattr(sgk_bot, 'main'):
                sgk_bot.main(self.excel_path, self.log_signal.emit, self.progress_signal, lambda: self._running)
            else:
                self.log_signal.emit("Uyari: sgk_bot.main() fonksiyonu bulunamadi.")
                self._simulate_work()
        except ImportError:
            self.log_signal.emit("sgk_bot.py bulunamadi, demo mod calistiriliyor...")
            self._simulate_work()
        except Exception as e:
            self.log_signal.emit(f"Hata: {str(e)}")
        finally:
            self.finished_signal.emit("Tamamlandi")

    def _simulate_work(self):
        for i in range(101):
            if not self._running:
                self.log_signal.emit("Durduruldu.")
                break
            self.progress_signal.emit(i)
            if i % 20 == 0 and i > 0:
                self.log_signal.emit(f"Islem devam ediyor... %{i}")
            time.sleep(0.05)

    def stop(self):
        self._running = False


# --- Styled Button ---
class StyledButton(QPushButton):
    def __init__(self, text, color=ACCENT_PRIMARY, parent=None):
        super().__init__(text, parent)
        self.base_color = color
        self.setMinimumHeight(48)
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.base_color};
                color: #1a1a1a;
                border: 2px solid {self.base_color};
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_SECONDARY};
                border-color: {ACCENT_SECONDARY};
            }}
            QPushButton:pressed {{
                background-color: #6d5a3a;
            }}
            QPushButton:disabled {{
                background-color: {BORDER_COLOR};
                color: #666666;
                border-color: {BORDER_COLOR};
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)

    def set_color(self, color):
        self.base_color = color
        self._update_style()


# --- Nav Button ---
class NavButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style(False)

    def _update_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(201, 168, 108, 0.2);
                    color: #c9a86c;
                    border: none;
                    border-radius: 6px;
                    margin: 2px 4px;
                    font-size: 13px;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: #999999;
                    border: none;
                    border-radius: 6px;
                    margin: 2px 4px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    color: #ffffff;
                    background-color: rgba(201, 168, 108, 0.1);
                }}
            """)

    def setChecked(self, checked):
        super().setChecked(checked)
        self._update_style(checked)


# --- Card Frame ---
class CardFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #242424;
                border: 1px solid #333333;
                border-radius: 10px;
            }}
        """)


# --- Stat Card Widget ---
class StatCard(QFrame):
    def __init__(self, title, value, color, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(90)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #242424;
                border: 1px solid #333333;
                border-left: 4px solid {color};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: #999999; font-size: 13px; font-weight: normal; background: transparent; border: none;")
        layout.addWidget(title_lbl)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(self.value_lbl)

    def set_value(self, v):
        self.value_lbl.setText(str(v))


# --- Main Window ---
class SGKApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{UYGULAMA_ADI} v{SURUM}")
        self.setMinimumSize(1000, 700)
        self.resize(1100, 780)
        self.hardware_id = get_hardware_id()
        self.bot_thread = None
        self.is_authorized = False
        self._apply_global_style()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self._create_top_bar())

        content_area = QHBoxLayout()
        content_area.setContentsMargins(0, 0, 0, 0)
        content_area.setSpacing(0)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_home_page())
        self.pages.addWidget(self._create_settings_page())
        self.pages.addWidget(self._create_license_page())
        self.pages.addWidget(self._create_credentials_page())
        self.pages.addWidget(self._create_about_page())
        content_area.addWidget(self.pages, 1)

        main_layout.addLayout(content_area, 1)
        main_layout.addWidget(self._create_status_bar())
        main_layout.addWidget(self._create_bottom_bar())

        self.nav_buttons = []
        self._update_nav(0)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        self._load_settings()

        # Startup: HWID + IP kaydet ve yetki kontrol et (widget'lar kurulduktan sonra)
        self._startup_license_check()

        # Otomatik guncelleme kontrolu (UI tam yuklendikten sonra)
        QTimer.singleShot(2000, self._check_for_updates)

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {BG_MAIN};
            }}
            QWidget {{
                background-color: transparent;
                color: {TEXT_PRIMARY};
            }}
            QScrollBar:vertical {{
                background: {NAV_BG};
                width: 14px;
                border-radius: 7px;
                margin: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {BORDER_COLOR};
                border-radius: 6px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {ACCENT_PRIMARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {NAV_BG};
                height: 14px;
                border-radius: 7px;
                margin: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {BORDER_COLOR};
                border-radius: 6px;
                min-width: 40px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {ACCENT_PRIMARY};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QLineEdit {{
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px 14px;
                font-size: 14px;
                selection-background-color: {ACCENT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 2px solid {ACCENT_PRIMARY};
            }}
            QLineEdit:read-only {{
                background-color: {NAV_BG};
            }}
            QTextEdit {{
                background-color: #111111;
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
            }}
            QComboBox {{
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                min-height: 24px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 36px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 7px solid {TEXT_SECONDARY};
                margin-right: 12px;
            }}
            QComboBox:hover {{
                border: 2px solid {ACCENT_PRIMARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {NAV_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_COLOR};
                border-radius: 4px;
                selection-background-color: {ACCENT_PRIMARY};
                padding: 6px;
                font-size: 14px;
            }}
            QSpinBox {{
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
            }}
            QSpinBox:focus {{
                border: 2px solid {ACCENT_PRIMARY};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {BORDER_COLOR};
                border: none;
                width: 24px;
            }}
            QCheckBox {{
                spacing: 12px;
                font-size: 14px;
                color: {TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 4px;
                border: 2px solid {BORDER_COLOR};
                background-color: {INPUT_BG};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT_PRIMARY};
                border-color: {ACCENT_PRIMARY};
            }}
            QProgressBar {{
                border: 2px solid {BORDER_COLOR};
                border-radius: 8px;
                text-align: center;
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                font-size: 14px;
                font-weight: bold;
                min-height: 32px;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT_PRIMARY};
                border-radius: 6px;
            }}
            QMessageBox {{
                background-color: {BG_CARD};
            }}
            QMessageBox QLabel {{
                color: {TEXT_PRIMARY};
                font-size: 14px;
            }}
            QMessageBox QPushButton {{
                background-color: {ACCENT_PRIMARY};
                color: #1a1a1a;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {ACCENT_SECONDARY};
            }}
        """)

    def _create_top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border-bottom: 1px solid #333333;
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        title_icon = QLabel("SGK")
        title_icon.setStyleSheet(f"""
            color: #c9a86c;
            font-size: 16px;
            font-weight: bold;
            background: transparent;
            padding: 4px 10px;
            border: 2px solid #c9a86c;
            border-radius: 6px;
        """)
        layout.addWidget(title_icon)

        title = QLabel(UYGULAMA_ADI)
        title.setStyleSheet(f"color: #ffffff; font-size: 15px; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        ver_label = QLabel(f"v{SURUM}")
        ver_label.setStyleSheet(f"color: #888888; font-size: 12px; background: transparent;")
        layout.addWidget(ver_label)

        layout.addStretch()

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setStyleSheet(f"""
            color: #c9a86c;
            background-color: rgba(201, 168, 108, 0.1);
            border: 1px solid rgba(201, 168, 108, 0.3);
            border-radius: 6px;
            padding: 4px 12px;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Consolas', monospace;
        """)
        layout.addWidget(self.clock_label)

        self.license_status = QLabel("Lisans: Demo")
        self.license_status.setStyleSheet(f"""
            color: #ff9800;
            background-color: rgba(255, 152, 0, 0.1);
            border: 1px solid rgba(255, 152, 0, 0.3);
            border-radius: 6px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: bold;
        """)
        layout.addWidget(self.license_status)

        layout.addStretch()

        return bar

    def _create_bottom_bar(self):
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border-top: 1px solid #333333;
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(6)

        nav_data = [
            ("Ana Sayfa", 0),
            ("Ayarlar", 1),
            ("Lisans", 2),
            ("Sifreler", 3),
            ("Hakkinda", 4),
        ]
        self.nav_buttons = []
        for text, idx in nav_data:
            btn = NavButton(text)
            btn.clicked.connect(lambda checked, i=idx: self._navigate_to(i))
            layout.addWidget(btn, 1)
            self.nav_buttons.append(btn)

        return bar

    def _create_status_bar(self):
        bar = QFrame()
        bar.setFixedHeight(28)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: #141414;
                border-top: 1px solid #2a2a2a;
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        status_text = QLabel(f"Hazir | Son guncelleme: {datetime.now().strftime('%d.%m.%Y')} | v{SURUM}")
        status_text.setStyleSheet(f"color: #666666; font-size: 11px; background: transparent;")
        layout.addWidget(status_text)

        layout.addStretch()

        return bar

    def _navigate_to(self, index):
        self.pages.setCurrentIndex(index)
        self._update_nav(index)

    def _update_nav(self, active_index):
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == active_index)

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))

    # --- Home Page ---
    def _create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(16)

        header = QLabel("Ana Sayfa")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: #c9a86c; background: transparent;")
        layout.addWidget(header)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.stat_total = StatCard("Toplam Islem", "0", "#c9a86c")
        stats_row.addWidget(self.stat_total, 1)

        self.stat_success = StatCard("Basarili", "0", "#4caf50")
        stats_row.addWidget(self.stat_success, 1)

        self.stat_error = StatCard("Hatali", "0", "#f44336")
        stats_row.addWidget(self.stat_error, 1)

        layout.addLayout(stats_row)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(16, 14, 16, 14)
        c1_layout.setSpacing(10)

        excel_label = QLabel("Excel Dosyasi Secin")
        excel_label.setStyleSheet(f"color: #ffffff; font-size: 14px; font-weight: bold; background: transparent;")
        c1_layout.addWidget(excel_label)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        self.excel_path_input = QLineEdit()
        self.excel_path_input.setPlaceholderText("Excel dosyasini secin veya surukleyip birakin...")
        self.excel_path_input.setMinimumHeight(36)
        file_row.addWidget(self.excel_path_input, 1)

        self.browse_btn = QPushButton("Gozat")
        self.browse_btn.setFixedSize(90, 36)
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #c9a86c;
                color: #1a1a1a;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #d4b87a; }}
            QPushButton:pressed {{ background-color: #b8975b; }}
        """)
        self.browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self.browse_btn)
        c1_layout.addLayout(file_row)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(16, 14, 16, 14)
        c2_layout.setSpacing(12)

        progress_title = QLabel("Islem Durumu")
        progress_title.setStyleSheet(f"color: #ffffff; font-size: 14px; font-weight: bold; background: transparent;")
        c2_layout.addWidget(progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - Hazir")
        self.progress_bar.setFixedHeight(28)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #333333;
                border-radius: 6px;
                text-align: center;
                background-color: #1a1a1a;
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: #c9a86c;
                border-radius: 5px;
            }}
        """)
        c2_layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.start_btn = QPushButton("Botu Baslat")
        self.start_btn.setFixedSize(120, 38)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #4caf50;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #5cbf60; }}
            QPushButton:pressed {{ background-color: #3d8b40; }}
            QPushButton:disabled {{ background-color: #333333; color: #666666; }}
        """)
        self.start_btn.clicked.connect(self._start_bot)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Durdur")
        self.stop_btn.setFixedSize(100, 38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #f44336;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #ff5745; }}
            QPushButton:pressed {{ background-color: #d32f2f; }}
            QPushButton:disabled {{ background-color: #333333; color: #666666; }}
        """)
        self.stop_btn.clicked.connect(self._stop_bot)
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()
        c2_layout.addLayout(btn_row)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)
        c3_layout.setContentsMargins(16, 14, 16, 14)
        c3_layout.setSpacing(10)

        log_header = QLabel("Islem Logu")
        log_header.setStyleSheet(f"color: #ffffff; font-size: 14px; font-weight: bold; background: transparent;")
        c3_layout.addWidget(log_header)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)
        self.log_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: #111111;
                color: #cccccc;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        c3_layout.addWidget(self.log_output)

        clear_btn = QPushButton("Logu Temizle")
        clear_btn.setFixedSize(120, 30)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #333333;
                color: #cccccc;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #444444; }}
        """)
        clear_btn.clicked.connect(lambda: self.log_output.clear())
        c3_layout.addWidget(clear_btn, 0, Qt.AlignRight)

        layout.addWidget(card3, 1)

        return page

    # --- Settings Page ---
    def _create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(SC(32), SC(24), SC(32), SC(20))
        layout.setSpacing(SC(20))

        header = QLabel("Ayarlar")
        header.setStyleSheet(f"font-size: {SC(26)}px; font-weight: bold; color: {ACCENT_PRIMARY}; background: transparent;")
        layout.addWidget(header)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(SC(16))

        auto_update = QLabel("Otomatik Guncelleme")
        auto_update.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {SC(17)}px; font-weight: bold; background: transparent;")
        c1_layout.addWidget(auto_update)

        self.auto_update_cb = QCheckBox("Uygulama baslangicinda guncelleme kontrol et")
        self.auto_update_cb.setChecked(True)
        c1_layout.addWidget(self.auto_update_cb)

        notif_label = QLabel("Bildirimler")
        notif_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {SC(17)}px; font-weight: bold; background: transparent;")
        c1_layout.addWidget(notif_label)

        self.notif_cb = QCheckBox("Islem tamamlanma bildirimleri goster")
        self.notif_cb.setChecked(True)
        c1_layout.addWidget(self.notif_cb)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(SC(16))

        wait_label = QLabel("Bekleme Suresi")
        wait_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {SC(17)}px; font-weight: bold; background: transparent;")
        c2_layout.addWidget(wait_label)

        wait_row = QHBoxLayout()
        self.wait_spin = QSpinBox()
        self.wait_spin.setRange(1, 120)
        self.wait_spin.setValue(3)
        self.wait_spin.setSuffix(" saniye")
        self.wait_spin.setFixedWidth(220)
        wait_row.addWidget(self.wait_spin)
        wait_row.addStretch()
        c2_layout.addLayout(wait_row)

        lang_label = QLabel("Dil")
        lang_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {SC(17)}px; font-weight: bold; background: transparent;")
        c2_layout.addWidget(lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Turkce", "English"])
        self.lang_combo.setFixedWidth(260)
        c2_layout.addWidget(self.lang_combo)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)
        c3_layout.setSpacing(SC(16))

        save_btn = StyledButton("Ayarlari Kaydet", ACCENT_PRIMARY)
        save_btn.setFixedWidth(260)
        save_btn.clicked.connect(self._save_settings)
        c3_layout.addWidget(save_btn)

        layout.addWidget(card3)

        layout.addStretch()
        return page

    # --- License Page ---
    def _create_license_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(SC(32), SC(24), SC(32), SC(20))
        layout.setSpacing(SC(20))

        header = QLabel("Lisans Yonetimi")
        header.setStyleSheet(f"font-size: {SC(26)}px; font-weight: bold; color: {ACCENT_PRIMARY}; background: transparent;")
        layout.addWidget(header)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(SC(16))

        hw_label = QLabel("Hardware ID (Cihaz Kimligi)")
        hw_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {SC(17)}px; font-weight: bold; background: transparent;")
        c1_layout.addWidget(hw_label)

        hw_row = QHBoxLayout()
        hw_row.setSpacing(SC(16))
        self.hw_id_display = QLineEdit(self.hardware_id)
        self.hw_id_display.setReadOnly(True)
        self.hw_id_display.setMinimumHeight(40)
        self.hw_id_display.setStyleSheet(f"""
            QLineEdit {{
                background-color: {NAV_BG};
                color: {ACCENT_SECONDARY};
                border: 2px solid {ACCENT_SECONDARY};
                border-radius: 8px;
                padding: 12px 14px;
                font-family: 'Consolas', monospace;
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        hw_row.addWidget(self.hw_id_display, 1)

        self.copy_hw_btn = StyledButton("Kopyala", ACCENT_SECONDARY)
        self.copy_hw_btn.setFixedWidth(140)
        self.copy_hw_btn.clicked.connect(self._copy_hw_id)
        hw_row.addWidget(self.copy_hw_btn)
        c1_layout.addLayout(hw_row)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(SC(16))

        key_label = QLabel("Lisans Anahtari")
        key_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {SC(17)}px; font-weight: bold; background: transparent;")
        c2_layout.addWidget(key_label)

        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("SGK-XXXX-XXXX-XXXX-XXXX formatinda girin...")
        self.license_input.setMinimumHeight(40)
        c2_layout.addWidget(self.license_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SC(16))

        self.verify_btn = StyledButton("Lisans Dogrula", SUCCESS)
        self.verify_btn.setMinimumHeight(40)
        self.verify_btn.clicked.connect(self._verify_license)
        btn_row.addWidget(self.verify_btn)

        self.demo_btn = StyledButton("Demo Lisans Al", WARNING)
        self.demo_btn.setMinimumHeight(40)
        self.demo_btn.clicked.connect(self._get_demo_license)
        btn_row.addWidget(self.demo_btn)

        btn_row.addStretch()
        c2_layout.addLayout(btn_row)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)

        self.license_info = QLabel("Lisans durumu: Demo modunda calisiyor")
        self.license_info.setStyleSheet(f"color: {WARNING}; font-size: {SC(17)}px; font-weight: bold; background: transparent;")
        self.license_info.setWordWrap(True)
        c3_layout.addWidget(self.license_info)

        layout.addWidget(card3)
        layout.addStretch()
        return page

    # --- SGK Sifreleri Page ---
    def _create_credentials_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(SC(32), SC(24), SC(32), SC(20))
        layout.setSpacing(SC(16))

        header = QLabel("SGK Sifreleri")
        header.setStyleSheet(f"color: {ACCENT_PRIMARY}; font-size: {SC(26)}px; font-weight: bold; background: transparent;")
        layout.addWidget(header)

        desc = QLabel("SGK giris bilgilerinizi buradan kaydedebilirsiniz.\n"
                       "Bilgiler yalnizca bu bilgisayarda saklanir, baska yere gonderilmez.")
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {SC(14)}px; background: transparent;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Yeni Ekle Card ---
        card_add = QFrame()
        card_add.setStyleSheet(f"""
            QFrame {{ background-color: {BG_CARD}; border-radius: {SC(12)}px; padding: {SC(20)}px; border: 1px solid {BORDER_COLOR}; }}
        """)
        add_layout = QVBoxLayout(card_add)
        add_layout.setSpacing(SC(12))

        add_title = QLabel("Yeni Sifre Ekle / Guncelle")
        add_title.setStyleSheet(f"color: {ACCENT_PRIMARY}; font-size: {SC(17)}px; font-weight: bold; background: transparent;")
        add_layout.addWidget(add_title)

        form = QHBoxLayout()
        form.setSpacing(SC(12))

        self.cred_name_input = QLineEdit()
        self.cred_name_input.setPlaceholderText("Isim (orn: Arda)")
        self.cred_name_input.setMinimumHeight(40)
        form.addWidget(self.cred_name_input, 1)

        self.cred_tc_input = QLineEdit()
        self.cred_tc_input.setPlaceholderText("TC Kimlik No")
        self.cred_tc_input.setMaxLength(11)
        self.cred_tc_input.setMinimumHeight(40)
        form.addWidget(self.cred_tc_input, 1)

        self.cred_pass_input = QLineEdit()
        self.cred_pass_input.setPlaceholderText("Sifre")
        self.cred_pass_input.setEchoMode(QLineEdit.Password)
        self.cred_pass_input.setMinimumHeight(40)
        form.addWidget(self.cred_pass_input, 1)

        add_layout.addLayout(form)

        btn_row = QHBoxLayout()
        save_cred_btn = StyledButton("Kaydet", SUCCESS)
        save_cred_btn.setMinimumHeight(40)
        save_cred_btn.clicked.connect(self._save_credential)
        btn_row.addWidget(save_cred_btn)
        btn_row.addStretch()
        add_layout.addLayout(btn_row)

        layout.addWidget(card_add)

        # --- Kayitli Sifreler Card ---
        card_list = QFrame()
        card_list.setStyleSheet(f"""
            QFrame {{ background-color: {BG_CARD}; border-radius: 12px; padding: 16px; border: 1px solid {BORDER_COLOR}; }}
        """)
        list_layout = QVBoxLayout(card_list)
        list_layout.setSpacing(10)

        list_title = QLabel("Kayitli Sifreler")
        list_title.setStyleSheet(f"color: {ACCENT_PRIMARY}; font-size: 16px; font-weight: bold;")
        list_layout.addWidget(list_title)

        self.cred_list_layout = QVBoxLayout()
        self.cred_list_layout.setSpacing(6)
        list_layout.addLayout(self.cred_list_layout)

        refresh_btn = StyledButton("Yenile", ACCENT_SECONDARY)
        refresh_btn.clicked.connect(self._refresh_credentials_list)
        list_layout.addWidget(refresh_btn)

        layout.addWidget(card_list)
        layout.addStretch()

        # Ilk yukleme
        QTimer.singleShot(100, self._refresh_credentials_list)

        return page

    def _refresh_credentials_list(self):
        """Kayitli sifreleri listeyi temizleyip yeniden yukler."""
        # Mevcut widget'lari temizle
        while self.cred_list_layout.count():
            item = self.cred_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        creds = _load_credentials()
        if not creds:
            lbl = QLabel("  Henuz kayitli sifre yok.")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; padding: 8px;")
            self.cred_list_layout.addWidget(lbl)
            return

        for cred in creds:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{ background-color: {BG_MAIN}; border-radius: 8px; padding: 8px; border: 1px solid {BORDER_COLOR}; }}
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 6, 12, 6)

            name_lbl = QLabel(cred.get("name", "?"))
            name_lbl.setStyleSheet(f"color: {ACCENT_PRIMARY}; font-size: 14px; font-weight: bold; min-width: 100px;")
            row_layout.addWidget(name_lbl)

            tc_lbl = QLabel(f"TC: {cred.get('tc', '****')}")
            tc_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; min-width: 140px;")
            row_layout.addWidget(tc_lbl)

            pass_lbl = QLabel(f"Sifre: {'*' * len(cred.get('password', ''))}")
            pass_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
            row_layout.addWidget(pass_lbl)

            del_btn = QPushButton("Sil")
            del_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {ERROR}; color: white; border: none; border-radius: 4px;
                               padding: 4px 12px; font-size: 12px; }}
                QPushButton:hover {{ background-color: #d32f2f; }}
            """)
            del_btn.clicked.connect(lambda _, n=cred.get("name"): self._delete_credential(n))
            row_layout.addWidget(del_btn)

            self.cred_list_layout.addWidget(row)

    def _save_credential(self):
        name = self.cred_name_input.text().strip()
        tc = self.cred_tc_input.text().strip()
        pw = self.cred_pass_input.text().strip()

        if not name or not tc or not pw:
            QMessageBox.warning(self, "Uyari", "Tum alanlari doldurun (Isim, TC, Sifre).")
            return
        if len(tc) != 11 or not tc.isdigit():
            QMessageBox.warning(self, "Uyari", "TC Kimlik No 11 haneli ve sadece rakam olmali.")
            return

        _add_credential(name, tc, pw)
        self.cred_name_input.clear()
        self.cred_tc_input.clear()
        self.cred_pass_input.clear()
        self._refresh_credentials_list()
        QMessageBox.information(self, "Kaydedildi", f"'{name}' icin SGK bilgileri kaydedildi.")

    def _delete_credential(self, name):
        cevap = QMessageBox.question(
            self, "Silme Onayi",
            f"'{name}' kaydini silmek istediginize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if cevap == QMessageBox.Yes:
            _delete_credential(name)
            self._refresh_credentials_list()

    # --- About Page ---
    def _create_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 20)
        layout.setSpacing(20)

        header = QLabel("Hakkinda")
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {ACCENT_PRIMARY};")
        layout.addWidget(header)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(16)

        app_title = QLabel(UYGULAMA_ADI)
        app_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {ACCENT_PRIMARY};")
        c1_layout.addWidget(app_title)

        ver_info = QLabel(f"Surum: {SURUM}")
        ver_info.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px;")
        c1_layout.addWidget(ver_info)

        dev_info = QLabel(f"Gelistirici: {SIRKET}")
        dev_info.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px;")
        c1_layout.addWidget(dev_info)

        copy_info = QLabel("2025 Tum haklari saklidir.")
        copy_info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")
        c1_layout.addWidget(copy_info)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(12)

        feat_title = QLabel("Ozellikler")
        feat_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {TEXT_PRIMARY};")
        c2_layout.addWidget(feat_title)

        features = [
            "Otomatik SGK E-Kesinti islemleri",
            "Excel dosyasindan toplu veri isleme",
            "Gercek zamanli ilerleme takibi",
            "Detayli islem loglama",
            "Otomatik guncelleme sistemi",
            "Kolay kullanim arayuzu",
            "Demo modu destegi",
            "Coklu dil destegi (planlanan)",
            "Yapay zeka destekli asistan (yeni!)",
        ]
        for feat in features:
            lbl = QLabel(f"  •  {feat}")
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; padding: 8px 4px; background: transparent;")
            lbl.setWordWrap(True)
            c2_layout.addWidget(lbl)

        layout.addWidget(card2)

        layout.addStretch()

        return page

    # --- Core Methods ---
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyasi Sec", "",
            "Excel Dosyalari (*.xlsx *.xls);;Tum Dosyalar (*)"
        )
        if path:
            self.excel_path_input.setText(path)

    def _start_bot(self):
        if not self.is_authorized:
            QMessageBox.warning(self, "Yetkisiz", "Lisans dogrulamasi yapilmadi. Once lisansinizi dogrulayin.")
            return

        path = self.excel_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Uyari", "Lutfen bir Excel dosyasi secin.")
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "Uyari", "Secilen dosya bulunamadi.")
            return

        self._append_log("Bot baslatildi...", "info")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Calisiyor... %p%")

        self.bot_thread = BotThread(path)
        self.bot_thread.log_signal.connect(self._on_log)
        self.bot_thread.progress_signal.connect(self._on_progress)
        self.bot_thread.finished_signal.connect(self._on_bot_finished)
        self.bot_thread.start()

    def _stop_bot(self):
        if self.bot_thread and self.bot_thread.isRunning():
            self.bot_thread.stop()
            self._append_log("Durduruluyor...", "warning")

    def _on_log(self, message):
        msg_lower = message.lower()
        if "hata" in msg_lower or "error" in msg_lower or "bulunamadi" in msg_lower:
            msg_type = "error"
        elif "basari" in msg_lower or "tamamlandi" in msg_lower:
            msg_type = "success"
        elif "uyari" in msg_lower or "warning" in msg_lower:
            msg_type = "warning"
        else:
            msg_type = "info"
        self._append_log(message, msg_type)

    def _append_log(self, message, msg_type="info"):
        ts = datetime.now().strftime('%H:%M:%S')
        color_map = {
            "success": SUCCESS,
            "error": ERROR,
            "warning": WARNING,
            "info": ACCENT_SECONDARY,
        }
        color = color_map.get(msg_type, ACCENT_SECONDARY)
        self.log_output.append(f'<span style="color: {color};">[{ts}] {message}</span>')
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def _on_progress(self, value):
        self.progress_bar.setValue(value)

    def _on_bot_finished(self, status):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setFormat("Tamamlandi! %p%")
        self._append_log(status, "success")

    def _copy_hw_id(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hardware_id)
        self.copy_hw_btn.setText("Kopyalandi!")
        QTimer.singleShot(2000, lambda: self.copy_hw_btn.setText("Kopyala"))

    def _startup_license_check(self):
        """Uygulama basladiginda API'ye HWID + IP gonder ve yetki kontrol et"""
        if not API_AVAILABLE:
            self.is_authorized = False
            self.license_status.setText("Lisans: Offline")
            self.license_status.setStyleSheet(f"""
                color: {WARNING};
                background-color: rgba(245, 158, 11, 0.15);
                border: 2px solid {WARNING};
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 14px;
                font-weight: bold;
            """)
            self.start_btn.setEnabled(False)
            self.start_btn.setText("Yetkisiz - Internet Baglantisi Gerekli")
            return

        try:
            result = register_and_check(self.hardware_id)
            self.is_authorized = result.get("authorized", False)
            is_demo = result.get("demo", False)
            admin_ok = result.get("admin_authorized", False)
            days_left = result.get("demo_days_left", 0)

            if self.is_authorized:
                if admin_ok:
                    self.license_status.setText("Lisans: Aktif (Sunucu)")
                    self.license_status.setStyleSheet(f"""
                        color: {SUCCESS};
                        background-color: rgba(16, 185, 129, 0.15);
                        border: 2px solid {SUCCESS};
                        border-radius: 8px;
                        padding: 6px 16px;
                        font-size: 14px;
                        font-weight: bold;
                    """)
                    self.license_info.setText("Lisans durumu: Aktif - Sunucu tarafindan dogrulandi")
                    self.license_info.setStyleSheet(f"color: {SUCCESS}; font-size: 16px; font-weight: bold;")
                else:
                    self.license_status.setText(f"Lisans: Demo ({days_left} gun)")
                    self.license_status.setStyleSheet(f"""
                        color: {WARNING};
                        background-color: rgba(245, 158, 11, 0.15);
                        border: 2px solid {WARNING};
                        border-radius: 8px;
                        padding: 6px 16px;
                        font-size: 14px;
                        font-weight: bold;
                    """)
                    self.license_info.setText(f"Lisans durumu: Demo aktif ({days_left} gun kaldi)")
                    self.license_info.setStyleSheet(f"color: {WARNING}; font-size: 16px; font-weight: bold;")
                self.start_btn.setEnabled(True)
                self.start_btn.setText("Botu Baslat")
            else:
                msg = result.get("message", "Yetkisiz")
                self.license_status.setText(f"Lisans: {msg}")
                self.license_status.setStyleSheet(f"""
                    color: {ERROR};
                    background-color: rgba(244, 67, 54, 0.15);
                    border: 2px solid {ERROR};
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-size: 14px;
                    font-weight: bold;
                """)
                self.start_btn.setEnabled(False)
                self.start_btn.setText("Yetkisiz - Admin ile iletisime gecin")
        except Exception:
            self.is_authorized = False
            self.license_status.setText("Lisans: Hata")
            self.license_status.setStyleSheet(f"""
                color: {WARNING};
                background-color: rgba(245, 158, 11, 0.15);
                border: 2px solid {WARNING};
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 14px;
                font-weight: bold;
            """)
            self.start_btn.setEnabled(False)
            self.start_btn.setText("Baglanti Hatasi - Tekrar Deneyin")

    def _check_for_updates(self):
        """GitHub'da yeni surum varsa bildirim goster, onaylanirse indir ve uygula."""
        if not hasattr(self, 'auto_update_cb') or not self.auto_update_cb.isChecked():
            return
        try:
            sonuc = _guncelleme_var_mi()
            yeni_surum, zip_url = sonuc
            if not yeni_surum or not zip_url:
                return
            cevap = QMessageBox.question(
                self, "Guncelleme Mevcut",
                f"Yeni surum bulundu: v{yeni_surum}\n"
                f"Mevcut surum: v{SURUM}\n\n"
                f"Simdi guncellensin mi?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if cevap == QMessageBox.Yes:
                QMessageBox.information(self, "Guncelleme",
                    "Yeni surum indiriliyor... Lutfen bekleyin.")
                _otomatik_guncelle(zip_url)
                QMessageBox.information(self, "Guncelleme Tamamlandi",
                    f"v{yeni_surum} basariyla yuklendi!\nUygulama yeniden baslatilacak.")
                script_yol = os.path.abspath(__file__)
                subprocess.Popen([sys.executable, script_yol] + sys.argv[1:])
                sys.exit(0)
        except Exception as e:
            QMessageBox.warning(self, "Guncelleme Hatasi",
                f"Guncelleme basarisiz: {e}\n\nManuel guncelleme icin siteden ZIP indirin.")

    def _verify_license(self):
        key = self.license_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Uyari", "Lisans anahtari bos olamaz.")
            return

        if not API_AVAILABLE:
            QMessageBox.warning(self, "Baglanti Hatasi",
                                "Sunucuya ulasilamiyor. Lisans dogrulamasi icin internet baglantisi gerekli.")
            return

        try:
            result = register_and_check(self.hardware_id)
            self.is_authorized = result.get("authorized", False)
            is_demo = result.get("demo", False)
            admin_ok = result.get("admin_authorized", False)
            days_left = result.get("demo_days_left", 0)

            if self.is_authorized:
                if admin_ok:
                    self.license_status.setText("Lisans: Aktif (Sunucu)")
                    self.license_status.setStyleSheet(f"""
                        color: {SUCCESS};
                        background-color: rgba(16, 185, 129, 0.15);
                        border: 2px solid {SUCCESS};
                        border-radius: 8px;
                        padding: 6px 16px;
                        font-size: 14px;
                        font-weight: bold;
                    """)
                    self.license_info.setText("Lisans durumu: Aktif - Sunucu tarafindan dogrulandi")
                    self.license_info.setStyleSheet(f"color: {SUCCESS}; font-size: 16px; font-weight: bold;")
                    QMessageBox.information(self, "Basarili", "Lisans dogrulandi!\nTum ozellikler aktif.")
                else:
                    self.license_status.setText("Lisans: Demo")
                    self.license_status.setStyleSheet(f"""
                        color: {WARNING};
                        background-color: rgba(245, 158, 11, 0.15);
                        border: 2px solid {WARNING};
                        border-radius: 8px;
                        padding: 6px 16px;
                        font-size: 14px;
                        font-weight: bold;
                    """)
                    self.license_info.setText(f"Lisans durumu: Demo aktif ({days_left} gun kaldi)")
                    self.license_info.setStyleSheet(f"color: {WARNING}; font-size: 16px; font-weight: bold;")
                    QMessageBox.information(self, "Demo Lisans",
                                            f"Demo lisans aktif!\n\n{days_left} gun kaldi. Sure bitince admin onayi gerekir.")
            else:
                self.license_status.setText("Lisans: Yetkisiz")
                self.license_status.setStyleSheet(f"""
                    color: {ERROR};
                    background-color: rgba(244, 67, 54, 0.15);
                    border: 2px solid {ERROR};
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-size: 14px;
                    font-weight: bold;
                """)
                msg = result.get("message", "HWID yetkisiz")
                self.license_info.setText(f"Lisans durumu: {msg}")
                self.license_info.setStyleSheet(f"color: {ERROR}; font-size: 16px; font-weight: bold;")
                QMessageBox.warning(self, "Yetkisiz",
                                    f"{msg}\n\nDemo suresi doldu veya yetki verilmedi.\nAdmin panelinden yetkilendirme gerektirir.")
        except Exception as e:
            self.is_authorized = False
            QMessageBox.warning(self, "Hata", f"Sunucu baglantisi hatasi:\n{str(e)}")

    def _get_demo_license(self):
        self.license_input.setText(DEMO_LISANS)
        QMessageBox.information(
            self, "Demo Lisans",
            f"Demo lisans anahtari yuklendi:\n\n{DEMO_LISANS}\n\nDogrulama icin 'Lisans Dogrula' butonuna basin."
        )

    def _save_settings(self):
        settings = {
            "auto_update": self.auto_update_cb.isChecked(),
            "notifications": self.notif_cb.isChecked(),
            "wait_time": self.wait_spin.value(),
            "language": self.lang_combo.currentText(),
        }
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Kaydedildi", "Ayarlar basariyla kaydedildi.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ayarlar kaydedilemedi:\n{str(e)}")

    def _load_settings(self):
        settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.auto_update_cb.setChecked(settings.get("auto_update", True))
                self.notif_cb.setChecked(settings.get("notifications", True))
                self.wait_spin.setValue(settings.get("wait_time", 3))
                lang = settings.get("language", "Turkce")
                idx = self.lang_combo.findText(lang)
                if idx >= 0:
                    self.lang_combo.setCurrentIndex(idx)
            except Exception:
                pass

    def closeEvent(self, event):
        if self.bot_thread and self.bot_thread.isRunning():
            reply = QMessageBox.question(
                self, "Cikis Onayi",
                "Bot hala calisiyor. Cikmak istediginize emin misiniz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.bot_thread.stop()
                self.bot_thread.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    # Yüksek DPI ekranlarda (laptop/4K) metinlerin üst üste binmemesi icin gerekli
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont("Segoe UI", int(11 * _scale))
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)

    window = SGKApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()