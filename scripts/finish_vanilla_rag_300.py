import functools
import json
import hashlib
import sys
import time
from pathlib import Path
import pandas as pd

print = functools.partial(print, flush=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.real_llm_client import RealLLMClient
from src.evaluation.experiment_runner import serialize_trace_to_text, precision_recall_fscore_support

cache_path = PROJECT_ROOT / "vanilla_rag_real_cache.json"
disk_cache = {}
if cache_path.exists():
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            disk_cache = json.load(f)
    except Exception:
        disk_cache = {}

items_path = PROJECT_ROOT / "data" / "processed" / "benchmark_items.json"
with open(items_path, "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Loaded {len(items)} items from benchmark_items.json.")
print(f"Current disk cache contains {len(disk_cache)} entries.")

llm = RealLLMClient(cache_file="vanilla_rag_real_cache.json")

missing_items = []
prepared_prompts = []

for idx, item in enumerate(items):
    chunk = item["retrieved_chunk"]
    df_item = pd.DataFrame(item["events"])
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
    cache_key = hashlib.sha256(
        json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    has_cache = (
        cache_key in disk_cache
        and disk_cache[cache_key]
        and disk_cache[cache_key].strip() not in ("", "{}")
    )
    prepared_prompts.append((idx, item, messages, cache_key, has_cache))
    if not has_cache:
        missing_items.append((idx, item, messages, cache_key))

print(f"Initial status: {len(items) - len(missing_items)} / {len(items)} cached. Missing: {len(missing_items)} items.")

# Run missing items
completed_count = 0
for idx, item, messages, cache_key in missing_items:
    print(f"[{completed_count+1}/{len(missing_items)}] Calling LLM for Item {idx+1}/{len(items)} (ID: {item['benchmark_id']}, Rule: {item['rule_id']})...")
    raw_dict = llm.chat_json(messages, temperature=0.0)
    raw_res = json.dumps(raw_dict, ensure_ascii=False) if isinstance(raw_dict, dict) else str(raw_dict)
    
    if raw_res and raw_res.strip() not in ("", "{}"):
        disk_cache[cache_key] = raw_res
        with open(cache_path, "w", encoding="utf-8") as f_out:
            json.dump(disk_cache, f_out, indent=2, ensure_ascii=False)
    
    completed_count += 1
    # Small pause to respect RPM limits
    time.sleep(1.0)

print("\n--- ALL 300 ITEMS CACHED! CALCULATING BASELINE 1 METRICS ---")
y_true = []
y_pred = []
for idx, item, messages, cache_key, _ in prepared_prompts:
    gt = item["ground_truth_label"]
    y_true.append(gt)
    raw_res = disk_cache.get(cache_key, "{}")
    pred_label = "BASELESS"
    try:
        parsed = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
        cand_lbl = str(parsed.get("label") or parsed.get("verdict") or "").upper().strip()
        if cand_lbl in ("ENTAILED", "CONTRADICTED", "BASELESS"):
            pred_label = cand_lbl
    except Exception:
        pred_label = "BASELESS"
    y_pred.append(pred_label)

labels = ["ENTAILED", "CONTRADICTED", "BASELESS"]
p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
    y_true, y_pred, labels=labels, average="macro", zero_division=0
)
per_p, per_r, per_f1, per_sup = precision_recall_fscore_support(
    y_true, y_pred, labels=labels, zero_division=0
)

results = {
    "Configuration": "Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)",
    "Total_Items": len(items),
    "Macro_Precision": round(float(p_macro), 4),
    "Macro_Recall": round(float(r_macro), 4),
    "Macro_F1": round(float(f1_macro), 4),
    "Per_Class_Metrics": {
        lbl: {
            "Precision": round(float(p), 4),
            "Recall": round(float(r), 4),
            "F1-Score": round(float(f), 4),
            "Support": int(s),
        }
        for lbl, p, r, f, s in zip(labels, per_p, per_r, per_f1, per_sup)
    },
}

print(json.dumps(results, indent=2, ensure_ascii=False))

out_path = PROJECT_ROOT / "scratch" / "results_baseline1_300.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"Saved results to {out_path}!")
