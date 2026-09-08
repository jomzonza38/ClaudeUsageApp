#!/bin/bash
#
# ถอนการติดตั้ง Claude Usage Widget
#
# วิธีใช้: chmod +x uninstall.sh && ./uninstall.sh

set -e

APP_NAME="Claude Usage"
BUNDLE_ID="com.worawalan.claudeusage"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}==>${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }

info "ปิดแอป…"
osascript -e "quit app \"$APP_NAME\"" 2>/dev/null || true
sleep 1

PLIST="$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"
if [[ -f "$PLIST" ]]; then
    info "ยกเลิกการเปิดอัตโนมัติ…"
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
fi

if [[ -d "/Applications/$APP_NAME.app" ]]; then
    info "ลบแอปออกจาก /Applications…"
    rm -rf "/Applications/$APP_NAME.app"
fi

CONFIG="$HOME/.claude_usage_widget.json"
if [[ -f "$CONFIG" ]]; then
    read -r -p "ลบไฟล์ตั้งค่า (ตำแหน่ง/ภาษา/RGB) ด้วยไหม? [y/N] " REPLY
    [[ "$REPLY" =~ ^[Yy]$ ]] && rm -f "$CONFIG" && info "ลบไฟล์ตั้งค่าแล้ว"
fi

echo
read -r -p "ลบ sessionKey ออกจาก Keychain ด้วยไหม? [y/N] " REPLY
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    security delete-generic-password -s "claude-usage-bar" 2>/dev/null \
        && info "ลบ sessionKey แล้ว" \
        || warn "ไม่พบ sessionKey ใน Keychain"
fi

echo
info "ถอนการติดตั้งเรียบร้อย"
warn "โฟลเดอร์ build (venv/, build/, dist/) ยังอยู่ ลบเองได้ถ้าไม่ใช้แล้ว"
