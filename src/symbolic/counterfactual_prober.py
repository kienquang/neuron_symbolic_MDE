"""
Bước 3.1 (Kiến trúc Mới): Kiểm chứng Ngữ nghĩa Không cần Đáp án bằng Đột biến Vết Đối chứng
(Counterfactual Trace Mutation Probing).

Lấy cảm hứng từ Kiểm thử Đột biến (Mutation Testing) trong Kỹ thuật Phần mềm:
1. Tiền kiểm tra Thực thể Định lượng Tổng quát (`verify_generic_numeric_entities` bằng Regex) để chặn các ngưỡng số học bịa đặt.
2. Tự động sinh cặp Vết Đối chứng Giả định Tối thiểu $(\tau^+, \tau^-)$ từ công thức ứng viên $c$:
   - $\tau^+$ (Compliant Trace Story): Tình huống hồ sơ ngắn nhất thỏa mãn công thức $c$.
   - $\tau^-$ (Counterfactual Mutant Trace Story): Tình huống hồ sơ đột biến vi phạm công thức $c$
     (Đảo thứ tự, Khuyết hệ quả, Vượt biên thời gian $k+5$ ngày, Đồng xuất hiện xung khắc, hoặc Vượt biên thuộc tính).
3. Đưa $(\tau^+, \tau^-)$ cùng điều khoản luật cho Thẩm phán Độc lập (Blind Legal Judge) phán xử:
   - Nếu công thức $c$ đánh giá $\tau^-$ là Vi phạm, nhưng Thẩm phán Luật phán xử $\tau^-$ vẫn Hợp lệ -> Phát hiện lỗi đảo chiều
     (`Precedence` vs `Response`) hoặc chọn sai hoạt động kích hoạt!
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.mde.constraint_ast import extract_json_payload
from src.symbolic.verbalizer_roundtrip import (
    verbalize_declare_ast,
    verify_generic_numeric_entities,
)


def _normalize_rule_fields(compiled_rule: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chuẩn hóa trường dữ liệu giữa `DeonticNormativeFrame` (`anchor_activity`, `consequent_activity`, `deadline_days`, ...)
    và `DeclareConstraintAST` (`activation_activity`, `target_activity`, `time_max`, ...).
    """
    tpl = compiled_rule.get("template_name") or compiled_rule.get("template") or "Precedence"
    act_a = compiled_rule.get("activation_activity") or compiled_rule.get("anchor_activity") or ""
    act_b = compiled_rule.get("target_activity") or compiled_rule.get("consequent_activity")
    attr = compiled_rule.get("activation_attr") or compiled_rule.get("attribute_guard")
    op = compiled_rule.get("activation_op") or compiled_rule.get("guard_operator")
    val = (
        compiled_rule.get("activation_val")
        if compiled_rule.get("activation_val") is not None
        else compiled_rule.get("guard_threshold")
    )
    d_max = (
        compiled_rule.get("time_max")
        if compiled_rule.get("time_max") is not None
        else compiled_rule.get("deadline_days")
    )
    t_unit = compiled_rule.get("time_unit") or ("d" if d_max is not None else None)

    return {
        "article_id": compiled_rule.get("article_id", ""),
        "template_name": tpl,
        "activation_activity": act_a,
        "target_activity": act_b,
        "activation_attr": attr,
        "activation_op": op,
        "activation_val": val,
        "time_min": compiled_rule.get("time_min", 0 if d_max is not None else None),
        "time_max": d_max,
        "time_unit": t_unit,
    }


def _describe_act(act_name: Optional[str], process_schema: Optional[Dict[str, Any]]) -> str:
    if not act_name:
        return ""
    if process_schema and isinstance(process_schema, dict):
        descs = process_schema.get("activity_descriptions") or {}
        if act_name in descs:
            return f"'{act_name}' ({descs[act_name]})"
    return f"'{act_name}'"


def generate_counterfactual_trace_mutant(
    compiled_rule: Dict[str, Any],
    process_schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Tự động sinh cặp Vết Đối chứng Giả định Tối thiểu $(\tau^+, \tau^-)$:
      - `tau_plus_story`: Tình huống hồ sơ tuân thủ công thức $c$.
      - `tau_minus_story`: Tình huống hồ sơ đột biến vi phạm tối thiểu công thức $c$.
    """
    norm = _normalize_rule_fields(compiled_rule)
    tpl = norm["template_name"]
    act_a = norm["activation_activity"]
    act_b = norm["target_activity"]
    d_max = norm["time_max"]
    attr = norm["activation_attr"]
    op = norm["activation_op"]
    val = norm["activation_val"]

    desc_a = _describe_act(act_a, process_schema)
    desc_b = _describe_act(act_b, process_schema)
    cond_clause = f" (with {attr} {op} {val})" if (attr and val is not None) else ""

    # 1. Ràng buộc có giới hạn thời gian k > 0 (Phân biệt rõ Response vs Precedence kèm deadline_days)
    if tpl in {"Response", "Chain Response", "Alternate Response"} and isinstance(d_max, (int, float)) and d_max > 0:
        d_int = int(d_max)
        violating_days = d_int + 5
        compliant_day = max(1, d_int - 1)
        return {
            "mutation_operator": f"MANDATORY_RESPONSE_AND_DEADLINE_MUTATION (+5 days over {d_int}d)",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Trigger event {desc_a}{cond_clause} occurred on Day 1, and "
                f"mandatory follow-up event {desc_b} was completed on Day {1 + compliant_day} (within {d_int} calendar days)."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Trigger event {desc_a}{cond_clause} occurred on Day 1, "
                f"and EITHER (i) {desc_b} NEVER occurred in the loan case, "
                f"OR (ii) {desc_b} occurred on Day {1 + violating_days} ({violating_days} calendar days elapsed, exceeding the {d_int}-day window)."
            ),
            "tau_asymmetry_story": (
                f"Case C (Directionality & Optionality Check): Under candidate {tpl}, whenever {desc_a}{cond_clause} occurs "
                f"and {desc_b} NEVER happens afterward (e.g., because an optional consumer/branch event did not happen), the trace is "
                f"STRICTLY FLAGGED AS A VIOLATION; conversely, {desc_b} occurring WITHOUT prior {desc_a} is ALLOWED."
            ),
        }

    if tpl in {"Precedence", "Chain Precedence", "Alternate Precedence"} and isinstance(d_max, (int, float)) and d_max > 0:
        d_int = int(d_max)
        violating_days = d_int + 5
        compliant_day = max(1, d_int - 1)
        return {
            "mutation_operator": f"PREREQUISITE_WINDOW_BOUNDARY_MUTATION (+5 days over {d_int}d)",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Prerequisite {desc_a}{cond_clause} occurred on Day 1, and when "
                f"target event {desc_b} occurred on Day {1 + compliant_day}, it was within {d_int} calendar days after {desc_a}."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Target event {desc_b} was executed on Day {1 + violating_days} "
                f"after {desc_a}{cond_clause} on Day 1 ({violating_days} calendar days elapsed, exceeding the {d_int}-day window, "
                f"or {desc_b} occurred without prior {desc_a})."
            ),
            "tau_asymmetry_story": (
                f"Case C (Directionality & Permissibility Check): Under candidate {tpl}, if {desc_a}{cond_clause} occurs on Day 1 "
                f"and {desc_b} NEVER occurs in the loan case, the trace IS ALLOWED AS COMPLIANT."
            ),
        }

    # 2A. Điều kiện tiên quyết NGAY SÁT TRƯỚC (Chain Precedence)
    if tpl == "Chain Precedence":
        return {
            "mutation_operator": "IMMEDIATE_ADJACENCY_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Prerequisite {desc_a}{cond_clause} was executed on Day 1, "
                f"and {desc_b} occurred IMMEDIATELY as the very next step with zero intervening events."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Either {desc_b} occurred without prior {desc_a}{cond_clause}, "
                f"or an intermediate event occurred between {desc_a} and {desc_b} (breaking immediate adjacency)."
            ),
            "tau_asymmetry_story": (
                f"Case C (Permissibility Check): Under Chain Precedence, if {desc_a}{cond_clause} occurs and {desc_b} NEVER "
                f"happens in the case, it IS ALLOWED AS COMPLIANT."
            ),
        }

    # 2B. Điều kiện tiên quyết thông thường (Precedence / Alternate Precedence)
    if tpl in {"Precedence", "Alternate Precedence"}:
        return {
            "mutation_operator": "PREREQUISITE_INVERSION_AND_OMISSION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Prerequisite {desc_a}{cond_clause} was completed on Day 1, "
                f"other intermediate workflow events occurred on Day 2, and {desc_b} was executed later on Day 3 (non-immediate precedence)."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): The bank executed {desc_b} on Day 1 WITHOUT "
                f"performing {desc_a}{cond_clause} beforehand (or {desc_a} was only done later on Day 5)."
            ),
            "tau_asymmetry_story": (
                f"Case C (Directionality & Permissibility Check — A without B): Under candidate {tpl}, if {desc_a}{cond_clause} "
                f"occurs on Day 1 and {desc_b} NEVER occurs afterward, Case C IS ALLOWED AS COMPLIANT."
            ),
        }

    # 3. Nhóm nghĩa vụ kéo theo (Response / Chain Response / Alternate Response / Responded Existence)
    if tpl == "Chain Response":
        return {
            "mutation_operator": "CHAIN_RESPONSE_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Immediately after trigger event {desc_a}{cond_clause} occurred, "
                f"the very next event in the loan case was {desc_b} with no intervening step."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Trigger event {desc_a}{cond_clause} occurred in the loan case, "
                f"but either {desc_b} never occurred afterwards or another unrelated activity intervened before {desc_b}."
            ),
            "tau_asymmetry_story": (
                f"Case C (Directionality Check): Under Chain Response, if {desc_b} occurs WITHOUT prior {desc_a}, "
                f"it IS ALLOWED; only omitting/delaying {desc_b} after {desc_a} violates."
            ),
        }

    if tpl == "Responded Existence":
        return {
            "mutation_operator": "MISSING_COEXISTENT_TARGET_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Trigger event {desc_a}{cond_clause} occurred in the loan case, "
                f"and companion event {desc_b} also occurred somewhere in the same case (before or after {desc_a})."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Trigger event {desc_a}{cond_clause} occurred in the loan case, "
                f"but {desc_b} NEVER occurred anywhere in the case (neither before nor after {desc_a})."
            ),
            "tau_asymmetry_story": (
                f"Case C (Order-Insensitivity Check): Under Responded Existence, {desc_b} occurring BEFORE {desc_a} is ALLOWED "
                f"just like {desc_b} AFTER {desc_a}."
            ),
        }

    if tpl in {"Response", "Alternate Response"}:
        return {
            "mutation_operator": "MISSING_RESPONSE_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): After trigger event {desc_a}{cond_clause} occurred on Day 1, "
                f"the process subsequently executed {desc_b} on Day 2."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Trigger event {desc_a}{cond_clause} occurred in the loan case, "
                f"but follow-up event {desc_b} was NEVER executed afterwards before the case closed."
            ),
            "tau_asymmetry_story": (
                f"Case C (Directionality & Permissibility Check — B without A): Under candidate {tpl}, {desc_b} occurring "
                f"WITHOUT prior {desc_a} is ALLOWED, whereas {desc_a}{cond_clause} occurring WITHOUT subsequent {desc_b} is STRICTLY FLAGGED AS A VIOLATION."
            ),
        }

    # 4. Nhóm loại trừ / cấm đoán hai ngôi (Not Co-Existence / Not Responded Existence / Not Response / Not Precedence)
    if tpl == "Not Response":
        return {
            "mutation_operator": "FORBIDDEN_SUBSEQUENT_RESPONSE_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Event {desc_a}{cond_clause} occurred, and conflicting event "
                f"{desc_b} NEVER occurred afterwards (any occurrence before {desc_a} or absence of {desc_b} is allowed)."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Trigger event {desc_a}{cond_clause} occurred first, "
                f"and subsequently conflicting event {desc_b} WAS executed afterwards in the exact same loan application."
            ),
            "tau_asymmetry_story": (
                f"Case C (Directionality Check — B before A): Under directional Not Response, if {desc_b} occurs FIRST on Day 1 "
                f"and {desc_a}{cond_clause} occurs LATER on Day 5, Case C IS ALLOWED AS COMPLIANT."
            ),
        }

    if tpl == "Not Precedence":
        return {
            "mutation_operator": "FORBIDDEN_PRECEDING_ANTECEDENT_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Event {desc_b} occurred without {desc_a}{cond_clause} ever "
                f"preceding it beforehand (either {desc_a} never occurred or only occurred after {desc_b})."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Event {desc_a}{cond_clause} occurred first, "
                f"and later in the exact same loan application event {desc_b} occurred after it."
            ),
            "tau_asymmetry_story": (
                f"Case C (Directionality Check — B before A): Under directional Not Precedence, if {desc_b} occurs FIRST on Day 1 "
                f"and {desc_a}{cond_clause} occurs LATER on Day 5, Case C IS ALLOWED AS COMPLIANT."
            ),
        }

    if tpl in {"Not Co-Existence", "Not Responded Existence"}:
        return {
            "mutation_operator": "CO_OCCURRENCE_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Event {desc_a}{cond_clause} occurred, and conflicting event "
                f"{desc_b} never occurred anywhere in the loan application."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Both {desc_a}{cond_clause} AND {desc_b} were "
                f"executed within the exact same loan application."
            ),
            "tau_asymmetry_story": (
                f"Case C (Order-Inversion Check — B before A): Under symmetric {tpl}, even if {desc_b} occurs FIRST on Day 1 "
                f"and {desc_a}{cond_clause} occurs ONLY LATER on Day 5 (no {desc_b} after {desc_a}), Case C is STRICTLY FORBIDDEN AS A VIOLATION "
                f"(whereas directional Not Response or Not Precedence would allow B before A)."
            ),
        }

    has_guard = attr is not None and op is not None and val is not None

    # 5. Nhóm cấm đoán đơn ngôi có điều kiện thuộc tính hoặc cấm toàn phần (Absence)
    if tpl == "Absence":
        if has_guard:
            return {
                "mutation_operator": "FORBIDDEN_ATTRIBUTE_MUTATION",
                "tau_plus_story": (
                    f"Case A (Compliant Trace τ+): Event {desc_a} was executed with a valid attribute value where "
                    f"the prohibited condition ({attr} {op} {val}) did NOT hold."
                ),
                "tau_minus_story": (
                    f"Counterfactual Case B (Mutant Trace τ-): Event {desc_a} was executed in the loan process "
                    f"while the prohibited condition ({attr} {op} {val}) held TRUE."
                ),
            }
        return {
            "mutation_operator": "FORBIDDEN_ACTIVITY_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Prohibited event {desc_a} NEVER occurred anywhere in the loan case."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Prohibited event {desc_a} WAS executed in the loan case."
            ),
        }

    # 6. Mặc định cho Existence / Init / Exactly1 (có hoặc không có điều kiện thuộc tính)
    if has_guard:
        return {
            "mutation_operator": "ATTRIBUTE_BOUNDARY_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): Event {desc_a} occurred satisfying attribute condition ({attr} {op} {val})."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): Event {desc_a} occurred, but attribute {attr} violated "
                f"the required condition ({attr} {op} {val} was FALSE)."
            ),
            "tau_asymmetry_story": (
                f"Case C (Missing Second-Endpoint Check): Under single-activity Existence on {desc_a} with ({attr} {op} {val}), "
                f"a trace containing ONLY {desc_a} (and omitting any follow-up or subsequent milestone mentioned in the policy) "
                f"is treated as FULLY COMPLIANT."
            ),
        }
    if tpl == "Init":
        return {
            "mutation_operator": "MISSING_INIT_MUTATION",
            "tau_plus_story": (
                f"Case A (Compliant Trace τ+): The loan process started with {desc_a} as its very first event."
            ),
            "tau_minus_story": (
                f"Counterfactual Case B (Mutant Trace τ-): The loan process began with a different event before "
                f"{desc_a} (or never executed {desc_a} at all)."
            ),
        }
    return {
        "mutation_operator": "MISSING_EXISTENCE_MUTATION",
        "tau_plus_story": (
            f"Case A (Compliant Trace τ+): Mandatory event {desc_a} was executed in the loan application."
        ),
        "tau_minus_story": (
            f"Counterfactual Case B (Mutant Trace τ-): Mandatory event {desc_a} was completely OMITTED from "
            f"the entire loan application."
        ),
        "tau_asymmetry_story": (
            f"Case C (Missing Second-Endpoint Check): Under single-activity Existence on {desc_a}, NO causal ordering or "
            f"companion workflow milestone is checked (a trace with {desc_a} alone is COMPLIANT)."
        ),
    }


def verify_via_counterfactual_probing(
    compiled_rule: Dict[str, Any],
    retrieved_chunk: Dict[str, Any],
    llm_client: Any,
    rule_meta: Optional[Dict[str, Any]] = None,
    process_schema: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """
    Kiểm chứng Ngữ nghĩa bằng Đột biến Vết Đối chứng (Counterfactual Trace Mutation Probing):
      1. Chạy `verify_generic_numeric_entities` (Regex Pre-Filter) để chặn đứng các con số bịa đặt không có trong luật.
      2. Sinh cặp Vết Đối chứng $(\tau^+, \tau^-)$ từ công thức vừa biên dịch.
      3. Đưa $(\tau^+, \tau^-)$ cùng điều khoản luật cho Thẩm phán Độc lập (Blind Legal Judge) phán xử.
    """
    norm_ast = _normalize_rule_fields(compiled_rule)
    verbalized_rule = verbalize_declare_ast(norm_ast)

    # Bước 0: Nếu Bộ biên dịch Deontic MDE ở Giai đoạn 1 đã chặn điều khoản Miễn trừ (EXEMPTION) hoặc Thiếu thuộc tính Log (Φ)
    if compiled_rule.get("deontic_baseless_reason"):
        return (
            False,
            f"{compiled_rule['deontic_baseless_reason']} (Back-translation: {verbalized_rule})",
        )

    policy_req = ""
    policy_context = ""
    if rule_meta and rule_meta.get("description"):
        raw_desc = str(rule_meta.get("description") or "").strip()
        policy_req = re.sub(
            r"^(?:Quy định gài bẫy|Quy định bẫy|Gài bẫy|Bẫy|Trap)[^:\-]*[:\-]\s*",
            "",
            raw_desc,
            flags=re.IGNORECASE,
        ).strip()
        if policy_req:
            policy_context = f'- Bank Operational Policy Requirement: "{policy_req}"\n'

    # Bước 1: Kiểm tra tính có căn cứ của các con số định lượng bằng Regex (100% tất định, 0 API call)
    ok_num, num_verdict, num_diag = verify_generic_numeric_entities(
        norm_ast, retrieved_chunk, policy_text=policy_req
    )
    if not ok_num and num_verdict and num_diag:
        return (
            False,
            f"[Layer 3 Semantic {num_verdict}]: {num_diag} (Back-translation: {verbalized_rule})",
        )

    # Nạp process_schema nếu chưa truyền vào
    if not process_schema:
        schema_path = Path("data/processed/process_schema.json")
        if schema_path.exists():
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    process_schema = json.load(f)
            except Exception:
                pass

    mutants = generate_counterfactual_trace_mutant(norm_ast, process_schema=process_schema)
    asym_line = (
        f"\n  3. {mutants['tau_asymmetry_story']}"
        if mutants.get("tau_asymmetry_story")
        else ""
    )

    schema_context = ""
    if process_schema and isinstance(process_schema, dict):
        act_descs = process_schema.get("activity_descriptions") or {}
        schema_lines = []
        if isinstance(act_descs, dict) and act_descs:
            schema_lines.extend([f"  - `{k}`: {v}" for k, v in act_descs.items()])
        ev_attrs = process_schema.get("event_attributes") or {}
        cand_attr = norm_ast.get("activation_attr")
        if cand_attr and isinstance(ev_attrs, dict) and cand_attr in ev_attrs:
            app_acts = ev_attrs[cand_attr].get("applicable_activities") or []
            if app_acts:
                schema_lines.append(
                    f"  - Attribute Domain Ownership: `{cand_attr}` is ONLY logged on activities {app_acts} in the schema."
                )
        if schema_lines:
            schema_context = "- Event Log Activity Data Dictionary:\n" + "\n".join(schema_lines) + "\n"

    judge_prompt = f"""You are an independent EU Financial Law Judge performing Counterfactual Trace Mutation Probing.
Read the EU Directive 2008/48/EC legal clause, the operational policy requirement, and evaluate the synthetic counterfactual scenarios (Case A: τ+, Counterfactual Case B: τ-, and Case C boundary/asymmetry check if shown):
- Original Legal Clause ({retrieved_chunk['article_id']}): "{retrieved_chunk['text']}"
{policy_context}{schema_context}- Candidate Constraint Summary: "{verbalized_rule}"
- Synthetic Trace Suite ({mutants['mutation_operator']}):
  1. {mutants['tau_plus_story']}
  2. {mutants['tau_minus_story']}{asym_line}

Evaluation Principles:
1. Quantitative Entity Grounding:
   - Independently check every quantitative bound (`time_max` or `activation_val`) and temporal unit in the Candidate Constraint against the Original Legal Clause and operational policy.
   - Verify that the operational mapping faithfully preserves every numeric bound and temporal unit stated by the clause and operational policy without inventing, omitting, or altering thresholds.
   - IMPORTANT: When Case A complies within the bound and Counterfactual Case B cleanly violates that bound (e.g., exceeding `time_max` days), `case_a_complies` MUST be `true`, `case_b_violates` MUST be `true`, and `verdict` MUST be `"EQUIVALENT"`. Reserve `"THRESHOLD_MISMATCH"` strictly for cases where the Candidate Constraint itself states an incorrect, altered, or missing bound relative to the legal clause/policy (do NOT label a faithful bound as `THRESHOLD_MISMATCH` merely because mutant Case B breaches it).
2. Temporal Direction, Asymmetry & Immediacy (`REVERSED_ORDER` / `SEMANTIC_MISMATCH`):
   - Carefully evaluate Case C (Directionality / Asymmetry Check):
     * `Precedence(A, B)` ALLOWS `A` without `B` (Case C) and only requires `A` before `B`. If the policy instead makes `B` mandatory whenever `A` happens (so Case C `A without B` is actually a VIOLATION), `Precedence` is reversed/too weak -> set `case_a_complies: false`, `verdict: "REVERSED_ORDER"`.
     * `Response(A, B)` VIOLATES whenever `A` occurs without `B`, and ALLOWS `B` without `A`. If `B` is an optional/conditional event (e.g., consumer cancellation/withdrawal or a branch that may never happen) or if `A` is a prerequisite gate BEFORE `B` can occur, forcing `B` on every `A` reverses the rule (Case C shows `Response` is wrong!) -> set `case_a_complies: false`, `case_b_violates: false`, `verdict: "REVERSED_ORDER"`.
     * `Not Co-Existence(A, B)` is SYMMETRIC and forbids Case C (`B` *before* `A`). If the policy only forbids `B` *after* `A` (`Not Response`) or `A` *before* `B` (`Not Precedence`) while allowing `B` before `A`, set `case_a_complies: false`, `verdict: "SEMANTIC_MISMATCH"`.
     * If the Candidate Constraint is unary (`Existence` with `target_activity=null`, Case C) while the policy requires a relation or prerequisite involving a second workflow activity, set `case_a_complies: false`, `verdict: "SEMANTIC_MISMATCH"`.
     * If immediate step adjacency is explicitly required (no intervening events), standard non-immediate `Precedence`/`Response` is too weak because Case A allows intermediate events (`case_a_complies: false`, `verdict: "SEMANTIC_MISMATCH"`).
3. Activity Endpoint & Lifecycle Granularity Alignment (`SEMANTIC_MISMATCH`):
   - Inspect EVERY candidate activity against all alternatives in the Event Log Activity Data Dictionary:
     * Compare exact lifecycle stages using the schema definitions (e.g., drafting vs. persistence vs. transmission/communication to the customer; initial intake vs. formal acceptance vs. back-office validation; customer acceptance vs. final activation/disbursement approval; official state milestones vs. repeatable human work-item tasks).
   - Respect Attribute Domain Ownership shown in the Data Dictionary: if a rule enforces an event-level attribute predicate and the schema explicitly notes that attribute is ONLY recorded on specific activity(ies), do NOT reject that activity as wrong lifecycle stage.
   - Otherwise, if another activity in the Data Dictionary matches the Operational Policy Requirement clearly better at that exact lifecycle stage (e.g., conflating drafting vs. persistence vs. dispatch for pure control-flow, customer acceptance vs. final approval, or an official milestone vs. a human work-item task), set `case_b_violates: false`, `verdict: "SEMANTIC_MISMATCH"`, and identify both the mismatched activity and why the Data Dictionary distinguishes it.
4. Unsupported, Misattributed, or Overreached Clauses vs Valid Operational Specialization (`is_unsupported_clause: true`, `verdict: "BASELESS"`):
   - IMPORTANT — Permitted Domain Specialization: Bank Operational Policies legitimately specialize abstract EU Directive mandates (such as pre-contractual disclosure, durable-medium terms, creditworthiness checks, right of withdrawal/termination cancellation, or settlement timing) onto concrete internal workflow milestones defined in the schema. Do NOT set `is_unsupported_clause: true` merely because the statutory article expresses the principle at an abstract legal level rather than naming event-log activities or prohibiting declined deals explicitly.
   - Set `is_unsupported_clause: true` and `verdict: "BASELESS"` ONLY IF there is a genuine legal conflict, subject mismatch, or fabrication between the cited Directive clause and the stated operational rule, including:
     (a) Statutory exemption/exclusion or clearly unrelated legal subject/product (e.g., applying an excluded product category or a distinct statutory provision's applicability limit as a generic loan workflow mandate).
     (b) Duty-Holder or Numeric Misattribution: even if a number or duration literally appears in the Original Legal Clause, reject as `"BASELESS"` when the operational policy converts a right, notice window, or optional Member State threshold belonging to a different party/mechanism into an unrelated creditor obligation or eligibility filter.
     (c) Non-Sequitur Action Fabrication: when the clause only grants optional Member State discretion or mandates notifying/disclosing information to the consumer without prescribing an incompatible substantive business action claimed by the policy.

Return strictly JSON:
{{
  "case_a_complies": true | false,
  "case_b_violates": true | false,
  "is_unsupported_clause": true | false,
  "verdict": "EQUIVALENT" | "REVERSED_ORDER" | "SEMANTIC_MISMATCH" | "THRESHOLD_MISMATCH" | "BASELESS",
  "explanation": "..."
}}
"""

    if hasattr(llm_client, "chat_json"):
        res = llm_client.chat_json(
            judge_prompt,
            temperature=0.0,
            ast_dict=norm_ast,
            retrieved_chunk=retrieved_chunk,
        )
        raw_res = json.dumps(res) if isinstance(res, dict) else str(res)
    else:
        raw_res = llm_client.chat(
            [{"role": "user", "content": judge_prompt}],
            temperature=0.0,
        )

    try:
        clean_json = extract_json_payload(raw_res)
        verdict_obj = json.loads(clean_json)
    except Exception as e:
        return (
            False,
            f"[Layer 3 Counterfactual Probe Error]: Blind Judge returned non-JSON verdict ({e}). "
            f"Raw output: {str(raw_res)[:200]}",
        )

    explanation = str(
        verdict_obj.get("explanation")
        or verdict_obj.get("diagnostic_feedback")
        or "No explanation provided."
    )
    verdict_tag = str(verdict_obj.get("verdict") or "").upper().strip()
    case_a_ok = verdict_obj.get("case_a_complies")
    case_b_viol = verdict_obj.get("case_b_violates")

    is_unsupported = verdict_obj.get("is_unsupported_clause") is True
    # 1. Kiểm tra nếu điều khoản không có căn cứ pháp lý (BASELESS / UNSUPPORTED) - Không chấp nhận nếu phán quyết tự mâu thuẫn hoặc unsupported
    if verdict_tag == "BASELESS" or (
        is_unsupported and verdict_tag in ("", "BASELESS", "EQUIVALENT")
    ):
        return (
            False,
            f"[Layer 3 Semantic BASELESS]: [Counterfactual Probe -> BASELESS]: {explanation} (Back-translation: {verbalized_rule})",
        )
    if (
        verdict_tag == "EQUIVALENT"
        and not is_unsupported
        and (
            (case_a_ok is True and case_b_viol is True)
            or (case_a_ok is None and case_b_viol is None)
        )
    ):
        return (
            True,
            f"Counterfactual Probe Passed ({mutants['mutation_operator']}): {explanation}",
        )

    # 3. Nếu bất đồng thuận -> Phát hiện lỗi đảo chiều (Precedence vs Response), sai hoạt động hoặc sai ngưỡng
    err_tag = verdict_tag if verdict_tag in ("REVERSED_ORDER", "SEMANTIC_MISMATCH", "THRESHOLD_MISMATCH") else "SEMANTIC_MISMATCH"
    return (
        False,
        (
            f"[Layer 3 Semantic {err_tag}]: [Counterfactual Mutation Disagreement ({mutants['mutation_operator']})]: "
            f"Your synthesized rule claims '{mutants['tau_minus_story']}' is a violation, "
            f"but under {retrieved_chunk.get('article_id', '')}, Judge determined: {explanation} "
            f"Hint: Check if you confused PREREQUISITE_BEFORE (Precedence) with MANDATORY_RESPONSE (Response), "
            f"symmetric MUTUAL_EXCLUSION (Not Co-Existence) vs directional PROHIBITION + MANDATORY_RESPONSE/PREREQUISITE_BEFORE "
            f"(Not Response / Not Precedence), omitted consequent_activity via UNARY_CONDITION, or selected the wrong lifecycle activity. "
            f"(Back-translation: {verbalized_rule})"
        ),
    )
