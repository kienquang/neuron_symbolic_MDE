import json
import sys
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

traps = [r for r in rules if r.get("is_baseless_trap", False) or r.get("is_trap", False)]
print(f"Total trap rules: {len(traps)}")

detected = 0
for r in traps:
    rid = r["rule_id"]
    res = run_single_rule_with_real_llm(
        rule_item=r,
        retrieved_chunk=r["retrieved_chunk"],
        process_schema=schema,
        llm=llm,
        max_retry=5,
        enable_l1_l2=True,
        enable_l3_roundtrip=True,
    )
    last_status = res["trajectory"][-1]["status"] if res["trajectory"] else "NONE"
    is_detected = (last_status == "DETECTED_BASELESS_TRAP") or (not res["roundtrip_ok"] and "BASELESS" in str(res.get("roundtrip_msg")))
    if is_detected:
        detected += 1
    print(f"Trap {rid} | Rounds: {res['rounds_needed']} | Last Status: {last_status} | Detected: {is_detected}")
    print(f"   Diagnostic: {str(res.get('roundtrip_msg'))[:120]}...")

print(f"\nFinal Detection Rate: {detected}/{len(traps)} ({detected/len(traps)*100:.1f}%)")
