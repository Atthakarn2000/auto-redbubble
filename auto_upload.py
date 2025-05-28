import os
import time
import uuid
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

# ตั้งค่า API Key จาก DeepAI (โปรดตรวจสอบว่าคีย์นี้เป็นของคุณจริง)
DEEPAI_API_KEY = "2bf13735-62a2-49c9-82e4-062d0115aca6"

# สำหรับบัญชี Redbubble ให้ตั้งค่าข้อมูลของคุณลงไป (หรือสามารถนำมาใช้ environment variables ได้)
RB_EMAIL = os.getenv("RB_EMAIL") or "your_redbubble_email@example.com"
RB_PASS  = os.getenv("RB_PASS")  or "your_redbubble_password"

# ค่าคงที่สำหรับงานอัปโหลด
UPLOAD_TITLE = "AI-Generated Artwork"
DESIGN_FOLDER = Path("designs")
DESIGN_FOLDER.mkdir(exist_ok=True)

def generate_images(prompt, num_images=1):
    """
    สร้างภาพโดยใช้ DeepAI Text-to-Image API
    แล้วดาวน์โหลดและบันทึกไฟล์ภาพในโฟลเดอร์ 'designs/'
    """
    api_url = "https://api.deepai.org/api/text2img"
    # เปลี่ยนชื่อ header ให้ถูกต้องเป็น "Api-Key"
    headers = {"Api-Key": DEEPAI_API_KEY}
    
    image_paths = []
    
    for i in range(num_images):
        data = {"text": prompt}
        print("กำลังส่งคำขอสร้างภาพไปยัง DeepAI ...")
        response = requests.post(api_url, data=data, headers=headers)
        
        if response.status_code != 200:
            print(f"Error generating image: {response.status_code} {response.text}")
            exit(1)
        
        result = response.json()
        image_url = result.get("output_url")
        if not image_url:
            print("Error: ไม่พบข้อมูล output_url ในผลลัพธ์")
            exit(1)
        
        # ดาวน์โหลดภาพจาก URL ที่ได้
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        
        image_uuid = f"{uuid.uuid4()}.png"
        image_path = DESIGN_FOLDER / image_uuid
        
        with open(image_path, "wb") as img_file:
            img_file.write(img_response.content)
        
        image_paths.append(str(image_path))
        print(f"ดาวน์โหลดภาพสำเร็จ: {image_path}")
        
        # รอเล็กน้อยก่อนทำงานในรอบต่อไป (ถ้ามี)
        time.sleep(1)
    
    return image_paths

def upload_to_redbubble(image_paths):
    """
    อัปโหลดภาพไปยัง Redbubble โดยใช้ Playwright จำลองเบราว์เซอร์
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
        print("Error: ไม่สามารถสร้างภาพได้")
        exit(1)

if __name__ == "__main__":
    main()
