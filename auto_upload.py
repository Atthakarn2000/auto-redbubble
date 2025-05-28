import os
import time
import openai
import requests
from playwright.sync_api import sync_playwright

# Load environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
RB_EMAIL = os.getenv("RB_EMAIL")
RB_PASS = os.getenv("RB_PASS")

# OpenAI API setup
openai.api_key = OPENAI_API_KEY
openai.api_type = "openai"
openai.api_base = "https://api.openai.com/v1"

# Hugging Face API setup
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}
SD_MODEL_ID = "stabilityai/stable-diffusion-2-base"
UPSCALE_MODEL_ID = "stabilityai/stable-diffusion-x4-upscaler"

def gen_with_openai():
    """Generate an image with OpenAI DALL·E."""
    try:
        response = openai.Image.create(
            model="dall-e",
            prompt="A stunning landscape painting in digital art style.",
            size="1024x1024"
        )
        return response["data"][0]["url"]
    except Exception as e:
        print(f"OpenAI image generation failed: {e}")
        return None

def gen_with_hf():
    """Generate an image with Hugging Face Stable Diffusion."""
    url = f"https://api-inference.huggingface.co/models/{SD_MODEL_ID}"
    payload = {"inputs": "A stunning landscape painting in digital art style."}
    try:
        response = requests.post(url, headers=HF_HEADERS, json=payload)
        response.raise_for_status()
        return response.content  # Image binary
    except requests.RequestException as e:
        print(f"Hugging Face image generation failed: {e}")
        return None

def upscale_with_hf(image):
    """Upscale an image using Hugging Face stable-diffusion-x4-upscaler."""
    url = f"https://api-inference.huggingface.co/models/{UPSCALE_MODEL_ID}"
    try:
        response = requests.post(url, headers=HF_HEADERS, files={"file": image})
        response.raise_for_status()
        return response.content  # Upscaled image binary
    except requests.RequestException as e:
        print(f"Upscaling failed: {e}")
        return None

def upload_to_redbubble(image_path):
    """Automate the Redbubble upload process using Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Logging into Redbubble...")
        page.goto("https://www.redbubble.com/auth/login")
        page.fill('input[name="email"]', RB_EMAIL)
        page.fill('input[name="password"]', RB_PASS)
        page.click('button[type="submit"]')
        time.sleep(5)  # Allow time for login

        print("Navigating to upload page...")
        page.goto("https://www.redbubble.com/portfolio/manage_works/new")
        time.sleep(3)

        print("Uploading image...")
        page.set_input_files('input[type="file"]', image_path)
        time.sleep(5)

        print("Setting metadata...")
        page.fill('#work_title', "Generated Art Design")
        page.fill('#work_description', "A beautiful AI-generated artwork.")
        page.fill('#work_tags', "AI, Digital Art, Landscape, Cool")

        print("Publishing design...")
        page.click('#submit_button')
        time.sleep(5)

        print("Upload complete!")
        browser.close()

def main():
    image = gen_with_openai() or gen_with_hf()
    if image:
        upscaled_image = upscale_with_hf(image) if image else None
        final_image = upscaled_image or image
        image_path = "generated_image.png"
        with open(image_path, "wb") as f:
            f.write(final_image)

        upload_to_redbubble(image_path)
    else:
        print("Failed to generate an image.")

if __name__ == "__main__":
    main()
