import sys, os, json
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
from src.evaluation.benchmark_builder import (
    build_normative_rule_benchmark,
    build_stratified_trace_benchmark,
)

with open('data/processed/directive_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
chunks_by_id = {c['article_id']: c for c in chunks}

normative_rules = build_normative_rule_benchmark(chunks_by_id, split='all')
print(f"Loaded {len(normative_rules)} normative rules.")

df_prop = pd.read_parquet('data/interim/bpic2017_events.parquet')
print(f"Loaded df_prop with {len(df_prop)} rows.")

items = build_stratified_trace_benchmark(
    df_propagated=df_prop,
    df_raw=df_prop,
    normative_rules=normative_rules,
    target_total_items=300,
    split='all',
)

print(f"Built benchmark with {len(items)} items.")
counts = {}
for it in items:
    lbl = it['ground_truth_label']
    counts[lbl] = counts.get(lbl, 0) + 1
print("Label breakdown:", counts)

rules_used = {}
for it in items:
    r = it['rule_id']
    rules_used[r] = rules_used.get(r, 0) + 1
print("Rules used count:", len(rules_used))
print(sorted(rules_used.keys()))
