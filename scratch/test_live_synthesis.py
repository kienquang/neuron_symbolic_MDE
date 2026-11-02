import json
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from scratch.test_all_natural_rules import NATURAL_POLICY_DESCRIPTIONS
from src.evaluation.benchmark_builder import BENCHMARK_RULES

with open("data/processed/directive_chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)
chunks_by_article = {c["article_id"]: c for c in chunks}

with open("data/processed/process_schema.json", "r", encoding="utf-8") as f:
    process_schema = json.load(f)

rules_by_id = {r["rule_id"]: r for r in BENCHMARK_RULES}

test_rules = ["R01", "R13", "R23"]
llm = RealLLMClient()

for rid in test_rules:
    rule_item = dict(rules_by_id[rid])
    rule_item["description"] = NATURAL_POLICY_DESCRIPTIONS[rid]
    rule_item["is_baseless_trap"] = rule_item.get("is_trap", False)
    chunk = chunks_by_article.get(rule_item["article_id"], {"article_id": rule_item["article_id"], "text": ""})
    print(f"=== Testing {rid} ===")
    print(f"Desc: {rule_item['description']}")
    res = run_single_rule_with_real_llm(rule_item, chunk, process_schema, llm, max_retry=3)
    print(f"Result: rounds_needed={res['rounds_needed']}, ok={res['roundtrip_ok']}")
    print(f"Trajectory length: {len(res['trajectory'])}")
    for step in res["trajectory"]:
        print(f"  Round {step['round']}: status={step['status']}, err={step.get('error')}")
