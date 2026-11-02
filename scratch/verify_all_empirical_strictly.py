import functools
import json
import sys
from pathlib import Path
from collections import Counter
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path.cwd()))

from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.experiment_runner import (
    evaluate_rq1_complexity_tiers,
    run_ablation_experiment,
)

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
rules_by_id = {r["rule_id"]: r for r in rules}
normative_rules = [r for r in rules if not r.get("is_baseless_trap", False) and not r.get("is_trap", False)]
trap_rules = [r for r in rules if r.get("is_baseless_trap", False) or r.get("is_trap", False)]

schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
llm = RealLLMClient(bypass_cache=False)

print("="*70)
print("1. KIEM TRA THUC TE BANG 1 (RQ1 COMPLEXITY TIERS)")
print("="*70)
rq1_oneshot = evaluate_rq1_complexity_tiers(normative_rules, df, schema, enable_self_correction=False, llm_client=llm)
rq1_full = evaluate_rq1_complexity_tiers(normative_rules, df, schema, enable_self_correction=True, llm_client=llm)

print("RQ1 One-Shot:")
print(json.dumps(rq1_oneshot, indent=2))
print("RQ1 Full Pipeline:")
print(json.dumps(rq1_full, indent=2))

print("\n" + "="*70)
print("2. KIEM TRA THUC TE BANG 2 & BANG 3 TREN 60 MAU PHAN TANG")
print("="*70)
items_all = json.load(open("data/processed/benchmark_items.json", encoding="utf-8"))
stratified_60 = items_all[0:20] + items_all[100:120] + items_all[200:220]

converted_items = []
for it in stratified_60:
    rid = it["rule_id"]
    rule_meta = rules_by_id[rid]
    df_item = pd.DataFrame(it["events"])
    df_item["time:timestamp"] = pd.to_datetime(df_item["time:timestamp"], format="ISO8601")
    converted_items.append({
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

res_table2 = {}
for name, kwargs in modes:
    res = run_ablation_experiment(
        converted_items,
        df,
        schema,
        llm_client=llm,
        enable_l1_l2=kwargs["enable_l1_l2"],
        enable_self_correction=(kwargs["max_retry"] > 1),
        enable_l3_roundtrip=kwargs["enable_l3_roundtrip"],
        max_retry=kwargs["max_retry"],
    )
    res_table2[name] = res
    print(f"{name:<65} | Exec: {res['Executable_Rate (%)']}% | Eq: {res['Eq_Rate (%)']}% | F1: {res['Macro_F1']:.4f}")

print("\n" + "="*70)
print("3. KIEM TRA THUC TE BANG 3 (PER-CLASS PHAN PHOI TRANG THAI - FULL PIPELINE)")
print("="*70)
res_full = res_table2["Full Neuro-Symbolic Pipeline (Đề xuất)"]
for cls_name in ["ENTAILED", "CONTRADICTED", "BASELESS"]:
    m = res_full["Per_Class_Metrics"][cls_name]
    print(f"{cls_name:<15}: Precision={m['Precision']:.4f}, Recall={m['Recall']:.4f}, F1={m['F1-Score']:.4f}, Retries={m['Avg_Retries']:.2f}, Time={m['Avg_Verification_Time (s)']:.4f}s, Citation={m['Citation_Fidelity (%)']:.1f}%")

print(f"\nOverall Macro: Precision={res_full['Macro_Precision']:.4f}, Recall={res_full['Macro_Recall']:.4f}, F1={res_full['Macro_F1']:.4f}, Time={res_full['Avg_Verification_Time (s)']:.4f}s")

print("\n" + "="*70)
print("4. KIEM TRA THUC TE BANG 4 (BASELESS TRAPS DETECTION)")
print("="*70)
table4_results = []
detected_traps = 0
for r in trap_rules:
    rid = r["rule_id"]
    res = run_single_rule_with_real_llm(
        rule_item=r,
        retrieved_chunk=r["retrieved_chunk"],
        process_schema=schema,
        llm=llm,
        max_retry=5,
        enable_l1_l2=True,
        enable_l3_roundtrip=True,
    )
    last_status = res["trajectory"][-1]["status"] if res["trajectory"] else "NONE"
    is_detected = (last_status == "DETECTED_BASELESS_TRAP") or (not res["roundtrip_ok"] and "BASELESS" in str(res.get("roundtrip_msg")))
    if is_detected:
        detected_traps += 1
    table4_results.append({
        "rule_id": rid,
        "article_id": r["article_id"],
        "description": r["description"],
        "rounds_needed": res["rounds_needed"],
        "status": "DETECTED_BASELESS_TRAP" if is_detected else "FAILED_DETECTION",
        "diag": str(res.get("roundtrip_msg"))[:100],
    })
    print(f"Trap {rid} ({r['article_id']}): Status={table4_results[-1]['status']}, Rounds={res['rounds_needed']}, Diag={table4_results[-1]['diag']}")

print(f"\nTong hop Bat bay ao giac: {detected_traps}/{len(trap_rules)} ({detected_traps/len(trap_rules)*100:.1f}%)")
