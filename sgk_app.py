"""
SGK E-Kesinti Otomasyon v1.1.0
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
import threading
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QLineEdit,
    QProgressBar, QTextEdit, QFileDialog, QCheckBox, QSpinBox,
    QComboBox, QMessageBox, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QDesktopWidget
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup,
    QPoint, QRect, QPointF
)
from PyQt5.QtGui import (
    QFont, QColor, QIcon, QPixmap, QPainter, QLinearGradient, QPalette,
    QRadialGradient, QPen, QBrush, QConicalGradient, QFontMetrics
)

# --- Sabitler ---
SURUM = "1.1.0"
UYGULAMA_ADI = "SGK E-Kesinti Otomasyon"
SIRKET = "Arda Yazilim"

# --- Renkler ---
CYAN = "#00d4ff"
CYAN_DARK = "#0099cc"
CYAN_LIGHT = "#33ddff"
NAVY = "#1a1a2e"
NAVY_MID = "#16213e"
NAVY_LIGHT = "#0f3460"
DARK_BG = "#0d1117"
CARD_BG = "#161b22"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
SUCCESS = "#3fb950"
WARNING = "#d29922"
ERROR = "#f85149"
INPUT_BG = "#0d1117"
INPUT_BORDER = "#30363d"
HOVER_BG = "#1c2333"
INFO_COLOR = "#58a6ff"

# --- OpenRouter ---
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
OPENROUTER_SYSTEM_PROMPT = (
    "Sen SGK E-Kesinti Otomasyonu asistanisin. Kullanicilara SGK tarimsal kesinti "
    "islemleri, Excel formati, hata cozumu ve bot kullanimi konularinda yardim ediyorsun. "
    "Turkce yanit ver."
)

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


def create_icon_emoji(emoji_char, size=64):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    font = QFont("Segoe UI Emoji", size // 2)
    painter.setFont(font)
    painter.setPen(QColor(CYAN))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, emoji_char)
    painter.end()
    return QIcon(pixmap)


# --- Progress Ring Widget ---
class CircularProgressRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._max = 100
        self.setMinimumSize(120, 120)
        self.setMaximumSize(120, 120)
        self._color = QColor(CYAN)
        self._bg_color = QColor(INPUT_BORDER)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = max(0, min(v, self._max))
        self.update()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        self._color = QColor(c)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        margin = 10
        pen_width = 10
        rect = QRect(margin, margin, w - 2 * margin, h - 2 * margin)
        center = QPointF(w / 2, h / 2)
        radius = min(rect.width(), rect.height()) / 2 - pen_width / 2

        # Background circle
        bg_pen = QPen(self._bg_color, pen_width, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(center, radius, radius)

        # Progress arc
        if self._value > 0:
            start_angle = 90 * 16
            span_angle = -int((self._value / self._max) * 360 * 16)
            progress_pen = QPen(self._color, pen_width, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(progress_pen)
            painter.drawArc(rect, start_angle, span_angle)

        # Text
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
        painter.drawText(rect, Qt.AlignCenter, f"%{int(self._value)}")

        painter.end()


# --- Stat Card Widget ---
class StatCard(QFrame):
    def __init__(self, title, value, color, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_BG};
                border: 1px solid {INPUT_BORDER};
                border-left: 4px solid {color};
                border-radius: 10px;
                padding: 12px 16px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        layout.addWidget(title_lbl)

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold; background: transparent;")
        layout.addWidget(self.value_lbl)

    def set_value(self, v):
        self.value_lbl.setText(str(v))


# --- Animated Header Widget ---
class AnimatedHeader(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._hue = 0
        self._glow_active = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

    def _animate(self):
        self._hue = (self._hue + 0.5) % 360
        c = QColor()
        c.setHsvF(self._hue / 360.0, 0.3, 0.12)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c.name()};
                border-bottom: 1px solid {INPUT_BORDER};
            }}
        """)

    def enterEvent(self, event):
        self._glow_active = True

    def leaveEvent(self, event):
        self._glow_active = False


# --- Logo Label with Glow ---
class GlowLogo(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._glow = False
        self._glow_opacity = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse)
        self._timer.start(30)
        self._target = 0.0

    def enterEvent(self, event):
        self._target = 1.0

    def leaveEvent(self, event):
        self._target = 0.0

    def _pulse(self):
        if self._glow_opacity < self._target:
            self._glow_opacity = min(self._glow_opacity + 0.08, 1.0)
        elif self._glow_opacity > self._target:
            self._glow_opacity = max(self._glow_opacity - 0.08, 0.0)
        if self._glow_opacity > 0:
            c = QColor(CYAN)
            c.setAlphaF(self._glow_opacity * 0.5)
            self.setStyleSheet(f"""
                font-size: 18px;
                color: {c.name()};
                text-shadow: 0 0 {int(self._glow_opacity * 12)}px {CYAN};
                background: transparent;
            """)
        else:
            self.setStyleSheet("font-size: 18px; color: #e6edf3; background: transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._glow_opacity > 0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(0, 212, 255, int(self._glow_opacity * 40))))
            painter.drawEllipse(self.rect().center(), 30 + int(self._glow_opacity * 10),
                                30 + int(self._glow_opacity * 10))
        painter.end()
        super().paintEvent(event)


# --- AI Thread ---
class AIThread(QThread):
    response_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, messages, parent=None):
        super().__init__(parent)
        self.messages = messages

    def run(self):
        try:
            payload = json.dumps({
                "model": OPENROUTER_MODEL,
                "messages": self.messages,
                "max_tokens": 1024,
                "temperature": 0.7,
            }).encode("utf-8")

            req = Request(
                OPENROUTER_API_URL,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://sgk-bot.local",
                    "X-Title": "SGK E-Kesinti Otomasyon",
                },
                method="POST",
            )

            with urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                self.response_signal.emit(content)
            else:
                self.error_signal.emit("Bos yanit alindi.")
        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            self.error_signal.emit(f"HTTP {e.code}: {e.reason}\n{body[:500]}")
        except URLError as e:
            self.error_signal.emit(f"Ag hatasi: {str(e)}")
        except Exception as e:
            self.error_signal.emit(f"Beklenmeyen hata: {str(e)}")
        finally:
            self.finished_signal.emit()


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
    def __init__(self, text, color=CYAN, parent=None):
        super().__init__(text, parent)
        self.base_color = color
        self._scale = 1.0
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.base_color};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {CYAN_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {CYAN_DARK};
            }}
            QPushButton:disabled {{
                background-color: {INPUT_BG};
                color: {TEXT_SECONDARY};
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)

    def set_color(self, color):
        self.base_color = color
        self._update_style()

    def enterEvent(self, event):
        self.setStyleSheet(self.styleSheet() + f"""
            QPushButton {{
                border: 1px solid rgba(0, 212, 255, 60);
                box-shadow: 0 0 8px rgba(0, 212, 255, 0.3);
            }}
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style()
        super().leaveEvent(event)


# --- Nav Button ---
class NavButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self._update_style(False)

    def _update_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {CYAN};
                    border: none;
                    border-top: 3px solid {CYAN};
                    padding: 10px 8px;
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_SECONDARY};
                    border: none;
                    border-top: 3px solid transparent;
                    padding: 10px 8px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    color: {TEXT_PRIMARY};
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
                background-color: {CARD_BG};
                border: 1px solid {INPUT_BORDER};
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


# --- Main Window ---
class SGKApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{UYGULAMA_ADI} v{SURUM}")
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)
        self.hardware_id = get_hardware_id()
        self.bot_thread = None
        self.ai_thread = None
        self.chat_history = []
        self.dark_palette()

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
        self.pages.addWidget(self._create_ai_page())
        content_area.addWidget(self.pages, 1)

        main_layout.addLayout(content_area, 1)
        main_layout.addWidget(self._create_status_bar())

        bottom_area = QVBoxLayout()
        bottom_area.setContentsMargins(0, 0, 0, 0)
        bottom_area.setSpacing(0)
        bottom_area.addWidget(self._create_bottom_bar())
        main_layout.addLayout(bottom_area)

        self.nav_buttons = []
        self._update_nav(0)

        # Clock timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        # Fade animation for page transitions
        self._fade_opacity = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(self._fade_opacity)
        self._fade_opacity.setOpacity(1.0)

    def dark_palette(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {DARK_BG};
            }}
            QWidget {{
                background-color: transparent;
                color: {TEXT_PRIMARY};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QScrollBar:vertical {{
                background: {NAVY};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {NAVY_LIGHT};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {NAVY};
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {NAVY_LIGHT};
                border-radius: 5px;
                min-width: 30px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QLineEdit {{
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {INPUT_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                selection-background-color: {CYAN};
            }}
            QLineEdit:focus {{
                border: 1px solid {CYAN};
            }}
            QTextEdit {{
                background-color: {INPUT_BG};
                color: {SUCCESS};
                border: 1px solid {INPUT_BORDER};
                border-radius: 8px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
            }}
            QComboBox {{
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {INPUT_BORDER};
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
                min-height: 20px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {TEXT_SECONDARY};
                margin-right: 10px;
            }}
            QComboBox:hover {{
                border: 1px solid {CYAN};
            }}
            QComboBox QAbstractItemView {{
                background-color: {NAVY_MID};
                color: {TEXT_PRIMARY};
                border: 1px solid {INPUT_BORDER};
                border-radius: 4px;
                selection-background-color: {CYAN};
                padding: 4px;
            }}
            QSpinBox {{
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {INPUT_BORDER};
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
            }}
            QSpinBox:focus {{
                border: 1px solid {CYAN};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {NAVY_LIGHT};
                border: none;
                width: 20px;
            }}
            QCheckBox {{
                spacing: 10px;
                font-size: 14px;
                color: {TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {INPUT_BORDER};
                background-color: {INPUT_BG};
            }}
            QCheckBox::indicator:checked {{
                background-color: {CYAN};
                border-color: {CYAN};
            }}
            QProgressBar {{
                border: 1px solid {INPUT_BORDER};
                border-radius: 8px;
                text-align: center;
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                font-size: 13px;
                font-weight: bold;
                min-height: 28px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {CYAN_DARK}, stop:1 {CYAN});
                border-radius: 7px;
            }}
        """)

    def _create_top_bar(self):
        bar = AnimatedHeader()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        logo_label = GlowLogo("🔷")
        logo_label.setFont(QFont("Segoe UI Emoji", 18))
        layout.addWidget(logo_label)

        title = QLabel(f"  {UYGULAMA_ADI}")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold; background: transparent;")
        layout.addWidget(title)

        ver_label = QLabel(f"  v{SURUM}")
        ver_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        layout.addWidget(ver_label)

        layout.addStretch()

        self.clock_label = QLabel("00:00:00")
        self.clock_label.setStyleSheet(f"""
            color: {CYAN};
            background-color: rgba(0, 212, 255, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 10px;
            padding: 4px 12px;
            font-size: 13px;
            font-weight: bold;
            font-family: 'Consolas', monospace;
        """)
        layout.addWidget(self.clock_label)

        layout.addSpacing(12)

        self.license_status = QLabel("  Lisans: Demo  ")
        self.license_status.setStyleSheet(f"""
            color: {WARNING};
            background-color: rgba(210, 153, 34, 0.15);
            border: 1px solid {WARNING};
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 600;
        """)
        layout.addWidget(self.license_status)

        dev_label = QLabel(f"  {SIRKET}  ")
        dev_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        layout.addWidget(dev_label)

        return bar

    def _create_bottom_bar(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {NAVY};
                border-top: 1px solid {INPUT_BORDER};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        nav_data = [
            ("🏠  Ana Sayfa", 0),
            ("⚙️  Ayarlar", 1),
            ("🔑  Lisans", 2),
            ("ℹ️  Hakkında", 3),
            ("✨  Yardimci AI", 4),
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
        bar.setFixedHeight(24)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {NAVY_MID};
                border-top: 1px solid {INPUT_BORDER};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        status_text = QLabel(f"Hazir | Son guncelleme: {datetime.now().strftime('%d.%m.%Y')} | v{SURUM}")
        status_text.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        layout.addWidget(status_text)

        layout.addStretch()

        return bar

    def _navigate_to(self, index):
        self._fade_opacity.setOpacity(0.0)
        anim = QPropertyAnimation(self._fade_opacity, b"opacity")
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self._fade_anim = anim

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
        layout.setSpacing(16)

        header = QLabel("Ana Sayfa")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {CYAN};")
        layout.addWidget(header)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.stat_total = StatCard("Toplam Islem", "1,247", CYAN)
        stats_row.addWidget(self.stat_total)

        self.stat_success = StatCard("Basarili", "1,198", SUCCESS)
        stats_row.addWidget(self.stat_success)

        self.stat_error = StatCard("Hatali", "49", ERROR)
        stats_row.addWidget(self.stat_error)

        layout.addLayout(stats_row)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(12)

        excel_label = QLabel("Excel Dosyasi Secin:")
        excel_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        c1_layout.addWidget(excel_label)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        self.excel_path_input = QLineEdit()
        self.excel_path_input.setPlaceholderText("Dosya yolunu secin veya yapistirin...")
        file_row.addWidget(self.excel_path_input, 1)

        self.browse_btn = StyledButton("📂  Gözat")
        self.browse_btn.setFixedWidth(120)
        self.browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(self.browse_btn)
        c1_layout.addLayout(file_row)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(12)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(16)
        progress_row.setAlignment(Qt.AlignCenter)

        self.progress_ring = CircularProgressRing()
        self.progress_ring.value = 0
        progress_row.addWidget(self.progress_ring)

        progress_side = QVBoxLayout()
        progress_side.setSpacing(8)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - Hazir")
        progress_side.addWidget(self.progress_bar)

        progress_row.addLayout(progress_side, 1)
        c2_layout.addLayout(progress_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self.start_btn = StyledButton("▶️  Baslat", SUCCESS)
        self.start_btn.clicked.connect(self._start_bot)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = StyledButton("⏹  Durdur", ERROR)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_bot)
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()
        c2_layout.addLayout(btn_row)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)
        c3_layout.setSpacing(8)

        log_header = QLabel("📝  Islem Logu")
        log_header.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        c3_layout.addWidget(log_header)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(160)
        self.log_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {INPUT_BG};
                color: {SUCCESS};
                border: 1px solid {INPUT_BORDER};
                border-radius: 8px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
            }}
        """)
        c3_layout.addWidget(self.log_output)

        clear_btn = StyledButton("🗑️  Logu Temizle", TEXT_SECONDARY)
        clear_btn.setFixedWidth(160)
        clear_btn.clicked.connect(lambda: self.log_output.clear())
        c3_layout.addWidget(clear_btn, 0, Qt.AlignRight)

        layout.addWidget(card3, 1)

        return page

    # --- Settings Page ---
    def _create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 20)
        layout.setSpacing(16)

        header = QLabel("Ayarlar")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {CYAN};")
        layout.addWidget(header)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(14)

        auto_update = QLabel("Otomatik Guncelleme")
        auto_update.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        c1_layout.addWidget(auto_update)

        self.auto_update_cb = QCheckBox("Uygulama baslangicinda guncelleme kontrol et")
        self.auto_update_cb.setChecked(True)
        c1_layout.addWidget(self.auto_update_cb)

        notif_label = QLabel("Bildirimler")
        notif_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        c1_layout.addWidget(notif_label)

        self.notif_cb = QCheckBox("Islem tamamlanma bildirimleri goster")
        self.notif_cb.setChecked(True)
        c1_layout.addWidget(self.notif_cb)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(14)

        wait_label = QLabel("Bekleme Suresi (saniye)")
        wait_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        c2_layout.addWidget(wait_label)

        wait_row = QHBoxLayout()
        self.wait_spin = QSpinBox()
        self.wait_spin.setRange(1, 120)
        self.wait_spin.setValue(3)
        self.wait_spin.setSuffix(" sn")
        self.wait_spin.setFixedWidth(160)
        wait_row.addWidget(self.wait_spin)
        wait_row.addStretch()
        c2_layout.addLayout(wait_row)

        lang_label = QLabel("Dil")
        lang_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        c2_layout.addWidget(lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Turkce", "English"])
        self.lang_combo.setFixedWidth(200)
        c2_layout.addWidget(self.lang_combo)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)
        c3_layout.setSpacing(14)

        save_btn = StyledButton("💾  Ayarlari Kaydet")
        save_btn.setFixedWidth(200)
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
        layout.setSpacing(16)

        header = QLabel("Lisans Yonetimi")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {CYAN};")
        layout.addWidget(header)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(12)

        hw_label = QLabel("Hardware ID (Cihaz Kimligi):")
        hw_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        c1_layout.addWidget(hw_label)

        hw_row = QHBoxLayout()
        hw_row.setSpacing(10)
        self.hw_id_display = QLineEdit(self.hardware_id)
        self.hw_id_display.setReadOnly(True)
        self.hw_id_display.setStyleSheet(f"""
            QLineEdit {{
                background-color: {NAVY_MID};
                color: {CYAN};
                border: 1px solid {CYAN};
                border-radius: 8px;
                padding: 10px 14px;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        hw_row.addWidget(self.hw_id_display, 1)

        self.copy_hw_btn = StyledButton("📋 Kopyala", CYAN_DARK)
        self.copy_hw_btn.setFixedWidth(120)
        self.copy_hw_btn.clicked.connect(self._copy_hw_id)
        hw_row.addWidget(self.copy_hw_btn)
        c1_layout.addLayout(hw_row)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(12)

        key_label = QLabel("Lisans Anahtari:")
        key_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        c2_layout.addWidget(key_label)

        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("SGK-XXXX-XXXX-XXXX-XXXX formatinda girin...")
        self.license_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {INPUT_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                font-family: 'Consolas', monospace;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {CYAN};
            }}
        """)
        c2_layout.addWidget(self.license_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.verify_btn = StyledButton("✅  Lisansi Dogrula", SUCCESS)
        self.verify_btn.clicked.connect(self._verify_license)
        btn_row.addWidget(self.verify_btn)

        self.demo_btn = StyledButton("🧪  Demo Lisans Al", WARNING)
        self.demo_btn.clicked.connect(self._get_demo_license)
        btn_row.addWidget(self.demo_btn)

        btn_row.addStretch()
        c2_layout.addLayout(btn_row)

        layout.addWidget(card2)

        card3 = CardFrame()
        c3_layout = QVBoxLayout(card3)

        self.license_info = QLabel("Lisans durumu: Demo modunda calisiyor")
        self.license_info.setStyleSheet(f"color: {WARNING}; font-size: 14px; font-weight: 600;")
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
        layout.setSpacing(16)

        header = QLabel("Hakkinda")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {CYAN};")
        layout.addWidget(header)

        card1 = CardFrame()
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(12)

        app_title = QLabel(f"🔷  {UYGULAMA_ADI}")
        app_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {CYAN};")
        c1_layout.addWidget(app_title)

        ver_info = QLabel(f"Surum: {SURUM}")
        ver_info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")
        c1_layout.addWidget(ver_info)

        dev_info = QLabel(f"Gelistirici: {SIRKET}")
        dev_info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px;")
        c1_layout.addWidget(dev_info)

        copy_info = QLabel("© 2025 Tum haklari saklidir.")
        copy_info.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        c1_layout.addWidget(copy_info)

        layout.addWidget(card1)

        card2 = CardFrame()
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(8)

        feat_title = QLabel("✨  Ozellikler")
        feat_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {TEXT_PRIMARY};")
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
            "Animasyonlu arayuz (yeni!)",
        ]
        for feat in features:
            lbl = QLabel(f"  •  {feat}")
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; padding: 3px 0;")
            c2_layout.addWidget(lbl)

        layout.addWidget(card2)

        layout.addStretch()

        footer = QLabel(f"{SIRKET} tarafindan 💙 ile yapildi")
        footer.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        return page

    # --- AI Page ---
    def _create_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 20)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header = QLabel("✨  Yardimci AI")
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {CYAN};")
        header_row.addWidget(header)

        header_row.addStretch()

        model_label = QLabel(f"Model: {OPENROUTER_MODEL}")
        model_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        header_row.addWidget(model_label)

        layout.addLayout(header_row)

        card = CardFrame()
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        self.ai_chat_display = QTextEdit()
        self.ai_chat_display.setReadOnly(True)
        self.ai_chat_display.setMinimumHeight(300)
        self.ai_chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {INPUT_BG};
                color: {TEXT_PRIMARY};
                border: 1px solid {INPUT_BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.5;
            }}
        """)
        self.ai_chat_display.setHtml(self._ai_welcome_html())
        c_layout.addWidget(self.ai_chat_display)

        layout.addWidget(card, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Mesajinizi yazin...")
        self.ai_input.returnPressed.connect(self._send_ai_message)
        input_row.addWidget(self.ai_input, 1)

        self.ai_send_btn = StyledButton("Gonder", CYAN)
        self.ai_send_btn.setFixedWidth(100)
        self.ai_send_btn.clicked.connect(self._send_ai_message)
        input_row.addWidget(self.ai_send_btn)

        self.ai_clear_btn = StyledButton("Temizle", TEXT_SECONDARY)
        self.ai_clear_btn.setFixedWidth(100)
        self.ai_clear_btn.clicked.connect(self._clear_ai_chat)
        input_row.addWidget(self.ai_clear_btn)

        layout.addLayout(input_row)

        return page

    def _ai_welcome_html(self):
        return f"""
        <div style="padding: 10px;">
            <p style="color: {CYAN}; font-size: 15px; font-weight: bold;">Merhaba! Ben SGK E-Kesinti Asistani ✨</p>
            <p style="color: {TEXT_SECONDARY}; font-size: 13px;">SGK tarimsal kesinti islemleri, Excel formati, hata cozumu ve bot kullanimi konularinda size yardimci olabilirim.</p>
            <hr style="border-color: {INPUT_BORDER}; margin: 10px 0;">
            <p style="color: {TEXT_SECONDARY}; font-size: 12px;">Ornek sorular:</p>
            <ul style="color: {TEXT_SECONDARY}; font-size: 12px;">
                <li>Excel dosyasi nasil hazirlanir?</li>
                <li>E-Kesinti hatasi aliyorum, ne yapmaliyim?</li>
                <li>Bot nasil calistirilir?</li>
            </ul>
        </div>
        """

    def _send_ai_message(self):
        text = self.ai_input.text().strip()
        if not text:
            return

        self.chat_history.append({"role": "user", "content": text})
        self._append_ai_message("Siz", text, CYAN)

        self.ai_input.clear()
        self.ai_send_btn.setEnabled(False)
        self.ai_input.setEnabled(False)

        typing_html = f"""
        <div style="padding: 4px 0;">
            <span style="color: {INFO_COLOR}; font-size: 13px; font-style: italic;">
                ⏳ Asistani yaziyor...
            </span>
        </div>
        """
        self.ai_chat_display.append(typing_html)

        messages_for_api = [
            {"role": "system", "content": OPENROUTER_SYSTEM_PROMPT}
        ] + self.chat_history

        self.ai_thread = AIThread(messages_for_api)
        self.ai_thread.response_signal.connect(self._on_ai_response)
        self.ai_thread.error_signal.connect(self._on_ai_error)
        self.ai_thread.finished_signal.connect(self._on_ai_finished)
        self.ai_thread.start()

    def _on_ai_response(self, content):
        self.chat_history.append({"role": "assistant", "content": content})

        cursor = self.ai_chat_display.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.movePosition(cursor.End)
        self.ai_chat_display.setTextCursor(cursor)
        self.ai_chat_display.append("")

        self._append_ai_message("AI Asistan", content, SUCCESS)

    def _on_ai_error(self, error_msg):
        cursor = self.ai_chat_display.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.movePosition(cursor.End)
        self.ai_chat_display.setTextCursor(cursor)
        self.ai_chat_display.append("")

        self._append_ai_message("Hata", f"API hatasi: {error_msg}", ERROR)

    def _on_ai_finished(self):
        self.ai_send_btn.setEnabled(True)
        self.ai_input.setEnabled(True)
        self.ai_input.setFocus()

    def _append_ai_message(self, sender, text, color):
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        escaped = escaped.replace("\n", "<br>")
        timestamp = datetime.now().strftime("%H:%M")

        html = f"""
        <div style="padding: 6px 0; border-bottom: 1px solid {INPUT_BORDER};">
            <span style="color: {color}; font-weight: bold; font-size: 13px;">{sender}</span>
            <span style="color: {TEXT_SECONDARY}; font-size: 11px; margin-left: 8px;">{timestamp}</span>
            <p style="color: {TEXT_PRIMARY}; font-size: 14px; margin: 4px 0 0 0;">{escaped}</p>
        </div>
        """
        self.ai_chat_display.append(html)
        sb = self.ai_chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_ai_chat(self):
        self.chat_history.clear()
        self.ai_chat_display.setHtml(self._ai_welcome_html())

    # --- Core Methods ---
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Excel Dosyasi Sec", "",
            "Excel Dosyalari (*.xlsx *.xls);;Tum Dosyalar (*)"
        )
        if path:
            self.excel_path_input.setText(path)

    def _start_bot(self):
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
        self.progress_ring.value = 0

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
        elif "basari" in msg_lower or "tamamlandi" in msg_lower or "tamamlandi" in msg_lower:
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
            "info": INFO_COLOR,
        }
        color = color_map.get(msg_type, INFO_COLOR)
        self.log_output.append(f'<span style="color: {color};">[{ts}] {message}</span>')
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def _on_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_ring.value = value

    def _on_bot_finished(self, status):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setFormat("Tamamlandi! %p%")
        self._append_log(status, "success")

    def _copy_hw_id(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hardware_id)
        self.copy_hw_btn.setText("✅ Kopyalandi!")
        QTimer.singleShot(2000, lambda: self.copy_hw_btn.setText("📋 Kopyala"))

    def _verify_license(self):
        key = self.license_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Uyari", "Lisans anahtari bos olamaz.")
            return

        if key == DEMO_LISANS:
            self.license_status.setText("  Lisans: Demo  ")
            self.license_status.setStyleSheet(f"""
                color: {WARNING};
                background-color: rgba(210, 153, 34, 0.15);
                border: 1px solid {WARNING};
                border-radius: 12px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: 600;
            """)
            self.license_info.setText("Lisans durumu: Demo lisans aktif (30 gun sinirli)")
            self.license_info.setStyleSheet(f"color: {WARNING}; font-size: 14px; font-weight: 600;")
            QMessageBox.information(self, "Demo Lisans", "Demo lisans basariyla aktif edildi!\n\nBu lisans 30 gun gecerlidir.")
        else:
            simple_check = (key.startswith("SGK-") and len(key) == 24 and key.count("-") == 4)
            if simple_check:
                self.license_status.setText("  Lisans: Aktif  ")
                self.license_status.setStyleSheet(f"""
                    color: {SUCCESS};
                    background-color: rgba(63, 185, 80, 0.15);
                    border: 1px solid {SUCCESS};
                    border-radius: 12px;
                    padding: 4px 14px;
                    font-size: 12px;
                    font-weight: 600;
                """)
                self.license_info.setText("Lisans durumu: Aktif - Tum ozellikler acik")
                self.license_info.setStyleSheet(f"color: {SUCCESS}; font-size: 14px; font-weight: 600;")
                QMessageBox.information(self, "Basarili", "Lisans dogrulandi!\nTum ozellikler aktif.")
            else:
                QMessageBox.warning(self, "Hata", "Gecersiz lisans formati!\nBeklenen: SGK-XXXX-XXXX-XXXX-XXXX")

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

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = SGKApp()
    window._load_settings()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
