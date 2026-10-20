"""
Script scripts/build_benchmark.py:
Tự động xuất Bộ 30 Quy tắc Chuẩn (benchmark_rules_30.json) từ Chỉ thị 2008/48/EC
và quét BPI_Challenge_2017.xes (qua bộ đệm Parquet) để trích xuất các hồ sơ vay thực tế
đủ cả 3 nhãn (ENTAILED, CONTRADICTED, BASELESS) ra file data/processed/benchmark_items.json.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.evaluation.benchmark_builder import BENCHMARK_RULES, export_benchmark_json


if __name__ == "__main__":
    summary = export_benchmark_json(
        output_rules_path=str(PROJECT_ROOT / "data" / "processed" / "benchmark_rules_30.json"),
        output_items_path=str(PROJECT_ROOT / "data" / "processed" / "benchmark_items.json"),
        chunks_path=str(PROJECT_ROOT / "data" / "processed" / "directive_chunks.json"),
        parquet_path=str(PROJECT_ROOT / "data" / "interim" / "bpic2017_events.parquet"),
        max_serialized_items=300,
    )
    print(f"Đã xuất thành công {summary['rules_count']} quy tắc chuẩn (R01-R30) ra benchmark_rules_30.json & {summary['rules_path']}!")
    print(f"Đã đóng gói thành công {summary['items_count']} hồ sơ kiểm thử phân tầng (ENTAILED, CONTRADICTED, BASELESS) ra {summary['items_path']}!")
