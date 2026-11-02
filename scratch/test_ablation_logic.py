import json
import pandas as pd
from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.experiment_runner import is_executable_against_log_schema

with open("results/real_llm_trajectories.json", encoding="utf-8") as f:
    trajs = json.load(f)

with open("data/processed/process_schema.json", encoding="utf-8") as f:
    schema = json.load(f)

print("Ablation simulation on real LLM trajectories:")
for mode in ["Baseline 2", "No L1/L2", "No Self-Correction", "Full Pipeline"]:
    exec_count = 0
    total = len(trajs)
    crashes = []
    for rid, t in sorted(trajs.items()):
        traj = t.get("trajectory", [])
        if not traj:
            crashes.append(rid)
            continue
        
        if mode == "Baseline 2":
            # Round 1 only, no L1/L2, no L3
            r1 = traj[0]
            try:
                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                if is_executable_against_log_schema(cand, schema):
                    exec_count += 1
                else:
                    crashes.append(rid)
            except Exception:
                crashes.append(rid)
                
        elif mode == "No L1/L2":
            # Self-correction allowed via L3, but L1/L2 off
            # If round 1 has schema error, L1/L2 didn't catch it
            # In our logs: R25, R27, R28, R30 failed L1/L2 on round 1!
            # Without L1/L2, LLM never got L1/L2 compiler errors!
            r1 = traj[0]
            try:
                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                if is_executable_against_log_schema(cand, schema):
                    exec_count += 1
                else:
                    crashes.append(rid)
            except Exception:
                crashes.append(rid)
                
        elif mode == "No Self-Correction":
            # Round 1 only, with L1/L2 and L3
            r1 = traj[0]
            if r1["status"] in ("PASSED", "DETECTED_BASELESS_TRAP"):
                exec_count += 1
            else:
                crashes.append(rid)
                
        elif mode == "Full Pipeline":
            if t.get("final_ast") is not None or t.get("roundtrip_ok") or "BASELESS" in t.get("roundtrip_msg", ""):
                exec_count += 1
            else:
                crashes.append(rid)
                
    print(f"  {mode}: Executable = {exec_count}/{total} ({exec_count/total*100:.1f}%), Crashes: {crashes}")
