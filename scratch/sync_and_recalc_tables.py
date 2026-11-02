import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.experiment_runner import (
    classify_semantic_equivalence,
    evaluate_rq1_complexity_tiers,
    run_ablation_experiment,
)
from src.mde.constraint_ast import DeclareConstraintAST
import pandas as pd

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
rule_map = {r["rule_id"]: r for r in rules}

schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
llm = RealLLMClient(bypass_cache=False)

trajs_path = Path("results/real_llm_trajectories.json")
trajs = json.load(open(trajs_path, encoding="utf-8"))

print("1. Cập nhật quỹ đạo (trajectories) cho R01, R14, R17...")
for rid in ["R01", "R14", "R17"]:
    r = rule_map[rid]
    res = run_single_rule_with_real_llm(
        rule_item=r,
        retrieved_chunk=r["retrieved_chunk"],
        process_schema=schema,
        llm=llm,
        max_retry=5,
        enable_l1_l2=True,
        enable_l3_roundtrip=True,
    )
    trajs[rid] = {
        "rule_id": rid,
        "dataset_split": "dev" if rid in [f"R{i:02d}" for i in range(1, 16)] else "heldout_test",
        "tier": r["tier"],
        "article_id": r["article_id"],
        "rounds_needed": res["rounds_needed"],
        "final_ast": res["final_ast"],
        "roundtrip_ok": res["roundtrip_ok"],
        "roundtrip_msg": res["roundtrip_msg"],
        "trajectory": res["trajectory"],
    }
    ast_obj = DeclareConstraintAST(**res["final_ast"]) if res["final_ast"] else None
    cat = classify_semantic_equivalence(ast_obj, r["gold_ast"], df)
    print(f"   {rid}: rounds={res['rounds_needed']}, L3_ok={res['roundtrip_ok']}, cat={cat}")

with open(trajs_path, "w", encoding="utf-8") as f:
    json.dump(trajs, f, indent=2, ensure_ascii=False)
print("   Đã lưu real_llm_trajectories.json!")

print("\n2. Đánh giá lại Bảng 1 (RQ1 Complexity Tiers)...")
normative_rules = [r for r in rules if not r.get("is_baseless_trap", False)]

rq1_oneshot = evaluate_rq1_complexity_tiers(
    normative_rules, df, schema, enable_self_correction=False, llm_client=llm
)
rq1_full = evaluate_rq1_complexity_tiers(
    normative_rules, df, schema, enable_self_correction=True, llm_client=llm
)

print("RQ1 One-Shot:")
print(json.dumps(rq1_oneshot, indent=2))
print("RQ1 Full Pipeline:")
print(json.dumps(rq1_full, indent=2))
