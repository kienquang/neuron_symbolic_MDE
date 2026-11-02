import sys, json, os
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
from src.evaluation.experiment_runner import extract_clause_numeric_entities

with open('data/processed/directive_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for c in chunks:
    entities = extract_clause_numeric_entities(c['text'])
    if entities:
        print(f"Article {c['article_id']}: {entities}")
