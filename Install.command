#!/bin/bash
#
# ตัวติดตั้ง Claude Usage Widget — ดับเบิลคลิกไฟล์นี้ได้เลย
#
# ครั้งแรกอาจโดน macOS บล็อก ให้คลิกขวาที่ไฟล์ → Open → กด Open อีกครั้ง

cd "$(dirname "$0")"

clear
cat <<'BANNER'

   ┌─────────────────────────────────────────┐
   │                                         │
   │      Claude Usage Widget                │
   │      ตัวติดตั้งสำหรับ macOS                  │
   │                                         │
   └─────────────────────────────────────────┘

BANNER

# ปลดล็อกไฟล์ที่ดาวน์โหลดมา (quarantine flag ทำให้รันไม่ได้)
xattr -d com.apple.quarantine ./*.sh ./*.py 2>/dev/null || true
chmod +x ./*.sh 2>/dev/null || true

if [[ ! -f install.sh ]]; then
    echo "  ✗ ไม่พบ install.sh"
    echo
    echo "  ไฟล์ต่อไปนี้ต้องอยู่โฟลเดอร์เดียวกันทั้งหมด:"
    echo "     • Install.command   (ไฟล์นี้)"
    echo "     • install.sh"
    echo "     • claude_usage_widget.py"
    echo "     • make_icon.py      (ไม่บังคับ — ใช้สร้างไอคอน)"
    echo
    echo "  กด Enter เพื่อปิดหน้าต่าง"
    read -r
    exit 1
fi

echo "  กำลังเริ่มติดตั้ง…"
echo "  (ใช้เวลาประมาณ 3-5 นาที ส่วนใหญ่หมดไปกับขั้นตอน build)"
echo

./install.sh
STATUS=$?

echo
if [[ $STATUS -eq 0 ]]; then
    echo "  ─────────────────────────────────────────"
    echo "  เสร็จเรียบร้อย ปิดหน้าต่างนี้ได้เลย"
    echo "  ─────────────────────────────────────────"
else
    echo "  ─────────────────────────────────────────"
    echo "  ติดตั้งไม่สำเร็จ (รหัส $STATUS)"
    echo "  ลองอ่านข้อความด้านบนเพื่อดูสาเหตุ"
    echo "  ─────────────────────────────────────────"
fi

echo
echo "  กด Enter เพื่อปิด"
read -r
