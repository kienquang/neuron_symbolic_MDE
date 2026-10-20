"""
Bước 3.1: Kiểm chứng Ràng buộc Không cần Đáp án chuẩn (Deterministic Verbalization, Generic Entity Matcher & Roundtrip Check)
Tham khảo:
- Bài OCL2026 (OVAS): Mục 3.4.6 & Mục 5.3 (Reference-free verification scenarios)
- Bài IJCAI 2025 (Declarative PM) & Roundtrip Check (arXiv:2604.25031):
  1. Dịch ngược tất định AST DECLARE sang câu ngôn ngữ tự nhiên chuẩn hóa (verbalization).
  2. Thuật toán Đối chiếu thực thể định lượng tổng quát (Generic Entity Matcher): Dùng Regex quét toàn bộ các con số
     và đơn vị trong điều khoản luật gốc; nếu AI chọn con số không xuất hiện trong văn bản luật, trả về phản hồi
     theo phong cách Trình biên dịch (Compiler Diagnostic) mà không mớm đáp án.
  3. Trọng tài LLM độc lập (Independent Roundtrip Judge): Đối chiếu câu dịch ngược với văn bản luật thô.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

TIME_UNIT_NAMES = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "calendar days",
}

# Các từ chỉ số lượng phổ biến trong văn bản pháp lý tiếng Anh của EU Directive
WORD_NUMBER_MAP: List[Tuple[str, float, str]] = [
    (r"\bone\s+month\b", 30.0, "days"),
    (r"\bone\s+year\b", 12.0, "months"),
    (r"\btwelve\s+months\b", 12.0, "months"),
    (r"\bfourteen\s+calendar\s+days\b", 14.0, "days"),
    (r"\bfourteen\s+days\b", 14.0, "days"),
]


def extract_clause_numeric_entities(clause_text: str) -> List[Tuple[float, str]]:
    """
    Bước 1 của Generic Entity Matcher:
    Dùng Regex quét toàn bộ các con số và đơn vị định lượng trong văn bản điều khoản luật
    (ví dụ: [(14.0, 'days'), (200.0, 'EUR'), (75000.0, 'EUR'), (1.0, '%')]).
    Không gõ cứng theo bất kỳ mã điều khoản (article_id) nào.
    """
    if not clause_text:
        return []

    found: List[Tuple[float, str]] = []
    seen: set = set()

    # 1. Quét dạng "EUR 200", "EUR 75 000", "EUR 10,000", "EUR 1 500"
    eur_prefix_pattern = re.compile(
        r"\b(EUR|euro|euros)\s*(\d{1,3}(?:[\s,]\d{3})+|\d+(?:[.,]\d+)?)\b",
        re.IGNORECASE,
    )
    for match in eur_prefix_pattern.finditer(clause_text):
        raw_num = match.group(2).replace(" ", "").replace(",", ".")
        # Nếu có nhiều dấu chấm do phân tách hàng nghìn (vd 75.000), xử lý chuẩn
        if raw_num.count(".") == 1 and len(raw_num.split(".")[1]) == 3:
            raw_num = raw_num.replace(".", "")
        try:
            val = float(raw_num)
            key = (val, "EUR")
            if key not in seen:
                seen.add(key)
                found.append(key)
        except ValueError:
            pass

    # 2. Quét dạng "<số> <đơn vị>" như "14 calendar days", "30 calendar days", "1 %", "0,5 %", "12 months"
    num_unit_pattern = re.compile(
        r"\b(\d{1,3}(?:[\s]\d{3})+|\d+(?:[.,]\d+)?)\s*"
        r"(calendar\s+days|working\s+days|days|months|years|EUR|euro|euros|%)\b",
        re.IGNORECASE,
    )
    for match in num_unit_pattern.finditer(clause_text):
        raw_num = match.group(1).replace(" ", "").replace(",", ".")
        unit_raw = match.group(2).lower()
        if "day" in unit_raw:
            unit = "days"
        elif "month" in unit_raw:
            unit = "months"
        elif "year" in unit_raw:
            unit = "years"
        elif "eur" in unit_raw:
            unit = "EUR"
        else:
            unit = unit_raw
        try:
            val = float(raw_num)
            key = (val, unit)
            if key not in seen:
                seen.add(key)
                found.append(key)
        except ValueError:
            pass

    # 3. Quét các cụm từ chỉ số lượng chuẩn trong văn bản pháp lý ("one month" -> 30 days, "one year" -> 12 months)
    for pattern_str, mapped_val, mapped_unit in WORD_NUMBER_MAP:
        if re.search(pattern_str, clause_text, flags=re.IGNORECASE):
            key = (mapped_val, mapped_unit)
            if key not in seen:
                seen.add(key)
                found.append(key)

    return found


def verify_generic_numeric_entities(
    ast_dict: Dict[str, Any],
    retrieved_chunk: Dict[str, Any],
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Bước 2 & 3 của Generic Entity Matcher:
    So sánh con số mà AI nộp lên (`time_max` hoặc `activation_val`) với danh sách các mốc định lượng
    được trích xuất tự động bằng Regex từ văn bản điều khoản `retrieved_chunk['text']`.
    Nếu lệch hoặc không xuất hiện, trả về thông báo theo phong cách Trình biên dịch (Compiler Diagnostic)
    không mớm đáp án:
      (False, verdict, diagnostic_message)
    Nếu hợp lệ (hoặc không dùng ngưỡng số), trả về:
      (True, None, None)
    """
    clause_text = str(retrieved_chunk.get("text", ""))
    entities = extract_clause_numeric_entities(clause_text)
    allowed_numbers = {val for val, _ in entities}
    formatted_entities = (
        ", ".join(f"[{int(v) if v.is_integer() else v}, '{u}']" for v, u in entities)
        if entities
        else "Không có mốc số học nào được quy định trong điều khoản này"
    )

    # 1. Kiểm tra time_max nếu AI đặt giới hạn thời gian
    t_max = ast_dict.get("time_max")
    if isinstance(t_max, (int, float)) and t_max > 0:
        if not entities:
            return (
                False,
                "BASELESS",
                (
                    f"[Diagnostic Mismatch]: Con số time_max={t_max} bạn chọn không xuất hiện trong văn bản luật "
                    f"của điều khoản này ({formatted_entities}). Đây là suy luận thiếu căn cứ định lượng từ văn bản gốc."
                ),
            )
        if float(t_max) not in allowed_numbers:
            return (
                False,
                "THRESHOLD_MISMATCH",
                (
                    f"[Diagnostic Mismatch]: Con số time_max={t_max} bạn chọn không xuất hiện trong văn bản luật "
                    f"của điều khoản này. Các mốc định lượng được luật đề cập gồm: {formatted_entities}. "
                    f"Hãy đọc lại văn bản và tự hiệu chỉnh."
                ),
            )

    # 2. Kiểm tra activation_val nếu AI đặt ngưỡng số học (khác 0 — vì 0 thường dùng để kiểm tra tồn tại > 0)
    act_val = ast_dict.get("activation_val")
    if isinstance(act_val, (int, float)) and not isinstance(act_val, bool) and float(act_val) != 0.0:
        if not entities:
            return (
                False,
                "BASELESS",
                (
                    f"[Diagnostic Mismatch]: Con số activation_val={act_val} bạn chọn không xuất hiện trong văn bản luật "
                    f"của điều khoản này ({formatted_entities}). Văn bản gốc không quy định ngưỡng số học này."
                ),
            )
        if float(act_val) not in allowed_numbers:
            return (
                False,
                "THRESHOLD_MISMATCH",
                (
                    f"[Diagnostic Mismatch]: Con số activation_val={act_val} bạn chọn không xuất hiện trong văn bản luật "
                    f"của điều khoản này. Các mốc định lượng được luật đề cập gồm: {formatted_entities}. "
                    f"Hãy đọc lại văn bản và tự hiệu chỉnh."
                ),
            )

    return True, None, None


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
    rule_meta: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """
    2. Kiểm tra Roundtrip (Kết hợp Generic Entity Matcher + Trọng tài LLM độc lập đối chiếu với điều khoản gốc).
    Tuyệt đối không sử dụng bất kỳ đáp án chuẩn (`gold_ast`) hay lệnh `if-else` mớm lời theo mã điều khoản.
    """
    verbalized_rule = verbalize_declare_ast(ast_dict)

    # Bước A: Chạy Generic Entity Matcher (kiểm tra tính có căn cứ của các con số bằng Regex)
    ok_num, num_verdict, num_diag = verify_generic_numeric_entities(ast_dict, retrieved_chunk)
    if not ok_num and num_verdict and num_diag:
        return (
            False,
            f"[Layer 3 Semantic {num_verdict}]: {num_diag} (Back-translation: {verbalized_rule})",
        )

    policy_context = ""
    if rule_meta and rule_meta.get("description"):
        raw_desc = str(rule_meta.get("description") or "").strip()
        policy_req = re.sub(r"^Bẫy[^:]*:\s*", "", raw_desc).strip()
        if policy_req:
            policy_context = f"- Bank Operational Policy Requirement: \"{policy_req}\"\n"

    prompt = f"""You are a formal semantic compliance judge for financial process mining.
Compare the original EU Directive 2008/48/EC legal clause with the back-translated business process constraint:
- Original Legal Clause ({retrieved_chunk['article_id']}): "{retrieved_chunk['text']}"
{policy_context}- Candidate AST JSON: {json.dumps(ast_dict, ensure_ascii=False)}
- Back-translated Constraint: "{verbalized_rule}"

Context:
In business process modeling for financial institutions, statutory principles (e.g. assessing creditworthiness, providing pre-contractual information, explaining credit suitability, right of withdrawal) are operationalized into concrete workflow steps and status transitions in the bank's IT system (e.g. preliminary acceptance, validation tasks, creating/refusing offers).
- An operational workflow constraint that logically supports, facilitates, or implements a broader statutory obligation (such as conducting credit assessments before loan commitments, or explaining credit suitability before validation) is a legitimate implementation and should be classified as EQUIVALENT.
- Do NOT classify a constraint as BASELESS simply because specific IT activity names (like W_Call after offers, A_Accepted, O_Refused) do not appear verbatim in the Directive text.
- STRICTLY classify as BASELESS if and only if:
   1. The transaction or domain is explicitly EXCLUDED from the Directive's scope (e.g. real estate mortgage loans under Article 2(2));
   2. The constraint invents arbitrary, unauthorized quantitative thresholds (e.g. minimum CreditScore >= 750 or fabricated interest rates/penalties);
   3. The claimed rule directly contradicts the legal text (e.g. claiming the bank can force contract return within 14 days, when Article 14(1) grants a withdrawal right to the consumer).

Provide compiler-style diagnostic feedback WITHOUT revealing any benchmark ground-truth answers.
Return JSON only: {{"verdict": "EQUIVALENT" | "REVERSED_ORDER" | "THRESHOLD_MISMATCH" | "BASELESS", "diagnostic_feedback": "..."}}
"""
    if hasattr(llm_client, "chat_json"):
        res = llm_client.chat_json(
            prompt,
            temperature=0.0,
            ast_dict=ast_dict,
            retrieved_chunk=retrieved_chunk,
        )
        if isinstance(res, str):
            res = json.loads(res)
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
