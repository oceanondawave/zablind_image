from transformers import BlipProcessor, BlipForConditionalGeneration
import os

# Absolute path to local folder
model_dir = os.path.join(os.path.dirname(__file__), "models", "blip")

# Actually download model & processor into this folder
print(f"📦 Downloading BLIP model to: {model_dir}")
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", cache_dir=model_dir)
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", cache_dir=model_dir)

# Save both manually (optional but clean)
processor.save_pretrained(model_dir)
model.save_pretrained(model_dir)

print("✅ Done. Model saved to local folder.")
