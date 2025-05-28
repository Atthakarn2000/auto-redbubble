import os
import time
import uuid
import requests
import replicate
from pathlib import Path
from playwright.sync_api import sync_playwright

# โหลดค่าจาก Environment Variables
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
RB_EMAIL = os.getenv("RB_EMAIL")
RB_PASS = os.getenv("RB_PASS")

# ค่าคงที่
UPLOAD_TITLE = "AI-Generated Artwork"
DESIGN_FOLDER = Path("designs")
DESIGN_FOLDER.mkdir(exist_ok=True)

def generate_images(prompt, num_images=1):
    """
    สร้างภาพด้วย Replicate API โดยใช้ Stable Diffusion พร้อมดาวน์โหลดภาพ
    """
    # ระบุโมเดลให้ถูกต้องโดยใส่ version id ด้วย
    # ตรวจสอบ version id ใน Replicate แล้วเปลี่ยน "<VERSION_ID>" ให้ถูกต้อง
    model = "stability-ai/stable-diffusion:dd0eae1a0e7f00fcd4b1b62ecd6ff501d99f60b1727429e7060e4f9d1f07a71f"
    params = {
        "prompt": prompt,
        "width": 512,
        "height": 512,
        "num_inference_steps": 30
    }
    
    try:
        client = replicate.Client(api_token=REPLICATE_API_TOKEN)
        # เรียกใช้งานโมเดลโดยส่งพารามิเตอร์เข้าไป
        output_urls = client.run(model, input=params)
        
        image_paths = []
        for url in output_urls[:num_images]:
            image_uuid = f"{uuid.uuid4()}.png"
            image_path = DESIGN_FOLDER / image_uuid
            response = requests.get(url)
            response.raise_for_status()
            
            with open(image_path, "wb") as img_file:
                img_file.write(response.content)
            
            image_paths.append(str(image_path))
            print(f"ดาวน์โหลดภาพสำเร็จ: {image_path}")
        return image_paths
    except requests.RequestException as e:
        print(f"Error downloading images: {e}")
        exit(1)
    except Exception as ex:
        print(f"Error generating images: {ex}")
        exit(1)

def upload_to_redbubble(image_paths):
    """
    อัปโหลดภาพไปยัง Redbubble ผ่าน Playwright ด้วยการจำลองเบราว์เซอร์
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("เข้าสู่ระบบ Redbubble...")
        page.goto("https://www.redbubble.com/auth/login")
        page.fill('input[name="email"]', RB_EMAIL)
        page.fill('input[name="password"]', RB_PASS)
        page.click('button[type="submit"]')
        page.wait_for_selector('text=Dashboard', timeout=10000)
        
        page.goto("https://www.redbubble.com/portfolio/images/new")
        page.wait_for_selector('input[type="file"]')
        
        for image_path in image_paths:
            print(f"กำลังอัปโหลด {image_path}...")
            page.set_input_files('input[type="file"]', image_path)
            page.fill('#work_title', UPLOAD_TITLE)
            page.click('#submit_button')
            page.wait_for_selector('text=Your design has been published', timeout=15000)
        
        print("อัปโหลดเสร็จสิ้น!")
        browser.close()

def main():
    prompt = "A futuristic cyberpunk city at night, vibrant and neon-lit."
    image_paths = generate_images(prompt, num_images=1)
    
    if image_paths:
        upload_to_redbubble(image_paths)
    else:
        print("ไม่สามารถสร้างภาพได้")
        exit(1)

if __name__ == "__main__":
    main()
