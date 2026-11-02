import json
import pandas as pd
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient
from src.evaluation.experiment_runner import evaluate_rq1_complexity_tiers

with open("data/processed/directive_chunks.json", encoding="utf-8") as f:
    chunks = {c["article_id"]: c for c in json.load(f)}

with open("data/processed/process_schema.json", encoding="utf-8") as f:
    process_schema = json.load(f)

norm_rules = build_normative_rule_benchmark(chunks, split="all")
df_dummy = pd.DataFrame()
llm = RealLLMClient(bypass_cache=False)

rq1_oneshot = evaluate_rq1_complexity_tiers(norm_rules, df_dummy, process_schema, enable_self_correction=False, llm_client=llm)
print("=== RQ1 One-Shot ===")
print(json.dumps(rq1_oneshot, indent=2))

rq1_full = evaluate_rq1_complexity_tiers(norm_rules, df_dummy, process_schema, enable_self_correction=True, llm_client=llm)
print("=== RQ1 Full ===")
print(json.dumps(rq1_full, indent=2))
