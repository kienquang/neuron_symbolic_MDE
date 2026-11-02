import json
import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path.cwd()))

from src.evaluation.real_llm_client import RealLLMClient
from src.evaluation.experiment_runner import serialize_trace_to_text

items = json.load(open("data/processed/benchmark_items.json", encoding="utf-8"))
missing_item = items[130]
chunk = missing_item["retrieved_chunk"]
df_item = pd.DataFrame(missing_item["events"])
df_item["time:timestamp"] = pd.to_datetime(df_item["time:timestamp"], format="ISO8601")
trace_text = serialize_trace_to_text(df_item)

user_prompt = (
    "Dựa vào văn bản luật sau, hồ sơ này TUÂN THỦ (ENTAILED), VI PHẠM (CONTRADICTED) "
    "hay KHÔNG ĐỦ DỮ LIỆU (BASELESS)?\n\n"
    f"--- VĂN BẢN LUẬT ({chunk.get('article_id', '')}) ---\n"
    f"{chunk.get('text', '')}\n\n"
    f"--- LỊCH SỬ HỒ SƠ VAY (EVENT LOG TRACE) ---\n"
    f"{trace_text}\n\n"
    'Hãy trả lời bằng duy nhất một đối tượng JSON theo định dạng: '
    '{"label": "ENTAILED" | "CONTRADICTED" | "BASELESS", "rationale": "..."}'
)

messages = [
    {
        "role": "system",
        "content": (
            "You are a direct legal compliance QA baseline. Read the legal clause and the process trace, "
            "then classify the trace into strictly one of: ENTAILED, CONTRADICTED, or BASELESS. "
            "Output valid JSON with key 'label'."
        ),
    },
    {"role": "user", "content": user_prompt},
]

llm = RealLLMClient(bypass_cache=True)
print("Testing live call for 1 missing item...")
resp = llm.chat_json(messages, temperature=0.0)
print("Response:", resp)
