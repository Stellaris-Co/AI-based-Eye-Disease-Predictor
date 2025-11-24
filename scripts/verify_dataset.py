import os
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'dataset')

def verify_images():
    print(f"🔍 Scanning {DATA_DIR}...")
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with Image.open(file_path) as img: img.verify()
            except:
                print(f"🗑️ Deleting: {file}")
                os.remove(file_path)
    print("✅ Done.")

if __name__ == "__main__":
    verify_images()