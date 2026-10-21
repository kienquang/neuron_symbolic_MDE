"""
Unit Tests Giả lập (Mock Tests - `test_unit_mock.py`):
Kiểm tra độc lập xem các hàm `check_layer1_and_layer2`, `check_roundtrip_fidelity` và bộ đánh giá 3 trạng thái
có bắt đúng lỗi khi đưa dữ liệu hỏng (broken JSON / hallucinated activity / mismatched threshold) vào hay không
mà không cần tốn quota gọi API thực tế.
"""

import json
import unittest
from pathlib import Path
import pandas as pd

from src.evaluation.benchmark_builder import (
    BENCHMARK_RULES,
    build_normative_rule_benchmark,
    build_stratified_trace_benchmark,
)
from src.evaluation.experiment_runner import (
    BenchmarkExperimentLLMClient,
    check_layer1_and_layer2,
    evaluate_rq1_complexity_tiers,
    run_ablation_experiment,
    run_vanilla_rag_baseline,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestUnitMock(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(PROJECT_ROOT / "data" / "processed" / "directive_chunks.json", "r", encoding="utf-8") as f:
            chunks = json.load(f)
        cls.chunks_by_id = {c["article_id"]: c for c in chunks}

        with open(PROJECT_ROOT / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            cls.process_schema = json.load(f)

        cls.normative_rules = build_normative_rule_benchmark(cls.chunks_by_id)

    def test_check_layer1_and_layer2_catches_broken_inputs(self) -> None:
        """Kiểm tra check_layer1_and_layer2 bắt chính xác lỗi cú pháp Tầng 1 và lỗi kiểu/thực thể Tầng 2."""
        chunk = self.chunks_by_id["Article 14(1)"]

        # 1. Đưa vào Template không tồn tại (Lỗi Tầng 1 Closed Enum)
        broken_t1 = json.dumps(
            {
                "article_id": "Article 14(1)",
                "template_name": "Invalid_Template_XYZ",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "O_Returned",
            }
        )
        ok1, err1 = check_layer1_and_layer2(broken_t1, self.process_schema, chunk)
        self.assertFalse(ok1)
        self.assertIn("Layer 1", str(err1))

        # 2. Đưa vào Tên hoạt động bịa đặt không có trong Log Schema (Lỗi Tầng 2 Unknown Activity)
        broken_t2_act = json.dumps(
            {
                "article_id": "Article 14(1)",
                "template_name": "Response",
                "activation_activity": "W_Verify_Withdrawal_Signature",
                "target_activity": "O_Returned",
            }
        )
        ok2, err2 = check_layer1_and_layer2(broken_t2_act, self.process_schema, chunk)
        self.assertFalse(ok2)
        self.assertIn("W_Verify_Withdrawal_Signature", str(err2))

        # 3. Đưa vào Thuộc tính không có trong Log Schema Γ (Lỗi Tầng 2 Unknown Attribute - Bẫy R27/R28)
        broken_t2_attr = json.dumps(
            {
                "article_id": "Article 16(2)",
                "template_name": "Existence",
                "activation_activity": "O_Create Offer",
                "activation_attr": "EarlyRepaymentCompensationFee",
                "activation_op": "<=",
                "activation_val": 1.0,
            }
        )
        ok3, err3 = check_layer1_and_layer2(broken_t2_attr, self.process_schema, chunk)
        self.assertFalse(ok3)
        self.assertIn("EarlyRepaymentCompensationFee", str(err3))

        # 4. Đưa vào JSON hợp lệ hoàn toàn cả Tầng 1 & Tầng 2
        valid_json = json.dumps(
            {
                "article_id": "Article 14(1)",
                "template_name": "Response",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "O_Returned",
                "time_min": 0,
                "time_max": 14,
                "time_unit": "d",
            }
        )
        ok4, res4 = check_layer1_and_layer2(valid_json, self.process_schema, chunk)
        self.assertTrue(ok4)
        self.assertEqual(res4["template_name"], "Response")

    def test_hardened_edge_cases_and_semantic_guards(self) -> None:
        """Kiểm tra các chốt chặn mới được tăng cường: đơn vị thời gian, ngữ cảnh phủ định, tính bất biến AST."""
        from src.symbolic.verbalizer_roundtrip import (
            extract_clause_numeric_entities,
            verify_generic_numeric_entities,
        )
        from src.evaluation.grounded_auditor import verify_posthoc_grounding
        from src.mde.constraint_ast import DeclareConstraintAST
        from src.mde.typing_environment import ProcessTypingEnvironment
        from src.neural.rag_retriever import DirectiveRAGRetriever

        # 1. Kiểm tra trích xuất từ chỉ số lượng mở rộng ("a fortnight", "three weeks")
        entities_fortnight = extract_clause_numeric_entities("The consumer has a fortnight to withdraw.")
        self.assertIn((14.0, "days"), entities_fortnight)

        entities_weeks = extract_clause_numeric_entities("The creditor shall reply within three weeks.")
        self.assertIn((21.0, "days"), entities_weeks)

        # 2. Kiểm tra phát hiện sai lệch đơn vị (14 months vs 14 days)
        chunk_days = {"article_id": "Art_X", "text": "The consumer has 14 calendar days to withdraw."}
        ast_wrong_unit = {
            "template_name": "Response",
            "activation_activity": "O_Sent (mail and online)",
            "target_activity": "O_Returned",
            "time_max": 14,
            "time_unit": "months",
        }
        ok_u, verdict_u, diag_u = verify_generic_numeric_entities(ast_wrong_unit, chunk_days)
        self.assertFalse(ok_u)
        self.assertEqual(verdict_u, "THRESHOLD_MISMATCH")
        self.assertIn("đơn vị", diag_u)

        # 3. Kiểm tra chốt chặn hậu kiểm phát hiện hiện tượng phủ định kết luận (Negation Blindness)
        j_tree = {
            "audit_status": "CONTRADICTED",
            "reason_category": "PROCESS_COMPLIANCE_VIOLATION",
            "normative_node": {"directive": "Directive 2008/48/EC", "article_id": "Article 14(1)"},
            "symbolic_rule_node": {"declare_formula": "Response[A, B]"},
            "trace_evidence_node": {
                "case_id": "Application_999",
                "proof_or_counterexample": {"actual_duration_days": 18.0, "allowed_max_days": 14},
            },
        }
        negated_text = "Hồ sơ Application_999 KHÔNG PHẢI là CONTRADICTED theo Article 14(1) với 18.0 ngày và tối đa 14 ngày."
        guard_neg = verify_posthoc_grounding(j_tree, negated_text)
        self.assertFalse(guard_neg["is_citation_verified"])
        self.assertTrue(any("negated" in m for m in guard_neg["missing_anchors"]))

        # 4. Kiểm tra phát hiện điều khoản bịa đặt lạ (Bidirectional Citation Guard)
        hallucinated_article_text = (
            "Hồ sơ Application_999 có kết luận CONTRADICTED theo Article 14(1) và Article 99 với 18.0 ngày và tối đa 14 ngày."
        )
        guard_halluc = verify_posthoc_grounding(j_tree, hallucinated_article_text)
        self.assertFalse(guard_halluc["is_citation_verified"])
        self.assertTrue(any("unauthorized_article_hallucination" in m for m in guard_halluc["missing_anchors"]))

        # 5. Kiểm tra tính bất biến (Immutable AST) trong validate_ast
        gamma = ProcessTypingEnvironment(self.process_schema)
        ast_obj = DeclareConstraintAST(
            article_id="Article 14(1)",
            template_name="Response",
            activation_activity="O_Sent (mail and online)",
            target_activity="O_Returned",
            activation_attr="A.OfferedAmount",
            activation_op=">=",
            activation_val=200.0,
        )
        ok_v, _ = gamma.validate_ast(ast_obj)
        self.assertTrue(ok_v)
        # AST đầu vào không bị đột biến thay đổi activation_attr
        self.assertEqual(ast_obj.activation_attr, "A.OfferedAmount")

        # 6. Kiểm tra candidate_attrs trong RAG Retriever không chứa thuộc tính lạ ngoài schema
        filtered = DirectiveRAGRetriever.filter_relevant_schema(chunk_days, self.process_schema)
        valid_schema_attrs = set(self.process_schema.get("case_attributes", {}).keys()) | set(
            self.process_schema.get("event_attributes", {}).keys()
        )
        valid_schema_attrs |= {k.replace("case:", "", 1) for k in self.process_schema.get("case_attributes", {}).keys()}
        for attr in filtered["recommended_attributes"]:
            self.assertIn(attr, valid_schema_attrs)


if __name__ == "__main__":
    unittest.main()
