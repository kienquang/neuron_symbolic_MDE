import json
import sys
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.extract_process_schema import load_bpic2017_dataframe
from src.neural.synthesis_loop import (
    NeuroSymbolicLegalSynthesizerClient,
    generate_with_three_layer_defense_loop,
)
from src.symbolic.declare4py_verifier import Declare4Py


def run_step3_pipeline() -> List[Dict[str, Any]]:
    chunks_path = PROJECT_ROOT / "data" / "processed" / "directive_chunks.json"
    schema_path = PROJECT_ROOT / "data" / "processed" / "process_schema.json"
    xes_path = PROJECT_ROOT / "datasets" / "BPI Challenge 2017.xes"
    parquet_cache_path = PROJECT_ROOT / "data" / "interim" / "bpic2017_events.parquet"
    output_report_path = PROJECT_ROOT / "results" / "layer3_conformance_report.json"

    with open(chunks_path, "r", encoding="utf-8") as f:
        directive_chunks = json.load(f)
    with open(schema_path, "r", encoding="utf-8") as f:
        process_schema = json.load(f)

    chunk_lookup = {c["article_id"]: c for c in directive_chunks}

    # 1. Nạp Event Log BPI Challenge 2017 (31.509 traces) vào Engine Declare4Py
    log_df = load_bpic2017_dataframe(xes_path, parquet_cache_path=parquet_cache_path)
    print("Đang lập chỉ mục 31.509 hồ sơ vay trong Declare4Py Engine ...")
    d4py_engine = Declare4Py(log_df=log_df)

    # 2. Khởi tạo Client với cả mô phỏng sửa lỗi Tầng 2 (Article 8(1)) và Tầng 3:
    #    - Article 14(1): Attempt 1 sai ngưỡng thời gian (time_max=30 vs 14 ngày) -> Bị Tầng 3.1 Roundtrip bắt lỗi -> Attempt 2 tự sửa!
    #    - Article 16(4): Attempt 1 đặt ngưỡng phi thực tế (OfferedAmount >= 99999999) gây 0 kích hoạt -> Bị Tầng 3.2 Vacuity Check bắt lỗi -> Attempt 2 tự sửa!
    #    - Article 23: Điều khoản hành chính xử phạt cấp nhà nước -> Bị Tầng 3.1 chặn với nhãn BASELESS!
    llm_client = NeuroSymbolicLegalSynthesizerClient(
        simulate_self_correction=True,
        simulate_layer3_correction=True,
    )

    target_ids = [
        "Article 2(2)",
        "Article 5(1)",
        "Article 8(1)",
        "Article 9(2)",
        "Article 14(1)",
        "Article 14(3)",
        "Article 16(4)",
        "Article 23",  # Kiểm tra kịch bản phát hiện BASELESS ở Tầng 3.1
    ]

    all_reports: List[Dict[str, Any]] = []
    print("\n=== BƯỚC 3: KIỂM CHỨNG TẤT ĐỊNH 3 TẦNG (ROUNDTRIP + VACUITY + DECLARE4PY CONFORMANCE) ===")

    for art_id in target_ids:
        chunk = chunk_lookup[art_id]
        result = generate_with_three_layer_defense_loop(
            retrieved_chunk=chunk,
            process_schema=process_schema,
            d4py_engine=d4py_engine,
            log_df=d4py_engine.log_df,
            llm_client=llm_client,
            max_retry=5,
        )
        all_reports.append(result)

        status = result["status"]
        attempts = result["attempts_used"]
        if status == "VERIFIED":
            conf = result["conformance_report"]
            print(
                f"  [{art_id}] PASS (Attempt {attempts}) | {conf['decl_formula']}\n"
                f"      -> Verbalized: {result['verbalized_constraint']}\n"
                f"      -> Activated Cases: {conf['activated_cases_count']}/{conf['total_cases']} | "
                f"Satisfied: {conf['satisfied_cases_count']} | Violated: {conf['violated_cases_count']} | "
                f"Vacuous: {conf['vacuous_cases_count']} | Compliance Rate: {conf['compliance_rate']}%"
            )
            if conf["counterexample_snapshots"]:
                sample_ce = conf["counterexample_snapshots"][0]
                print(
                    f"      -> Sample Counterexample Snapshot: case_id='{sample_ce['case_id']}', "
                    f"requested_amount={sample_ce['requested_amount']}, "
                    f"events_count={len(sample_ce['full_trace_sequence'])}"
                )
        else:
            print(
                f"  [{art_id}] HALTED ({status} at Attempt {attempts})\n"
                f"      -> Diagnostic: {result.get('diagnostic_feedback', '')}"
            )

    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2, ensure_ascii=False)

    print(f"\nĐã xuất Báo cáo Kiểm chứng Tầng 3 & Bản chụp Phản ví dụ ra: {output_report_path}")
    return all_reports


if __name__ == "__main__":
    run_step3_pipeline()
