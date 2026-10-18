"""
Unit Tests cho Bước 4 (Step 4.1, 4.2, 4.3):
- Bước 4.1: Kiểm tra Tập điều kiện An toàn Φ & Gán nhãn 3 Trạng thái (ENTAILED / CONTRADICTED / BASELESS)
- Bước 4.2: Dựng Cây Biện minh Tất định (Justification Tree) & Tập Sửa lỗi Tối thiểu (MCS)
- Bước 4.3: Sinh Báo cáo Giải trình có Khóa Nguồn & Chốt chặn Hậu kiểm (Post-hoc Grounding Guard)
"""

import unittest
import pandas as pd

from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status
from src.evaluation.justification_tree import (
    check_single_trace_semantics,
    build_justification_tree,
)
from src.evaluation.grounded_auditor import (
    DeterministicAuditNarratorClient,
    generate_accountable_explanation,
    verify_posthoc_grounding,
)


class TestPhase4AccountableAudit(unittest.TestCase):
    def setUp(self) -> None:
        self.article14_chunk = {
            "article_id": "Article 14(1)",
            "article_title": "Right of withdrawal",
            "text": "The consumer shall have a period of 14 calendar days in which to withdraw from the credit agreement without giving any reason.",
        }
        self.response_ast = DeclareConstraintAST(
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
        self.precedence_ast = DeclareConstraintAST(
            article_id="Article 8(1)",
            template_name="Precedence",
            activation_activity="W_Validate application",
            target_activity="O_Accepted",
            activation_attr="CreditScore",
            activation_op=">=",
            activation_val=0.0,
        )

    def test_step4_1_and_4_2_contradicted_deadline_exceeded(self) -> None:
        """Kiểm tra hồ sơ vi phạm thời hạn 14 ngày -> CONTRADICTED + tính đúng số ngày vượt hạn (MCS)."""
        case_df = pd.DataFrame(
            [
                {
                    "case:concept:name": "Application_654321",
                    "concept:name": "O_Sent (mail and online)",
                    "OfferedAmount": 15000.0,
                    "time:timestamp": pd.Timestamp("2016-05-01T10:00:00Z"),
                },
                {
                    "case:concept:name": "Application_654321",
                    "concept:name": "O_Returned",
                    "OfferedAmount": 15000.0,
                    "time:timestamp": pd.Timestamp("2016-05-20T14:30:00Z"),
                },
            ]
        )
        trace_eval = evaluate_trace_safety_and_status(
            case_df=case_df,
            ast_obj=self.response_ast,
            roundtrip_passed=True,
            roundtrip_msg="OK",
        )
        self.assertEqual(trace_eval["label"], "CONTRADICTED")
        self.assertEqual(trace_eval["reason_type"], "PROCESS_COMPLIANCE_VIOLATION")
        details = trace_eval["details"]
        self.assertEqual(details["violation_subtype"], "DEADLINE_EXCEEDED")
        self.assertAlmostEqual(details["actual_duration_days"], 19.19, places=2)
        self.assertEqual(details["allowed_max_days"], 14)
        self.assertIn("5.19 ngày", details["deviation_magnitude"])
        self.assertIn("5.19 ngày", details["minimal_correction_mcs"])

        tree = build_justification_tree(trace_eval, self.response_ast, self.article14_chunk)
        self.assertEqual(tree["audit_status"], "CONTRADICTED")
        self.assertEqual(tree["normative_node"]["article_id"], "Article 14(1)")
        self.assertIn("Response[O_Sent (mail and online), O_Returned]", tree["symbolic_rule_node"]["declare_formula"])

        report = generate_accountable_explanation(tree, DeterministicAuditNarratorClient())
        self.assertTrue(report["is_citation_verified"])
        self.assertIn("Application_654321", report["natural_language_audit_report"])
        self.assertIn("19.19", report["natural_language_audit_report"])

    def test_step4_1_entailed_compliant_trace(self) -> None:
        """Kiểm tra hồ sơ hoàn thành trong vòng 5 ngày (<= 14 ngày) -> ENTAILED."""
        case_df = pd.DataFrame(
            [
                {
                    "case:concept:name": "Application_111222",
                    "concept:name": "O_Sent (mail and online)",
                    "OfferedAmount": 10000.0,
                    "time:timestamp": pd.Timestamp("2016-05-01T10:00:00Z"),
                },
                {
                    "case:concept:name": "Application_111222",
                    "concept:name": "O_Returned",
                    "OfferedAmount": 10000.0,
                    "time:timestamp": pd.Timestamp("2016-05-06T10:00:00Z"),
                },
            ]
        )
        trace_eval = evaluate_trace_safety_and_status(
            case_df=case_df,
            ast_obj=self.response_ast,
            roundtrip_passed=True,
            roundtrip_msg="OK",
        )
        self.assertEqual(trace_eval["label"], "ENTAILED")
        self.assertEqual(trace_eval["reason_type"], "COMPLIANT_WITH_EVIDENCE")
        self.assertEqual(trace_eval["details"]["actual_duration_days"], 5.0)

    def test_step4_1_baseless_missing_log_phi_violation(self) -> None:
        """Kiểm tra Tập điều kiện an toàn Φ khi thuộc tính OfferedAmount bị NaN -> BASELESS."""
        case_df = pd.DataFrame(
            [
                {
                    "case:concept:name": "Application_998877",
                    "concept:name": "O_Sent (mail and online)",
                    "OfferedAmount": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T10:00:00Z"),
                },
                {
                    "case:concept:name": "Application_998877",
                    "concept:name": "O_Returned",
                    "OfferedAmount": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-03T10:00:00Z"),
                },
            ]
        )
        trace_eval = evaluate_trace_safety_and_status(
            case_df=case_df,
            ast_obj=self.response_ast,
            roundtrip_passed=True,
            roundtrip_msg="OK",
        )
        self.assertEqual(trace_eval["label"], "BASELESS")
        self.assertEqual(trace_eval["reason_type"], "MISSING_LOG_EVIDENCE_PHI_VIOLATION")
        self.assertIn("OfferedAmount", trace_eval["details"])

    def test_step4_1_baseless_unsupported_by_directive_text(self) -> None:
        """Kiểm tra khi Roundtrip phát hiện điều khoản không chứa quy tắc hoặc bịa đặt -> BASELESS."""
        case_df = pd.DataFrame(
            [
                {
                    "case:concept:name": "Application_654321",
                    "concept:name": "O_Sent (mail and online)",
                    "OfferedAmount": 15000.0,
                    "time:timestamp": pd.Timestamp("2016-05-01T10:00:00Z"),
                }
            ]
        )
        trace_eval = evaluate_trace_safety_and_status(
            case_df=case_df,
            ast_obj=self.response_ast,
            roundtrip_passed=False,
            roundtrip_msg="Dừng kiểm chứng (Semantic Hallucination): Số ['7'] không tồn tại trong Article 14(1).",
        )
        self.assertEqual(trace_eval["label"], "BASELESS")
        self.assertEqual(trace_eval["reason_type"], "UNSUPPORTED_BY_DIRECTIVE_TEXT")

    def test_step4_2_precedence_temporal_order_inversion(self) -> None:
        """Kiểm tra mẫu Precedence khi sự kiện tiền đề xảy ra muộn sau sự kiện đích -> TEMPORAL_ORDER_INVERSION."""
        case_df = pd.DataFrame(
            [
                {
                    "case:concept:name": "Application_333444",
                    "concept:name": "O_Accepted",
                    "CreditScore": 750.0,
                    "time:timestamp": pd.Timestamp("2016-06-10T08:00:00Z"),
                },
                {
                    "case:concept:name": "Application_333444",
                    "concept:name": "W_Validate application",
                    "CreditScore": 750.0,
                    "time:timestamp": pd.Timestamp("2016-06-10T14:00:00Z"),
                },
            ]
        )
        is_ok, info = check_single_trace_semantics(case_df, self.precedence_ast)
        self.assertFalse(is_ok)
        self.assertEqual(info["violation_subtype"], "TEMPORAL_ORDER_INVERSION")
        self.assertIn("6.0 giờ", info["deviation_magnitude"])

    def test_step4_3_posthoc_grounding_guard_catches_hallucination(self) -> None:
        """Kiểm tra chốt chặn hậu kiểm phát hiện khi văn bản giải trình sửa sai case_id hoặc số ngày."""
        j_tree = {
            "audit_status": "CONTRADICTED",
            "reason_category": "PROCESS_COMPLIANCE_VIOLATION",
            "normative_node": {
                "directive": "Directive 2008/48/EC",
                "article_id": "Article 14(1)",
                "verbatim_quote": "14 calendar days...",
            },
            "symbolic_rule_node": {
                "declare_formula": "Response[O_Sent (mail and online), O_Returned] | A.OfferedAmount > 0 | | 0,14,d",
                "template": "Response",
            },
            "trace_evidence_node": {
                "case_id": "Application_654321",
                "proof_or_counterexample": {
                    "actual_duration_days": 19.19,
                    "allowed_max_days": 14,
                },
            },
        }
        # Câu giải thích bịa đặt sai số ngày (25 ngày thay vì 19.19) và sai trạng thái
        bad_explanation = "Hồ sơ Application_654321 vi phạm Article 14(1) với thời gian 25 ngày (ENTAILED)."
        guard_res = verify_posthoc_grounding(j_tree, bad_explanation)
        self.assertFalse(guard_res["is_citation_verified"])
        self.assertTrue(len(guard_res["missing_anchors"]) >= 2)


if __name__ == "__main__":
    unittest.main()
