import json
from pathlib import Path
from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.experiment_runner import is_executable_against_log_schema
from src.evaluation.benchmark_builder import BENCHMARK_RULES

with open("data/processed/process_schema.json", encoding="utf-8") as f:
    process_schema = json.load(f)

with open("results/real_llm_trajectories.json", encoding="utf-8") as f:
    trajs = json.load(f)

for rule_item in BENCHMARK_RULES:
    rule_id = rule_item.get("rule_id")
    for mode_name, kwargs in [
        ("B2", dict(enable_l1_l2=False, enable_l3_roundtrip=False, max_retry=1)),
        ("NoL12", dict(enable_l1_l2=False, enable_l3_roundtrip=True, max_retry=5)),
        ("NoSC", dict(enable_l1_l2=True, enable_l3_roundtrip=True, max_retry=1)),
        ("Full", dict(enable_l1_l2=True, enable_l3_roundtrip=True, max_retry=5)),
    ]:
        enable_l1_l2 = kwargs["enable_l1_l2"]
        enable_l3_roundtrip = kwargs["enable_l3_roundtrip"]
        max_retry = kwargs["max_retry"]
        try:
            if rule_id in trajs:
                t = trajs[rule_id]
                req_art = rule_item.get("article_id")
                if not req_art or t.get("article_id") == req_art:
                    if enable_l1_l2 and enable_l3_roundtrip and max_retry >= 5:
                        res = "Full ok"
                    else:
                        traj_steps = t.get("trajectory", [])
                        if traj_steps:
                            r1 = traj_steps[0]
                            if not enable_l1_l2 and not enable_l3_roundtrip:
                                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                                res = "B2 ok"
                            elif not enable_l1_l2:
                                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                                res = "NoL12 ok"
                            elif max_retry == 1:
                                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                                res = "NoSC ok"
                else:
                    print(f"MISMATCH art_id: {rule_id}: {t.get('article_id')} vs {req_art}")
            else:
                print(f"NOT IN TRAJS: {rule_id}")
        except Exception as e:
            print(f"EXCEPTION for {rule_id} in {mode_name}: {type(e)} {e}")
print("AUDIT COMPLETE")
