import json
import sys
from pathlib import Path
from collections import Counter
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.justification_tree import check_single_trace_semantics
from src.evaluation.benchmark_builder import _rule_to_ast_dict, BENCHMARK_RULES

print("=== BẮT ĐẦU KIỂM TRA ĐỘ CHÍNH XÁC CỦA BENCHMARK ĐÃ CẬP NHẬT ===")

items_path = Path("data/processed/benchmark_items.json")
rules_path = Path("data/processed/benchmark_rules_30.json")

print(f"File items size: {items_path.stat().st_size:,} bytes")
print(f"File rules size: {rules_path.stat().st_size:,} bytes")

with open(items_path, "r", encoding="utf-8") as f:
    items = json.load(f)

with open(rules_path, "r", encoding="utf-8") as f:
    rules = json.load(f)

rule_map = {r["rule_id"]: r for r in rules}

print(f"\n1. TỔNG SỐ LƯỢNG MẪU: {len(items)}")
labels = Counter(it["ground_truth_label"] for it in items)
print(f"Phân bố nhãn: {dict(labels)}")
assert labels["ENTAILED"] == 100, f"Expected 100 ENTAILED, got {labels['ENTAILED']}"
assert labels["CONTRADICTED"] == 100, f"Expected 100 CONTRADICTED, got {labels['CONTRADICTED']}"
assert labels["BASELESS"] == 100, f"Expected 100 BASELESS, got {labels['BASELESS']}"

print("\n2. PHÂN BỐ CÁC QUY TẮC THEO TỪNG NHÃN:")
for lbl in ["ENTAILED", "CONTRADICTED", "BASELESS"]:
    r_counts = Counter(it["rule_id"] for it in items if it["ground_truth_label"] == lbl)
    print(f"  [{lbl}] ({sum(r_counts.values())} mẫu): {sorted(r_counts.items())}")

print("\n3. KIỂM TRA CÁC QUY TẮC TỪNG BỊ THIẾU (R10, R13, R14, R15):")
for rid in ["R10", "R13", "R14", "R15"]:
    ent_cnt = sum(1 for it in items if it["rule_id"] == rid and it["ground_truth_label"] == "ENTAILED")
    con_cnt = sum(1 for it in items if it["rule_id"] == rid and it["ground_truth_label"] == "CONTRADICTED")
    print(f"  {rid}: ENTAILED = {ent_cnt}, CONTRADICTED = {con_cnt} (Tổng = {ent_cnt + con_cnt})")
    assert ent_cnt > 0 and con_cnt > 0, f"Rule {rid} must have both ENTAILED and CONTRADICTED samples!"

print("\n4. KIỂM TRA ENTAILED (KHÔNG CÓ VACUOUS TRUTH & KHÔNG DÙNG A_Validated):")
a_validated_count = 0
vacuous_entailed = []
for it in items:
    if it["ground_truth_label"] != "ENTAILED":
        continue
    events = it["events"]
    acts = [e["concept:name"] for e in events]
    if "A_Validated" in acts:
        a_validated_count += 1
    
    rid = it["rule_id"]
    rmeta = rule_map[rid]
    gast = DeclareConstraintAST(**_rule_to_ast_dict(rmeta))
    tpl = gast.template_name
    act_a = gast.activation_activity
    act_b = gast.target_activity
    
    # Check non-vacuous activation dynamically from current rule schema
    if tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
        if act_b not in acts:
            vacuous_entailed.append((it["benchmark_id"], rid, f"Target '{act_b}' not in trace"))
        if gast.activation_attr:
            attr_name = gast.activation_attr
            vals = [e.get(attr_name) for e in events if e.get("concept:name") == act_a and e.get(attr_name) is not None and not pd.isna(e.get(attr_name))]
            if not vals or (gast.activation_op == ">" and max(vals) <= float(gast.activation_val or 0)):
                vacuous_entailed.append((it["benchmark_id"], rid, f"{rid} {attr_name} missing or <= {gast.activation_val}"))
    elif tpl in ("Response", "Alternate Response", "Chain Response"):
        if act_a not in acts:
            vacuous_entailed.append((it["benchmark_id"], rid, f"Activation '{act_a}' not in trace"))
    elif tpl == "Not Co-Existence":
        if act_a not in acts and act_b not in acts:
            vacuous_entailed.append((it["benchmark_id"], rid, f"Neither '{act_a}' nor '{act_b}' in trace"))
    elif tpl in ("Existence", "Absence"):
        if act_a not in acts:
            vacuous_entailed.append((it["benchmark_id"], rid, f"Activation '{act_a}' not in trace"))

print(f"  Số trace chứa 'A_Validated': {a_validated_count} (Yêu cầu = 0)")
assert a_validated_count == 0, "A_Validated must be 0!"
print(f"  Số mẫu ENTAILED bị kích hoạt rỗng (vacuous): {len(vacuous_entailed)} (Yêu cầu = 0)")
if vacuous_entailed:
    for v in vacuous_entailed[:10]:
        print("    ", v)
assert len(vacuous_entailed) == 0, "No ENTAILED item should be vacuously compliant!"

print("\n5. KIỂM TRA TẤT CẢ 100 MẪU CONTRADICTED QUA JUSTIFICATION TREE:")
invalid_con = []
con_reasons = Counter()
r18_con_vals = []
r18_attr = rule_map["R18"].get("attr") or "NumberOfTerms"
for it in items:
    if it["ground_truth_label"] != "CONTRADICTED":
        continue
    events = it["events"]
    df = pd.DataFrame(events)
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], format="ISO8601")
    
    rid = it["rule_id"]
    rmeta = rule_map[rid]
    gast = DeclareConstraintAST(**_rule_to_ast_dict(rmeta))
    
    is_comp, details = check_single_trace_semantics(df, gast)
    subtype = details.get("violation_subtype", "UNKNOWN")
    con_reasons[subtype] += 1
    
    if is_comp:
        invalid_con.append((it["benchmark_id"], rid, it["trace_origin"], details))
    
    if rid == "R18":
        vals = [e.get(r18_attr) for e in events if e.get(r18_attr) is not None and not pd.isna(e.get(r18_attr))]
        r18_con_vals.append((it["benchmark_id"], max(vals) if vals else None, subtype))

print(f"  Số mẫu CONTRADICTED không bị vi phạm (is_comp == True): {len(invalid_con)} (Yêu cầu = 0)")
if invalid_con:
    for ic in invalid_con:
        print("    ", ic)
assert len(invalid_con) == 0, "All CONTRADICTED items must evaluate to is_comp == False!"
print("  Phân bố lý do vi phạm trong CONTRADICTED:")
for st, cnt in con_reasons.most_common():
    print(f"    - {st}: {cnt} mẫu")
print(f"  Chi tiết R18 CONTRADICTED ({len(r18_con_vals)} mẫu):")
for bid, val, st in r18_con_vals:
    print(f"    {bid}: {r18_attr} = {val}, lý do: {st}")

print("\n6. KIỂM TRA CÁC BẪY BASELESS (R23–R30):")
from src.evaluation.benchmark_builder import BENCHMARK_RULES, DEV_RULE_IDS, HELDOUT_TEST_RULE_IDS
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status

rules_by_id = {r["rule_id"]: r for r in BENCHMARK_RULES}
assert rules_by_id["R07"]["article_id"] == "Article 5(1)" and rules_by_id["R07"]["act_a"] == "O_Sent (mail and online)" and rules_by_id["R07"]["act_b"] == "O_Accepted", "R07 must be Article 5(1) Precedence(O_Sent, O_Accepted)"
assert rules_by_id["R29"]["article_id"] == "Article 5(6)" and rules_by_id["R29"]["template"] == "Response" and rules_by_id["R29"]["act_a"] == "O_Sent (mail and online)" and rules_by_id["R29"]["act_b"] == "W_Call after offers", "R29 must be Article 5(6) Response(O_Sent, W_Call after offers)"

r29_ast = DeclareConstraintAST(
    article_id=rules_by_id["R29"]["article_id"],
    template_name=rules_by_id["R29"]["template"],
    activation_activity=rules_by_id["R29"]["act_a"],
    target_activity=rules_by_id["R29"]["act_b"],
    activation_attr=rules_by_id["R29"]["attr"],
    activation_op=rules_by_id["R29"]["op"],
    activation_val=rules_by_id["R29"]["val"],
)

r29_total = 0
r29_no_sent = 0
r29_baseless_eval = 0
r30_total = 0
r30_nan_attr = 0
r30_attr = rules_by_id["R30"].get("attr") or "NumberOfTerms"
distinct_traces_r23_r28 = set()

for it in items:
    if it["ground_truth_label"] != "BASELESS":
        continue
    rid = it["rule_id"]
    events = it["events"]
    acts = [e["concept:name"] for e in events]
    cname = events[0]["case:concept:name"]

    if rid == "R29":
        r29_total += 1
        if "O_Sent (mail and online)" not in acts:
            r29_no_sent += 1
        t_df = pd.DataFrame(events)
        t_df["time:timestamp"] = pd.to_datetime(t_df["time:timestamp"], utc=True)
        eval_res = evaluate_trace_safety_and_status(
            t_df, r29_ast, True, "Counterfactual Probe Passed"
        )
        if eval_res["label"] == "BASELESS" and eval_res["reason_type"] == "INAPPLICABLE_TRACE_NO_ACTIVATION":
            r29_baseless_eval += 1
    elif rid == "R30":
        r30_total += 1
        if all(e.get(r30_attr) is None or pd.isna(e.get(r30_attr)) for e in events):
            r30_nan_attr += 1
    else:
        distinct_traces_r23_r28.add(cname)

print(f"  R29: không có O_Sent (mail and online) = {r29_no_sent}/{r29_total}, Declare+Phi BASELESS = {r29_baseless_eval}/{r29_total}")
assert r29_total >= 12 and r29_no_sent == r29_total and r29_baseless_eval == r29_total, "R29 must lack O_Sent and evaluate to INAPPLICABLE_TRACE_NO_ACTIVATION"
print(f"  R30: có {r30_attr} là null/NaN = {r30_nan_attr}/{r30_total}")
assert r30_total >= 12 and r30_nan_attr == r30_total, f"R30 must have null {r30_attr}"
print(f"  R23–R28: số case traces nền khác nhau = {len(distinct_traces_r23_r28)} (Đã đa dạng hóa không trùng lặp)")
assert len(distinct_traces_r23_r28) > 10, "R23-R28 should use diverse traces!"

print("\n7. KIỂM TRA CÂN BẰNG PHÂN TẦNG & KHÔNG TÁI CHẾ CASE ID (DATA HYGIENE):")
ent_cids = [it["events"][0]["case:concept:name"] for it in items if it["ground_truth_label"] == "ENTAILED"]
all_cids_bench = [it["events"][0]["case:concept:name"] for it in items]
dev_cids = {it["events"][0]["case:concept:name"] for it in items if it["rule_id"] in DEV_RULE_IDS}
test_cids = {it["events"][0]["case:concept:name"] for it in items if it["rule_id"] in HELDOUT_TEST_RULE_IDS}

ent_by_rule = {}
con_by_rule = {}
for it in items:
    rid = it["rule_id"]
    if it["ground_truth_label"] == "ENTAILED":
        ent_by_rule[rid] = ent_by_rule.get(rid, 0) + 1
    elif it["ground_truth_label"] == "CONTRADICTED":
        con_by_rule[rid] = con_by_rule.get(rid, 0) + 1

for rid in [f"R{i:02d}" for i in range(1, 23)]:
    assert ent_by_rule.get(rid, 0) >= 4, f"{rid} starved in ENTAILED: {ent_by_rule.get(rid, 0)}"
    assert con_by_rule.get(rid, 0) >= 4, f"{rid} starved in CONTRADICTED: {con_by_rule.get(rid, 0)}"

print(f"  ENTAILED unique Case IDs: {len(set(ent_cids))}/{len(ent_cids)}")
assert len(set(ent_cids)) == len(ent_cids), f"ENTAILED Case IDs recycled: {len(set(ent_cids))}/{len(ent_cids)}"
print(f"  All benchmark items unique Case IDs: {len(set(all_cids_bench))}/{len(all_cids_bench)}")
assert len(set(all_cids_bench)) == len(all_cids_bench), f"Benchmark Case IDs recycled: {len(set(all_cids_bench))}/{len(all_cids_bench)}"
print(f"  DEV vs HELDOUT Case ID overlap: {len(dev_cids & test_cids)}")
assert len(dev_cids & test_cids) == 0, "DEV and HELDOUT benchmark items share Case IDs!"

print("\n=== TẤT CẢ CÁC KIỂM TRA ĐỀU VƯỢT QUA HOÀN TOÀN (100% VALIDATED) ===")
