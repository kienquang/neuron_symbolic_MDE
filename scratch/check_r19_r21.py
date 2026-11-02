import sys, json
sys.stdout.reconfigure(encoding='utf-8')
with open('results/real_llm_trajectories.json', 'r', encoding='utf-8') as f:
    trajs = json.load(f)
for rid in ['R19', 'R20', 'R21']:
    print(f'=== {rid} ===')
    for step in trajs[rid]['trajectory']:
        print(step['round'], step['status'], step['error'])
