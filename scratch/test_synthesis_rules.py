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
rules_by_id = {r['rule_id']: r for r in rules}

llm = RealLLMClient(cache_file='real_llm_cache.json')

for rid in ['R15', 'R18', 'R19', 'R20', 'R21', 'R22']:
    r_meta = rules_by_id[rid]
    chunk = r_meta['retrieved_chunk']
    print(f"\n--- Testing synthesis & roundtrip for {rid} ({r_meta['article_id']}) ---")
    res = run_single_rule_with_real_llm(
        rule_item=r_meta,
        retrieved_chunk=chunk,
        process_schema=process_schema,
        llm=llm,
        max_retry=3,
        enable_l1_l2=True,
        enable_l3_roundtrip=True,
    )
    print(f"{rid}: roundtrip_ok={res['roundtrip_ok']}, rounds={res['rounds_needed']}, final_ast={res['final_ast']}")
    if not res['roundtrip_ok']:
        print("  Error:", res['roundtrip_msg'])
