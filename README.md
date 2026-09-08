# Claude Usage Widget

![platform](https://img.shields.io/badge/platform-macOS%2012%2B-000000?logo=apple&logoColor=white)
![python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)
[![release](https://img.shields.io/github/v/release/jomzonza38/ClaudeUsageApp?color=7a6fd6)](https://github.com/jomzonza38/ClaudeUsageApp/releases/latest)
[![license](https://img.shields.io/badge/license-MIT-d6ff5c)](LICENSE)

Floating widget บนเดสก์ท็อป macOS สำหรับดูโควตาการใช้งาน Claude แบบเรียลไทม์ — ไม่ต้องเปิดเว็บไปเช็คเอง

เขียนด้วย Python + PyQt6 แล้ว build เป็นแอป `.app` ด้วย py2app

<p align="center">
  <img src="myicon.png" alt="Claude Usage Widget" width="128">
</p>

## ฟีเจอร์

- อัปเดตอัตโนมัติทุก 5 วินาที
- แถวข้อมูลสร้างตาม API จริง — โมเดลไหนถูกใช้ก็ขึ้นแถวนั้น
- นับถอยหลังเวลารีเซ็ตโควตาแบบอ่านง่าย
- ลากย้ายตำแหน่งได้ และจำตำแหน่งไว้ให้
- ลากไปชิดขอบซ้าย/ขวา → เลื่อนซ่อนอัตโนมัติ เหลือแท็บเล็ก ๆ ให้กดเรียกกลับ
- แสดงเปอร์เซ็นต์แบตเตอรี่
- ขอบ RGB เรืองแสงปรับความเร็ว/สีได้ในหน้าตั้งค่า
- สลับภาษาไทย/อังกฤษ
- ดับเบิลคลิกที่ส่วนหัว = ย่อไปขอบขวาทันที
- ตอนย่อเป็นแท็บ แสดง % ที่เหลือของลิมิตที่ตึงที่สุด ไล่สีตามการใช้งาน
- โหมดแถบเมนู (menu bar) แสดง % ปรับสีตามธีมระบบ
- แจ้งเตือนเมื่อใช้ถึง 90% และเมื่อมีข่าวใหม่จาก Anthropic
- กราฟแนวโน้มการใช้งานย้อนหลัง 7 วัน
- ทำเครื่องหมาย ● ที่โมเดลซึ่งโควตากำลังเดิน (อนุมานจากค่าที่ขยับ)
- ซ่อนโมเดลที่ยังไม่ได้ใช้โดยอัตโนมัติ
- คลิกขวา: รีเฟรช / ซ่อน / ตั้งค่า / ล้าง sessionKey / ปิด
- `sessionKey` เก็บใน macOS Keychain ไม่ได้เขียนลงไฟล์

## สิ่งที่ต้องมีก่อน

| อย่าง | หมายเหตุ |
|---|---|
| macOS | สคริปต์เช็ค `uname` ถ้าไม่ใช่ Darwin จะหยุดทันที |
| Python 3 | ถ้ายังไม่มีโหลดจาก [python.org](https://www.python.org) |
| บัญชี claude.ai | ต้องใช้ `sessionKey` จากคุกกี้ (ดูหัวข้อด้านล่าง) |

dependency ทั้งหมดล็อกเวอร์ชันไว้ใน [`requirements.txt`](requirements.txt) แล้ว ตัวติดตั้งจะลงให้เองใน virtualenv แยก ไม่ไปยุ่งกับ Python ของเครื่อง

## ติดตั้ง

### 1. โหลดโปรเจกต์ลงมา

```bash
git clone https://github.com/jomzonza38/ClaudeUsageApp.git
cd ClaudeUsageApp
```

หรือกดปุ่มเขียว **Code → Download ZIP** บนหน้า GitHub แล้วแตกไฟล์

### 2. รันตัวติดตั้ง

**แบบดับเบิลคลิก**

ดับเบิลคลิก `Install.command` ได้เลย

> ครั้งแรก macOS มักบล็อกเพราะไฟล์โหลดมาจากอินเทอร์เน็ต ให้ **คลิกขวาที่ไฟล์ → Open → กด Open ซ้ำ** ในกล่องที่เด้งขึ้นมา

**แบบ Terminal**

```bash
chmod +x install.sh
./install.sh
```

ใช้เวลาราว 3-5 นาที ส่วนใหญ่หมดไปกับขั้นตอน build

### 3. ระหว่างติดตั้งจะมีคำถาม 2 ข้อ

- `ตั้งให้เปิดอัตโนมัติตอนเปิดเครื่องด้วยไหม?` — ตอบ `y` จะสร้าง LaunchAgent ให้ (ยกเลิกทีหลังได้ด้วย `./uninstall.sh`)
- `เปิดแอปเลยไหม?` — ตอบ `Y` แอปจะเด้งขึ้นมาทันที

### ตัวติดตั้งทำอะไรบ้าง

1. สร้าง `venv/` แล้วลง dependency ทั้งหมดในนั้น
2. แปลง `myicon.png` เป็น `icon.icns` ด้วย `sips` + `iconutil` (ถ้ามี `icon.icns` อยู่แล้วจะข้าม)
3. generate `setup.py` ใหม่ทุกครั้ง แล้ว build `.app` ด้วย py2app
4. คัดลอกไปที่ `/Applications/Claude Usage.app` แล้วลบ quarantine flag ออก
5. (ถ้าตอบ y) ติดตั้ง LaunchAgent สำหรับเปิดตอนบูต

## ตั้งค่าครั้งแรก — ใส่ sessionKey

เปิดแอปครั้งแรกจะมีช่องให้กรอก `sessionKey` หาได้แบบนี้:

1. เปิด [claude.ai](https://claude.ai) ในเบราว์เซอร์ แล้วล็อกอินให้เรียบร้อย
2. กด **⌘ + ⌥ + I** เปิด DevTools
3. ไปแท็บ **Application** → เมนูซ้าย **Cookies** → เลือก `https://claude.ai`
4. หาแถวชื่อ `sessionKey` แล้วคัดลอกค่าในช่อง Value
5. วางลงในช่องที่แอปถาม

ค่านี้จะถูกเก็บใน **macOS Keychain** (service: `claude-usage-bar`) ไม่ได้เขียนลงไฟล์ใด ๆ ในโปรเจกต์

> `sessionKey` มีค่าเท่ากับรหัสผ่านบัญชี Claude ของคุณ — อย่าแชร์ให้ใคร และอย่า commit ขึ้น repo

ถ้าจะเปลี่ยนคีย์ทีหลัง: คลิกขวาที่ widget → **ล้าง sessionKey** แล้วเปิดแอปใหม่

## ไฟล์ตั้งค่า

`~/.claude_usage_widget.json` เก็บตำแหน่ง widget, ภาษา, และการตั้งค่าขอบ RGB — ลบไฟล์นี้เท่ากับรีเซ็ตค่าทั้งหมดกลับเป็นค่าเริ่มต้น

## ถอนการติดตั้ง

```bash
chmod +x uninstall.sh
./uninstall.sh
```

จะปิดแอป → ลบ LaunchAgent → ลบแอปออกจาก `/Applications` แล้วถามต่อว่าจะลบไฟล์ตั้งค่าและ `sessionKey` ใน Keychain ด้วยไหม

โฟลเดอร์ `venv/`, `build/`, `dist/` จะยังอยู่ ลบเองได้ถ้าไม่ใช้แล้ว

## สร้างไฟล์ .dmg สำหรับแจกจ่าย

ต้อง `./install.sh` ให้ build ผ่านก่อน แล้วค่อยรัน:

```bash
chmod +x make_dmg.sh
./make_dmg.sh
```

ได้ไฟล์ `ClaudeUsage-<version>.dmg` ที่ผู้รับเปิดแล้วลากแอปไปใส่ Applications ได้เลย

### เซ็นชื่อ + notarize (แนะนำถ้าจะแจกให้คนอื่น)

ไฟล์ที่ไม่ได้เซ็นจะโดน Gatekeeper บล็อกที่เครื่องปลายทาง ต้องสอนให้คลิกขวา → Open ทุกครั้ง
ถ้ามีบัญชี Apple Developer ใช้ `notarize.sh` จบปัญหานี้ได้:

```bash
./install.sh --build-only
SIGN_ID="Developer ID Application: ชื่อคุณ (TEAMID)" ./notarize.sh
```

สคริปต์จะเซ็นไฟล์ย่อยทั้งหมด → เซ็นแอป → ทำ dmg → ส่งให้ Apple ตรวจ → staple ผลติดไฟล์
วิธีเตรียม certificate กับ credential อ่านได้ที่หัวไฟล์ `notarize.sh`

### ปล่อยเวอร์ชันใหม่อัตโนมัติ

`.github/workflows/build.yml` จะ build `.dmg` แล้วแนบเข้า GitHub Release ให้เองเมื่อ push tag:

```bash
git tag v1.4.0
git push origin v1.4.0
```

> ไฟล์จาก CI ยังไม่ได้เซ็น (certificate อยู่ในเครื่องคุณ ไม่ได้อยู่บน runner)
> ถ้าจะแจกจริงจัง ให้ใช้ `notarize.sh` บนเครื่องแล้วอัปโหลดทับ

## ปัญหาที่เจอบ่อย

**ดับเบิลคลิก `Install.command` แล้วไม่มีอะไรเกิดขึ้น / ขึ้นว่าเปิดไม่ได้**
คลิกขวาที่ไฟล์ → Open → กด Open ซ้ำ หรือสั่ง `xattr -d com.apple.quarantine Install.command`

**ขึ้นว่า "ไม่พบ python3"**
ติดตั้ง Python 3 จาก python.org แล้วเปิด Terminal ใหม่

**build ไม่สำเร็จ**
รัน `source venv/bin/activate && python setup.py py2app` เพื่อดู error เต็ม ๆ (ตัวติดตั้งกรอง output ไว้)

**เปิดแอปแล้วโดน Gatekeeper บล็อก**
แอปยังไม่ได้ code sign / notarize — แก้ด้วย `xattr -cr "/Applications/Claude Usage.app"` หรือคลิกขวาที่แอป → Open

**ตัวเลขไม่อัปเดต / ขึ้น error**
`sessionKey` น่าจะหมดอายุแล้ว (เกิดตอนล็อกเอาต์หรือเปลี่ยนรหัสผ่าน) — คลิกขวา → ล้าง sessionKey แล้วใส่ค่าใหม่

## ข้อควรรู้

แอปนี้เรียก endpoint ภายในของ claude.ai ที่ **ไม่มีเอกสารทางการรองรับ** ถ้า Anthropic เปลี่ยนโครงสร้าง response เมื่อไหร่ แอปอาจพังได้ และไม่ได้เกี่ยวข้องกับ Anthropic แต่อย่างใด

เป็นโปรเจกต์ส่วนตัว ใช้เองเป็นหลัก

## ภาพประกอบ

ตอนนี้หัว README ใช้ไอคอนแอปไปพลางก่อน ถ้าจะใส่ภาพจริง:

**ภาพนิ่ง**

1. กด `⌘ + ⇧ + 4` แล้วกด `Space` → เคอร์เซอร์เปลี่ยนเป็นรูปกล้อง
2. คลิกที่ widget → ได้ภาพเฉพาะหน้าต่างพร้อมเงาโปร่งใส ไปอยู่บนเดสก์ท็อป
3. ย้ายเข้าโปรเจกต์แล้วเปลี่ยน `myicon.png` ในหัว README เป็น `docs/screenshot.png`

```bash
mkdir -p docs
mv ~/Desktop/"Screenshot "*.png docs/screenshot.png
```

**ภาพเคลื่อนไหว** (แนะนำ — ขอบ RGB กับจังหวะเลื่อนซ่อนต้องเห็นเคลื่อนไหวถึงจะเข้าใจ)

```bash
# ⌘ + ⇧ + 5 → บันทึกส่วนที่เลือก → กด Stop บนแถบเมนู → ได้ .mov บนเดสก์ท็อป
brew install ffmpeg     # ถ้ายังไม่มี
ffmpeg -i ~/Desktop/screen.mov -vf "fps=15,scale=380:-1:flags=lanczos" -loop 0 docs/demo.gif
```

แล้วเปลี่ยนบรรทัดภาพในหัว README เป็น `docs/demo.gif`

> GIF ที่ยาวเกิน 10 วินาทีจะไฟล์ใหญ่มาก ตัดให้เหลือ 5-8 วินาทีกำลังดี

## License

[MIT](LICENSE) — Copyright (c) 2026 Worawalan Kongsom
