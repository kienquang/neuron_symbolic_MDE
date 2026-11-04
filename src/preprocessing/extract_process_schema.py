import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union
import pandas as pd
import pm4py

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


BPIC2017_ACTIVITY_DESCRIPTIONS: Dict[str, str] = {
    "A_Create Application": "Initial creation and receipt of the credit/loan application.",
    "A_Concept": "Preliminary assessment and evaluation of the loan application concept.",
    "A_Accepted": "Preliminary approval / acceptance of the credit application by the bank.",
    "A_Complete": "Completion of loan application processing after offer returned.",
    "A_Validating": "Validation and verification stage of customer documentation and creditworthiness.",
    "A_Pending": "Loan finalized, awaiting disbursement / payout.",
    "A_Denied": "Credit application denied or rejected by the creditor.",
    "A_Cancelled": "Credit application cancelled by customer withdrawal or bank.",
    "A_Incomplete": "Application marked as incomplete pending missing documentation.",
    "A_Submitted": "Loan application submitted by applicant or broker.",
    "O_Create Offer": "Creation of a formal loan offer for the applicant.",
    "O_Created": "Loan offer document officially created and registered in the bank system.",
    "O_Sent (mail and online)": "Loan offer and pre-contractual information sent to the customer via mail and online portal.",
    "O_Sent (online only)": "Loan offer sent to the customer via online banking portal only.",
    "O_Returned": "Signed loan offer contract returned by the customer.",
    "O_Accepted": "Loan offer officially accepted and confirmed.",
    "O_Refused": "Loan offer refused or rejected.",
    "O_Cancelled": "Loan offer cancelled.",
    "W_Validate application": "Workflow task for bank clerk to manually validate application documents.",
    "W_Complete application": "Workflow task to complete application details.",
    "W_Call after offers": "Workflow task to make consultation/explanation call to applicant after offer creation.",
    "W_Call incomplete files": "Workflow task to contact applicant regarding missing files.",
    "W_Handle leads": "Workflow task to handle incoming credit leads.",
    "W_Assess potential fraud": "Workflow task to investigate potential fraud indicators.",
    "W_Personal Loan collection": "Workflow task for debt collection on personal loans.",
    "W_Shortened completion ": "Workflow task for expedited application completion.",
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

    # 3. Trích xuất Kiểu dữ liệu của các Thuộc tính (Typing Environment Γ cho Tầng 2)
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
            event_attributes[col] = {"type": mapped_type, "samples": samples}

    # 4. Khám phá các cặp sự kiện nối tiếp phổ biến (Directly-Follows Graph)
    dfg, start_acts, end_acts = pm4py.discover_dfg(df)
    # Chỉ giữ lại các cặp chuyển trạng thái xuất hiện >= 500 lần để lọc nhiễu
    frequent_transitions = [
        {"from": k[0], "to": k[1], "count": int(v)}
        for k, v in sorted(dfg.items(), key=lambda x: x[1], reverse=True)
        if v >= 500 and k[0] != k[1]
    ][:30]

    schema: Dict[str, Any] = {
        "dataset": "BPI Challenge 2017 (Consumer Loan Process)",
        "activity_aliases": {
            "A_Validated": "A_Validating",
            "A_Validating": "A_Validated",
        },
        "activity_descriptions": BPIC2017_ACTIVITY_DESCRIPTIONS,
        "valid_activities": all_activities,
        "activities_by_origin": activities_by_origin,
        "case_attributes": case_attributes,
        "event_attributes": event_attributes,
        "start_activities": list(start_acts.keys()),
        "end_activities": list(end_acts.keys()),
        "frequent_transitions": frequent_transitions,
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
