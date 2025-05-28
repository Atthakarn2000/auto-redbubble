import os
import time
import uuid
import requests
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright

# ─ CONFIG ─────────────────────────────────────────────────────────────────────────

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("❌ No HF_TOKEN env found")

RB_EMAIL = os.getenv("RB_EMAIL")
RB_PASS  = os.getenv("RB_PASS")
if not RB_EMAIL or not RB_PASS:
    raise RuntimeError("❌ No Redbubble credentials env found")

PROMPT = "Minimalist cartoon cat T-shirt design, flat style, transparent background"

# ─ IMAGE GENERATION (Hugging Face) ────────────────────────────────────────────────

def gen_images_hf(prompt, n=1):
    url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Accept": "application/octet-stream"
    }
    images = []
    for _ in range(n):
        resp = requests.post(url, headers=headers, json={"inputs": prompt})
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGBA")
        images.append(img)
    return images

# ─ REDBUBBLE UPLOAD ───────────────────────────────────────────────────────────────

def upload_to_redbubble(image: Image, title: str):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.redbubble.com/auth/login")
        page.fill('input[type="email"]', RB_EMAIL)
        page.fill('input[type="password"]', RB_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard")  # รอ login เสร็จ

        page.goto("https://www.redbubble.com/portfolio/images/upload")
        # อัปโหลดไฟล์ภาพ
        img_path = f"/tmp/{uuid.uuid4().hex}.png"
        image.save(img_path)
        page.set_input_files('input[type="file"]', img_path)

        # ใส่ title และ description เพิ่มเติมตามต้องการ
        page.fill('input[name="title"]', title)
        page.click('button:has-text("Save")')
        page.wait_for_timeout(3000)  # รอ upload เสร็จ

        new_url = page.url
        browser.close()
        return new_url

# ─ MAIN ───────────────────────────────────────────────────────────────────────────

def main():
    print("🚀 Starting auto-upload workflow")
    images = gen_images_hf(PROMPT, n=1)

    for img in images:
        unique_title = f"AI Cat {int(time.time())}"
        print(f"🔗 Uploading `{unique_title}` to Redbubble…")
        url = upload_to_redbubble(img, unique_title)
        print("✅ Uploaded at:", url)

if __name__ == "__main__":
    main()
