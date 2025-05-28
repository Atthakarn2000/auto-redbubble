import os, time, uuid, requests
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright
import replicate

# ─ CONFIG ─────────────────────────────────────────────────────
REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN")
RB_EMAIL       = os.getenv("RB_EMAIL")
RB_PASS        = os.getenv("RB_PASS")
DESIGNS_DIR    = "designs"        # โฟลเดอร์เก็บรูปก่อนอัป
UPLOAD_TITLE   = "My AI T-shirt"  # ปรับได้ตามชอบ
PROMPT         = "Minimalist cat T-shirt design, transparent background"

if not REPLICATE_TOKEN:
    raise RuntimeError("❌ REPLICATE_API_TOKEN not set")
if not RB_EMAIL or not RB_PASS:
    raise RuntimeError("❌ RB_EMAIL/RB_PASS not set")

# ─ STEP 1: Generate image(s) via Replicate ────────────────────
def gen_images(prompt, n=1):
    os.makedirs(DESIGNS_DIR, exist_ok=True)
    model = replicate.models.get("stability-ai/stable-diffusion")
    outputs = model.predict(
        prompt=prompt,
        width=512, height=512,
        num_inference_steps=30,
        api_token=REPLICATE_TOKEN
    )
    saved = []
    for i, url in enumerate(outputs):
        r = requests.get(url); r.raise_for_status()
        path = os.path.join(DESIGNS_DIR, f"{uuid.uuid4().hex}.png")
        with open(path, "wb") as f: f.write(r.content)
        saved.append(path)
        print(f"✅ Saved {path}")
    return saved

# ─ STEP 2: Upload to Redbubble via Playwright ─────────────────
def upload_to_redbubble(image_paths):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # 2.1 Login
        page.goto("https://www.redbubble.com/auth/login")
        page.fill('input[type="email"]', RB_EMAIL)
        page.fill('input[type="password"]', RB_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("https://www.redbubble.com/portfolio", timeout=15000)
        # 2.2 ไปหน้าอัพโหลดงานใหม่
        page.goto("https://www.redbubble.com/portfolio/images/new")
        for img in image_paths:
            print(f"🚀 Uploading {img}")
            page.set_input_files('input[type="file"]', img)
            page.wait_for_selector('text="Title"', timeout=10000)
            page.fill('input[name="title"]', UPLOAD_TITLE)
            page.click('button:has-text("Save & Continue")')
            page.wait_for_selector('text="Your design has been published"', timeout=20000)
            print("✅ Uploaded!")
        browser.close()

# ─ MAIN ───────────────────────────────────────────────────────
def main():
    print("🔧 Generating images…")
    imgs = gen_images(PROMPT, n=1)
    print("🔧 Uploading to Redbubble…")
    upload_to_redbubble(imgs)
    print("🎉 All done!")

if __name__ == "__main__":
    main()
