import sys, json
sys.stdout.reconfigure(encoding='utf-8')
with open('results/real_llm_trajectories.json', 'r', encoding='utf-8') as f:
    trajs = json.load(f)

for rid in ['R15', 'R18', 'R19', 'R20', 'R21', 'R22']:
    print(f'=== {rid} ===')
    t = trajs.get(rid, {})
    print('Roundtrip ok:', t.get('roundtrip_ok'))
    print('Status msg:', t.get('roundtrip_msg'))
    print('Trajectory steps:')
    for step in t.get('trajectory', []):
        err = step.get('error')
        out = step.get('output')
        print(f"  Round {step.get('round')}: {step.get('status')} - Error: {err}")
        print(f"    Output: {out[:120]}...")
