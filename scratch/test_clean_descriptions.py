import json, re, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.experiment_runner import classify_semantic_equivalence
from src.mde.constraint_ast import DeclareConstraintAST
import pandas as pd

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
llm = RealLLMClient(bypass_cache=False)

clean_descriptions = {
    "R01": "Quy trình yêu cầu tiếp nhận hồ sơ vay trước khi tiến hành bước đánh giá sơ bộ.",
    "R02": "Quy trình yêu cầu đánh giá sơ bộ hồ sơ trước khi hồ sơ được chấp thuận.",
    "R07": "Khách hàng phải chấp thuận đề nghị vay trước khi khoản vay được giải ngân.",
    "R13": "Đề nghị vay phải có số tiền không dưới mức sàn luật định 200 EUR theo Điều 2(2)(c).",
    "R14": "Đề nghị vay phải có số tiền không vượt quá mức trần luật định 75.000 EUR theo Điều 2(2)(c).",
}

print("KIỂM TRA THỬ NGHIỆM VỚI MÔ TẢ NGHIỆP VỤ CHUẨN (KHÔNG MỚM TÊN BIẾN CODE):")
print("=" * 80)

for rid, desc in clean_descriptions.items():
    r = next(item for item in rules if item["rule_id"] == rid)
    gold = r["gold_ast"]
    
    r_test = dict(r)
    r_test["description"] = desc

    # 1. One-shot (max_retry=1, no L3)
    res_1 = run_single_rule_with_real_llm(r_test, r["retrieved_chunk"], schema, llm, max_retry=1, enable_l1_l2=True, enable_l3_roundtrip=False)
    ast_1 = DeclareConstraintAST(**res_1["final_ast"]) if res_1["final_ast"] else None
    cat_1 = classify_semantic_equivalence(ast_1, gold, df)

    # 2. Full pipeline (max_retry=5, with L3)
    res_5 = run_single_rule_with_real_llm(r_test, r["retrieved_chunk"], schema, llm, max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True)
    ast_5 = DeclareConstraintAST(**res_5["final_ast"]) if res_5["final_ast"] else None
    cat_5 = classify_semantic_equivalence(ast_5, gold, df)

    print(f"[{rid}] Mô tả nghiệp vụ: '{desc}'")
    print(f"  Gold:      {gold['template_name']}({gold['activation_activity']}, {gold.get('target_activity')}) attr={gold.get('activation_attr')} {gold.get('activation_op')} {gold.get('activation_val')}")
    print(f"  One-Shot:  Cat={cat_1} -> {ast_1.template_name if ast_1 else None}({ast_1.activation_activity if ast_1 else None}, {ast_1.target_activity if ast_1 else None}) attr={ast_1.activation_attr if ast_1 else None} {ast_1.activation_op if ast_1 else None} {ast_1.activation_val if ast_1 else None}")
    print(f"  Full-Pipe: Cat={cat_5} (rounds={res_5['rounds_needed']}) -> {ast_5.template_name if ast_5 else None}({ast_5.activation_activity if ast_5 else None}, {ast_5.target_activity if ast_5 else None}) attr={ast_5.activation_attr if ast_5 else None} {ast_5.activation_op if ast_5 else None} {ast_5.activation_val if ast_5 else None}")
    print("-" * 80)
