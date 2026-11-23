"""
Định nghĩa Mô hình Ràng buộc Khai báo (Declarative Constraint AST - PSM) cho Declare4Py.
Kết hợp:
- Mô hình AST định kiểu chặt (Typed AST) biên dịch trực tiếp sang dòng lệnh `.decl` của Declare4Py
- Cấu trúc phân rã ngữ nghĩa trung gian (Semantic Decomposition) từ Req2LTL (ASE 2025)
"""

import json
import re
from enum import Enum
from typing import Any, Dict, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field, ValidationError, model_validator

class TemporalDirection(str, Enum):
    PREREQUISITE = "Prerequisite (Precedence: Target B requires prior Activation A)"
    CONSEQUENCE = "Consequence (Response: Activation A triggers subsequent Target B)"
    UNARY = "Unary (Existence / Absence / Init / Exactly1 of Activity A)"
    NEGATIVE = "Negative / Mutual Exclusion (Not Response / Not Precedence / Not Co-Existence)"

# Tập mẫu Unary và Binary chuẩn trong Declare4Py
UNARY_TEMPLATES = {
    "Existence",
    "Absence",
    "Init",
    "Exactly1",
}

BINARY_TEMPLATES = {
    "Choice",
    "Exclusive Choice",
    "Responded Existence",
    "Response",
    "Alternate Response",
    "Chain Response",
    "Precedence",
    "Alternate Precedence",
    "Chain Precedence",
    "Not Responded Existence",
    "Not Response",
    "Not Precedence",
    "Not Co-Existence",
}

TemplateLiteral = Literal[
    "Existence",
    "Absence",
    "Init",
    "Exactly1",
    "Choice",
    "Exclusive Choice",
    "Responded Existence",
    "Response",
    "Alternate Response",
    "Chain Response",
    "Precedence",
    "Alternate Precedence",
    "Chain Precedence",
    "Not Responded Existence",
    "Not Response",
    "Not Precedence",
    "Not Co-Existence",
]

OperatorLiteral = Literal["==", "!=", "<", "<=", ">", ">="]
TimeUnitLiteral = Literal["s", "m", "h", "d"]


class SemanticDecomposition(BaseModel):
    """
    Bước trung gian từ Req2LTL (ASE 2025, arXiv:2512.17334):
    Phân rã câu yêu cầu pháp lý phức tạp thành các thành phần Tiền đề (Activation) -
    Hệ quả (Target) - Điều kiện thời gian/dữ liệu để tránh nhầm chiều Precedence vs Response.
    """

    temporal_direction: Literal[
        "Prerequisite (Precedence: Target B requires prior Activation A)",
        "Consequence (Response: Activation A triggers subsequent Target B)",
        "Unary (Existence / Absence / Init / Exactly1 of Activity A)",
        "Negative / Mutual Exclusion (Not Response / Not Precedence / Not Co-Existence)",
    ] = Field(
        description="Identify canonical temporal direction before selecting a Declare4Py template"
    )
    activation_semantics: str = Field(
        description="Description of the activation/prerequisite event in the legal clause"
    )
    target_semantics: Optional[str] = Field(
        default=None,
        description="Description of the target/consequent event in the legal clause",
    )
    data_guard_semantics: Optional[str] = Field(
        default=None,
        description="Quantitative data guard condition (if any, e.g., EUR amount, credit score)",
    )
    temporal_bound_semantics: Optional[str] = Field(
        default=None,
        description="Temporal deadline bound (if any, e.g., within 14 calendar days, 30 days)",
    )


class DeclareConstraintAST(BaseModel):
    """
    Khuôn mẫu AST đóng kín (Closed-Enumeration Pydantic Schema)
    kết hợp với định dạng chuẩn của decl_parser.py trong Declare4Py.
    """

    article_id: str = Field(
        description="Referenced clause from Directive 2008/48/EC (e.g., Article 8(1), Article 14(1))"
    )
    decomposition: Optional[SemanticDecomposition] = Field(
        default=None,
        description="Req2LTL semantic decomposition prior to Declare template mapping",
    )

    # Khóa cứng vào đúng tên các Template trong class Templatable của repo Declare4Py
    template_name: TemplateLiteral

    # Cặp hoạt động (Unary template chỉ dùng activation_activity, Binary dùng cả hai)
    activation_activity: str
    target_activity: Optional[str] = None

    # Điều kiện thuộc tính dữ liệu theo cú pháp A.<attribute> của Declare4Py (VD: A.OfferedAmount >= 200)
    activation_attr: Optional[str] = None
    activation_op: Optional[OperatorLiteral] = None
    activation_val: Optional[Union[float, int, str, bool]] = None

    # Điều kiện thời gian chuẩn của Declare4Py: min_time, max_time, unit (s/m/h/d)
    time_min: Optional[int] = 0
    time_max: Optional[int] = None
    time_unit: Optional[TimeUnitLiteral] = "d"

    @model_validator(mode="after")
    def validate_structural_invariants(self) -> "DeclareConstraintAST":
        """Kiểm tra tính hợp lệ cấu trúc AST (Arity của Template, bộ ba điều kiện dữ liệu, khoảng thời gian)."""
        if self.template_name in UNARY_TEMPLATES and self.target_activity is not None:
            raise ValueError(
                f"AST Structural Error: Unary template '{self.template_name}' "
                f"must NOT specify 'target_activity' (got '{self.target_activity}')."
            )
        if self.template_name in BINARY_TEMPLATES and not self.target_activity:
            raise ValueError(
                f"AST Structural Error: Binary template '{self.template_name}' "
                f"requires a non-empty 'target_activity'."
            )

        # Kiểm tra bộ ba điều kiện thuộc tính (activation_attr, activation_op, activation_val)
        attr_fields = [
            self.activation_attr is not None,
            self.activation_op is not None,
            self.activation_val is not None,
        ]
        if any(attr_fields) and not all(attr_fields):
            raise ValueError(
                "AST Structural Error: Data condition requires all three fields "
                "('activation_attr', 'activation_op', 'activation_val') to be set together."
            )

        # Kiểm tra khoảng thời gian hợp lệ
        if self.time_max is not None:
            min_t = 0 if self.time_min is None else self.time_min
            if min_t < 0 or self.time_max < min_t:
                raise ValueError(
                    f"AST Structural Error: Invalid time interval [{min_t}, {self.time_max}] "
                    f"(require 0 <= time_min <= time_max)."
                )
        return self

    def to_declare4py_line(self) -> str:
        """
        Hàm biên dịch AST trực tiếp sang định dạng dòng lệnh .decl của Declare4Py:
        Template[Activation, Target] | Activation_Condition | Correlation_Condition | Time_Condition
        """
        acts = (
            f"{self.activation_activity}, {self.target_activity}"
            if self.target_activity
            else self.activation_activity
        )
        if self.activation_attr:
            val_str = (
                f'"{self.activation_val}"'
                if isinstance(self.activation_val, str)
                and not str(self.activation_val).replace(".", "", 1).isdigit()
                and str(self.activation_val) not in ("True", "False")
                else str(self.activation_val)
            )
            act_cond = f"A.{self.activation_attr} {self.activation_op} {val_str}"
        else:
            act_cond = ""

        min_t = 0 if self.time_min is None else self.time_min
        unit = self.time_unit or "d"
        time_cond = (
            f"{min_t},{self.time_max},{unit}" if self.time_max is not None else ""
        )
        return f"{self.template_name}[{acts}] | {act_cond} | | {time_cond}"

    def to_declare4py_dict(self) -> Dict[str, Any]:
        """
        Xuất trực tiếp cấu trúc từ điển tương thích với DeclModel / decl_parser.py của Declare4Py
        để truyền thẳng sang Bước 3 không cần viết hàm chuyển đổi.
        """
        activities = (
            [self.activation_activity, self.target_activity]
            if self.target_activity
            else [self.activation_activity]
        )
        line = self.to_declare4py_line()
        parts = line.split("|")
        conditions = [p.strip() for p in parts[1:]]
        return {
            "article_id": self.article_id,
            "template": self.template_name,
            "activities": activities,
            "condition": conditions,  # [activation_cond, correlation_cond, time_cond]
            "decl_line": line,
        }


def extract_json_payload(raw_text: str) -> str:
    """Bóc tách chuỗi JSON từ phản hồi của LLM (loại bỏ thẻ <think> và markdown code block nếu có)."""
    text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text


def validate_declare_ast(
    raw_input: Union[str, Dict[str, Any]]
) -> Tuple[bool, Union[DeclareConstraintAST, str]]:
    """
    Kiểm tra cấu trúc & lược đồ AST (Declarative Constraint Schema Check):
    Đảm bảo đầu ra tuân thủ nghiêm ngặt cấu trúc của DeclareConstraintAST.
    """
    try:
        if isinstance(raw_input, str):
            clean_json = extract_json_payload(raw_input)
            data = json.loads(clean_json)
        elif isinstance(raw_input, dict):
            data = raw_input
        else:
            return False, f"[AST Syntax Error]: Unsupported payload type {type(raw_input).__name__}."

        ast_obj = DeclareConstraintAST.model_validate(data)
        return True, ast_obj

    except json.JSONDecodeError as exc:
        return (
            False,
            f"[AST JSON Decode Error]: Output is not valid JSON ({exc}). "
            f"Please output strictly a JSON object conforming to DeclareConstraintAST.",
        )
    except ValidationError as exc:
        error_details = "; ".join(
            f"field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}"
            for err in exc.errors()
        )
        return (
            False,
            f"[AST Schema Violation]: {error_details}",
        )


# Backward-compatible alias
validate_layer1_ast = validate_declare_ast
