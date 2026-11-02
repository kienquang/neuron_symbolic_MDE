import json
import pandas as pd
from pathlib import Path
from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.experiment_runner import is_executable_against_log_schema, classify_semantic_equivalence, precision_recall_fscore_support
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status
from src.evaluation.justification_tree import check_single_trace_semantics

with open("results/real_llm_trajectories.json", encoding="utf-8") as f:
    trajs = json.load(f)

with open("data/processed/process_schema.json", encoding="utf-8") as f:
    schema = json.load(f)

with open("data/processed/benchmark_items.json", encoding="utf-8") as f:
    benchmark_items = json.load(f)

for it in benchmark_items:
    df = pd.DataFrame(it["events"])
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], format="ISO8601")
    it["test_case_df"] = df

print(f"Loaded {len(benchmark_items)} benchmark items.")

def get_ast_for_mode(rule_id, mode, r_meta):
    t = trajs.get(rule_id)
    if not t or not t.get("trajectory"):
        return None, False, "No trajectory"
    traj = t["trajectory"]
    r1 = traj[0]
    
    if mode == "baseline2":
        try:
            cand = DeclareConstraintAST.model_validate_json(r1["output"])
            if is_executable_against_log_schema(cand, schema):
                return cand, True, "One-shot"
            else:
                return None, False, "Schema crash"
        except Exception as e:
            return None, False, str(e)
            
    elif mode == "no_l1_l2":
        try:
            cand = DeclareConstraintAST.model_validate_json(r1["output"])
            if not is_executable_against_log_schema(cand, schema):
                return None, False, "Schema crash"
            if t.get("final_ast"):
                return DeclareConstraintAST(**t["final_ast"]), t.get("roundtrip_ok", True), t.get("roundtrip_msg", "")
            return cand, True, "OK"
        except Exception as e:
            return None, False, str(e)
            
    elif mode == "no_self_correction":
        if r1["status"] == "PASSED":
            cand = DeclareConstraintAST.model_validate_json(r1["output"])
            return cand, True, "Passed round 1"
        elif r1["status"] == "DETECTED_BASELESS_TRAP":
            return None, False, r1.get("error", "BASELESS")
        else:
            return None, False, r1.get("error", "Failed round 1")
            
    elif mode == "full_pipeline":
        if t.get("final_ast") is not None:
            return DeclareConstraintAST(**t["final_ast"]), t.get("roundtrip_ok", True), t.get("roundtrip_msg", "")
        else:
            return None, False, t.get("roundtrip_msg", "BASELESS")

for mode in ["baseline2", "no_l1_l2", "no_self_correction", "full_pipeline"]:
    y_true = []
    y_pred = []
    exec_count = 0
    
    for it in benchmark_items:
        rid = it["rule_id"]
        gt = it["ground_truth_label"]
        case_df = it["test_case_df"]
        y_true.append(gt)
        
        ast_obj, rt_ok, rt_msg = get_ast_for_mode(rid, mode, it)
        
        if ast_obj is None:
            if mode == "baseline2":
                y_pred.append("CRASH")
            else:
                if "BASELESS" in rt_msg or "DETECTED_BASELESS_TRAP" in rt_msg or not rt_ok:
                    y_pred.append("BASELESS")
                else:
                    y_pred.append("CRASH")
            continue
            
        exec_count += 1
        if mode == "baseline2":
            is_c, d_info = check_single_trace_semantics(case_df, ast_obj)
            y_pred.append("ENTAILED" if is_c else "CONTRADICTED")
        else:
            trace_eval = evaluate_trace_safety_and_status(case_df, ast_obj, rt_ok, rt_msg)
            y_pred.append(trace_eval["label"])
            
    labels = ["ENTAILED", "CONTRADICTED", "BASELESS"]
    p_m, r_m, f1_m, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    exec_rate = exec_count / len(benchmark_items) * 100.0
    print(f"Mode {mode:20s}: Executable Rate = {exec_rate:5.1f}%, Macro F1 = {f1_m:.4f}")
    p_arr, r_arr, f1_arr, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, average=None, zero_division=0)
    print(f"   Per class F1: ENT={f1_arr[0]:.4f}, CON={f1_arr[1]:.4f}, BAS={f1_arr[2]:.4f}")
