with open('src/evaluation/real_llm_client.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_str = '                if t.get("article_id") == rule_item.get("article_id"):'
new_str = '''                req_art = rule_item.get("article_id") or (retrieved_chunk.get("article_id") if retrieved_chunk else None)
                if not req_art or t.get("article_id") == req_art:'''

assert old_str in text, f"old_str not in text!"
text = text.replace(old_str, new_str, 1)

with open('src/evaluation/real_llm_client.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("SUCCESSFULLY REPLACED")
