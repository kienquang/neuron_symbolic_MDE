import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.benchmark_builder import export_benchmark_json, BENCHMARK_RULES

print("--- 1. XÓA BỘ ĐỆM BENCHMARK CŨ ĐỂ TÁI TẠO BẢN SẠCH (BENCHMARK V2) ---")
for fpath in [
    PROJECT_ROOT / "benchmark_rules_30.json",
    PROJECT_ROOT / "data" / "processed" / "benchmark_rules_30.json",
    PROJECT_ROOT / "data" / "processed" / "benchmark_items.json",
]:
    if fpath.exists():
        fpath.unlink()
        print(f"Đã xóa: {fpath}")

print("\n--- 2. CHẠY HÀM EXPORT_BENCHMARK_JSON() ĐỂ TÁI TẠO 300 HỒ SƠ CHUẨN ---")
res = export_benchmark_json(max_serialized_items=300)
print(f"Kết quả tái tạo: {res}")

print("\n--- 3. KIỂM TRA ĐỘ TOÀN VẸN CỦA DỮ LIỆU ĐÃ TÁI TẠO ---")
items_path = PROJECT_ROOT / "data" / "processed" / "benchmark_items.json"
with open(items_path, "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Tổng số hồ sơ: {len(items)}")
from collections import Counter
counts = Counter(it["ground_truth_label"] for it in items)
print("Phân bổ nhãn:", counts)

rules_counts = Counter(it["rule_id"] for it in items)
print(f"Phân bổ trên {len(rules_counts)} quy tắc:", dict(sorted(rules_counts.items())))

# Kiểm tra 60 mẫu đầu tiên (20 mẫu mỗi loại)
dev_60 = [it for it in items if int(it["benchmark_id"].split("-")[1]) <= 20]
print(f"\nSố lượng mẫu trong tập 60 mẫu Dev: {len(dev_60)}")
dev_counts = Counter(it["ground_truth_label"] for it in dev_60)
print("Phân bổ tập 60 mẫu:", dev_counts)

print("\n--- HOÀN TẤT TÁI TẠO BENCHMARK V2 THÀNH CÔNG! ---")
