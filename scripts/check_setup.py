import torch
import sys
import os

def check():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("------------------------------------------------")
    print(f"✅ Python Version: {sys.version.split()[0]}")
    print(f"✅ PyTorch Version: {torch.__version__}")
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"🚀 GPU DETECTED: {gpu_name}")
        print(f"   VRAM: {vram:.2f} GB")
        print("   Ready for accelerated training.")
    else:
        print("⚠️ NO GPU FOUND.")
        print("   Training will be slow (CPU only).")
        print("   Did you install the CUDA version of PyTorch?")
    print("------------------------------------------------")
if __name__ == "__main__":
    check()
