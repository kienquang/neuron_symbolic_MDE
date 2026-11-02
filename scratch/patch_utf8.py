with open("src/evaluation/real_llm_client.py", "r", encoding="utf-8") as f:
    text = f.read()
old = "import os\nimport re\nimport time"
new = 'import os\nimport re\nimport sys\nimport time\nif hasattr(sys.stdout, "reconfigure"):\n    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")\n    except Exception: pass'
assert old in text, "old string not found"
text = text.replace(old, new, 1)
with open("src/evaluation/real_llm_client.py", "w", encoding="utf-8") as f:
    f.write(text)
print("SUCCESSFULLY PATCHED real_llm_client.py")
