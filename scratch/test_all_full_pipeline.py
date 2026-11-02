import json
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from src.evaluation.benchmark_builder import BENCHMARK_RULES
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm

with open("data/processed/directive_chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)
chunks_by_article = {c["article_id"]: c for c in chunks}
with open("data/processed/process_schema.json", "r", encoding="utf-8") as f:
    process_schema = json.load(f)

llm = RealLLMClient()

normative_rules = [r for r in BENCHMARK_RULES if not r.get("is_trap", False)]

print(f"Testing Full Pipeline (Self-Correction) on all {len(normative_rules)} normative rules...")
results = {}

for r in normative_rules:
    rid = r["rule_id"]
    chunk = chunks_by_article.get(r["article_id"], {"article_id": r["article_id"], "text": ""})
    print(f"\n--- Synthesizing {rid} ---")
    res = run_single_rule_with_real_llm(
        r, chunk, process_schema, llm, max_retry=3, enable_l1_l2=True, enable_l3_roundtrip=True
    )
    ast = res["final_ast"]
    
    # Check exact match with ground truth
    match = True
    reasons = []
    if ast is None:
        match = False
        reasons.append("AST is None")
    else:
        if ast.get("template_name") != r["template"]:
            match = False
            reasons.append(f"tpl: {ast.get('template_name')} vs {r['template']}")
        if ast.get("activation_activity") != r["act_a"]:
            match = False
            reasons.append(f"act_a: {ast.get('activation_activity')} vs {r['act_a']}")
        if ast.get("target_activity") != r["act_b"]:
            match = False
            reasons.append(f"act_b: {ast.get('target_activity')} vs {r['act_b']}")
        if r.get("attr") and ast.get("activation_attr") != r["attr"]:
            match = False
            reasons.append(f"attr: {ast.get('activation_attr')} vs {r['attr']}")
        if r.get("op") and ast.get("activation_op") != r["op"]:
            match = False
            reasons.append(f"op: {ast.get('activation_op')} vs {r['op']}")
        if r.get("val") is not None and ast.get("activation_val") != r["val"]:
            match = False
            reasons.append(f"val: {ast.get('activation_val')} vs {r['val']}")
        if r.get("time_max") is not None and ast.get("time_max") != r["time_max"]:
            match = False
            reasons.append(f"time_max: {ast.get('time_max')} vs {r['time_max']}")

    results[rid] = {
        "match": match,
        "rounds_needed": res["rounds_needed"],
        "reasons": reasons,
        "ast": ast,
        "trajectory": res["trajectory"],
    }
    status = "OK" if match else f"MISMATCH ({', '.join(reasons)})"
    print(f"[{rid} Result]: {status} (Rounds needed: {res['rounds_needed']})")

correct = sum(1 for v in results.values() if v["match"])
print(f"\nFull Pipeline Summary: {correct}/{len(normative_rules)} ({correct/len(normative_rules)*100:.2f}%)")

with open("scratch/full_pipeline_synthesis_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
