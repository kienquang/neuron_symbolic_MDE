with open("src/symbolic/verbalizer_roundtrip.py", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("prompt = f")
print("Found prompt at char index:", idx)
if idx != -1:
    end_idx = text.find('"""', idx + 15)
    print(text[idx:end_idx+3])
