"""
Claude Usage Widget — floating widget บนเดสก์ท็อป macOS

วิธีรัน:
    pip3 install PyQt6 requests keyring
    python3 claude_usage_widget.py

ฟีเจอร์:
- ลาก widget ย้ายตำแหน่งได้ (จำตำแหน่งไว้)
- ลากไปชิดขอบซ้าย/ขวา → เลื่อนซ่อนแบบ animation เหลือแท็บให้กดเปิด
- แถวข้อมูลสร้างตาม API จริง (per-model limit ขึ้นตามโมเดลที่ใช้)
- คลิกขวา: รีเฟรช / ซ่อน / ล้าง sessionKey / ปิด
- sessionKey เก็บใน macOS Keychain

ข้อควรรู้: ใช้ endpoint ภายในของ claude.ai ที่ไม่มีเอกสารทางการรองรับ
ถ้า Anthropic เปลี่ยนโครงสร้าง response สคริปต์นี้อาจพัง
"""

import sys
import json
import os
from datetime import datetime, timezone, timedelta

import requests
import keyring

try:
    import objc
except ImportError:
    objc = None
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMenu, QInputDialog, QMessageBox, QLineEdit, QSlider, QPushButton,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QFont, QPainterPath, QAction, QIcon,
    QConicalGradient, QPen,
)

SERVICE_NAME = "claude-usage-bar"
ACCOUNT_NAME = "sessionKey"
BASE_URL = "https://claude.ai/api"
REFRESH_MS = 5_000
CONFIG_PATH = os.path.expanduser("~/.claude_usage_widget.json")
ICON_PATH = os.path.expanduser("~/.claude_usage_widget_icon.png")
VERSION = "1.3.1"

SLIDER_QSS = """
QSlider::groove:horizontal { height: 4px; background: #3f3b58; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 13px; height: 13px; margin: -5px 0;
    background: #d6ff5c; border-radius: 7px;
}
QSlider::handle:horizontal:disabled { background: #5a5674; }
QSlider::sub-page:horizontal { background: #7a6fd6; border-radius: 2px; }
"""

SNAP_THRESHOLD = 40
ANIM_MS = 280

BG = QColor(22, 20, 32)
TRACK = QColor(63, 59, 88)
ORANGE = QColor(255, 122, 78)
LIME = QColor(214, 255, 92)
VIOLET = QColor(178, 148, 255)

THAI_FONTS = [
    "IBM Plex Sans Thai", "Noto Sans Thai", "Sukhumvit Set",
    "Thonburi", "Helvetica Neue",
]

# ชื่อที่จะแสดงสำหรับแต่ละ key ที่ API ส่งมา
LANG = "th"  # ถูกเขียนทับตอนโหลด config

LABELS = {
    "five_hour": {
        "th": "จำนวนที่ใช้ไปแล้ว · 5 ชม.",
        "en": "Used · 5-hour",
        "color": ORANGE,
    },
    "seven_day": {
        "th": "จำนวนที่ใช้ไปแล้ว · สัปดาห์นี้",
        "en": "Used · this week",
        "color": LIME,
    },
    "seven_day_opus": {
        "th": "จำนวนที่ใช้ไปแล้ว · Opus",
        "en": "Used · Opus",
        "color": VIOLET,
    },
    "seven_day_sonnet": {
        "th": "จำนวนที่ใช้ไปแล้ว · Sonnet",
        "en": "Used · Sonnet",
        "color": VIOLET,
    },
    "seven_day_haiku": {
        "th": "จำนวนที่ใช้ไปแล้ว · Haiku",
        "en": "Used · Haiku",
        "color": VIOLET,
    },
    "seven_day_fable": {
        "th": "จำนวนที่ใช้ไปแล้ว · Fable",
        "en": "Used · Fable",
        "color": VIOLET,
    },
}

STRINGS = {
    "settings_title":  {"th": "ตั้งค่าไฟ RGB",      "en": "RGB settings"},
    "rgb_on":          {"th": "ไฟ RGB: เปิด",       "en": "RGB: on"},
    "rgb_off":         {"th": "ไฟ RGB: ปิด",        "en": "RGB: off"},
    "speed":           {"th": "ความเร็ว",           "en": "Speed"},
    "glow":            {"th": "ความฟุ้ง",           "en": "Glow"},
    "per_frame":       {"th": "°/เฟรม",             "en": "°/frame"},
    "menu_refresh":    {"th": "รีเฟรชตอนนี้",       "en": "Refresh now"},
    "menu_settings":   {"th": "ตั้งค่าไฟ RGB…",     "en": "RGB settings…"},
    "menu_hide_left":  {"th": "ซ่อนไปทางซ้าย",      "en": "Hide to left"},
    "menu_hide_right": {"th": "ซ่อนไปทางขวา",       "en": "Hide to right"},
    "menu_clear":      {"th": "ล้าง sessionKey",    "en": "Clear sessionKey"},
    "menu_quit":       {"th": "ปิดโปรแกรม",         "en": "Quit"},
    "cleared_title":   {"th": "ล้างแล้ว",           "en": "Cleared"},
    "cleared_body":    {"th": "ปิดแล้วรันใหม่เพื่อใส่ sessionKey ใหม่",
                        "en": "Restart the app to enter a new sessionKey"},
    "session_expired": {"th": "session หมดอายุ",    "en": "Session expired"},
    "reset_done":      {"th": "รีเซ็ตแล้ว",          "en": "Reset"},
    "paste_key":       {"th": "วาง sessionKey ของคุณ (เก็บใน macOS Keychain):",
                        "en": "Paste your sessionKey (stored in macOS Keychain):"},
}


def T(key):
    return STRINGS.get(key, {}).get(LANG, key)

def usage_color(pct):
    """ไล่สีตามการใช้งาน: เขียว → เหลือง → ส้ม → แดง"""
    pct = max(0.0, min(100.0, float(pct)))
    stops = [
        (0,   (120, 235, 130)),
        (50,  (214, 255, 92)),
        (75,  (255, 214, 80)),
        (90,  (255, 140, 70)),
        (100, (255, 70, 70)),
    ]
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if p0 <= pct <= p1:
            t = 0 if p1 == p0 else (pct - p0) / (p1 - p0)
            return QColor(*[round(c0[j] + (c1[j] - c0[j]) * t) for j in range(3)])
    return QColor(*stops[-1][1])


CRAB = [
    "..X...X..",
    "..XX.XX..",
    ".XXXXXXX.",
    "XX.XXX.XX",
    "XXXXXXXXX",
    ".X.X.X.X.",
    "X.......X",
]


def thai_font(size, weight=QFont.Weight.Normal, serif=False):
    if serif:
        f = QFont("Georgia")
    else:
        f = QFont()
        f.setFamilies(THAI_FONTS)
    f.setPointSize(size)
    f.setWeight(weight)
    return f


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f)
    except Exception:
        pass


def humanize_reset(iso_str):
    """คืนข้อความ เช่น 'รีเซ็ตอีก 3 ชม. 45 นาที · 19:20'"""
    if not iso_str:
        return ""
    try:
        target = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        local = target.astimezone()
        secs = int((target - datetime.now(timezone.utc)).total_seconds())
        if secs <= 0:
            return T("reset_done")

        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        mins = rem // 60

        if LANG == "en":
            if days:
                left = f"Resets in {days}d {hours}h"
                when = local.strftime("%-d %b %H:%M")
            elif hours:
                left = f"Resets in {hours}h {mins}m"
                when = local.strftime("%H:%M")
            else:
                left = f"Resets in {mins}m"
                when = local.strftime("%H:%M")
            return f"{left} · {when}"

        if days:
            left = f"อีก {days} วัน {hours} ชม."
            when = local.strftime("%-d/%-m %H:%M")
        elif hours:
            left = f"อีก {hours} ชม. {mins} นาที"
            when = local.strftime("%H:%M")
        else:
            left = f"อีก {mins} นาที"
            when = local.strftime("%H:%M")

        return f"รีเซ็ต{left} · {when}"
    except Exception:
        return ""


def pretty_label(key):
    """คืน (ข้อความตามภาษาปัจจุบัน, สี)"""
    if key in LABELS:
        e = LABELS[key]
        return (e[LANG], e["color"])
    name = key.replace("seven_day_", "").replace("five_hour_", "")
    name = name.replace("_", " ").title()
    prefix = "จำนวนที่ใช้ไปแล้ว · " if LANG == "th" else "Used · "
    return (f"{prefix}{name}", VIOLET)


class CrabIcon(QWidget):
    """โลโก้พิกเซล ขยับขึ้นลงเบาๆ + ขาแกว่ง"""

    def __init__(self, scale=3):
        super().__init__()
        self.scale = scale
        self.frame = 0
        self.setFixedSize(9 * scale, 7 * scale + 8)
        self.anim = QTimer(self)
        self.anim.timeout.connect(self._step)
        self.anim.start(140)

    def _step(self):
        self.frame = (self.frame + 1) % 8
        self.update()

    def paintEvent(self, _):
        import math
        p = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        s = self.scale
        bob = math.sin(self.frame / 8 * 2 * math.pi) * 2.2
        sway = 1 if self.frame in (2, 3, 6, 7) else 0

        # เงาเรืองแสงจางๆ
        glow = QColor(ORANGE)
        glow.setAlpha(30)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QRectF(1, self.height() - 7, self.width() - 2, 6))

        p.setBrush(QBrush(ORANGE))
        for y, row in enumerate(CRAB):
            for x, ch in enumerate(row):
                if ch != "X":
                    continue
                dx = sway * s if y >= 5 else 0  # แถวล่าง = ขา ให้แกว่ง
                p.drawRect(int(x * s + dx), int(y * s + bob + 4), s, s)


def read_battery():
    """อ่านเปอร์เซ็นต์แบตจาก pmset คืน (percent, charging) หรือ (None, False)"""
    try:
        import subprocess, re as _re
        out = subprocess.run(
            ["pmset", "-g", "batt"], capture_output=True, text=True, timeout=3
        ).stdout
        m = _re.search(r"(\d+)%", out)
        if not m:
            return None, False
        charging = "AC Power" in out or "charging" in out.lower()
        return int(m.group(1)), charging
    except Exception:
        return None, False


class BatteryIcon(QWidget):
    def __init__(self):
        super().__init__()
        self.percent = None
        self.charging = False
        self.setFixedHeight(16)
        self.setFixedWidth(52)
        self.setFont(thai_font(10))
        self.tick = QTimer(self)
        self.tick.timeout.connect(self.reload)
        self.tick.start(60_000)
        self.reload()

    def reload(self):
        self.percent, self.charging = read_battery()
        from PyQt6.QtGui import QFontMetrics
        text = f"{self.percent}%" if self.percent is not None else "--"
        tw = QFontMetrics(thai_font(10)).horizontalAdvance(text)
        self.setFixedWidth(26 + 5 + tw)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        shell = QColor(200, 198, 214)
        p.setBrush(QBrush(shell))
        p.drawRoundedRect(QRectF(0, 2, 21, 12), 3, 3)
        p.drawRoundedRect(QRectF(22, 6, 3, 5), 1, 1)
        p.setBrush(QBrush(BG))
        p.drawRoundedRect(QRectF(1.5, 3.5, 18, 9), 2, 2)

        pct = self.percent if self.percent is not None else 0
        fill_w = max(2.0, 16.0 * pct / 100.0)
        if pct <= 20:
            color = QColor(255, 78, 78)      # แดง
        elif pct <= 50:
            color = QColor(255, 214, 80)     # เหลือง
        else:
            color = QColor(120, 230, 130)    # เขียว
        p.setBrush(QBrush(color))
        p.drawRoundedRect(QRectF(2.5, 4.5, fill_w, 7), 1.5, 1.5)

        if self.charging:
            # สายฟ้าตรงกลางตัวแบต พร้อมขอบเข้มให้อ่านออกบนพื้นสว่าง
            from PyQt6.QtGui import QPolygonF
            from PyQt6.QtCore import QPointF as _P
            bolt = QPolygonF([
                _P(12.0, 3.4), _P(8.6, 8.6), _P(10.8, 8.6),
                _P(9.4, 12.6), _P(13.0, 7.2), _P(10.8, 7.2),
            ])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(BG))
            p.save()
            p.translate(0.6, 0.4)
            p.drawPolygon(bolt)
            p.restore()
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawPolygon(bolt)

        p.setPen(color if self.percent is not None else QColor(139, 135, 163))
        p.setFont(thai_font(10))
        text = f"{pct}%" if self.percent is not None else "--"
        p.drawText(
            QRectF(31, 0, self.width() - 31, 16),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            text,
        )


class Track(QWidget):
    """แถบ progress พร้อม animation ตอนค่าเปลี่ยน"""

    def __init__(self, color):
        super().__init__()
        self._value = 0.0
        self.color = color
        self.setFixedHeight(17)
        self.anim = QPropertyAnimation(self, b"value")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_value(self):
        return self._value

    def set_value(self, v):
        self._value = v
        self.update()

    value = pyqtProperty(float, get_value, set_value)

    def set_color(self, color):
        self.color = color
        self.update()

    def animate_to(self, target):
        self.anim.stop()
        self.anim.setStartValue(self._value)
        self.anim.setEndValue(target)
        self.anim.start()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.translate(0, 5)
        p.setBrush(QBrush(TRACK))
        p.drawRoundedRect(QRectF(0, 0, self.width(), 7), 3.5, 3.5)
        if self._value > 0:
            w = max(7.0, self.width() * self._value)
            # ชั้นเรืองแสง: วาดซ้อนขยายออกด้วยความโปร่งต่ำ
            for spread, alpha in ((5, 26), (3, 46), (1.5, 80)):
                glow = QColor(self.color)
                glow.setAlpha(alpha)
                p.setBrush(QBrush(glow))
                p.drawRoundedRect(
                    QRectF(-spread, -spread, w + spread * 2, 7 + spread * 2),
                    3.5 + spread, 3.5 + spread,
                )
            p.setBrush(QBrush(self.color))
            p.drawRoundedRect(QRectF(0, 0, w, 7), 3.5, 3.5)


class Row(QWidget):
    def __init__(self, label, color):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)

        self.pct = QLabel("--")
        self.pct.setStyleSheet("color: #ffffff; background: transparent;")
        self.pct.setFont(thai_font(19, QFont.Weight.Bold))

        self.tag = QLabel(label)
        self.tag.setStyleSheet(
            "color: #d2cee2; background: #413c5c; border-radius: 10px; padding: 3px 11px;"
        )
        self.tag.setFont(thai_font(10))

        top.addWidget(self.pct)
        top.addWidget(self.tag)
        top.addStretch()
        layout.addLayout(top)

        self.track = Track(color)
        layout.addWidget(self.track)

        self.reset = QLabel("")
        self.reset.setStyleSheet("color: #8b87a3; background: transparent;")
        self.reset.setFont(thai_font(10))
        layout.addWidget(self.reset)

    def set_label(self, text):
        self.tag.setText(text)

    def set_value(self, pct, reset_text):
        self.pct.setText(f"{round(pct)}%")
        self.track.set_color(usage_color(pct))
        self.track.animate_to(max(0.0, min(100.0, pct)) / 100.0)
        self.reset.setText(reset_text)
        self.reset.setVisible(bool(reset_text))


class EdgeTab(QWidget):
    def __init__(self, widget, side):
        super().__init__()
        self.widget = widget
        self.side = side
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        self.setFixedSize(34, 96)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setWindowOpacity(0.0)
        self.fade = QPropertyAnimation(self, b"windowOpacity")
        self.fade.setDuration(200)
        self.frame = 0
        self.anim = QTimer(self)
        self.anim.timeout.connect(self._step)
        self.anim.start(140)

    def _step(self):
        self.frame = (self.frame + 1) % 8
        self.update()

    def fade_in(self):
        self.show()
        self.fade.stop()
        self.fade.setStartValue(0.0)
        self.fade.setEndValue(1.0)
        self.fade.start()

    def paintEvent(self, _):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        path = QPainterPath()
        if self.side == "left":
            path.addRoundedRect(QRectF(-14, 0, 48, 96), 14, 14)
            ox = 3
        else:
            path.addRoundedRect(QRectF(0, 0, 48, 96), 14, 14)
            ox = 8
        p.fillPath(path, QBrush(BG))

        # โลโก้พิกเซลกลางแท็บ ขยับเบาๆ
        s_ = 2
        bob = math.sin(self.frame / 8 * 2 * math.pi) * 1.6
        sway = 1 if self.frame in (2, 3, 6, 7) else 0
        p.setBrush(QBrush(ORANGE))
        for y, row in enumerate(CRAB):
            for x, ch in enumerate(row):
                if ch != "X":
                    continue
                dx = sway * s_ if y >= 5 else 0
                p.drawRect(int(ox + x * s_ + dx), int(31 + y * s_ + bob), s_, s_)

        # จุดบอกสถานะด้านล่าง
        dot = QColor(ORANGE)
        dot.setAlpha(150)
        p.setBrush(QBrush(dot))
        p.drawEllipse(QRectF(ox + 7, 66, 4, 4))

    def mousePressEvent(self, _):
        self.widget.reveal()


class SettingsPanel(QWidget):
    """หน้าต่างตั้งค่าไฟ RGB"""

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        self.setFixedWidth(250)
        self._drag = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(14)

        head = QHBoxLayout()
        t = QLabel(T("settings_title"))
        t.setStyleSheet("color: #ffffff; background: transparent;")
        t.setFont(thai_font(13, QFont.Weight.Bold))
        self.lbl_title = t
        close = QPushButton("✕")
        close.setFixedSize(20, 20)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setStyleSheet(
            "QPushButton{color:#8b87a3;background:transparent;border:none;}"
            "QPushButton:hover{color:#ffffff;}"
        )
        close.clicked.connect(self.hide)
        head.addWidget(t)
        head.addStretch()
        head.addWidget(close)
        lay.addLayout(head)

        self.btn_toggle = QPushButton()
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setFont(thai_font(11))
        self.btn_toggle.clicked.connect(self._toggle)
        lay.addWidget(self.btn_toggle)

        self.lbl_speed = QLabel()
        self.lbl_speed.setStyleSheet("color: #8b87a3; background: transparent;")
        self.lbl_speed.setFont(thai_font(10))
        lay.addWidget(self.lbl_speed)

        self.sld_speed = QSlider(Qt.Orientation.Horizontal)
        self.sld_speed.setRange(1, 60)  # = ค่า *0.1 องศาต่อเฟรม
        self.sld_speed.setValue(int(widget.rgb_speed * 10))
        self.sld_speed.valueChanged.connect(self._speed_changed)
        self.sld_speed.setStyleSheet(SLIDER_QSS)
        lay.addWidget(self.sld_speed)

        self.lbl_glow = QLabel()
        self.lbl_glow.setStyleSheet("color: #8b87a3; background: transparent;")
        self.lbl_glow.setFont(thai_font(10))
        lay.addWidget(self.lbl_glow)

        self.sld_glow = QSlider(Qt.Orientation.Horizontal)
        self.sld_glow.setRange(0, 100)
        self.sld_glow.setValue(int(widget.rgb_glow * 100))
        self.sld_glow.valueChanged.connect(self._glow_changed)
        self.sld_glow.setStyleSheet(SLIDER_QSS)
        lay.addWidget(self.sld_glow)

        self._sync()

    def retranslate(self):
        self.lbl_title.setText(T("settings_title"))
        self._sync()

    def _sync(self):
        on = self.widget.rgb_on
        self.btn_toggle.setText(T("rgb_on") if on else T("rgb_off"))
        self.btn_toggle.setStyleSheet(
            "QPushButton{color:%s;background:#2c2940;border:none;"
            "border-radius:9px;padding:8px;}"
            "QPushButton:hover{background:#37334d;}"
            % ("#d6ff5c" if on else "#8b87a3")
        )
        self.lbl_speed.setText(
            f'{T("speed")}  {self.widget.rgb_speed:.1f}{T("per_frame")}'
        )
        self.lbl_glow.setText(f'{T("glow")}  {round(self.widget.rgb_glow * 100)}%')
        self.sld_speed.setEnabled(on)
        self.sld_glow.setEnabled(on)

    def _toggle(self):
        self.widget.toggle_rgb()
        self._sync()

    def _speed_changed(self, v):
        self.widget.rgb_speed = v / 10.0
        self.widget.save_rgb()
        self._sync()

    def _glow_changed(self, v):
        self.widget.rgb_glow = v / 100.0
        self.widget.save_rgb()
        self._sync()
        self.widget.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        p.fillPath(path, QBrush(BG))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None


class UsageWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedWidth(310)
        self._drag_pos = None
        self.tab = None
        self.rows = {}

        self.slide = QPropertyAnimation(self, b"pos")
        self.slide.setDuration(ANIM_MS)

        global LANG
        cfg0 = load_config()
        LANG = cfg0.get("lang", "th")
        self.rgb_on = cfg0.get("rgb", True)
        self.rgb_speed = cfg0.get("rgb_speed", 1.6)
        self.rgb_glow = cfg0.get("rgb_glow", 1.0)
        self.rgb_angle = 0.0
        self.panel = None
        self.rgb_timer = QTimer(self)
        self.rgb_timer.timeout.connect(self._rgb_step)
        if self.rgb_on:
            self.rgb_timer.start(33)

        self.session_key = self._get_key()
        if not self.session_key:
            sys.exit(0)
        self.http = requests.Session()
        self.http.cookies.set("sessionKey", self.session_key, domain=".claude.ai")
        self.http.headers.update({"User-Agent": "claude-usage-widget/1.0"})
        self.org_id = None
        self.next_refresh = None

        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(20, 16, 20, 14)
        self.layout_main.setSpacing(14)
        self.layout_main.setContentsMargins(20, 16, 20, 8)

        # ซ้าย/ขวากว้างเท่ากัน เพื่อให้ "Usage" อยู่กึ่งกลางการ์ดพอดี
        SIDE_W = 66

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(0)

        left = QWidget()
        left.setFixedWidth(SIDE_W)
        left_l = QHBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.addWidget(CrabIcon(), 0, Qt.AlignmentFlag.AlignTop)
        left_l.addStretch()

        title = QLabel("Usage")
        title.setStyleSheet("color: #ffffff; background: transparent;")
        title.setFont(thai_font(21, QFont.Weight.Bold, serif=True))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right = QWidget()
        right.setFixedWidth(SIDE_W)
        right_l = QHBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.addStretch()
        right_l.addWidget(BatteryIcon(), 0, Qt.AlignmentFlag.AlignTop)

        header.addWidget(left)
        header.addWidget(title, 1)
        header.addWidget(right)
        self.layout_main.addLayout(header)

        self.rows_container = QVBoxLayout()
        self.rows_container.setSpacing(14)
        self.layout_main.addLayout(self.rows_container)

        self.footer = QLabel("")
        self.footer.setStyleSheet("color: #e2aa46; background: transparent;")
        self.footer.setFont(thai_font(11))
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer.hide()
        self.layout_main.addWidget(self.footer)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.addStretch()

        gear = QPushButton("⚙")
        gear.setFixedSize(30, 30)
        gear.setCursor(Qt.CursorShape.PointingHandCursor)
        gear.setToolTip("ตั้งค่าไฟ RGB")
        gear.setStyleSheet(
            "QPushButton{color:#7a7596;background:#262338;border:none;"
            "border-radius:15px;font-size:17px;}"
            "QPushButton:hover{color:#d6ff5c;background:#332f4a;}"
        )
        gear.clicked.connect(self.open_settings)
        version = QLabel(f"v{VERSION}")
        version.setStyleSheet("color: #4a4760; background: transparent;")
        version.setFont(thai_font(9))
        bottom.addWidget(version)
        bottom.addSpacing(8)

        self.btn_lang = QPushButton()
        self.btn_lang.setFixedSize(52, 30)
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.clicked.connect(self.toggle_lang)

        # ป้ายข้อความซ้อนบนปุ่ม (ปุ่มธรรมดาระบายสีคนละสีในข้อความเดียวไม่ได้)
        self.lbl_lang = QLabel(self.btn_lang)
        self.lbl_lang.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl_lang.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_lang.setGeometry(0, 0, 52, 30)
        self.lbl_lang.setStyleSheet("background: transparent;")

        self._style_lang_btn()
        bottom.addWidget(self.btn_lang)
        bottom.addSpacing(6)
        bottom.addWidget(gear)

        self.layout_main.addLayout(bottom)

        cfg = load_config()
        if "x" in cfg and "y" in cfg:
            self.move(QPoint(cfg["x"], cfg["y"]))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(REFRESH_MS)

        # ย้ำ window level เป็นระยะ กันโดนแอปอื่นทับ
        self.keep_top = QTimer(self)
        self.keep_top.timeout.connect(
            lambda: setup_macos_behavior([self if self.isVisible() else self.tab])
        )
        self.keep_top.start(3000)

        self.refresh()

        if cfg.get("hidden_side"):
            QTimer.singleShot(150, lambda: self.hide_to_edge(cfg["hidden_side"], animate=False))

    def _get_key(self):
        key = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
        if key:
            return key
        key, ok = QInputDialog.getText(
            None, "Claude Usage Widget",
            T("paste_key"),
            QLineEdit.EchoMode.Password,
        )
        if ok and key.strip():
            keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, key.strip())
            return key.strip()
        return None

    def _rgb_step(self):
        self.rgb_angle = (self.rgb_angle + self.rgb_speed) % 360
        self.update()

    def _style_lang_btn(self):
        # ใช้ QLabel ซ้อนบนปุ่ม เพื่อระบายสีเฉพาะภาษาที่ใช้อยู่
        active = "#d6ff5c"    # เขียวนีออน = ภาษาที่ใช้อยู่
        idle = "#5f5b7a"      # เทาจาง = ภาษาที่ยังไม่ได้ใช้
        if LANG == "th":
            html = (f'<span style="color:{active};">TH</span>'
                    f'<span style="color:{idle};"> / EN</span>')
        else:
            html = (f'<span style="color:{idle};">TH / </span>'
                    f'<span style="color:{active};">EN</span>')
        self.lbl_lang.setText(html)
        self.lbl_lang.setFont(thai_font(9, QFont.Weight.Bold))
        self.btn_lang.setStyleSheet(
            "QPushButton{background:#262338;border:none;border-radius:15px;}"
            "QPushButton:hover{background:#332f4a;}"
        )

    def toggle_lang(self):
        global LANG
        LANG = "en" if LANG == "th" else "th"
        cfg = load_config()
        cfg["lang"] = LANG
        save_config(cfg)
        self._style_lang_btn()
        if self.panel:
            self.panel.retranslate()
        self.refresh()

    def save_rgb(self):
        cfg = load_config()
        cfg["rgb"] = self.rgb_on
        cfg["rgb_speed"] = self.rgb_speed
        cfg["rgb_glow"] = self.rgb_glow
        save_config(cfg)

    def open_settings(self):
        if self.panel is None:
            self.panel = SettingsPanel(self)
        self.panel.move(self.x(), self.y() + self.height() + 10)
        self.panel.show()
        self.panel.raise_()
        QTimer.singleShot(60, lambda: setup_macos_behavior([self.panel]))

    def toggle_rgb(self):
        self.rgb_on = not self.rgb_on
        if self.rgb_on:
            self.rgb_timer.start(33)
        else:
            self.rgb_timer.stop()
        self.save_rgb()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        inset = 3.0
        body = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)

        if self.rgb_on:
            cx, cy = self.width() / 2, self.height() / 2
            # ชั้นเรืองแสงรอบนอก วาดจากจางไปเข้ม
            g = self.rgb_glow
            layers = ((3.0 + 6.0 * g, int(22 * g)), (3.0 + 3.0 * g, int(45 * g)), (3.0, 200))
            for width, alpha in layers:
                if alpha <= 0 and width > 3.0:
                    continue
                grad = QConicalGradient(cx, cy, self.rgb_angle)
                for i in range(13):
                    t = i / 12
                    c = QColor.fromHsvF(t % 1.0, 0.85, 1.0)
                    c.setAlpha(alpha)
                    grad.setColorAt(t, c)
                pen = QPen(QBrush(grad), width)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(body, 18, 18)

        path = QPainterPath()
        path.addRoundedRect(body, 18, 18)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(path, QBrush(BG))

    # ---------- ซ่อน / แสดง (มี animation) ----------

    def hide_to_edge(self, side, animate=True):
        if self.panel:
            self.panel.hide()
        screen = QApplication.primaryScreen().availableGeometry()
        y = max(screen.top() + 20, min(self.y(), screen.bottom() - 116))

        cfg = load_config()
        cfg["hidden_side"] = side
        cfg["hidden_y"] = y
        save_config(cfg)

        def finish():
            if self.panel:
                self.panel.hide()
            self.hide()
            if self.tab:
                self.tab.close()
            self.tab = EdgeTab(self, side)
            if side == "left":
                self.tab.move(screen.left(), y)
            else:
                self.tab.move(screen.right() - 32, y)
            self.tab.fade_in()
            QTimer.singleShot(60, lambda: setup_macos_behavior([self.tab]))

        if not animate:
            finish()
            return

        target_x = screen.left() - self.width() - 10 if side == "left" else screen.right() + 10
        self.slide.stop()
        try:
            self.slide.finished.disconnect()
        except TypeError:
            pass
        self.slide.setEasingCurve(QEasingCurve.Type.InCubic)
        self.slide.setStartValue(self.pos())
        self.slide.setEndValue(QPoint(target_x, self.y()))
        self.slide.finished.connect(finish)
        self.slide.start()

    def reveal(self):
        screen = QApplication.primaryScreen().availableGeometry()
        cfg = load_config()
        side = cfg.get("hidden_side", "right")
        y = cfg.get("hidden_y", screen.top() + 60)

        if self.tab:
            self.tab.close()
            self.tab = None

        start_x = screen.left() - self.width() - 10 if side == "left" else screen.right() + 10
        end_x = screen.left() + 12 if side == "left" else screen.right() - self.width() - 12

        self.move(start_x, y)
        self.show()
        self.raise_()
        QTimer.singleShot(60, lambda: setup_macos_behavior([self]))

        self.slide.stop()
        try:
            self.slide.finished.disconnect()
        except TypeError:
            pass
        self.slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide.setStartValue(QPoint(start_x, y))
        self.slide.setEndValue(QPoint(end_x, y))
        self.slide.start()

        cfg.pop("hidden_side", None)
        cfg["x"], cfg["y"] = end_x, y
        save_config(cfg)

    def check_snap(self):
        screen = QApplication.primaryScreen().availableGeometry()
        if self.x() <= screen.left() + SNAP_THRESHOLD:
            self.hide_to_edge("left")
            return True
        if self.x() + self.width() >= screen.right() - SNAP_THRESHOLD:
            self.hide_to_edge("right")
            return True
        return False

    # ---------- เมาส์ ----------

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _reposition_panel(self):
        if self.panel and self.panel.isVisible():
            self.panel.move(self.x(), self.y() + self.height() + 10)

    def moveEvent(self, e):
        super().moveEvent(e)
        self._reposition_panel()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _):
        self._drag_pos = None
        if not self.check_snap():
            save_config({"x": self.x(), "y": self.y()})

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        menu.setFont(thai_font(12))
        a_refresh = QAction(T("menu_refresh"), self)
        a_refresh.triggered.connect(self.refresh)
        a_hide_l = QAction(T("menu_hide_left"), self)
        a_hide_l.triggered.connect(lambda: self.hide_to_edge("left"))
        a_hide_r = QAction(T("menu_hide_right"), self)
        a_hide_r.triggered.connect(lambda: self.hide_to_edge("right"))
        a_settings = QAction(T("menu_settings"), self)
        a_settings.triggered.connect(self.open_settings)
        menu.addAction(a_settings)
        menu.addSeparator()
        a_clear = QAction(T("menu_clear"), self)
        a_clear.triggered.connect(self.clear_key)
        a_quit = QAction(T("menu_quit"), self)
        a_quit.triggered.connect(QApplication.quit)
        menu.addAction(a_refresh)
        menu.addSeparator()
        menu.addAction(a_hide_l)
        menu.addAction(a_hide_r)
        menu.addSeparator()
        menu.addAction(a_clear)
        menu.addAction(a_quit)
        menu.exec(e.globalPos())

    def clear_key(self):
        try:
            keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception:
            pass
        QMessageBox.information(self, T("cleared_title"), T("cleared_body"))

    # ---------- ข้อมูล ----------

    def sync_rows(self, entries):
        """สร้าง/ลบแถวให้ตรงกับข้อมูลที่ API ส่งมาจริง"""
        wanted = [k for k, _ in entries]

        for key in list(self.rows):
            if key not in wanted:
                w = self.rows.pop(key)
                self.rows_container.removeWidget(w)
                w.deleteLater()

        for idx, (key, node) in enumerate(entries):
            label, color = pretty_label(key)
            if key not in self.rows:
                row = Row(label, color)
                self.rows[key] = row
                self.rows_container.insertWidget(idx, row)
            else:
                self.rows[key].set_label(label)
            self.rows[key].set_value(
                node.get("utilization", 0), humanize_reset(node.get("resets_at"))
            )

        self.adjustSize()

    def refresh(self):
        try:
            if not self.org_id:
                r = self.http.get(f"{BASE_URL}/organizations", timeout=10)
                r.raise_for_status()
                orgs = r.json()
                if not orgs:
                    raise RuntimeError("ไม่พบ organization")
                self.org_id = orgs[0]["uuid"]

            r = self.http.get(f"{BASE_URL}/organizations/{self.org_id}/usage", timeout=10)
            if r.status_code == 401:
                self.footer.setText(T("session_expired"))
                self.footer.show()
                return
            r.raise_for_status()
            data = r.json()

            entries = []
            # เรียง: 5-hour → weekly → per-model
            order = ["five_hour", "seven_day"]
            for key in order:
                node = data.get(key)
                if isinstance(node, dict) and node:
                    entries.append((key, node))
            for key, node in data.items():
                if key in order:
                    continue
                if not isinstance(node, dict) or not node:
                    continue
                if node.get("utilization") is None:
                    continue
                entries.append((key, node))

            # debug: ดูว่า API ส่ง key อะไรมาบ้าง (ลบทิ้งได้)
            print("keys:", list(data.keys()))

            self.sync_rows(entries)

            self.footer.hide()

        except Exception as ex:
            self.footer.setText(f"ผิดพลาด: {type(ex).__name__}")
            self.footer.show()
            import traceback
            traceback.print_exc()


def setup_macos_behavior(widgets):
    """ทำให้ widget ลอยเหนือแอปอื่นตลอด และไม่โผล่ใน Dock/Cmd-Tab

    ต้องมี pyobjc: pip3 install pyobjc-framework-Cocoa
    ถ้าไม่มีก็ยังใช้งานได้ปกติ เพียงแต่จะมีไอคอนใน Dock
    """
    try:
        from AppKit import NSApp, NSApplicationActivationPolicyAccessory
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        # 25 = NSStatusWindowLevel ลอยเหนือหน้าต่างแอปทั่วไปทุกตัว
        for w in widgets:
            if w is None:
                continue
            view = objc.objc_object(c_void_p=int(w.winId()))
            win = view.window()
            win.setLevel_(25)
            # CanJoinAllSpaces | FullScreenAuxiliary | IgnoresCycle
            win.setCollectionBehavior_((1 << 0) | (1 << 8) | (1 << 6))
    except Exception as e:
        print(f"(ข้ามการตั้งค่าเฉพาะ macOS: {e})")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))
    w = UsageWidget()
    w.show()
    QTimer.singleShot(200, lambda: setup_macos_behavior([w]))
    sys.exit(app.exec())
