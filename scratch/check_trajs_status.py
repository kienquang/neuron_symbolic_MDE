import json
with open('results/real_llm_trajectories.json', 'r', encoding='utf-8') as f:
    trajs = json.load(f)

for rid, t in sorted(trajs.items()):
    status = t['trajectory'][-1]['status'] if t.get('trajectory') else 'NONE'
    print(f"{rid}: {status}, has_final_ast={t.get('final_ast') is not None}")
