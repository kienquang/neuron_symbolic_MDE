with open("src/evaluation/real_llm_client.py", "r", encoding="utf-8") as f:
    text = f.read()

old_block = '''                        # 4. No Self-Correction mode (max_retry = 1)
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
                                }'''

new_block = '''                        # 4. No Self-Correction mode (max_retry = 1)
                        if max_retry == 1:
                            status = r1.get("status")
                            try:
                                cand = DeclareConstraintAST.model_validate_json(r1["output"])
                                cand_dict = cand.model_dump()
                            except Exception:
                                cand_dict = None

                            if status == "PASSED":
                                if cand_dict is not None:
                                    return {
                                        "final_ast": cand_dict,
                                        "rounds_needed": 0,
                                        "trajectory": [r1],
                                        "roundtrip_ok": True,
                                        "roundtrip_msg": "Passed round 1.",
                                    }
                                else:
                                    return {
                                        "final_ast": None,
                                        "rounds_needed": 1,
                                        "trajectory": [r1],
                                        "roundtrip_ok": False,
                                        "roundtrip_msg": "Schema violation in round 1.",
                                    }
                            elif status == "DETECTED_BASELESS_TRAP":
                                return {
                                    "final_ast": cand_dict,
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
                                }'''

assert old_block in text, "old_block not found in src/evaluation/real_llm_client.py"
text = text.replace(old_block, new_block, 1)

with open("src/evaluation/real_llm_client.py", "w", encoding="utf-8") as f:
    f.write(text)

print("SUCCESSFULLY PATCHED Case 4 in real_llm_client.py")
