import json
import pandas as pd
from pathlib import Path
from src.evaluation.real_llm_client import RealLLMClient
from src.evaluation.experiment_runner import run_ablation_experiment

with open("data/processed/benchmark_items.json", encoding="utf-8") as f:
    items = json.load(f)

# Reconstruct test_case_df for each item
converted_items = []
for it in items:
    evs = it["events"]
    df = pd.DataFrame(evs)
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], format="ISO8601")
    converted_items.append({
        "benchmark_id": it["benchmark_id"],
        "rule_id": it["rule_id"],
        "ground_truth_label": it["ground_truth_label"],
        "trace_origin": it["trace_origin"],
        "retrieved_chunk": it["retrieved_chunk"],
        "rule_meta": {"rule_id": it["rule_id"], "is_baseless_trap": it["rule_id"] in [f"R{i}" for i in range(23, 31)]},
        "test_case_df": df,
    })

with open("data/processed/process_schema.json", encoding="utf-8") as f:
    process_schema = json.load(f)

llm = RealLLMClient(bypass_cache=False)

modes = [
    ("Baseline 2 (One-Shot)", dict(max_retry=1, enable_l1_l2=False, enable_l3_roundtrip=False)),
    ("- Pre-Verification (No L1/L2)", dict(max_retry=5, enable_l1_l2=False, enable_l3_roundtrip=True)),
    ("- Self-Correction (No SC)", dict(max_retry=1, enable_l1_l2=True, enable_l3_roundtrip=True)),
    ("Full Pipeline", dict(max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True)),
]

for name, kwargs in modes:
    res = run_ablation_experiment(
        converted_items,
        df,
        process_schema,
        llm_client=llm,
        enable_l1_l2=kwargs["enable_l1_l2"],
        enable_self_correction=(kwargs["max_retry"] > 1),
        enable_l3_roundtrip=kwargs["enable_l3_roundtrip"],
        max_retry=kwargs["max_retry"],
    )
    print(f"=== {name} ===")
    print(f"Executable Rate: {res['Executable_Rate (%)']}%")
    print(f"Macro F1: {res['Macro_F1']}")
    print(f"Macro Precision: {res['Macro_Precision']}")
    print(f"Macro Recall: {res['Macro_Recall']}")
    print(f"Confusion Matrix: {res.get('Confusion_Matrix')}")
