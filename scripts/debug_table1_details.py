import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.experiment_runner import classify_semantic_equivalence
from src.mde.constraint_ast import DeclareConstraintAST
import pandas as pd
from pathlib import Path

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="dev")
schema_path = next(Path("data/processed").glob("*schema*.json"))
schema = json.load(open(schema_path, encoding="utf-8"))
llm = RealLLMClient()
df = pd.read_parquet("data/interim/bpic2017_events.parquet")

print("--- KIỂM TRA TẬP DEV (R01 - R15) ---")
for r in rules:
    rid = r["rule_id"]
    gold = r["gold_ast"]
    
    # 1. One-shot (enable_self_correction=False)
    res_1 = run_single_rule_with_real_llm(r, r["retrieved_chunk"], schema, llm, max_retry=1, enable_l1_l2=True, enable_l3_roundtrip=False)
    ast_1 = DeclareConstraintAST(**res_1["final_ast"]) if res_1["final_ast"] else None
    cat_1 = classify_semantic_equivalence(ast_1, gold, df)

    # 2. Full pipeline (enable_self_correction=True)
    res_5 = run_single_rule_with_real_llm(r, r["retrieved_chunk"], schema, llm, max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True)
    ast_5 = DeclareConstraintAST(**res_5["final_ast"]) if res_5["final_ast"] else None
    cat_5 = classify_semantic_equivalence(ast_5, gold, df)

    if cat_1 != cat_5 or cat_1 != "EQ":
        print(f"Rule {rid}:")
        print(f"  Gold AST: {gold}")
        print(f"  One-shot AST: {res_1['final_ast']} -> cat: {cat_1}")
        print(f"  Full-pipe AST: {res_5['final_ast']} -> cat: {cat_5} (rounds: {res_5['rounds_needed']})")
