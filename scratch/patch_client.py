import re
from pathlib import Path

# 1. Update real_llm_client.py
client_path = Path("src/evaluation/real_llm_client.py")
code = client_path.read_text(encoding="utf-8")

old_pattern = r"(print\(f\"\s+\[GROQ ALL KEYS LIMITED\]:.*?\n\s+)(time\.sleep\(sleep_needed\))"
new_replacement = (
    r"\1sleep_end = time.time() + sleep_needed\n"
    r"                    while time.time() < sleep_end:\n"
    r"                        time.sleep(min(5.0, max(0.5, sleep_end - time.time())))\n"
    r"                        now_c = time.time()\n"
    r"                        if any(now_c >= key_cooldown_until.get(i, 0.0) for i in range(len(self.api_keys))):\n"
    r"                            break"
)

code_mod = re.sub(old_pattern, new_replacement, code)
if code_mod != code:
    client_path.write_text(code_mod, encoding="utf-8")
    print("Successfully patched real_llm_client.py with dynamic polling!")
else:
    print("Could not match old_pattern in real_llm_client.py")

# 2. Update scratch/evaluate_all_final.py to flush prints
eval_path = Path("scratch/evaluate_all_final.py")
eval_code = eval_path.read_text(encoding="utf-8")
eval_code = eval_code.replace("print(", "print(flush=True, ")
eval_code = eval_code.replace("print(flush=True, flush=True, ", "print(flush=True, ")
eval_path.write_text(eval_code, encoding="utf-8")
print("Successfully patched scratch/evaluate_all_final.py with flush=True!")
