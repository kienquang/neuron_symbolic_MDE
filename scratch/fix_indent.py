from pathlib import Path

path = Path("src/evaluation/real_llm_client.py")
code = path.read_text(encoding="utf-8")

old_part = """                    if len(self.api_keys) > 1:
                        now = time.time()
                        ready_keys = [i for i in range(len(self.api_keys)) if now >= key_cooldown_until.get(i, 0.0)]
                        if ready_keys:
                            next_k = ready_keys[0]
                            self.current_key_idx = next_k
                            from openai import OpenAI
                            self.client = OpenAI(api_key=self.api_keys[self.current_key_idx], base_url=self.base_url, timeout=35.0)
                            print(f"      [GROQ KEY ROTATED]: Switched to ready key ({self.api_keys[self.current_key_idx][:10]}...).")
                            time.sleep(1.0)
                        else:
                            earliest_idx = min(range(len(self.api_keys)), key=lambda i: key_cooldown_until.get(i, 0.0))
                            sleep_needed = max(key_cooldown_until[earliest_idx] - time.time() + 2.0, 2.0)
                            print(f"      [GROQ ALL KEYS LIMITED]: All {len(self.api_keys)} keys hit quota. Waiting {sleep_needed:.1f}s for key ({self.api_keys[earliest_idx][:10]}...) to reset...")
                            sleep_end = time.time() + sleep_needed
                    while time.time() < sleep_end:
                        time.sleep(min(5.0, max(0.5, sleep_end - time.time())))
                        now_c = time.time()
                        if any(now_c >= key_cooldown_until.get(i, 0.0) for i in range(len(self.api_keys))):
                            break
                            self.current_key_idx = earliest_idx
                            from openai import OpenAI
                            self.client = OpenAI(api_key=self.api_keys[self.current_key_idx], base_url=self.base_url, timeout=35.0)
                    else:"""

new_part = """                    if len(self.api_keys) > 1:
                        now = time.time()
                        ready_keys = [i for i in range(len(self.api_keys)) if now >= key_cooldown_until.get(i, 0.0)]
                        if ready_keys:
                            next_k = ready_keys[0]
                            self.current_key_idx = next_k
                            from openai import OpenAI
                            self.client = OpenAI(api_key=self.api_keys[self.current_key_idx], base_url=self.base_url, timeout=35.0)
                            print(f"      [GROQ KEY ROTATED]: Switched to ready key ({self.api_keys[self.current_key_idx][:10]}...).", flush=True)
                            time.sleep(1.0)
                        else:
                            earliest_idx = min(range(len(self.api_keys)), key=lambda i: key_cooldown_until.get(i, 0.0))
                            sleep_needed = max(key_cooldown_until[earliest_idx] - time.time() + 2.0, 2.0)
                            print(f"      [GROQ ALL KEYS LIMITED]: All {len(self.api_keys)} keys hit quota. Waiting up to {sleep_needed:.1f}s for key ({self.api_keys[earliest_idx][:10]}...) to reset...", flush=True)
                            sleep_end = time.time() + sleep_needed
                            while time.time() < sleep_end:
                                time.sleep(min(5.0, max(0.5, sleep_end - time.time())))
                                now_c = time.time()
                                any_ready = [i for i in range(len(self.api_keys)) if now_c >= key_cooldown_until.get(i, 0.0)]
                                if any_ready:
                                    earliest_idx = any_ready[0]
                                    break
                            self.current_key_idx = earliest_idx
                            from openai import OpenAI
                            self.client = OpenAI(api_key=self.api_keys[self.current_key_idx], base_url=self.base_url, timeout=35.0)
                    else:"""

assert old_part in code, "old_part not found!"
code = code.replace(old_part, new_part)
path.write_text(code, encoding="utf-8")
print("Cleanly fixed indentation in real_llm_client.py!")
