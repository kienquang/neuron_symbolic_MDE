import sys, json
sys.stdout.reconfigure(encoding='utf-8')
with open('data/processed/directive_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for c in chunks:
    print(f"Article {c['article_id']}: {c.get('article_title')}")
