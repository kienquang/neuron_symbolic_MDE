import sys
sys.path.insert(0, '.')
import json
import pandas as pd
from src.evaluation.benchmark_builder import build_normative_rule_benchmark, _rule_to_ast_dict
from src.evaluation.justification_tree import check_single_trace_semantics
from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status

df = pd.read_parquet('data/interim/bpic2017_events.parquet')
chunks = json.load(open('data/processed/directive_chunks.json', 'r', encoding='utf-8'))
chunks_by_id = {c['article_id']: c for c in chunks}
normative_rules = build_normative_rule_benchmark(chunks_by_id, split='dev')
trajs = json.load(open('results/real_llm_trajectories.json', 'r', encoding='utf-8'))

# Candidate valid rules for dev
valid_rules = [
    r for r in normative_rules
    if r['rule_id'] in ['R01', 'R02', 'R03', 'R08', 'R09', 'R11', 'R12']
]
print("Candidate valid rules:", [r['rule_id'] for r in valid_rules])

sample_cids = df['case:concept:name'].drop_duplicates().iloc[:500].tolist()
sub_df = df[df['case:concept:name'].isin(sample_cids)]
grouped_prop = {
    cid: grp.sort_values("time:timestamp").reset_index(drop=True)
    for cid, grp in sub_df.groupby("case:concept:name", sort=False)
}

entailed = []
contradicted = []

for cid, cdf in grouped_prop.items():
    acts = set(cdf['concept:name'])
    for r in valid_rules:
        gold_ast = DeclareConstraintAST(**_rule_to_ast_dict(r))
        act_a = gold_ast.activation_activity
        act_b = gold_ast.target_activity
        # Check if trace contains activation activity
        if act_a not in acts and (not act_b or act_b not in acts):
            continue
        is_comp, details = check_single_trace_semantics(cdf, gold_ast)
        if is_comp and len(entailed) < 20:
            entailed.append({
                "rule_id": r['rule_id'],
                "case_id": cid,
                "case_df": cdf,
            })
        elif not is_comp and len(contradicted) < 20:
            contradicted.append({
                "rule_id": r['rule_id'],
                "case_id": cid,
                "case_df": cdf,
            })
    if len(entailed) >= 20 and len(contradicted) >= 20:
        break

print(f"Collected ENTAILED: {len(entailed)}")
print("Entailed rule distribution:", pd.Series([x['rule_id'] for x in entailed]).value_counts().to_dict())
print(f"Collected CONTRADICTED: {len(contradicted)}")
print("Contradicted rule distribution:", pd.Series([x['rule_id'] for x in contradicted]).value_counts().to_dict())

# Now test how our Full Pipeline predicts these ENTAILED items!
ent_preds = []
for it in entailed:
    rk = it['rule_id']
    t_info = trajs[rk]
    ast_obj = DeclareConstraintAST(**t_info['final_ast'])
    rt_ok = t_info['roundtrip_ok']
    rt_msg = t_info['roundtrip_msg']
    res = evaluate_trace_safety_and_status(it['case_df'], ast_obj, rt_ok, rt_msg)
    ent_preds.append(res['label'])

print("Predictions on ENTAILED items:", pd.Series(ent_preds).value_counts().to_dict())
