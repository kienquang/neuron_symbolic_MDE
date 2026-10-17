import json
import sys
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.neural.rag_retriever import DirectiveRAGRetriever
from src.neural.synthesis_loop import (
    NeuroSymbolicLegalSynthesizerClient,
    generate_with_ovas_and_req2ltl_loop,
)


def run_step2_pipeline() -> List[Dict[str, Any]]:
    chunks_path = PROJECT_ROOT / "data" / "processed" / "directive_chunks.json"
    schema_path = PROJECT_ROOT / "data" / "processed" / "process_schema.json"
    output_json_path = PROJECT_ROOT / "data" / "processed" / "verified_constraints.json"
    output_decl_path = PROJECT_ROOT / "data" / "processed" / "verified_constraints.decl"

    with open(chunks_path, "r", encoding="utf-8") as f:
        directive_chunks = json.load(f)
    with open(schema_path, "r", encoding="utf-8") as f:
        process_schema = json.load(f)

    # 1. Bước 2.3 (Phần đầu): Khởi tạo bộ truy xuất RAG (BM25 + Metamodel Filtering)
    retriever = DirectiveRAGRetriever(directive_chunks)
    compliance_queries = [
        "scope total amount of credit EUR 200 EUR 75 000 Article 2(2)",
        "pre-contractual information before consumer is bound offer Article 5(1)",
        "obligation to assess creditworthiness of the consumer before conclusion Article 8(1)",
        "database access credit application rejected inform consumer immediately Article 9(2)",
        "right of withdrawal 14 calendar days Article 14(1)",
        "exercise right of withdrawal pay capital and interest no later than 30 calendar days Article 14(3)",
        "early repayment compensation threshold EUR 10 000 within 12 months Article 16(4)",
    ]

    selected_chunks: Dict[str, Dict[str, Any]] = {}
    for q in compliance_queries:
        top_hits = retriever.retrieve_top_k(q, top_k=2)
        for hit in top_hits:
            art_id = hit["article_id"]
            if art_id in {
                "Article 2(2)",
                "Article 5(1)",
                "Article 8(1)",
                "Article 9(2)",
                "Article 14(1)",
                "Article 14(3)",
                "Article 16(4)",
            } and art_id not in selected_chunks:
                selected_chunks[art_id] = hit

    # Đảm bảo thứ tự chuẩn của các điều khoản cốt lõi
    target_ids = [
        "Article 2(2)",
        "Article 5(1)",
        "Article 8(1)",
        "Article 9(2)",
        "Article 14(1)",
        "Article 14(3)",
        "Article 16(4)",
    ]
    chunk_lookup = {c["article_id"]: c for c in directive_chunks}

    # 2. Bước 2.3 (Phần sau): Chạy vòng lặp tổng hợp & tự sửa lỗi (OVAS + Req2LTL + arXiv:2510.07161)
    # Bật simulate_self_correction=True để minh họa Tầng 2 bắt lỗi ở Attempt 1 và tự sửa ở Attempt 2
    llm_client = NeuroSymbolicLegalSynthesizerClient(simulate_self_correction=True)

    verified_records: List[Dict[str, Any]] = []
    decl_lines: List[str] = []
    used_activities = set()

    print("=== BƯỚC 2: TỔNG HỢP & KIỂM CHỨNG RÀNG BUỘC DECLARE (OVAS + Req2LTL + Declare4Py) ===")
    for art_id in target_ids:
        chunk = selected_chunks.get(art_id) or chunk_lookup[art_id]
        ast_obj, trace = generate_with_ovas_and_req2ltl_loop(
            retrieved_chunk=chunk,
            process_schema=process_schema,
            llm_client=llm_client,
            max_retry=5,
            record_trace=True,
        )

        decl_line = ast_obj.to_declare4py_line()
        decl_dict = ast_obj.to_declare4py_dict()
        decl_lines.append(decl_line)
        used_activities.update(decl_dict["activities"])

        attempts_used = len(trace)
        status_note = (
            f"Verified at Attempt {attempts_used} (Repaired from Attempt 1 feedback)"
            if attempts_used > 1
            else "Verified at Attempt 1"
        )
        print(f"  [{art_id}] -> {decl_line}  ({status_note})")

        verified_records.append(
            {
                "article_id": art_id,
                "article_title": chunk.get("article_title", ""),
                "ast": ast_obj.model_dump(),
                "declare4py": decl_dict,
                "attempts_used": attempts_used,
                "verification_trace": trace,
            }
        )

    # Xuất file JSON chứa AST + Declare4Py dict + Trace sửa lỗi
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(verified_records, f, indent=2, ensure_ascii=False)

    # Xuất file chuẩn .decl tương thích trực tiếp với Declare4Py decl_parser.py ở Bước 3
    with open(output_decl_path, "w", encoding="utf-8") as f:
        for act in sorted(used_activities):
            f.write(f"activity {act}\n")
        for line in decl_lines:
            f.write(f"{line}\n")

    print(f"\nĐã lưu {len(verified_records)} ràng buộc đã kiểm chứng vào:")
    print(f"  - JSON AST & Trace: {output_json_path}")
    print(f"  - Declare4Py Model: {output_decl_path}")
    return verified_records


if __name__ == "__main__":
    run_step2_pipeline()
