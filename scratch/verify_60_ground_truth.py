import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json
import pandas as pd
from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.justification_tree import check_single_trace_semantics

items_all = json.load(open("data/processed/benchmark_items.json", encoding="utf-8"))
stratified_60 = items_all[0:20] + items_all[100:120] + items_all[200:220]
from src.evaluation.benchmark_builder import build_normative_rule_benchmark

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules_list = build_normative_rule_benchmark(chunks, split="all")
rules = {r["rule_id"]: r for r in rules_list}

matches = 0
mismatches = []
for idx, it in enumerate(stratified_60):
    rid = it["rule_id"]
    rule = rules[rid]
    gt = it["ground_truth_label"]
    df_item = pd.DataFrame(it["events"])
    df_item["time:timestamp"] = pd.to_datetime(df_item["time:timestamp"], format="ISO8601")
    
    if gt == "BASELESS":
        if rule.get("is_trap", False) or rule.get("is_baseless_trap", False):
            matches += 1
        else:
            mismatches.append((idx, it["benchmark_id"], rid, gt, "Expected trap"))
    else:
        gold_ast = rule["gold_ast"]
        ast_obj = DeclareConstraintAST(**gold_ast)
        is_comp, dev_info = check_single_trace_semantics(df_item, ast_obj)
        expected_status = "ENTAILED" if is_comp else "CONTRADICTED"
        if expected_status == gt:
            matches += 1
        else:
            mismatches.append((idx, it["benchmark_id"], rid, gt, expected_status))

print(f"Total verified items against true gold AST semantics: {matches}/{len(stratified_60)}")
if mismatches:
    print("Mismatches found:", mismatches)
