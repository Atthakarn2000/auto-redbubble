#!/usr/bin/env python3
import os, sys, logging
from playwright.sync_api import sync_playwright

# — config —
RB_EMAIL = os.getenv("RB_EMAIL")
RB_PASS  = os.getenv("RB_PASS")
if not RB_EMAIL or not RB_PASS:
    print("❌ ต้องตั้ง RB_EMAIL / RB_PASS เป็น GitHub Secrets ก่อน")
    sys.exit(1)

DESIGN_DIR = "designs"   # โฟลเดอร์ที่วาง .png ไฟล์
UPLOAD_URL = "https://www.redbubble.com/portfolio/upload"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

def login(page):
    logging.info("🔑 Logging in…")
    page.goto("https://www.redbubble.com/auth/login")
    page.fill("input[name='username']", RB_EMAIL)
    page.fill("input[name='password']", RB_PASS)
    page.click("button[type='submit']")
    page.wait_for_url("https://www.redbubble.com/portfolio", timeout=60000)

def upload_one(page, img_path):
    title = os.path.splitext(os.path.basename(img_path))[0]
    desc  = title
    logging.info("📤 Uploading %s …", img_path)
    page.goto(UPLOAD_URL)
    page.set_input_files("input[type='file']", img_path)
    page.fill("input[name='title']", title)
    page.fill("textarea[name='description']", desc)
    page.click("button[type='submit']")
    # รอจนเห็นคำว่า “Success” หรือ element ยืนยันการอัปโหลด
    page.wait_for_selector("text=Success", timeout=120000)
    url = page.url
    logging.info("✅ Done: %s → %s", img_path, url)

def main():
    designs = sorted(f for f in os.listdir(DESIGN_DIR) if f.lower().endswith(".png"))
    if not designs:
        logging.error("❌ ไม่มีไฟล์ .png ใน %s", DESIGN_DIR)
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login(page)
        for fn in designs:
            path = os.path.join(DESIGN_DIR, fn)
            upload_one(page, path)
        browser.close()

if __name__ == "__main__":
    main()
