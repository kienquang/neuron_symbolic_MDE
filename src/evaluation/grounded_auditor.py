"""
Bước 4.3: Sinh Báo cáo Giải trình có Khóa Nguồn (Grounded Audit Report) & Hậu kiểm Chống Bịa đặt
Tham khảo:
- Bài "Grounding LLM Explanations for Process Mining" (CEUR Vol-4259)
- Bài "Know Your Limits" (arXiv:2606.16118)
- Bài OCL2026 (OVAS):
  Không để LLM tự suy luận kết quả kiểm chứng (chống "scope laundering").
  Ép LLM chỉ được diễn đạt lại Justification Tree đã tính sẵn ở Bước 4.2 ở mức temperature = 0.0,
  kèm hàm hậu kiểm (Post-hoc Grounding Guard) đối chiếu 100% mã case_id, trạng thái, số ngày và số hiệu Article.
"""

import json
from typing import Any, Dict, List


class DeterministicAuditNarratorClient:
    """
    Client diễn đạt Báo cáo Giải trình Kiểm toán (Compliance Auditor) khóa chặt vào Justification Tree
    ở mức temperature = 0.0, đảm bảo trích dẫn chính xác 100% số liệu toán học đã tính ở Bước 4.2.
    Cũng tương thích với mọi LLMClient có phương thức `.chat(prompt_or_messages, temperature=0.0)`.
    """

    def chat(self, prompt_or_messages: Any, temperature: float = 0.0) -> str:
        if isinstance(prompt_or_messages, str):
            prompt_text = prompt_or_messages
        else:
            prompt_text = prompt_or_messages[-1]["content"]

        # Bóc tách Justification Tree từ prompt nếu có
        marker = "[JUSTIFICATION TREE JSON]:"
        if marker in prompt_text:
            raw_tree = prompt_text.split(marker, 1)[1].strip()
            try:
                tree = json.loads(raw_tree)
                return self._render_from_tree(tree)
            except Exception:
                pass
        return prompt_text

    @staticmethod
    def _render_from_tree(tree: Dict[str, Any]) -> str:
        status = tree["audit_status"]
        reason_cat = tree["reason_category"]
        norm = tree["normative_node"]
        sym = tree["symbolic_rule_node"]
        ev = tree["trace_evidence_node"]

        art_id = norm["article_id"]
        art_title = norm.get("article_title", "")
        case_id = ev["case_id"]
        details = ev["proof_or_counterexample"]
        formula = sym["declare_formula"]

        if status == "CONTRADICTED" and isinstance(details, dict):
            subtype = details.get("violation_subtype", "VIOLATION")
            dev_mag = details.get("deviation_magnitude", "")
            mcs = details.get("minimal_correction_mcs", "")
            act_ev = details.get("activation_event", {})
            tgt_ev = details.get("target_event", {})
            missing_ev = details.get("missing_event", "")

            if subtype == "DEADLINE_EXCEEDED":
                return (
                    f"[BÁO CÁO KIỂM TOÁN TUÂN THỦ - KẾT LUẬN: {status}]\n"
                    f"- Hồ sơ kiểm toán: {case_id}\n"
                    f"- Căn cứ pháp lý: {norm['directive']} - {art_id} ({art_title})\n"
                    f"- Ràng buộc hình thức (DECLARE): {formula}\n"
                    f"- Bằng chứng vi phạm ({subtype}): Sự kiện kích hoạt '{act_ev.get('activity')}' xảy ra lúc "
                    f"{act_ev.get('timestamp')}, nhưng sự kiện phản hồi '{tgt_ev.get('activity')}' diễn ra lúc "
                    f"{tgt_ev.get('timestamp')} (thời gian thực tế: {details.get('actual_duration_days')} ngày so với "
                    f"giới hạn tối đa {details.get('allowed_max_days')} ngày). {dev_mag}\n"
                    f"- Khuyến nghị khắc phục tối thiểu (Minimal Correction - MCS): {mcs}"
                )
            if subtype == "MISSING_PREREQUISITE_ACTIVITY":
                return (
                    f"[BÁO CÁO KIỂM TOÁN TUÂN THỦ - KẾT LUẬN: {status}]\n"
                    f"- Hồ sơ kiểm toán: {case_id}\n"
                    f"- Căn cứ pháp lý: {norm['directive']} - {art_id} ({art_title})\n"
                    f"- Ràng buộc hình thức (DECLARE): {formula}\n"
                    f"- Bằng chứng vi phạm ({subtype}): Sự kiện đích '{tgt_ev.get('activity')}' diễn ra lúc "
                    f"{tgt_ev.get('timestamp')} nhưng thiếu sự kiện tiền đề bắt buộc '{missing_ev}'. {dev_mag}\n"
                    f"- Khuyến nghị khắc phục tối thiểu (Minimal Correction - MCS): {mcs}"
                )
            if subtype == "TEMPORAL_ORDER_INVERSION":
                return (
                    f"[BÁO CÁO KIỂM TOÁN TUÂN THỦ - KẾT LUẬN: {status}]\n"
                    f"- Hồ sơ kiểm toán: {case_id}\n"
                    f"- Căn cứ pháp lý: {norm['directive']} - {art_id} ({art_title})\n"
                    f"- Ràng buộc hình thức (DECLARE): {formula}\n"
                    f"- Bằng chứng vi phạm ({subtype}): Sự kiện đích '{tgt_ev.get('activity')}' ({tgt_ev.get('timestamp')}) "
                    f"xảy ra trước sự kiện tiền đề '{act_ev.get('activity')}' ({act_ev.get('timestamp')}). {dev_mag}\n"
                    f"- Khuyến nghị khắc phục tối thiểu (Minimal Correction - MCS): {mcs}"
                )
            return (
                f"[BÁO CÁO KIỂM TOÁN TUÂN THỦ - KẾT LUẬN: {status}]\n"
                f"- Hồ sơ kiểm toán: {case_id}\n"
                f"- Căn cứ pháp lý: {norm['directive']} - {art_id} ({art_title})\n"
                f"- Ràng buộc hình thức (DECLARE): {formula}\n"
                f"- Bằng chứng vi phạm ({subtype}): {dev_mag}\n"
                f"- Khuyến nghị khắc phục tối thiểu (Minimal Correction - MCS): {mcs}"
            )

        if status == "BASELESS":
            return (
                f"[BÁO CÁO KIỂM TOÁN TUÂN THỦ - KẾT LUẬN: {status}]\n"
                f"- Hồ sơ kiểm toán: {case_id}\n"
                f"- Căn cứ pháp lý đối chiếu: {norm['directive']} - {art_id} ({art_title})\n"
                f"- Phân loại nguyên nhân ({reason_cat}): Không đủ bằng chứng xác thực.\n"
                f"- Chi tiết chẩn đoán an toàn Φ / Văn bản: {details}"
            )

        # ENTAILED
        msg = details.get("msg", str(details)) if isinstance(details, dict) else str(details)
        return (
            f"[BÁO CÁO KIỂM TOÁN TUÂN THỦ - KẾT LUẬN: {status}]\n"
            f"- Hồ sơ kiểm toán: {case_id}\n"
            f"- Căn cứ pháp lý: {norm['directive']} - {art_id} ({art_title})\n"
            f"- Ràng buộc hình thức (DECLARE): {formula}\n"
            f"- Bằng chứng tuân thủ: {msg}"
        )


import re

def verify_posthoc_grounding(
    justification_tree: Dict[str, Any],
    explanation_text: str,
) -> Dict[str, Any]:
    """
    Chốt chặn Hậu kiểm (Post-hoc Grounding Guard):
    1. Kiểm tra 100% mã hồ sơ (case_id), số hiệu điều khoản (article_id), nhãn kết luận (audit_status).
    2. Ngăn chặn hiện tượng mù ngữ cảnh phủ định (Negation Blindness, ví dụ: 'KHÔNG PHẢI là CONTRADICTED' hoặc 'not CONTRADICTED').
    3. Kiểm tra hai chiều (Bidirectional Guard): phát hiện các số hiệu điều khoản bịa đặt lạ (như Article 99).
    4. Kiểm tra toàn bộ các mốc độ lệch định lượng (actual_duration_days, allowed_max_days, excess_days).
    """
    case_id = str(justification_tree["trace_evidence_node"]["case_id"])
    article_id = str(justification_tree["normative_node"]["article_id"])
    audit_status = str(justification_tree["audit_status"])
    details = justification_tree["trace_evidence_node"]["proof_or_counterexample"]

    missing_anchors: List[str] = []

    # 1. Kiểm tra sự hiện diện của mã hồ sơ và số hiệu điều khoản
    if case_id not in explanation_text:
        missing_anchors.append(f"case_id '{case_id}'")
    if article_id not in explanation_text:
        missing_anchors.append(f"article_id '{article_id}'")

    # 2. Kiểm tra nhãn kết luận và phát hiện phủ định (Negation Blindness Guard)
    if audit_status not in explanation_text:
        missing_anchors.append(f"audit_status '{audit_status}'")
    else:
        # Kiểm tra xem nhãn có bị đặt sau từ phủ định hay không
        negation_pattern = re.compile(
            rf"\b(?:không\s+(?:phải|phải\s+là|được|coi\s+là)?|chưa\s+(?:phải)?|not|never|non-|neither)\s+{re.escape(audit_status)}\b",
            re.IGNORECASE,
        )
        if negation_pattern.search(explanation_text):
            missing_anchors.append(f"negated_audit_status '{audit_status}' (phủ định trái phép kết luận)")

        # Kiểm tra nếu xuất hiện nhãn mâu thuẫn trực tiếp
        conflicting_labels = [s for s in ("ENTAILED", "CONTRADICTED", "BASELESS") if s != audit_status]
        for conflict in conflicting_labels:
            if re.search(rf"\b(?:kết\s+luận|conclusion|verdict|status)[:\s]+{conflict}\b", explanation_text, re.IGNORECASE):
                missing_anchors.append(f"conflicting_verdict '{conflict}' (trái ngược với {audit_status})")

    # 3. Kiểm tra hai chiều chống bịa đặt điều khoản lạ (Bidirectional Citation Guard)
    cited_articles = re.findall(
        r"\b(?:Article|Điều)\s*(\d+(?:\([^)]+\))?)",
        explanation_text,
        re.IGNORECASE,
    )
    expected_art_match = re.search(r"(\d+(?:\([^)]+\))?)", article_id)
    if expected_art_match:
        expected_norm = expected_art_match.group(1).lower().replace(" ", "")
        for cited in cited_articles:
            norm_cited = cited.lower().replace(" ", "")
            if norm_cited != expected_norm:
                missing_anchors.append(f"unauthorized_article_hallucination 'Article {cited}'")

    # 4. Kiểm tra các con số định lượng độ lệch
    if isinstance(details, dict):
        if "actual_duration_days" in details and details["actual_duration_days"] is not None:
            dur_str = str(details["actual_duration_days"])
            if dur_str not in explanation_text:
                missing_anchors.append(f"actual_duration_days '{dur_str}'")

        if "allowed_max_days" in details and details["allowed_max_days"] is not None:
            max_str = str(details["allowed_max_days"])
            if max_str not in explanation_text:
                missing_anchors.append(f"allowed_max_days '{max_str}'")

        if "excess_days" in details and details["excess_days"] is not None:
            exc_val = details["excess_days"]
            exc_str = str(exc_val)
            try:
                exc_round = f"{float(exc_val):.2f}"
            except (ValueError, TypeError):
                exc_round = exc_str
            if exc_str not in explanation_text and exc_round not in explanation_text:
                missing_anchors.append(f"excess_days '{exc_str}'")

    return {
        "is_citation_verified": len(missing_anchors) == 0,
        "missing_anchors": missing_anchors,
    }


def generate_accountable_explanation(
    justification_tree: Dict[str, Any],
    llm_client: Any = None,
) -> Dict[str, Any]:
    """
    Bước 4.3: Dùng LLM diễn đạt lại Cây biện minh tất định (xpSHACL / CEUR Vol-4259)
    kèm chốt chặn kiểm tra hậu kỳ đảm bảo không sai lệch số liệu và vòng lặp tự thử lại (1-round retry).
    """
    if llm_client is None:
        llm_client = DeterministicAuditNarratorClient()

    tree_json_str = json.dumps(justification_tree, indent=2, ensure_ascii=False, default=str)
    prompt = f"""Bạn là Kiểm toán viên Tuân thủ Quy trình (Compliance Auditor).
Dựa TUYỆT ĐỐI vào Cây Biện minh Tất định (Justification Tree) dưới đây, hãy viết báo cáo giải trình bằng tiếng Việt.
QUY TẮC BẮT BUỘC:
1. Giữ nguyên trạng thái kết luận: {justification_tree['audit_status']}.
2. Trích dẫn chính xác mã hồ sơ (case_id), số hiệu điều khoản ({justification_tree['normative_node']['article_id']}), tên sự kiện và các mốc thời gian/số ngày lệch.
3. Nêu rõ khuyến nghị khắc phục tối thiểu (minimal_correction_mcs) nếu trạng thái là CONTRADICTED, hoặc nêu rõ dữ liệu bị khuyết nếu trạng thái là BASELESS.

[JUSTIFICATION TREE JSON]:
{tree_json_str}
"""
    # Chạy ở temperature = 0.0 theo chuẩn thực nghiệm của bài OCL2026
    explanation_text = llm_client.chat(prompt, temperature=0.0)

    # Chốt chặn Hậu kiểm (Post-hoc Grounding Guard)
    grounding_check = verify_posthoc_grounding(justification_tree, explanation_text)

    # Cơ chế tự thử lại (1-round retry loop) nếu chốt chặn hậu kiểm phát hiện lỗi
    if not grounding_check["is_citation_verified"] and hasattr(llm_client, "chat"):
        retry_prompt = (
            f"{prompt}\n\n"
            f"[CẢNH BÁO HẬU KIỂM - YÊU CẦU TỰ HIỆU CHỈNH]:\n"
            f"Văn bản giải trình vừa sinh đã bị Chốt chặn Hậu kiểm (Post-hoc Grounding Guard) từ chối vì:\n"
            f"- Các mỏ neo bị thiếu hoặc sai lệch: {grounding_check['missing_anchors']}.\n"
            f"Yêu cầu viết lại tuyệt đối chính xác: Trích dẫn đúng 100% case_id, article_id, "
            f"giữ nguyên trạng thái kết luận '{justification_tree['audit_status']}' (không phủ định), "
            f"không bịa đặt thêm số hiệu Điều khoản nào khác ngoài {justification_tree['normative_node']['article_id']}."
        )
        retry_text = llm_client.chat(retry_prompt, temperature=0.0)
        retry_check = verify_posthoc_grounding(justification_tree, retry_text)
        if retry_check["is_citation_verified"]:
            explanation_text = retry_text
            grounding_check = retry_check

    case_id = justification_tree["trace_evidence_node"]["case_id"]

    return {
        "case_id": case_id,
        "final_label": justification_tree["audit_status"],
        "reason_category": justification_tree["reason_category"],
        "is_citation_verified": grounding_check["is_citation_verified"],
        "grounding_guard_details": grounding_check,
        "justification_tree": justification_tree,
        "natural_language_audit_report": explanation_text,
    }
