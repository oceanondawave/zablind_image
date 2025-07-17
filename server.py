from flask import Flask, request, jsonify
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch
from gtts import gTTS
import pygame
import os
from io import BytesIO
import threading
from googletrans import Translator
import socket
import hashlib
import time
import subprocess
import platform
import sys

app = Flask(__name__)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS  # PyInstaller sets this at runtime
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

SECRET_TOKEN = "zbimage"

# Load BLIP model
print("🔄 Loading BLIP base model...")
# 👇 Load from a local folder instead of downloading
LOCAL_MODEL_PATH = resource_path(os.path.join(os.path.dirname(__file__), "models", "blip"))

processor = BlipProcessor.from_pretrained(LOCAL_MODEL_PATH)
model = BlipForConditionalGeneration.from_pretrained(LOCAL_MODEL_PATH)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print("✅ BLIP model ready.")

# Initialize Google Translate
translator = Translator()

# Cache directory
CACHE_DIR = resource_path(os.path.join(os.path.dirname(__file__), "cache"))

os.makedirs(CACHE_DIR, exist_ok=True)

# Cache cleanup
def cleanup_cache_loop():
    """
    Clears the cache on startup, then periodically clears it again
    if the number of files exceeds the specified limit.
    """
    # Helper function to perform the actual file deletion
    def _clear_all_cache():
        cleared_count = 0
        try:
            for filename in os.listdir(CACHE_DIR):
                path = os.path.join(CACHE_DIR, filename)
                if os.path.isfile(path):
                    os.remove(path)
                    cleared_count += 1
        except Exception as e:
            print(f"⚠️  Error during cache cleanup: {e}")
        
        if cleared_count > 0:
            print(f"✅  Removed {cleared_count} cache file(s).")

    # 🧹 Clean everything once at startup for a fresh start
    print("🟡 Clearing all cache files on startup...")
    _clear_all_cache()

    # 🔁 Periodically check file count and clear if limit is exceeded
    while True:
        try:
            # Check every 60 seconds
            time.sleep(60)

            # Get a list of actual files, ignoring subdirectories
            files = [f for f in os.listdir(CACHE_DIR) if os.path.isfile(os.path.join(CACHE_DIR, f))]
            
            if len(files) > 10:
                print(f"🟡 Cache limit exceeded ({len(files)} files > 10). Clearing all files...")
                _clear_all_cache()

        except FileNotFoundError:
            print(f"❌ Cache directory '{CACHE_DIR}' not found. Exiting cleanup loop.")
            break # Stop the loop if the directory is gone
        except Exception as e:
            print(f"An unexpected error occurred in cleanup loop: {e}")

# TTS (Vietnamese) with caching
def speak_vi_cached(text, hash_key):
    audio_path = os.path.join(CACHE_DIR, f"{hash_key}.mp3")
    if not os.path.exists(audio_path):
        tts = gTTS(text, lang='vi')
        tts.save(audio_path)

    pygame.mixer.init()
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.set_volume(1.0)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pass
    pygame.mixer.quit()

def speak_startup_message():
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(resource_path("startup.mp3"))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pass
    pygame.mixer.quit()

# Flask route
@app.route("/caption", methods=["POST"])
def caption_image():
    auth = request.headers.get("X-Auth")
    if auth != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    image = None
    image_bytes = None
    file_hash = None

    try:
        # -----------------------
        # Case 1: image file sent
        # -----------------------
        if "image" in request.files:
            file = request.files["image"]
            image_bytes = file.read()
            image = Image.open(BytesIO(image_bytes)).convert("RGB")

        # -----------------------
        # Case 2: image path sent
        # -----------------------
        elif request.is_json:
            data = request.get_json()
            image_path = data.get("path")

            if not image_path:
                return jsonify({"error": "No image path provided"}), 400

            if not os.path.exists(image_path):
                # Try appending .jpg if missing
                alt_path = image_path + ".jpg"
                if os.path.exists(alt_path):
                    image_path = alt_path
                else:
                    return jsonify({"error": "Image path does not exist"}), 404

            with open(image_path, "rb") as f:
                image_bytes = f.read()
                image = Image.open(BytesIO(image_bytes)).convert("RGB")

        else:
            return jsonify({"error": "No image or path provided"}), 400

        # -----------------------
        # Cache lookup
        # -----------------------
        file_hash = hashlib.md5(image_bytes).hexdigest()
        caption_path = os.path.join(CACHE_DIR, f"{file_hash}.txt")

        if os.path.exists(caption_path):
            with open(caption_path, "r", encoding="utf-8") as f:
                caption_en = f.readline().strip()
                caption_vi = f.readline().strip()

            threading.Thread(target=speak_vi_cached, args=(caption_vi, file_hash)).start()
            return jsonify({
                "caption_en": caption_en,
                "caption_vi": caption_vi,
                "cached": True
            })

        # -----------------------
        # Generate new caption
        # -----------------------
        inputs = processor(images=image, return_tensors="pt").to(device)
        out = model.generate(**inputs, max_length=50)
        caption_en = processor.decode(out[0], skip_special_tokens=True).strip()
        caption_vi = translator.translate(caption_en, src='en', dest='vi').text.strip()

        # Save cache
        with open(caption_path, "w", encoding="utf-8") as f:
            f.write(caption_en + "\n" + caption_vi + "\n")

        threading.Thread(target=speak_vi_cached, args=(caption_vi, file_hash)).start()

        return jsonify({
            "caption_en": caption_en,
            "caption_vi": caption_vi,
            "cached": False
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Kill process using port (cross-platform)
def kill_process_on_port(port):
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
            for line in result.strip().split("\n"):
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    subprocess.call(f"taskkill /PID {pid} /F", shell=True)
        else:
            subprocess.call(f"fuser -k {port}/tcp", shell=True)
    except Exception as e:
        print(f"⚠️ Could not free port {port}: {e}")

if __name__ == "__main__":
    # Start merged cache cleanup thread
    threading.Thread(target=cleanup_cache_loop, daemon=True).start()

    # Use high, uncommon port
    fixed_port = 47860
    kill_process_on_port(fixed_port)

    speak_startup_message()

    print(f"🚀 Starting server on port {fixed_port}")
    app.run(port=fixed_port)
