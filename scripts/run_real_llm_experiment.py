"""
Kịch bản Thực thi Thực nghiệm Chính thức với Model Thật (Groq API / OpenAI / Gemini / Ollama)
trên toàn bộ 30 Quy tắc Chuẩn (R01 -> R30):
1. Khởi tạo `RealLLMClient` ở `temperature = 0.0` (Mục 4.1.2 bài OCL2026) kèm Disk Cache (`real_llm_cache.json`).
2. Chạy `run_single_rule_with_real_llm` cho cả 30 quy tắc R01–R30 và lưu Nhật ký Tự sửa Thật (`results/real_llm_trajectories.json`).
3. Chạy thực nghiệm đánh giá RQ1, RQ2, RQ3 với `RealLLMClient` trên 1.200 mẫu đối sánh Quy tắc – Hồ sơ vay (`BPI Challenge 2017.xes`)
   và xuất bảng kết quả vào `results/rq1_rq2_rq3_evaluation_tables.json` & `results/rq1_rq2_rq3_paper_tables.md`.
"""

import argparse
import json
import os
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

from src.evaluation.benchmark_builder import (
    build_normative_rule_benchmark,
    build_stratified_trace_benchmark,
    export_benchmark_json,
)
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.experiment_runner import (
    evaluate_rq1_complexity_tiers,
    run_ablation_experiment,
    run_vanilla_rag_baseline,
)


OFFER_LEVEL_COLS = [
    "OfferedAmount",
    "CreditScore",
    "Accepted",
    "MonthlyCost",
    "NumberOfTerms",
    "FirstWithdrawalAmount",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy thực nghiệm 30 quy tắc R01-R30 với RealLLMClient (Groq/OpenAI/Ollama)")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        help="Base URL của OpenAI-compatible API (mặc định: Groq https://api.groq.com/openai/v1)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LLM_MODEL_NAME", "openai/gpt-oss-120b"),
        help="Tên model trên Groq/OpenAI/Ollama (mặc định: openai/gpt-oss-120b)",
    )
    parser.add_argument(
        "--cache-file",
        default="real_llm_cache.json",
        help="Đường dẫn file lưu Disk Cache phản hồi thật của LLM",
    )
    parser.add_argument(
        "--max-retry",
        type=int,
        default=5,
        help="Số vòng tự sửa tối đa cho mỗi quy tắc (mặc định: 5)",
    )
    parser.add_argument(
        "--split",
        choices=["dev", "heldout_test", "all"],
        default="dev",
        help="Tập quy tắc thực thi: 'dev' (15 quy tắc R01-R15 để phát triển) hoặc 'heldout_test' (15 quy tắc R16-R30 kiểm thử mù)",
    )
    parser.add_argument(
        "--annotations-path",
        default=None,
        help="Đường dẫn tới file JSON/CSV chứa các hồ sơ BPIC 2017 đã gán nhãn thực tế",
    )
    parser.add_argument(
        "--target-items",
        type=int,
        default=60,
        help="Tổng số mẫu hồ sơ kiểm thử phân tầng (mặc định: 60 = 20 ENTAILED + 20 CONTRADICTED + 20 BASELESS)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bỏ qua Disk Cache, ép buộc 100% request gọi trực tiếp lên Groq API",
    )
    args = parser.parse_args()

    parquet_path = PROJECT_ROOT / "data" / "interim" / "bpic2017_events.parquet"
    chunks_path = PROJECT_ROOT / "data" / "processed" / "directive_chunks.json"
    schema_path = PROJECT_ROOT / "data" / "processed" / "process_schema.json"
    trajectories_out_path = PROJECT_ROOT / "results" / "real_llm_trajectories.json"
    out_json_path = PROJECT_ROOT / "results" / "rq1_rq2_rq3_evaluation_tables.json"
    out_md_path = PROJECT_ROOT / "results" / "rq1_rq2_rq3_paper_tables.md"

    print("=" * 96)
    print(
        f"CHẠY THỰC NGHIỆM MODEL THẬT ({args.model} | split={args.split} | no_cache={args.no_cache}) TRÊN BỘ QUY TẮC CHUẨN & BPIC 2017"
    )
    print("=" * 96)

    # 1. Khởi tạo RealLLMClient (tự động đọc GROQ_API_KEY từ .env)
    llm = RealLLMClient(
        base_url=args.base_url,
        model_name=args.model,
        cache_file=args.cache_file,
        bypass_cache=args.no_cache,
    )

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    chunks_by_id = {c["article_id"]: c for c in chunks}

    with open(schema_path, "r", encoding="utf-8") as f:
        process_schema = json.load(f)

    export_benchmark_json(
        output_rules_path=str(PROJECT_ROOT / "data" / "processed" / "benchmark_rules_30.json"),
        output_items_path=str(PROJECT_ROOT / "data" / "processed" / "benchmark_items.json"),
        chunks_path=str(chunks_path),
        parquet_path=str(parquet_path),
        max_serialized_items=300,
    )
    normative_rules = build_normative_rule_benchmark(chunks_by_id, split=args.split)

    # 2. Chạy tổng hợp & ghi lại Nhật ký Tự sửa Thật (Trajectory Logging)
    print(
        f"\n[1/4] Đang chạy RealLLMClient ({args.model}) cho {len(normative_rules)} quy tắc thuộc tập '{args.split}' (max_retry={args.max_retry})..."
    )
    all_trajectories = {}
    for r_meta in normative_rules:
        rule_id = r_meta["rule_id"]
        chunk = r_meta["retrieved_chunk"]
        res = run_single_rule_with_real_llm(
            rule_item=r_meta,
            retrieved_chunk=chunk,
            process_schema=process_schema,
            llm=llm,
            max_retry=args.max_retry,
        )
        all_trajectories[rule_id] = {
            "rule_id": rule_id,
            "dataset_split": r_meta["dataset_split"],
            "tier": r_meta["tier"],
            "article_id": r_meta["article_id"],
            "rounds_needed": res["rounds_needed"],
            "final_ast": res["final_ast"],
            "roundtrip_ok": res["roundtrip_ok"],
            "roundtrip_msg": res["roundtrip_msg"],
            "trajectory": res["trajectory"],
        }
        status_tag = res["trajectory"][-1]["status"] if res["trajectory"] else "NONE"
        print(f"  - {rule_id} [{r_meta['dataset_split']}] ({r_meta['article_id']}): {status_tag} (rounds_needed={res['rounds_needed']})")

    trajectories_out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(trajectories_out_path, "w", encoding="utf-8") as f:
        json.dump(all_trajectories, f, indent=2, ensure_ascii=False)
    print(f"      -> Đã lưu Nhật ký Tự sửa Thật vào: {trajectories_out_path}")

    # 3. Tải Log BPIC 2017 và nạp mẫu đối sánh
    print("\n[2/4] Đang tải Event Log BPI Challenge 2017 và nạp mẫu đối sánh...")
    df_raw = pd.read_parquet(parquet_path)
    df_raw["time:timestamp"] = pd.to_datetime(df_raw["time:timestamp"], utc=True)

    present_offer_cols = [c for c in OFFER_LEVEL_COLS if c in df_raw.columns]
    df_propagated = df_raw.copy()
    if present_offer_cols:
        grp = df_propagated.groupby("case:concept:name", sort=False)[present_offer_cols]
        df_propagated[present_offer_cols] = grp.ffill().bfill()
        df_propagated[present_offer_cols] = (
            df_propagated.groupby("case:concept:name", sort=False)[present_offer_cols].bfill()
        )

    benchmark_items = build_stratified_trace_benchmark(
        df_propagated=df_propagated,
        df_raw=df_raw,
        normative_rules=normative_rules,
        target_total_items=args.target_items,
        split=args.split,
        annotations_path=args.annotations_path,
    )

    # 4. Đánh giá RQ1, RQ2, RQ3 với RealLLMClient
    print("\n[3/4] Đang đánh giá RQ1, RQ2 (Ablation Study) và RQ3 với RealLLMClient...")
    rq1_oneshot_table = evaluate_rq1_complexity_tiers(
        normative_rules, df_propagated, process_schema, enable_self_correction=False, llm_client=llm
    )
    rq1_full_table = evaluate_rq1_complexity_tiers(
        normative_rules, df_propagated, process_schema, enable_self_correction=True, llm_client=llm
    )

    ablation_b1 = run_vanilla_rag_baseline(
        benchmark_items,
        llm_client=llm,
        cache_file="vanilla_rag_real_cache.json",
    )
    ablation_b2 = run_ablation_experiment(
        benchmark_items,
        df_propagated,
        process_schema,
        llm_client=llm,
        enable_l1_l2=False,
        enable_self_correction=False,
        enable_l3_roundtrip=False,
        max_retry=1,
    )
    ablation_no_l12 = run_ablation_experiment(
        benchmark_items,
        df_propagated,
        process_schema,
        llm_client=llm,
        enable_l1_l2=False,
        enable_self_correction=True,
        enable_l3_roundtrip=True,
        max_retry=args.max_retry,
    )
    ablation_no_sc = run_ablation_experiment(
        benchmark_items,
        df_propagated,
        process_schema,
        llm_client=llm,
        enable_l1_l2=True,
        enable_self_correction=False,
        enable_l3_roundtrip=True,
        max_retry=1,
    )
    ablation_full = run_ablation_experiment(
        benchmark_items,
        df_propagated,
        process_schema,
        llm_client=llm,
        enable_l1_l2=True,
        enable_self_correction=True,
        enable_l3_roundtrip=True,
        max_retry=args.max_retry,
    )

    rq2_table = [
        {
            "Configuration": "Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)",
            "Executable_Rate (%)": "N/A",
            "Eq_Rate (%)": "N/A",
            "Conformance_F1": ablation_b1["Macro_F1"],
        },
        {
            "Configuration": "Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)",
            "Executable_Rate (%)": ablation_b2["Executable_Rate (%)"],
            "Eq_Rate (%)": ablation_b2["Eq_Rate (%)"],
            "Conformance_F1": ablation_b2["Macro_F1"],
        },
        {
            "Configuration": "- Pre-Verification (Tắt Tầng 1 & Tầng 2)",
            "Executable_Rate (%)": ablation_no_l12["Executable_Rate (%)"],
            "Eq_Rate (%)": ablation_no_l12["Eq_Rate (%)"],
            "Conformance_F1": ablation_no_l12["Macro_F1"],
        },
        {
            "Configuration": "- Self-Correction Loop (Tắt Vòng lặp Tự sửa)",
            "Executable_Rate (%)": ablation_no_sc["Executable_Rate (%)"],
            "Eq_Rate (%)": ablation_no_sc["Eq_Rate (%)"],
            "Conformance_F1": ablation_no_sc["Macro_F1"],
        },
        {
            "Configuration": "Full Neuro-Symbolic Pipeline (Đề xuất)",
            "Executable_Rate (%)": ablation_full["Executable_Rate (%)"],
            "Eq_Rate (%)": ablation_full["Eq_Rate (%)"],
            "Conformance_F1": ablation_full["Macro_F1"],
        },
    ]

    rq3_table = {
        "ENTAILED (Tuân thủ)": ablation_full["Per_Class_Metrics"]["ENTAILED"],
        "CONTRADICTED (Vi phạm)": ablation_full["Per_Class_Metrics"]["CONTRADICTED"],
        "BASELESS (Ảo giác / Thiếu bằng chứng Φ)": ablation_full["Per_Class_Metrics"]["BASELESS"],
        "Trung bình Toàn hệ thống (Overall)": {
            "Precision": ablation_full["Macro_Precision"],
            "Recall": ablation_full["Macro_Recall"],
            "F1-Score": ablation_full["Macro_F1"],
            "Avg_Retries": ablation_full["Avg_Retry_Rounds"],
            "Avg_Verification_Time (s)": ablation_full["Avg_Verification_Time (s)"],
            "Citation_Fidelity (%)": ablation_full["Citation_Fidelity (%)"],
        },
    }

    payload = {
        "llm_provider": {
            "base_url": args.base_url,
            "model_name": args.model,
            "cache_file": str(llm.cache_path),
            "trajectories_file": str(trajectories_out_path),
        },
        "benchmark_metadata": {
            "total_normative_rules": len(normative_rules),
            "tier1_control_flow_rules": sum(
                1 for r in normative_rules if r["complexity_tier"] == "Tier 1: Control-Flow Only"
            ),
            "tier2_temporal_data_rules": sum(
                1 for r in normative_rules if r["complexity_tier"] == "Tier 2: Temporal & Data-Aware"
            ),
            "tier3_baseless_traps": sum(1 for r in normative_rules if r.get("is_trap")),
            "total_stratified_trace_items": len(benchmark_items),
        },
        "table1_rq1_full_pipeline": rq1_full_table,
        "table1_rq1_without_self_correction": rq1_oneshot_table,
        "table2_rq2_ablation_study": rq2_table,
        "table3_rq3_diagnostic_and_efficiency": rq3_table,
    }

    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    md_lines = [
        f"# Bảng Kết quả Thực nghiệm Chuẩn cho Bài báo (Model Thật: `{args.model}` — Bộ 30 Quy tắc R01–R30)\n",
        "## Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp\n",
        "### 1A. Khi tắt Vòng lặp Tự sửa (One-Shot Synthesis - Phân bố kết quả vòng đầu của LLM trên R01–R22)",
        "| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for tier_lbl, row in rq1_oneshot_table.items():
        md_lines.append(
            f"| **{tier_lbl}** | {row['Eq. (%)']}% | {row['Strengthened (%)']}% | {row['Weakened (%)']}% | {row['Reversed (%)']}% | {row['Vacuous (%)']}% |"
        )

    md_lines.extend(
        [
            "\n### 1B. Full Neuro-Symbolic Pipeline (Sau khi qua Kiến trúc 3 Tầng & Vòng lặp Tự sửa)",
            "| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Lỏng - Weakened (%) ↓ | Quá Chặt - Strengthened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
    )
    for tier_lbl, row in rq1_full_table.items():
        md_lines.append(
            f"| **{tier_lbl}** | {row['Eq. (%)']}% | {row['Strengthened (%)']}% | {row['Weakened (%)']}% | {row['Reversed (%)']}% | {row['Vacuous (%)']}% |"
        )

    md_lines.extend(
        [
            "\n---\n",
            "## Bảng 2 (Trả lời RQ2): Nghiên cứu Cắt bỏ Thành phần (Ablation Study)\n",
            "| Cấu hình Hệ thống (Configuration) | Tỷ lệ Ràng buộc Hợp lệ Thực thi được (%) ↑ | Tỷ lệ Đúng Ngữ nghĩa - Eq. Rate (%) ↑ | Độ chính xác Kiểm tra Tuân thủ trên Log (F1-Score) ↑ |",
            "| :--- | :---: | :---: | :---: |",
        ]
    )
    for row in rq2_table:
        exec_str = f"{row['Executable_Rate (%)']}%" if row["Executable_Rate (%)"] != "N/A" else "N/A"
        eq_str = f"{row['Eq_Rate (%)']}%" if row["Eq_Rate (%)"] != "N/A" else "N/A"
        md_lines.append(
            f"| **{row['Configuration']}** | {exec_str} | {eq_str} | {row['Conformance_F1']} |"
        )

    md_lines.extend(
        [
            "\n---\n",
            "## Bảng 3 (Trả lời RQ3): Hiệu quả Phát hiện Ảo giác 3 Trạng thái, Giải trình & Chi phí Thời gian\n",
            "| Nhãn Chẩn đoán (Diagnostic Class) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng Tự sửa TB (Avg. Retries) ↓ | Thời gian Kiểm chứng Declare4Py (s) ↓ | Độ chuẩn xác Trích dẫn Giải trình (Citation Fidelity %) ↑ |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
    )
    for cls_lbl, row in rq3_table.items():
        md_lines.append(
            f"| **{cls_lbl}** | {row['Precision']} | {row['Recall']} | {row['F1-Score']} | {row['Avg_Retries']} | {row['Avg_Verification_Time (s)']}s | {row['Citation_Fidelity (%)']}% |"
        )

    with open(out_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print("\n[4/4] HOÀN TẤT THỰC NGHIỆM VỚI MODEL THẬT!")
    print("\n".join(md_lines))
    print("=" * 96)
    print(f"Đã lưu Cache phản hồi thật : {llm.cache_path}")
    print(f"Đã lưu Nhật ký Tự sửa Thật : {trajectories_out_path}")
    print(f"Đã lưu dữ liệu JSON tại    : {out_json_path}")
    print(f"Đã lưu bảng Markdown tại   : {out_md_path}")


if __name__ == "__main__":
    main()
