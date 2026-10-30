import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

rules_path = PROJECT_ROOT / "benchmark_rules_30.json"
chunks_path = PROJECT_ROOT / "data" / "processed" / "directive_chunks.json"

with open(rules_path, "r", encoding="utf-8") as f:
    rules = json.load(f)

with open(chunks_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

chunk_map = {c["article_id"]: c for c in chunks}

print(f"TOTAL RULES: {len(rules)}\n")

for r in rules:
    art_id = r.get("article_id")
    ch = chunk_map.get(art_id)
    title = ch.get("article_title", "N/A") if ch else "N/A"
    full_text = ch.get("text", "") if ch else "NO CHUNK"
    
    print("=" * 80)
    print(f"RULE ID: {r['rule_id']} | Tier: {r.get('tier')} | Trap: {r.get('is_trap')}")
    print(f"Căn cứ: {art_id} - {title}")
    print(f"Mẫu DECLARE : {r.get('template')}")
    print(f"Hoạt động   : Act A = '{r.get('act_a')}', Act B = '{r.get('act_b')}'")
    print(f"Thuộc tính  : {r.get('attr')} {r.get('op')} {r.get('val')}")
    print(f"Thời hạn max: {r.get('time_max')} ngày")
    print(f"Mô tả bench : {r.get('description')}")
    print("-" * 80)
    print("TRÍCH DẪN ĐIỀU LUẬT GỐC (DIRECTIVE 2008/48/EC):")
    # In tối đa 300 ký tự đầu của chunk luật
    clean_text = " ".join(full_text.split())
    print(clean_text[:350] + ("..." if len(clean_text) > 350 else ""))
    print()
