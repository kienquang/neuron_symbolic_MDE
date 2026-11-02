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

r23 = [r for r in rules if r["rule_id"] == "R23"][0]
print("R23 meta:", r23["rule_id"], "is_trap:", r23.get("is_trap"), "is_baseless_trap:", r23.get("is_baseless_trap"))
print("R23 desc:", r23["description"])

res = run_single_rule_with_real_llm(
    rule_item=r23,
    retrieved_chunk=r23["retrieved_chunk"],
    process_schema=schema,
    llm=llm,
    max_retry=5,
    enable_l1_l2=True,
    enable_l3_roundtrip=True,
)
print("R23 result:")
print("rounds_needed:", res["rounds_needed"])
print("roundtrip_ok:", res["roundtrip_ok"])
print("roundtrip_msg:", res["roundtrip_msg"])
print("final_ast:", res["final_ast"])
print("trajectory:", json.dumps(res["trajectory"], indent=2, ensure_ascii=False))
