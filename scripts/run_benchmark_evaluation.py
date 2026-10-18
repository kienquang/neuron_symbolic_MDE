"""
Script Chạy Thực nghiệm Tự động & Xuất 3 Bảng Số liệu Chuẩn cho Bài báo (RQ1, RQ2, RQ3):
- Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp (Tier 1 vs. Tier 2)
- Bảng 2 (Trả lời RQ2): Nghiên cứu Cắt bỏ Thành phần (Ablation Study - 5 cấu hình)
- Bảng 3 (Trả lời RQ3): Hiệu quả Phát hiện Ảo giác 3 Trạng thái, Giải trình & Chi phí Thời gian
"""

import json
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.evaluation.benchmark_builder import (
    build_normative_rule_benchmark,
    build_stratified_trace_benchmark,
)
from src.evaluation.experiment_runner import (
    BenchmarkExperimentLLMClient,
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
    parquet_path = PROJECT_ROOT / "data" / "interim" / "bpic2017_events.parquet"
    chunks_path = PROJECT_ROOT / "data" / "processed" / "directive_chunks.json"
    schema_path = PROJECT_ROOT / "data" / "processed" / "process_schema.json"
    out_json_path = PROJECT_ROOT / "results" / "rq1_rq2_rq3_evaluation_tables.json"
    out_md_path = PROJECT_ROOT / "results" / "rq1_rq2_rq3_paper_tables.md"

    print("=" * 96)
    print("THỰC NGHIỆM ĐÁNH GIÁ TOÀN DIỆN (RQ1, RQ2, RQ3) TRÊN DIRECTIVE 2008/48/EC & BPIC 2017")
    print("=" * 96)

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    chunks_by_id = {c["article_id"]: c for c in chunks}

    with open(schema_path, "r", encoding="utf-8") as f:
        process_schema = json.load(f)

    print("[1/5] Đang nạp nhật ký sự kiện BPIC 2017 và khởi tạo Bộ Benchmark Phân tầng...")
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

    # Khởi tạo Phần A (28 Quy tắc Luật: 10 Tier 1 + 12 Tier 2 + 6 Group 3 Baseless Traps)
    normative_rules = build_normative_rule_benchmark(chunks_by_id)
    # Khởi tạo Phần B (1.200 Hồ sơ Kiểm thử Phân tầng: 400 ENTAILED + 400 CONTRADICTED + 400 BASELESS)
    benchmark_items = build_stratified_trace_benchmark(
        df_propagated=df_propagated,
        df_raw=df_raw,
        normative_rules=normative_rules,
        target_total_items=1200,
    )
    print(
        f"      -> Đã khởi tạo {len(normative_rules)} quy tắc chuẩn (10 Tier 1, 12 Tier 2, 6 Group 3 Traps) "
        f"và {len(benchmark_items)} mẫu hồ sơ vết thực thi phân tầng."
    )

    # =========================================================================
    # [2/5] CHẠY THỰC NGHIỆM BẢNG 1 (RQ1): ĐỘ PHỨC TẠP RÀNG BUỘC (TIER 1 & TIER 2)
    # =========================================================================
    print("[2/5] Đang đánh giá RQ1 (Bảng 1 - Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp)...")
    rq1_full_table = evaluate_rq1_complexity_tiers(
        normative_rules=normative_rules,
        log_df=df_propagated,
        process_schema=process_schema,
        enable_self_correction=True,
    )
    rq1_oneshot_table = evaluate_rq1_complexity_tiers(
        normative_rules=normative_rules,
        log_df=df_propagated,
        process_schema=process_schema,
        enable_self_correction=False,
    )

    # =========================================================================
    # [3/5] CHẠY THỰC NGHIỆM BẢNG 2 (RQ2): NGHIÊN CỨU CẮT BỎ THÀNH PHẦN (ABLATION STUDY)
    # =========================================================================
    print("[3/5] Đang chạy RQ2 (Bảng 2 - Nghiên cứu Cắt bỏ Thành phần với 5 cấu hình)...")
    llm_client = BenchmarkExperimentLLMClient(log_df=df_propagated)

    # 1. Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)
    ablation_b1 = run_vanilla_rag_baseline(benchmark_items)

    # 2. Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)
    ablation_b2 = run_ablation_experiment(
        benchmark_items=benchmark_items,
        log_df=df_propagated,
        process_schema=process_schema,
        llm_client=llm_client,
        enable_l1_l2=False,
        enable_self_correction=False,
        enable_l3_roundtrip=False,
        max_retry=1,
    )

    # 3. - Pre-Verification (Tắt Tầng 1 & Tầng 2)
    ablation_no_l12 = run_ablation_experiment(
        benchmark_items=benchmark_items,
        log_df=df_propagated,
        process_schema=process_schema,
        llm_client=llm_client,
        enable_l1_l2=False,
        enable_self_correction=True,
        enable_l3_roundtrip=True,
        max_retry=5,
    )

    # 4. - Self-Correction Loop (Tắt Vòng lặp Tự sửa)
    ablation_no_sc = run_ablation_experiment(
        benchmark_items=benchmark_items,
        log_df=df_propagated,
        process_schema=process_schema,
        llm_client=llm_client,
        enable_l1_l2=True,
        enable_self_correction=False,
        enable_l3_roundtrip=True,
        max_retry=1,
    )

    # 5. Full Neuro-Symbolic Pipeline (Đề xuất)
    ablation_full = run_ablation_experiment(
        benchmark_items=benchmark_items,
        log_df=df_propagated,
        process_schema=process_schema,
        llm_client=llm_client,
        enable_l1_l2=True,
        enable_self_correction=True,
        enable_l3_roundtrip=True,
        max_retry=5,
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

    # =========================================================================
    # [4/5] TỔNG HỢP BẢNG 3 (RQ3): CHẨN ĐOÁN 3 TRẠNG THÁI, GIẢI TRÌNH & THỜI GIAN
    # =========================================================================
    print("[4/5] Đang trích xuất RQ3 (Bảng 3 - Hiệu quả Phát hiện Ảo giác 3 Trạng thái & Giải trình)...")
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
        "benchmark_metadata": {
            "total_normative_rules": len(normative_rules),
            "tier1_control_flow_rules": 10,
            "tier2_temporal_data_rules": 12,
            "group3_baseless_traps": 6,
            "total_stratified_trace_items": len(benchmark_items),
            "entailed_traces": 400,
            "contradicted_traces": 400,
            "baseless_traces": 400,
        },
        "table1_rq1_full_pipeline": rq1_full_table,
        "table1_rq1_without_self_correction": rq1_oneshot_table,
        "table2_rq2_ablation_study": rq2_table,
        "table3_rq3_diagnostic_and_efficiency": rq3_table,
    }

    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Xuất thêm file Markdown chuẩn cho bài báo
    md_lines = [
        "# Bảng Kết quả Thực nghiệm Chuẩn cho Bài báo (RQ1, RQ2, RQ3)\n",
        "## Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp\n",
        "### 1A. Khi tắt Vòng lặp Tự sửa (One-Shot Synthesis - Phân bố lỗi ban đầu của LLM)",
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
            "| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |",
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

    print("\n[5/5] TÓM TẮT KẾT QUẢ THỰC NGHIỆM (RQ1, RQ2, RQ3):")
    print("\n".join(md_lines))
    print("=" * 96)
    print(f"Đã lưu dữ liệu JSON tại    : {out_json_path}")
    print(f"Đã lưu bảng Markdown tại   : {out_md_path}")


if __name__ == "__main__":
    main()
