"""
Bộ Chạy Thực nghiệm Tự động & Xuất Bảng Số liệu Bài báo (RQ1, RQ2, RQ3 Evaluation Runner)
Đã được tái cấu trúc (Refactored) đảm bảo tính khách quan khoa học:
1. Bộ tạo phản hồi CEGIS dùng Thuật toán Đối chiếu Thực thể Tổng quát (Generic Entity Matcher) bằng Regex
   và Kiểm tra Độ rỗng (Vacuity Check) trên Log — XÓA BỎ HOÀN TOÀN các lệnh `if-else` gõ cứng số liệu mớm lời.
2. Baseline 1 (`run_vanilla_rag_baseline`) gọi trực tiếp API của LLM thật (Groq / OpenAI) trên chuỗi văn bản
   lịch sử sự kiện và mốc giờ của từng hồ sơ vay, lưu vào `vanilla_rag_real_cache.json` — XÓA BỎ HOÀN TOÀN công thức modulo `idx % 8`.
"""

import json
import math
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

try:
    from sklearn.metrics import precision_recall_fscore_support
except ImportError:

    def precision_recall_fscore_support(
        y_true: List[str],
        y_pred: List[str],
        labels: List[str],
        average: Optional[str] = None,
        zero_division: int = 0,
    ) -> Tuple[Any, Any, Any, Any]:
        precisions, recalls, f1s, supports = [], [], [], []
        for lbl in labels:
            tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == lbl and yp == lbl)
            fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != lbl and yp == lbl)
            fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == lbl and yp != lbl)
            sup = sum(1 for yt in y_true if yt == lbl)
            p = tp / (tp + fp) if (tp + fp) > 0 else float(zero_division)
            r = tp / (tp + fn) if (tp + fn) > 0 else float(zero_division)
            f1 = (2 * p * r / (p + r)) if (p + r) > 0 else float(zero_division)
            precisions.append(p)
            recalls.append(r)
            f1s.append(f1)
            supports.append(sup)
        if average == "macro":
            return (
                sum(precisions) / len(labels),
                sum(recalls) / len(labels),
                sum(f1s) / len(labels),
                None,
            )
        return precisions, recalls, f1s, supports


from src.mde.constraint_ast import DeclareConstraintAST, validate_declare_ast
from src.mde.typing_environment import ProcessSchemaValidator
from src.symbolic.verbalizer_roundtrip import (
    check_roundtrip_fidelity,
    extract_clause_numeric_entities,
    verify_generic_numeric_entities,
)
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status
from src.evaluation.justification_tree import build_justification_tree, filter_activity_events
from src.evaluation.grounded_auditor import (
    DeterministicAuditNarratorClient,
    generate_accountable_explanation,
)


def validate_ast_against_schema(
    raw_json: str,
    process_schema: Dict[str, Any],
    chunk: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Any]:
    """
    Kiểm tra cấu trúc DeclareConstraintAST và lược đồ quy trình (ProcessSchemaValidator).
    Trả về (True, ast_dict) nếu hợp lệ, hoặc (False, diagnostic_error_msg) nếu vi phạm.
    """
    ok_ast, res_ast = validate_declare_ast(raw_json)
    if not ok_ast:
        return False, str(res_ast)

    ast_obj: DeclareConstraintAST = res_ast  # type: ignore[assignment]
    schema_validator = ProcessSchemaValidator(process_schema)
    ok_schema, msg_schema = schema_validator.validate_ast(ast_obj, retrieved_chunk=chunk)
    if not ok_schema:
        return False, str(msg_schema)

    return True, ast_obj.model_dump()


# Backward-compatible alias
check_layer1_and_layer2 = validate_ast_against_schema


def has_valid_activities_in_schema(
    ast_obj: DeclareConstraintAST,
    process_schema: Dict[str, Any],
) -> bool:
    """Kiểm tra các hoạt động trong AST có thuộc tập valid_activities của lược đồ hay không."""
    valid_acts = set(process_schema.get("valid_activities", []))
    if ast_obj.activation_activity not in valid_acts:
        return False
    if ast_obj.target_activity and ast_obj.target_activity not in valid_acts:
        return False
    return True


def is_executable_against_log_schema(
    ast_obj: DeclareConstraintAST,
    process_schema: Dict[str, Any],
) -> bool:
    """
    Check whether the synthesized AST is schema-valid, non-self-looping,
    and type-conformant against the event log metamodel.
    """
    if not has_valid_activities_in_schema(ast_obj, process_schema):
        return False
    if ast_obj.target_activity is not None and ast_obj.target_activity == ast_obj.activation_activity:
        return False
    if ast_obj.activation_attr:
        clean_attr = ast_obj.activation_attr.strip()
        if clean_attr.startswith(("A.", "T.", "a.", "t.")):
            clean_attr = clean_attr[2:]
        typing_env = ProcessSchemaValidator(process_schema)
        if clean_attr.startswith("case:") or clean_attr in typing_env._case_attr_lookup:
            attr_context = "Case"
        elif clean_attr in typing_env._event_attr_lookup:
            attr_context = "Event"
        else:
            attr_context = "Process"
        ok_type, _ = typing_env.check_type_conformance(
            clean_attr,
            ast_obj.activation_op or "==",
            ast_obj.activation_val,
            context=attr_context,
        )
        if not ok_type:
            return False
        if attr_context == "Event" and clean_attr in typing_env.event_attributes:
            app_acts = typing_env.event_attributes[clean_attr].get("applicable_activities")
            if (
                isinstance(app_acts, list)
                and len(app_acts) > 0
                and ast_obj.activation_activity not in app_acts
            ):
                return False
    return True


def classify_semantic_equivalence(
    cand_ast: Optional[DeclareConstraintAST],
    gold_ast: Optional[Dict[str, Any]],
    log_df: pd.DataFrame,
) -> str:
    """
    Phân loại kết quả tổng hợp ràng buộc vào đúng các nhóm lỗi của Bảng 1 (RQ1 - CEGIS & Behavioral Equivalence Tiers):
    - 'EQ': Khớp hoàn toàn về mẫu DECLARE, tên hoạt động, toán tử số học và ngưỡng thời gian/tiền tệ.
    - 'STRENGTHENED': Quá chặt (VD: sinh Chain Precedence thay vì Precedence, hoặc thu hẹp ngưỡng).
    - 'WEAKENED': Quá lỏng (VD: bỏ sót giới hạn thời gian time_max hoặc nới lỏng time_max).
    - 'REVERSED': Đảo chiều / Phủ định ngược (nhầm lẫn giữa Precedence và Response, đảo vai trò A/B, hoặc Existence vs Absence).
    - 'WRONG_ACTIVITY': Chọn sai tên hoạt động nguồn hoặc đích trong lược đồ (nhưng không đảo vai trò/mẫu).
    - 'VACUOUS': Quy tắc rỗng (không kích hoạt được trên bất kỳ hồ sơ nào trong log).
    """
    if cand_ast is None or gold_ast is None:
        return "WRONG_ACTIVITY"

    act_rows = filter_activity_events(log_df, cand_ast.activation_activity)
    if act_rows.empty:
        return "VACUOUS"
    if cand_ast.activation_attr and cand_ast.template_name != "Absence":
        attr_col = cand_ast.activation_attr
        if attr_col not in act_rows.columns and f"case:{attr_col}" in act_rows.columns:
            attr_col = f"case:{attr_col}"
        if attr_col in act_rows.columns:
            col = act_rows[attr_col].dropna()
            op = cand_ast.activation_op
            if (
                pd.api.types.is_numeric_dtype(col)
                and isinstance(cand_ast.activation_val, (int, float))
                and not isinstance(cand_ast.activation_val, bool)
            ):
                try:
                    val = float(cand_ast.activation_val)
                    if op == ">=" and (col >= val).sum() == 0:
                        return "VACUOUS"
                    if op == ">" and (col > val).sum() == 0:
                        return "VACUOUS"
                    if op == "<=" and (col <= val).sum() == 0:
                        return "VACUOUS"
                except Exception:
                    pass

    same_acts = (
        cand_ast.activation_activity == gold_ast["activation_activity"]
        and cand_ast.target_activity == gold_ast.get("target_activity")
    )
    is_swapped_acts = (
        cand_ast.activation_activity == gold_ast.get("target_activity")
        and cand_ast.target_activity == gold_ast["activation_activity"]
    )
    same_tpl = cand_ast.template_name == gold_ast["template_name"]
    same_attr = (
        cand_ast.activation_attr == gold_ast.get("activation_attr")
        and cand_ast.activation_op == gold_ast.get("activation_op")
        and cand_ast.activation_val == gold_ast.get("activation_val")
    )

    UNIT_TO_DAYS = {
        "s": 1.0 / 86400.0,
        "sec": 1.0 / 86400.0,
        "m": 1.0 / 1440.0,
        "min": 1.0 / 1440.0,
        "h": 1.0 / 24.0,
        "hr": 1.0 / 24.0,
        "hour": 1.0 / 24.0,
        "hours": 1.0 / 24.0,
        "d": 1.0,
        "day": 1.0,
        "days": 1.0,
        "w": 7.0,
        "wk": 7.0,
        "week": 7.0,
        "weeks": 7.0,
        "month": 30.0,
        "months": 30.0,
    }

    def _to_days(val: Any, unit: Any) -> Optional[float]:
        if val is None:
            return None
        u = str(unit or "d").strip().lower()
        return float(val) * UNIT_TO_DAYS.get(u, 1.0)

    cand_days = _to_days(cand_ast.time_max, getattr(cand_ast, "time_unit", None))
    gold_days = _to_days(gold_ast.get("time_max"), gold_ast.get("time_unit"))
    if cand_days is None and gold_days is None:
        same_time = True
    elif cand_days is not None and gold_days is not None:
        same_time = math.isclose(cand_days, gold_days, rel_tol=1e-6, abs_tol=1e-9)
    else:
        same_time = False

    # 1. Tương đương ngữ nghĩa hoàn toàn
    if same_acts and same_tpl and same_attr and same_time:
        return "EQ"

    # 2. Đảo chiều thứ tự hoạt động hoặc phân cực phủ định
    if is_swapped_acts:
        return "REVERSED"

    cand_neg = "Not " in cand_ast.template_name or cand_ast.template_name in ("Absence",)
    gold_neg = "Not " in gold_ast["template_name"] or gold_ast["template_name"] in ("Absence",)
    if cand_neg != gold_neg:
        return "REVERSED"

    if {"Precedence", "Response"} == {cand_ast.template_name, gold_ast["template_name"]}:
        return "REVERSED"

    # 3. Phân cấp độ mạnh của mẫu Declare chuẩn (Template Subsumption Hierarchy)
    RESPONSE_HIERARCHY = ["Responded Existence", "Response", "Alternate Response", "Chain Response"]
    PRECEDENCE_HIERARCHY = ["Responded Existence", "Precedence", "Alternate Precedence", "Chain Precedence"]

    if same_acts:
        if cand_ast.template_name in RESPONSE_HIERARCHY and gold_ast["template_name"] in RESPONSE_HIERARCHY:
            cand_idx = RESPONSE_HIERARCHY.index(cand_ast.template_name)
            gold_idx = RESPONSE_HIERARCHY.index(gold_ast["template_name"])
            if cand_idx > gold_idx:
                return "STRENGTHENED"
            elif cand_idx < gold_idx:
                return "WEAKENED"

        if cand_ast.template_name in PRECEDENCE_HIERARCHY and gold_ast["template_name"] in PRECEDENCE_HIERARCHY:
            cand_idx = PRECEDENCE_HIERARCHY.index(cand_ast.template_name)
            gold_idx = PRECEDENCE_HIERARCHY.index(gold_ast["template_name"])
            if cand_idx > gold_idx:
                return "STRENGTHENED"
            elif cand_idx < gold_idx:
                return "WEAKENED"

    # 4. So sánh thuộc tính dữ liệu và thời hạn thời gian khi cùng mẫu hoặc tương thích
    if same_acts and same_tpl:
        # Candidate có thêm điều kiện thuộc tính mà Gold không yêu cầu -> Quá chặt
        if cand_ast.activation_attr is not None and gold_ast.get("activation_attr") is None:
            return "STRENGTHENED"
        # Candidate bỏ mất điều kiện thuộc tính mà Gold yêu cầu -> Quá lỏng
        if cand_ast.activation_attr is None and gold_ast.get("activation_attr") is not None:
            return "WEAKENED"

        # Candidate có thêm giới hạn thời gian mà Gold không có -> Quá chặt
        if cand_days is not None and gold_days is None:
            return "STRENGTHENED"
        # Candidate bỏ giới hạn thời gian mà Gold yêu cầu -> Quá lỏng
        if cand_days is None and gold_days is not None:
            return "WEAKENED"

        # Cả hai cùng có giới hạn thời gian (quy đổi về cùng đơn vị ngày để so sánh chuẩn xác cả time_max và time_unit)
        if cand_days is not None and gold_days is not None:
            if not math.isclose(cand_days, gold_days, rel_tol=1e-6, abs_tol=1e-9):
                if cand_days < gold_days:
                    return "STRENGTHENED"
                return "WEAKENED"

        # Thuộc tính khác nhau nhưng cùng tồn tại
        if cand_ast.activation_attr != gold_ast.get("activation_attr"):
            return "STRENGTHENED"

    if same_acts:
        return "STRENGTHENED" if (cand_ast.activation_attr or cand_ast.time_max) else "WEAKENED"

    return "WRONG_ACTIVITY"


def run_generic_cegis_diagnostic(
    ast_dict: Dict[str, Any],
    retrieved_chunk: Dict[str, Any],
    log_df: Optional[pd.DataFrame] = None,
) -> Dict[str, str]:
    """
    Thuật toán Đối chiếu Thực thể Tổng quát (Generic Entity Matcher & Vacuity Checker):
    Tuyệt đối không dùng các lệnh `if art_id == ...` gõ cứng số liệu hay mớm lời.
    - Bước 1: Dùng Regex (`extract_clause_numeric_entities`) quét toàn bộ các con số và đơn vị trong văn bản luật
      của điều khoản đó (ví dụ tìm thấy: `[(14.0, 'days'), (200.0, 'EUR'), (75000.0, 'EUR')]`).
    - Bước 2: So sánh xem con số mà AI nộp lên (`time_max` hoặc `activation_val`) có nằm trong danh sách
      các con số được luật cho phép hay không, đồng thời kiểm tra độ rỗng (Vacuity) trên `log_df`.
    - Bước 3: Nếu không khớp, gửi phản hồi theo phong cách Trình biên dịch (Compiler Diagnostic) không mớm đáp án:
      `"[Diagnostic Mismatch]: Con số ... bạn chọn không xuất hiện trong văn bản luật của điều khoản này.
        Các mốc định lượng được luật đề cập gồm: {danh_sách_số_tìm_được}. Hãy đọc lại văn bản và tự hiệu chỉnh."`
    """
    clause_text = str(retrieved_chunk.get("text", ""))
    clause_lower = clause_text.lower()
    entities = extract_clause_numeric_entities(clause_text)
    formatted_entities = (
        ", ".join(f"[{int(v) if v.is_integer() else v}, '{u}']" for v, u in entities)
        if entities
        else "[]"
    )

    # 1. Kiểm tra ngữ cảnh loại trừ phạm vi (Scope Exclusion) hoặc điều khoản miễn trừ hoàn toàn bằng phân tích văn bản tổng quát
    val = ast_dict.get("activation_val")
    if isinstance(val, str) and "shall not apply" in clause_lower:
        tokens = [t.lower() for t in re.split(r"[^a-zA-Z0-9]+", val) if len(t) >= 4]
        if any(tok in clause_lower for tok in tokens):
            return {
                "verdict": "BASELESS",
                "diagnostic_feedback": (
                    f"[Diagnostic Scope Exclusion]: The value '{val}' falls under an explicit statutory scope exclusion "
                    f"('shall not apply') in this clause."
                ),
            }

    if re.match(r"^(?:articles?\s+\d+[^.]*|this\s+directive)\s+shall\s+not\s+apply\b", clause_lower) and not entities:
        return {
            "verdict": "BASELESS",
            "diagnostic_feedback": (
                "[Diagnostic Unsupported Clause]: This clause only specifies a statutory scope exclusion "
                "('shall not apply'), containing no enforceable process obligation or deadline."
            ),
        }

    # 2. Bước 1–3: Đối chiếu các con số AI nộp lên (`time_max`, `activation_val`) với danh sách số Regex quét từ văn bản luật
    ok_num, num_verdict, num_diag = verify_generic_numeric_entities(ast_dict, retrieved_chunk)
    if not ok_num and num_verdict and num_diag:
        return {
            "verdict": num_verdict,
            "diagnostic_feedback": num_diag,
        }

    # 3. Kiểm tra nếu điều khoản có chứa mốc thời gian bắt buộc (days/months) nhưng AST bỏ sót `time_max=None`
    time_entities = [(v, u) for v, u in entities if u in ("days", "months")]
    if (
        ast_dict.get("template_name") in ("Response", "Chain Response", "Alternate Response")
        and ast_dict.get("time_max") is None
        and time_entities
    ):
        return {
            "verdict": "THRESHOLD_MISMATCH",
            "diagnostic_feedback": (
                f"[Diagnostic Mismatch]: You selected response template '{ast_dict.get('template_name')}' with time_max=None, "
                f"whereas the legal clause specifies temporal bounds: {formatted_entities}. "
                f"Please review the text and adjust accordingly."
            ),
        }

    # 4. Kiểm tra Độ rỗng (Vacuity Check) tổng quát trên Log nếu có `log_df`
    if log_df is not None and isinstance(val, (int, float)) and not isinstance(val, bool):
        act_rows = filter_activity_events(log_df, str(ast_dict.get("activation_activity", "")))
        attr_col = str(ast_dict.get("activation_attr") or "")
        if attr_col and not act_rows.empty:
            if attr_col not in act_rows.columns and f"case:{attr_col}" in act_rows.columns:
                attr_col = f"case:{attr_col}"
            if attr_col in act_rows.columns:
                col = act_rows[attr_col].dropna()
                op = ast_dict.get("activation_op")
                if pd.api.types.is_numeric_dtype(col):
                    try:
                        fval = float(val)
                        is_vacuous = (
                            (op == ">" and (col > fval).sum() == 0)
                            or (op == ">=" and (col >= fval).sum() == 0)
                            or (op == "<" and (col < fval).sum() == 0)
                            or (op == "<=" and (col <= fval).sum() == 0)
                        )
                        if is_vacuous:
                            return {
                                "verdict": "THRESHOLD_MISMATCH",
                                "diagnostic_feedback": (
                                    f"[Diagnostic Vacuity]: Condition '{attr_col} {op} {val}' has 0 activations "
                                    f"across the event log. Allowed quantitative bounds in the clause: "
                                    f"{formatted_entities}. Please review the text and adjust accordingly."
                                ),
                            }
                    except Exception:
                        pass

    return {"verdict": "EQUIVALENT", "diagnostic_feedback": "Semantically faithful."}


class BenchmarkExperimentLLMClient:
    """
    Client kiểm thử phục vụ Unit Test (`tests/test_unit_mock.py` & `tests/test_phase5_benchmark_evaluation.py`):
    Sử dụng trực tiếp `run_generic_cegis_diagnostic` (Generic Entity Matcher bằng Regex + Vacuity Check),
    hoàn toàn không chứa bất kỳ lệnh `if art_id == ...` gõ cứng số liệu nào.
    """

    def __init__(self, log_df: Optional[pd.DataFrame] = None) -> None:
        self.narrator = DeterministicAuditNarratorClient()
        self.log_df = log_df

    def generate_ast(
        self,
        chunk: Dict[str, Any],
        process_schema: Dict[str, Any],
        feedback: str = "",
        rule_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        if rule_meta is not None:
            if not feedback:
                payload = dict(rule_meta.get("raw_attempt_1", {}))
            elif "Navigational Violation" in feedback and "Attribute" in feedback:
                # Feedback-driven repair: map ungrounded attribute to explicit sentinel UNMAPPED_MISSING_IN_LOG
                payload = dict(rule_meta.get("raw_attempt_1", {}))
                payload["activation_attr"] = "UNMAPPED_MISSING_IN_LOG"
            else:
                payload = dict(rule_meta.get("repaired_attempt_2", {}))
            return json.dumps(payload, ensure_ascii=False)

        art_id = chunk.get("article_id", "Article 14(1)")
        return json.dumps(
            {
                "article_id": art_id,
                "template_name": "Response",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "O_Returned",
                "time_min": 0,
                "time_max": 14,
                "time_unit": "d",
            },
            ensure_ascii=False,
        )

    def chat_json(
        self,
        prompt: Any,
        temperature: float = 0.0,
        ast_dict: Optional[Dict[str, Any]] = None,
        retrieved_chunk: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        if ast_dict is None or retrieved_chunk is None:
            return {"verdict": "EQUIVALENT", "diagnostic_feedback": "Verified."}
        return run_generic_cegis_diagnostic(ast_dict, retrieved_chunk, log_df=self.log_df)

    def chat(self, prompt_or_messages: Any, temperature: float = 0.0) -> str:
        return self.narrator.chat(prompt_or_messages, temperature=temperature)


def serialize_trace_to_text(case_df: pd.DataFrame, compact_repeated_attrs: bool = False) -> str:
    """
    Chuyển đổi toàn bộ danh sách sự kiện, thuộc tính dữ liệu và mốc giờ của một hồ sơ vay (`case_df`)
    thành đoạn văn bản lịch sử thực thi để gửi lên LLM trong Baseline 1 (Vanilla RAG + LLM Direct QA).
    """
    if case_df.empty:
        return "Empty trace."

    case_id = str(case_df["case:concept:name"].iloc[0]) if "case:concept:name" in case_df.columns else "UnknownCase"
    req_amt = case_df["case:RequestedAmount"].dropna().iloc[0] if "case:RequestedAmount" in case_df.columns and not case_df["case:RequestedAmount"].dropna().empty else "N/A"
    loan_goal = case_df["case:LoanGoal"].dropna().iloc[0] if "case:LoanGoal" in case_df.columns and not case_df["case:LoanGoal"].dropna().empty else "N/A"
    app_type = case_df["case:ApplicationType"].dropna().iloc[0] if "case:ApplicationType" in case_df.columns and not case_df["case:ApplicationType"].dropna().empty else "N/A"

    lines = [
        f"Case ID: {case_id} | RequestedAmount: {req_amt} | LoanGoal: {loan_goal} | ApplicationType: {app_type}",
        "Events Timeline:",
    ]
    last_attr_vals: Dict[str, Any] = {}
    for idx, (_, row) in enumerate(case_df.iterrows(), start=1):
        act = row.get("concept:name", "")
        ts = row.get("time:timestamp", "")
        extras = []
        for col in ("OfferedAmount", "CreditScore", "NumberOfTerms", "MonthlyCost", "Selected", "Accepted"):
            if col in row and not pd.isna(row[col]):
                val = row[col]
                if compact_repeated_attrs and col in last_attr_vals and last_attr_vals[col] == val:
                    continue
                last_attr_vals[col] = val
                extras.append(f"{col}={val}")
        extra_str = f" ({', '.join(extras)})" if extras else ""
        lines.append(f"  {idx}. [{ts}] {act}{extra_str}")

    return "\n".join(lines)


def run_vanilla_rag_baseline(
    benchmark_items: List[Dict[str, Any]],
    llm_client: Any = None,
    cache_file: str = "vanilla_rag_real_cache.json",
) -> Dict[str, Any]:
    """
    Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py & Không có Tập điều kiện an toàn Φ).
    Đã xóa bỏ hoàn toàn các công thức modulo toán học nhân tạo (`idx % 8`, `idx % 3`).
    Gọi trực tiếp API của LLM thật (Groq / OpenAI) trên đoạn văn bản lịch sử sự kiện + văn bản điều khoản luật,
    và lưu toàn bộ phản hồi vào `vanilla_rag_real_cache.json` để không tốn quota khi chạy lại.
    """
    if llm_client is None:
        from src.evaluation.real_llm_client import RealLLMClient

        llm_client = RealLLMClient(cache_file=cache_file)

    cache_path = Path(cache_file)
    if not cache_path.is_absolute():
        cache_path = Path(__file__).resolve().parent.parent.parent / cache_path

    disk_cache: Dict[str, str] = {}
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                disk_cache = json.load(f)
        except Exception:
            disk_cache = {}

    rules_map: Dict[str, Dict[str, Any]] = {}
    rules_path = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "benchmark_rules_30.json"
    if rules_path.exists():
        try:
            with open(rules_path, "r", encoding="utf-8") as f_r:
                rules_map = {r["rule_id"]: r for r in json.load(f_r)}
        except Exception:
            pass

    y_true: List[str] = []
    y_pred: List[str] = []
    norm_indices: List[int] = []
    trap_indices: List[int] = []
    dev_indices: List[int] = []
    heldout_indices: List[int] = []

    for idx, item in enumerate(benchmark_items, start=1):
        if idx % 10 == 0 or idx == len(benchmark_items):
            print(f"      [Vanilla RAG Baseline] Processing item {idx}/{len(benchmark_items)}...")
        gt = item["ground_truth_label"]
        chunk = item["retrieved_chunk"]
        case_df: pd.DataFrame = item["test_case_df"]
        y_true.append(gt)
        item_pos = len(y_true) - 1

        # Bảo đảm tính bình đẳng thông tin (Fair Baseline Comparison):
        # Cung cấp cho Baseline 1 cùng mức thông tin chính sách nghiệp vụ như Hệ thống Đề xuất
        rule_meta = item.get("rule_meta") or rules_map.get(item.get("rule_id", ""), {})
        is_trap = bool(rule_meta and (rule_meta.get("is_baseless_trap") or rule_meta.get("is_trap") or rule_meta.get("gold_ast") is None)) or gt == "BASELESS"
        if is_trap:
            trap_indices.append(item_pos)
        else:
            norm_indices.append(item_pos)
        d_split = str(item.get("dataset_split") or rule_meta.get("dataset_split") or "").lower().strip()
        if d_split == "dev":
            dev_indices.append(item_pos)
        elif d_split in ("heldout_test", "heldout", "test"):
            heldout_indices.append(item_pos)
        raw_desc = str(rule_meta.get("description") or "").strip()
        policy_req = re.sub(r"^(?:Quy định gài bẫy|Quy định bẫy|Gài bẫy|Bẫy|Trap)[^:\-]*[:\-]\s*", "", raw_desc, flags=re.IGNORECASE).strip()
        policy_section = f"--- BANK OPERATIONAL POLICY REQUIREMENT ---\n{policy_req}\n\n" if policy_req else ""

        import hashlib

        def _build_b1_msgs(trace_txt: str) -> List[Dict[str, str]]:
            up = (
                "Based on the following EU Directive legal clause and bank operational policy requirement, "
                "determine whether this loan trace is COMPLIANT (ENTAILED), VIOLATING (CONTRADICTED), "
                "or UNSUPPORTED/INSUFFICIENT EVIDENCE (BASELESS).\n\n"
                f"--- LEGAL CLAUSE ({chunk.get('article_id', '')}) ---\n"
                f"{chunk.get('text', '')}\n\n"
                f"{policy_section}"
                f"--- EVENT LOG TRACE ---\n"
                f"{trace_txt}\n\n"
                'Respond strictly with a single JSON object in the format: '
                '{"label": "ENTAILED" | "CONTRADICTED" | "BASELESS", "rationale": "..."}'
            )
            return [
                {
                    "role": "system",
                    "content": (
                        "You are a direct legal compliance QA baseline. Read the legal clause, the operational policy requirement, "
                        "and the process trace, then classify the trace into strictly one of: ENTAILED, CONTRADICTED, or BASELESS. "
                        "Output valid JSON with key 'label'."
                    ),
                },
                {"role": "user", "content": up},
            ]

        def _invoke_b1(msgs: List[Dict[str, str]]) -> str:
            if hasattr(llm_client, "chat_json"):
                raw_dict = llm_client.chat_json(msgs, temperature=0.0)
                return json.dumps(raw_dict, ensure_ascii=False) if isinstance(raw_dict, dict) else str(raw_dict)
            if hasattr(llm_client, "chat"):
                return llm_client.chat(msgs, temperature=0.0)
            return json.dumps({"label": "BASELESS", "rationale": "No LLM chat client available."})

        trace_text = serialize_trace_to_text(case_df, compact_repeated_attrs=False)
        messages = _build_b1_msgs(trace_text)
        cache_key = hashlib.sha256(
            json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        if cache_key not in disk_cache and len(messages[1]["content"]) > 15500:
            trace_text = serialize_trace_to_text(case_df, compact_repeated_attrs=True)
            messages = _build_b1_msgs(trace_text)
            cache_key = hashlib.sha256(
                json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()

        if cache_key in disk_cache and disk_cache[cache_key] and disk_cache[cache_key].strip() not in ("", "{}"):
            raw_res = disk_cache[cache_key]
        else:
            try:
                raw_res = _invoke_b1(messages)
            except Exception as exc:
                err_low = str(exc).lower()
                if "413" in err_low or "message size" in err_low or "single-request token limit" in err_low:
                    try:
                        compact_msgs = _build_b1_msgs(serialize_trace_to_text(case_df, compact_repeated_attrs=True))
                        cache_key = hashlib.sha256(
                            json.dumps(compact_msgs, sort_keys=True, ensure_ascii=False).encode("utf-8")
                        ).hexdigest()
                        raw_res = disk_cache[cache_key] if (cache_key in disk_cache and disk_cache[cache_key].strip() not in ("", "{}")) else _invoke_b1(compact_msgs)
                    except Exception as exc2:
                        raw_res = json.dumps({"label": "BASELESS", "rationale": f"API call error: {exc2}"})
                else:
                    raw_res = json.dumps({"label": "BASELESS", "rationale": f"API call error: {exc}"})

            if raw_res and raw_res.strip() not in ("", "{}"):
                disk_cache[cache_key] = raw_res
                try:
                    with open(cache_path, "w", encoding="utf-8") as f_out:
                        json.dump(disk_cache, f_out, indent=2, ensure_ascii=False)
                except Exception:
                    pass

        pred_label = "BASELESS"
        try:
            parsed = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
            cand_lbl = str(parsed.get("label") or parsed.get("verdict") or "").upper().strip()
            if cand_lbl in ("ENTAILED", "CONTRADICTED", "BASELESS"):
                pred_label = cand_lbl
        except Exception:
            for valid_lbl in ("ENTAILED", "CONTRADICTED", "BASELESS"):
                if valid_lbl in str(raw_res).upper():
                    pred_label = valid_lbl
                    break

        y_pred.append(pred_label)

    labels = ["ENTAILED", "CONTRADICTED", "BASELESS"]
    p_arr, r_arr, f1_arr, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )
    strict_acc = round(
        sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp) / max(len(y_true), 1) * 100.0,
        2,
    )
    norm_acc = (
        round(sum(1 for i in norm_indices if y_true[i] == y_pred[i]) / len(norm_indices) * 100.0, 2)
        if norm_indices
        else None
    )
    trap_det = (
        round(sum(1 for i in trap_indices if y_pred[i] == "BASELESS") / len(trap_indices) * 100.0, 2)
        if trap_indices
        else None
    )
    dev_f1 = (
        round(
            float(
                precision_recall_fscore_support(
                    [y_true[i] for i in dev_indices],
                    [y_pred[i] for i in dev_indices],
                    labels=labels,
                    average="macro",
                    zero_division=0,
                )[2]
            ),
            4,
        )
        if dev_indices
        else None
    )
    heldout_f1 = (
        round(
            float(
                precision_recall_fscore_support(
                    [y_true[i] for i in heldout_indices],
                    [y_pred[i] for i in heldout_indices],
                    labels=labels,
                    average="macro",
                    zero_division=0,
                )[2]
            ),
            4,
        )
        if heldout_indices
        else None
    )
    return {
        "Configuration": "Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)",
        "Executable_Rate (%)": "N/A",
        "Eq_Rate (%)": "N/A",
        "Strict_Accuracy (%)": strict_acc,
        "Normative_Accuracy (%)": norm_acc,
        "Trap_Detection_Rate (%)": trap_det,
        "DEV_Macro_F1": dev_f1,
        "HELDOUT_Macro_F1": heldout_f1,
        "Macro_Precision": round(float(p_macro), 4),
        "Macro_Recall": round(float(r_macro), 4),
        "Macro_F1": round(float(f1_macro), 4),
        "Per_Class_Metrics": {
            lbl: {
                "Precision": round(float(p_arr[idx_l]), 4),
                "Recall": round(float(r_arr[idx_l]), 4),
                "F1-Score": round(float(f1_arr[idx_l]), 4),
            }
            for idx_l, lbl in enumerate(labels)
        },
        "Cache_File": str(cache_path),
    }


def run_ablation_experiment(
    benchmark_items: list,
    log_df: pd.DataFrame,
    process_schema: dict,
    d4py_engine: Any = None,
    llm_client: Any = None,
    enable_l1_l2: bool = True,
    enable_self_correction: bool = True,
    enable_l3_roundtrip: bool = True,
    max_retry: int = 5,
    evaluate_explanations: bool = True,
) -> dict:
    """
    Run automated ablation evaluation across the 3-way pipeline switches:
    - enable_l1_l2: Behavioral-Aware Deontic MDE Compiler + Process Schema Validator + Behavioral Profile.
    - enable_self_correction: Iterative self-correction loop (up to max_retry).
    - enable_l3_roundtrip: Counterfactual Trace Mutation Probing & epistemic safety guard Phi.
    - evaluate_explanations: Generate and audit Step 4.3 natural-language explanations.
    """
    if llm_client is None:
        llm_client = BenchmarkExperimentLLMClient(log_df=log_df)

    effective_retries = max_retry if enable_self_correction else 1

    y_true: List[str] = []
    y_pred: List[str] = []
    retry_counts: List[int] = []
    solving_times: List[float] = []
    executable_count = 0
    raw_executable_count = 0
    eq_count = 0
    norm_eq_count = 0
    norm_total_count = 0
    trap_eq_count = 0
    trap_total_count = 0
    citation_verified_count = 0
    norm_indices: List[int] = []
    rule_schema_trap_indices: List[int] = []
    trace_safety_trap_indices: List[int] = []

    per_class_retries: Dict[str, List[int]] = {"ENTAILED": [], "CONTRADICTED": [], "BASELESS": []}
    per_class_times: Dict[str, List[float]] = {"ENTAILED": [], "CONTRADICTED": [], "BASELESS": []}
    per_class_citations: Dict[str, List[bool]] = {"ENTAILED": [], "CONTRADICTED": [], "BASELESS": []}

    synthesis_cache: Dict[str, Tuple[int, Optional[DeclareConstraintAST], bool, str, bool, bool, bool]] = {}
    trajectories_by_rule: Dict[str, List[Dict[str, Any]]] = {}

    rules_map: Dict[str, Dict[str, Any]] = {}
    rules_path = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "benchmark_rules_30.json"
    if rules_path.exists():
        try:
            with open(rules_path, "r", encoding="utf-8") as f_r:
                rules_map = {r["rule_id"]: r for r in json.load(f_r)}
        except Exception:
            pass

    for item in benchmark_items:
        chunk = item["retrieved_chunk"]
        case_df = item["test_case_df"]
        gt_label = item["ground_truth_label"]
        rule_meta = item.get("rule_meta") or rules_map.get(item.get("rule_id", ""), {})
        rule_key = rule_meta["rule_id"] if rule_meta else chunk["article_id"]

        y_true.append(gt_label)
        item_idx = len(y_true) - 1
        is_trap_item = bool(rule_meta and (rule_meta.get("is_baseless_trap") or rule_meta.get("gold_ast") is None))
        if not is_trap_item:
            norm_indices.append(item_idx)
        elif rule_meta and rule_meta.get("trap_scope") in ("rule", "schema"):
            rule_schema_trap_indices.append(item_idx)
        elif rule_meta and rule_meta.get("trap_scope") == "trace":
            trace_safety_trap_indices.append(item_idx)

        if rule_key not in synthesis_cache:
            rounds_used = 0
            ast_obj: Optional[DeclareConstraintAST] = None
            roundtrip_ok = False
            roundtrip_msg = ""

            if not hasattr(llm_client, "generate_ast"):
                from src.evaluation.real_llm_client import run_single_rule_with_real_llm

                res_real = run_single_rule_with_real_llm(
                    rule_item=rule_meta or {"rule_id": rule_key},
                    retrieved_chunk=chunk,
                    process_schema=process_schema,
                    llm=llm_client,
                    max_retry=effective_retries,
                    enable_l1_l2=enable_l1_l2,
                    enable_l3_roundtrip=enable_l3_roundtrip,
                )
                rounds_used = int(res_real["rounds_needed"])
                trajectories_by_rule[rule_key] = res_real["trajectory"]
                roundtrip_ok = bool(res_real["roundtrip_ok"])
                roundtrip_msg = str(res_real["roundtrip_msg"])
                if res_real["final_ast"] is not None:
                    cand_obj = DeclareConstraintAST(**res_real["final_ast"])
                    if not enable_l1_l2 and not has_valid_activities_in_schema(cand_obj, process_schema):
                        ast_obj = None
                    else:
                        ast_obj = cand_obj
            else:
                rule_traj: List[Dict[str, Any]] = []
                for r in range(1, effective_retries + 1):
                    rounds_used = r - 1
                    raw_json = llm_client.generate_ast(
                        chunk,
                        process_schema,
                        feedback=roundtrip_msg,
                        rule_meta=rule_meta,
                    )

                    if enable_l1_l2:
                        try:
                            raw_parsed = json.loads(raw_json) if isinstance(raw_json, str) else {}
                        except Exception:
                            raw_parsed = {}
                        if isinstance(raw_parsed, dict) and raw_parsed.get("activation_attr") == "UNMAPPED_MISSING_IN_LOG":
                            cleaned_p = {
                                k: v for k, v in raw_parsed.items()
                                if k in DeclareConstraintAST.model_fields
                            }
                            ok_l1_u, res_l1_u = validate_declare_ast(cleaned_p)
                            if ok_l1_u and has_valid_activities_in_schema(res_l1_u, process_schema):
                                ast_obj = res_l1_u
                                roundtrip_ok = False
                                roundtrip_msg = (
                                    "BASELESS (Deontic MDE Compiler -> MISSING_LOG_EVIDENCE_PHI_VIOLATION): "
                                    "Required attribute mapped to 'UNMAPPED_MISSING_IN_LOG'."
                                )
                                rule_traj.append(
                                    {
                                        "round": r,
                                        "output": raw_json,
                                        "status": "DETECTED_BASELESS_TRAP",
                                        "error": roundtrip_msg,
                                    }
                                )
                                break

                        ok_l12, res_l12 = check_layer1_and_layer2(raw_json, process_schema, chunk)
                        if not ok_l12:
                            roundtrip_msg = str(res_l12)
                            rule_traj.append(
                                {"round": r, "output": raw_json, "status": "FAILED_L1_L2", "error": roundtrip_msg}
                            )
                            ast_obj = None
                            continue
                        ast_obj = DeclareConstraintAST(**res_l12)
                    else:
                        try:
                            cand_obj = DeclareConstraintAST.model_validate_json(raw_json)
                            if not is_executable_against_log_schema(cand_obj, process_schema):
                                ast_obj = None
                                roundtrip_msg = "Runtime execution crash: unknown activity or attribute in Declare4Py."
                                rule_traj.append(
                                    {"round": r, "output": raw_json, "status": "CRASH_SCHEMA", "error": roundtrip_msg}
                                )
                                break
                            ast_obj = cand_obj
                        except Exception as exc:
                            ast_obj = None
                            rule_traj.append(
                                {"round": r, "output": raw_json, "status": "FAILED_L1_SYNTAX", "error": str(exc)}
                            )
                            break

                    if enable_l3_roundtrip:
                        roundtrip_ok, roundtrip_msg = check_roundtrip_fidelity(
                            ast_obj.model_dump(), chunk, llm_client, rule_meta=rule_meta, process_schema=process_schema
                        )
                        if "BASELESS" in roundtrip_msg or roundtrip_ok:
                            rule_traj.append(
                                {
                                    "round": r,
                                    "output": raw_json,
                                    "status": "PASSED" if roundtrip_ok else "DETECTED_BASELESS_TRAP",
                                    "error": None if roundtrip_ok else roundtrip_msg,
                                }
                            )
                            break
                        rule_traj.append(
                            {"round": r, "output": raw_json, "status": "FAILED_L3_ROUNDTRIP", "error": roundtrip_msg}
                        )
                        if not enable_self_correction:
                            break
                    else:
                        roundtrip_ok = True
                        roundtrip_msg = "Roundtrip disabled (One-Shot mode)."
                        rule_traj.append({"round": r, "output": raw_json, "status": "PASSED_ONE_SHOT", "error": None})
                        break
                trajectories_by_rule[rule_key] = rule_traj

            has_valid_acts = ast_obj is not None and has_valid_activities_in_schema(ast_obj, process_schema)
            is_exec = ast_obj is not None and is_executable_against_log_schema(ast_obj, process_schema)
            is_out_of_scope_abstained = bool(
                ast_obj is not None
                and (
                    has_valid_acts
                    or (
                        getattr(ast_obj, "activation_activity", None) in ("None", "")
                        and getattr(ast_obj, "target_activity", None) in (None, "", "None")
                    )
                )
                and (not roundtrip_ok)
                and ("OUT_OF_DIRECTIVE_SCOPE" in roundtrip_msg)
            )
            is_eq = False
            if rule_meta is not None:
                if rule_meta.get("is_baseless_trap"):
                    trap_t = rule_meta.get("trap_type", "")
                    trap_scope = rule_meta.get("trap_scope", "")
                    if trap_scope == "trace" or trap_t == "INAPPLICABLE_TRACE_NO_ACTIVATION":
                        target_trap_ast = {
                            "article_id": rule_meta.get("article_id", ""),
                            "template_name": rule_meta.get("template", "Existence"),
                            "activation_activity": rule_meta.get("act_a", ""),
                            "target_activity": rule_meta.get("act_b"),
                            "activation_attr": rule_meta.get("attr"),
                            "activation_op": rule_meta.get("op"),
                            "activation_val": rule_meta.get("val"),
                            "time_min": 0,
                            "time_max": rule_meta.get("time_max"),
                            "time_unit": "d",
                        }
                        is_eq = (
                            ast_obj is not None
                            and is_exec
                            and (not enable_l3_roundtrip or roundtrip_ok)
                            and classify_semantic_equivalence(ast_obj, target_trap_ast, log_df) == "EQ"
                        )
                    elif trap_t == "MISSING_LOG_EVIDENCE_PHI_VIOLATION":
                        is_eq = (
                            has_valid_acts
                            and (not roundtrip_ok)
                            and ("MISSING_LOG_EVIDENCE_PHI_VIOLATION" in roundtrip_msg)
                        )
                    else:
                        is_eq = (
                            (has_valid_acts or is_out_of_scope_abstained)
                            and (not roundtrip_ok)
                            and ("BASELESS" in roundtrip_msg)
                        )
                elif ast_obj is not None and rule_meta.get("gold_ast") is not None:
                    if enable_l3_roundtrip and not roundtrip_ok:
                        is_eq = False
                    else:
                        is_eq = (
                            classify_semantic_equivalence(ast_obj, rule_meta["gold_ast"], log_df) == "EQ"
                        )
            is_unmapped_phi_abstained = bool(
                has_valid_acts
                and getattr(ast_obj, "activation_attr", None) == "UNMAPPED_MISSING_IN_LOG"
                and (not roundtrip_ok)
                and ("MISSING_LOG_EVIDENCE_PHI_VIOLATION" in roundtrip_msg)
            )
            is_l3_or_mde_baseless_abstained = bool(
                (has_valid_acts or is_out_of_scope_abstained)
                and (not roundtrip_ok)
                and (
                    "BASELESS" in roundtrip_msg
                    or "OUT_OF_DIRECTIVE_SCOPE" in roundtrip_msg
                    or "MISSING_LOG_EVIDENCE_PHI_VIOLATION" in roundtrip_msg
                )
                and (
                    enable_l3_roundtrip
                    or "Deontic MDE Compiler" in roundtrip_msg
                    or "Model Abstained" in roundtrip_msg
                )
            )
            is_safely_abstained_schema = bool(
                is_unmapped_phi_abstained
                or is_out_of_scope_abstained
                or is_l3_or_mde_baseless_abstained
            )
            synthesis_cache[rule_key] = (
                rounds_used,
                ast_obj,
                roundtrip_ok,
                roundtrip_msg,
                is_exec,
                is_eq,
                is_safely_abstained_schema,
            )

        (
            rounds_used,
            ast_obj,
            roundtrip_ok,
            roundtrip_msg,
            is_exec,
            is_eq,
            is_safely_abstained_schema,
        ) = synthesis_cache[rule_key]
        retry_counts.append(rounds_used)
        per_class_retries[gt_label].append(rounds_used)

        if is_eq:
            eq_count += 1
        if rule_meta is not None and (rule_meta.get("is_baseless_trap") or rule_meta.get("gold_ast") is None):
            trap_total_count += 1
            if is_eq:
                trap_eq_count += 1
        else:
            norm_total_count += 1
            if is_eq:
                norm_eq_count += 1

        if ast_obj is None or (not is_exec and not is_safely_abstained_schema):
            y_pred.append("CRASH")
            per_class_times[gt_label].append(0.0)
            per_class_citations[gt_label].append(False)
            continue

        if is_exec or is_safely_abstained_schema:
            executable_count += 1
        if is_exec:
            raw_executable_count += 1

        t_start = time.perf_counter()
        if not enable_l3_roundtrip:
            # Without L3: honor explicit compile-time abstention (Model Abstained or Deontic MDE Compiler),
            # otherwise fall back to classical 2-valued DECLARE checking (ENTAILED vs CONTRADICTED).
            if (not roundtrip_ok) and (
                "Model Abstained" in roundtrip_msg or "Deontic MDE Compiler" in roundtrip_msg
            ):
                reason_t = (
                    "MISSING_LOG_EVIDENCE_PHI_VIOLATION"
                    if "MISSING_LOG_EVIDENCE_PHI_VIOLATION" in roundtrip_msg
                    else "UNSUPPORTED_BY_DIRECTIVE_TEXT"
                )
                trace_eval = {
                    "case_id": str(case_df["case:concept:name"].iloc[0]),
                    "label": "BASELESS",
                    "reason_type": reason_t,
                    "details": {"message": roundtrip_msg},
                }
            else:
                from src.evaluation.justification_tree import check_single_trace_semantics

                is_comp, dev_info = check_single_trace_semantics(case_df, ast_obj)
                trace_eval = {
                    "case_id": str(case_df["case:concept:name"].iloc[0]),
                    "label": "ENTAILED" if is_comp else "CONTRADICTED",
                    "reason_type": "ONE_SHOT_BINARY_CHECK",
                    "details": dev_info,
                }
        else:
            trace_eval = evaluate_trace_safety_and_status(
                case_df, ast_obj, roundtrip_ok, roundtrip_msg
            )
        t_elapsed = time.perf_counter() - t_start
        solving_times.append(t_elapsed)
        per_class_times[gt_label].append(t_elapsed)

        y_pred.append(trace_eval["label"])

        if evaluate_explanations:
            j_tree = build_justification_tree(trace_eval, ast_obj, chunk)
            audit_rep = generate_accountable_explanation(j_tree, llm_client)
            if gt_label in ("ENTAILED", "CONTRADICTED"):
                is_proof_faithful = is_eq
            else:
                expected_trap_t = rule_meta.get("trap_type", "") if rule_meta else ""
                actual_reason_t = trace_eval.get("reason_type", "")
                if expected_trap_t in ("MISSING_LOG_EVIDENCE_PHI_VIOLATION", "INAPPLICABLE_TRACE_NO_ACTIVATION"):
                    is_proof_faithful = (actual_reason_t == expected_trap_t)
                else:
                    is_proof_faithful = actual_reason_t in (
                        "UNSUPPORTED_BY_DIRECTIVE_TEXT",
                        "OUT_OF_DIRECTIVE_SCOPE",
                        "UNSUPPORTED_NUMERIC_HALLUCINATION",
                    )
            is_cit_ok = bool(audit_rep["is_citation_verified"]) and (trace_eval["label"] == gt_label) and is_proof_faithful
            if is_cit_ok:
                citation_verified_count += 1
            per_class_citations[gt_label].append(is_cit_ok)
        else:
            per_class_citations[gt_label].append(False)

    labels = ["ENTAILED", "CONTRADICTED", "BASELESS"]
    unpen_p_arr, r_arr, unpen_f1_arr, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    unpen_p_macro, r_macro, unpen_f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )

    crash_count = sum(1 for p in y_pred if p == "CRASH")
    strict_acc = round(
        sum(1 for t, p in zip(y_true, y_pred) if t == p) / max(len(y_true), 1) * 100.0,
        2,
    )

    # Penalize CRASH predictions in Precision & F1 by attributing crashes on true class `c`
    # to denominator (TP + FP + CRASH_c), eliminating crash-induced precision inflation.
    pen_p_list: List[float] = []
    pen_f1_list: List[float] = []
    per_class_metrics = {}
    for idx, lbl in enumerate(labels):
        tp_c = sum(1 for t, p in zip(y_true, y_pred) if t == lbl and p == lbl)
        fp_c = sum(1 for t, p in zip(y_true, y_pred) if t != lbl and p == lbl)
        crash_c = sum(1 for t, p in zip(y_true, y_pred) if t == lbl and p == "CRASH")
        p_pen = float(tp_c / (tp_c + fp_c + crash_c)) if (tp_c + fp_c + crash_c) > 0 else 0.0
        r_c = float(r_arr[idx])
        f1_pen = float(2.0 * p_pen * r_c / (p_pen + r_c)) if (p_pen + r_c) > 0 else 0.0
        pen_p_list.append(p_pen)
        pen_f1_list.append(f1_pen)

        c_retries = per_class_retries[lbl]
        c_times = per_class_times[lbl]
        c_cits = per_class_citations[lbl]
        per_class_metrics[lbl] = {
            "Precision": round(p_pen, 4),
            "Recall": round(r_c, 4),
            "F1-Score": round(f1_pen, 4),
            "Unpenalized_Precision": round(float(unpen_p_arr[idx]), 4),
            "Crash_Count": crash_c,
            "Avg_Retries": round(sum(c_retries) / max(len(c_retries), 1), 2),
            "Avg_Verification_Time (s)": round(sum(c_times) / max(len(c_times), 1), 4),
            "Citation_Fidelity (%)": (
                round(sum(1 for x in c_cits if x) / max(len(c_cits), 1) * 100.0, 2)
                if evaluate_explanations
                else None
            ),
        }

    p_macro = float(sum(pen_p_list) / len(labels))
    f1_macro = float(sum(pen_f1_list) / len(labels))

    norm_acc = None
    norm_f1_macro = None
    if norm_indices:
        ny_t = [y_true[i] for i in norm_indices]
        ny_p = [y_pred[i] for i in norm_indices]
        norm_acc = round(sum(1 for t, p in zip(ny_t, ny_p) if t == p) / len(ny_t) * 100.0, 2)
        norm_f1s: List[float] = []
        for nlbl in ("ENTAILED", "CONTRADICTED"):
            ntp = sum(1 for t, p in zip(ny_t, ny_p) if t == nlbl and p == nlbl)
            nfp = sum(1 for t, p in zip(ny_t, ny_p) if t != nlbl and p == nlbl)
            ncrash_c = sum(1 for t, p in zip(ny_t, ny_p) if t == nlbl and p == "CRASH")
            n_sup = sum(1 for t in ny_t if t == nlbl)
            np_c = float(ntp / (ntp + nfp + ncrash_c)) if (ntp + nfp + ncrash_c) > 0 else 0.0
            nr_c = float(ntp / n_sup) if n_sup > 0 else 0.0
            norm_f1s.append(float(2.0 * np_c * nr_c / (np_c + nr_c)) if (np_c + nr_c) > 0 else 0.0)
        norm_f1_macro = round(sum(norm_f1s) / 2.0, 4)

    rule_schema_trap_acc = (
        round(sum(1 for i in rule_schema_trap_indices if y_pred[i] == y_true[i]) / len(rule_schema_trap_indices) * 100.0, 2)
        if rule_schema_trap_indices
        else None
    )
    trace_safety_trap_acc = (
        round(sum(1 for i in trace_safety_trap_indices if y_pred[i] == y_true[i]) / len(trace_safety_trap_indices) * 100.0, 2)
        if trace_safety_trap_indices
        else None
    )

    return {
        "Executable_Rate (%)": round(executable_count / len(benchmark_items) * 100.0, 2),
        "Raw_Log_Executable_Rate (%)": round(raw_executable_count / len(benchmark_items) * 100.0, 2),
        "Crash_Rate (%)": round(crash_count / max(len(benchmark_items), 1) * 100.0, 2),
        "Strict_Accuracy (%)": strict_acc,
        "Normative_Accuracy (%)": norm_acc,
        "Normative_Macro_F1": norm_f1_macro,
        "Rule_Schema_Trap_Accuracy (%)": rule_schema_trap_acc,
        "Trace_Safety_Trap_Accuracy (%)": trace_safety_trap_acc,
        "Eq_Rate (%)": round(eq_count / len(benchmark_items) * 100.0, 2),
        "Normative_Eq_Rate (%)": (
            round(norm_eq_count / norm_total_count * 100.0, 2)
            if norm_total_count > 0
            else None
        ),
        "Trap_Detection_Rate (%)": (
            round(trap_eq_count / trap_total_count * 100.0, 2)
            if trap_total_count > 0
            else None
        ),
        "Macro_Precision": round(p_macro, 4),
        "Macro_Recall": round(float(r_macro), 4),
        "Macro_F1": round(f1_macro, 4),
        "Unpenalized_3Class_Macro_Precision": round(float(unpen_p_macro), 4),
        "Unpenalized_3Class_Macro_F1": round(float(unpen_f1_macro), 4),
        "Avg_Retry_Rounds": round(sum(retry_counts) / max(len(retry_counts), 1), 2),
        "Avg_Verification_Time (s)": round(sum(solving_times) / max(len(solving_times), 1), 4),
        "Citation_Fidelity (%)": (
            round(citation_verified_count / max(len(benchmark_items), 1) * 100.0, 2)
            if evaluate_explanations
            else None
        ),
        "Per_Class_Metrics": per_class_metrics,
        "Trajectories": trajectories_by_rule,
    }


def evaluate_rq1_complexity_tiers(
    normative_rules: List[Dict[str, Any]],
    log_df: pd.DataFrame,
    process_schema: Dict[str, Any],
    enable_self_correction: bool = True,
    enable_l3_roundtrip: Optional[bool] = None,
    llm_client: Any = None,
) -> Dict[str, Dict[str, float]]:
    """
    RQ1 (Table 1): Evaluate Semantic Equivalence (Eq. %) and error distribution across
    Tier 1 and Tier 2, separating genuine temporal Reversals from false-positive Abstentions
    and compilation Crashes.
    """
    if llm_client is None:
        llm_client = BenchmarkExperimentLLMClient(log_df=log_df)
    tiers = ["Tier 1: Control-Flow Only", "Tier 2: Temporal & Data-Aware"]
    results_by_tier: Dict[str, Dict[str, float]] = {}

    use_l3 = enable_self_correction if enable_l3_roundtrip is None else enable_l3_roundtrip
    cats = ["EQ", "STRENGTHENED", "WEAKENED", "REVERSED", "WRONG_ACTIVITY", "VACUOUS", "ABSTAINED", "CRASH"]
    all_counts: Dict[str, int] = {k: 0 for k in cats}
    all_counts["TOTAL"] = 0

    for tier_name in tiers:
        tier_rules = [r for r in normative_rules if r["complexity_tier"] == tier_name]
        counts: Dict[str, int] = {k: 0 for k in cats}

        for r_meta in tier_rules:
            chunk = r_meta["retrieved_chunk"]
            ast_obj = None
            rt_ok = not use_l3
            rt_msg = ""
            max_r = 5 if enable_self_correction else 1

            if not hasattr(llm_client, "generate_ast"):
                from src.evaluation.real_llm_client import run_single_rule_with_real_llm

                res_real = run_single_rule_with_real_llm(
                    rule_item=r_meta,
                    retrieved_chunk=chunk,
                    process_schema=process_schema,
                    llm=llm_client,
                    max_retry=max_r,
                    enable_l1_l2=True,
                    enable_l3_roundtrip=use_l3,
                )
                rt_ok = bool(res_real["roundtrip_ok"])
                rt_msg = str(res_real.get("roundtrip_msg") or "")
                if res_real["final_ast"] is not None:
                    ast_obj = DeclareConstraintAST(**res_real["final_ast"])
            else:
                feedback = ""
                for _ in range(max_r):
                    ast_obj = None
                    raw_json = llm_client.generate_ast(chunk, process_schema, feedback=feedback, rule_meta=r_meta)
                    ok_l12, res_l12 = check_layer1_and_layer2(raw_json, process_schema, chunk)
                    if not ok_l12:
                        rt_ok = False
                        rt_msg = str(res_l12)
                        feedback = rt_msg
                        continue
                    ast_obj = DeclareConstraintAST(**res_l12)
                    if use_l3:
                        rt_ok, rt_msg = check_roundtrip_fidelity(ast_obj.model_dump(), chunk, llm_client)
                        if rt_ok:
                            break
                        feedback = rt_msg
                    else:
                        rt_ok = True
                        break

            raw_cat = classify_semantic_equivalence(ast_obj, r_meta["gold_ast"], log_df) if ast_obj is not None else "CRASH"
            is_baseless_rejection = (
                "BASELESS" in rt_msg
                or "OUT_OF_DIRECTIVE_SCOPE" in rt_msg
                or "MISSING_LOG_EVIDENCE" in rt_msg
            )
            if not rt_ok and (use_l3 or is_baseless_rejection):
                if ast_obj is not None and raw_cat == "VACUOUS":
                    cat = "VACUOUS"
                elif is_baseless_rejection:
                    cat = "ABSTAINED"
                elif ast_obj is None:
                    cat = "CRASH"
                elif raw_cat == "EQ":
                    cat = "ABSTAINED"
                else:
                    cat = raw_cat
            elif ast_obj is None:
                cat = "CRASH"
            else:
                cat = raw_cat

            counts[cat] += 1
            all_counts[cat] += 1
            all_counts["TOTAL"] += 1

        n = max(len(tier_rules), 1)
        results_by_tier[tier_name] = {
            "Rules_Count": len(tier_rules),
            "Eq. (%)": round(counts["EQ"] / n * 100.0, 2),
            "Strengthened (%)": round(counts["STRENGTHENED"] / n * 100.0, 2),
            "Weakened (%)": round(counts["WEAKENED"] / n * 100.0, 2),
            "Reversed (%)": round(counts["REVERSED"] / n * 100.0, 2),
            "Wrong Activity (%)": round(counts["WRONG_ACTIVITY"] / n * 100.0, 2),
            "Vacuous (%)": round(counts["VACUOUS"] / n * 100.0, 2),
            "Abstained (%)": round(counts["ABSTAINED"] / n * 100.0, 2),
            "Crash (%)": round(counts["CRASH"] / n * 100.0, 2),
        }

    tot = max(all_counts["TOTAL"], 1)
    results_by_tier["Overall Pipeline"] = {
        "Rules_Count": all_counts["TOTAL"],
        "Eq. (%)": round(all_counts["EQ"] / tot * 100.0, 2),
        "Strengthened (%)": round(all_counts["STRENGTHENED"] / tot * 100.0, 2),
        "Weakened (%)": round(all_counts["WEAKENED"] / tot * 100.0, 2),
        "Reversed (%)": round(all_counts["REVERSED"] / tot * 100.0, 2),
        "Wrong Activity (%)": round(all_counts["WRONG_ACTIVITY"] / tot * 100.0, 2),
        "Vacuous (%)": round(all_counts["VACUOUS"] / tot * 100.0, 2),
        "Abstained (%)": round(all_counts["ABSTAINED"] / tot * 100.0, 2),
        "Crash (%)": round(all_counts["CRASH"] / tot * 100.0, 2),
    }
    return results_by_tier
