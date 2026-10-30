import sys
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
import pandas as pd
from collections import Counter

tables_json_path = Path("results/rq1_rq2_rq3_evaluation_tables.json")
with open(tables_json_path, "r", encoding="utf-8") as f:
    eval_tables = json.load(f)

trajectories_path = Path("results/real_llm_trajectories.json")
with open(trajectories_path, "r", encoding="utf-8") as f:
    trajectories = json.load(f)

benchmark_items_path = Path("data/processed/benchmark_items.json")
with open(benchmark_items_path, "r", encoding="utf-8") as f:
    benchmark_items = json.load(f)

print("=== 1. KIỂM TRA BẢNG 1 (RQ1) ===")
print("Table 1A (Without Self-Correction):")
print(json.dumps(eval_tables.get("table1_rq1_without_self_correction"), indent=2))
print("\nTable 1B (Full Pipeline With Self-Correction):")
print(json.dumps(eval_tables.get("table1_rq1_full_pipeline"), indent=2))

print("\n=== 2. KIỂM TRA NHẬT KÝ TRAJECTORIES TẬP DEV (R01 - R15) ===")
for rid in [f"R{i:02d}" for i in range(1, 16)]:
    if rid in trajectories:
        traj = trajectories[rid]
        final = traj.get("final_ast")
        status = traj["trajectory"][-1]["status"] if traj["trajectory"] else "NONE"
        rounds = traj["rounds_needed"]
        print(f"{rid} ({traj.get('tier')}): status={status}, rounds_needed={rounds}, ok={traj.get('roundtrip_ok')}")

print("\n=== 3. KIỂM TRA BẢNG 2 (RQ2 ABLATION STUDY) ===")
for row in eval_tables.get("table2_rq2_ablation_study", []):
    print(f"Config: {row['Configuration']:<65} | Exec: {str(row['Executable_Rate (%)']):<5} | Eq: {str(row['Eq_Rate (%)']):<5} | F1: {row['Conformance_F1']}")

print("\n=== 4. KIỂM TRA BẢNG 3 (RQ3 DIAGNOSTIC & EFFICIENCY) ===")
print(json.dumps(eval_tables.get("table3_rq3_diagnostic_and_efficiency"), indent=2))

print("\n=== 5. KIỂM TRA PHÂN PHỐI BENCHMARK ITEMS (60 MẪU) ===")
labels_count = Counter(it["ground_truth_label"] for it in benchmark_items[:60])
print(f"Tổng mẫu trong benchmark_items: {len(benchmark_items)}")
print(f"Phân phối 60 mẫu đầu tiên: {labels_count}")
rule_ids_count = Counter(it["rule_id"] for it in benchmark_items[:60])
print(f"Phân phối theo quy tắc trong 60 mẫu:")
for rid, cnt in sorted(rule_ids_count.items()):
    print(f"  {rid}: {cnt} mẫu")
