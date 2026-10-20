"""
Bước 4.1: Kiểm tra Tập điều kiện An toàn Φ & Phân loại 3 Trạng thái (ENTAILED / CONTRADICTED / BASELESS)
Tham khảo:
- Bài OCL2026 (OVAS): Mục 3.4.2 – 3.4.3 (Value-Condition Separation <v, Φ> & Null-dereference safety guard)
- Bài RT4CHART (arXiv:2603.27752): Khung phân loại 3 trạng thái (ENTAILED, CONTRADICTED, BASELESS)
"""

import math
from typing import Any, Dict
import pandas as pd
from .justification_tree import check_single_trace_semantics, filter_activity_events


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
    if case_df.empty:
        return {
            "case_id": "UNKNOWN_CASE",
            "label": "BASELESS",
            "reason_type": "EMPTY_TRACE",
            "details": "Hồ sơ vay rỗng (không có sự kiện nào trong log).",
        }

    case_id = str(case_df["case:concept:name"].iloc[0])
    safety_conditions_phi = []  # Tập điều kiện an toàn Φ

    # 1. Kiểm tra bằng chứng văn bản luật (Text-level Evidence Sufficiency)
    if not roundtrip_passed:
        reason_type = "UNSUPPORTED_BY_DIRECTIVE_TEXT"
        if "OUT_OF_DIRECTIVE_SCOPE" in roundtrip_msg:
            reason_type = "OUT_OF_DIRECTIVE_SCOPE"
        elif "UNSUPPORTED_NUMERIC_HALLUCINATION" in roundtrip_msg:
            reason_type = "UNSUPPORTED_NUMERIC_HALLUCINATION"
        elif "MISSING_LOG_EVIDENCE_PHI_VIOLATION" in roundtrip_msg:
            reason_type = "MISSING_LOG_EVIDENCE_PHI_VIOLATION"
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
            "reason_type": "UNSUPPORTED_BY_DIRECTIVE_TEXT",
            "details": roundtrip_msg or "Không có AST hợp lệ để kiểm chứng.",
        }

    # 2. Kiểm tra sự tồn tại của thuộc tính trong lược đồ Log (VD: R27 EarlyRepaymentCompensationFee, R28 AnnualPercentageRateAPR)
    if getattr(ast_obj, "activation_attr", None):
        attr_col = ast_obj.activation_attr
        alt_col = f"case:{attr_col}" if not attr_col.startswith("case:") else attr_col.replace("case:", "", 1)
        if attr_col not in case_df.columns and alt_col not in case_df.columns:
            return {
                "case_id": case_id,
                "label": "BASELESS",
                "reason_type": "MISSING_LOG_EVIDENCE_PHI_VIOLATION",
                "details": (
                    f"Vi phạm Tập điều kiện an toàn Φ: Thuộc tính '{attr_col}' được yêu cầu bởi quy tắc "
                    f"nhưng hoàn toàn không tồn tại trong lược đồ nhật ký sự kiện BPIC 2017."
                ),
            }

    # 3. Kiểm tra sự tồn tại của sự kiện kích hoạt quy tắc trong hồ sơ (VD: R29)
    tpl = getattr(ast_obj, "template_name", "Response")
    act_events = filter_activity_events(case_df, ast_obj.activation_activity)
    tgt_events = (
        filter_activity_events(case_df, ast_obj.target_activity)
        if getattr(ast_obj, "target_activity", None)
        else pd.DataFrame()
    )

    if tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
        if tgt_events.empty and act_events.empty:
            return {
                "case_id": case_id,
                "label": "BASELESS",
                "reason_type": "INAPPLICABLE_TRACE_NO_ACTIVATION",
                "details": (
                    f"Hồ sơ '{case_id}' không phát sinh hoạt động kích hoạt '{ast_obj.target_activity}' "
                    f"lẫn hoạt động tiền đề '{ast_obj.activation_activity}'."
                ),
            }
        if tgt_events.empty and not ast_obj.activation_attr:
            return {
                "case_id": case_id,
                "label": "BASELESS",
                "reason_type": "INAPPLICABLE_TRACE_NO_ACTIVATION",
                "details": (
                    f"Hồ sơ '{case_id}' không phát sinh hoạt động mục tiêu '{ast_obj.target_activity}' "
                    f"của ràng buộc {tpl}."
                ),
            }
    elif tpl == "Not Co-Existence":
        if act_events.empty and tgt_events.empty:
            return {
                "case_id": case_id,
                "label": "BASELESS",
                "reason_type": "INAPPLICABLE_TRACE_NO_ACTIVATION",
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
                "reason_type": "INAPPLICABLE_TRACE_NO_ACTIVATION",
                "details": f"Hồ sơ '{case_id}' không phát sinh hoạt động kích hoạt '{ast_obj.activation_activity}'.",
            }

    # 4. Kiểm tra Tập điều kiện an toàn Φ đối với thuộc tính dữ liệu và thời gian (Null-dereference guard - VD: R30)
    events_for_phi = act_events if not act_events.empty else tgt_events
    if getattr(ast_obj, "activation_attr", None):
        attr_col = ast_obj.activation_attr
        for _, row in events_for_phi.iterrows():
            val = row.get(attr_col, None)
            if val is None and not attr_col.startswith("case:"):
                val = row.get(f"case:{attr_col}", None)
            if val is None or (isinstance(val, float) and math.isnan(val)) or pd.isna(val):
                safety_conditions_phi.append(
                    f"Thuộc tính '{attr_col}' tại sự kiện '{row['concept:name']}' bị khuyết (null/NaN)."
                )
                break

    for _, row in events_for_phi.iterrows():
        if pd.isna(row.get("time:timestamp")):
            safety_conditions_phi.append(
                f"Mốc thời gian 'time:timestamp' của '{row['concept:name']}' bị khuyết (null)."
            )
            break

    if safety_conditions_phi:
        return {
            "case_id": case_id,
            "label": "BASELESS",
            "reason_type": "MISSING_LOG_EVIDENCE_PHI_VIOLATION",
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
