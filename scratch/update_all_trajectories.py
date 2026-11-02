import sys, os, json
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm

with open('data/processed/directive_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
chunks_by_id = {c['article_id']: c for c in chunks}

with open('data/processed/process_schema.json', 'r', encoding='utf-8') as f:
    process_schema = json.load(f)

rules = build_normative_rule_benchmark(chunks_by_id, split='all')
llm = RealLLMClient(cache_file='real_llm_cache.json')

with open('results/real_llm_trajectories.json', 'r', encoding='utf-8') as f:
    trajectories = json.load(f)

for r_meta in rules:
    rid = r_meta['rule_id']
    chunk = r_meta['retrieved_chunk']
    res = run_single_rule_with_real_llm(
        rule_item=r_meta,
        retrieved_chunk=chunk,
        process_schema=process_schema,
        llm=llm,
        max_retry=3,
        enable_l1_l2=True,
        enable_l3_roundtrip=True,
    )
    trajectories[rid] = {
        "rule_id": rid,
        "article_id": r_meta["article_id"],
        "dataset_split": r_meta["dataset_split"],
        "is_baseless_trap": r_meta.get("is_baseless_trap", False),
        "rounds_needed": res["rounds_needed"],
        "final_ast": res["final_ast"],
        "roundtrip_ok": res["roundtrip_ok"],
        "roundtrip_msg": res["roundtrip_msg"],
        "trajectory": res["trajectory"],
    }
    status = res['trajectory'][-1]['status'] if res['trajectory'] else 'NONE'
    print(f"Rule {rid} ({r_meta['article_id']}): {status}, rounds={res['rounds_needed']}, ok={res['roundtrip_ok']}")

with open('results/real_llm_trajectories.json', 'w', encoding='utf-8') as f:
    json.dump(trajectories, f, indent=2, ensure_ascii=False)
print("\nUpdated results/real_llm_trajectories.json successfully!")
