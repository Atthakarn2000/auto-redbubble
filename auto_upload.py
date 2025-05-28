import os
import time
import uuid
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

# ——— CONFIGURATION ———
DEEPAI_API_KEY = os.getenv("DEEPAI_API_KEY")
RB_EMAIL        = os.getenv("RB_EMAIL")
RB_PASS         = os.getenv("RB_PASS")

if not DEEPAI_API_KEY:
    raise RuntimeError("❌ No DEEPAI_API_KEY env var found")
if not RB_EMAIL or not RB_PASS:
    raise RuntimeError("❌ RB_EMAIL and RB_PASS must be set in env")

PROMPTS = [
    "Minimalist cartoon cat T-shirt design, flat style, transparent background"
]
DESIGN_DIR = Path("designs")
DESIGN_DIR.mkdir(exist_ok=True)

# ——— IMAGE GENERATION VIA DeepAI ———
def generate_images_deepai(prompt: str, n: int = 1) -> list[Path]:
    urls = []
    for i in range(n):
        print(f"🖼️  Generating image {i+1}/{n} for prompt `{prompt}`…")
        resp = requests.post(
            "https://api.deepai.org/api/text2img",
            data={"text": prompt},
            headers={"api-key": DEEPAI_API_KEY},
            timeout=120
        )
        if resp.status_code != 200:
            raise RuntimeError(f"DeepAI error ({resp.status_code}): {resp.text}")
        output_url = resp.json().get("output_url")
        if not output_url:
            raise RuntimeError("DeepAI did not return output_url")
        # download
        r2 = requests.get(output_url, timeout=120)
        r2.raise_for_status()
        filename = DESIGN_DIR / f"{uuid.uuid4()}.png"
        with open(filename, "wb") as f:
            f.write(r2.content)
        print(f"✅ Saved to {filename}")
        urls.append(filename)
        time.sleep(1)
    return urls

# ——— PLAYWRIGHT REDBUBBLE UPLOAD ———
def upload_to_redbubble(image_paths: list[Path]):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 1) Login
        page.goto("https://www.redbubble.com/auth/login")
        page.fill('input[name="username"]', RB_EMAIL)
        page.fill('input[name="password"]', RB_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("https://www.redbubble.com/portfolio", timeout=60000)
        print("🔑 Logged into Redbubble")

        # 2) Go to new upload page
        page.goto("https://www.redbubble.com/portfolio/images/new")
        page.wait_for_selector('input[type="file"]', timeout=30000)

        for img in image_paths:
            print(f"🚀 Uploading {img.name}…")
            # upload file
            page.set_input_files('input[type="file"]', str(img))
            # fill title/description
            title = img.stem.replace("-", " ").capitalize()
            page.fill('input[name="title"]', title)
            # submit
            page.click('button:has-text("Save & Continue")')
            # wait for confirmation
            page.wait_for_selector('text=Your design has been published', timeout=60000)
            print(f"✅ Uploaded {img.name}")
            time.sleep(2)

        browser.close()

# ——— MAIN ———
def main():
    all_designs = []
    for prompt in PROMPTS:
        designs = generate_images_deepai(prompt, n=1)
        all_designs.extend(designs)
    if not all_designs:
        raise RuntimeError("No designs generated, aborting")
    upload_to_redbubble(all_designs)

if __name__ == "__main__":
    main()
