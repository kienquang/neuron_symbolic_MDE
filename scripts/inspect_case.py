"""
Công cụ Hỗ trợ Kiểm tra Thủ công (Manual Inspection Tool)
Cho phép người dùng tự tay kiểm tra chi tiết từng hồ sơ trong bộ benchmark đối sánh 300 mẫu trên 26 quy tắc.

Sử dụng:
  python scripts/inspect_case.py --stats
  python scripts/inspect_case.py --list --rule R01
  python scripts/inspect_case.py --id ENT-0001
  python scripts/inspect_case.py --id CON-0015
  python scripts/inspect_case.py --id BAS-0050
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ITEMS_PATH = PROJECT_ROOT / "data" / "processed" / "benchmark_items.json"

def load_items():
    if not ITEMS_PATH.exists():
        print(f"Lỗi: Không tìm thấy tệp {ITEMS_PATH}")
        sys.exit(1)
    with open(ITEMS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def print_stats(items):
    print("=" * 80)
    print("THỐNG KÊ TOÀN BỘ BỘ DỮ LIỆU THẨM ĐỊNH BENCHMARK (300 HỒ SƠ)")
    print("=" * 80)
    total = len(items)
    label_counts = Counter(it.get("ground_truth_label") for it in items)
    rule_counts = Counter(it.get("rule_id") for it in items)
    
    print(f"Tổng số hồ sơ trong kho dữ liệu: {total} hồ sơ")
    print("\n1. Phân bổ theo 3 trạng thái phán quyết (3-state logic):")
    print(f"   - Tuân thủ (ENTAILED)        : {label_counts.get('ENTAILED', 0)} hồ sơ (Mã từ ENT-0001 đến ENT-0100)")
    print(f"   - Vi phạm (CONTRADICTED)     : {label_counts.get('CONTRADICTED', 0)} hồ sơ (Mã từ CON-0001 đến CON-0100)")
    print(f"   - Không căn cứ (BASELESS)    : {label_counts.get('BASELESS', 0)} hồ sơ (Mã từ BAS-0001 đến BAS-0100)")
    
    print(f"\n2. Phân bổ trên {len(rule_counts)} Quy tắc Pháp lý khác nhau (R01..R30):")
    sorted_rules = sorted(rule_counts.items(), key=lambda x: x[0])
    lines = []
    for r_id, cnt in sorted_rules:
        sample_ids = [it.get("benchmark_id") for it in items if it.get("rule_id") == r_id][:3]
        lines.append(f"   * Quy tắc {r_id:<4}: {cnt:>2} hồ sơ | Ví dụ mã kiểm tra: {', '.join(sample_ids)}")
    print("\n".join(lines))
    print("=" * 80)
    print("MẸO: Chạy `python scripts/inspect_case.py --id <MÃ>` để xem chi tiết từng hồ sơ.")
    print("=" * 80)

def list_by_rule(items, target_rule):
    target_rule = target_rule.upper()
    matched = [it for it in items if it.get("rule_id") == target_rule]
    if not matched:
        print(f"Không tìm thấy hồ sơ nào thuộc quy tắc '{target_rule}'.")
        return
    print("=" * 80)
    print(f"DANH SÁCH HỒ SƠ THUỘC QUY TẮC PHÁP LÝ: {target_rule} ({len(matched)} hồ sơ)")
    print("=" * 80)
    print(f"{'Mã Hồ sơ':<12} | {'Nhãn Chuẩn (Ground Truth)':<18} | {'Nguồn gốc vết (Origin)':<25} | {'Điều luật trích dẫn'}")
    print("-" * 80)
    for it in matched:
        bid = it.get("benchmark_id")
        lbl = it.get("ground_truth_label")
        ori = it.get("trace_origin")
        art = it.get("retrieved_chunk", {}).get("article_id", "N/A")
        print(f"{bid:<12} | {lbl:<18} | {ori:<25} | {art}")
    print("=" * 80)
    print(f"Gợi ý: Chọn bất kỳ mã nào ở cột 'Mã Hồ sơ' để soi chi tiết: python scripts/inspect_case.py --id {matched[0].get('benchmark_id')}")

def inspect_case(items, benchmark_id: str):
    benchmark_id = benchmark_id.strip().upper()
    matched = [it for it in items if it.get("benchmark_id") == benchmark_id]
    if not matched:
        print(f"Không tìm thấy mẫu có benchmark_id = '{benchmark_id}'.")
        print("Gợi ý: Chạy `python scripts/inspect_case.py --stats` để xem danh sách toàn bộ các mã.")
        return

    item = matched[0]
    print("=" * 80)
    print(f"THÔNG TIN HỒ SƠ KIỂM TRA THỦ CÔNG: {item.get('benchmark_id')}")
    print("=" * 80)
    print(f"1. Nhãn Chuẩn Vàng (Ground-Truth) : {item.get('ground_truth_label')}")
    print(f"2. Mã Quy tắc Áp dụng (Rule ID)   : {item.get('rule_id')}")
    print(f"3. Nguồn gốc Vết Sự kiện (Origin) : {item.get('trace_origin')}")
    
    chunk = item.get("retrieved_chunk", {})
    print(f"\n4. Căn cứ Pháp lý (Article ID)   : {chunk.get('article_id')} - {chunk.get('article_title')}")
    print(f"   Trích dẫn Luật:\n   \"{chunk.get('text')}\"")
    
    events = item.get("events", [])
    print(f"\n5. Danh sách Sự kiện Diễn ra trong Hồ sơ ({len(events)} sự kiện):")
    print(f"{'STT':<4} | {'Thời gian (Timestamp)':<32} | {'Tên Hoạt động (Activity)':<28} | {'Thuộc tính nổi bật'}")
    print("-" * 100)
    for idx, ev in enumerate(events, start=1):
        act = ev.get("concept:name", "N/A")
        ts = ev.get("time:timestamp", "N/A")
        extras = []
        for col in ("OfferedAmount", "CreditScore", "case:RequestedAmount", "NumberOfTerms"):
            if col in ev and ev[col] is not None:
                extras.append(f"{col}={ev[col]}")
        extra_str = ", ".join(extras) if extras else "-"
        print(f"{idx:<4} | {ts:<32} | {act:<28} | {extra_str}")

    print("=" * 80)
    print("HƯỚNG DẪN KIỂM TRA BẰNG MẮT CỦA BẠN (HUMAN AUDITOR AUDIT):")
    label = item.get("ground_truth_label")
    rule_id = item.get("rule_id")
    if label == "ENTAILED":
        print(f"* Hồ sơ này là ĐÚNG / TUÂN THỦ theo quy tắc {rule_id}:")
        print("  - Bạn hãy nhìn cột 'Tên Hoạt động' và 'Thời gian'.")
        print("  - Đối chiếu với trích dẫn luật ở mục 4 xem các hoạt động bắt buộc có diễn ra đúng trình tự và thời hạn không.")
    elif label == "CONTRADICTED":
        print(f"* Hồ sơ này là SAI / VI PHẠM (được tiêm lỗi giả định) theo quy tắc {rule_id}:")
        print("  - Hãy tìm điểm bất thường: một hoạt động bắt buộc bị thiếu, hoặc thứ tự hai hoạt động bị đảo ngược,")
        print("    hoặc khoảng cách thời gian giữa hai bước vượt quá quy định của điều luật.")
    elif label == "BASELESS":
        print(f"* Hồ sơ này là KHÔNG ĐỦ CĂN CỨ (BASELESS) đối với quy tắc {rule_id}:")
        print("  - Hãy đọc kỹ trích dẫn luật ở mục 4 và nhìn vào chuỗi sự kiện ở mục 5.")
        print("  - Bạn sẽ thấy điều luật này hoàn toàn không quy định hay chi phối các sự kiện có trong hồ sơ này")
        print("    (hoặc dữ liệu cần thiết để phán xét bị thiếu/NaN), vì vậy máy kết luận BASELESS là chính xác.")
    print("=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kiểm tra thủ công từng hồ sơ vay")
    parser.add_argument("--id", type=str, default=None, help="Mã hồ sơ cụ thể (VD: ENT-0001, CON-0015, BAS-0050)")
    parser.add_argument("--rule", type=str, default=None, help="Lọc danh sách các hồ sơ theo mã quy tắc (VD: R01, R16, R23)")
    parser.add_argument("--list", action="store_true", help="Liệt kê danh sách hồ sơ")
    parser.add_argument("--stats", action="store_true", help="Hiển thị thống kê tổng quan 300 hồ sơ và 26 quy tắc")
    args = parser.parse_args()

    items = load_items()

    if args.stats:
        print_stats(items)
    elif args.rule:
        list_by_rule(items, args.rule)
    elif args.id:
        inspect_case(items, args.id)
    else:
        # Mặc định hiển thị thống kê và ví dụ
        print_stats(items)
