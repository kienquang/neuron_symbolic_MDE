import sys
sys.path.insert(0, ".")
import json
import re
from pathlib import Path
from scratch.test_all_natural_rules import NATURAL_POLICY_DESCRIPTIONS

builder_path = Path("src/evaluation/benchmark_builder.py")
content = builder_path.read_text(encoding="utf-8")

# Verify all 30 rules are present
assert len(NATURAL_POLICY_DESCRIPTIONS) == 30

# For each rule, replace its description in benchmark_builder.py
for rid, new_desc in NATURAL_POLICY_DESCRIPTIONS.items():
    # Find block for this rule
    pattern = rf'("rule_id":\s*"{rid}",.*?"description":\s*)"(?:\\.|[^"\\])*"'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        old_part = match.group(0)
        escaped_desc = new_desc.replace('"', '\\"')
        new_part = f'{match.group(1)}"{escaped_desc}"'
        content = content.replace(old_part, new_part)
        print(f"Updated {rid}")
    else:
        print(f"WARNING: Could not find block for {rid}")

builder_path.write_text(content, encoding="utf-8")
print("Successfully updated src/evaluation/benchmark_builder.py")

# Now load BENCHMARK_RULES from benchmark_builder and export JSONs
import sys
sys.path.insert(0, ".")
# Force re-import
if "src.evaluation.benchmark_builder" in sys.modules:
    del sys.modules["src.evaluation.benchmark_builder"]

from src.evaluation.benchmark_builder import BENCHMARK_RULES

print(f"Loaded {len(BENCHMARK_RULES)} rules from benchmark_builder.")

# Write to benchmark_rules_30.json and data/processed/benchmark_rules_30.json
for out_path in ["benchmark_rules_30.json", "data/processed/benchmark_rules_30.json"]:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(BENCHMARK_RULES, f, indent=2, ensure_ascii=False)
    print(f"Exported to {out_path}")
