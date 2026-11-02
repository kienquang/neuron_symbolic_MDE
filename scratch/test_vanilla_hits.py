import json
import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path.cwd()))

from src.evaluation.experiment_runner import serialize_trace_to_text
from src.evaluation.real_llm_client import RealLLMClient

cache = json.load(open("vanilla_rag_real_cache.json", encoding="utf-8"))
items = json.load(open("data/processed/benchmark_items.json", encoding="utf-8"))
llm = RealLLMClient(cache_file="vanilla_rag_real_cache.json")

hits = 0
for idx, item in enumerate(items):
    chunk = item["retrieved_chunk"]
    df_item = pd.DataFrame(item["events"])
    df_item["time:timestamp"] = pd.to_datetime(df_item["time:timestamp"], format="ISO8601")
    trace_text = serialize_trace_to_text(df_item)
    user_prompt = (
        f"Directive Clause ({chunk['article_id']}): {chunk['text']}\n"
        f"Loan Application Execution Trace:\n{trace_text}\n\n"
        "Determine if this loan application execution trace complies with the directive clause. "
        "Respond strictly with a JSON object: {\"label\": \"ENTAILED\" | \"CONTRADICTED\" | \"BASELESS\", \"rationale\": \"...\"}"
    )
    messages = [
        {"role": "system", "content": "You are a formal compliance auditor. Always respond with a valid JSON object."},
        {"role": "user", "content": user_prompt},
    ]
    key = llm._make_key(messages, 0.0)
    if key in cache:
        hits += 1

print(f"Hits in vanilla_rag_real_cache: {hits} / {len(items)}")
