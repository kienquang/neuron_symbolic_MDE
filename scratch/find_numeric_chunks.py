import sys, json
sys.stdout.reconfigure(encoding='utf-8')
with open('data/processed/directive_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for c in chunks:
    if c.get('has_numeric_bound'):
        print(f"Article: {c['article_id']} | Title: {c.get('article_title')}")
        print(f"  Text: {c['text'][:250]}...\n")
