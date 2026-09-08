#!/bin/bash
#
# ตัวถอนการติดตั้ง Claude Usage Widget — ดับเบิลคลิกได้เลย

cd "$(dirname "$0")"

clear
echo
echo "   ถอนการติดตั้ง Claude Usage Widget"
echo "   ─────────────────────────────────────"
echo

chmod +x ./uninstall.sh 2>/dev/null || true

if [[ ! -f uninstall.sh ]]; then
    echo "   ✗ ไม่พบ uninstall.sh ในโฟลเดอร์นี้"
    echo
    echo "   กด Enter เพื่อปิด"
    read -r
    exit 1
fi

./uninstall.sh

echo
echo "   กด Enter เพื่อปิด"
read -r
