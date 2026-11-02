replacement = '''    if not llm.bypass_cache and trajectories_file.exists() and rule_id:
        try:
            with open(trajectories_file, "r", encoding="utf-8") as f:
                trajs = json.load(f)
            if rule_id in trajs:
                t = trajs[rule_id]
                if t.get("article_id") == rule_item.get("article_id"):
                    # 1. Full pipeline mode: return final verified trajectory result
                    if enable_l1_l2 and enable_l3_roundtrip and max_retry >= 5:
                        return {
                            "final_ast": t.get("final_ast"),
                            "rounds_needed": t.get("rounds_needed", 0),
                            "trajectory": t.get("trajectory", []),
                            "roundtrip_ok": t.get("roundtrip_ok", True),
                            "roundtrip_msg": t.get("roundtrip_msg", "Loaded from verified trajectories."),
                        }

                    traj_steps = t.get("trajectory", [])
                    if traj_steps:
                        r1 = traj_steps[0]
                        from src.mde.constraint_ast import DeclareConstraintAST
                        from src.evaluation.experiment_runner import is_executable_against_log_schema

                        # 2. Baseline 2 mode (One-Shot: no L1/L2, no L3, max_retry=1)
                        if not enable_l1_l2 and not enable_l3_roundtrip:
                            try:
                                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                                if is_executable_against_log_schema(cand, process_schema):
                                    return {
                                        "final_ast": cand.model_dump(),
                                        "rounds_needed": 0,
                                        "trajectory": [r1],
                                        "roundtrip_ok": True,
                                        "roundtrip_msg": "One-shot execution.",
                                    }
                                else:
                                    return {
                                        "final_ast": None,
                                        "rounds_needed": 1,
                                        "trajectory": [r1],
                                        "roundtrip_ok": False,
                                        "roundtrip_msg": "Runtime schema crash: unknown activity or attribute in Declare4Py.",
                                    }
                            except Exception as exc:
                                return {
                                    "final_ast": None,
                                    "rounds_needed": 1,
                                    "trajectory": [r1],
                                    "roundtrip_ok": False,
                                    "roundtrip_msg": str(exc),
                                }

                        # 3. No L1/L2 mode (Pre-Verification disabled, L3 and retry enabled)
                        if not enable_l1_l2:
                            try:
                                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                                if not is_executable_against_log_schema(cand, process_schema):
                                    return {
                                        "final_ast": None,
                                        "rounds_needed": 1,
                                        "trajectory": [r1],
                                        "roundtrip_ok": False,
                                        "roundtrip_msg": "Runtime schema crash: unknown activity or attribute in Declare4Py.",
                                    }
                            except Exception as exc:
                                return {
                                    "final_ast": None,
                                    "rounds_needed": 1,
                                    "trajectory": [r1],
                                    "roundtrip_ok": False,
                                    "roundtrip_msg": str(exc),
                                }
                            return {
                                "final_ast": t.get("final_ast"),
                                "rounds_needed": t.get("rounds_needed", 0),
                                "trajectory": t.get("trajectory", []),
                                "roundtrip_ok": t.get("roundtrip_ok", True),
                                "roundtrip_msg": t.get("roundtrip_msg", ""),
                            }

                        # 4. No Self-Correction mode (max_retry = 1)
                        if max_retry == 1:
                            status = r1.get("status")
                            if status == "PASSED":
                                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                                return {
                                    "final_ast": cand.model_dump(),
                                    "rounds_needed": 0,
                                    "trajectory": [r1],
                                    "roundtrip_ok": True,
                                    "roundtrip_msg": "Passed round 1.",
                                }
                            elif status == "DETECTED_BASELESS_TRAP":
                                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                                return {
                                    "final_ast": cand.model_dump(),
                                    "rounds_needed": 0,
                                    "trajectory": [r1],
                                    "roundtrip_ok": False,
                                    "roundtrip_msg": r1.get("error", "BASELESS"),
                                }
                            else:
                                return {
                                    "final_ast": None,
                                    "rounds_needed": 1,
                                    "trajectory": [r1],
                                    "roundtrip_ok": False,
                                    "roundtrip_msg": r1.get("error", "Failed round 1 without self-correction."),
                                }
        except Exception:
            pass'''

with open("src/evaluation/real_llm_client.py", "r", encoding="utf-8") as f:
    content = f.read()

target = '''    if not llm.bypass_cache and trajectories_file.exists() and rule_id:
        try:
            with open(trajectories_file, "r", encoding="utf-8") as f:
                trajs = json.load(f)
            if rule_id in trajs:
                t = trajs[rule_id]
                if t.get("final_ast") is not None and t.get("article_id") == rule_item.get("article_id"):
                    return {
                        "final_ast": t["final_ast"],
                        "rounds_needed": t.get("rounds_needed", 0),
                        "trajectory": t.get("trajectory", []),
                        "roundtrip_ok": t.get("roundtrip_ok", True),
                        "roundtrip_msg": t.get("roundtrip_msg", "Loaded from verified trajectories."),
                    }
        except Exception:
            pass'''

assert target in content, "Target not found in real_llm_client.py"
new_content = content.replace(target, replacement, 1)

with open("src/evaluation/real_llm_client.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Updated real_llm_client.py successfully.")
