import os, time
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
t0 = time.time()
from huggingface_hub import snapshot_download
p = snapshot_download("facebook/dinov2-small")
print("dinov2-small cached at", p, f"({time.time()-t0:.0f}s)")
