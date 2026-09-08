#!/bin/bash
#
# ตัวติดตั้ง Claude Usage Widget สำหรับ macOS
#
# วิธีใช้:
#   1. วางไฟล์นี้ไว้โฟลเดอร์เดียวกับ claude_usage_widget.py
#   2. chmod +x install.sh
#   3. ./install.sh
#
# สคริปต์จะ: สร้าง venv → ลง dependency → สร้างไอคอน → build .app
#            → ติดตั้งลง /Applications → (ถามก่อน) ตั้งให้เปิดเองตอนบูต

set -e

APP_NAME="Claude Usage"
BUNDLE_ID="com.worawalan.claudeusage"
SCRIPT="claude_usage_widget.py"
WORKDIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}==>${NC} $1"; }
warn()  { echo -e "${YELLOW}!${NC} $1"; }
fail()  { echo -e "${RED}✗${NC} $1"; exit 1; }

cd "$WORKDIR"

# ---------- ตรวจสภาพแวดล้อม ----------
[[ "$(uname)" == "Darwin" ]] || fail "สคริปต์นี้ใช้ได้เฉพาะ macOS"
command -v python3 >/dev/null || fail "ไม่พบ python3 — ติดตั้งจาก https://www.python.org ก่อน"
[[ -f "$SCRIPT" ]] || fail "ไม่พบ $SCRIPT ในโฟลเดอร์นี้"

PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "พบ Python $PYVER"

VERSION=$(grep -m1 '^VERSION = ' "$SCRIPT" | sed 's/.*"\(.*\)".*/\1/')
[[ -n "$VERSION" ]] || VERSION="1.0.0"
info "เวอร์ชัน $VERSION"

# ---------- venv ----------
if [[ ! -d venv ]]; then
    info "สร้าง virtualenv…"
    python3 -m venv venv
else
    info "ใช้ virtualenv เดิม"
fi
source venv/bin/activate

info "ติดตั้ง dependency (อาจใช้เวลาสักครู่)…"
pip install --upgrade pip -q
if [[ -f requirements.txt ]]; then
    pip install -q -r requirements.txt
else
    pip install -q py2app PyQt6 requests keyring pyobjc-framework-Cocoa pillow
fi

# ---------- ไอคอน ----------
if [[ -f icon.icns ]]; then
    info "ใช้ icon.icns เดิม"
else
    PNG=""
    for f in myicon.png claude_usage_icon.png icon.png; do
        if [[ -f "$f" ]] && file "$f" | grep -q "PNG image data"; then
            PNG="$f"; break
        fi
    done

    if [[ -z "$PNG" && -f make_icon.py ]]; then
        info "ไม่พบไฟล์ PNG — สร้างไอคอนใหม่จาก make_icon.py"
        python - <<'PYEOF'
import re, pathlib
src = pathlib.Path("make_icon.py").read_text()
src = src.replace('"/mnt/user-data/outputs/claude_usage_icon.png"', '"myicon.png"')
exec(compile(src, "make_icon.py", "exec"))
PYEOF
        PNG="myicon.png"
    fi

    if [[ -n "$PNG" ]]; then
        info "แปลง $PNG เป็น .icns…"
        rm -rf icon.iconset && mkdir -p icon.iconset
        for spec in "16 icon_16x16" "32 icon_16x16@2x" "32 icon_32x32" \
                    "64 icon_32x32@2x" "128 icon_128x128" "256 icon_128x128@2x" \
                    "256 icon_256x256" "512 icon_256x256@2x" "512 icon_512x512" \
                    "1024 icon_512x512@2x"; do
            set -- $spec
            sips -z "$1" "$1" "$PNG" --out "icon.iconset/$2.png" >/dev/null 2>&1
        done
        iconutil -c icns icon.iconset -o icon.icns
        rm -rf icon.iconset
        info "สร้าง icon.icns สำเร็จ"
    else
        warn "ไม่พบไอคอน — จะใช้ไอคอน default"
    fi
fi

# ---------- setup.py ----------
info "สร้าง setup.py…"
ICONLINE=""
[[ -f icon.icns ]] && ICONLINE="'iconfile': 'icon.icns',"

cat > setup.py <<EOF
from setuptools import setup

setup(
    app=['$SCRIPT'],
    name='$APP_NAME',
    options={'py2app': {
        $ICONLINE
        'plist': {
            'CFBundleName': '$APP_NAME',
            'CFBundleDisplayName': '$APP_NAME',
            'CFBundleIdentifier': '$BUNDLE_ID',
            'CFBundleVersion': '$VERSION',
            'CFBundleShortVersionString': '$VERSION',
            'LSUIElement': True,
            'NSHighResolutionCapable': True,
        },
        'packages': ['PyQt6', 'requests', 'keyring'],
        'includes': ['objc', 'AppKit'],
        'excludes': ['PyQt6.QtWebEngineCore', 'PyQt6.QtQuick', 'PyQt6.Qt3DCore',
                     'PyQt6.QtMultimedia', 'PyQt6.QtBluetooth', 'PyQt6.QtQml',
                     'tkinter', 'matplotlib', 'numpy', 'PIL'],
    }},
    setup_requires=['py2app'],
)
EOF

# ---------- build ----------
info "กำลัง build (1-3 นาที)…"
rm -rf build dist
python setup.py py2app -q 2>&1 | grep -Ei "error|warning: mod" || true

[[ -d "dist/$APP_NAME.app" ]] || fail "build ไม่สำเร็จ — ลองรัน: python setup.py py2app"

SIZE=$(du -sh "dist/$APP_NAME.app" | cut -f1)
info "build สำเร็จ ($SIZE)"

# ---------- ติดตั้ง ----------
if [[ -d "/Applications/$APP_NAME.app" ]]; then
    warn "พบแอปเดิมอยู่แล้ว กำลังแทนที่…"
    osascript -e "quit app \"$APP_NAME\"" 2>/dev/null || true
    sleep 1
    rm -rf "/Applications/$APP_NAME.app"
fi

info "ติดตั้งลง /Applications…"
cp -R "dist/$APP_NAME.app" /Applications/
xattr -cr "/Applications/$APP_NAME.app" 2>/dev/null || true

# ---------- เปิดเองตอนบูต ----------
echo
read -r -p "ตั้งให้เปิดอัตโนมัติตอนเปิดเครื่องด้วยไหม? [y/N] " REPLY
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    PLIST="$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$BUNDLE_ID</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-a</string>
        <string>/Applications/$APP_NAME.app</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST"
    info "ตั้งค่าเปิดอัตโนมัติแล้ว (ยกเลิกได้ด้วย ./uninstall.sh)"
fi

# ---------- เสร็จ ----------
echo
echo -e "${GREEN}────────────────────────────────────${NC}"
echo -e "${GREEN} ติดตั้งสำเร็จ${NC}"
echo -e "${GREEN}────────────────────────────────────${NC}"
echo " แอป:  /Applications/$APP_NAME.app"
echo " ขนาด: $SIZE"
echo
echo " ครั้งแรกที่เปิด จะถาม sessionKey"
echo " หาได้จาก: claude.ai → DevTools (Cmd+Option+I)"
echo "          → Application → Cookies → sessionKey"
echo

read -r -p "เปิดแอปเลยไหม? [Y/n] " REPLY
[[ "$REPLY" =~ ^[Nn]$ ]] || open -a "/Applications/$APP_NAME.app"
