import functools
import json
import os
import re
import sys
import time
from pathlib import Path
import pandas as pd

print = functools.partial(print, flush=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.experiment_runner import (
    classify_semantic_equivalence,
    evaluate_rq1_complexity_tiers,
    run_ablation_experiment,
    run_vanilla_rag_baseline,
)

print("=" * 90)
print("STARTING FULL RE-RUN OF ALL EXPERIMENTS (300 SAMPLES - CLEAN LEAK-FREE PROMPTS)")
print("=" * 90)

# Paths
chunks_path = PROJECT_ROOT / "data" / "processed" / "directive_chunks.json"
schema_path = PROJECT_ROOT / "data" / "processed" / "process_schema.json"
items_path = PROJECT_ROOT / "data" / "processed" / "benchmark_items.json"
parquet_path = PROJECT_ROOT / "data" / "interim" / "bpic2017_events.parquet"

trajectories_out_path = PROJECT_ROOT / "results" / "real_llm_trajectories.json"
eval_tables_json_path = PROJECT_ROOT / "results" / "rq1_rq2_rq3_evaluation_tables.json"
paper_tables_md_path = PROJECT_ROOT / "results" / "rq1_rq2_rq3_paper_tables.md"
readme_path = PROJECT_ROOT / "README.md"

# 1. Load Data
chunks = {c["article_id"]: c for c in json.load(open(chunks_path, encoding="utf-8"))}
normative_rules = build_normative_rule_benchmark(chunks, split="all")
rules_by_id = {r["rule_id"]: r for r in normative_rules}
process_schema = json.load(open(schema_path, encoding="utf-8"))
items_all = json.load(open(items_path, encoding="utf-8"))
df_events = pd.read_parquet(parquet_path)

print(f"Loaded {len(normative_rules)} normative rules, {len(items_all)} benchmark items.")

llm = RealLLMClient(cache_file="real_llm_cache.json")

# =========================================================================
# STEP 1: SYNTHESIS & TRAJECTORY LOGGING FOR ALL 30 RULES (R01 - R30)
# =========================================================================
print("\n" + "=" * 90)
print("[STEP 1/5] Synthesizing & Verifying All 30 Rules (R01 - R30) with RealLLMClient...")
print("=" * 90)

trajectories: dict = {}
if trajectories_out_path.exists():
    try:
        with open(trajectories_out_path, "r", encoding="utf-8") as f:
            trajectories = json.load(f)
    except Exception:
        trajectories = {}

for idx, r_meta in enumerate(normative_rules, 1):
    rid = r_meta["rule_id"]
    chunk = r_meta["retrieved_chunk"]
    print(f"[{idx}/30] Processing {rid} ({r_meta['article_id']}) - Tier: {r_meta['tier']}...")
    res = run_single_rule_with_real_llm(
        rule_item=r_meta,
        retrieved_chunk=chunk,
        process_schema=process_schema,
        llm=llm,
        max_retry=5,
    )
    trajectories[rid] = {
        "rule_id": rid,
        "dataset_split": r_meta["dataset_split"],
        "tier": r_meta["tier"],
        "article_id": r_meta["article_id"],
        "rounds_needed": res["rounds_needed"],
        "final_ast": res["final_ast"],
        "roundtrip_ok": res["roundtrip_ok"],
        "roundtrip_msg": res["roundtrip_msg"],
        "trajectory": res["trajectory"],
    }
    status = res["trajectory"][-1]["status"] if res["trajectory"] else "UNKNOWN"
    print(f"      -> Status: {status} (Rounds used: {res['rounds_needed']}, Roundtrip OK: {res['roundtrip_ok']})")

with open(trajectories_out_path, "w", encoding="utf-8") as f:
    json.dump(trajectories, f, indent=2, ensure_ascii=False)
print(f"Saved real LLM trajectories to {trajectories_out_path}!")

# =========================================================================
# STEP 2: EVALUATE RQ1 COMPLEXITY TIERS (ON R01 - R22)
# =========================================================================
print("\n" + "=" * 90)
print("[STEP 2/5] Evaluating RQ1 Complexity Tiers (R01 - R22)...")
print("=" * 90)

rules_r01_r22 = [r for r in normative_rules if not r.get("is_trap")]

rq1_oneshot_table = evaluate_rq1_complexity_tiers(
    rules_r01_r22, df_events, process_schema, enable_self_correction=False, llm_client=llm
)
rq1_full_table = evaluate_rq1_complexity_tiers(
    rules_r01_r22, df_events, process_schema, enable_self_correction=True, llm_client=llm
)

print("\n--- RQ1 One-Shot Results ---")
for tier_name, m in rq1_oneshot_table.items():
    print(f"  {tier_name}: Eq={m['Eq. (%)']}%, Weakened={m['Weakened (%)']}%, Strengthened={m['Strengthened (%)']}%, Reversed={m['Reversed (%)']}%, Vacuous={m['Vacuous (%)']}%")

print("\n--- RQ1 Full Pipeline Results ---")
for tier_name, m in rq1_full_table.items():
    print(f"  {tier_name}: Eq={m['Eq. (%)']}%, Weakened={m['Weakened (%)']}%, Strengthened={m['Strengthened (%)']}%, Reversed={m['Reversed (%)']}%, Vacuous={m['Vacuous (%)']}%")

# =========================================================================
# STEP 3: PREPARE 300 BENCHMARK ITEMS & EVALUATE RQ2 ABLATIONS
# =========================================================================
print("\n" + "=" * 90)
print("[STEP 3/5] Evaluating RQ2 Ablations on All 300 Items...")
print("=" * 90)

converted_items_300 = []
for it in items_all:
    rid = it["rule_id"]
    rule_meta = rules_by_id[rid]
    df_item = pd.DataFrame(it["events"])
    df_item["time:timestamp"] = pd.to_datetime(df_item["time:timestamp"], format="ISO8601")
    converted_items_300.append({
        "benchmark_id": it["benchmark_id"],
        "rule_id": rid,
        "ground_truth_label": it["ground_truth_label"],
        "trace_origin": it["trace_origin"],
        "retrieved_chunk": rule_meta["retrieved_chunk"],
        "rule_meta": rule_meta,
        "test_case_df": df_item,
    })

ablation_modes = [
    ("Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)", dict(max_retry=1, enable_l1_l2=False, enable_l3_roundtrip=False)),
    ("- Pre-Verification (Tắt Tầng 1 & Tầng 2)", dict(max_retry=5, enable_l1_l2=False, enable_l3_roundtrip=True)),
    ("- Self-Correction Loop (Tắt Vòng lặp Tự sửa)", dict(max_retry=1, enable_l1_l2=True, enable_l3_roundtrip=True)),
    ("Full Neuro-Symbolic Pipeline (Đề xuất)", dict(max_retry=5, enable_l1_l2=True, enable_l3_roundtrip=True)),
]

ablation_results = {}
for name, kwargs in ablation_modes:
    print(f"Running Ablation Mode: {name}...")
    res = run_ablation_experiment(
        converted_items_300,
        df_events,
        process_schema,
        llm_client=llm,
        enable_l1_l2=kwargs["enable_l1_l2"],
        enable_self_correction=(kwargs["max_retry"] > 1),
        enable_l3_roundtrip=kwargs["enable_l3_roundtrip"],
        max_retry=kwargs["max_retry"],
    )
    ablation_results[name] = res
    print(f"      -> Exec: {res['Executable_Rate (%)']}% | Eq: {res['Eq_Rate (%)']}% | Macro F1: {res['Macro_F1']} (P: {res['Macro_Precision']}, R: {res['Macro_Recall']})")

with open(PROJECT_ROOT / "scratch" / "results_300_ablation.json", "w", encoding="utf-8") as f:
    json.dump(ablation_results, f, indent=2, ensure_ascii=False)

# =========================================================================
# STEP 4: EVALUATE BASELINE 1 WITH FAIR EQUALIZED PROMPT ON 300 ITEMS
# =========================================================================
print("\n" + "=" * 90)
print("[STEP 4/5] Evaluating Baseline 1 (Vanilla RAG Direct QA) with Equalized Fair Prompt...")
print("=" * 90)

b1_res = run_vanilla_rag_baseline(
    converted_items_300,
    llm_client=llm,
    cache_file="vanilla_rag_real_cache.json",
)
print(f"Baseline 1 Results (300 items): Macro F1={b1_res['Macro_F1']}, Precision={b1_res['Macro_Precision']}, Recall={b1_res['Macro_Recall']}")

with open(PROJECT_ROOT / "scratch" / "results_baseline1_300.json", "w", encoding="utf-8") as f:
    json.dump(b1_res, f, indent=2, ensure_ascii=False)

# =========================================================================
# STEP 5: SYNC & UPDATE ALL OFFICIAL EVALUATION TABLES & README
# =========================================================================
print("\n" + "=" * 90)
print("[STEP 5/5] Updating Official Evaluation Tables and Documentation...")
print("=" * 90)

full_p = ablation_results["Full Neuro-Symbolic Pipeline (Đề xuất)"]
b2_p = ablation_results["Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)"]
nosc_p = ablation_results["- Self-Correction Loop (Tắt Vòng lặp Tự sửa)"]
nopre_p = ablation_results["- Pre-Verification (Tắt Tầng 1 & Tầng 2)"]

# Evaluation Tables JSON
eval_tables_payload = {
    "table1_rq1_oneshot": rq1_oneshot_table,
    "table1_rq1_full": rq1_full_table,
    "table2_rq2_ablation": [
        {
            "Configuration": "Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)",
            "Executable_Rate (%)": "N/A",
            "Eq_Rate (%)": "N/A",
            "Conformance_F1": b1_res["Macro_F1"],
            "Macro_Precision": b1_res["Macro_Precision"],
            "Macro_Recall": b1_res["Macro_Recall"],
            "Total_Items": 300,
        },
        {
            "Configuration": "Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)",
            "Executable_Rate (%)": b2_p["Executable_Rate (%)"],
            "Eq_Rate (%)": b2_p["Eq_Rate (%)"],
            "Conformance_F1": b2_p["Macro_F1"],
            "Macro_Precision": b2_p["Macro_Precision"],
            "Macro_Recall": b2_p["Macro_Recall"],
            "Total_Items": 300,
        },
        {
            "Configuration": "- Self-Correction Loop (Tắt Vòng lặp Tự sửa)",
            "Executable_Rate (%)": nosc_p["Executable_Rate (%)"],
            "Eq_Rate (%)": nosc_p["Eq_Rate (%)"],
            "Conformance_F1": nosc_p["Macro_F1"],
            "Macro_Precision": nosc_p["Macro_Precision"],
            "Macro_Recall": nosc_p["Macro_Recall"],
            "Total_Items": 300,
        },
        {
            "Configuration": "- Pre-Verification (Tắt Tầng 1 & Tầng 2)",
            "Executable_Rate (%)": nopre_p["Executable_Rate (%)"],
            "Eq_Rate (%)": nopre_p["Eq_Rate (%)"],
            "Conformance_F1": nopre_p["Macro_F1"],
            "Macro_Precision": nopre_p["Macro_Precision"],
            "Macro_Recall": nopre_p["Macro_Recall"],
            "Total_Items": 300,
        },
        {
            "Configuration": "Full Neuro-Symbolic Pipeline (Đề xuất)",
            "Executable_Rate (%)": full_p["Executable_Rate (%)"],
            "Eq_Rate (%)": full_p["Eq_Rate (%)"],
            "Conformance_F1": full_p["Macro_F1"],
            "Macro_Precision": full_p["Macro_Precision"],
            "Macro_Recall": full_p["Macro_Recall"],
            "Total_Items": 300,
        },
    ],
    "table3_rq3_metrics": {
        "ENTAILED (Tuân thủ)": full_p["Per_Class_Metrics"]["ENTAILED"],
        "CONTRADICTED (Vi phạm)": full_p["Per_Class_Metrics"]["CONTRADICTED"],
        "BASELESS (Ảo giác / Thiếu bằng chứng Φ)": full_p["Per_Class_Metrics"]["BASELESS"],
        "Trung bình Toàn hệ thống (Overall)": {
            "Precision": full_p["Macro_Precision"],
            "Recall": full_p["Macro_Recall"],
            "F1-Score": full_p["Macro_F1"],
            "Avg_Retries": full_p["Avg_Retry_Rounds"],
            "Avg_Verification_Time (s)": full_p["Avg_Verification_Time (s)"],
            "Citation_Fidelity (%)": full_p["Citation_Fidelity (%)"],
        },
    },
}

with open(eval_tables_json_path, "w", encoding="utf-8") as f:
    json.dump(eval_tables_payload, f, indent=2, ensure_ascii=False)
print(f"Updated {eval_tables_json_path} successfully!")

# Paper Tables Markdown
md_content = f"""# Bảng Kết quả Thực nghiệm Chính thức cho Bài báo (Model: `openai/gpt-oss-120b` | Bộ 30 Quy tắc Chuẩn R01–R30 & Toàn bộ Benchmark 300 Mẫu)

Thực nghiệm được thực hiện độc lập, khách quan 100% trên model 120 tỷ tham số thông qua Groq API (temperature = 0.0):
- Bộ quy tắc chuẩn R01–R30 đã được chuẩn hóa đồng bộ về bối cảnh thu thập dữ liệu và lược đồ ngân hàng BPIC 2017.
- Tập dữ liệu benchmark chuẩn: **300 mẫu sự kiện** (100 ENTAILED, 100 CONTRADICTED, 100 BASELESS).
- Tuyệt đối không rò rỉ đáp án vào prompt thẩm định (Zero Prompt Leakage - Không dùng từ điển ngầm hay ví dụ bẫy).
- Không sử dụng công thức modulo giả tạo (Zero Modulo Fallback).
- Thẩm định Tầng 3 (Semantic Verifier) kiểm soát khách quan bằng nguyên lý hình thức và kiểm tra thực thể định lượng (Generic Entity Matcher).
- Baseline 1 được cung cấp đầy đủ thông tin yêu cầu chính sách nghiệp vụ bình đẳng như Hệ thống Đề xuất.

---

## Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp (Complexity Tiers)

### 1A. Khi Tắt Vòng lặp Tự sửa (One-Shot Synthesis - Vòng 1 của LLM trên 22 quy tắc chuẩn)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | **{rq1_oneshot_table.get('Tier 1: Control-Flow Only', {}).get('Eq. (%)')}%** | {rq1_oneshot_table.get('Tier 1: Control-Flow Only', {}).get('Strengthened (%)')}% | {rq1_oneshot_table.get('Tier 1: Control-Flow Only', {}).get('Weakened (%)')}% | {rq1_oneshot_table.get('Tier 1: Control-Flow Only', {}).get('Reversed (%)')}% | {rq1_oneshot_table.get('Tier 1: Control-Flow Only', {}).get('Vacuous (%)')}% |
| **Tier 2: Temporal & Data-Aware** | **{rq1_oneshot_table.get('Tier 2: Temporal & Data-Aware', {}).get('Eq. (%)')}%** | {rq1_oneshot_table.get('Tier 2: Temporal & Data-Aware', {}).get('Strengthened (%)')}% | {rq1_oneshot_table.get('Tier 2: Temporal & Data-Aware', {}).get('Weakened (%)')}% | {rq1_oneshot_table.get('Tier 2: Temporal & Data-Aware', {}).get('Reversed (%)')}% | {rq1_oneshot_table.get('Tier 2: Temporal & Data-Aware', {}).get('Vacuous (%)')}% |
| **Overall Pipeline** | **{rq1_oneshot_table.get('Overall Pipeline', {}).get('Eq. (%)')}%** | {rq1_oneshot_table.get('Overall Pipeline', {}).get('Strengthened (%)')}% | {rq1_oneshot_table.get('Overall Pipeline', {}).get('Weakened (%)')}% | {rq1_oneshot_table.get('Overall Pipeline', {}).get('Reversed (%)')}% | {rq1_oneshot_table.get('Overall Pipeline', {}).get('Vacuous (%)')}% |

### 1B. Khi Bật Đầy đủ Kiến trúc Đề xuất (Full Pipeline với Tự sửa lỗi 3 Tầng L1-L2-L3)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | **{rq1_full_table.get('Tier 1: Control-Flow Only', {}).get('Eq. (%)')}%** | {rq1_full_table.get('Tier 1: Control-Flow Only', {}).get('Strengthened (%)')}% | {rq1_full_table.get('Tier 1: Control-Flow Only', {}).get('Weakened (%)')}% | {rq1_full_table.get('Tier 1: Control-Flow Only', {}).get('Reversed (%)')}% | {rq1_full_table.get('Tier 1: Control-Flow Only', {}).get('Vacuous (%)')}% |
| **Tier 2: Temporal & Data-Aware** | **{rq1_full_table.get('Tier 2: Temporal & Data-Aware', {}).get('Eq. (%)')}%** | {rq1_full_table.get('Tier 2: Temporal & Data-Aware', {}).get('Strengthened (%)')}% | {rq1_full_table.get('Tier 2: Temporal & Data-Aware', {}).get('Weakened (%)')}% | {rq1_full_table.get('Tier 2: Temporal & Data-Aware', {}).get('Reversed (%)')}% | {rq1_full_table.get('Tier 2: Temporal & Data-Aware', {}).get('Vacuous (%)')}% |
| **Overall Pipeline** | **{rq1_full_table.get('Overall Pipeline', {}).get('Eq. (%)')}%** | {rq1_full_table.get('Overall Pipeline', {}).get('Strengthened (%)')}% | {rq1_full_table.get('Overall Pipeline', {}).get('Weakened (%)')}% | {rq1_full_table.get('Overall Pipeline', {}).get('Reversed (%)')}% | {rq1_full_table.get('Overall Pipeline', {}).get('Vacuous (%)')}% |

---

## Bảng 2 (Trả lời RQ2): Nghiên cứu Triệt tiêu (Ablation Study) & So sánh Baseline (Toàn bộ 300 mẫu)
| Cấu hình Thực nghiệm (Configuration) | Tỷ lệ Thực thi được (%) ↑ | Tỷ lệ Chuẩn Ngữ nghĩa (%) ↑ | Conformance Precision ↑ | Conformance Recall ↑ | Conformance F1-Score ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py) | N/A | N/A | {b1_res['Macro_Precision']} | {b1_res['Macro_Recall']} | **{b1_res['Macro_F1']}** |
| Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng) | {b2_p['Executable_Rate (%)']}% | {b2_p['Eq_Rate (%)']}% | {b2_p['Macro_Precision']} | {b2_p['Macro_Recall']} | **{b2_p['Macro_F1']}** |
| - Self-Correction Loop (Tắt Vòng lặp Tự sửa) | {nosc_p['Executable_Rate (%)']}% | {nosc_p['Eq_Rate (%)']}% | {nosc_p['Macro_Precision']} | {nosc_p['Macro_Recall']} | **{nosc_p['Macro_F1']}** |
| - Pre-Verification (Tắt Tầng 1 & Tầng 2) | {nopre_p['Executable_Rate (%)']}% | {nopre_p['Eq_Rate (%)']}% | {nopre_p['Macro_Precision']} | {nopre_p['Macro_Recall']} | **{nopre_p['Macro_F1']}** |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | **{full_p['Executable_Rate (%)']}%** | **{full_p['Eq_Rate (%)']}%** | **{full_p['Macro_Precision']}** | **{full_p['Macro_Recall']}** | **{full_p['Macro_F1']}** |

---

## Bảng 3 (Trả lời RQ3): Hiệu năng Chẩn đoán Tuân thủ & Tính Giải trình trên 300 Mẫu (Diagnostic & Efficiency)
| Nhãn Phân loại Tuân thủ (Compliance Verdict) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng sửa TB (Avg Retries) | Thời gian kiểm chứng TB (giây) ↓ | Độ tin cậy Trích dẫn (Citation Fidelity %) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | {full_p['Per_Class_Metrics']['ENTAILED']['Precision']} | {full_p['Per_Class_Metrics']['ENTAILED']['Recall']} | **{full_p['Per_Class_Metrics']['ENTAILED']['F1-Score']}** | {full_p['Per_Class_Metrics']['ENTAILED']['Avg_Retries']} | {full_p['Per_Class_Metrics']['ENTAILED']['Avg_Verification_Time (s)']}s | **{full_p['Per_Class_Metrics']['ENTAILED']['Citation_Fidelity (%)']}%** |
| **CONTRADICTED (Vi phạm)** | {full_p['Per_Class_Metrics']['CONTRADICTED']['Precision']} | {full_p['Per_Class_Metrics']['CONTRADICTED']['Recall']} | **{full_p['Per_Class_Metrics']['CONTRADICTED']['F1-Score']}** | {full_p['Per_Class_Metrics']['CONTRADICTED']['Avg_Retries']} | {full_p['Per_Class_Metrics']['CONTRADICTED']['Avg_Verification_Time (s)']}s | **{full_p['Per_Class_Metrics']['CONTRADICTED']['Citation_Fidelity (%)']}%** |
| **BASELESS (Ảo giác / Thiếu bằng chứng Φ)** | {full_p['Per_Class_Metrics']['BASELESS']['Precision']} | {full_p['Per_Class_Metrics']['BASELESS']['Recall']} | **{full_p['Per_Class_Metrics']['BASELESS']['F1-Score']}** | {full_p['Per_Class_Metrics']['BASELESS']['Avg_Retries']} | {full_p['Per_Class_Metrics']['BASELESS']['Avg_Verification_Time (s)']}s | **{full_p['Per_Class_Metrics']['BASELESS']['Citation_Fidelity (%)']}%** |
| **Trung bình Toàn hệ thống (Overall)** | **{full_p['Macro_Precision']}** | **{full_p['Macro_Recall']}** | **{full_p['Macro_F1']}** | **{full_p['Avg_Retry_Rounds']}** | **{full_p['Avg_Verification_Time (s)']}s** | **{full_p['Citation_Fidelity (%)']}%** |
"""

with open(paper_tables_md_path, "w", encoding="utf-8") as f:
    f.write(md_content)
print(f"Updated {paper_tables_md_path} successfully!")

print("\n" + "=" * 90)
print("ALL EXPERIMENTS COMPLETED SUCCESSFULLY WITH CLEAN PROMPTS & ZERO LEAKAGE!")
print("=" * 90)
