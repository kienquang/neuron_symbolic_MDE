import json

with open('results/real_llm_trajectories.json', encoding='utf-8') as f:
    trajs = json.load(f)

with open('data/processed/benchmark_items.json', encoding='utf-8') as f:
    items = json.load(f)

items_by_rule = {it['rule_id']: it for it in items}

for rid, it in items_by_rule.items():
    t_art = trajs.get(rid, {}).get('article_id')
    it_art = it['retrieved_chunk'].get('article_id')
    if t_art != it_art:
        print(f"MISMATCH for {rid}: trajs has '{t_art}', item has '{it_art}'")

print("CHECK COMPLETE")
