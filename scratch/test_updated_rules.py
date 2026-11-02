import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.experiment_runner import classify_semantic_equivalence
from src.mde.constraint_ast import DeclareConstraintAST
import pandas as pd

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
rule_map = {r["rule_id"]: r for r in rules}

schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
llm = RealLLMClient(bypass_cache=False)

print("=== KIỂM TRA THỬ NGHIỆM 3 QUY TẮC VỪA CHUẨN HÓA ===")
for rid in ["R01", "R14", "R17"]:
    r = rule_map[rid]
    chunk = r["retrieved_chunk"]
    gold = r["gold_ast"]

    print(f"\n--- {rid} ---")
    print(f"Mô tả mới: {r['description']}")
    
    # Run full pipeline with max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True
    res = run_single_rule_with_real_llm(
        rule_item=r,
        retrieved_chunk=chunk,
        process_schema=schema,
        llm=llm,
        max_retry=5,
        enable_l1_l2=True,
        enable_l3_roundtrip=True,
    )

    final_ast = res["final_ast"]
    rounds = res["rounds_needed"]
    ok = res["roundtrip_ok"]
    ast_obj = DeclareConstraintAST(**final_ast) if final_ast else None
    cat = classify_semantic_equivalence(ast_obj, gold, df)

    print(f"Rounds: {rounds} | L3 OK: {ok} | Cat: {cat}")
    print(f"Gold AST:     {gold['template_name']}({gold['activation_activity']}, {gold.get('target_activity')}) attr={gold.get('activation_attr')} {gold.get('activation_op')} {gold.get('activation_val')} t={gold.get('time_max')}")
    if ast_obj:
        print(f"Final AST:    {ast_obj.template_name}({ast_obj.activation_activity}, {ast_obj.target_activity}) attr={ast_obj.activation_attr} {ast_obj.activation_op} {ast_obj.activation_val} t={ast_obj.time_max}")
    else:
        print(f"Final AST:    None (L3 Feedback: {res['roundtrip_msg']})")
