import sys
from pathlib import Path

# Thêm thư mục gốc của project vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.parse_directive import parse_eu_directive


def main() -> None:
    pdf_path = PROJECT_ROOT / "datasets" / "directive_2008_48_EC.pdf"
    output_json_path = PROJECT_ROOT / "data" / "processed" / "directive_chunks.json"

    chunks = parse_eu_directive(pdf_path, output_json_path)
    numeric_chunks = [c for c in chunks if c["has_numeric_bound"]]
    print(f"Tổng số điều khoản/khoản (Articles 1-24): {len(chunks)}")
    print(f"Số phân đoạn có ràng buộc định lượng/thời gian (has_numeric_bound=True): {len(numeric_chunks)}")


if __name__ == "__main__":
    main()
