"""
Bước 4.2: Dựng Cây Biện minh Tất định (Justification Tree) & Tập Sửa lỗi Tối thiểu (Minimal Correction - MCS)
Tham khảo:
- Repo xpSHACL (VLDB 2025, https://github.com/wimmics/xpshacl):
  Cấu trúc Cây biện minh tất định (Justification Tree) nối 3 nút:
  Điều khoản luật (Normative Node) <-> Công thức quy tắc (Symbolic Rule Node) <-> Bằng chứng sự kiện (Trace Evidence Node).
- Bài VERGE (arXiv:2601.20055) & pm4py:
  Tính toán độ lệch tối thiểu (Minimal Correction / Deviation Cost) — chỉ ra chính xác sự kiện bị thiếu,
  bị đảo thứ tự hoặc vượt ngưỡng bao nhiêu ngày/giờ/EUR.
"""

from typing import Any, Dict, Tuple
import pandas as pd


def check_single_trace_semantics(
    case_df: pd.DataFrame,
    ast_obj: Any,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Tính toán chi tiết bằng chứng tuân thủ/vi phạm và Minimal Correction (MCS - theo bài VERGE & xpSHACL).
    """
    case_df = case_df.sort_values("time:timestamp").reset_index(drop=True)
    tpl = ast_obj.template_name
    act_a = ast_obj.activation_activity
    act_b = ast_obj.target_activity

    events_a = case_df[case_df["concept:name"] == act_a]
    events_b = case_df[case_df["concept:name"] == act_b] if act_b else pd.DataFrame()

    # Trường hợp 1: Kiểm tra mẫu Precedence[A, B] (Nếu B xảy ra thì A phải xảy ra trước B)
    # Ví dụ: Điều 8(1) - Đánh giá tín dụng trước khi chấp thuận đề nghị vay, hoặc Điều 5(1) - Gửi thông tin trước khi chấp thuận
    if tpl in {"Precedence", "Alternate Precedence", "Chain Precedence"}:
        if events_b.empty:
            return True, {
                "msg": f"Hoạt động đích '{act_b}' không xảy ra, quy tắc {tpl} được bảo toàn."
            }

        first_b_time = events_b["time:timestamp"].iloc[0]
        prior_a = events_a[events_a["time:timestamp"] <= first_b_time]

        if prior_a.empty:
            # Kiểm tra xem A bị bỏ qua hoàn toàn (Missing) hay xảy ra muộn sau B (Out-of-order)
            if events_a.empty:
                return False, {
                    "violation_subtype": "MISSING_PREREQUISITE_ACTIVITY",
                    "target_event": {"activity": act_b, "timestamp": str(first_b_time)},
                    "missing_event": act_a,
                    "deviation_magnitude": f"Hoạt động tiền đề bắt buộc '{act_a}' hoàn toàn không xuất hiện trước '{act_b}'.",
                    "minimal_correction_mcs": f"Bắt buộc thực hiện '{act_a}' trước thời điểm {first_b_time}.",
                }
            else:
                late_a_time = events_a["time:timestamp"].iloc[0]
                delay_hours = round(
                    (late_a_time - first_b_time).total_seconds() / 3600.0, 2
                )
                return False, {
                    "violation_subtype": "TEMPORAL_ORDER_INVERSION",
                    "activation_event": {
                        "activity": act_a,
                        "timestamp": str(late_a_time),
                    },
                    "target_event": {
                        "activity": act_b,
                        "timestamp": str(first_b_time),
                    },
                    "deviation_magnitude": f"'{act_a}' diễn ra muộn hơn '{act_b}' {delay_hours} giờ.",
                    "minimal_correction_mcs": (
                        f"Đảo thứ tự thực thi: hoàn tất '{act_a}' trước '{act_b}' (trước {first_b_time})."
                    ),
                }

        # Kiểm tra giới hạn thời gian trên Precedence (nếu có time_max)
        t_a_valid = prior_a["time:timestamp"].iloc[-1]
        elapsed_days = (first_b_time - t_a_valid).total_seconds() / 86400.0
        if ast_obj.time_max is not None and elapsed_days > ast_obj.time_max:
            excess_days = round(elapsed_days - ast_obj.time_max, 2)
            return False, {
                "violation_subtype": "DEADLINE_EXCEEDED",
                "activation_event": {"activity": act_a, "timestamp": str(t_a_valid)},
                "target_event": {"activity": act_b, "timestamp": str(first_b_time)},
                "actual_duration_days": round(elapsed_days, 2),
                "allowed_max_days": ast_obj.time_max,
                "deviation_magnitude": f"Vượt quá thời hạn quy định {excess_days} ngày.",
                "minimal_correction_mcs": (
                    f"Rút ngắn khoảng cách thời gian giữa '{act_a}' và '{act_b}' tối thiểu {excess_days} ngày "
                    f"(về mức <= {ast_obj.time_max} ngày)."
                ),
            }

        dur_days = round(elapsed_days, 2)
        return True, {
            "msg": (
                f"Hoạt động tiền đề '{act_a}' ({t_a_valid}) đã diễn ra hợp lệ trước "
                f"'{act_b}' ({first_b_time}) (khoảng cách thời gian: {dur_days} ngày)."
            ),
            "activation_event": {"activity": act_a, "timestamp": str(t_a_valid)},
            "target_event": {"activity": act_b, "timestamp": str(first_b_time)},
            "actual_duration_days": dur_days,
        }

    # Trường hợp 2: Kiểm tra mẫu Response[A, B] kèm giới hạn thời gian time_max (ngày)
    # Ví dụ: Điều 14(1) - 14 ngày lịch rút lui hoặc Điều 14(3)(b) - 30 ngày lịch hoàn trả
    if tpl in {"Response", "Alternate Response", "Chain Response"}:
        if events_a.empty:
            return True, {
                "msg": f"Hoạt động kích hoạt '{act_a}' không xảy ra, quy tắc {tpl} được bảo toàn."
            }

        for _, row_a in events_a.iterrows():
            t_a = row_a["time:timestamp"]
            subsequent_b = events_b[events_b["time:timestamp"] >= t_a]

            if subsequent_b.empty:
                return False, {
                    "violation_subtype": "MISSING_TARGET_RESPONSE",
                    "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                    "missing_event": act_b,
                    "deviation_magnitude": f"Sự kiện kích hoạt '{act_a}' đã xảy ra lúc {t_a} nhưng thiếu sự kiện phản hồi '{act_b}'.",
                    "minimal_correction_mcs": f"Bổ sung hoạt động phản hồi '{act_b}' sau thời điểm {t_a}"
                    + (
                        f" trong vòng tối đa {ast_obj.time_max} ngày."
                        if ast_obj.time_max is not None
                        else "."
                    ),
                }

            t_b = subsequent_b["time:timestamp"].iloc[0]
            elapsed_days = (t_b - t_a).total_seconds() / 86400.0

            if ast_obj.time_max is not None and elapsed_days > ast_obj.time_max:
                excess_days = round(elapsed_days - ast_obj.time_max, 2)
                return False, {
                    "violation_subtype": "DEADLINE_EXCEEDED",
                    "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                    "target_event": {"activity": act_b, "timestamp": str(t_b)},
                    "actual_duration_days": round(elapsed_days, 2),
                    "allowed_max_days": ast_obj.time_max,
                    "deviation_magnitude": f"Vượt quá thời hạn quy định {excess_days} ngày.",
                    "minimal_correction_mcs": (
                        f"Rút ngắn thời gian thực hiện '{act_b}' tối thiểu {excess_days} ngày "
                        f"(về mức <= {ast_obj.time_max} ngày)."
                    ),
                }

        first_a_ts = events_a["time:timestamp"].iloc[0]
        first_b_ts = events_b[events_b["time:timestamp"] >= first_a_ts]["time:timestamp"].iloc[0]
        dur = round((first_b_ts - first_a_ts).total_seconds() / 86400.0, 2)
        return True, {
            "msg": f"Tất cả các sự kiện '{act_a}' đều được phản hồi bởi '{act_b}' đúng hạn ({dur} ngày).",
            "activation_event": {"activity": act_a, "timestamp": str(first_a_ts)},
            "target_event": {"activity": act_b, "timestamp": str(first_b_ts)},
            "actual_duration_days": dur,
        }

    return True, {"msg": "Tất cả các sự kiện trong hồ sơ thỏa mãn ràng buộc."}


def build_justification_tree(
    trace_eval: Dict[str, Any],
    ast_obj: Any,
    retrieved_chunk: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Đóng gói Cây biện minh tất định (Deterministic Justification Tree - theo mẫu xpSHACL)
    nối trực tiếp: Điều khoản Luật -> Công thức DECLARE -> Bằng chứng Sự kiện & MCS.
    """
    return {
        "audit_status": trace_eval["label"],  # ENTAILED / CONTRADICTED / BASELESS
        "reason_category": trace_eval["reason_type"],
        "normative_node": {
            "directive": "Directive 2008/48/EC",
            "article_id": retrieved_chunk["article_id"],
            "article_title": retrieved_chunk.get("article_title", ""),
            "verbatim_quote": retrieved_chunk["text"],
        },
        "symbolic_rule_node": {
            "declare_formula": ast_obj.to_declare4py_line() if ast_obj is not None else "N/A (Halted prior to execution)",
            "template": ast_obj.template_name if ast_obj is not None else "N/A",
        },
        "trace_evidence_node": {
            "case_id": trace_eval["case_id"],
            "proof_or_counterexample": trace_eval["details"],
        },
    }
