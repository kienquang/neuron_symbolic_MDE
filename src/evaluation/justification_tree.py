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

from typing import Any, Dict, Optional, Tuple
import pandas as pd


DEFAULT_ACTIVITY_ALIASES: Dict[str, Any] = {
    "A_Validated": {"A_Validated", "A_Validating"},
    "A_Validating": {"A_Validated", "A_Validating"},
}
ACTIVITY_ALIASES = DEFAULT_ACTIVITY_ALIASES


def filter_activity_events(
    case_df: pd.DataFrame,
    act_name: Optional[str],
    aliases: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """Lọc các dòng sự kiện khớp với tên hoạt động (hỗ trợ đồng bộ bí danh hoạt động qua schema hoặc cấu hình)."""
    if not act_name:
        return pd.DataFrame()
    alias_map = aliases if aliases is not None else DEFAULT_ACTIVITY_ALIASES
    raw_equiv = alias_map.get(act_name, {act_name})
    if isinstance(raw_equiv, (list, tuple, set)):
        equivalent_names = set(raw_equiv) | {act_name}
    elif isinstance(raw_equiv, str):
        equivalent_names = {raw_equiv, act_name}
    else:
        equivalent_names = {act_name}
    return case_df[case_df["concept:name"].isin(equivalent_names)]


def evaluate_data_predicate(row: pd.Series, attr: str, op: str, expected_val: Any) -> Tuple[bool, Any]:
    """Đánh giá biểu thức điều kiện thuộc tính A.<attr> <op> <val> trên một dòng sự kiện."""
    actual = row.get(attr, None)
    if actual is None and not attr.startswith("case:"):
        actual = row.get(f"case:{attr}", None)
    if actual is None or pd.isna(actual):
        return False, None

    try:
        if isinstance(expected_val, (int, float)) and not isinstance(expected_val, bool):
            actual_num = float(actual)
            exp_num = float(expected_val)
            if op == ">=":
                return actual_num >= exp_num, actual_num
            if op == "<=":
                return actual_num <= exp_num, actual_num
            if op == ">":
                return actual_num > exp_num, actual_num
            if op == "<":
                return actual_num < exp_num, actual_num
            if op == "==":
                return actual_num == exp_num, actual_num
            if op == "!=":
                return actual_num != exp_num, actual_num
    except (ValueError, TypeError):
        pass

    actual_str = str(actual)
    exp_str = str(expected_val)
    if op == "==":
        return actual_str == exp_str, actual_str
    if op == "!=":
        return actual_str != exp_str, actual_str
    return False, actual


def check_single_trace_semantics(
    case_df: pd.DataFrame,
    ast_obj: Any,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Tính toán chi tiết bằng chứng tuân thủ/vi phạm và Minimal Correction (MCS - theo bài VERGE & xpSHACL)
    hỗ trợ đầy đủ 30 quy tắc chuẩn R01-R30 (Existence, Precedence, Chain Precedence, Response, Not Co-Existence).
    """
    case_df = case_df.sort_values("time:timestamp").reset_index(drop=True)
    tpl = ast_obj.template_name
    act_a = ast_obj.activation_activity
    act_b = ast_obj.target_activity

    events_a = filter_activity_events(case_df, act_a)
    events_b = filter_activity_events(case_df, act_b) if act_b else pd.DataFrame()

    # =========================================================================
    # Trường hợp 0: Kiểm tra mẫu Unary (Existence, Init, Exactly1) kèm điều kiện thuộc tính (R13, R14, R20, R21)
    # =========================================================================
    if tpl in {"Existence", "Init", "Exactly1"}:
        if events_a.empty:
            return False, {
                "violation_subtype": "MISSING_REQUIRED_ACTIVITY",
                "missing_event": act_a,
                "deviation_magnitude": f"Hoạt động bắt buộc '{act_a}' không xuất hiện trong hồ sơ.",
                "minimal_correction_mcs": f"Bổ sung sự kiện '{act_a}' vào quy trình xử lý hồ sơ.",
            }

        if ast_obj.activation_attr and ast_obj.activation_op is not None and ast_obj.activation_val is not None:
            attr = ast_obj.activation_attr
            op = ast_obj.activation_op
            val = ast_obj.activation_val
            last_actual = None
            for _, row_a in events_a.iterrows():
                ok_pred, actual_val = evaluate_data_predicate(row_a, attr, op, val)
                last_actual = actual_val
                if ok_pred:
                    return True, {
                        "msg": (
                            f"Sự kiện '{act_a}' thỏa mãn điều kiện '{attr} {op} {val}' "
                            f"(giá trị thực tế: {actual_val})."
                        ),
                        "activation_event": {
                            "activity": act_a,
                            "timestamp": str(row_a["time:timestamp"]),
                            attr: actual_val,
                        },
                    }

            return False, {
                "violation_subtype": "DATA_ATTRIBUTE_THRESHOLD_VIOLATION",
                "activation_event": {
                    "activity": act_a,
                    "timestamp": str(events_a["time:timestamp"].iloc[0]),
                    attr: last_actual,
                },
                "deviation_magnitude": (
                    f"Thuộc tính '{attr}' tại '{act_a}' có giá trị thực tế là {last_actual}, "
                    f"vi phạm ngưỡng quy định '{attr} {op} {val}'."
                ),
                "minimal_correction_mcs": (
                    f"Điều chỉnh giá trị '{attr}' tại '{act_a}' từ {last_actual} về ngưỡng thỏa mãn '{op} {val}'."
                ),
            }

        return True, {
            "msg": f"Sự kiện bắt buộc '{act_a}' đã xuất hiện hợp lệ trong hồ sơ.",
            "activation_event": {
                "activity": act_a,
                "timestamp": str(events_a["time:timestamp"].iloc[0]),
            },
        }

    # =========================================================================
    # Trường hợp 0B: Mẫu Absence, Choice, Exclusive Choice
    # =========================================================================
    if tpl == "Absence":
        if not events_a.empty:
            return False, {
                "violation_subtype": "FORBIDDEN_ACTIVITY_PRESENT",
                "activation_event": {
                    "activity": act_a,
                    "timestamp": str(events_a["time:timestamp"].iloc[0]),
                },
                "deviation_magnitude": f"Hoạt động bị cấm '{act_a}' xuất hiện {len(events_a)} lần trong hồ sơ.",
                "minimal_correction_mcs": f"Loại bỏ toàn bộ các sự kiện '{act_a}' khỏi hồ sơ xử lý.",
            }
        return True, {
            "msg": f"Hoạt động bị cấm '{act_a}' hoàn toàn không xuất hiện (tuân thủ Absence)."
        }

    if tpl == "Choice":
        if events_a.empty and events_b.empty:
            return False, {
                "violation_subtype": "MISSING_CHOICE_ACTIVITY",
                "deviation_magnitude": f"Cả hai hoạt động lựa chọn '{act_a}' và '{act_b}' đều không xuất hiện trong hồ sơ.",
                "minimal_correction_mcs": f"Bắt buộc thực hiện ít nhất một trong hai hoạt động '{act_a}' hoặc '{act_b}'.",
            }
        return True, {
            "msg": f"Đã thực hiện ít nhất một trong hai hoạt động lựa chọn '{act_a}' hoặc '{act_b}' (tuân thủ Choice)."
        }

    if tpl == "Exclusive Choice":
        has_a = not events_a.empty
        has_b = not events_b.empty
        if has_a and has_b:
            t_a = events_a["time:timestamp"].iloc[0]
            t_b = events_b["time:timestamp"].iloc[0]
            return False, {
                "violation_subtype": "EXCLUSIVE_CHOICE_CONFLICT",
                "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                "target_event": {"activity": act_b, "timestamp": str(t_b)},
                "deviation_magnitude": (
                    f"Cả hai hoạt động loại trừ lẫn nhau '{act_a}' ({t_a}) và '{act_b}' ({t_b}) cùng xuất hiện."
                ),
                "minimal_correction_mcs": f"Chỉ thực hiện chính xác một trong hai hoạt động '{act_a}' hoặc '{act_b}', loại bỏ hoạt động còn lại.",
            }
        if not has_a and not has_b:
            return False, {
                "violation_subtype": "EXCLUSIVE_CHOICE_OMISSION",
                "deviation_magnitude": f"Không có hoạt động nào trong cặp loại trừ '{act_a}' và '{act_b}' xuất hiện.",
                "minimal_correction_mcs": f"Bắt buộc thực hiện chính xác một trong hai hoạt động '{act_a}' hoặc '{act_b}'.",
            }
        return True, {
            "msg": f"Chính xác một trong hai hoạt động '{act_a}' hoặc '{act_b}' đã xuất hiện (tuân thủ Exclusive Choice)."
        }

    # =========================================================================
    # Trường hợp 1: Kiểm tra mẫu Phủ định (Negative templates) tách biệt ngữ nghĩa thời gian
    # =========================================================================
    if tpl in {"Not Co-Existence", "Not Responded Existence"}:
        if not events_a.empty and not events_b.empty:
            t_a = events_a["time:timestamp"].iloc[0]
            t_b = events_b["time:timestamp"].iloc[0]
            return False, {
                "violation_subtype": "MUTUAL_EXCLUSION_VIOLATION",
                "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                "target_event": {"activity": act_b, "timestamp": str(t_b)},
                "deviation_magnitude": (
                    f"Hai sự kiện xung đột '{act_a}' ({t_a}) và '{act_b}' ({t_b}) cùng xuất hiện trong một hồ sơ."
                ),
                "minimal_correction_mcs": (
                    f"Loại bỏ sự kiện xung đột '{act_b}' (lúc {t_b}) sau khi hồ sơ đã có '{act_a}'."
                ),
            }
        return True, {
            "msg": f"Hai sự kiện loại trừ '{act_a}' và '{act_b}' không cùng xảy ra trong hồ sơ (tuân thủ {tpl})."
        }

    if tpl == "Not Response":
        # B không được xuất hiện SAU A (nếu B xuất hiện TRƯỚC A thì vẫn hợp lệ)
        for _, row_a in events_a.iterrows():
            t_a = row_a["time:timestamp"]
            after_b = events_b[events_b["time:timestamp"] >= t_a]
            if not after_b.empty:
                t_b = after_b["time:timestamp"].iloc[0]
                return False, {
                    "violation_subtype": "NOT_RESPONSE_VIOLATION",
                    "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                    "target_event": {"activity": act_b, "timestamp": str(t_b)},
                    "deviation_magnitude": f"Sự kiện cấm '{act_b}' ({t_b}) xuất hiện sau khi '{act_a}' ({t_a}) đã diễn ra.",
                    "minimal_correction_mcs": f"Loại bỏ sự kiện phản hồi bị cấm '{act_b}' sau thời điểm {t_a}.",
                }
        return True, {
            "msg": f"Không có sự kiện '{act_b}' nào xảy ra sau '{act_a}' (tuân thủ Not Response)."
        }

    if tpl == "Not Precedence":
        # A không được xuất hiện TRƯỚC B
        for _, row_b in events_b.iterrows():
            t_b = row_b["time:timestamp"]
            before_a = events_a[events_a["time:timestamp"] <= t_b]
            if not before_a.empty:
                t_a = before_a["time:timestamp"].iloc[-1]
                return False, {
                    "violation_subtype": "NOT_PRECEDENCE_VIOLATION",
                    "activation_event": {"activity": act_b, "timestamp": str(t_b)},
                    "target_event": {"activity": act_a, "timestamp": str(t_a)},
                    "deviation_magnitude": f"Sự kiện cấm '{act_a}' ({t_a}) xuất hiện trước '{act_b}' ({t_b}).",
                    "minimal_correction_mcs": f"Loại bỏ sự kiện '{act_a}' xảy ra trước thời điểm {t_b}.",
                }
        return True, {
            "msg": f"Không có sự kiện '{act_a}' nào xảy ra trước '{act_b}' (tuân thủ Not Precedence)."
        }

    # =========================================================================
    # Trường hợp 2: Kiểm tra mẫu Precedence / Alternate Precedence / Chain Precedence (R01-R08, R12, R17, R18)
    # =========================================================================
    if tpl in {"Precedence", "Alternate Precedence", "Chain Precedence"}:
        if events_b.empty:
            return True, {
                "msg": f"Hoạt động đích '{act_b}' không xảy ra, quy tắc {tpl} được bảo toàn."
            }

        first_b_idx = events_b.index[0]
        first_b_time = events_b["time:timestamp"].iloc[0]
        prior_a = events_a[events_a["time:timestamp"] <= first_b_time]

        if prior_a.empty:
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

        # Kiểm tra riêng cho Chain Precedence[A, B] (R04: Ngay trước B phải là A)
        if tpl == "Chain Precedence" and first_b_idx > 0:
            prev_act = str(case_df.loc[first_b_idx - 1, "concept:name"])
            equiv_a = ACTIVITY_ALIASES.get(act_a, {act_a})
            if prev_act not in equiv_a:
                return False, {
                    "violation_subtype": "CHAIN_ADJACENCY_VIOLATION",
                    "activation_event": {"activity": act_a, "timestamp": str(prior_a["time:timestamp"].iloc[-1])},
                    "target_event": {"activity": act_b, "timestamp": str(first_b_time)},
                    "deviation_magnitude": (
                        f"Sự kiện ngay trước '{act_b}' là '{prev_act}' thay vì '{act_a}' (vi phạm Chain Precedence)."
                    ),
                    "minimal_correction_mcs": (
                        f"Đảm bảo '{act_a}' diễn ra liền kề ngay trước '{act_b}' mà không bị chèn bởi '{prev_act}'."
                    ),
                }

        # Kiểm tra điều kiện thuộc tính trên sự kiện tiền đề A nếu có (VD: R17 CreditScore > 0)
        if ast_obj.activation_attr and ast_obj.activation_op is not None and ast_obj.activation_val is not None:
            attr = ast_obj.activation_attr
            op = ast_obj.activation_op
            val = ast_obj.activation_val
            valid_prior_rows = []
            last_actual = None
            for _, row_a in prior_a.iterrows():
                ok_pred, actual_val = evaluate_data_predicate(row_a, attr, op, val)
                last_actual = actual_val
                if ok_pred:
                    valid_prior_rows.append(row_a)
            if not valid_prior_rows:
                return False, {
                    "violation_subtype": "DATA_ATTRIBUTE_THRESHOLD_VIOLATION",
                    "activation_event": {
                        "activity": act_a,
                        "timestamp": str(prior_a["time:timestamp"].iloc[-1]),
                        attr: last_actual,
                    },
                    "target_event": {"activity": act_b, "timestamp": str(first_b_time)},
                    "deviation_magnitude": (
                        f"Sự kiện tiền đề '{act_a}' xảy ra trước '{act_b}' nhưng giá trị '{attr}={last_actual}' "
                        f"không thỏa mãn điều kiện '{attr} {op} {val}'."
                    ),
                    "minimal_correction_mcs": (
                        f"Đảm bảo thuộc tính '{attr}' tại bước '{act_a}' thỏa mãn '{op} {val}' trước khi duyệt '{act_b}'."
                    ),
                }

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

    # =========================================================================
    # Trường hợp 3: Kiểm tra mẫu họ Response (Response, Chain Response, Alternate Response) (R09, R11, R15, R16, R19, R22)
    # =========================================================================
    if tpl in {"Response", "Alternate Response", "Chain Response"}:
        if events_a.empty:
            return True, {
                "msg": f"Hoạt động kích hoạt '{act_a}' không xảy ra, quy tắc {tpl} được bảo toàn."
            }

        # 3A. Kiểm tra riêng cho Chain Response[A, B]: B bắt buộc phải là sự kiện liền kề ngay sau A
        if tpl == "Chain Response":
            for idx in events_a.index:
                t_a = case_df.loc[idx, "time:timestamp"]
                if idx + 1 >= len(case_df):
                    return False, {
                        "violation_subtype": "CHAIN_RESPONSE_VIOLATION",
                        "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                        "missing_event": act_b,
                        "deviation_magnitude": f"Sự kiện '{act_a}' nằm ở cuối hồ sơ và thiếu sự kiện phản hồi liền kề '{act_b}'.",
                        "minimal_correction_mcs": f"Bổ sung hoạt động phản hồi '{act_b}' liền kề ngay sau '{act_a}'.",
                    }
                next_row = case_df.iloc[idx + 1]
                next_act = str(next_row["concept:name"])
                equiv_b = ACTIVITY_ALIASES.get(act_b, {act_b})
                if next_act != act_b and next_act not in equiv_b:
                    return False, {
                        "violation_subtype": "CHAIN_RESPONSE_VIOLATION",
                        "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                        "target_event": {"activity": next_act, "timestamp": str(next_row["time:timestamp"])},
                        "deviation_magnitude": f"Sự kiện ngay sau '{act_a}' là '{next_act}' thay vì '{act_b}' (vi phạm Chain Response).",
                        "minimal_correction_mcs": f"Đảm bảo '{act_b}' diễn ra liền kề ngay sau '{act_a}' mà không bị chèn bởi '{next_act}'.",
                    }

        # 3B. Kiểm tra riêng cho Alternate Response[A, B]: Sau mỗi A phải có B trước khi A khác lặp lại
        if tpl == "Alternate Response":
            for i in range(len(events_a)):
                t_a_curr = events_a["time:timestamp"].iloc[i]
                t_a_next = events_a["time:timestamp"].iloc[i + 1] if i + 1 < len(events_a) else None
                if t_a_next is not None:
                    inter_b = events_b[(events_b["time:timestamp"] >= t_a_curr) & (events_b["time:timestamp"] < t_a_next)]
                else:
                    inter_b = events_b[events_b["time:timestamp"] >= t_a_curr]
                if inter_b.empty:
                    return False, {
                        "violation_subtype": "ALTERNATE_RESPONSE_VIOLATION",
                        "activation_event": {"activity": act_a, "timestamp": str(t_a_curr)},
                        "missing_event": act_b,
                        "deviation_magnitude": f"Sự kiện '{act_a}' lặp lại nhưng thiếu sự kiện phản hồi '{act_b}' xen giữa (vi phạm Alternate Response).",
                        "minimal_correction_mcs": f"Hoàn tất hoạt động '{act_b}' trước khi kích hoạt lại '{act_a}'.",
                    }

        # 3C. Kiểm tra chung cho Response: Có B sau A trong khoảng thời gian quy định
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
                        f" trong vòng tối đa {ast_obj.time_max} {ast_obj.time_unit or 'ngày'}."
                        if ast_obj.time_max is not None
                        else "."
                    ),
                }

            t_b = subsequent_b["time:timestamp"].iloc[0]
            # Đảm bảo đơn điệu về thời gian: t_b >= t_a (không dùng abs)
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
                        f"(về mức <= {ast_obj.time_max} {ast_obj.time_unit or 'ngày'})."
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
