"""
Script thực thi Bước 4 (Step 4.1 -> 4.2 -> 4.3):
Gán nhãn Chống ảo giác 3 Trạng thái (ENTAILED / CONTRADICTED / BASELESS)
& Sinh Báo cáo Giải trình Tất định (Accountable Audit Trail) trên dữ liệu thực BPIC 2017 và Directive 2008/48/EC.
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

from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status
from src.evaluation.justification_tree import build_justification_tree
from src.evaluation.grounded_auditor import (
    DeterministicAuditNarratorClient,
    generate_accountable_explanation,
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
    layer3_report_path = PROJECT_ROOT / "results" / "layer3_conformance_report.json"
    output_path = PROJECT_ROOT / "results" / "step4_accountable_audit_reports.json"

    print("=" * 92)
    print("BƯỚC 4: GÁN NHÃN 3 TRẠNG THÁI (ENTAILED/CONTRADICTED/BASELESS) & BÁO CÁO GIẢI TRÌNH")
    print("=" * 92)

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    chunks_by_id = {c["article_id"]: c for c in chunks}

    with open(layer3_report_path, "r", encoding="utf-8") as f:
        layer3_reports = json.load(f)

    print(f"[1/4] Đang nạp bảng sự kiện BPIC 2017 từ: {parquet_path.name} ...")
    df = pd.read_parquet(parquet_path)
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True)

    # Lan truyền thuộc tính mức Offer bằng toán tử vector hóa C++ (nhanh gấp 100 lần lambda)
    present_offer_cols = [c for c in OFFER_LEVEL_COLS if c in df.columns]
    df_propagated = df.copy()
    if present_offer_cols:
        grp = df_propagated.groupby("case:concept:name", sort=False)[present_offer_cols]
        df_propagated[present_offer_cols] = grp.ffill().bfill()
        df_propagated[present_offer_cols] = (
            df_propagated.groupby("case:concept:name", sort=False)[present_offer_cols].bfill()
        )

    narrator_client = DeterministicAuditNarratorClient()
    rule_audit_summaries = []

    # Chọn trước 1 hồ sơ điển hình hoàn tất đầy đủ để kiểm tra các trường hợp ENTAILED
    default_compliant_cid = "Application_654321"
    if default_compliant_cid not in df_propagated["case:concept:name"].values:
        default_compliant_cid = str(df_propagated["case:concept:name"].iloc[0])

    print("[2/4] Đang thực thi Bước 4.1 -> 4.2 -> 4.3 cho toàn bộ các quy tắc từ Bước 3...")
    for r_idx, l3_item in enumerate(layer3_reports, start=1):
        art_id = l3_item["article_id"]
        chunk = chunks_by_id.get(
            art_id,
            {
                "article_id": art_id,
                "article_title": l3_item.get("article_title", ""),
                "text": l3_item.get("article_title", ""),
            },
        )
        status = l3_item.get("status", "VERIFIED")

        # Nếu quy tắc đã bị Bước 3.1 (Roundtrip) bác bỏ là BASELESS (VD: Article 23)
        if status == "BASELESS" or "ast" not in l3_item:
            rt_msg = l3_item.get("diagnostic_feedback", "Unsupported by directive text.")
            sample_df = df_propagated[df_propagated["case:concept:name"] == default_compliant_cid]
            trace_eval = evaluate_trace_safety_and_status(
                case_df=sample_df,
                ast_obj=None,
                roundtrip_passed=False,
                roundtrip_msg=rt_msg,
            )
            j_tree = build_justification_tree(
                trace_eval=trace_eval,
                ast_obj=None,
                retrieved_chunk=chunk,
            )
            audit_pkg = generate_accountable_explanation(
                justification_tree=j_tree,
                llm_client=narrator_client,
            )
            rule_audit_summaries.append(
                {
                    "rule_index": r_idx,
                    "article_id": art_id,
                    "article_title": l3_item.get("article_title", ""),
                    "layer3_status": status,
                    "final_declare": "N/A (Halted at Layer 3.1 Roundtrip)",
                    "population_metrics": {
                        "total_cases": 31509,
                        "activated_cases": 0,
                        "entailed_compliant_cases": 0,
                        "contradicted_violated_cases": 0,
                        "baseless_cases": 31509,
                    },
                    "audited_trace_reports": [audit_pkg],
                }
            )
            continue

        ast_obj = DeclareConstraintAST.model_validate(l3_item["ast"])
        conf = l3_item["conformance_report"]

        # Lấy các hồ sơ vi phạm (counterexamples) từ Bước 3
        counterexamples = conf.get("counterexample_snapshots", [])
        sample_case_ids = [ce["case_id"] for ce in counterexamples[:2]]
        if not sample_case_ids:
            sample_case_ids = [default_compliant_cid]

        audited_traces = []
        for cid in sample_case_ids:
            case_df = df_propagated[df_propagated["case:concept:name"] == cid]
            trace_eval = evaluate_trace_safety_and_status(
                case_df=case_df,
                ast_obj=ast_obj,
                roundtrip_passed=True,
                roundtrip_msg="Roundtrip check passed.",
            )
            j_tree = build_justification_tree(
                trace_eval=trace_eval,
                ast_obj=ast_obj,
                retrieved_chunk=chunk,
            )
            audit_pkg = generate_accountable_explanation(
                justification_tree=j_tree,
                llm_client=narrator_client,
            )
            audited_traces.append(audit_pkg)

        rule_audit_summaries.append(
            {
                "rule_index": r_idx,
                "article_id": art_id,
                "article_title": l3_item.get("article_title", ""),
                "layer3_status": status,
                "final_declare": l3_item["declare4py"]["decl_line"],
                "population_metrics": {
                    "total_cases": conf["total_cases"],
                    "activated_cases": conf["activated_cases_count"],
                    "entailed_compliant_cases": conf["satisfied_cases_count"],
                    "contradicted_violated_cases": conf["violated_cases_count"],
                    "baseless_inapplicable_or_null_cases": conf["vacuous_cases_count"],
                },
                "audited_trace_reports": audited_traces,
            }
        )

    # =========================================================================
    # [3/4] TỔNG HỢP 4 KỊCH BẢN ĐỐI CHIẾU TRỌNG TÂM (CASE STUDY CHO BÀI BÁO)
    # =========================================================================
    print("[3/4] Đang xuất 4 kịch bản Case Study chuẩn cho mục Thực nghiệm (Evaluation)...")

    # Tìm quy tắc Article 14(1) từ kết quả Bước 3
    art14_l3 = next(item for item in layer3_reports if item["article_id"] == "Article 14(1)")
    art14_chunk = chunks_by_id["Article 14(1)"]
    art14_ast = DeclareConstraintAST.model_validate(art14_l3["ast"])

    # Kịch bản 1 (CONTRADICTED - DEADLINE_EXCEEDED):
    # Hồ sơ Application_1000610355 trong BPIC 2017: O_Sent (mail and online) -> O_Returned mất 18.5 ngày (> 14 ngày)
    contradicted_cid = "Application_1000610355"
    case_df_contra = df_propagated[df_propagated["case:concept:name"] == contradicted_cid]
    eval_contra = evaluate_trace_safety_and_status(case_df_contra, art14_ast, True, "Roundtrip check passed.")
    tree_contra = build_justification_tree(eval_contra, art14_ast, art14_chunk)
    report_contra = generate_accountable_explanation(tree_contra, narrator_client)

    # Kịch bản 2 (ENTAILED - COMPLIANT_WITH_EVIDENCE):
    # Tìm 1 hồ sơ thực tế thỏa mãn Article 14(1) (có cả O_Sent (mail and online) và O_Returned trong <= 14 ngày)
    sent_cases = set(df_propagated[df_propagated["concept:name"] == "O_Sent (mail and online)"]["case:concept:name"])
    ret_cases = set(df_propagated[df_propagated["concept:name"] == "O_Returned"]["case:concept:name"])
    candidate_cids = sorted(sent_cases.intersection(ret_cases))
    eval_entailed = None
    for cand_cid in candidate_cids[:50]:
        cand_df = df_propagated[df_propagated["case:concept:name"] == cand_cid]
        cand_eval = evaluate_trace_safety_and_status(cand_df, art14_ast, True, "Roundtrip check passed.")
        if cand_eval["label"] == "ENTAILED":
            eval_entailed = cand_eval
            break
    tree_entailed = build_justification_tree(eval_entailed, art14_ast, art14_chunk)
    report_entailed = generate_accountable_explanation(tree_entailed, narrator_client)

    # Kịch bản 3 (BASELESS - MISSING_LOG_EVIDENCE_PHI_VIOLATION):
    # Trên nhật ký sự kiện gốc (chưa nội suy thuộc tính chéo), sự kiện 'O_Sent (mail and online)' của
    # hồ sơ 'Application_1000086665' bị khuyết thuộc tính 'OfferedAmount' (giá trị NaN).
    # Khi kiểm tra quy tắc yêu cầu điều kiện dữ liệu A.OfferedAmount > 0.0, Tập điều kiện an toàn Φ lập tức chặn lại.
    raw_phi_cid = "Application_1000086665"
    case_df_phi_null = df[df["case:concept:name"] == raw_phi_cid]
    ast_requiring_offered_amount = DeclareConstraintAST(
        article_id="Article 14(1)",
        template_name="Response",
        activation_activity="O_Sent (mail and online)",
        target_activity="O_Returned",
        activation_attr="OfferedAmount",
        activation_op=">",
        activation_val=0.0,
        time_min=0,
        time_max=14,
        time_unit="d",
    )
    eval_baseless_phi = evaluate_trace_safety_and_status(
        case_df=case_df_phi_null,
        ast_obj=ast_requiring_offered_amount,
        roundtrip_passed=True,
        roundtrip_msg="Roundtrip check passed.",
    )
    tree_baseless_phi = build_justification_tree(
        trace_eval=eval_baseless_phi,
        ast_obj=ast_requiring_offered_amount,
        retrieved_chunk=art14_chunk,
    )
    report_baseless_phi = generate_accountable_explanation(tree_baseless_phi, narrator_client)

    # Kịch bản 4 (BASELESS - UNSUPPORTED_BY_DIRECTIVE_TEXT):
    # Điều 23 (Penalties) quy định chế tài cấp quốc gia thành viên, không chứa quy tắc luồng sự kiện mức hồ sơ
    art23_l3 = next(item for item in layer3_reports if item["article_id"] == "Article 23")
    art23_chunk = chunks_by_id["Article 23"]
    eval_baseless_text = evaluate_trace_safety_and_status(
        case_df=case_df_contra,
        ast_obj=None,
        roundtrip_passed=False,
        roundtrip_msg=art23_l3["diagnostic_feedback"],
    )
    tree_baseless_text = build_justification_tree(
        trace_eval=eval_baseless_text,
        ast_obj=None,
        retrieved_chunk=art23_chunk,
    )
    report_baseless_text = generate_accountable_explanation(tree_baseless_text, narrator_client)

    case_study_showcase = {
        "scenario_1_contradicted_with_mcs": report_contra,
        "scenario_2_entailed_compliant": report_entailed,
        "scenario_3_baseless_missing_log_phi": report_baseless_phi,
        "scenario_4_baseless_unsupported_by_directive": report_baseless_text,
    }

    final_payload = {
        "pipeline_stage": "Step 4 - 3-Valued Anti-Hallucination Labeling & Accountable Audit Trail",
        "taxonomy_labels": ["ENTAILED", "CONTRADICTED", "BASELESS"],
        "case_study_showcase": case_study_showcase,
        "rule_level_audits": rule_audit_summaries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2, ensure_ascii=False)

    print("\n[4/4] KẾT QUẢ 4 KỊCH BẢN CASE STUDY TRỌNG TÂM:")
    for sc_name, sc_rep in case_study_showcase.items():
        print("-" * 92)
        print(
            f"  * Kịch bản: {sc_name}\n"
            f"    - Hồ sơ (case_id)       : {sc_rep['case_id']}\n"
            f"    - Nhãn 3 trạng thái     : {sc_rep['final_label']} ({sc_rep['reason_category']})\n"
            f"    - Hậu kiểm trích dẫn    : {'PASS (100%)' if sc_rep['is_citation_verified'] else 'FAIL'}\n"
            f"    - Báo cáo kiểm toán     :\n{sc_rep['natural_language_audit_report']}"
        )
    print("=" * 92)
    print(f"Đã lưu báo cáo giải trình Bước 4 tại: {output_path}")


if __name__ == "__main__":
    main()
