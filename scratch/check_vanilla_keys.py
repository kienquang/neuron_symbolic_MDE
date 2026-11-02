import json
import sys
from pathlib import Path
import hashlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path.cwd()))

cache = json.load(open("vanilla_rag_real_cache.json", encoding="utf-8"))
first_hash = list(cache.keys())[0]
print("First hash in cache:", first_hash)

# Let's inspect scripts that generated vanilla_rag_real_cache.json
# Search git log for vanilla_rag_real_cache.json
import subprocess
out = subprocess.check_output(["git", "log", "--stat", "-n", "5", "vanilla_rag_real_cache.json"], text=True)
print("Git log for vanilla_rag_real_cache.json:")
print(out)
