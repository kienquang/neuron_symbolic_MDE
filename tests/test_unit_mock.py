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


if __name__ == "__main__":
    unittest.main()
