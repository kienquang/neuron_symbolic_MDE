import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import pm4py

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


BPIC2017_ACTIVITY_DESCRIPTIONS: Dict[str, str] = {
    "A_Create Application": "Application state milestone logged when a new loan application record is first created.",
    "A_Concept": "Application state milestone recorded during initial concept and draft intake.",
    "A_Accepted": "Application state milestone indicating formal intake acceptance into active credit processing.",
    "A_Complete": "Application state milestone recorded when application workflow submission reaches completion.",
    "A_Validating": "Application state milestone indicating formal back-office application validation status.",
    "A_Pending": "Application state milestone indicating final approval and readiness for disbursement.",
    "A_Denied": "Application state milestone recorded when the loan application is declined.",
    "A_Cancelled": "Application state milestone recorded when the loan application is closed as cancelled.",
    "A_Incomplete": "Application state milestone indicating missing items or incomplete verification files.",
    "A_Submitted": "Application state milestone logged when an online application is submitted into workflow.",
    "O_Create Offer": "Offer lifecycle event logged when a loan offer record is drafted with financial terms.",
    "O_Created": "Offer lifecycle event logged when the finalized offer document is persisted in the system.",
    "O_Sent (mail and online)": "Offer dispatch event logged when an offer is sent via postal mail and online portal.",
    "O_Sent (online only)": "Offer dispatch event logged when an offer is sent via the online portal only.",
    "O_Returned": "Offer lifecycle event logged when a signed/returned offer response arrives from the customer.",
    "O_Accepted": "Offer lifecycle event logged when the loan offer is marked accepted.",
    "O_Refused": "Offer lifecycle event logged when the loan offer is marked declined.",
    "O_Cancelled": "Offer lifecycle event logged when the loan offer is marked cancelled.",
    "W_Validate application": "Human officer work-item task (repeatable staff activity) for reviewing files/documents during post-offer verification.",
    "W_Complete application": "Human officer work-item task (repeatable staff activity) for filling in application intake fields.",
    "W_Call after offers": "Human officer work-item task for outbound follow-up calls after offers are sent.",
    "W_Call incomplete files": "Human officer work-item task for calling applicants regarding missing documents.",
    "W_Handle leads": "Human officer work-item task for processing incoming leads.",
    "W_Assess potential fraud": "Human officer work-item task for reviewing flagged anomaly or fraud alerts.",
    "W_Personal Loan collection": "Human officer work-item task for personal loan collection follow-up.",
    "W_Shortened completion ": "Human officer work-item task for shortened completion processing.",
}


def load_bpic2017_dataframe(
    xes_path: Union[str, Path],
    parquet_cache_path: Optional[Union[str, Path]] = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Đọc file BPI Challenge 2017 (.xes) bằng pm4py và hỗ trợ lưu/đọc bộ nhớ đệm Parquet
    để tăng tốc cho các giai đoạn suy luận phía sau.
    """
    xes_path = Path(xes_path)
    if parquet_cache_path is not None:
        parquet_cache_path = Path(parquet_cache_path)

    if use_cache and parquet_cache_path and parquet_cache_path.exists():
        print(f"Đang đọc Event Log từ bộ nhớ đệm Parquet: {parquet_cache_path} ...")
        df = pd.read_parquet(parquet_cache_path)
        if "time:timestamp" in df.columns:
            df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True)
        return df

    if not xes_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file XES tại: {xes_path}")

    print(f"Đang đọc file XES bằng pm4py: {xes_path} ...")
    df = pm4py.read_xes(str(xes_path))

    if parquet_cache_path is not None:
        try:
            parquet_cache_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(parquet_cache_path, index=False)
            print(f"Đã lưu bản đệm Parquet tại: {parquet_cache_path}")
        except Exception as exc:
            print(f"Cảnh báo: Không thể lưu cache Parquet ({exc})")

    return df


def compute_behavioral_profile_matrix(
    df: pd.DataFrame,
    dfg: Dict[Tuple[str, str], int],
) -> Dict[str, Any]:
    """
    Tính toán Ma trận Quan hệ Hành vi (Behavioral Profile Matrix) từ Event Log:
      1. strict_causal_pairs: Các cặp sự kiện (A, B) có quan hệ thứ tự nhân quả trong hồ sơ thực tế
         kèm xác suất chuyển tiếp P(B|A), P(A|B), tỷ lệ thứ tự bất đối xứng (order_ratio) và
         khoảng thời gian trung vị median_days.
      2. mutually_exclusive_pairs: Các cặp sự kiện (A, B) xung khắc (tỷ lệ đồng xuất hiện <= 1%).
    Hoàn toàn dựa trên thống kê dữ liệu quy trình, không chứa bất kỳ quy tắc viết cứng nào.
    """
    if df.empty or "case:concept:name" not in df.columns or "concept:name" not in df.columns:
        return {"strict_causal_pairs": [], "mutually_exclusive_pairs": []}

    work_df = df[["case:concept:name", "concept:name", "time:timestamp"]].copy()
    work_df["time:timestamp"] = pd.to_datetime(work_df["time:timestamp"], utc=True)
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    work_df["_ts_sec"] = (work_df["time:timestamp"] - epoch).dt.total_seconds()

    # Ma trận thời điểm xuất hiện đầu tiên của mỗi hoạt động trên từng hồ sơ (n_cases x n_activities)
    first_ts_df = (
        work_df.groupby(["case:concept:name", "concept:name"], sort=False)["_ts_sec"]
        .min()
        .unstack()
    )
    total_cases = len(first_ts_df)
    min_support = max(2, int(total_cases * 0.02))

    act_names = list(first_ts_df.columns)
    ts_mat = first_ts_df.to_numpy(dtype=float)
    has_mat = ~np.isnan(ts_mat)
    case_counts = has_mat.sum(axis=0)

    strict_causal_pairs: List[Dict[str, Any]] = []
    mutually_exclusive_pairs: List[Dict[str, Any]] = []

    for i, act_a in enumerate(act_names):
        count_a = int(case_counts[i])
        if count_a < min_support:
            continue
        for j, act_b in enumerate(act_names):
            if i == j:
                continue
            count_b = int(case_counts[j])
            if count_b < min_support:
                continue

            co_mask = has_mat[:, i] & has_mat[:, j]
            co_count = int(co_mask.sum())

            # Kiểm tra loại trừ lẫn nhau (Mutual Exclusion) một chiều i < j để không trùng lặp
            if i < j:
                co_ratio = co_count / float(min(count_a, count_b))
                if co_ratio <= 0.01:
                    mutually_exclusive_pairs.append(
                        {
                            "act_a": act_a,
                            "act_b": act_b,
                            "cases_a": count_a,
                            "cases_b": count_b,
                            "co_occurrence_cases": co_count,
                            "co_occurrence_rate": round(co_ratio, 4),
                        }
                    )

            if co_count < min_support:
                continue

            a_before_b_mask = co_mask & (ts_mat[:, i] <= ts_mat[:, j])
            a_before_b_count = int(a_before_b_mask.sum())
            order_ratio = a_before_b_count / float(co_count)

            # Nếu A xảy ra trước B trong >= 90% số hồ sơ đồng xuất hiện
            if order_ratio >= 0.90:
                deltas_days = (ts_mat[a_before_b_mask, j] - ts_mat[a_before_b_mask, i]) / 86400.0
                median_days = round(float(np.median(deltas_days)), 2) if len(deltas_days) > 0 else 0.0
                direct_count = int(dfg.get((act_a, act_b), 0))
                strict_causal_pairs.append(
                    {
                        "from": act_a,
                        "to": act_b,
                        "co_occurrence_cases": co_count,
                        "order_ratio": round(order_ratio, 4),
                        "prob_to_given_from": round(a_before_b_count / float(count_a), 4),
                        "prob_from_given_to": round(a_before_b_count / float(count_b), 4),
                        "direct_dfg_count": direct_count,
                        "median_days": median_days,
                    }
                )

    # Giữ cả nhóm Direct-DFG cao (phục vụ Chain) lẫn nhóm Eventually-Follows bất biến (phục vụ Precedence/Response
    # ngay cả khi có event trung gian như W_* chen giữa khiến direct_dfg_count = 0).
    direct_ranked = sorted(
        strict_causal_pairs,
        key=lambda x: (x["direct_dfg_count"], x["co_occurrence_cases"]),
        reverse=True,
    )
    eventual_ranked = sorted(
        [
            p for p in strict_causal_pairs
            if p["order_ratio"] >= 0.95 and p["prob_from_given_to"] >= 0.90
        ],
        key=lambda x: (x["co_occurrence_cases"], x["order_ratio"], -x["median_days"]),
        reverse=True,
    )
    merged_pairs: List[Dict[str, Any]] = []
    seen_edges: set[Tuple[str, str]] = set()
    for p in direct_ranked[:40] + eventual_ranked[:80]:
        edge_key = (p["from"], p["to"])
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            merged_pairs.append(p)
    merged_pairs.sort(
        key=lambda x: (x["direct_dfg_count"], x["co_occurrence_cases"]),
        reverse=True,
    )

    mutually_exclusive_pairs.sort(
        key=lambda x: (x["co_occurrence_rate"], -(x["cases_a"] + x["cases_b"]))
    )

    return {
        "total_cases": total_cases,
        "strict_causal_pairs": merged_pairs[:110],
        "mutually_exclusive_pairs": mutually_exclusive_pairs[:20],
    }


def extract_bpic2017_schema(
    xes_path: Union[str, Path],
    output_schema_path: Union[str, Path],
    parquet_cache_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Phần 1B: Trích xuất Lược đồ Quy trình (Process Metamodel / Typing Environment Γ)
    từ BPI_Challenge_2017.xes sang process_schema.json.
    """
    output_schema_path = Path(output_schema_path)

    # 1. Đọc file XES bằng pm4py (trả về DataFrame chuẩn của pm4py)
    df = load_bpic2017_dataframe(xes_path, parquet_cache_path=parquet_cache_path)

    # 2. Trích xuất danh mục Hoạt động (Activities) gom theo phân hệ (EventOrigin)
    activities_by_origin: Dict[str, list] = {}
    if "EventOrigin" in df.columns:
        for origin, group in df.groupby("EventOrigin"):
            activities_by_origin[str(origin)] = sorted(
                group["concept:name"].dropna().unique().tolist()
            )

    all_activities = sorted(df["concept:name"].dropna().unique().tolist())

    # 3. Trích xuất Kiểu dữ liệu & Miền hoạt động áp dụng của các Thuộc tính (Process Schema)
    case_attributes: Dict[str, Dict[str, Any]] = {}
    event_attributes: Dict[str, Dict[str, Any]] = {}
    for col in df.columns:
        non_null_series = df[col].dropna()
        dtype_str = str(non_null_series.dtype).lower()
        unique_vals = non_null_series.unique()[:3]
        samples = [str(v) for v in unique_vals]

        is_bool_col = (
            "bool" in dtype_str
            or (len(samples) > 0 and set(samples).issubset({"True", "False"}))
        )
        mapped_type = (
            "Boolean" if is_bool_col else
            "Float" if "float" in dtype_str else
            "Integer" if "int" in dtype_str else
            "Timestamp" if ("datetime" in dtype_str or "timestamp" in dtype_str) else
            "String"
        )

        if col.startswith("case:"):
            case_attributes[col] = {"type": mapped_type, "samples": samples}
        else:
            applicable_acts = (
                sorted(df.loc[df[col].notna(), "concept:name"].dropna().unique().tolist())
                if "concept:name" in df.columns and col != "concept:name"
                else all_activities
            )
            event_attributes[col] = {
                "type": mapped_type,
                "samples": samples,
                "applicable_activities": applicable_acts,
            }

    # 4. Khám phá các cặp sự kiện nối tiếp phổ biến (Directly-Follows Graph)
    dfg, start_acts, end_acts = pm4py.discover_dfg(df)
    # Chỉ giữ lại các cặp chuyển trạng thái xuất hiện >= 500 lần để lọc nhiễu
    frequent_transitions = [
        {"from": k[0], "to": k[1], "count": int(v)}
        for k, v in sorted(dfg.items(), key=lambda x: x[1], reverse=True)
        if v >= 500 and k[0] != k[1]
    ][:30]

    # 5. Tính Ma trận Quan hệ Hành vi (Behavioral Profile Matrix: Direct Succession, Eventually-Follows & Mutual Exclusion)
    behavioral_profile = compute_behavioral_profile_matrix(df, dfg)

    schema: Dict[str, Any] = {
        "dataset": "BPI Challenge 2017 (Consumer Loan Process)",
        "activity_aliases": {},
        "activity_descriptions": BPIC2017_ACTIVITY_DESCRIPTIONS,
        "valid_activities": all_activities,
        "activities_by_origin": activities_by_origin,
        "case_attributes": case_attributes,
        "event_attributes": event_attributes,
        "start_activities": list(start_acts.keys()),
        "end_activities": list(end_acts.keys()),
        "frequent_transitions": frequent_transitions,
        "behavioral_profile": behavioral_profile,
    }

    output_schema_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"Đã xuất Process Schema ra {output_schema_path}")
    return schema


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    default_xes = project_root / "datasets" / "BPI Challenge 2017.xes"
    default_output = project_root / "data" / "processed" / "process_schema.json"
    default_cache = project_root / "data" / "interim" / "bpic2017_events.parquet"
    extract_bpic2017_schema(default_xes, default_output, parquet_cache_path=default_cache)
