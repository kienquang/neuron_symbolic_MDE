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
    
    # Check non-vacuous activation
    if tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
        if act_b not in acts:
            vacuous_entailed.append((it["benchmark_id"], rid, f"Target '{act_b}' not in trace"))
        if rid == "R18":
            max_amt = max(e["OfferedAmount"] for e in events if e.get("OfferedAmount") is not None)
            if max_amt <= 10000:
                vacuous_entailed.append((it["benchmark_id"], rid, f"R18 OfferedAmount {max_amt} <= 10000"))
        if rid == "R17":
            max_cs = max(e["CreditScore"] for e in events if e.get("CreditScore") is not None)
            if max_cs <= 0:
                vacuous_entailed.append((it["benchmark_id"], rid, f"R17 CreditScore {max_cs} <= 0"))
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
r18_con_amounts = []
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
        max_amt = max(e["OfferedAmount"] for e in events if e.get("OfferedAmount") is not None)
        r18_con_amounts.append((it["benchmark_id"], max_amt, subtype))

print(f"  Số mẫu CONTRADICTED không bị vi phạm (is_comp == True): {len(invalid_con)} (Yêu cầu = 0)")
if invalid_con:
    for ic in invalid_con:
        print("    ", ic)
assert len(invalid_con) == 0, "All CONTRADICTED items must evaluate to is_comp == False!"
print("  Phân bố lý do vi phạm trong CONTRADICTED:")
for st, cnt in con_reasons.most_common():
    print(f"    - {st}: {cnt} mẫu")
print(f"  Chi tiết R18 CONTRADICTED ({len(r18_con_amounts)} mẫu):")
for bid, amt, st in r18_con_amounts:
    print(f"    {bid}: OfferedAmount = {amt:,.2f} EUR, lý do: {st}")
    assert amt > 10000, f"R18 CONTRADICTED trace must have OfferedAmount > 10000, got {amt}"

print("\n6. KIỂM TRA CÁC BẪY BASELESS (R23–R30):")
r29_denied_found = 0
r29_no_offer = 0
r30_nan_score = 0
distinct_traces_r23_r28 = set()
for it in items:
    if it["ground_truth_label"] != "BASELESS":
        continue
    rid = it["rule_id"]
    events = it["events"]
    acts = [e["concept:name"] for e in events]
    cname = events[0]["case:concept:name"]
    
    if rid == "R29":
        if "A_Denied" in acts:
            r29_denied_found += 1
        if "O_Create Offer" not in acts:
            r29_no_offer += 1
    elif rid == "R30":
        if all(e.get("CreditScore") is None or pd.isna(e.get("CreditScore")) for e in events):
            r30_nan_score += 1
    else:
        distinct_traces_r23_r28.add(cname)

print(f"  R29: có A_Denied = {r29_denied_found}/12, không có O_Create Offer = {r29_no_offer}/12")
assert r29_denied_found == 12 and r29_no_offer == 12, "R29 must have A_Denied and no O_Create Offer"
print(f"  R30: có CreditScore là null/NaN = {r30_nan_score}/12")
assert r30_nan_score == 12, "R30 must have null CreditScore"
print(f"  R23–R28: số case traces nền khác nhau = {len(distinct_traces_r23_r28)} (Đã đa dạng hóa không trùng lặp)")
assert len(distinct_traces_r23_r28) > 10, "R23-R28 should use diverse traces!"

print("\n=== TẤT CẢ CÁC KIỂM TRA ĐỀU VƯỢT QUA HOÀN TOÀN (100% VALIDATED) ===")
