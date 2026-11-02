import json, re, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.evaluation.benchmark_builder import BENCHMARK_RULES

print("SO SÁNH MÔ TẢ HIỆN TẠI VÀ MÔ TẢ NGHIỆP VỤ THUẦN TÚY (KHÔNG MỚM TÊN KỸ THUẬT):")
print("=" * 80)
for r in BENCHMARK_RULES[:6]:
    rid = r["rule_id"]
    desc = r.get("description", "")
    # Remove technical code names in parentheses
    clean_desc = re.sub(r"\([A-Z][A-Za-z0-9_\s\(\)]*\)", "", desc)
    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
    print(f"[{rid}]")
    print(f"  Hiện tại (Mớm tên):   {desc}")
    print(f"  Thuần túy nghiệp vụ:  {clean_desc}")
    print()
