"""
Bộ Kiểm chứng Lược đồ Quy trình & Tính khả dụng Nhân quả Thuộc tính (Process Schema & Causal Attribute Validator):
- Khởi tạo từ điển hoạt động, thuộc tính mức Case/Event và quan hệ vòng đời từ `process_schema.json`.
- Kiểm tra tính hợp lệ thực thể hoạt động, phạm vi thuộc tính (Case vs Event), tương thích kiểu toán tử
  và tính khả dụng nhân quả (Causal Attribute Availability) của thuộc tính sự kiện theo Behavioral Profile.
"""

from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Tuple, Union
from .constraint_ast import (
    DeclareConstraintAST,
    TemporalDirection,
    validate_declare_ast,
)

ORDERING_OPERATORS = {"<", "<=", ">", ">="}
EQUALITY_OPERATORS = {"==", "!="}


class ProcessSchemaValidator:
    """
    Bộ kiểm chứng lược đồ & tính khả dụng nhân quả cho Khai phá Quy trình (Process Mining),
    xây dựng trực tiếp trên `process_schema.json` (bao gồm Behavioral Profile của Event Log).
    """

    def __init__(self, process_schema: Dict[str, Any]) -> None:
        self.schema = process_schema
        self.aliases: Dict[str, str] = dict(process_schema.get("activity_aliases", {}))
        self.valid_activities: List[str] = list(
            process_schema.get("valid_activities", [])
        )
        # Bổ sung các bí danh hoạt động (aliases) được cấu hình trong Metamodel Schema (thay vì nhúng cứng mã nguồn)
        for alias in self.aliases:
            if alias not in self.valid_activities:
                self.valid_activities.append(alias)

        self.activities_by_origin: Dict[str, List[str]] = dict(
            process_schema.get("activities_by_origin", {})
        )
        self.case_attributes: Dict[str, Dict[str, Any]] = dict(
            process_schema.get("case_attributes", {})
        )
        self.event_attributes: Dict[str, Dict[str, Any]] = dict(
            process_schema.get("event_attributes", {})
        )

        # Xây dựng bảng tra cứu thuộc tính phân tầng cho δ(C, p)
        # Lưu trữ riêng biệt theo scope Case vs Event để giải quyết triệt để xung đột tên rút gọn
        self._case_attr_lookup: Dict[str, Tuple[str, str, List[str]]] = {}
        self._event_attr_lookup: Dict[str, Tuple[str, str, List[str]]] = {}
        self._attr_lookup: Dict[str, Tuple[str, str, List[str]]] = {}

        for col, meta in self.case_attributes.items():
            entry = ("Case", meta["type"], meta.get("samples", []))
            self._case_attr_lookup[col] = entry
            self._attr_lookup[col] = entry
            short_name = col.replace("case:", "", 1)
            self._case_attr_lookup[short_name] = entry
            if short_name not in self._attr_lookup:
                self._attr_lookup[short_name] = entry

        for col, meta in self.event_attributes.items():
            entry = ("Event", meta["type"], meta.get("samples", []))
            self._event_attr_lookup[col] = entry
            # Tránh ghi đè nếu đã có trong Case attribute, ưu tiên giải quyết theo context cụ thể
            if col not in self._attr_lookup:
                self._attr_lookup[col] = entry

    def delta_activity(self, activity_name: str) -> Tuple[bool, Optional[str]]:
        """
        Hàm tra cứu thực thể hoạt động δ(Activity, a):
        Kiểm tra xem hoạt động a có thuộc tập valid_activities trong Γ hay không.
        """
        if activity_name in self.valid_activities:
            # Tìm phân hệ (Application / Offer / Workflow)
            for origin, acts in self.activities_by_origin.items():
                if activity_name in acts:
                    return True, origin
            return True, "Process"

        suggestions = get_close_matches(
            activity_name, self.valid_activities, n=3, cutoff=0.4
        )
        hint = f" Did you mean: {suggestions}?" if suggestions else ""
        return (
            False,
            f"Navigational Violation for activity '{activity_name}': "
            f"Activity '{activity_name}' does not exist in Process Schema.{hint} "
            f"Valid activities are: {self.valid_activities}.",
        )

    def delta(
        self, context: str, prop: str
    ) -> Tuple[bool, Union[Tuple[str, str, List[str]], str]]:
        """
        Tra cứu thuộc tính dữ liệu theo ngữ cảnh (Case / Event / Process) trên Process Schema.
        Trả về (True, (origin_scope, mapped_type, samples)) nếu hợp lệ,
        hoặc (False, diagnostic_error) nếu thuộc tính không tồn tại.
        """
        clean_prop = prop.strip()
        if clean_prop.startswith(("A.", "T.", "a.", "t.")):
            clean_prop = clean_prop[2:]

        # 1. Tra cứu theo scope cụ thể nếu context được chỉ định
        if context == "Case" and clean_prop in self._case_attr_lookup:
            return True, self._case_attr_lookup[clean_prop]
        if context == "Event" and clean_prop in self._event_attr_lookup:
            return True, self._event_attr_lookup[clean_prop]

        # 2. Tra cứu tổng quát
        if clean_prop in self._attr_lookup:
            scope, attr_type, samples = self._attr_lookup[clean_prop]
            if context in ("Process", "Any", scope):
                return True, (scope, attr_type, samples)

        # 3. Chẩn đoán lỗi sai phạm vi (Scope Mismatch)
        if context == "Case" and clean_prop in self._event_attr_lookup:
            return (
                False,
                f"Scope Mismatch for '{prop}': Attribute '{prop}' is defined at Event scope, "
                f"not Case scope in Process Schema.",
            )
        if context == "Event" and clean_prop in self._case_attr_lookup:
            return (
                False,
                f"Scope Mismatch for '{prop}': Attribute '{prop}' is defined at Case scope, "
                f"not Event scope in Process Schema.",
            )

        all_valid_attrs = list(self.case_attributes.keys()) + list(
            self.event_attributes.keys()
        )
        suggestions = get_close_matches(clean_prop, all_valid_attrs, n=3, cutoff=0.4)
        hint = f" Closest valid attributes: {suggestions}." if suggestions else ""
        return (
            False,
            f"Navigational Violation for attribute '{prop}' ({context} scope): "
            f"Attribute '{prop}' is undefined in Process Schema.{hint} "
            f"Valid attributes: {all_valid_attrs}.",
        )

    def check_type_conformance(
        self,
        attr_name: str,
        operator: str,
        value: Any,
        context: str = "Process",
    ) -> Tuple[bool, Optional[str]]:
        """
        Kiểm tra quy tắc tương thích kiểu toán tử – giá trị cho biểu thức điều kiện thuộc tính:
        - Thuộc tính kiểu String hoặc Boolean không được phép dùng toán tử so sánh thứ tự (<, <=, >, >=).
        - Thuộc tính kiểu Float/Integer bắt buộc phải so sánh với giá trị số (int/float).
        - Thuộc tính kiểu Boolean chỉ được so sánh với True/False.
        """
        ok, lookup_res = self.delta(context, attr_name)
        if not ok:
            return False, str(lookup_res)

        scope, attr_type, samples = lookup_res  # type: ignore[misc]

        if attr_type in ("String", "Boolean") and operator in ORDERING_OPERATORS:
            return (
                False,
                f"Type Conformance Violation: Attribute '{attr_name}' ({scope} scope) "
                f"has type '{attr_type}' (samples: {samples}), which does not support ordering operator '{operator}'. "
                f"Only equality operators ('==', '!=') are permitted for '{attr_type}'.",
            )

        if attr_type in ("Float", "Integer"):
            is_numeric = isinstance(value, (int, float)) and not isinstance(
                value, bool
            )
            if not is_numeric and isinstance(value, str):
                try:
                    float(value)
                    is_numeric = True
                except ValueError:
                    is_numeric = False
            if not is_numeric:
                return (
                    False,
                    f"Type Conformance Violation: Attribute '{attr_name}' has numeric type '{attr_type}' "
                    f"(samples: {samples}), but was compared against non-numeric value {repr(value)}.",
                )

        if attr_type == "Boolean":
            valid_bool = isinstance(value, bool) or str(value) in (
                "True",
                "False",
                "true",
                "false",
            )
            if not valid_bool:
                return (
                    False,
                    f"Type Conformance Violation: Attribute '{attr_name}' has type 'Boolean' "
                    f"(samples: {samples}), but got incompatible value {repr(value)}.",
                )

        return True, None

    def validate_ast(
        self,
        ast_obj: DeclareConstraintAST,
        retrieved_chunk: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Thực thi kiểm tra lược đồ quy trình, kiểu dữ liệu & tính khả dụng nhân quả thuộc tính trên AST.
        """
        errors: List[str] = []

        # 1. Kiểm tra activation_activity
        ok_act, msg_act = self.delta_activity(ast_obj.activation_activity)
        if not ok_act and msg_act:
            errors.append(msg_act)

        # 2. Kiểm tra target_activity (nếu có)
        if ast_obj.target_activity is not None:
            ok_tgt, msg_tgt = self.delta_activity(ast_obj.target_activity)
            if not ok_tgt and msg_tgt:
                errors.append(msg_tgt)
            elif ast_obj.target_activity == ast_obj.activation_activity:
                errors.append(
                    f"Semantic Self-Loop Violation: 'activation_activity' and 'target_activity' "
                    f"cannot be identical ('{ast_obj.activation_activity}')."
                )

        # 3. Kiểm tra thuộc tính dữ liệu, tương thích kiểu & tính khả dụng nhân quả (Causal Attribute Availability)
        if ast_obj.activation_attr is not None:
            clean_attr = ast_obj.activation_attr.strip()
            if clean_attr.startswith(("A.", "T.", "a.", "t.")):
                clean_attr = clean_attr[2:]

            if clean_attr.startswith("case:") or clean_attr in self._case_attr_lookup:
                attr_context = "Case"
            elif clean_attr in self._event_attr_lookup:
                attr_context = "Event"
            else:
                attr_context = "Process"

            ok_type, msg_type = self.check_type_conformance(
                clean_attr,
                ast_obj.activation_op or "==",
                ast_obj.activation_val,
                context=attr_context,
            )
            if not ok_type and msg_type:
                errors.append(msg_type)
            elif attr_context == "Event" and clean_attr in self.event_attributes:
                app_acts = self.event_attributes[clean_attr].get("applicable_activities")
                if (
                    isinstance(app_acts, list)
                    and len(app_acts) > 0
                    and ast_obj.activation_activity not in app_acts
                ):
                    # Bổ sung chẩn đoán thứ tự nhân quả từ Behavioral Profile (nếu activation xảy ra trước khi thuộc tính phát sinh)
                    bp_pairs = self.schema.get("behavioral_profile", {}).get("strict_causal_pairs", [])
                    strict_before_origin = any(
                        p.get("from") == ast_obj.activation_activity
                        and p.get("to") in app_acts
                        and p.get("order_ratio", 0.0) >= 0.99
                        for p in bp_pairs
                    )
                    if strict_before_origin:
                        errors.append(
                            f"Causal Attribute Availability Violation: Event attribute '{clean_attr}' is only "
                            f"populated later in the lifecycle on {app_acts}, which strictly follow "
                            f"'{ast_obj.activation_activity}' in the Behavioral Profile (attribute does not yet exist "
                            f"under causal evaluation). Anchor the rule on an activity in {app_acts}."
                        )
                    else:
                        errors.append(
                            f"Event-Attribute Lifecycle Domain Violation: Event attribute '{clean_attr}' "
                            f"is never populated (0 non-null records) on activity '{ast_obj.activation_activity}'. "
                            f"In the Process Schema, '{clean_attr}' is only recorded on activities: {app_acts}. "
                            f"Please select an anchor/activation activity from {app_acts}."
                        )

        # 4. Kiểm tra tính nhất quán giữa bước phân rã Req2LTL (nếu có) và Template được chọn
        if ast_obj.decomposition is not None:
            direction = str(ast_obj.decomposition.temporal_direction)
            is_prereq = (
                direction == TemporalDirection.PREREQUISITE
                or direction.startswith("Prerequisite")
            )
            is_conseq = (
                direction == TemporalDirection.CONSEQUENCE
                or direction.startswith("Consequence")
            )
            if is_prereq and ast_obj.template_name in (
                "Response",
                "Alternate Response",
                "Chain Response",
                "Responded Existence",
            ):
                errors.append(
                    f"Req2LTL Decomposition Mismatch: Decomposition identified a Prerequisite/Precedence rule "
                    f"('{direction}'), but template '{ast_obj.template_name}' (Response family) was selected. "
                    f"Use 'Precedence', 'Alternate Precedence', or 'Chain Precedence' instead."
                )
            elif is_conseq and ast_obj.template_name in (
                "Precedence",
                "Alternate Precedence",
                "Chain Precedence",
            ):
                errors.append(
                    f"Req2LTL Decomposition Mismatch: Decomposition identified a Consequence/Response rule "
                    f"('{direction}'), but template '{ast_obj.template_name}' (Precedence family) was selected. "
                    f"Use 'Response', 'Alternate Response', or 'Chain Response' instead."
                )

        # 5. Đối chiếu article_id với đoạn luật truy xuất (nếu được cung cấp)
        if retrieved_chunk and "article_id" in retrieved_chunk:
            expected_id = retrieved_chunk["article_id"].strip()
            actual_id = ast_obj.article_id.strip()
            # Cho phép khớp chính xác hoặc khớp quan hệ tiểu mục (ví dụ "Article 2(2)(c)" là tiểu mục của "Article 2(2)")
            is_subclause_match = (
                actual_id == expected_id
                or actual_id.startswith(expected_id)
                or expected_id.startswith(actual_id)
            )
            if not is_subclause_match:
                errors.append(
                    f"Traceability Mismatch: AST 'article_id' is '{actual_id}', "
                    f"expected '{expected_id}' from retrieved legal clause."
                )

        if errors:
            formatted = "\n".join(f"- [Process Schema Validation Error]: {e}" for e in errors)
            return False, formatted

        return True, None


# Backward-compatible class alias
ProcessTypingEnvironment = ProcessSchemaValidator


def validate_ast_against_process_schema(
    raw_response: Union[str, Dict[str, Any]],
    process_schema: Dict[str, Any],
    retrieved_chunk: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Union[DeclareConstraintAST, str]]:
    """
    Hàm kiểm chứng hợp nhất cấu trúc DeclareConstraintAST với Lược đồ Quy trình & Tính khả dụng Thuộc tính.
    Trả về:
      - (True, DeclareConstraintAST) nếu hợp lệ (trả về AST mới đã chuẩn hóa).
      - (False, diagnostic_feedback_str) nếu phát hiện vi phạm cấu trúc hoặc lược đồ.
    """
    is_ast_valid, ast_result = validate_declare_ast(raw_response)
    if not is_ast_valid:
        return False, str(ast_result)

    ast_obj = ast_result  # type: ignore[assignment]
    assert isinstance(ast_obj, DeclareConstraintAST)

    validator = ProcessSchemaValidator(process_schema)
    is_schema_valid, schema_error = validator.validate_ast(ast_obj, retrieved_chunk=retrieved_chunk)
    if not is_schema_valid:
        return False, str(schema_error)

    # Trả về AST mới (immutable pattern) nếu có tiền tố A./T.
    if ast_obj.activation_attr is not None:
        raw_attr = ast_obj.activation_attr.strip()
        if raw_attr.startswith(("A.", "T.", "a.", "t.")):
            ast_obj = ast_obj.model_copy(update={"activation_attr": raw_attr[2:]})

    # Chuẩn hóa article_id theo mã định danh chuẩn của retrieved_chunk nếu là dạng mở rộng tiểu mục
    if retrieved_chunk and "article_id" in retrieved_chunk:
        expected_id = retrieved_chunk["article_id"].strip()
        if ast_obj.article_id.strip() != expected_id and (
            ast_obj.article_id.strip().startswith(expected_id) or expected_id.startswith(ast_obj.article_id.strip())
        ):
            ast_obj = ast_obj.model_copy(update={"article_id": expected_id})

    return True, ast_obj


# Backward-compatible function alias
check_layer1_and_layer2 = validate_ast_against_process_schema
