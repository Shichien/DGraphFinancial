import torch

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version (PyTorch built with): {torch.version.cuda}")
    print(f"GPU count: {torch.cuda.device_count()}")
    print(f"Device name: {torch.cuda.get_device_name(0)}")
else:
    print("--- 警告 ---")
    print("CUDA is NOT available. PyTorch is running in CPU-only mode.")