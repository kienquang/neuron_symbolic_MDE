import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json
import pandas as pd
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.experiment_runner import classify_semantic_equivalence
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.mde.constraint_ast import DeclareConstraintAST

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
normative_rules = [r for r in rules if not r.get("is_baseless_trap", False)]
schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
llm = RealLLMClient(bypass_cache=False)

print("| Rule | Tier | One-Shot Class | Full-Pipeline Class | Rounds | Self-Correction Outcome |")
print("|---|---|---|---|---|---|")
for r in normative_rules:
    res_one = run_single_rule_with_real_llm(r, r["retrieved_chunk"], schema, llm, max_retry=1, enable_l1_l2=False, enable_l3_roundtrip=False)
    ast_one = DeclareConstraintAST(**res_one["final_ast"]) if res_one["final_ast"] else None
    c_one = classify_semantic_equivalence(ast_one, r["gold_ast"], df)

    res_full = run_single_rule_with_real_llm(r, r["retrieved_chunk"], schema, llm, max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True)
    ast_full = DeclareConstraintAST(**res_full["final_ast"]) if res_full["final_ast"] else None
    c_full = classify_semantic_equivalence(ast_full, r["gold_ast"], df)
    
    rounds = res_full["rounds_needed"]
    changed = "Fixed to EQ!" if c_one != "EQ" and c_full == "EQ" else ("Maintained EQ" if c_one == "EQ" and c_full == "EQ" else f"Remained {c_full}")
    print(f"| {r['rule_id']} | {r.get('tier', '')} | {c_one} | {c_full} | {rounds} | {changed} |")
