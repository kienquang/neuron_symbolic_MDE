import json, re, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.experiment_runner import classify_semantic_equivalence
from src.mde.constraint_ast import DeclareConstraintAST
import pandas as pd

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="dev")
schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
llm = RealLLMClient(bypass_cache=False)

print("KIỂM TRA THỬ NGHIỆM KHI BỎ 'MỚM TÊN HOẠT ĐỘNG' TRONG POLICY REQUIREMENT:")
print("=" * 80)

# Test R02 and R03
for rid in ["R02", "R03"]:
    r = next(item for item in rules if item["rule_id"] == rid)
    gold = r["gold_ast"]
    raw_desc = r["description"]
    # Strip explicit technical names
    clean_desc = re.sub(r"\b[AOWh]_[A-Za-z0-9_\s\(\)]+\b", "", raw_desc)
    clean_desc = re.sub(r"\([A-Za-z0-9_\s\(\)]*\)", "", clean_desc)
    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
    
    rule_modified = dict(r)
    rule_modified["description"] = clean_desc

    print(f"Rule: {rid}")
    print(f"  Mô tả cũ: {raw_desc}")
    print(f"  Mô tả mới (thuần nghiệp vụ): {clean_desc}")

    # One-shot
    res_1 = run_single_rule_with_real_llm(rule_modified, r["retrieved_chunk"], schema, llm, max_retry=1, enable_l1_l2=True, enable_l3_roundtrip=False)
    ast_1 = DeclareConstraintAST(**res_1["final_ast"]) if res_1["final_ast"] else None
    cat_1 = classify_semantic_equivalence(ast_1, gold, df)

    # Full pipeline
    res_5 = run_single_rule_with_real_llm(rule_modified, r["retrieved_chunk"], schema, llm, max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True)
    ast_5 = DeclareConstraintAST(**res_5["final_ast"]) if res_5["final_ast"] else None
    cat_5 = classify_semantic_equivalence(ast_5, gold, df)

    print(f"  One-Shot:  {cat_1} -> {ast_1.model_dump() if ast_1 else None}")
    print(f"  Full-Pipe: {cat_5} (rounds={res_5['rounds_needed']}) -> {ast_5.model_dump() if ast_5 else None}")
    print("-" * 80)
