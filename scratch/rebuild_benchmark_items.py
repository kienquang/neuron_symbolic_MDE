from src.evaluation.benchmark_builder import export_benchmark_json

res = export_benchmark_json(force_rebuild=True)
print("Export result:", res)
