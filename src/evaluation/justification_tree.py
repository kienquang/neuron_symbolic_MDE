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


DEFAULT_ACTIVITY_ALIASES: Dict[str, Any] = {}
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
    elif actual is None and attr.startswith("case:"):
        actual = row.get(attr.replace("case:", "", 1), None)
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


def _allowed_days(ast_obj: Any) -> Optional[float]:
    t_max = getattr(ast_obj, "time_max", None)
    if t_max is None:
        return None
    u = str(getattr(ast_obj, "time_unit", None) or "d").strip().lower()
    scale = {
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
    }.get(u, 1.0)
    return float(t_max) * scale


def _filter_by_activation_predicate(events_df: pd.DataFrame, ast_obj: Any) -> pd.DataFrame:
    if events_df.empty:
        return events_df
    attr = getattr(ast_obj, "activation_attr", None)
    op = getattr(ast_obj, "activation_op", None)
    val = getattr(ast_obj, "activation_val", None)
    if not (attr and op is not None and val is not None):
        return events_df
    mask = [evaluate_data_predicate(row, attr, op, val)[0] for _, row in events_df.iterrows()]
    return events_df[mask]


def check_single_trace_semantics(
    case_df: pd.DataFrame,
    ast_obj: Any,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Tính toán chi tiết bằng chứng tuân thủ/vi phạm và Minimal Correction (MCS - theo bài VERGE & xpSHACL)
    hỗ trợ đầy đủ 30 quy tắc chuẩn R01-R30 (Existence, Precedence, Chain Precedence, Response, Not Co-Existence).
    """
    case_df = case_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
    tpl = ast_obj.template_name
    act_a = ast_obj.activation_activity
    act_b = ast_obj.target_activity

    events_a = filter_activity_events(case_df, act_a)
    events_b = filter_activity_events(case_df, act_b) if act_b else pd.DataFrame()

    has_attr_cond = bool(
        ast_obj.activation_attr and ast_obj.activation_op is not None and ast_obj.activation_val is not None
    )
    valid_events_a = _filter_by_activation_predicate(events_a, ast_obj) if has_attr_cond else events_a
    allowed_days = _allowed_days(ast_obj)
    unit_norm = str(getattr(ast_obj, "time_unit", None) or "d").strip().lower()
    allowed_days_disp = (
        ast_obj.time_max
        if (allowed_days is not None and unit_norm in {"d", "day", "days"})
        else (round(allowed_days, 4) if allowed_days is not None else None)
    )

    # =========================================================================
    # Trường hợp 0: Kiểm tra mẫu Unary (Existence, Init, Exactly1) kèm điều kiện thuộc tính
    # =========================================================================
    if tpl in {"Existence", "Init", "Exactly1"}:
        if events_a.empty:
            return False, {
                "violation_subtype": "MISSING_REQUIRED_ACTIVITY",
                "missing_event": act_a,
                "deviation_magnitude": f"Hoạt động bắt buộc '{act_a}' không xuất hiện trong hồ sơ.",
                "minimal_correction_mcs": f"Bổ sung sự kiện '{act_a}' vào quy trình xử lý hồ sơ.",
            }

        if tpl == "Init":
            first_row = case_df.iloc[0]
            if 0 not in events_a.index:
                return False, {
                    "violation_subtype": "TEMPORAL_ORDER_INVERSION",
                    "activation_event": {"activity": str(first_row["concept:name"]), "timestamp": str(first_row["time:timestamp"])},
                    "missing_event": act_a,
                    "deviation_magnitude": f"Hồ sơ bắt đầu bằng '{first_row['concept:name']}' thay vì '{act_a}'.",
                    "minimal_correction_mcs": f"Đảm bảo '{act_a}' là sự kiện đầu tiên của hồ sơ.",
                }
            if has_attr_cond and 0 not in valid_events_a.index:
                attr, op, val = ast_obj.activation_attr, ast_obj.activation_op, ast_obj.activation_val
                _, actual_val = evaluate_data_predicate(first_row, attr, op, val)
                return False, {
                    "violation_subtype": "DATA_ATTRIBUTE_THRESHOLD_VIOLATION",
                    "activation_event": {"activity": act_a, "timestamp": str(first_row["time:timestamp"]), attr: actual_val},
                    "deviation_magnitude": f"Thuộc tính '{attr}' tại sự kiện khởi tạo '{act_a}' là {actual_val}, vi phạm '{attr} {op} {val}'.",
                    "minimal_correction_mcs": f"Điều chỉnh giá trị '{attr}' tại '{act_a}' về ngưỡng '{op} {val}'.",
                }
            return True, {
                "msg": f"Sự kiện '{act_a}' là sự kiện khởi tạo hợp lệ của hồ sơ.",
                "activation_event": {"activity": act_a, "timestamp": str(first_row["time:timestamp"])},
            }

        if tpl == "Exactly1":
            if len(valid_events_a) != 1:
                if has_attr_cond and len(valid_events_a) == 0:
                    attr, op, val = ast_obj.activation_attr, ast_obj.activation_op, ast_obj.activation_val
                    _, last_actual = evaluate_data_predicate(events_a.iloc[-1], attr, op, val)
                    return False, {
                        "violation_subtype": "DATA_ATTRIBUTE_THRESHOLD_VIOLATION",
                        "activation_event": {"activity": act_a, "timestamp": str(events_a["time:timestamp"].iloc[0]), attr: last_actual},
                        "deviation_magnitude": f"Không có sự kiện '{act_a}' nào thỏa điều kiện '{attr} {op} {val}' (giá trị gần nhất: {last_actual}).",
                        "minimal_correction_mcs": f"Điều chỉnh để có đúng 1 sự kiện '{act_a}' thỏa '{attr} {op} {val}'.",
                    }
                return False, {
                    "violation_subtype": "EXACTLY1_CARDINALITY_VIOLATION",
                    "activation_event": {"activity": act_a, "timestamp": str(valid_events_a["time:timestamp"].iloc[0])},
                    "deviation_magnitude": f"Hoạt động '{act_a}' xuất hiện hợp lệ {len(valid_events_a)} lần (yêu cầu đúng 1 lần).",
                    "minimal_correction_mcs": f"Điều chỉnh để hoạt động '{act_a}' chỉ xảy ra chính xác 1 lần.",
                }
            row_one = valid_events_a.iloc[0]
            return True, {
                "msg": f"Sự kiện '{act_a}' xuất hiện chính xác 1 lần hợp lệ trong hồ sơ.",
                "activation_event": {"activity": act_a, "timestamp": str(row_one["time:timestamp"])},
            }

        if has_attr_cond:
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
        attr = ast_obj.activation_attr
        op = ast_obj.activation_op
        val = ast_obj.activation_val
        if attr and op is not None and val is not None:
            forbidden_events = []
            for _, row in events_a.iterrows():
                ok_pred, actual_val = evaluate_data_predicate(row, attr, op, val)
                if ok_pred:
                    forbidden_events.append((row, actual_val))
            if forbidden_events:
                bad_ev, act_val = forbidden_events[0]
                return False, {
                    "violation_subtype": "DATA_ATTRIBUTE_THRESHOLD_VIOLATION",
                    "activation_event": {
                        "activity": act_a,
                        "timestamp": str(bad_ev["time:timestamp"]),
                        attr: act_val,
                    },
                    "deviation_magnitude": (
                        f"Sự kiện '{act_a}' xuất hiện với {attr} = {act_val} thỏa mãn điều kiện bị cấm '{attr} {op} {val}'."
                    ),
                    "minimal_correction_mcs": (
                        f"Không tạo sự kiện '{act_a}' có {attr} {op} {val}."
                    ),
                }
            return True, {
                "msg": f"Không có sự kiện '{act_a}' nào có {attr} {op} {val} (tuân thủ Absence có điều kiện dữ liệu)."
            }
        else:
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
        has_a = not valid_events_a.empty
        has_b = not events_b.empty
        if not has_a and not has_b:
            return False, {
                "violation_subtype": "MISSING_CHOICE_ACTIVITY",
                "deviation_magnitude": f"Cả hai hoạt động lựa chọn '{act_a}' và '{act_b}' đều không xuất hiện hợp lệ trong hồ sơ.",
                "minimal_correction_mcs": f"Bắt buộc thực hiện ít nhất một trong hai hoạt động '{act_a}' hoặc '{act_b}'.",
            }
        return True, {
            "msg": f"Đã thực hiện ít nhất một trong hai hoạt động lựa chọn '{act_a}' hoặc '{act_b}' (tuân thủ Choice)."
        }

    if tpl == "Exclusive Choice":
        has_a = not valid_events_a.empty
        has_b = not events_b.empty
        if has_a and has_b:
            t_a = valid_events_a["time:timestamp"].iloc[0]
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
                "deviation_magnitude": f"Không có hoạt động nào trong cặp loại trừ '{act_a}' và '{act_b}' xuất hiện hợp lệ.",
                "minimal_correction_mcs": f"Bắt buộc thực hiện chính xác một trong hai hoạt động '{act_a}' hoặc '{act_b}'.",
            }
        return True, {
            "msg": f"Chính xác một trong hai hoạt động '{act_a}' hoặc '{act_b}' đã xuất hiện (tuân thủ Exclusive Choice)."
        }

    # =========================================================================
    # Trường hợp 1: Kiểm tra mẫu Phủ định (Negative templates) tách biệt ngữ nghĩa thời gian
    # =========================================================================
    if tpl in {"Not Co-Existence", "Not Responded Existence"}:
        if not valid_events_a.empty and not events_b.empty:
            for _, row_a in valid_events_a.iterrows():
                t_a = row_a["time:timestamp"]
                for _, row_b in events_b.iterrows():
                    t_b = row_b["time:timestamp"]
                    dist_days = abs((t_b - t_a).total_seconds()) / 86400.0
                    if allowed_days is None or dist_days <= allowed_days:
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
            "msg": f"Hai sự kiện loại trừ '{act_a}' và '{act_b}' không cùng xảy ra trong khoảng xung đột (tuân thủ {tpl})."
        }

    if tpl == "Not Response":
        # B không được xuất hiện SAU A (nếu B xuất hiện TRƯỚC A thì vẫn hợp lệ)
        for a_idx, row_a in valid_events_a.iterrows():
            t_a = row_a["time:timestamp"]
            after_b = events_b[events_b.index > a_idx]
            if allowed_days is not None and not after_b.empty:
                after_b = after_b[((after_b["time:timestamp"] - t_a).dt.total_seconds() / 86400.0) <= allowed_days]
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
        for b_idx, row_b in events_b.iterrows():
            t_b = row_b["time:timestamp"]
            before_a = valid_events_a[valid_events_a.index < b_idx]
            if allowed_days is not None and not before_a.empty:
                before_a = before_a[((t_b - before_a["time:timestamp"]).dt.total_seconds() / 86400.0) <= allowed_days]
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
    # Trường hợp 1B: Responded Existence[A, B] (B phải tồn tại trước hoặc sau A)
    # =========================================================================
    if tpl == "Responded Existence":
        if valid_events_a.empty:
            return True, {
                "msg": f"Hoạt động kích hoạt '{act_a}' không xảy ra, quy tắc Responded Existence được bảo toàn."
            }
        if events_b.empty:
            first_a_ts = valid_events_a["time:timestamp"].iloc[0]
            return False, {
                "violation_subtype": "MISSING_TARGET_RESPONSE",
                "activation_event": {"activity": act_a, "timestamp": str(first_a_ts)},
                "missing_event": act_b,
                "deviation_magnitude": f"Hoạt động '{act_a}' xuất hiện lúc {first_a_ts} nhưng thiếu hoạt động đồng hành '{act_b}' trong hồ sơ.",
                "minimal_correction_mcs": f"Bổ sung hoạt động '{act_b}' vào hồ sơ trước hoặc sau '{act_a}'.",
            }
        witness_pair = None
        for _, row_a in valid_events_a.iterrows():
            t_a = row_a["time:timestamp"]
            dists = (events_b["time:timestamp"] - t_a).abs().dt.total_seconds() / 86400.0
            min_idx = dists.idxmin()
            min_dist = float(dists.loc[min_idx])
            closest_b_ts = events_b.loc[min_idx, "time:timestamp"]
            if allowed_days is not None and min_dist > allowed_days:
                excess_days = round(min_dist - allowed_days, 2)
                return False, {
                    "violation_subtype": "DEADLINE_EXCEEDED",
                    "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                    "target_event": {"activity": act_b, "timestamp": str(closest_b_ts)},
                    "actual_duration_days": round(min_dist, 2),
                    "allowed_max_days": allowed_days_disp,
                    "deviation_magnitude": f"Khoảng cách giữa '{act_a}' và '{act_b}' vượt thời hạn {excess_days} ngày.",
                    "minimal_correction_mcs": f"Rút ngắn khoảng cách thời gian giữa '{act_a}' và '{act_b}' về <= {ast_obj.time_max} {ast_obj.time_unit or 'ngày'}.",
                }
            if witness_pair is None:
                witness_pair = (t_a, closest_b_ts, round(min_dist, 2))
        t_a0, t_b0, d0 = witness_pair
        return True, {
            "msg": f"Hoạt động '{act_a}' ({t_a0}) đi kèm hợp lệ với '{act_b}' ({t_b0}).",
            "activation_event": {"activity": act_a, "timestamp": str(t_a0)},
            "target_event": {"activity": act_b, "timestamp": str(t_b0)},
            "actual_duration_days": d0,
        }

    # =========================================================================
    # Trường hợp 2: Kiểm tra mẫu Precedence / Alternate Precedence / Chain Precedence (tất cả lần xuất hiện của B)
    # =========================================================================
    if tpl in {"Precedence", "Alternate Precedence", "Chain Precedence"}:
        if events_b.empty:
            return True, {
                "msg": f"Hoạt động đích '{act_b}' không xảy ra, quy tắc {tpl} được bảo toàn."
            }

        prev_b_idx = -1
        witness_info = None
        equiv_a = ACTIVITY_ALIASES.get(act_a, {act_a})

        for occ_idx, (b_idx, row_b) in enumerate(events_b.iterrows()):
            b_time = row_b["time:timestamp"]
            if tpl == "Alternate Precedence":
                prior_raw_a = events_a[(events_a.index > prev_b_idx) & (events_a.index < b_idx)]
            else:
                prior_raw_a = events_a[events_a.index < b_idx]

            if prior_raw_a.empty:
                if tpl == "Alternate Precedence" and occ_idx > 0 and not events_a[events_a.index < b_idx].empty:
                    return False, {
                        "violation_subtype": "ALTERNATE_PRECEDENCE_VIOLATION",
                        "target_event": {"activity": act_b, "timestamp": str(b_time)},
                        "missing_event": act_a,
                        "deviation_magnitude": f"Hoạt động '{act_b}' lặp lại lúc {b_time} mà không có '{act_a}' xen giữa (vi phạm Alternate Precedence).",
                        "minimal_correction_mcs": f"Thực hiện '{act_a}' xen giữa hai lần '{act_b}'.",
                    }
                if events_a.empty:
                    return False, {
                        "violation_subtype": "MISSING_PREREQUISITE_ACTIVITY",
                        "target_event": {"activity": act_b, "timestamp": str(b_time)},
                        "missing_event": act_a,
                        "deviation_magnitude": f"Hoạt động tiền đề bắt buộc '{act_a}' hoàn toàn không xuất hiện trước '{act_b}'.",
                        "minimal_correction_mcs": f"Bắt buộc thực hiện '{act_a}' trước thời điểm {b_time}.",
                    }
                late_a_df = events_a[events_a.index > b_idx]
                late_a_time = late_a_df["time:timestamp"].iloc[0] if not late_a_df.empty else events_a["time:timestamp"].iloc[0]
                delay_hours = round((late_a_time - b_time).total_seconds() / 3600.0, 2)
                return False, {
                    "violation_subtype": "TEMPORAL_ORDER_INVERSION",
                    "activation_event": {"activity": act_a, "timestamp": str(late_a_time)},
                    "target_event": {"activity": act_b, "timestamp": str(b_time)},
                    "deviation_magnitude": f"'{act_a}' diễn ra muộn hơn '{act_b}' {delay_hours} giờ.",
                    "minimal_correction_mcs": f"Đảo thứ tự thực thi: hoàn tất '{act_a}' trước '{act_b}' (trước {b_time}).",
                }

            if tpl == "Chain Precedence":
                if b_idx == 0:
                    return False, {
                        "violation_subtype": "MISSING_PREREQUISITE_ACTIVITY",
                        "target_event": {"activity": act_b, "timestamp": str(b_time)},
                        "missing_event": act_a,
                        "deviation_magnitude": f"Hoạt động tiền đề '{act_a}' không xuất hiện ngay trước '{act_b}'.",
                        "minimal_correction_mcs": f"Thực hiện '{act_a}' liền kề ngay trước '{act_b}'.",
                    }
                prev_row = case_df.iloc[b_idx - 1]
                prev_act = str(prev_row["concept:name"])
                if prev_act not in equiv_a:
                    return False, {
                        "violation_subtype": "CHAIN_ADJACENCY_VIOLATION",
                        "activation_event": {"activity": act_a, "timestamp": str(prior_raw_a["time:timestamp"].iloc[-1])},
                        "target_event": {"activity": act_b, "timestamp": str(b_time)},
                        "deviation_magnitude": (
                            f"Sự kiện ngay trước '{act_b}' là '{prev_act}' thay vì '{act_a}' (vi phạm Chain Precedence)."
                        ),
                        "minimal_correction_mcs": (
                            f"Đảm bảo '{act_a}' diễn ra liền kề ngay trước '{act_b}' mà không bị chèn bởi '{prev_act}'."
                        ),
                    }
                if has_attr_cond:
                    attr, op, val = ast_obj.activation_attr, ast_obj.activation_op, ast_obj.activation_val
                    ok_pred, actual_val = evaluate_data_predicate(prev_row, attr, op, val)
                    if not ok_pred:
                        return False, {
                            "violation_subtype": "DATA_ATTRIBUTE_THRESHOLD_VIOLATION",
                            "activation_event": {"activity": act_a, "timestamp": str(prev_row["time:timestamp"]), attr: actual_val},
                            "target_event": {"activity": act_b, "timestamp": str(b_time)},
                            "deviation_magnitude": (
                                f"Sự kiện tiền đề liền kề '{act_a}' có '{attr}={actual_val}', "
                                f"không thỏa mãn điều kiện '{attr} {op} {val}'."
                            ),
                            "minimal_correction_mcs": f"Đảm bảo '{attr}' tại '{act_a}' thỏa mãn '{op} {val}' ngay trước '{act_b}'.",
                        }
                t_a_valid = prev_row["time:timestamp"]
            else:
                if has_attr_cond:
                    attr, op, val = ast_obj.activation_attr, ast_obj.activation_op, ast_obj.activation_val
                    prior_valid_rows = []
                    last_actual = None
                    for _, row_a in prior_raw_a.iterrows():
                        ok_pred, actual_val = evaluate_data_predicate(row_a, attr, op, val)
                        last_actual = actual_val
                        if ok_pred:
                            prior_valid_rows.append(row_a)
                    if not prior_valid_rows:
                        return False, {
                            "violation_subtype": "DATA_ATTRIBUTE_THRESHOLD_VIOLATION",
                            "activation_event": {
                                "activity": act_a,
                                "timestamp": str(prior_raw_a["time:timestamp"].iloc[-1]),
                                attr: last_actual,
                            },
                            "target_event": {"activity": act_b, "timestamp": str(b_time)},
                            "deviation_magnitude": (
                                f"Sự kiện tiền đề '{act_a}' xảy ra trước '{act_b}' nhưng giá trị '{attr}={last_actual}' "
                                f"không thỏa mãn điều kiện '{attr} {op} {val}'."
                            ),
                            "minimal_correction_mcs": (
                                f"Đảm bảo thuộc tính '{attr}' tại bước '{act_a}' thỏa mãn '{op} {val}' trước khi duyệt '{act_b}'."
                            ),
                        }
                    t_a_valid = prior_valid_rows[-1]["time:timestamp"]
                else:
                    t_a_valid = prior_raw_a["time:timestamp"].iloc[-1]

            elapsed_days = (b_time - t_a_valid).total_seconds() / 86400.0
            if allowed_days is not None and elapsed_days > allowed_days:
                excess_days = round(elapsed_days - allowed_days, 2)
                return False, {
                    "violation_subtype": "DEADLINE_EXCEEDED",
                    "activation_event": {"activity": act_a, "timestamp": str(t_a_valid)},
                    "target_event": {"activity": act_b, "timestamp": str(b_time)},
                    "actual_duration_days": round(elapsed_days, 2),
                    "allowed_max_days": allowed_days_disp,
                    "deviation_magnitude": f"Vượt quá thời hạn quy định {excess_days} ngày.",
                    "minimal_correction_mcs": (
                        f"Rút ngắn khoảng cách thời gian giữa '{act_a}' và '{act_b}' tối thiểu {excess_days} ngày "
                        f"(về mức <= {ast_obj.time_max} {ast_obj.time_unit or 'ngày'})."
                    ),
                }

            if witness_info is None:
                witness_info = (t_a_valid, b_time, round(elapsed_days, 2))
            prev_b_idx = b_idx

        t_a0, b_time0, dur_days = witness_info
        return True, {
            "msg": (
                f"Hoạt động tiền đề '{act_a}' ({t_a0}) đã diễn ra hợp lệ trước "
                f"tất cả '{act_b}' (khoảng cách thời gian mẫu đầu: {dur_days} ngày)."
            ),
            "activation_event": {"activity": act_a, "timestamp": str(t_a0)},
            "target_event": {"activity": act_b, "timestamp": str(b_time0)},
            "actual_duration_days": dur_days,
        }

    # =========================================================================
    # Trường hợp 3: Kiểm tra mẫu họ Response (Response, Chain Response, Alternate Response)
    # =========================================================================
    if tpl in {"Response", "Alternate Response", "Chain Response"}:
        if valid_events_a.empty:
            return True, {
                "msg": f"Hoạt động kích hoạt '{act_a}' không xảy ra (hoặc không thỏa điều kiện kích hoạt), quy tắc {tpl} được bảo toàn."
            }

        equiv_b = ACTIVITY_ALIASES.get(act_b, {act_b})

        # 3A. Chain Response[A, B]: B bắt buộc là sự kiện liền kề ngay sau mọi A hợp lệ
        if tpl == "Chain Response":
            for idx, row_a in valid_events_a.iterrows():
                t_a = row_a["time:timestamp"]
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
                if next_act != act_b and next_act not in equiv_b:
                    return False, {
                        "violation_subtype": "CHAIN_RESPONSE_VIOLATION",
                        "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                        "target_event": {"activity": next_act, "timestamp": str(next_row["time:timestamp"])},
                        "deviation_magnitude": f"Sự kiện ngay sau '{act_a}' là '{next_act}' thay vì '{act_b}' (vi phạm Chain Response).",
                        "minimal_correction_mcs": f"Đảm bảo '{act_b}' diễn ra liền kề ngay sau '{act_a}' mà không bị chèn bởi '{next_act}'.",
                    }
                elapsed_days = (next_row["time:timestamp"] - t_a).total_seconds() / 86400.0
                if allowed_days is not None and elapsed_days > allowed_days:
                    excess_days = round(elapsed_days - allowed_days, 2)
                    return False, {
                        "violation_subtype": "DEADLINE_EXCEEDED",
                        "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                        "target_event": {"activity": act_b, "timestamp": str(next_row["time:timestamp"])},
                        "actual_duration_days": round(elapsed_days, 2),
                        "allowed_max_days": allowed_days_disp,
                        "deviation_magnitude": f"Vượt quá thời hạn quy định {excess_days} ngày.",
                        "minimal_correction_mcs": (
                            f"Rút ngắn thời gian thực hiện '{act_b}' tối thiểu {excess_days} ngày "
                            f"(về mức <= {ast_obj.time_max} {ast_obj.time_unit or 'ngày'})."
                        ),
                    }

        # 3B. Alternate Response[A, B]: Sau mỗi A hợp lệ phải có B trước khi A bất kỳ tiếp theo lặp lại
        if tpl == "Alternate Response":
            for idx, row_a in valid_events_a.iterrows():
                t_a_curr = row_a["time:timestamp"]
                later_any_a = events_a[events_a.index > idx]
                if not later_any_a.empty:
                    next_a_idx = later_any_a.index[0]
                    inter_b = events_b[(events_b.index > idx) & (events_b.index < next_a_idx)]
                else:
                    inter_b = events_b[events_b.index > idx]
                if inter_b.empty:
                    return False, {
                        "violation_subtype": "ALTERNATE_RESPONSE_VIOLATION",
                        "activation_event": {"activity": act_a, "timestamp": str(t_a_curr)},
                        "missing_event": act_b,
                        "deviation_magnitude": f"Sự kiện '{act_a}' lặp lại nhưng thiếu sự kiện phản hồi '{act_b}' xen giữa (vi phạm Alternate Response).",
                        "minimal_correction_mcs": f"Hoàn tất hoạt động '{act_b}' trước khi kích hoạt lại '{act_a}'.",
                    }
                t_b_first = inter_b["time:timestamp"].iloc[0]
                elapsed_days = (t_b_first - t_a_curr).total_seconds() / 86400.0
                if allowed_days is not None and elapsed_days > allowed_days:
                    excess_days = round(elapsed_days - allowed_days, 2)
                    return False, {
                        "violation_subtype": "DEADLINE_EXCEEDED",
                        "activation_event": {"activity": act_a, "timestamp": str(t_a_curr)},
                        "target_event": {"activity": act_b, "timestamp": str(t_b_first)},
                        "actual_duration_days": round(elapsed_days, 2),
                        "allowed_max_days": allowed_days_disp,
                        "deviation_magnitude": f"Vượt quá thời hạn quy định {excess_days} ngày.",
                        "minimal_correction_mcs": (
                            f"Rút ngắn thời gian thực hiện '{act_b}' tối thiểu {excess_days} ngày "
                            f"(về mức <= {ast_obj.time_max} {ast_obj.time_unit or 'ngày'})."
                        ),
                    }

        # 3C. Kiểm tra chung cho Response: Có B sau mỗi A hợp lệ trong khoảng thời gian quy định
        for a_idx, row_a in valid_events_a.iterrows():
            t_a = row_a["time:timestamp"]
            subsequent_b = events_b[events_b.index > a_idx]

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
            elapsed_days = (t_b - t_a).total_seconds() / 86400.0

            if allowed_days is not None and elapsed_days > allowed_days:
                excess_days = round(elapsed_days - allowed_days, 2)
                return False, {
                    "violation_subtype": "DEADLINE_EXCEEDED",
                    "activation_event": {"activity": act_a, "timestamp": str(t_a)},
                    "target_event": {"activity": act_b, "timestamp": str(t_b)},
                    "actual_duration_days": round(elapsed_days, 2),
                    "allowed_max_days": allowed_days_disp,
                    "deviation_magnitude": f"Vượt quá thời hạn quy định {excess_days} ngày.",
                    "minimal_correction_mcs": (
                        f"Rút ngắn thời gian thực hiện '{act_b}' tối thiểu {excess_days} ngày "
                        f"(về mức <= {ast_obj.time_max} {ast_obj.time_unit or 'ngày'})."
                    ),
                }

        first_a_idx = valid_events_a.index[0]
        first_a_ts = valid_events_a["time:timestamp"].iloc[0]
        first_b_ts = events_b[events_b.index > first_a_idx]["time:timestamp"].iloc[0]
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
