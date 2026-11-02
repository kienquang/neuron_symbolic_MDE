import json
import sys
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path.cwd()))

from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
llm = RealLLMClient(bypass_cache=False)

print(f"Loaded {len(rules)} benchmark rules.")
print(f"Total entries in real_llm_cache.json: {len(llm.cache)}")

results = []
missing_in_cache = []

for r in rules:
    rid = r["rule_id"]
    chunk = r["retrieved_chunk"]
    is_trap = r.get("is_baseless_trap", False) or r.get("is_trap", False)
    
    # Run single rule with max_retry=5, enable_l1_l2=True, enable_l3=True
    # Since bypass_cache=False, this will query llm.cache
    # If any key is missing, it would attempt a live call.
    # To detect whether it hits cache or calls live, we check if key exists beforehand:
    res = run_single_rule_with_real_llm(
        rule_item=r,
        retrieved_chunk=chunk,
        process_schema=schema,
        llm=llm,
        max_retry=5,
        enable_l1_l2=True,
        enable_l3_roundtrip=True,
    )
    
    rounds = res["rounds_needed"]
    final_ast = res["final_ast"]
    rt_ok = res["roundtrip_ok"]
    
    status_str = "TRAP_CAUGHT" if (is_trap and final_ast is None) else ("PASS" if final_ast else "FAIL")
    results.append({
        "rule_id": rid,
        "is_trap": is_trap,
        "rounds_needed": rounds,
        "status": status_str,
        "final_ast": final_ast,
        "roundtrip_ok": rt_ok,
    })
    print(f"Rule {rid:<4} | Trap: {str(is_trap):<5} | Rounds: {rounds} | Status: {status_str:<12} | AST: {final_ast['template_name'] if final_ast else 'None'}")

print("\n--- SUMMARY OF ALL 30 RULES FROM REAL LLM CACHE (HUONG A) ---")
total_rules = len(results)
traps_caught = sum(1 for x in results if x["is_trap"] and x["status"] == "TRAP_CAUGHT")
normative_pass = sum(1 for x in results if not x["is_trap"] and x["status"] == "PASS")
print(f"Normative Rules (R01-R22) successfully synthesized: {normative_pass}/22")
print(f"Trap Rules (R23-R30) successfully caught/rejected: {traps_caught}/8")
