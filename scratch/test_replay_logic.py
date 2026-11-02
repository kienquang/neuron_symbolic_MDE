import json
from pathlib import Path
from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.experiment_runner import is_executable_against_log_schema

with open("results/real_llm_trajectories.json", encoding="utf-8") as f:
    trajs = json.load(f)

with open("data/processed/process_schema.json", encoding="utf-8") as f:
    process_schema = json.load(f)

def replay_rule_from_trajectory(rule_item, process_schema, max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True):
    rule_id = rule_item.get("rule_id")
    t = trajs.get(rule_id)
    if not t:
        return {"final_ast": None, "rounds_needed": max_retry, "trajectory": [], "roundtrip_ok": False, "roundtrip_msg": "No trajectory found."}

    # Full pipeline: use final AST from trajectory
    if enable_l1_l2 and enable_l3_roundtrip and max_retry >= 5:
        return {
            "final_ast": t.get("final_ast"),
            "rounds_needed": t.get("rounds_needed", 0),
            "trajectory": t.get("trajectory", []),
            "roundtrip_ok": t.get("roundtrip_ok", True),
            "roundtrip_msg": t.get("roundtrip_msg", "Loaded from verified trajectories."),
        }

    traj_steps = t.get("trajectory", [])
    if not traj_steps:
        return {"final_ast": None, "rounds_needed": max_retry, "trajectory": [], "roundtrip_ok": False, "roundtrip_msg": "Empty trajectory."}

    # Case 1: Baseline 2 (One-Shot: no L1/L2, no L3, max_retry=1)
    if not enable_l1_l2 and not enable_l3_roundtrip:
        r1 = traj_steps[0]
        try:
            cand = DeclareConstraintAST.model_validate_json(r1["output"])
            if is_executable_against_log_schema(cand, process_schema):
                return {"final_ast": cand.model_dump(), "rounds_needed": 0, "trajectory": [r1], "roundtrip_ok": True, "roundtrip_msg": "One-shot execution."}
            else:
                return {"final_ast": None, "rounds_needed": 1, "trajectory": [r1], "roundtrip_ok": False, "roundtrip_msg": "Runtime schema crash in Declare4Py."}
        except Exception as e:
            return {"final_ast": None, "rounds_needed": 1, "trajectory": [r1], "roundtrip_ok": False, "roundtrip_msg": str(e)}

    # Case 2: No L1/L2 (Pre-Verification disabled, but L3 and retry enabled)
    if not enable_l1_l2:
        # Without L1/L2, schema crashes on round 1 cannot be repaired by typing environment
        r1 = traj_steps[0]
        try:
            cand = DeclareConstraintAST.model_validate_json(r1["output"])
            if not is_executable_against_log_schema(cand, process_schema):
                return {"final_ast": None, "rounds_needed": 1, "trajectory": [r1], "roundtrip_ok": False, "roundtrip_msg": "Runtime schema crash in Declare4Py."}
        except Exception as e:
            return {"final_ast": None, "rounds_needed": 1, "trajectory": [r1], "roundtrip_ok": False, "roundtrip_msg": str(e)}
        # If round 1 was executable against schema, check if it had L3 error and was repaired
        return {
            "final_ast": t.get("final_ast"),
            "rounds_needed": t.get("rounds_needed", 0),
            "trajectory": t.get("trajectory", []),
            "roundtrip_ok": t.get("roundtrip_ok", True),
            "roundtrip_msg": t.get("roundtrip_msg", ""),
        }

    # Case 3: No Self-Correction (max_retry = 1)
    if max_retry == 1:
        r1 = traj_steps[0]
        status = r1.get("status")
        if status == "PASSED":
            cand = DeclareConstraintAST.model_validate_json(r1["output"])
            return {"final_ast": cand.model_dump(), "rounds_needed": 0, "trajectory": [r1], "roundtrip_ok": True, "roundtrip_msg": "Passed round 1."}
        elif status == "DETECTED_BASELESS_TRAP":
            cand = DeclareConstraintAST.model_validate_json(r1["output"])
            return {"final_ast": cand.model_dump(), "rounds_needed": 0, "trajectory": [r1], "roundtrip_ok": False, "roundtrip_msg": r1.get("error", "BASELESS")}
        else:
            # Failed round 1, cannot retry
            return {"final_ast": None, "rounds_needed": 1, "trajectory": [r1], "roundtrip_ok": False, "roundtrip_msg": r1.get("error", "Failed round 1.")}

    return {
        "final_ast": t.get("final_ast"),
        "rounds_needed": t.get("rounds_needed", 0),
        "trajectory": t.get("trajectory", []),
        "roundtrip_ok": t.get("roundtrip_ok", True),
        "roundtrip_msg": t.get("roundtrip_msg", ""),
    }

with open("data/processed/directive_chunks.json", encoding="utf-8") as f:
    chunks = {c["article_id"]: c for c in json.load(f)}
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
norm_rules = build_normative_rule_benchmark(chunks, split="all")

for mode_name, kwargs in [
    ("Baseline 2 (One-Shot)", dict(max_retry=1, enable_l1_l2=False, enable_l3_roundtrip=False)),
    ("- Pre-Verification (No L1/L2)", dict(max_retry=5, enable_l1_l2=False, enable_l3_roundtrip=True)),
    ("- Self-Correction (No SC)", dict(max_retry=1, enable_l1_l2=True, enable_l3_roundtrip=True)),
    ("Full Pipeline", dict(max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True)),
]:
    exec_c = 0
    crashes = []
    for r in norm_rules:
        res = replay_rule_from_trajectory(r, process_schema, **kwargs)
        if res["final_ast"] is not None:
            exec_c += 1
        else:
            crashes.append(r["rule_id"])
    print(f"{mode_name:30s}: Executable = {exec_c}/30 ({exec_c/30*100:.1f}%), Crashes: {crashes}")
