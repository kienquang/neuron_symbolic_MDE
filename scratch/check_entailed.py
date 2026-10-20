import sys
sys.path.insert(0, '.')
import json
import pandas as pd
from src.evaluation.benchmark_builder import build_stratified_trace_benchmark
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status
from src.mde.constraint_ast import DeclareConstraintAST

df = pd.read_parquet('data/interim/bpic2017_events.parquet')
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
chunks = json.load(open('data/processed/directive_chunks.json', 'r', encoding='utf-8'))
chunks_by_id = {c["article_id"]: c for c in chunks}
normative_rules = build_normative_rule_benchmark(chunks_by_id, split='dev')
items = build_stratified_trace_benchmark(
    df_propagated=df,
    df_raw=df,
    normative_rules=normative_rules,
    target_total_items=60,
    split='dev',
)
trajs = json.load(open('results/real_llm_trajectories.json', 'r', encoding='utf-8'))

ent_items = [it for it in items if it['ground_truth_label'] == 'ENTAILED']
print(f"Total ENTAILED items: {len(ent_items)}")
for idx, it in enumerate(ent_items):
    rk = it['rule_id']
    t_info = trajs.get(rk, {})
    ast_dict = t_info.get('final_ast')
    ast_obj = DeclareConstraintAST(**ast_dict) if ast_dict else None
    rt_ok = t_info.get('roundtrip_ok', False)
    rt_msg = t_info.get('roundtrip_msg', '')
    res = evaluate_trace_safety_and_status(it['test_case_df'], ast_obj, rt_ok, rt_msg)
    print(f"ENT-{idx+1:02d}: rule={rk}, pred={res['label']}, reason={res['reason_type']}")
    if idx == 1:
        print("AST for R05:", json.dumps(ast_dict, ensure_ascii=True))
        print("Details for ENT-02:", json.dumps(res.get("details"), ensure_ascii=True, default=str))
        print("Case events:", [row['concept:name'] for _, row in it['test_case_df'].iterrows()])


