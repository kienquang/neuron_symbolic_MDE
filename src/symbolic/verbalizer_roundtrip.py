"""
Bước 3.1: Kiểm chứng Ràng buộc Không cần Đáp án chuẩn (Deterministic Verbalization & Roundtrip Check)
Tham khảo:
- Bài OCL2026 (OVAS): Mục 3.4.6 & Mục 5.3 (Reference-free verification scenarios)
- Bài IJCAI 2025 (Declarative PM) & Roundtrip Check (arXiv:2604.25031):
  Dịch ngược tất định AST DECLARE sang câu ngôn ngữ tự nhiên chuẩn hóa (verbalization)
  và đối chiếu độ trung thực ngữ nghĩa với điều khoản gốc trong directive_2008_48_EC.pdf.
"""

import json
import re
from typing import Any, Dict, Tuple

TIME_UNIT_NAMES = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "calendar days",
}


def verbalize_declare_ast(ast_dict: Dict[str, Any]) -> str:
    """
    1. Hàm dịch ngược tất định (Deterministic Verbalizer) theo mẫu của Declare4Py & IJCAI 2025.
    Chuyển cây cú pháp DeclareConstraintAST thành câu tiếng Anh chuẩn hóa để kiểm tra Roundtrip.
    """
    tpl = ast_dict["template_name"]
    act_a = ast_dict["activation_activity"]
    act_b = ast_dict.get("target_activity")
    cond = (
        f" when {ast_dict['activation_attr']} {ast_dict['activation_op']} {ast_dict['activation_val']}"
        if ast_dict.get("activation_attr")
        else ""
    )
    unit_label = TIME_UNIT_NAMES.get(
        str(ast_dict.get("time_unit") or "d"),
        str(ast_dict.get("time_unit") or "d"),
    )
    time_str = (
        f" within {ast_dict['time_max']} {unit_label}"
        if ast_dict.get("time_max") is not None
        else ""
    )

    mapping = {
        "Existence": f"Activity '{act_a}'{cond} must occur at least once in the credit case.",
        "Absence": f"Activity '{act_a}'{cond} must never occur in the credit case.",
        "Init": f"Every credit case must start with activity '{act_a}'{cond}.",
        "Exactly1": f"Activity '{act_a}'{cond} must occur exactly once in the credit case.",
        "Choice": f"Either activity '{act_a}' or activity '{act_b}'{cond} must occur in the credit case.",
        "Exclusive Choice": f"Either activity '{act_a}' or activity '{act_b}'{cond} must occur, but not both.",
        "Responded Existence": f"If activity '{act_a}'{cond} occurs in the credit case, then '{act_b}' must also occur (before or after).",
        "Precedence": f"Whenever '{act_b}' occurs, '{act_a}'{cond} must have occurred BEFORE it{time_str}.",
        "Alternate Precedence": f"Each time '{act_b}' occurs, '{act_a}'{cond} must have occurred BEFORE it without another '{act_b}' in between{time_str}.",
        "Chain Precedence": f"Immediately before '{act_b}' occurs, '{act_a}'{cond} must occur{time_str}.",
        "Response": f"Whenever '{act_a}'{cond} occurs, '{act_b}' must eventually occur AFTER it{time_str}.",
        "Alternate Response": f"Each time '{act_a}'{cond} occurs, '{act_b}' must occur AFTER it before '{act_a}' recurs{time_str}.",
        "Chain Response": f"Immediately after '{act_a}'{cond} occurs, '{act_b}' must occur{time_str}.",
        "Not Responded Existence": f"If '{act_a}'{cond} occurs, '{act_b}' must never occur in the credit case.",
        "Not Response": f"Whenever '{act_a}'{cond} occurs, '{act_b}' must NOT occur after it{time_str}.",
        "Not Precedence": f"Whenever '{act_b}' occurs, '{act_a}'{cond} must NOT have occurred before it{time_str}.",
        "Not Co-Existence": f"Activities '{act_a}'{cond} and '{act_b}' cannot both occur in the same credit case.",
    }
    return mapping.get(tpl, f"{tpl}[{act_a}, {act_b}]{cond}{time_str}")


def check_roundtrip_fidelity(
    ast_dict: Dict[str, Any],
    retrieved_chunk: Dict[str, Any],
    llm_client: Any,
) -> Tuple[bool, str]:
    """
    2. Kiểm tra Roundtrip (Dịch ngược đối chiếu với điều khoản trong directive_2008_48_EC.pdf).
    Trả về (True, "Roundtrip check passed.") nếu EQUIVALENT,
    hoặc (False, "[Layer 3 Semantic <VERDICT>]: ...") nếu REVERSED_ORDER, THRESHOLD_MISMATCH, hoặc BASELESS.
    """
    verbalized_rule = verbalize_declare_ast(ast_dict)
    prompt = f"""Compare the original EU Directive clause with the back-translated process constraint:
- Original Legal Clause ({retrieved_chunk['article_id']}): "{retrieved_chunk['text']}"
- Back-translated Constraint: "{verbalized_rule}"

Classify their semantic relation into strictly ONE of:
1. EQUIVALENT: The constraint accurately captures the temporal order, obligation, and thresholds of the clause.
2. REVERSED_ORDER: The constraint confuses prerequisite (Precedence) with consequence (Response).
3. THRESHOLD_MISMATCH: Numeric bounds (days, EUR, %) or conditions do not match the clause.
4. BASELESS: The original clause does NOT contain or support this process constraint at all.

Return JSON: {{"verdict": "...", "diagnostic_feedback": "..."}}
"""
    if hasattr(llm_client, "chat_json"):
        res = llm_client.chat_json(
            prompt,
            temperature=0.0,
            ast_dict=ast_dict,
            retrieved_chunk=retrieved_chunk,
        )
    else:
        raw = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        res = json.loads(raw)

    verdict = res.get("verdict", "EQUIVALENT")
    if verdict == "EQUIVALENT":
        return True, "Roundtrip check passed."

    return (
        False,
        f"[Layer 3 Semantic {verdict}]: {res.get('diagnostic_feedback', '')} "
        f"(Back-translation: {verbalized_rule})",
    )
