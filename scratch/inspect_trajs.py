import json

with open("results/real_llm_trajectories.json", encoding="utf-8") as f:
    trajs = json.load(f)

for rid in sorted(trajs.keys()):
    t = trajs[rid]
    traj = t.get("trajectory", [])
    print(f"=== {rid} (total rounds: {len(traj)}) ===")
    for step in traj:
        err = step.get("error")
        err_str = err[:80].encode("ascii", "replace").decode("ascii") if err else "None"
        print(f"  Round {step['round']}: status={step['status']}, err={err_str}")
        if step['round'] == 1:
            out_str = step['output'][:100].encode("ascii", "replace").decode("ascii")
            print(f"    out: {out_str}...")
