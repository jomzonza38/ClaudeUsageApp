#!/bin/bash
#
# เซ็นชื่อ + notarize แอป แล้วออกเป็น .dmg ที่เปิดได้ทุกเครื่องโดยไม่โดน Gatekeeper บล็อก
#
# ── เตรียมครั้งเดียว ──────────────────────────────────────────
#   1. ต้องมี certificate "Developer ID Application" ใน Keychain
#      ดูว่ามีอะไรบ้าง:  security find-identity -v -p codesigning
#   2. สร้าง app-specific password ที่ appleid.apple.com → Sign-In and Security
#   3. เก็บ credential ไว้ใน Keychain (ทำครั้งเดียวพอ):
#        xcrun notarytool store-credentials "claudeusage" \
#              --apple-id "you@example.com" \
#              --team-id "U6X9GG6R4N" \
#              --password "xxxx-xxxx-xxxx-xxxx"
#
# ── วิธีใช้ ────────────────────────────────────────────────
#   ./install.sh --build-only
#   SIGN_ID="Developer ID Application: ชื่อคุณ (U6X9GG6R4N)" ./notarize.sh
#
set -e

APP_NAME="Claude Usage"
TEAM_ID="${TEAM_ID:-U6X9GG6R4N}"
PROFILE="${NOTARY_PROFILE:-claudeusage}"
WORKDIR="$(cd "$(dirname "$0")" && pwd)"
APP="$WORKDIR/dist/$APP_NAME.app"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}==>${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

cd "$WORKDIR"

# ---------- ตรวจของที่ต้องมี ----------
[[ -d "$APP" ]] || fail "ไม่พบ $APP — รัน ./install.sh --build-only ก่อน"
command -v xcrun >/dev/null || fail "ไม่พบ xcrun — ติดตั้ง Xcode Command Line Tools ก่อน"
[[ -f entitlements.plist ]] || fail "ไม่พบ entitlements.plist"

if [[ -z "${SIGN_ID:-}" ]]; then
    echo "ยังไม่ได้ตั้ง SIGN_ID — certificate ที่ใช้เซ็นได้ในเครื่องนี้:"
    security find-identity -v -p codesigning || true
    echo
    fail 'ตั้งค่าแล้วรันใหม่ เช่น: SIGN_ID="Developer ID Application: ชื่อคุณ ('"$TEAM_ID"')" ./notarize.sh'
fi

xcrun notarytool history --keychain-profile "$PROFILE" >/dev/null 2>&1 \
    || fail "ไม่พบ credential ชื่อ \"$PROFILE\" — ดูวิธีสร้างที่หัวสคริปต์"

# ---------- เซ็นชื่อ ----------
info "เซ็นไฟล์ย่อยข้างในก่อน (.so / .dylib / framework)…"
find "$APP" \( -name "*.so" -o -name "*.dylib" -o -name "*.framework" \) -print0 \
| while IFS= read -r -d '' f; do
    codesign --force --timestamp --options runtime \
             --entitlements entitlements.plist \
             --sign "$SIGN_ID" "$f" >/dev/null 2>&1 || true
done

info "เซ็นตัวแอป…"
codesign --force --deep --timestamp --options runtime \
         --entitlements entitlements.plist \
         --sign "$SIGN_ID" "$APP"

info "ตรวจลายเซ็น…"
codesign --verify --deep --strict --verbose=2 "$APP"

# ---------- ทำ dmg ----------
info "สร้าง .dmg…"
./make_dmg.sh >/dev/null
DMG=$(ls -t ClaudeUsage-*.dmg | head -1)
[[ -n "$DMG" ]] || fail "ไม่พบไฟล์ .dmg ที่เพิ่งสร้าง"

info "เซ็น $DMG…"
codesign --force --timestamp --sign "$SIGN_ID" "$DMG"

# ---------- notarize ----------
info "ส่ง $DMG ให้ Apple ตรวจ (รอ 2-10 นาที)…"
xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait

info "แนบผลการตรวจติดไฟล์ (staple)…"
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"

# ---------- ตรวจซ้ำแบบที่ Gatekeeper เห็น ----------
info "ตรวจแบบเดียวกับที่เครื่องปลายทางจะเห็น…"
spctl -a -vvv -t install "$DMG" || warn "spctl ไม่ผ่าน — ลองดูข้อความด้านบน"

SIZE=$(du -sh "$DMG" | cut -f1)
echo
echo -e "${GREEN}────────────────────────────────────${NC}"
echo -e "${GREEN} เรียบร้อย: $DMG ($SIZE)${NC}"
echo -e "${GREEN}────────────────────────────────────${NC}"
echo " ไฟล์นี้เปิดได้เลยทุกเครื่อง ไม่ต้องคลิกขวา → Open อีกต่อไป"
echo " อัปโหลดขึ้น GitHub Releases ได้เลย"
echo
