import os, time, uuid, requests
import openai
from PIL import Image
from io import BytesIO
from playwright.sync_api import sync_playwright

# — CONFIGURATION —
openai.api_key = os.getenv("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")
RB_EMAIL        = os.getenv("ozonena2543@gmail.com")
RB_PASS         = os.getenv("Ozone_190743")

prompts = [
    "Minimalist cartoon cat T-shirt design, flat style, transparent background"
]

def gen_and_upscale(prompt, n=3):
    # 1) เรียก DALL·E ที่ 1024×1024
    resp = openai.Image.create(prompt=prompt, n=n,
                               size="1024x1024",
                               response_format="url")
    files=[]
    for d in resp["data"]:
        r = requests.get(d["url"]); r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")

        # 2) Upscale เป็น 4500×5400 (letterbox transparent)
        target = (4500, 5400)
        img = img.resize((4500,4500), Image.LANCZOS)
        canvas = Image.new("RGBA", target, (255,255,255,0))
        top = (target[1] - 4500)//2
        canvas.paste(img, (0, top))
        fn = f"design_{uuid.uuid4().hex[:6]}.png"
        canvas.save(fn)
        files.append(fn)
    return files

def upload_to_redbubble(img_path, title, tags):
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page()
        pg.goto("https://www.redbubble.com/auth/login")
        pg.fill("input[name=email]", RB_EMAIL)
        pg.fill("input[name=password]", RB_PASS)
        pg.click("button[type=submit]")
        pg.wait_for_url("https://www.redbubble.com/portfolio")
        pg.goto("https://www.redbubble.com/portfolio/images/new")
        pg.set_input_files("input[type=file]", img_path)
        pg.wait_for_selector("textarea[name=title]")
        pg.fill("textarea[name=title]", title)
        pg.fill("textarea[name=description]", f"AI-generated design: {title}")
        pg.fill("input[name=tags]", ",".join(tags))
        pg.click("label[for='product-tshirt-image']")
        pg.click("button[type=submit]")
        br.close()

if __name__=="__main__":
    tags = ["minimalist","cartooncat","AI","tshirt","flatdesign"]
    for prompt in prompts:
        for img in gen_and_upscale(prompt, n=3):
            title = f"CatTee_{uuid.uuid4().hex[:6]}"
            upload_to_redbubble(img, title, tags)
            time.sleep(5)
