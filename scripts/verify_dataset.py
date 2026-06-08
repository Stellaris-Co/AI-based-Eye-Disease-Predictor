import os
from PIL import Image
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
DATA_DIR = os.path.join(project_root, 'dataset')

def verify_images():
    print(f"🔍 Scanning {DATA_DIR} for corrupt files...")
    bad_files = []
    checked_count = 0
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            if not file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                continue
            try:
                with Image.open(file_path) as img:
                    img.verify()
                checked_count += 1
                if checked_count % 1000 == 0:
                    print(f"   Checked {checked_count} images...")
            except (IOError, SyntaxError) as e:
                print(f"🗑️ Deleting CORRUPT image: {file_path}")
                try:
                    os.remove(file_path)
                    bad_files.append(file_path)
                except:
                    print(f"   ⚠️ Could not delete {file}")
    print(f"\n--- SCAN COMPLETE ---")
    print(f"✅ Total Valid Images: {checked_count}")
    if len(bad_files) == 0:
        print("✅ No corrupt images found. You are ready to train.")
    else:
        print(f"⚠️ Deleted {len(bad_files)} corrupt images.")
if __name__ == "__main__":
    verify_images()
