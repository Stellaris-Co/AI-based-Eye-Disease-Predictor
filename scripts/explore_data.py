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
    hierarchy_counts = {}
    all_diseases = []
    all_counts = []
    colors = []
    group_colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99']
    print("\n--- DATASET REPORT ---")
    groups = sorted([d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))])
    for group_idx, group in enumerate(groups):
        group_path = os.path.join(DATA_DIR, group)
        print(f"\n📁 Group: {group}")
        diseases = sorted([d for d in os.listdir(group_path) if os.path.isdir(os.path.join(group_path, d))])
        for disease in diseases:
            disease_path = os.path.join(group_path, disease)
            files = glob.glob(os.path.join(disease_path, "*"))
            img_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            count = len(img_files)
            print(f"   • {disease}: {count} images")
            all_diseases.append(disease)
            all_counts.append(count)
            colors.append(group_colors[group_idx % len(group_colors)])
    plt.figure(figsize=(14, 6))
    bars = plt.bar(all_diseases, all_counts, color=colors)
    plt.title("Images per Disease Class (Grouped)")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha='right')
    legend_labels = [plt.Rectangle((0,0),1,1, color=group_colors[i%len(group_colors)]) for i in range(len(groups))]
    plt.legend(legend_labels, groups)
    plt.tight_layout()
    plt.show()
    print("\nDisplaying random samples...")
    n_diseases = len(all_diseases)
    cols = 5
    rows = (n_diseases // cols) + 1
    fig, axes = plt.subplots(rows, cols, figsize=(20, 4 * rows))
    axes = axes.flatten()
    idx_counter = 0
    for group in groups:
        group_path = os.path.join(DATA_DIR, group)
        diseases = sorted([d for d in os.listdir(group_path) if os.path.isdir(os.path.join(group_path, d))])
        for disease in diseases:
            disease_path = os.path.join(group_path, disease)
            files = glob.glob(os.path.join(disease_path, "*"))
            valid_images = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if len(valid_images) > 0:
                rand_img = random.choice(valid_images)
                try:
                    img = Image.open(rand_img)
                    axes[idx_counter].imshow(img)
                    axes[idx_counter].set_title(f"{disease}\n({group.split('_')[1]})", fontsize=9)
                    axes[idx_counter].axis('off')
                except:
                    pass
            idx_counter += 1
    for i in range(idx_counter, len(axes)):
        axes[i].axis('off')
    plt.tight_layout()
    plt.show()
if __name__ == "__main__":
    main()
