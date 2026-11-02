import json, sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, ".")
from src.evaluation.benchmark_builder import BENCHMARK_RULES

for r in BENCHMARK_RULES:
    print(f"{r['rule_id']}: {r.get('description')}")
