#!/usr/bin/env python3
import os, time, uuid, logging
from io import BytesIO

import openai
import requests
from PIL import Image
from playwright.sync_api import sync_playwright

# ─── CONFIG ────────────────────────────────────────────────────────────────────
# สิ่งที่ต้องตั้งเป็น ENV ก่อนรัน:
#   OPENAI_API_KEY  – คีย์ OpenAI DALL·E
#   RB_EMAIL        – อีเมล Redbubble
#   RB_PASS         – รหัสผ่าน Redbubble

# บังคับใช้ OpenAI.com API (ไม่เอา Azure)
openai.api_type  = "openai"
openai.api_base  = "https://api.openai.com/v1"
openai.api_key   = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("❌ No OPENAI_API_KEY in env")

RB_EMAIL = os.getenv("RB_EMAIL")
RB_PASS  = os.getenv("RB_PASS")
if not (RB_EMAIL and RB_PASS):
    raise RuntimeError("❌ Please set RB_EMAIL and RB_PASS in env")

# ขนาดต้นทาง DALL·E และขนาดภาพปลายทางสำหรับ Redbubble
DALL_SIZE     = "1024x1024"
TARGET_W, TARGET_H = 4500, 5400
PROMPT        = "Minimalist cartoon cat T-shirt design, flat style, transparent background"

# เปิด logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def gen_and_upscale(prompt: str, n: int = 1):
    logging.info(f"▶️ Generating {n} image(s) at {DALL_SIZE} via DALL·E…")
    try:
        resp = openai.Image.create(
            prompt=prompt,
            n=n,
            size=DALL_SIZE,
            response_format="url"
        )
    except openai.error.OpenAIError as e:
        raise RuntimeError(f"🔥 OpenAI API error: {e}") from e

    imgs = []
    for item in resp.get("data", []):
        url = item.get("url")
        if not url:
            raise RuntimeError("⚠️ DALL·E returned no URL")
        r = requests.get(url); r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")

        # letterbox ให้เต็ม canvas 4500×5400
        ratio = min(TARGET_W/img.width, TARGET_H/img.height)
        nw, nh = int(img.width*ratio), int(img.height*ratio)
        img2 = img.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (TARGET_W, TARGET_H), (0,0,0,0))
        canvas.paste(img2, ((TARGET_W-nw)//2, (TARGET_H-nh)//2), img2)
        imgs.append(canvas)

    logging.info(f"✅ Generated & upscaled {len(imgs)} image(s).")
    return imgs


def login_rb(page):
    logging.info("🔐 Logging in to Redbubble…")
    page.goto("https://www.redbubble.com/auth/login/traditional")
    page.fill('input[name="username"]', RB_EMAIL)
    page.fill('input[name="password"]', RB_PASS)
    page.click('button[type="submit"]')
    page.wait_for_selector("header[aria-label='Redbubble']")


def upload_rb(page, img: Image.Image, title: str, desc: str, tags: list[str]):
    uid = uuid.uuid4().hex[:8]
    fn  = f"design_{uid}.png"
    logging.info(f"📤 Uploading {fn}…")
    buf = BytesIO()
    img.save(buf, "PNG"); buf.seek(0)

    page.goto("https://www.redbubble.com/portfolio/images/upload")
    page.query_selector('input[type="file"]').set_input_files(
        {"name": fn, "mimeType":"image/png", "buffer":buf.getvalue()}
    )
    page.wait_for_selector('input[name="title"]')
    page.fill('input[name="title"]', title)
    page.fill('textarea[name="description"]', desc)
    page.fill('input[name="tags"]', ",".join(tags))
    page.click('button[type="submit"]')
    page.wait_for_selector("a[href*='/work/']")
    url = page.query_selector("a[href*='/work/']").get_attribute("href")
    logging.info(f"✅ Uploaded! {url}")
    return url


def main():
    logging.info("🚀 Starting auto-upload workflow")
    images = gen_and_upscale(PROMPT, n=1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page    = browser.new_page()

        login_rb(page)
        for i, img in enumerate(images, 1):
            title = f"AI Cat #{i}"
            desc  = "Flat minimalist cat on transparent background"
            tags  = ["cat","minimalist","AI","tshirt"]
            upload_rb(page, img, title, desc, tags)

        browser.close()

    logging.info("🎉 All done!")


if __name__ == "__main__":
    main()
