import json
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.benchmark_builder import BENCHMARK_RULES

with open("data/processed/process_schema.json", encoding="utf-8") as f:
    process_schema = json.load(f)

with open("data/processed/directive_chunks.json", encoding="utf-8") as f:
    chunks = {c["article_id"]: c for c in json.load(f)}

llm = RealLLMClient(bypass_cache=False)

modes = [
    ("B2", dict(enable_l1_l2=False, enable_l3_roundtrip=False, max_retry=1)),
    ("NoL12", dict(enable_l1_l2=False, enable_l3_roundtrip=True, max_retry=5)),
    ("NoSC", dict(enable_l1_l2=True, enable_l3_roundtrip=True, max_retry=1)),
    ("Full", dict(enable_l1_l2=True, enable_l3_roundtrip=True, max_retry=5)),
]

for mode_name, kwargs in modes:
    exec_c = 0
    crashes = []
    for r in BENCHMARK_RULES:
        chunk = chunks.get(r["article_id"], {"article_id": r["article_id"], "text": r["description"]})
        res = run_single_rule_with_real_llm(
            rule_item=r,
            retrieved_chunk=chunk,
            process_schema=process_schema,
            llm=llm,
            **kwargs,
        )
        if res["final_ast"] is not None:
            exec_c += 1
        else:
            crashes.append(r["rule_id"])
    print(f"{mode_name:6s}: Executable = {exec_c}/30 ({exec_c/30*100:.1f}%), Crashes: {crashes}")
print("ALL MODES TESTED SUCCESSFULLY")
