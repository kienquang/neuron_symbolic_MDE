"""
Bước 4.1: Kiểm tra Tập điều kiện An toàn Φ & Phân loại 3 Trạng thái (ENTAILED / CONTRADICTED / BASELESS)
Tham khảo:
- Bài OCL2026 (OVAS): Mục 3.4.2 – 3.4.3 (Value-Condition Separation <v, Φ> & Null-dereference safety guard)
- Bài RT4CHART (arXiv:2603.27752): Khung phân loại 3 trạng thái (ENTAILED, CONTRADICTED, BASELESS)
"""

from enum import Enum
import math
from typing import Any, Dict
import pandas as pd
from .justification_tree import check_single_trace_semantics, filter_activity_events


class ReasonType(str, Enum):
    UNSUPPORTED_BY_DIRECTIVE_TEXT = "UNSUPPORTED_BY_DIRECTIVE_TEXT"
    OUT_OF_DIRECTIVE_SCOPE = "OUT_OF_DIRECTIVE_SCOPE"
    UNSUPPORTED_NUMERIC_HALLUCINATION = "UNSUPPORTED_NUMERIC_HALLUCINATION"
    MISSING_LOG_EVIDENCE_PHI_VIOLATION = "MISSING_LOG_EVIDENCE_PHI_VIOLATION"
    INAPPLICABLE_TRACE_NO_ACTIVATION = "INAPPLICABLE_TRACE_NO_ACTIVATION"
    EMPTY_TRACE = "EMPTY_TRACE"
    ONE_SHOT_BINARY_CHECK = "ONE_SHOT_BINARY_CHECK"


def evaluate_trace_safety_and_status(
    case_df: pd.DataFrame,
    ast_obj: Any,
    roundtrip_passed: bool,
    roundtrip_msg: str,
) -> Dict[str, Any]:
    """
    Bước 4.1: Áp dụng cơ chế tách Giá trị - Điều kiện An toàn (Value-Condition Separation <v, Φ>)
    của OVAS kết hợp phân loại 3 trạng thái của RT4CHART trên từng hồ sơ vay (Trace).
    """
    if not isinstance(case_df, pd.DataFrame) or case_df.empty:
        return {
            "case_id": "UNKNOWN_CASE",
            "label": "BASELESS",
            "reason_type": ReasonType.EMPTY_TRACE.value,
            "details": "Hồ sơ vay rỗng hoặc không đúng định dạng DataFrame.",
        }

    case_id = str(case_df["case:concept:name"].iloc[0]) if "case:concept:name" in case_df.columns else "UNKNOWN_CASE"
    safety_conditions_phi = []  # Tập điều kiện an toàn Φ

    # 1. Kiểm tra bằng chứng văn bản luật (Text-level Evidence Sufficiency)
    if not roundtrip_passed:
        reason_type = ReasonType.UNSUPPORTED_BY_DIRECTIVE_TEXT.value
        if "OUT_OF_DIRECTIVE_SCOPE" in roundtrip_msg:
            reason_type = ReasonType.OUT_OF_DIRECTIVE_SCOPE.value
        elif "UNSUPPORTED_NUMERIC_HALLUCINATION" in roundtrip_msg:
            reason_type = ReasonType.UNSUPPORTED_NUMERIC_HALLUCINATION.value
        elif "MISSING_LOG_EVIDENCE_PHI_VIOLATION" in roundtrip_msg:
            reason_type = ReasonType.MISSING_LOG_EVIDENCE_PHI_VIOLATION.value
        return {
            "case_id": case_id,
            "label": "BASELESS",
            "reason_type": reason_type,
            "details": roundtrip_msg,
        }

    if ast_obj is None:
        return {
            "case_id": case_id,
            "label": "BASELESS",
            "reason_type": ReasonType.UNSUPPORTED_BY_DIRECTIVE_TEXT.value,
            "details": roundtrip_msg or "Không có AST hợp lệ để kiểm chứng.",
        }

    # 2. Kiểm tra sự tồn tại của thuộc tính trong lược đồ Log (VD: R27 EarlyRepaymentCompensationFee, R28 AnnualPercentageRateAPR)
    attrs_required = []
    if getattr(ast_obj, "activation_attr", None):
        attrs_required.append(ast_obj.activation_attr)
    if getattr(ast_obj, "target_attr", None):
        attrs_required.append(ast_obj.target_attr)

    for attr_col in attrs_required:
        alt_col = f"case:{attr_col}" if not attr_col.startswith("case:") else attr_col.replace("case:", "", 1)
        if attr_col not in case_df.columns and alt_col not in case_df.columns:
            return {
                "case_id": case_id,
                "label": "BASELESS",
                "reason_type": ReasonType.MISSING_LOG_EVIDENCE_PHI_VIOLATION.value,
                "details": (
                    f"Vi phạm Tập điều kiện an toàn Φ: Thuộc tính '{attr_col}' được yêu cầu bởi quy tắc "
                    f"nhưng hoàn toàn không tồn tại trong lược đồ nhật ký sự kiện BPIC 2017."
                ),
            }

    # 3. Kiểm tra sự tồn tại của sự kiện kích hoạt quy tắc trong hồ sơ (VD: R29)
    tpl = getattr(ast_obj, "template_name", "Response")
    act_events = filter_activity_events(case_df, getattr(ast_obj, "activation_activity", ""))
    tgt_events = (
        filter_activity_events(case_df, ast_obj.target_activity)
        if getattr(ast_obj, "target_activity", None)
        else pd.DataFrame()
    )

    if tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
        # Trong họ Precedence, sự kiện kích hoạt là target_activity B (mỗi khi B xảy ra)
        if tgt_events.empty:
            return {
                "case_id": case_id,
                "label": "BASELESS",
                "reason_type": ReasonType.INAPPLICABLE_TRACE_NO_ACTIVATION.value,
                "details": (
                    f"Hồ sơ '{case_id}' không phát sinh hoạt động kích hoạt '{ast_obj.target_activity}' "
                    f"của ràng buộc {tpl}."
                ),
            }
    elif tpl == "Not Co-Existence":
        if act_events.empty and tgt_events.empty:
            return {
                "case_id": case_id,
                "label": "BASELESS",
                "reason_type": ReasonType.INAPPLICABLE_TRACE_NO_ACTIVATION.value,
                "details": (
                    f"Hồ sơ '{case_id}' không phát sinh cả hai hoạt động '{ast_obj.activation_activity}' "
                    f"và '{ast_obj.target_activity}'."
                ),
            }
    else:
        if act_events.empty:
            return {
                "case_id": case_id,
                "label": "BASELESS",
                "reason_type": ReasonType.INAPPLICABLE_TRACE_NO_ACTIVATION.value,
                "details": f"Hồ sơ '{case_id}' không phát sinh hoạt động kích hoạt '{ast_obj.activation_activity}'.",
            }

    # 4. Kiểm tra Tập điều kiện an toàn Φ đối với thuộc tính dữ liệu và thời gian (Null-dereference guard - VD: R30)
    attrs_to_check = []
    if getattr(ast_obj, "activation_attr", None):
        attrs_to_check.append((ast_obj.activation_attr, act_events))
    if getattr(ast_obj, "target_attr", None):
        attrs_to_check.append((ast_obj.target_attr, tgt_events))

    for attr_col, ev_df in attrs_to_check:
        if ev_df.empty:
            continue
        for _, row in ev_df.iterrows():
            val = row.get(attr_col, None)
            if val is None and not attr_col.startswith("case:"):
                val = row.get(f"case:{attr_col}", None)
            if val is None or (isinstance(val, float) and math.isnan(val)) or pd.isna(val):
                safety_conditions_phi.append(
                    f"Thuộc tính '{attr_col}' tại sự kiện '{row['concept:name']}' bị khuyết (null/NaN)."
                )
                break

    events_to_check_ts = act_events if not act_events.empty else tgt_events
    for _, row in events_to_check_ts.iterrows():
        if pd.isna(row.get("time:timestamp")):
            safety_conditions_phi.append(
                f"Mốc thời gian 'time:timestamp' của '{row['concept:name']}' bị khuyết (null)."
            )
            break

    if safety_conditions_phi:
        return {
            "case_id": case_id,
            "label": "BASELESS",
            "reason_type": ReasonType.MISSING_LOG_EVIDENCE_PHI_VIOLATION.value,
            "details": "; ".join(safety_conditions_phi),
        }

    # 5. Nếu tập Φ hoàn toàn an toàn (đủ bằng chứng), đánh giá giá trị logic v (Entailed vs. Contradicted)
    is_compliant, deviation_info = check_single_trace_semantics(case_df, ast_obj)
    if is_compliant:
        return {
            "case_id": case_id,
            "label": "ENTAILED",
            "reason_type": "COMPLIANT_WITH_EVIDENCE",
            "details": deviation_info,
        }
    else:
        return {
            "case_id": case_id,
            "label": "CONTRADICTED",
            "reason_type": "PROCESS_COMPLIANCE_VIOLATION",
            "details": deviation_info,
        }
