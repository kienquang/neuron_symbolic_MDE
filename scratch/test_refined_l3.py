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

rules_by_id = {r["rule_id"]: r for r in BENCHMARK_RULES}
llm = RealLLMClient()

for rid in ["R01", "R08"]:
    r = rules_by_id[rid]
    chunk = chunks_by_article.get(r["article_id"], {"article_id": r["article_id"], "text": ""})
    print(f"\n=== Testing {rid} ===")
    print("Policy Desc:", r["description"])
    res = run_single_rule_with_real_llm(
        r, chunk, process_schema, llm, max_retry=3, enable_l1_l2=True, enable_l3_roundtrip=True
    )
    print(f"Rounds needed: {res['rounds_needed']}, Roundtrip OK: {res['roundtrip_ok']}")
    print("Final AST:", json.dumps(res["final_ast"], indent=2))
    for step in res["trajectory"]:
        print(f"  Round {step['round']}: status={step['status']}, err={step.get('error')}")
