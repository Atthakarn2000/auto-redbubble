import os
import time
import uuid
import requests
import openai
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

# — เช็คว่ามี API key ใน ENV จริงหรือไม่
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("❌ No OPENAI_API_KEY env found")

# — ดึง Credentials Redbubble
RB_EMAIL = os.getenv("RB_EMAIL")
RB_PASS  = os.getenv("RB_PASS")
if not (RB_EMAIL and RB_PASS):
    raise RuntimeError("❌ No RB_EMAIL or RB_PASS env found")

# — ตัวอย่าง prompt list
prompts = [
    "Minimalist cartoon cat T-shirt design, flat style, transparent background"
]

def gen_and_upscale(prompt, n=1):
    """Generate via DALL·E → upscale → return list of PIL Images."""
    # 1) สร้างภาพขนาด 1024×1024
    resp = openai.Image.create(
        prompt=prompt, n=n,
        size="1024x1024",     # ขนาดที่ DALL·E รองรับ
        response_format="url"
    )
    files = []
    for data in resp["data"]:
        img_url = data["url"]
        r = requests.get(img_url)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")

        # 2) Upscale เป็น 4500×5400 ด้วย Pillow
        img = img.resize((4500, 5400), Image.LANCZOS)
        files.append(img)

    return files

def login_and_upload(images, prompt_text):
    """ใช้ Playwright ล็อกอิน Redbubble แล้วอัปโหลดภาพแต่ละภาพเป็นงานใหม่"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 1) เข้าเว็บ Redbubble, ล็อกอิน ฯลฯ
        page.goto("https://www.redbubble.com/auth/login")
        page.fill('input[name="username"]', RB_EMAIL)
        page.fill('input[name="password"]', RB_PASS)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        # 2) ไปหน้า Add New Work
        page.goto("https://www.redbubble.com/portfolio/images/new")
        for img in images:
            # เตรียมไฟล์ชั่วคราว
            fn = f"/tmp/{uuid.uuid4().hex}.png"
            img.save(fn, format="PNG", dpi=(300,300))
            # อัปโหลด
            page.set_input_files('input[type="file"]', fn)
            # รออัปโหลด-ประมวลผลแล้วใส่ Title/Tags ฯลฯ
            page.fill('input[name="title"]', prompt_text[:80])
            # … เพิ่ม description / tags ตามต้องการ …
            page.click('button:has-text("Save work")')
            page.wait_for_timeout(10000)

        browser.close()

def main():
    for prompt in prompts:
        images = gen_and_upscale(prompt, n=3)
        login_and_upload(images, prompt)

if __name__ == "__main__":
    main()
