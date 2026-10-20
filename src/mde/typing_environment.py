"""
Bước 2.2: Kiểm tra Thực thể & Kiểu dữ liệu Tĩnh (Tầng 2 - Static Checker)
Tham khảo Mục 3.3 bài OCL2026 (repo OVAS):
- Khởi tạo môi trường kiểu gắn ngữ cảnh (Context-Bound Typing Environment Γ) từ process_schema.json.
- Hàm tra cứu thuộc tính & thực thể δ(C, p) trên phân hệ quy trình (Activity, Case, Event).
- Kiểm tra tương thích kiểu (Type Conformance) cho biểu thức điều kiện thuộc tính trước khi đưa xuống Declare4Py.
"""

from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Tuple, Union
from .constraint_ast import (
    DeclareConstraintAST,
    validate_layer1_ast,
)

ORDERING_OPERATORS = {"<", "<=", ">", ">="}
EQUALITY_OPERATORS = {"==", "!="}


class ProcessTypingEnvironment:
    """
    Context-Bound Typing Environment Γ cho Khai phá Quy trình (Process Mining),
    chuyển thể từ OVAS (OCL2026, Section 3.3) trên lược đồ process_schema.json.
    """

    def __init__(self, process_schema: Dict[str, Any]) -> None:
        self.schema = process_schema
        self.valid_activities: List[str] = list(
            process_schema.get("valid_activities", [])
        )
        if "A_Validating" in self.valid_activities and "A_Validated" not in self.valid_activities:
            self.valid_activities.append("A_Validated")
        self.activities_by_origin: Dict[str, List[str]] = dict(
            process_schema.get("activities_by_origin", {})
        )
        self.case_attributes: Dict[str, Dict[str, Any]] = dict(
            process_schema.get("case_attributes", {})
        )
        self.event_attributes: Dict[str, Dict[str, Any]] = dict(
            process_schema.get("event_attributes", {})
        )

        # Xây dựng bảng tra cứu thuộc tính hợp nhất cho δ(C, p)
        # Cho phép tra cứu cả tên đầy đủ ("case:RequestedAmount") lẫn tên rút gọn ("RequestedAmount")
        self._attr_lookup: Dict[str, Tuple[str, str, List[str]]] = {}
        for col, meta in self.case_attributes.items():
            self._attr_lookup[col] = ("Case", meta["type"], meta.get("samples", []))
            short_name = col.replace("case:", "", 1)
            if short_name not in self._attr_lookup:
                self._attr_lookup[short_name] = (
                    "Case",
                    meta["type"],
                    meta.get("samples", []),
                )

        for col, meta in self.event_attributes.items():
            self._attr_lookup[col] = ("Event", meta["type"], meta.get("samples", []))

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
            f"Navigational Violation in δ(Activity, '{activity_name}'): "
            f"Activity '{activity_name}' does not exist in Process Metamodel Γ.{hint} "
            f"Valid activities are: {self.valid_activities}.",
        )

    def delta(
        self, context: str, prop: str
    ) -> Tuple[bool, Union[Tuple[str, str, List[str]], str]]:
        """
        Hàm tra cứu thuộc tính δ(C, p) từ OVAS (Mục 3.3):
        - C ∈ {'Case', 'Event', 'Process'}
        - p là tên thuộc tính dữ liệu (activation_attr).
        Trả về (True, (origin_scope, mapped_type, samples)) nếu hợp lệ,
        hoặc (False, diagnostic_error) nếu thuộc tính không tồn tại.
        """
        clean_prop = prop.strip()
        if clean_prop.startswith(("A.", "T.", "a.", "t.")):
            clean_prop = clean_prop[2:]

        if clean_prop in self._attr_lookup:
            scope, attr_type, samples = self._attr_lookup[clean_prop]
            if context in ("Process", "Any", scope):
                return True, (scope, attr_type, samples)

        all_valid_attrs = list(self.case_attributes.keys()) + list(
            self.event_attributes.keys()
        )
        suggestions = get_close_matches(clean_prop, all_valid_attrs, n=3, cutoff=0.4)
        hint = f" Closest valid attributes: {suggestions}." if suggestions else ""
        return (
            False,
            f"Navigational Violation in δ({context}, '{prop}'): "
            f"Attribute '{prop}' is undefined in Typing Environment Γ.{hint} "
            f"Valid attributes: {all_valid_attrs}.",
        )

    def check_type_conformance(
        self,
        attr_name: str,
        operator: str,
        value: Any,
    ) -> Tuple[bool, Optional[str]]:
        """
        Kiểm tra quy tắc tương thích kiểu (Type Conformance) của OVAS:
        - Thuộc tính kiểu String hoặc Boolean không được phép dùng toán tử so sánh thứ tự (<, <=, >, >=).
        - Thuộc tính kiểu Float/Integer bắt buộc phải so sánh với giá trị số (int/float).
        - Thuộc tính kiểu Boolean chỉ được so sánh với True/False.
        """
        ok, lookup_res = self.delta("Process", attr_name)
        if not ok:
            return False, str(lookup_res)

        scope, attr_type, samples = lookup_res  # type: ignore[misc]

        if attr_type in ("String", "Boolean") and operator in ORDERING_OPERATORS:
            return (
                False,
                f"Type Conformance Violation in Γ: Attribute '{attr_name}' ({scope} scope) "
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
                    f"Type Conformance Violation in Γ: Attribute '{attr_name}' has numeric type '{attr_type}' "
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
                    f"Type Conformance Violation in Γ: Attribute '{attr_name}' has type 'Boolean' "
                    f"(samples: {samples}), but got incompatible value {repr(value)}.",
                )

        return True, None

    def validate_ast(
        self,
        ast_obj: DeclareConstraintAST,
        retrieved_chunk: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Thực thi toàn bộ kiểm tra tĩnh Tầng 2 (Layer 2 Static Type & Entity Checker) trên AST.
        """
        errors: List[str] = []

        # 1. Kiểm tra activation_activity bằng δ(Activity, a)
        ok_act, msg_act = self.delta_activity(ast_obj.activation_activity)
        if not ok_act and msg_act:
            errors.append(msg_act)

        # 2. Kiểm tra target_activity (nếu có) bằng δ(Activity, b)
        if ast_obj.target_activity is not None:
            ok_tgt, msg_tgt = self.delta_activity(ast_obj.target_activity)
            if not ok_tgt and msg_tgt:
                errors.append(msg_tgt)
            elif ast_obj.target_activity == ast_obj.activation_activity:
                errors.append(
                    f"Semantic Self-Loop Violation: 'activation_activity' and 'target_activity' "
                    f"cannot be identical ('{ast_obj.activation_activity}')."
                )

        # 3. Kiểm tra thuộc tính dữ liệu và ép kiểu bằng δ(C, p) & Type Conformance
        if ast_obj.activation_attr is not None:
            clean_attr = ast_obj.activation_attr.strip()
            if clean_attr.startswith(("A.", "T.")):
                clean_attr = clean_attr[2:]
                ast_obj.activation_attr = clean_attr

            ok_type, msg_type = self.check_type_conformance(
                clean_attr,
                ast_obj.activation_op or "==",
                ast_obj.activation_val,
            )
            if not ok_type and msg_type:
                errors.append(msg_type)

        # 4. Kiểm tra tính nhất quán giữa bước phân rã Req2LTL (nếu có) và Template được chọn
        if ast_obj.decomposition is not None:
            direction = ast_obj.decomposition.temporal_direction
            if "Precedence" in direction and ast_obj.template_name in (
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
            elif "Response" in direction and ast_obj.template_name in (
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
            expected_id = retrieved_chunk["article_id"]
            if ast_obj.article_id.strip() != expected_id.strip():
                errors.append(
                    f"Traceability Mismatch: AST 'article_id' is '{ast_obj.article_id}', "
                    f"expected '{expected_id}' from retrieved legal clause."
                )

        if errors:
            formatted = "\n".join(f"- [Layer 2 Static Error]: {e}" for e in errors)
            return False, formatted

        return True, None


def check_layer1_and_layer2(
    raw_response: Union[str, Dict[str, Any]],
    process_schema: Dict[str, Any],
    retrieved_chunk: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Union[DeclareConstraintAST, str]]:
    """
    Hàm kiểm chứng tích hợp Tầng 1 (JSON Schema + Closed Enumeration) và
    Tầng 2 (Typing Environment Γ + δ(C, p) + Type Conformance).
    Trả về:
      - (True, DeclareConstraintAST) nếu vượt qua cả 2 tầng.
      - (False, diagnostic_feedback_str) nếu phát hiện lỗi ở Tầng 1 hoặc Tầng 2.
    """
    # Kiểm tra Tầng 1
    is_l1_valid, l1_result = validate_layer1_ast(raw_response)
    if not is_l1_valid:
        return False, str(l1_result)

    ast_obj = l1_result  # type: ignore[assignment]
    assert isinstance(ast_obj, DeclareConstraintAST)

    # Kiểm tra Tầng 2
    gamma = ProcessTypingEnvironment(process_schema)
    is_l2_valid, l2_error = gamma.validate_ast(ast_obj, retrieved_chunk=retrieved_chunk)
    if not is_l2_valid:
        return False, str(l2_error)

    return True, ast_obj
