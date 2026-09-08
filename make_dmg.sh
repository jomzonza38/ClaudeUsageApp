#!/bin/bash
#
# สร้างไฟล์ .dmg สำหรับแจกจ่าย (ลากแอปไปใส่ Applications ได้แบบแอปทั่วไป)
#
# ต้อง build ด้วย install.sh ก่อน แล้วค่อยรันตัวนี้
# วิธีใช้: chmod +x make_dmg.sh && ./make_dmg.sh

set -e

APP_NAME="Claude Usage"
WORKDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKDIR"

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${GREEN}==>${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

[[ -d "dist/$APP_NAME.app" ]] || fail "ไม่พบ dist/$APP_NAME.app — รัน ./install.sh ก่อน"

VERSION=$(defaults read "$WORKDIR/dist/$APP_NAME.app/Contents/Info.plist" \
          CFBundleShortVersionString 2>/dev/null || echo "1.0.0")
DMG_NAME="ClaudeUsage-$VERSION.dmg"

info "เตรียมโครงสร้าง…"
rm -rf dmg_staging "$DMG_NAME"
mkdir -p dmg_staging
cp -R "dist/$APP_NAME.app" dmg_staging/
ln -s /Applications dmg_staging/Applications

info "สร้าง $DMG_NAME…"
hdiutil create -volname "$APP_NAME" \
    -srcfolder dmg_staging \
    -ov -format UDZO \
    "$DMG_NAME" >/dev/null

rm -rf dmg_staging

SIZE=$(du -sh "$DMG_NAME" | cut -f1)
echo
info "สร้างเสร็จ: $DMG_NAME ($SIZE)"
echo
echo "  ผู้รับเปิดไฟล์แล้วลากแอปไปใส่โฟลเดอร์ Applications ได้เลย"
echo
echo "  หมายเหตุ: ไฟล์นี้ยังไม่ได้ code sign / notarize"
echo "  เครื่องอื่นอาจโดน Gatekeeper บล็อก แก้ด้วยการคลิกขวา → Open"
echo "  หรือสั่ง: xattr -cr \"/Applications/$APP_NAME.app\""
