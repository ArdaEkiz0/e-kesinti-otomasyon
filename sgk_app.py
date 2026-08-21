"""
SGK E-Kesinti Otomasyon v1.2.0
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
SURUM = "1.3.0"
UYGULAMA_ADI = "SGK E-Kesinti Otomasyon"
SIRKET = "Arda Yazilim"

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
        self.setFixedHeight(56)
        self._update_style(False)

    def _update_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(201, 168, 108, 0.2);
                    color: {NAV_ACTIVE};
                    border: none;
                    border-top: 3px solid {NAV_ACTIVE};
                    padding: 10px 12px;
                    font-size: 14px;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_SECONDARY};
                    border: none;
                    border-top: 3px solid transparent;
                    padding: 10px 12px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    color: {TEXT_PRIMARY};
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
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)


# --- Stat Card Widget ---
class StatCard(QFrame):
    def __init__(self, title, value, color, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_COLOR};
                border-left: 4px solid {color};
                border-radius: 12px;
                padding: 16px 20px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        layout.addWidget(title_lbl)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold; background: transparent;")
        layout.addWidget(self.value_lbl)

    def set_value(self, v):
        self.value_lbl.setText(str(v))


# --- Main Window ---
class SGKApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{UYGULAMA_ADI} v{SURUM}")
        self.setMinimumSize(960, 700)
        self.resize(1050, 750)
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

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {BG_MAIN};
            }}
            QWidget {{
                background-color: transparent;
                color: {TEXT_PRIMARY};
                font-family: 'Segoe UI';
                font-size: 14px;
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
        bar.setFixedHeight(64)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {NAV_BG};
                border-bottom: 2px solid {BORDER_COLOR};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)

        title_icon = QLabel("SGK")
        title_icon.setStyleSheet(f"""
            color: {ACCENT_PRIMARY};
            font-size: 20px;
            font-weight: bold;
            background: transparent;
            padding: 4px 12px;
            border: 2px solid {ACCENT_PRIMARY};
            border-radius: 6px;
        """)
        layout.addWidget(title_icon)

        layout.addSpacing(12)

        title = QLabel(UYGULAMA_ADI)
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 18px; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        ver_label = QLabel(f"v{SURUM}")
        ver_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        layout.addWidget(ver_label)

        layout.addStretch()

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setStyleSheet(f"""
            color: {ACCENT_SECONDARY};
            background-color: rgba(6, 182, 212, 0.1);
            border: 2px solid {ACCENT_SECONDARY};
            border-radius: 8px;
            padding: 6px 16px;
            font-size: 16px;
            font-weight: bold;
            font-family: 'Consolas', monospace;
        """)
        layout.addWidget(self.clock_label)

        layout.addSpacing(16)

        self.license_status = QLabel("Lisans: Demo")
        self.license_status.setStyleSheet(f"""
            color: {WARNING};
            background-color: rgba(245, 158, 11, 0.15);
            border: 2px solid {WARNING};
            border-radius: 8px;
            padding: 6px 16px;
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(self.license_status)

        layout.addSpacing(16)

        dev_label = QLabel(SIRKET)
        dev_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        layout.addWidget(dev_label)

        return bar

    def _create_bottom_bar(self):
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {NAV_BG};
                border-top: 2px solid {BORDER_COLOR};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        nav_data = [
            ("Ana Sayfa", 0),
            ("Ayarlar", 1),
            ("Lisans", 2),
            ("Hakkinda", 3),
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
        bar.setFixedHeight(32)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {NAV_BG};
                border-top: 1px solid {BORDER_COLOR};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        status_text = QLabel(f"Hazir | Son guncelleme: {datetime.now().strftime('%d.%m.%Y')} | v{SURUM}")
        status_text.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; background: transparent;")
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
        layout.setContentsMargins(30, 24, 30, 20)
        layout.setSpacing(20)

        header = QLabel("Ana Sayfa")
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {ACCENT_PRIMARY};")
        layout.addWidget(header)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self.stat_total = StatCard("Toplam Islem", "1,247", ACCENT_SECONDARY)
        stats_row.addWidget(self.stat_total)

        self.stat_success = StatCard("Basarili", "1,198", SUCCESS)
        stats_row.addWidget(self.stat_success)

        self.stat_error = StatCard("Hatali", "49", ERROR)
        stats_row.addWidget(self.stat_error)

        layout.addLayout(stats_row)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(16)

        excel_label = QLabel("Excel Dosyasi Secin")
        excel_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        c1_layout.addWidget(excel_label)

        file_row = QHBoxLayout()
        file_row.setSpacing(16)
        self.excel_path_input = QLineEdit()
        self.excel_path_input.setPlaceholderText("Dosya yolunu secin veya yapistirin...")
        file_row.addWidget(self.excel_path_input, 1)

        self.browse_btn = StyledButton("Gozat", ACCENT_SECONDARY)
        self.browse_btn.setFixedWidth(140)
        self.browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self.browse_btn)
        c1_layout.addLayout(file_row)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(20)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(24)
        progress_row.setAlignment(Qt.AlignCenter)

        progress_side = QVBoxLayout()
        progress_side.setSpacing(12)

        progress_title = QLabel("Islem Durumu")
        progress_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        progress_side.addWidget(progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - Hazir")
        progress_side.addWidget(self.progress_bar)

        progress_row.addLayout(progress_side, 1)
        c2_layout.addLayout(progress_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        self.start_btn = StyledButton("Baslat", SUCCESS)
        self.start_btn.clicked.connect(self._start_bot)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = StyledButton("Durdur", ERROR)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_bot)
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()
        c2_layout.addLayout(btn_row)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)
        c3_layout.setSpacing(12)

        log_header = QLabel("Islem Logu")
        log_header.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        c3_layout.addWidget(log_header)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(180)
        self.log_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: #111111;
                color: {TEXT_PRIMARY};
                border: 2px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
            }}
        """)
        c3_layout.addWidget(self.log_output)

        clear_btn = StyledButton("Logu Temizle", BORDER_COLOR)
        clear_btn.setFixedWidth(180)
        clear_btn.clicked.connect(lambda: self.log_output.clear())
        c3_layout.addWidget(clear_btn, 0, Qt.AlignRight)

        layout.addWidget(card3, 1)

        return page

    # --- Settings Page ---
    def _create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 20)
        layout.setSpacing(20)

        header = QLabel("Ayarlar")
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {ACCENT_PRIMARY};")
        layout.addWidget(header)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(16)

        auto_update = QLabel("Otomatik Guncelleme")
        auto_update.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        c1_layout.addWidget(auto_update)

        self.auto_update_cb = QCheckBox("Uygulama baslangicinda guncelleme kontrol et")
        self.auto_update_cb.setChecked(True)
        c1_layout.addWidget(self.auto_update_cb)

        notif_label = QLabel("Bildirimler")
        notif_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        c1_layout.addWidget(notif_label)

        self.notif_cb = QCheckBox("Islem tamamlanma bildirimleri goster")
        self.notif_cb.setChecked(True)
        c1_layout.addWidget(self.notif_cb)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(16)

        wait_label = QLabel("Bekleme Suresi")
        wait_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        c2_layout.addWidget(wait_label)

        wait_row = QHBoxLayout()
        self.wait_spin = QSpinBox()
        self.wait_spin.setRange(1, 120)
        self.wait_spin.setValue(3)
        self.wait_spin.setSuffix(" saniye")
        self.wait_spin.setFixedWidth(200)
        wait_row.addWidget(self.wait_spin)
        wait_row.addStretch()
        c2_layout.addLayout(wait_row)

        lang_label = QLabel("Dil")
        lang_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        c2_layout.addWidget(lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Turkce", "English"])
        self.lang_combo.setFixedWidth(240)
        c2_layout.addWidget(self.lang_combo)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)
        c3_layout.setSpacing(16)

        save_btn = StyledButton("Ayarlari Kaydet", ACCENT_PRIMARY)
        save_btn.setFixedWidth(240)
        save_btn.clicked.connect(self._save_settings)
        c3_layout.addWidget(save_btn)

        layout.addWidget(card3)

        layout.addStretch()
        return page

    # --- License Page ---
    def _create_license_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 20)
        layout.setSpacing(20)

        header = QLabel("Lisans Yonetimi")
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {ACCENT_PRIMARY};")
        layout.addWidget(header)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(16)

        hw_label = QLabel("Hardware ID (Cihaz Kimligi)")
        hw_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        c1_layout.addWidget(hw_label)

        hw_row = QHBoxLayout()
        hw_row.setSpacing(16)
        self.hw_id_display = QLineEdit(self.hardware_id)
        self.hw_id_display.setReadOnly(True)
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
        c2_layout.setSpacing(16)

        key_label = QLabel("Lisans Anahtari")
        key_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold;")
        c2_layout.addWidget(key_label)

        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("SGK-XXXX-XXXX-XXXX-XXXX formatinda girin...")
        c2_layout.addWidget(self.license_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        self.verify_btn = StyledButton("Lisans Dogrula", SUCCESS)
        self.verify_btn.clicked.connect(self._verify_license)
        btn_row.addWidget(self.verify_btn)

        self.demo_btn = StyledButton("Demo Lisans Al", WARNING)
        self.demo_btn.clicked.connect(self._get_demo_license)
        btn_row.addWidget(self.demo_btn)

        btn_row.addStretch()
        c2_layout.addLayout(btn_row)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)

        self.license_info = QLabel("Lisans durumu: Demo modunda calisiyor")
        self.license_info.setStyleSheet(f"color: {WARNING}; font-size: 16px; font-weight: bold;")
        self.license_info.setWordWrap(True)
        c3_layout.addWidget(self.license_info)

        layout.addWidget(card3)
        layout.addStretch()
        return page

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
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; padding: 6px 0;")
            c2_layout.addWidget(lbl)

        layout.addWidget(card2)

        layout.addStretch()

        footer = QLabel(f"{SIRKET} tarafindan yapildi")
        footer.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

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
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 11)
    app.setFont(font)

    window = SGKApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()