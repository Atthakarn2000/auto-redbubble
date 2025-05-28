import os, sys, time, requests
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright
import openai
from huggingface_hub import InferenceApi

# ─── Config ──────────────────────────────────────────────────
openai.api_key   = os.getenv("OPENAI_API_KEY")
HF_API_TOKEN     = os.getenv("HF_API_TOKEN")
RB_EMAIL, RB_PASS = os.getenv("RB_EMAIL"), os.getenv("RB_PASS")

if not all([openai.api_key, HF_API_TOKEN, RB_EMAIL, RB_PASS]):
    print("❌ Missing one of OPENAI_API_KEY, HF_API_TOKEN, RB_EMAIL, RB_PASS")
    sys.exit(1)

PROMPT = "Minimalist cartoon cat T-shirt design, flat style, transparent background"

# ─── 1) Generate 1024×1024 via OpenAI DALL·E ────────────────────
def gen_image_openai(prompt):
    print(f"🚀 Generating at 1024×1024: “{prompt}”")
    resp = openai.Image.create(
        prompt=prompt, n=1, size="1024x1024", response_format="url"
    )
    url = resp["data"][0]["url"]
    data = requests.get(url).content
    return Image.open(BytesIO(data)).convert("RGBA")

# ─── 2) Upscale เป็น 4500×5400 ด้วย HF Upscaler ───────────────
def upscale_hf(img: Image.Image) -> Image.Image:
    print("🖼 Upscaling via HF x4 upscaler…")
    # Model: stabilityai/stable-diffusion-xl-upscaler หรือ ตัว x4
    api = InferenceApi(
        repo_id="stabilityai/stable-diffusion-x4-upscaler",
        token=HF_API_TOKEN
    )
    buf = BytesIO()
    img.save(buf, format="PNG")
    out = api(inputs=buf.getvalue())
    up_url = out["images"][0]
    data = requests.get(up_url).content
    return Image.open(BytesIO(data)).convert("RGBA")

# ─── 3) Upload to Redbubble via Playwright ─────────────────────
def upload_redbubble(img: Image.Image, title="My AI T-shirt"):
    print("🔐 Logging into Redbubble…")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.redbubble.com/auth/login", timeout=60000)
        page.fill('input[name="login"]', RB_EMAIL)
        page.fill('input[name="password"]', RB_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("https://www.redbubble.com/portfolio", timeout=20000)

        print("⬆️ Navigating to New Work…")
        page.goto("https://www.redbubble.com/portfolio/images/new", timeout=60000)

        print("📤 Uploading image…")
        # เตรียม BytesIO
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        page.set_input_files('input[type="file"]', buf.read())

        # ใส่ Title
        page.fill('input[name="title"]', title)
        # (เพิ่มเติม) ใส่ Tags / Description ถ้าต้องการ
        page.click('button[type="submit"]')
        page.wait_for_selector('.work-page-url', timeout=30000)
        link = page.locator('.work-page-url').get_attribute("href")
        print("✅ Done! URL:", link)
        browser.close()

# ─── Main Script ───────────────────────────────────────────────
def main():
    try:
        img1024 = gen_image_openai(PROMPT)
        img_hi = upscale_hf(img1024)
        upload_redbubble(img_hi, title="Minimalist Cat Design")
    except Exception as e:
        print("❌ Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
