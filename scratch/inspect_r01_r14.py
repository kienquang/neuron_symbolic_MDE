import json
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

trajs = json.load(open('results/real_llm_trajectories.json', encoding='utf-8'))
for rid in ['R01', 'R14']:
    r = trajs.get(rid, {})
    print(f"=== {rid} ===")
    print("rounds_needed:", r.get('rounds_needed'))
    print("final_ast:", r.get('final_ast'))
    for step in r.get('trajectory', []):
        print(f"Round {step.get('round')}: status={step.get('status')}")
        print("  error:", step.get('error'))
        print("  output:", step.get('output'))
