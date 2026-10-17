import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.extract_process_schema import extract_bpic2017_schema


def main() -> None:
    xes_path = PROJECT_ROOT / "datasets" / "BPI Challenge 2017.xes"
    output_schema_path = PROJECT_ROOT / "data" / "processed" / "process_schema.json"
    parquet_cache_path = PROJECT_ROOT / "data" / "interim" / "bpic2017_events.parquet"

    schema = extract_bpic2017_schema(
        xes_path=xes_path,
        output_schema_path=output_schema_path,
        parquet_cache_path=parquet_cache_path,
    )

    print(f"Tổng số hoạt động (valid_activities): {len(schema['valid_activities'])}")
    for origin, acts in schema.get("activities_by_origin", {}).items():
        print(f"  - Phân hệ {origin}: {len(acts)} hoạt động")
    print(f"Số thuộc tính mức hồ sơ (case_attributes): {len(schema['case_attributes'])}")
    print(f"Số thuộc tính mức sự kiện (event_attributes): {len(schema['event_attributes'])}")
    print(f"Số cặp chuyển trạng thái phổ biến (frequent_transitions): {len(schema['frequent_transitions'])}")


if __name__ == "__main__":
    main()
