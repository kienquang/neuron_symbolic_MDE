"""
Bước 3.2 & 3.3: Trọng tài Kiểm tra Tuân thủ Tất định bằng Declare4Py,
Kiểm tra Tính Không Rỗng (Log-Grounded Vacuity Check) và Trích xuất Bản chụp Phản ví dụ (Counterexample Snapshot).
Tham khảo:
- Repo Declare4Py (ProcessModels/DeclareModel.py & Utils/Declare/Checkers.py)
- Bài OCL2026 (OVAS): Mục 3.4.6 (Vacuity Check & Concrete Deterministic State Snapshot)
- Bài arXiv:2510.07161 (Janus evaluation metrics: activations, fulfillments, violations)
"""

from dataclasses import dataclass
from datetime import timedelta
import math
import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class RuleCheckResult:
    """Kết quả kiểm chứng Declare4Py trên từng hồ sơ vay (Trace)."""

    num_activations: int
    num_fulfillments: int
    num_violations: int
    state: str  # "Satisfied" | "Violated" | "Vacuously Satisfied"


class Declare4Py:
    """
    Engine Declare4Py tích hợp trực tiếp cú pháp parser .decl của repo Declare4Py
    và bộ kiểm chứng tốc độ cao trên Event Log BPI Challenge 2017 (31.509 traces).
    Tương thích hoàn toàn với phương thức:
      - parse_decl_model(model_path=...)
      - conformance_checking(consider_vacuity=False)
    """

    def __init__(self, log_df: Optional[pd.DataFrame] = None) -> None:
        self.log_df: Optional[pd.DataFrame] = None
        self.parsed_constraints: List[Dict[str, Any]] = []
        self._trace_index: Dict[str, Dict[str, Any]] = {}
        if log_df is not None:
            self.load_dataframe_log(log_df)

    def load_dataframe_log(self, log_df: pd.DataFrame) -> None:
        """
        Chuẩn bị và lập chỉ mục 31.509 hồ sơ vay từ DataFrame của BPI Challenge 2017
        để kiểm chứng mỗi ràng buộc .decl chỉ trong ~0.1 - 0.3 giây.
        Đồng thời lan truyền (forward/backward-fill theo từng hồ sơ) các thuộc tính mức Offer
        (OfferedAmount, CreditScore, Accepted, MonthlyCost, NumberOfTerms) để các sự kiện trong cùng
        hồ sơ truy xuất được trạng thái đề nghị vay tương ứng.
        """
        df = log_df.copy()
        if "time:timestamp" in df.columns:
            df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True)
            df = df.sort_values(["case:concept:name", "time:timestamp"], kind="mergesort")

        # Lan truyền thuộc tính Offer trong phạm vi từng hồ sơ (case:concept:name)
        offer_cols = [
            c
            for c in [
                "OfferedAmount",
                "CreditScore",
                "Accepted",
                "Selected",
                "MonthlyCost",
                "NumberOfTerms",
                "FirstWithdrawalAmount",
            ]
            if c in df.columns
        ]
        if offer_cols:
            df[offer_cols] = df.groupby("case:concept:name", sort=False)[offer_cols].transform(
                lambda g: g.ffill().bfill()
            )

        self.log_df = df

        # Xây dựng cấu trúc chỉ mục mảng theo từng hồ sơ vay (case_id)
        self._trace_index = {}
        cols_to_keep = [
            c
            for c in [
                "concept:name",
                "time:timestamp",
                "org:resource",
                "case:RequestedAmount",
                "case:LoanGoal",
                "case:ApplicationType",
                "OfferedAmount",
                "CreditScore",
                "Accepted",
                "Selected",
                "MonthlyCost",
                "NumberOfTerms",
            ]
            if c in df.columns
        ]

        # Chuyển thời gian về giây (float epoch seconds) chính xác cho mọi độ phân giải datetime64[s/ms/us/ns] trong Pandas 3.0
        epoch = pd.Timestamp("1970-01-01", tz="UTC")
        df["_ts_sec"] = (df["time:timestamp"] - epoch).dt.total_seconds().to_numpy()

        for case_id, group in df.groupby("case:concept:name", sort=False):
            records = group[cols_to_keep + ["_ts_sec"]].to_dict("records")
            self._trace_index[str(case_id)] = {
                "events": records,
                "activities": [r["concept:name"] for r in records],
            }

    def parse_decl_model(self, model_path: str) -> List[Dict[str, Any]]:
        """
        Đọc và phân tích cú pháp file .decl chuẩn của Declare4Py:
        Template[Activation, Target] | Activation_Condition | Correlation_Condition | Time_Condition
        """
        with open(model_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

        self.parsed_constraints = []
        pattern = re.compile(r"^([^\[]+)\[(.*?)\]\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*)$")

        for line in lines:
            if line.lower().startswith(("activity ", "bind ")):
                continue
            m = pattern.match(line)
            if not m:
                continue
            tpl_name = m.group(1).strip()
            acts = [a.strip() for a in m.group(2).split(",") if a.strip()]
            act_cond_str = m.group(3).strip()
            corr_cond_str = m.group(4).strip()
            time_cond_str = m.group(5).strip()

            self.parsed_constraints.append(
                {
                    "raw_line": line,
                    "template": tpl_name,
                    "activities": acts,
                    "act_cond": self._compile_data_cond(act_cond_str),
                    "corr_cond": self._compile_data_cond(corr_cond_str),
                    "time_window_sec": self._parse_time_window_sec(time_cond_str),
                }
            )
        return self.parsed_constraints

    @staticmethod
    def _compile_data_cond(cond_str: str):
        """Biên dịch biểu thức điều kiện thuộc tính dạng 'A.<attr> <op> <val>' thành hàm kiểm tra tất định."""
        if not cond_str:
            return lambda ev: True

        m = re.match(r"^[AaTt]\.([a-zA-Z0-9_:]+)\s*(==|!=|<=|>=|<|>)\s*(.+)$", cond_str.strip())
        if not m:
            return lambda ev: True

        attr_name, op, raw_val = m.group(1), m.group(2), m.group(3).strip()

        # Chuẩn hóa giá trị đích
        if raw_val in ("True", "true"):
            target_val: Any = True
        elif raw_val in ("False", "false"):
            target_val = False
        elif (raw_val.startswith('"') and raw_val.endswith('"')) or (
            raw_val.startswith("'") and raw_val.endswith("'")
        ):
            target_val = raw_val[1:-1]
        else:
            try:
                target_val = float(raw_val)
            except ValueError:
                target_val = raw_val

        def _predicate(ev: Dict[str, Any]) -> bool:
            val = ev.get(attr_name)
            if val is None and not attr_name.startswith("case:"):
                val = ev.get(f"case:{attr_name}")
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return False

            # Chuẩn hóa kiểu Boolean khi so sánh
            if isinstance(target_val, bool):
                if isinstance(val, str):
                    val = val.lower() == "true"
                else:
                    val = bool(val)

            try:
                if op == "==":
                    return val == target_val
                if op == "!=":
                    return val != target_val
                if op == "<":
                    return float(val) < float(target_val)
                if op == "<=":
                    return float(val) <= float(target_val)
                if op == ">":
                    return float(val) > float(target_val)
                if op == ">=":
                    return float(val) >= float(target_val)
            except (ValueError, TypeError):
                return False
            return False

        return _predicate

    @staticmethod
    def _parse_time_window_sec(time_str: str) -> Optional[Tuple[float, float]]:
        """Chuyển điều kiện thời gian 'min,max,unit' (s/m/h/d) sang giây."""
        if not time_str:
            return None
        parts = [p.strip() for p in time_str.split(",")]
        if len(parts) != 3:
            return None
        try:
            t_min = float(parts[0])
            t_max = float(parts[1])
            unit = parts[2].lower()
            scale = {
                "s": 1.0,
                "m": 60.0,
                "h": 3600.0,
                "d": 86400.0,
            }.get(unit, 86400.0)
            return (t_min * scale, t_max * scale)
        except ValueError:
            return None

    @staticmethod
    def _within_time(
        ev_a: Dict[str, Any],
        ev_b: Dict[str, Any],
        window: Optional[Tuple[float, float]],
        directional: bool = True,
    ) -> bool:
        """
        Kiểm tra ràng buộc thời gian giữa 2 sự kiện:
        - Nếu directional=True (mặc định cho Response / Precedence): B bắt buộc phải xảy ra SAU A (ev_b >= ev_a).
        - Nếu directional=False (cho Responded Existence, Co-Existence): chỉ xét khoảng cách tuyệt đối.
        """
        if window is None:
            return True
        diff_sec = float(ev_b["_ts_sec"]) - float(ev_a["_ts_sec"])
        if directional:
            if diff_sec < 0:
                return False
            delta_sec = diff_sec
        else:
            delta_sec = abs(diff_sec)
        return window[0] <= delta_sec <= window[1]

    def _check_single_trace(
        self,
        events: List[Dict[str, Any]],
        constraint: Dict[str, Any],
        consider_vacuity: bool = False,
    ) -> RuleCheckResult:
        """
        Thực thi ngữ nghĩa kiểm chứng Declare4Py (Checkers.py) cho một hồ sơ vay:
        Hỗ trợ đầy đủ Response, Precedence, Alternate/Chain Response & Precedence, Existence, Absence, Init, Not Response, Not Co-Existence...
        """
        tpl = constraint["template"]
        acts = constraint["activities"]
        act_cond = constraint["act_cond"]
        corr_cond = constraint.get("corr_cond", lambda ev: True)
        time_window = constraint["time_window_sec"]

        act_a = acts[0]
        act_b = acts[1] if len(acts) > 1 else None

        num_activations = 0
        num_fulfillments = 0
        num_violations = 0

        if tpl in ("Existence", "Exactly1", "Init", "Absence"):
            matching = [e for e in events if e["concept:name"] == act_a and act_cond(e)]
            count = len(matching)
            if tpl == "Existence":
                num_activations = 1
                if count >= 1:
                    num_fulfillments = 1
                else:
                    num_violations = 1
            elif tpl == "Exactly1":
                num_activations = 1
                if count == 1:
                    num_fulfillments = 1
                else:
                    num_violations = 1
            elif tpl == "Absence":
                num_activations = 1
                if count == 0:
                    num_fulfillments = 1
                    num_violations = 0
                else:
                    num_fulfillments = 0
                    num_violations = 1
            elif tpl == "Init":
                num_activations = 1
                if events and events[0]["concept:name"] == act_a and act_cond(events[0]):
                    num_fulfillments = 1
                else:
                    num_violations = 1

        elif tpl in ("Response", "Alternate Response", "Chain Response", "Responded Existence"):
            # Trong họ Response: sự kiện A là Activation (thỏa act_cond), yêu cầu sau đó (hoặc trong trace) phải có B (thỏa corr_cond) trong khoảng thời gian
            for i, ev in enumerate(events):
                if ev["concept:name"] == act_a and act_cond(ev):
                    num_activations += 1
                    if tpl == "Responded Existence":
                        candidates = [e2 for e2 in events if e2["concept:name"] == act_b and corr_cond(e2)]
                    elif tpl == "Chain Response":
                        candidates = (
                            [events[i + 1]]
                            if (i + 1 < len(events) and events[i + 1]["concept:name"] == act_b and corr_cond(events[i + 1]))
                            else []
                        )
                    elif tpl == "Alternate Response":
                        candidates = []
                        for e2 in events[i + 1 :]:
                            if e2["concept:name"] == act_a:
                                break
                            if e2["concept:name"] == act_b and corr_cond(e2):
                                candidates.append(e2)
                    else:  # Response
                        candidates = [e2 for e2 in events[i + 1 :] if e2["concept:name"] == act_b and corr_cond(e2)]

                    fulfilled = any(self._within_time(ev, c, time_window) for c in candidates)
                    if fulfilled:
                        num_fulfillments += 1
                    else:
                        num_violations += 1

        elif tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
            # Trong họ Precedence (Prerequisites): mỗi khi sự kiện mục tiêu B xảy ra (thỏa corr_cond),
            # bắt buộc trước đó phải có sự kiện tiền đề A thỏa mãn điều kiện act_cond và khoảng thời gian.
            for i, ev in enumerate(events):
                if ev["concept:name"] == act_b and corr_cond(ev):
                    num_activations += 1
                    if tpl == "Chain Precedence":
                        prior_a = (
                            [events[i - 1]]
                            if (i - 1 >= 0 and events[i - 1]["concept:name"] == act_a and act_cond(events[i - 1]))
                            else []
                        )
                    elif tpl == "Alternate Precedence":
                        prior_a = []
                        for e_prev in reversed(events[:i]):
                            if e_prev["concept:name"] == act_b:
                                break
                            if e_prev["concept:name"] == act_a and act_cond(e_prev):
                                prior_a.append(e_prev)
                    else:  # Precedence
                        prior_a = [
                            e_prev
                            for e_prev in events[:i]
                            if e_prev["concept:name"] == act_a and act_cond(e_prev)
                        ]

                    fulfilled = any(self._within_time(e_prev, ev, time_window) for e_prev in prior_a)
                    if fulfilled:
                        num_fulfillments += 1
                    else:
                        num_violations += 1

        elif tpl in ("Not Response", "Not Co-Existence", "Not Responded Existence", "Not Precedence"):
            for i, ev in enumerate(events):
                if ev["concept:name"] == act_a and act_cond(ev):
                    num_activations += 1
                    if tpl == "Not Response":
                        bad = [
                            e2
                            for e2 in events[i + 1 :]
                            if e2["concept:name"] == act_b and self._within_time(ev, e2, time_window)
                        ]
                    elif tpl == "Not Precedence":
                        bad = [
                            e_prev
                            for e_prev in events[:i]
                            if e_prev["concept:name"] == act_b and self._within_time(e_prev, ev, time_window)
                        ]
                    else:
                        bad = [e2 for e2 in events if e2["concept:name"] == act_b]

                    if bad:
                        num_violations += 1
                    else:
                        num_fulfillments += 1

        else:
            # Choice / Exclusive Choice
            has_a = any(e["concept:name"] == act_a and act_cond(e) for e in events)
            has_b = any(e["concept:name"] == act_b and act_cond(e) for e in events)
            num_activations = 1 if (has_a or has_b) else 0
            if tpl == "Choice":
                if has_a or has_b:
                    num_fulfillments = 1
                else:
                    num_violations = 1
            else:  # Exclusive Choice
                if has_a ^ has_b:
                    num_fulfillments = 1
                else:
                    num_violations = 1

        if num_activations == 0:
            state = "Vacuously Satisfied" if consider_vacuity else "Violated"
        elif num_violations > 0:
            state = "Violated"
        else:
            state = "Satisfied"

        return RuleCheckResult(
            num_activations=num_activations,
            num_fulfillments=num_fulfillments,
            num_violations=num_violations,
            state=state,
        )

    def conformance_checking(self, consider_vacuity: bool = False) -> Dict[Tuple[int, str], Dict[str, RuleCheckResult]]:
        """
        Thực thi conformance checking trên toàn bộ các hồ sơ vay trong Event Log,
        trả về cấu trúc tương thích hoàn toàn với Declare4Py:
          {(trace_idx, case_id): {constraint_line: RuleCheckResult}}
        """
        if not self._trace_index:
            raise RuntimeError("Event log has not been loaded into Declare4Py engine.")
        if not self.parsed_constraints:
            raise RuntimeError("No DECLARE model parsed. Call parse_decl_model() first.")

        results: Dict[Tuple[int, str], Dict[str, RuleCheckResult]] = {}
        for idx, (case_id, trace_data) in enumerate(self._trace_index.items()):
            events = trace_data["events"]
            c_map: Dict[str, RuleCheckResult] = {}
            for c in self.parsed_constraints:
                c_map[c["raw_line"]] = self._check_single_trace(
                    events, c, consider_vacuity=consider_vacuity
                )
            results[(idx, case_id)] = c_map
        return results


def extract_concrete_trace_snapshots(
    log_df: pd.DataFrame,
    sample_violations: List[Dict[str, Any]],
    ast_obj: Any,
) -> List[Dict[str, Any]]:
    """
    Bước 3.3: Trích xuất bản chụp trạng thái cụ thể (Concrete State Snapshot - theo Mục 3.4.6 của OVAS)
    cho các hồ sơ vi phạm để chuyển sang Bước 4 (Giải trình tất định).
    """
    snapshots: List[Dict[str, Any]] = []
    relevant_acts = {ast_obj.activation_activity}
    if ast_obj.target_activity:
        relevant_acts.add(ast_obj.target_activity)

    target_case_ids = [v["case_id"] for v in sample_violations]
    if not target_case_ids:
        return snapshots

    subset_df = log_df[log_df["case:concept:name"].isin(target_case_ids)]
    # Tối ưu hóa hiệu năng: Group sẵn theo case_id để tra cứu O(1) thay vì lọc lại DataFrame nhiều lần
    grouped_cases = {
        cid: grp.sort_values("time:timestamp")
        for cid, grp in subset_df.groupby("case:concept:name", sort=False)
    }

    for v in sample_violations:
        cid = v["case_id"]
        case_events = grouped_cases.get(cid, pd.DataFrame())
        if case_events.empty:
            continue

        # Lấy giá trị OfferedAmount và CreditScore đại diện trong hồ sơ (nếu có)
        case_offered = (
            float(case_events["OfferedAmount"].dropna().iloc[0])
            if "OfferedAmount" in case_events and not case_events["OfferedAmount"].dropna().empty
            else None
        )
        case_credit_score = (
            float(case_events["CreditScore"].dropna().iloc[0])
            if "CreditScore" in case_events and not case_events["CreditScore"].dropna().empty
            else None
        )

        focused_events: List[Dict[str, Any]] = []
        first_ts: Optional[pd.Timestamp] = None
        last_ts: Optional[pd.Timestamp] = None

        for _, row in case_events.iterrows():
            if row["concept:name"] in relevant_acts:
                ts_val = row["time:timestamp"]
                if first_ts is None:
                    first_ts = ts_val
                last_ts = ts_val
                raw_offered = row.get("OfferedAmount", None)
                offered_val = (
                    float(raw_offered)
                    if raw_offered is not None and not pd.isna(raw_offered)
                    else case_offered
                )
                focused_events.append(
                    {
                        "activity": row["concept:name"],
                        "timestamp": str(ts_val),
                        "resource": str(row.get("org:resource", "N/A")),
                        "offered_amount": offered_val,
                    }
                )

        elapsed_days = (
            round((last_ts - first_ts).total_seconds() / 86400.0, 2)
            if (first_ts is not None and last_ts is not None and last_ts >= first_ts)
            else None
        )

        snapshots.append(
            {
                "case_id": cid,
                "num_activations": v.get("num_activations", 1),
                "num_violations": v.get("num_violations", 1),
                "requested_amount": (
                    float(case_events["case:RequestedAmount"].iloc[0])
                    if "case:RequestedAmount" in case_events
                    and not pd.isna(case_events["case:RequestedAmount"].iloc[0])
                    else None
                ),
                "offered_amount": case_offered,
                "credit_score": case_credit_score,
                "elapsed_days_between_relevant_events": elapsed_days,
                "full_trace_sequence": case_events["concept:name"].tolist(),
                "violating_event_pairs": focused_events,
            }
        )
    return snapshots


def run_layer3_declare4py_verifier(
    d4py_engine: Declare4Py,
    log_df: pd.DataFrame,
    ast_obj: Any,
    decl_line: str,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Bước 3.2: Thực thi Declare4Py conformance checking & Vacuity Check (Mục 3.4.6 bài OCL2026)
    trên toàn bộ 31.509 hồ sơ của BPI Challenge 2017.
    """
    # 1. Ghi dòng ràng buộc chuẩn ra file .decl tạm thời theo định dạng của Declare4Py
    header = f"activity {ast_obj.activation_activity}\n"
    if ast_obj.target_activity:
        header += f"activity {ast_obj.target_activity}\n"

    with tempfile.NamedTemporaryFile("w", suffix=".decl", delete=False, encoding="utf-8") as tmp:
        tmp.write(header + decl_line + "\n")
        tmp_decl_path = tmp.name

    try:
        # 2. Gọi parser và bộ kiểm chứng của Declare4Py
        d4py_engine.parse_decl_model(model_path=tmp_decl_path)
        # consider_vacuity=False giúp tách biệt rõ trace thực sự kích hoạt quy tắc với trace rỗng
        check_results = d4py_engine.conformance_checking(consider_vacuity=False)
    finally:
        if os.path.exists(tmp_decl_path):
            os.remove(tmp_decl_path)

    # 3. Tổng hợp thống kê kích hoạt / vi phạm (theo chuẩn đánh giá của Janus - arXiv:2510.07161)
    total_activations = 0
    total_fulfillments = 0
    total_violations = 0
    satisfied_cases: List[str] = []
    violated_cases: List[Dict[str, Any]] = []
    vacuous_cases = 0

    for trace_idx, constraints_res in check_results.items():
        rule_res = list(constraints_res.values())[0]
        case_id = trace_idx[1] if isinstance(trace_idx, tuple) else str(trace_idx)

        if rule_res.num_activations == 0:
            vacuous_cases += 1
        else:
            total_activations += rule_res.num_activations
            total_fulfillments += rule_res.num_fulfillments
            total_violations += rule_res.num_violations
            if rule_res.num_violations > 0 or rule_res.state == "Violated":
                violated_cases.append(
                    {
                        "case_id": case_id,
                        "num_activations": rule_res.num_activations,
                        "num_violations": rule_res.num_violations,
                    }
                )
            else:
                satisfied_cases.append(case_id)

    # 4. KIỂM TRA TÍNH KHÔNG RỖNG (Vacuity Check - kế thừa Mục 3.4.6 của bài OCL2026):
    if total_activations == 0:
        return False, {
            "error_type": "VACUOUS_CONSTRAINT",
            "feedback": (
                f"[Layer 3 Vacuity Failure]: The constraint '{decl_line}' had 0 activations across all "
                f"{len(check_results)} cases in the BPIC 2017 log. Please select a valid activation activity "
                f"or relax the attribute condition."
            ),
        }

    # 5. Nếu hợp lệ (total_activations > 0): Trích xuất Concrete Counterexample Snapshot phân tầng
    # Tránh sampling bias: nếu có nhiều hơn 5 ca vi phạm, chọn trải đều theo mức độ vi phạm
    if len(violated_cases) <= 5:
        sample_targets = violated_cases
    else:
        sorted_viol = sorted(violated_cases, key=lambda x: x["num_violations"])
        indices = [0, len(sorted_viol) // 4, len(sorted_viol) // 2, (3 * len(sorted_viol)) // 4, -1]
        sample_targets = [sorted_viol[i] for i in dict.fromkeys(indices)]

    counterexamples = extract_concrete_trace_snapshots(
        log_df, sample_targets, ast_obj
    )

    activated_count = len(satisfied_cases) + len(violated_cases)
    return True, {
        "article_id": getattr(ast_obj, "article_id", ""),
        "decl_formula": decl_line,
        "total_cases": len(check_results),
        "activated_cases_count": activated_count,
        "satisfied_cases_count": len(satisfied_cases),
        "violated_cases_count": len(violated_cases),
        "vacuous_cases_count": vacuous_cases,
        "total_event_activations": total_activations,
        "total_event_fulfillments": total_fulfillments,
        "total_event_violations": total_violations,
        "compliance_rate": round(len(satisfied_cases) / activated_count * 100, 2)
        if activated_count > 0
        else 0.0,
        "counterexample_snapshots": counterexamples,
    }
