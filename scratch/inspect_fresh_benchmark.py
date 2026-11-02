import json
import pandas as pd
from src.evaluation.benchmark_builder import build_normative_rule_benchmark, build_stratified_trace_benchmark

with open("data/processed/directive_chunks.json", encoding="utf-8") as f:
    chunks = {c["article_id"]: c for c in json.load(f)}

norm_rules = build_normative_rule_benchmark(chunks, split="all")

parquet_path = "data/interim/bpic2017_events.parquet"
df_raw = pd.read_parquet(parquet_path)
df_raw["time:timestamp"] = pd.to_datetime(df_raw["time:timestamp"], utc=True)

OFFER_LEVEL_COLS = ["OfferedAmount", "CreditScore", "Accepted", "MonthlyCost", "NumberOfTerms", "FirstWithdrawalAmount"]
sample_cids = list(dict.fromkeys(df_raw["case:concept:name"].drop_duplicates().iloc[:600].tolist()))
df_sub = df_raw[df_raw["case:concept:name"].isin(sample_cids)].copy()
present_cols = [c for c in OFFER_LEVEL_COLS if c in df_sub.columns]
if present_cols:
    df_sub[present_cols] = df_sub.groupby("case:concept:name", sort=False)[present_cols].ffill().bfill()
    df_sub[present_cols] = df_sub.groupby("case:concept:name", sort=False)[present_cols].bfill()

items = build_stratified_trace_benchmark(
    df_propagated=df_sub,
    df_raw=df_raw,
    normative_rules=norm_rules,
    target_total_items=300,
    split="all",
)

print(f"Generated {len(items)} items.")
from collections import Counter
print("Labels:", Counter(it["ground_truth_label"] for it in items))
print("Origins:")
for origin, count in Counter(it["trace_origin"] for it in items).most_common(20):
    print(f"  {origin}: {count}")
