import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.experiment_runner import classify_semantic_equivalence
from src.mde.constraint_ast import DeclareConstraintAST
import pandas as pd

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
trajs = json.load(open("results/real_llm_trajectories.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")

print("SUMMARY OF ALL 22 NORMATIVE RULES (R01 - R22):")
print("=" * 80)

problem_rules = []

for r in rules:
    rid = r["rule_id"]
    if r.get("is_baseless_trap", False):
        continue
    gold = r["gold_ast"]
    t = trajs.get(rid, {})
    traj = t.get("trajectory", [])
    r1 = traj[0] if traj else {}
    out_1 = r1.get("output")
    if isinstance(out_1, str):
        try: out_1 = json.loads(out_1)
        except: pass
    ast_1 = None
    try: ast_1 = DeclareConstraintAST(**out_1) if out_1 else None
    except: pass
    cat_1 = classify_semantic_equivalence(ast_1, gold, df)

    final_dict = t.get("final_ast")
    ast_final = None
    try: ast_final = DeclareConstraintAST(**final_dict) if final_dict else None
    except: pass
    cat_final = classify_semantic_equivalence(ast_final, gold, df)

    status = traj[-1].get("status") if traj else "NONE"
    rounds = t.get("rounds_needed", 0)

    is_problem = (cat_1 != "EQ" or cat_final != "EQ" or status != "PASSED")
    if is_problem:
        problem_rules.append(rid)

    mark = " [!] CHÚ Ý" if is_problem else " [OK]"
    print(f"{rid} ({r['complexity_tier']}) | Art: {r['article_id']}{mark}")
    print(f"   Desc:     {r['description']}")
    print(f"   Gold:     {gold['template_name']}({gold['activation_activity']}, {gold.get('target_activity')}) attr={gold.get('activation_attr')} {gold.get('activation_op')} {gold.get('activation_val')} t={gold.get('time_max')}")
    if is_problem:
        if ast_1:
            print(f"   OneShot:  {cat_1} -> {ast_1.template_name}({ast_1.activation_activity}, {ast_1.target_activity}) attr={ast_1.activation_attr} {ast_1.activation_op} {ast_1.activation_val} t={ast_1.time_max}")
        if ast_final:
            print(f"   FullPipe: {cat_final} -> {ast_final.template_name}({ast_final.activation_activity}, {ast_final.target_activity}) attr={ast_final.activation_attr} {ast_final.activation_op} {ast_final.activation_val} t={ast_final.time_max}")
        print(f"   Rounds:   {rounds} | Status: {status}")
    print("-" * 80)

print(f"\nTổng số quy tắc có vấn đề hoặc không đạt EQ: {len(problem_rules)} quy tắc: {problem_rules}")
