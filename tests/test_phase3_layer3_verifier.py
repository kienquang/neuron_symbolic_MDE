import unittest
import pandas as pd
from src.mde.constraint_ast import DeclareConstraintAST
from src.symbolic.verbalizer_roundtrip import check_roundtrip_fidelity, verbalize_declare_ast
from src.symbolic.declare4py_verifier import Declare4Py, run_layer3_declare4py_verifier
from src.neural.synthesis_loop import (
    NeuroSymbolicLegalSynthesizerClient,
    generate_with_three_layer_defense_loop,
)


class TestPhase3Layer3Verifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Tạo tập log mini đại diện (3 hồ sơ vay) để unit test chạy tức thì (<0.1s)
        data = [
            # Case 1: Tuân thủ đầy đủ (Offer sent -> Returned sau 5 ngày, trong hạn 14 ngày)
            {
                "case:concept:name": "Application_001",
                "concept:name": "A_Create Application",
                "time:timestamp": "2016-01-01 09:00:00+00:00",
                "org:resource": "User_1",
                "case:RequestedAmount": 15000.0,
                "OfferedAmount": None,
                "CreditScore": None,
                "Accepted": None,
            },
            {
                "case:concept:name": "Application_001",
                "concept:name": "W_Validate application",
                "time:timestamp": "2016-01-02 10:00:00+00:00",
                "org:resource": "User_2",
                "case:RequestedAmount": 15000.0,
                "OfferedAmount": 15000.0,
                "CreditScore": 950.0,
                "Accepted": True,
            },
            {
                "case:concept:name": "Application_001",
                "concept:name": "O_Sent (mail and online)",
                "time:timestamp": "2016-01-03 10:00:00+00:00",
                "org:resource": "User_2",
                "case:RequestedAmount": 15000.0,
                "OfferedAmount": 15000.0,
                "CreditScore": 950.0,
                "Accepted": True,
            },
            {
                "case:concept:name": "Application_001",
                "concept:name": "O_Returned",
                "time:timestamp": "2016-01-08 10:00:00+00:00",
                "org:resource": "User_3",
                "case:RequestedAmount": 15000.0,
                "OfferedAmount": 15000.0,
                "CreditScore": 950.0,
                "Accepted": True,
            },
            # Case 2: Vi phạm Điều 14(1) (Offer sent -> Returned sau 25 ngày > 14 ngày)
            {
                "case:concept:name": "Application_002",
                "concept:name": "O_Sent (mail and online)",
                "time:timestamp": "2016-02-01 09:00:00+00:00",
                "org:resource": "User_4",
                "case:RequestedAmount": 20000.0,
                "OfferedAmount": 20000.0,
                "CreditScore": 820.0,
                "Accepted": True,
            },
            {
                "case:concept:name": "Application_002",
                "concept:name": "O_Returned",
                "time:timestamp": "2016-02-26 09:00:00+00:00",
                "org:resource": "User_5",
                "case:RequestedAmount": 20000.0,
                "OfferedAmount": 20000.0,
                "CreditScore": 820.0,
                "Accepted": True,
            },
            # Case 3: Hồ sơ rỗng đối với O_Sent (Vacuous trace)
            {
                "case:concept:name": "Application_003",
                "concept:name": "A_Create Application",
                "time:timestamp": "2016-03-01 09:00:00+00:00",
                "org:resource": "User_1",
                "case:RequestedAmount": 5000.0,
                "OfferedAmount": None,
                "CreditScore": None,
                "Accepted": False,
            },
        ]
        cls.mini_df = pd.DataFrame(data)
        cls.d4py = Declare4Py(log_df=cls.mini_df)
        cls.client = NeuroSymbolicLegalSynthesizerClient(
            simulate_self_correction=True,
            simulate_layer3_correction=True,
        )

    def test_step3_1_verbalizer_and_roundtrip_check(self) -> None:
        """Kiểm thử Bước 3.1: Dịch ngược tất định và phát hiện THRESHOLD_MISMATCH / BASELESS."""
        chunk_14_1 = {
            "article_id": "Article 14(1)",
            "text": "1. The consumer shall have a period of 14 calendar days in which to withdraw from the credit agreement.",
        }
        wrong_ast = {
            "article_id": "Article 14(1)",
            "template_name": "Response",
            "activation_activity": "O_Sent (mail and online)",
            "target_activity": "O_Returned",
            "time_min": 0,
            "time_max": 30,
            "time_unit": "d",
        }
        ok, msg = check_roundtrip_fidelity(wrong_ast, chunk_14_1, self.client)
        self.assertFalse(ok)
        self.assertIn("THRESHOLD_MISMATCH", msg)

        correct_ast = {**wrong_ast, "time_max": 14}
        ok2, msg2 = check_roundtrip_fidelity(correct_ast, chunk_14_1, self.client)
        self.assertTrue(ok2)
        self.assertEqual(msg2, "Roundtrip check passed.")

    def test_step3_2_and_3_3_conformance_vacuity_and_snapshots(self) -> None:
        """Kiểm thử Bước 3.2 & 3.3: Kiểm tra tuân thủ Declare4Py, phát hiện Vacuous Rule và trích xuất Snapshot."""
        ast_14_1 = DeclareConstraintAST(
            article_id="Article 14(1)",
            template_name="Response",
            activation_activity="O_Sent (mail and online)",
            target_activity="O_Returned",
            time_min=0,
            time_max=14,
            time_unit="d",
        )
        ok, report = run_layer3_declare4py_verifier(
            self.d4py, self.d4py.log_df, ast_14_1, ast_14_1.to_declare4py_line()
        )
        self.assertTrue(ok)
        self.assertEqual(report["total_cases"], 3)
        self.assertEqual(report["activated_cases_count"], 2)
        self.assertEqual(report["satisfied_cases_count"], 1)
        self.assertEqual(report["violated_cases_count"], 1)
        self.assertEqual(report["vacuous_cases_count"], 1)
        self.assertEqual(report["compliance_rate"], 50.0)
        self.assertEqual(len(report["counterexample_snapshots"]), 1)
        self.assertEqual(
            report["counterexample_snapshots"][0]["case_id"], "Application_002"
        )

        # Kiểm tra Vacuity Check khi điều kiện thuộc tính phi thực tế (total_activations == 0)
        vacuous_ast = DeclareConstraintAST(
            article_id="Article 16(4)",
            template_name="Response",
            activation_activity="O_Sent (mail and online)",
            target_activity="O_Returned",
            activation_attr="OfferedAmount",
            activation_op=">=",
            activation_val=99999999.0,
        )
        ok_vac, vac_report = run_layer3_declare4py_verifier(
            self.d4py, self.d4py.log_df, vacuous_ast, vacuous_ast.to_declare4py_line()
        )
        self.assertFalse(ok_vac)
        self.assertEqual(vac_report["error_type"], "VACUOUS_CONSTRAINT")


if __name__ == "__main__":
    unittest.main()
