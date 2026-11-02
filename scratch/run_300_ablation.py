import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import json
import pandas as pd
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient
from src.evaluation.experiment_runner import run_ablation_experiment

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
rules_by_id = {r["rule_id"]: r for r in rules}
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
items_all = json.load(open("data/processed/benchmark_items.json", encoding="utf-8"))

converted_items_300 = []
for it in items_all:
    rid = it["rule_id"]
    rule_meta = rules_by_id[rid]
    df_item = pd.DataFrame(it["events"])
    df_item["time:timestamp"] = pd.to_datetime(df_item["time:timestamp"], format="ISO8601")
    converted_items_300.append({
        "benchmark_id": it["benchmark_id"],
        "rule_id": rid,
        "ground_truth_label": it["ground_truth_label"],
        "trace_origin": it["trace_origin"],
        "retrieved_chunk": rule_meta["retrieved_chunk"],
        "rule_meta": rule_meta,
        "test_case_df": df_item,
    })

modes = [
    ("Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)", dict(max_retry=1, enable_l1_l2=False, enable_l3_roundtrip=False)),
    ("- Pre-Verification (Tắt Tầng 1 & Tầng 2)", dict(max_retry=5, enable_l1_l2=False, enable_l3_roundtrip=True)),
    ("- Self-Correction Loop (Tắt Vòng lặp Tự sửa)", dict(max_retry=1, enable_l1_l2=True, enable_l3_roundtrip=True)),
    ("Full Neuro-Symbolic Pipeline (Đề xuất)", dict(max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True)),
]

llm = RealLLMClient(bypass_cache=False)
results = {}
for name, kwargs in modes:
    res = run_ablation_experiment(
        converted_items_300,
        df,
        schema,
        llm_client=llm,
        enable_l1_l2=kwargs["enable_l1_l2"],
        enable_self_correction=(kwargs["max_retry"] > 1),
        enable_l3_roundtrip=kwargs["enable_l3_roundtrip"],
        max_retry=kwargs["max_retry"],
    )
    results[name] = res
    print(f"{name:<65} | Exec: {res['Executable_Rate (%)']}% | Eq: {res['Eq_Rate (%)']}% | F1: {res['Macro_F1']}", flush=True)

with open("scratch/results_300_ablation.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("Done saving scratch/results_300_ablation.json!", flush=True)
