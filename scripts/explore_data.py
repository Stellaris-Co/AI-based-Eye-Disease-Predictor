import os
import matplotlib.pyplot as plt
import glob
import random
from PIL import Image

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
DATA_DIR = os.path.join(project_root, 'dataset')

def main():
    print(f"🔍 Looking for dataset at: {DATA_DIR}")
    
    if not os.path.exists(DATA_DIR):
        print("❌ Error: Dataset folder not found!")
        return

    classes = os.listdir(DATA_DIR)
    classes = [c for c in classes if os.path.isdir(os.path.join(DATA_DIR, c))]
    
    counts = {}
    print("\n--- DATASET REPORT ---")
    for c in classes:
        files = glob.glob(os.path.join(DATA_DIR, c, "*"))
        counts[c] = len(files)
        print(f"• {c}: {len(files)} images")
    
    plt.figure(figsize=(10, 5))
    plt.bar(counts.keys(), counts.values(), color='skyblue')
    plt.title("Images per Disease Class")
    plt.ylabel("Count")
    plt.show()

    print("\nDisplaying random samples from each class...")
    fig, axes = plt.subplots(1, len(classes), figsize=(15, 5))
    
    for i, c in enumerate(classes):
        files = glob.glob(os.path.join(DATA_DIR, c, "*"))
        if len(files) > 0:
            rand_img = random.choice(files)
            img = Image.open(rand_img)
            axes[i].imshow(img)
            axes[i].set_title(c)
            axes[i].axis('off')
    
    plt.show()

if __name__ == "__main__":
    main()