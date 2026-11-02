import json
import pandas as pd
from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status

with open("results/real_llm_trajectories.json", encoding="utf-8") as f:
    trajs = json.load(f)

with open("data/processed/benchmark_items.json", encoding="utf-8") as f:
    benchmark_items = json.load(f)

for it in benchmark_items:
    df = pd.DataFrame(it["events"])
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], format="ISO8601")
    it["test_case_df"] = df

misclassified = []
for it in benchmark_items:
    rid = it["rule_id"]
    gt = it["ground_truth_label"]
    case_df = it["test_case_df"]
    t = trajs.get(rid)
    ast_obj = DeclareConstraintAST(**t["final_ast"]) if t.get("final_ast") else None
    rt_ok = t.get("roundtrip_ok", True)
    rt_msg = t.get("roundtrip_msg", "")
    
    trace_eval = evaluate_trace_safety_and_status(case_df, ast_obj, rt_ok, rt_msg)
    pred = trace_eval["label"]
    if pred != gt:
        misclassified.append((it["benchmark_id"], rid, gt, pred, trace_eval["reason_type"]))

print(f"Total misclassified: {len(misclassified)}/{len(benchmark_items)}")
from collections import Counter
print("By rule:", Counter(m[1] for m in misclassified))
print("By (gt, pred):", Counter((m[2], m[3]) for m in misclassified))
for m in misclassified[:10]:
    print(" ", m)
