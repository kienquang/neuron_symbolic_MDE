import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.experiment_runner import classify_semantic_equivalence
from src.mde.constraint_ast import DeclareConstraintAST
import pandas as pd

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
trajs = json.load(open("results/real_llm_trajectories.json", encoding="utf-8"))
df = pd.read_parquet("data/interim/bpic2017_events.parquet")
schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))

valid_acts = set(schema.get("valid_activities", []))
case_attrs = set(schema.get("case_attributes", {}).keys())
event_attrs = set(schema.get("event_attributes", {}).keys())

print(f"=== KIỂM TRA TOÀN BỘ 30 QUY TẮC BENCHMARK (R01 - R30) ===")
print(f"Số lượng: {len(rules)} quy tắc\n")

for r in rules:
    rid = r["rule_id"]
    tier = r["tier"]
    art = r["article_id"]
    desc = r["description"]
    gold = r["gold_ast"]
    is_trap = r.get("is_baseless_trap", False)
    chunk = r.get("retrieved_chunk", {})
    chunk_text = chunk.get("text", "")[:120] + "..." if chunk else "NO CHUNK"

    t = trajs.get(rid, {})
    traj = t.get("trajectory", [])
    status = traj[-1].get("status") if traj else "NO_TRAJ"
    rounds = t.get("rounds_needed", 0)

    # One-shot classification
    ast_1 = None
    cat_1 = "NONE"
    if traj:
        out_1 = traj[0].get("output")
        if isinstance(out_1, str):
            try: out_1 = json.loads(out_1)
            except: pass
        try: ast_1 = DeclareConstraintAST(**out_1) if out_1 else None
        except: pass
        cat_1 = classify_semantic_equivalence(ast_1, gold, df)

    # Final classification
    final_dict = t.get("final_ast")
    ast_final = None
    cat_final = "NONE"
    if final_dict:
        try: ast_final = DeclareConstraintAST(**final_dict)
        except: pass
        cat_final = classify_semantic_equivalence(ast_final, gold, df)

    # Schema checks
    if gold is not None:
        act_a = gold.get("activation_activity")
        act_b = gold.get("target_activity")
        attr = gold.get("activation_attr")
        
        act_a_valid = act_a in valid_acts
        act_b_valid = (act_b in valid_acts) if act_b else True
        attr_valid = (attr in event_attrs or attr in case_attrs or f"case:{attr}" in case_attrs) if attr else True
        schema_str = f"Act_A={'OK' if act_a_valid else 'INVALID'} | Act_B={'OK' if act_b_valid else 'INVALID'} | Attr={'OK' if attr_valid else 'INVALID'}"
        gold_str = f"{gold.get('template_name')}({act_a}, {act_b}) attr={attr} {gold.get('activation_op')} {gold.get('activation_val')} t={gold.get('time_max')}"
    else:
        schema_str = "TRAP (No Gold AST)"
        gold_str = "None (BASELESS_TRAP)"

    print(f"[{rid}] ({tier}) | Điều: {art} | Bẫy: {is_trap}")
    print(f"  Mô tả: {desc}")
    print(f"  Luật: {chunk_text}")
    print(f"  Gold: {gold_str}")
    print(f"  Schema Check: {schema_str}")
    print(f"  LLM Kết quả: Status={status} (Rounds={rounds}) | OneShot={cat_1} | FullPipe={cat_final}")
    if not is_trap and (cat_1 != "EQ" or cat_final != "EQ"):
        print(f"  ==> CẦN XEM XÉT CHI TIẾT:")
        if ast_1:
            print(f"      One-Shot AST: {ast_1.template_name}({ast_1.activation_activity}, {ast_1.target_activity}) attr={ast_1.activation_attr} {ast_1.activation_op} {ast_1.activation_val} t={ast_1.time_max}")
        if ast_final:
            print(f"      Final AST:    {ast_final.template_name}({ast_final.activation_activity}, {ast_final.target_activity}) attr={ast_final.activation_attr} {ast_final.activation_op} {ast_final.activation_val} t={ast_final.time_max}")
    print("-" * 90)
