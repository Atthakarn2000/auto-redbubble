#!/usr/bin/env python3
import os
import time
import uuid
import logging
from io import BytesIO

import openai
import requests
from PIL import Image

from playwright.sync_api import sync_playwright


# ─── CONFIG ────────────────────────────────────────────────────────────────────
# ต้องตั้ง ENV:
#   OPENAI_API_KEY  – คีย์ OpenAI (DALL·E)
#   RB_EMAIL        – อีเมล Redbubble
#   RB_PASS         – รหัสผ่าน Redbubble

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("❌ No OPENAI_API_KEY env found")

RB_EMAIL = os.getenv("RB_EMAIL")
RB_PASS  = os.getenv("RB_PASS")
if not RB_EMAIL or not RB_PASS:
    raise RuntimeError("❌ No Redbubble credentials in env (RB_EMAIL/RB_PASS)")

# ตั้งค่าความละเอียดเอาตามที่ Redbubble รับ
DALL_SIZE      = "1024x1024"
TARGET_WIDTH   = 4500
TARGET_HEIGHT  = 5400
OUTPUT_FORMAT  = "PNG"   # Redbubble รองรับ PNG โปร่งใส
PROMPT         = "Minimalist cartoon cat T-shirt design, flat style, transparent background"

# เปิด debug log ของ OpenAI (ถ้าต้องการ)
# logging.basicConfig(level=logging.DEBUG)
# openai.log = "debug"


def gen_and_upscale(prompt: str, n: int = 1):
    """
    1) สร้างภาพ n ภาพด้วย DALL·E (1024×1024)
    2) อัปสเกลเป็น 4500×5400 px แบบ letterbox (transparent)
    คืน list ของ PIL.Image
    """
    print(f"🖌 [1] Generating {n} image(s) at {DALL_SIZE} from OpenAI…")
    resp = openai.Image.create(
        prompt=prompt,
        n=n,
        size=DALL_SIZE,
        response_format="url"
    )
    images = []
    for item in resp["data"]:
        url = item["url"]
        r = requests.get(url)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")

        # letterbox to TARGET_WIDTH x TARGET_HEIGHT
        ratio = min(TARGET_WIDTH / img.width, TARGET_HEIGHT / img.height)
        new_w, new_h = int(img.width * ratio), int(img.height * ratio)
        img_resized = img.resize((new_w, new_h), Image.LANCZOS)

        # canvas with transparency
        canvas = Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0, 0))
        x = (TARGET_WIDTH  - new_w) // 2
        y = (TARGET_HEIGHT - new_h) // 2
        canvas.paste(img_resized, (x, y), img_resized)
        images.append(canvas)

    print(f"✅ [1] Done generating & upscaling {n} image(s).")
    return images


def login_redbubble(page):
    """ล็อกอินเข้า Redbubble"""
    print("🔐 [2] Logging into Redbubble…")
    page.goto("https://www.redbubble.com/auth/login/traditional", timeout=60000)
    page.fill('input[name="username"]', RB_EMAIL)
    page.fill('input[name="password"]', RB_PASS)
    page.click('button[type="submit"]')
    # รอหน้า portfolio หรือ dashboard ปรากฎ
    page.wait_for_selector("header[aria-label='Redbubble']", timeout=60000)
    print("✅ [2] Logged in successfully.")


def upload_to_redbubble(page, image: Image.Image, title: str, description: str, tags: list):
    """
    อัปโหลดภาพเดียวเป็นงานใหม่
    คืน URL ของเพจดีไซน์
    """
    uid = uuid.uuid4().hex[:8]
    fname = f"design_{uid}.png"
    print(f"📤 [3] Uploading design as '{fname}'…")

    # save ชั่วคราวใน memory แล้วอัปโหลด
    buf = BytesIO()
    image.save(buf, OUTPUT_FORMAT)
    buf.seek(0)

    page.goto("https://www.redbubble.com/portfolio/images/upload", timeout=60000)
    # กรอกไฟล์
    # Input type="file" อาจอยู่ใน iframe; ปรับ selector ตามจริง
    file_input = page.query_selector('input[type="file"]')
    file_input.set_input_files({"name": fname, "mimeType": "image/png", "buffer": buf.getvalue()})

    # รอ form ปรากฎ แล้วกรอก metadata
    page.wait_for_selector('input[name="title"]', timeout=60000)
    page.fill('input[name="title"]', title)
    page.fill('textarea[name="description"]', description)
    # กรอก tags (comma-separated)
    page.fill('input[name="tags"]', ",".join(tags))

    # Submit
    page.click('button[type="submit"]')
    # รอ publish
    page.wait_for_selector("a[href*='/work/']", timeout=60000)
    work_url = page.query_selector("a[href*='/work/']").get_attribute("href")
    print(f"✅ [3] Uploaded! View at: {work_url}")
    return work_url


def main():
    print("🚀 Auto-upload workflow started.")

    # 1) generate & upscale
    images = gen_and_upscale(prompt=PROMPT, n=1)

    # 2) login + upload
    print("🚀 [2] Launching browser…")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        login_redbubble(page)

        # 3) สำหรับแต่ละภาพ ให้ตั้ง title/description/tag ตามต้องการ
        for idx, img in enumerate(images, start=1):
            title       = f"AI minimalist cat #{idx}"
            description = "A flat, minimalist cartoon cat design on transparent background."
            tags        = ["cat", "minimalist", "AI", "cartoon", "tshirt"]

            url = upload_to_redbubble(page, img, title, description, tags)

        browser.close()

    print("🎉 All done! Your designs are live on Redbubble.")


if __name__ == "__main__":
    main()
