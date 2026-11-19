"""
Bước 2 (Kiến trúc Mới): Khung Pháp lý Chuẩn tắc (Deontic MDE Intermediate Model),
Giải mã Ép Văn phạm (Grammar-Constrained Decoding) & Neo Thực thể bằng Ma trận Hành vi (Behavioral Profile Grounding).

Thay thế vòng lặp bắt lỗi cú pháp/từ vựng Tầng 1 & Tầng 2 truyền thống bằng:
1. Khóa không gian sinh token (Literal Enum Schema) trực tiếp từ `process_schema.json`.
2. Phân tách Mô hình Chuẩn tắc Độc lập Nền tảng (Deontic PIM: Obligation, Prohibition, Permission, Exemption)
   và Biên dịch Tất định (Deterministic MDE Model-to-Model Compiler) sang `DeclareConstraintAST`.
3. Tự động chặn các điều khoản Miễn trừ (`EXEMPTION_OUT_OF_SCOPE`) và Thiếu thuộc tính Log (`UNMAPPED_MISSING_IN_LOG`)
   ngay tại thời điểm biên dịch (Zero-Retry).
4. Kiểm tra và neo cặp hoạt động dựa trên Ma trận Quan hệ Hành vi (`behavioral_profile` / DFG Transition Prior).
"""

import json
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union
from pydantic import BaseModel, Field, ValidationError, create_model

from src.mde.constraint_ast import (
    BINARY_TEMPLATES,
    UNARY_TEMPLATES,
    DeclareConstraintAST,
    extract_json_payload,
)
from src.mde.typing_environment import ProcessTypingEnvironment

UNMAPPED_ATTR_TOKEN = "UNMAPPED_MISSING_IN_LOG"

DeonticModalityLiteral = Literal[
    "OBLIGATION",
    "PROHIBITION",
    "PERMISSION_RIGHT",
    "EXEMPTION_OUT_OF_SCOPE",
]

DeonticTemporalRelationLiteral = Literal[
    "PREREQUISITE_BEFORE",      # A phải xảy ra trước khi B được phép xảy ra (Precedence)
    "IMMEDIATE_PREREQUISITE",   # A phải xảy ra ngay sát trước B (Chain Precedence)
    "MANDATORY_RESPONSE",       # Khi A xảy ra thì B bắt buộc phải xảy ra sau đó (Response)
    "IMMEDIATE_RESPONSE",       # Khi A xảy ra thì B phải xảy ra ngay lập tức sau đó (Chain Response)
    "MUTUAL_EXCLUSION",         # A và B cấm cùng tồn tại trong một hồ sơ (Not Co-Existence)
    "UNARY_CONDITION",          # Ràng buộc đơn ngôi trên hoạt động A kèm điều kiện thuộc tính (Existence / Absence)
]

GuardOperatorLiteral = Literal["==", "!=", "<", "<=", ">", ">="]


def build_constrained_deontic_schema(process_schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Tự động biên dịch `process_schema.json` thành Grammar-Constrained Pydantic Schema tại thời điểm chạy.
    Khóa cứng tập token hoạt động (`ValidActEnum`) và thuộc tính (`ValidAttrEnum`) ngay ở tầng Decoding.
    """
    valid_acts = list(process_schema.get("valid_activities", []))
    for alias in process_schema.get("activity_aliases", {}):
        if alias not in valid_acts:
            valid_acts.append(alias)
    if not valid_acts:
        valid_acts = ["A_Create Application"]

    all_attrs = (
        list(process_schema.get("case_attributes", {}).keys())
        + list(process_schema.get("event_attributes", {}).keys())
    )
    # Hỗ trợ cả tên rút gọn không có tiền tố "case:" cho các thuộc tính mức Case
    for k in list(process_schema.get("case_attributes", {}).keys()):
        short_k = k.replace("case:", "", 1)
        if short_k not in all_attrs:
            all_attrs.append(short_k)
    if UNMAPPED_ATTR_TOKEN not in all_attrs:
        all_attrs.append(UNMAPPED_ATTR_TOKEN)

    ValidActEnum = Literal[tuple(valid_acts)]  # type: ignore[valid-type]
    ValidAttrEnum = Literal[tuple(all_attrs)]  # type: ignore[valid-type]

    DeonticNormativeFrame = create_model(
        "DeonticNormativeFrame",
        article_id=(
            str,
            Field(description="Directive article reference, e.g., Article 8(1), Article 14(1)"),
        ),
        deontic_modality=(
            DeonticModalityLiteral,
            Field(
                description=(
                    "Deontic legal modality of the clause: "
                    "'OBLIGATION' (mandatory requirement - shall/must), "
                    "'PROHIBITION' (forbidden action - shall not/forbidden), "
                    "'PERMISSION_RIGHT' (time-bounded right - may/right to withdraw), "
                    "or 'EXEMPTION_OUT_OF_SCOPE' (statutory scope exclusion - shall not apply)"
                )
            ),
        ),
        temporal_relation=(
            DeonticTemporalRelationLiteral,
            Field(
                description=(
                    "Temporal relation between process activities: "
                    "'PREREQUISITE_BEFORE' (Precedence: A must be completed before B), "
                    "'IMMEDIATE_PREREQUISITE' (Chain Precedence: A must occur immediately before B), "
                    "'MANDATORY_RESPONSE' (Response: A triggers an obligation to execute B afterwards), "
                    "'IMMEDIATE_RESPONSE' (Chain Response: A must be followed immediately by B as next step), "
                    "'MUTUAL_EXCLUSION' (Not Co-Existence: A and B cannot co-occur in the same case), "
                    "'UNARY_CONDITION' (Existence/Absence: unary attribute constraint on activity A)"
                )
            ),
        ),
        anchor_activity=(
            ValidActEnum,
            Field(description="First activity (A - Prerequisite or Activation activity)"),
        ),
        consequent_activity=(
            Optional[ValidActEnum],
            Field(default=None, description="Second activity (B - Consequent or Target activity; None if UNARY_CONDITION)"),
        ),
        attribute_guard=(
            Optional[ValidAttrEnum],
            Field(
                default=None,
                description=(
                    "Data attribute to check against a threshold (or 'UNMAPPED_MISSING_IN_LOG' "
                    "if the clause requires an attribute absent from the event log schema)"
                ),
            ),
        ),
        guard_operator=(
            Optional[GuardOperatorLiteral],
            Field(default=None, description="Comparison operator for the attribute guard (==, !=, <, <=, >, >=)"),
        ),
        guard_threshold=(
            Optional[Union[float, int, str, bool]],
            Field(default=None, description="Threshold value for the attribute guard condition"),
        ),
        deadline_days=(
            Optional[int],
            Field(default=None, description="Maximum time window in calendar days (if specified by the legal clause)"),
        ),
        unsupported_by_text=(
            bool,
            Field(
                default=False,
                description="True if the legal clause text contains no enforceable process obligation or required bound",
            ),
        ),
    )
    return DeonticNormativeFrame


def format_behavioral_profile_for_prompt(
    process_schema: Dict[str, Any],
    top_k: int = 110,
) -> str:
    """
    Trích xuất tóm tắt Ma trận Quan hệ Hành vi (Behavioral Profile / DFG Structural Prior)
    từ `process_schema.json` để làm ngữ cảnh neo thực thể cho LLM.
    """
    bp = process_schema.get("behavioral_profile", {})
    causal_pairs = bp.get("strict_causal_pairs", [])
    mutex_pairs = bp.get("mutually_exclusive_pairs", [])

    lines: List[str] = []
    if causal_pairs:
        lines.append(
            "Empirical Process Behavioral Profile (Prefixes: A_*=Application milestone, O_*=Offer event, "
            "W_*=repeatable human work-item w/ inflated DFG loops; DFG=Direct-Follows, EF=Eventually-Follows):"
        )
        for p in causal_pairs[:top_k]:
            direct_cnt = p.get("direct_dfg_count", 0)
            direct_tag = f"DFG:{direct_cnt}" if direct_cnt > 0 else "EF"
            lines.append(
                f"- {p['from']} -> {p['to']} ({p['order_ratio']:.0%},{direct_tag})"
            )
    elif process_schema.get("frequent_transitions"):
        lines.append("Frequent Directly-Follows Transitions (A -> B) in Event Log:")
        for t in process_schema["frequent_transitions"][:top_k]:
            lines.append(f"  - {t['from']} -> {t['to']} ({t['count']} transitions)")

    if mutex_pairs:
        mutex_strs = [f"({m['act_a']}, {m['act_b']})" for m in mutex_pairs[:8]]
        lines.append(f"Mutually Exclusive Activity Pairs in Event Log (Co-occurrence <= 1%): {', '.join(mutex_strs)}")

    return "\n".join(lines)


def check_behavioral_profile_grounding(
    ast_obj: DeclareConstraintAST,
    process_schema: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra tính neo thực thể hành vi (Behavioral Profile Grounding) cho cặp hoạt động (A, B):
    - Nếu chọn 'Chain Precedence' hoặc 'Chain Response', cặp (A, B) bắt buộc phải có chuyển tiếp trực tiếp (Direct DFG > 0)
      trong nhật ký sự kiện.
    """
    if ast_obj.template_name not in ("Chain Precedence", "Chain Response"):
        return True, None

    act_a = ast_obj.activation_activity
    act_b = ast_obj.target_activity
    if not act_b:
        return True, None

    # Kiểm tra trong frequent_transitions và behavioral_profile
    freq_trans = process_schema.get("frequent_transitions", [])
    bp_pairs = process_schema.get("behavioral_profile", {}).get("strict_causal_pairs", [])

    # Nếu lược đồ không chứa dữ liệu DFG (ví dụ trong mock test nhỏ), bỏ qua kiểm tra DFG
    if not freq_trans and not bp_pairs:
        return True, None

    has_direct = any(
        t.get("from") == act_a and t.get("to") == act_b and t.get("count", 0) > 0
        for t in freq_trans
    ) or any(
        p.get("from") == act_a and p.get("to") == act_b and p.get("direct_dfg_count", 0) > 0
        for p in bp_pairs
    )

    if not has_direct:
        return (
            False,
            f"Behavioral Profile Grounding Violation: Template '{ast_obj.template_name}' requires direct adjacency "
            f"(Directly-Follows > 0) between '{act_a}' and '{act_b}', but they are not directly adjacent in the DFG. "
            f"Use 'Precedence' or 'Response' instead, or select a directly adjacent pair.",
        )

    return True, None


def compile_deontic_to_declare4py(
    frame_dict: Dict[str, Any],
    process_schema: Optional[Dict[str, Any]] = None,
    retrieved_chunk: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Union[Dict[str, Any], str]]:
    """
    Bộ biên dịch MDE Tất định (Deterministic Model-to-Model Compiler):
    Chuyển đổi Khung Chuẩn tắc (`DeonticNormativeFrame`) sang công thức `DeclareConstraintAST` / Declare4Py
    mà không để LLM tự viết cú pháp DECLARE.

    Trả về:
      - ("BASELESS_OR_EXEMPT", diagnostic_reason) nếu là điều khoản Miễn trừ hoặc Không có căn cứ.
      - ("BASELESS_MISSING_ATTR", diagnostic_reason) nếu yêu cầu thuộc tính ngoài lược đồ Log (vi phạm Φ).
      - ("COMPILE_ERROR", diagnostic_error) nếu vi phạm ràng buộc phụ thuộc chéo (Self-loop, Arity, Type Conformance).
      - ("COMPILED_OK", compiled_dict) nếu biên dịch thành công.
    """
    # 1. Kiểm tra cờ Miễn trừ Phạm vi (Statutory Exemption) hoặc Không có căn cứ
    baseless_status: Optional[str] = None
    baseless_reason: Optional[str] = None

    raw_guard_val = frame_dict.get("guard_threshold")

    if frame_dict.get("deontic_modality") == "EXEMPTION_OUT_OF_SCOPE" or frame_dict.get("unsupported_by_text") is True:
        baseless_status = "BASELESS_OR_EXEMPT"
        baseless_reason = (
            f"[Layer 3 Semantic BASELESS]: [Deontic MDE Compiler -> OUT_OF_DIRECTIVE_SCOPE]: "
            f"Clause '{frame_dict.get('article_id', '')}' is classified as a statutory exemption "
            f"('shall not apply' / out-of-scope) or contains no enforceable process obligation."
        )

    # 2. Kiểm tra thuộc tính thiếu trong Metamodel Γ TRƯỚC khi kiểm tra tính toàn vẹn bộ ba điều kiện thuộc tính
    attr_guard = frame_dict.get("attribute_guard")
    guard_op_raw = frame_dict.get("guard_operator")
    if attr_guard == UNMAPPED_ATTR_TOKEN:
        if baseless_status is None and guard_op_raw is None and raw_guard_val is None:
            return (
                "COMPILE_ERROR",
                "[Deontic MDE Structural Error]: 'attribute_guard=UNMAPPED_MISSING_IN_LOG' was set without "
                "'guard_operator' or 'guard_threshold'. For pure ordering or deadline rules that do not check "
                "a data attribute threshold, set attribute_guard=null; only use 'UNMAPPED_MISSING_IN_LOG' paired "
                "with 'guard_operator' and 'guard_threshold' when enforcing a numeric/data metric absent from the schema.",
            )
        baseless_status = "BASELESS_MISSING_ATTR"
        baseless_reason = (
            f"[Layer 3 Semantic BASELESS]: [Deontic MDE Compiler -> MISSING_LOG_EVIDENCE_PHI_VIOLATION]: "
            f"Clause '{frame_dict.get('article_id', '')}' requires a quantitative metric/attribute that is absent from "
            f"the Process Metamodel Γ (UNMAPPED_MISSING_IN_LOG)."
        )

    attr_triplet = [attr_guard is not None, guard_op_raw is not None, raw_guard_val is not None]
    if baseless_status is None and any(attr_triplet) and not all(attr_triplet):
        return (
            "COMPILE_ERROR",
            "[Deontic MDE Structural Error]: Data guard condition requires all three fields "
            "('attribute_guard', 'guard_operator', 'guard_threshold') to be set together, or all set to null.",
        )

    deadline_val = frame_dict.get("deadline_days")
    if deadline_val is not None:
        try:
            if int(deadline_val) <= 0:
                return (
                    "COMPILE_ERROR",
                    "[Deontic MDE Compiler Error]: deadline_days must be a positive integer (> 0) or null if no calendar-day deadline is specified.",
                )
        except (ValueError, TypeError):
            return "COMPILE_ERROR", f"[Deontic MDE Compiler Error]: Invalid deadline_days '{deadline_val}'."

    # 3. Ánh xạ tất định từ (deontic_modality, temporal_relation) sang Template của Declare4Py
    raw_rel = frame_dict.get("temporal_relation")
    modality = frame_dict.get("deontic_modality", "OBLIGATION")

    # Nếu mô hình trả về EXEMPTION_OUT_OF_SCOPE hoặc khung BASELESS với temporal_relation=None/rỗng/omitted,
    # chuẩn hóa về UNARY_CONDITION để biên dịch an toàn thành AST Exemption thay vì CRASH Round 1.
    # Riêng các lỗi schema thực sự như OBLIGATION với chuỗi rác "None" vẫn bị từ chối COMPILE_ERROR.
    if "temporal_relation" not in frame_dict:
        rel = "UNARY_CONDITION" if baseless_status is not None else "PREREQUISITE_BEFORE"
    elif (raw_rel is None or (isinstance(raw_rel, str) and not raw_rel.strip())) and (
        modality == "EXEMPTION_OUT_OF_SCOPE" or baseless_status is not None
    ):
        rel = "UNARY_CONDITION"
    elif modality == "EXEMPTION_OUT_OF_SCOPE" and str(raw_rel).strip().lower() in ("none", "null", "n/a"):
        rel = "UNARY_CONDITION"
    else:
        rel = raw_rel

    rel_to_template = {
        "PREREQUISITE_BEFORE": "Precedence",
        "IMMEDIATE_PREREQUISITE": "Chain Precedence",
        "MANDATORY_RESPONSE": "Response",
        "IMMEDIATE_RESPONSE": "Chain Response",
        "MUTUAL_EXCLUSION": "Not Co-Existence",
        "UNARY_CONDITION": "Existence",
    }
    if rel not in rel_to_template:
        return "COMPILE_ERROR", f"[Deontic MDE Compiler Error]: Unknown temporal_relation '{rel}'."

    tpl = rel_to_template[rel]

    # Xử lý chuẩn xác ngữ nghĩa CẤM ĐOÁN (PROHIBITION):
    if modality == "PROHIBITION":
        if tpl == "Existence":
            tpl = "Absence"
        elif tpl == "Response":
            tpl = "Not Response"
        elif tpl == "Precedence":
            tpl = "Not Precedence"
        elif tpl in ("Chain Precedence", "Chain Response"):
            if baseless_status is not None:
                tpl = "Absence"
            else:
                return (
                    "COMPILE_ERROR",
                    "[Deontic MDE Compiler Error]: PROHIBITION modality is incompatible with "
                    f"{rel} (use PREREQUISITE_BEFORE, MANDATORY_RESPONSE, MUTUAL_EXCLUSION, or UNARY_CONDITION).",
                )

    act_a = frame_dict.get("anchor_activity")
    act_b = frame_dict.get("consequent_activity")

    # Nếu là khung BASELESS/EXEMPT và thiếu act_b (hoặc tự lặp), chuẩn hóa an toàn về Existence đơn ngôi
    # (giữ nguyên act_a=None -> "None" để không tự hợp thức hóa Raw_Log_Executable_Rate cho điều khoản miễn trừ)
    if baseless_status is not None and (not act_b or act_b == act_a):
        tpl = "Existence"
        act_b = None
    if baseless_status is not None and act_a == "":
        act_a = None

    # Chuẩn hóa arity nếu là UNARY_CONDITION
    if tpl in UNARY_TEMPLATES:
        act_b = None

    guard_op = frame_dict.get("guard_operator") if attr_guard else None
    guard_val = frame_dict.get("guard_threshold") if attr_guard else None
    deadline_days = frame_dict.get("deadline_days")
    has_complete_guard = attr_guard is not None and guard_op is not None and guard_val is not None

    # Kiểm tra cấu trúc AST qua DeclareConstraintAST
    # (Với khung BASELESS/EXEMPT chưa đủ bộ ba thuộc tính, vẫn dựng AST an toàn để truyền baseless_reason sang Layer 3)
    try:
        ast_obj = DeclareConstraintAST(
            article_id=str(frame_dict.get("article_id", "")),
            template_name=tpl,  # type: ignore[arg-type]
            activation_activity=str(act_a),
            target_activity=str(act_b) if act_b else None,
            activation_attr=str(attr_guard) if (has_complete_guard or baseless_status is None) and attr_guard else None,
            activation_op=guard_op if (has_complete_guard or baseless_status is None) else None,
            activation_val=guard_val if (has_complete_guard or baseless_status is None) else None,
            time_min=0 if deadline_days is not None else None,
            time_max=int(deadline_days) if deadline_days is not None else None,
            time_unit="d" if deadline_days is not None else None,
        )
    except ValidationError as exc:
        err_msg = "; ".join(f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors())
        return "COMPILE_ERROR", f"[Deontic MDE Structural Error]: {err_msg}"

    # 4. Nếu có process_schema: Kiểm tra Attribute-Grammar (Self-loop, Type Conformance, Behavioral Grounding)
    if process_schema is not None and baseless_status is None:
        gamma = ProcessTypingEnvironment(process_schema)
        ok_l2, l2_err = gamma.validate_ast(ast_obj, retrieved_chunk=retrieved_chunk)
        if not ok_l2:
            return "COMPILE_ERROR", str(l2_err)

        ok_bp, bp_err = check_behavioral_profile_grounding(ast_obj, process_schema)
        if not ok_bp:
            return "COMPILE_ERROR", str(bp_err)

        if ast_obj.activation_attr is not None:
            raw_attr = ast_obj.activation_attr.strip()
            if raw_attr.startswith(("A.", "T.", "a.", "t.")):
                ast_obj = ast_obj.model_copy(update={"activation_attr": raw_attr[2:]})

    decl_line = ast_obj.to_declare4py_line()
    compiled_payload: Dict[str, Any] = {
        **ast_obj.model_dump(),
        "decl_line": decl_line,
        "deontic_modality": modality,
        "temporal_relation": rel,
        "deontic_status": baseless_status or "COMPILED_OK",
        "deontic_baseless_reason": baseless_reason,
    }
    if baseless_status is not None:
        return baseless_status, compiled_payload
    return "COMPILED_OK", compiled_payload


def validate_and_compile_deontic_or_ast(
    raw_response: Union[str, Dict[str, Any]],
    process_schema: Dict[str, Any],
    retrieved_chunk: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    Hàm tích hợp hỗ trợ đồng thời cả 2 định dạng đầu ra:
      1. Định dạng mới `DeonticNormativeFrame` (có `deontic_modality`, `temporal_relation`, `anchor_activity`).
      2. Định dạng `DeclareConstraintAST` (có `template_name`, `activation_activity`) để tương thích ngược 100%
         với toàn bộ dữ liệu cache và bộ kiểm thử hiện có.
    """
    try:
        if isinstance(raw_response, str):
            clean_json = extract_json_payload(raw_response)
            data = json.loads(clean_json)
        elif isinstance(raw_response, dict):
            data = raw_response
        else:
            return False, f"[Layer 1 Syntax Error]: Unsupported payload type {type(raw_response).__name__}."
    except json.JSONDecodeError as exc:
        return False, f"[Layer 1 JSON Decode Error]: Output is not valid JSON ({exc})."

    # Trường hợp 1: Đầu ra là DeonticNormativeFrame
    if "deontic_modality" in data or "anchor_activity" in data or "temporal_relation" in data:
        # Nếu chưa phải trường hợp miễn trừ/missing attr thì kiểm tra schema DeonticNormativeFrame
        if not data.get("unsupported_by_text") and data.get("deontic_modality") != "EXEMPTION_OUT_OF_SCOPE":
            if data.get("attribute_guard") != UNMAPPED_ATTR_TOKEN:
                DeonticSchemaCls = build_constrained_deontic_schema(process_schema)
                try:
                    validated_frame = DeonticSchemaCls.model_validate(data)
                    data = validated_frame.model_dump()
                except ValidationError as exc:
                    error_details = "; ".join(
                        f"field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}"
                        for err in exc.errors()
                    )
                    return False, f"[Deontic Grammar-Constrained Schema Violation]: {error_details}"

        status, result = compile_deontic_to_declare4py(
            data, process_schema=process_schema, retrieved_chunk=retrieved_chunk
        )
        if status in ("COMPILED_OK", "BASELESS_OR_EXEMPT", "BASELESS_MISSING_ATTR"):
            assert isinstance(result, dict)
            return True, result
        return False, str(result)

    # Trường hợp 2: Đầu ra là DeclareConstraintAST (tương thích ngược)
    from src.mde.typing_environment import check_layer1_and_layer2 as _legacy_check_l1_l2

    ok_l12, res_l12 = _legacy_check_l1_l2(data, process_schema, retrieved_chunk)
    if not ok_l12:
        return False, str(res_l12)

    assert isinstance(res_l12, DeclareConstraintAST)
    ok_bp, bp_err = check_behavioral_profile_grounding(res_l12, process_schema)
    if not ok_bp:
        return False, f"- [Layer 2 Static Error]: {bp_err}"

    return True, res_l12.model_dump()
