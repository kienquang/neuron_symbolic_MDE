import json
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

import pandas as pd
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient
from src.evaluation.experiment_runner import evaluate_rq1_complexity_tiers

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
normative_rules = [r for r in rules if not r.get("is_baseless_trap", False)]
schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
llm = RealLLMClient()

print("Evaluating RQ1 Full Pipeline (Self-Correction)...")
rq1_full = evaluate_rq1_complexity_tiers(normative_rules, df, schema, enable_self_correction=True, llm_client=llm)
print("RQ1 Full Pipeline Result:")
print(json.dumps(rq1_full, indent=2))
