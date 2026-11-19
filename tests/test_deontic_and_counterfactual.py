import json
import unittest
from pathlib import Path

from src.mde.deontic_mde_compiler import (
    UNMAPPED_ATTR_TOKEN,
    build_constrained_deontic_schema,
    compile_deontic_to_declare4py,
    format_behavioral_profile_for_prompt,
    validate_and_compile_deontic_or_ast,
)
from src.symbolic.counterfactual_prober import (
    generate_counterfactual_trace_mutant,
    verify_via_counterfactual_probing,
)


class _DummyBlindJudgeClient:
    def __init__(self, response_dict: dict) -> None:
        self.response_dict = response_dict

    def chat_json(self, prompt: str, temperature: float = 0.0, **kwargs) -> str:
        return json.dumps(self.response_dict)


class TestDeonticMDEAndCounterfactualProbing(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]
        with open(
            cls.project_root / "data" / "processed" / "process_schema.json",
            "r",
            encoding="utf-8",
        ) as f:
            cls.process_schema = json.load(f)

    def test_deontic_schema_literal_constraints(self) -> None:
        """Kiểm tra Grammar-Constrained Schema khóa cứng tên hoạt động và thuộc tính."""
        SchemaCls = build_constrained_deontic_schema(self.process_schema)
        valid_frame = SchemaCls(
            article_id="Article 8(1)",
            deontic_modality="OBLIGATION",
            temporal_relation="PREREQUISITE_BEFORE",
            anchor_activity="A_Accepted",
            consequent_activity="O_Create Offer",
        )
        self.assertEqual(valid_frame.anchor_activity, "A_Accepted")

        # Hoạt động bịa đặt ngoài process_schema.json phải bị chặn ngay ở tầng Schema
        with self.assertRaises(Exception):
            SchemaCls(
                article_id="Article 8(1)",
                deontic_modality="OBLIGATION",
                temporal_relation="PREREQUISITE_BEFORE",
                anchor_activity="O_Fake_Hallucinated_Activity",
                consequent_activity="O_Create Offer",
            )

    def test_deontic_compiler_exemption_and_missing_attr_blocking(self) -> None:
        """Kiểm tra Bộ biên dịch MDE chặn ngay điều khoản Miễn trừ (EXEMPTION) và Thiếu thuộc tính Log (Φ)."""
        # 1. Điều khoản Miễn trừ (Article 7 / Article 2(2)(a))
        status_ex, payload_ex = compile_deontic_to_declare4py(
            {
                "article_id": "Article 7",
                "deontic_modality": "EXEMPTION_OUT_OF_SCOPE",
                "temporal_relation": "MANDATORY_RESPONSE",
                "anchor_activity": "A_Incomplete",
                "consequent_activity": "W_Call incomplete files",
                "unsupported_by_text": True,
            },
            process_schema=self.process_schema,
        )
        self.assertEqual(status_ex, "BASELESS_OR_EXEMPT")
        self.assertIsInstance(payload_ex, dict)
        self.assertIn("OUT_OF_DIRECTIVE_SCOPE", payload_ex["deontic_baseless_reason"])

        # 2. Điều khoản yêu cầu thuộc tính ngoài Log (UNMAPPED_MISSING_IN_LOG - VD: APR / Compensation Fee)
        status_phi, payload_phi = compile_deontic_to_declare4py(
            {
                "article_id": "Article 19(1)",
                "deontic_modality": "PROHIBITION",
                "temporal_relation": "UNARY_CONDITION",
                "anchor_activity": "O_Create Offer",
                "attribute_guard": UNMAPPED_ATTR_TOKEN,
                "guard_operator": ">",
                "guard_threshold": 20.0,
            },
            process_schema=self.process_schema,
        )
        self.assertEqual(status_phi, "BASELESS_MISSING_ATTR")
        self.assertIsInstance(payload_phi, dict)
        self.assertIn("MISSING_LOG_EVIDENCE_PHI_VIOLATION", payload_phi["deontic_baseless_reason"])

    def test_deontic_compiler_prohibition_and_behavioral_grounding(self) -> None:
        """Kiểm tra ánh xạ PROHIBITION -> Absence / Not Response và kiểm tra Behavioral Profile Grounding."""
        # PROHIBITION + UNARY_CONDITION -> Absence
        status_abs, res_abs = compile_deontic_to_declare4py(
            {
                "article_id": "Article 2(2)",
                "deontic_modality": "PROHIBITION",
                "temporal_relation": "UNARY_CONDITION",
                "anchor_activity": "O_Create Offer",
                "attribute_guard": "OfferedAmount",
                "guard_operator": "<",
                "guard_threshold": 200.0,
            },
            process_schema=self.process_schema,
        )
        self.assertEqual(status_abs, "COMPILED_OK")
        self.assertEqual(res_abs["template_name"], "Absence")
        self.assertEqual(res_abs["decl_line"], "Absence[O_Create Offer] | A.OfferedAmount < 200.0 | | ")

        # IMMEDIATE_PREREQUISITE trên cặp không nối tiếp trực tiếp phải bị Behavioral Profile Grounding chặn
        status_bp, err_bp = compile_deontic_to_declare4py(
            {
                "article_id": "Article 5(1)",
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "IMMEDIATE_PREREQUISITE",
                "anchor_activity": "A_Create Application",
                "consequent_activity": "A_Pending",
            },
            process_schema=self.process_schema,
        )
        self.assertEqual(status_bp, "COMPILE_ERROR")
        self.assertIn("Behavioral Profile Grounding Violation", str(err_bp))

        # IMMEDIATE_PREREQUISITE trên cặp nối tiếp trực tiếp (O_Create Offer -> O_Created) biên dịch thành công
        status_ok, res_ok = compile_deontic_to_declare4py(
            {
                "article_id": "Article 5(1)",
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "IMMEDIATE_PREREQUISITE",
                "anchor_activity": "O_Create Offer",
                "consequent_activity": "O_Created",
            },
            process_schema=self.process_schema,
        )
        self.assertEqual(status_ok, "COMPILED_OK")
        self.assertEqual(res_ok["template_name"], "Chain Precedence")

    def test_counterfactual_trace_mutation_probing(self) -> None:
        """Kiểm tra sinh Vết Đối chứng (τ+, τ-) và phát hiện lỗi đảo chiều Precedence vs Response."""
        rule_prec = {
            "article_id": "Article 8(1)",
            "template_name": "Precedence",
            "activation_activity": "A_Accepted",
            "target_activity": "O_Create Offer",
        }
        mutants = generate_counterfactual_trace_mutant(rule_prec, self.process_schema)
        self.assertEqual(mutants["mutation_operator"], "PREREQUISITE_INVERSION_AND_OMISSION")
        self.assertIn("WITHOUT performing", mutants["tau_minus_story"])

        # Khi Thẩm phán Độc lập đồng thuận (case_a_complies=True, case_b_violates=True) -> Passed
        chunk_8_1 = {
            "article_id": "Article 8(1)",
            "text": "Before the conclusion of the credit agreement, the creditor shall assess the consumer's creditworthiness.",
        }
        judge_agree = _DummyBlindJudgeClient(
            {
                "case_a_complies": True,
                "case_b_violates": True,
                "is_unsupported_clause": False,
                "verdict": "EQUIVALENT",
                "explanation": "Creating an offer without prior application acceptance violates the prerequisite duty.",
            }
        )
        ok_pass, msg_pass = verify_via_counterfactual_probing(
            rule_prec, chunk_8_1, judge_agree, process_schema=self.process_schema
        )
        self.assertTrue(ok_pass)
        self.assertIn("Counterfactual Probe Passed", msg_pass)

        # Khi công thức bị sinh ngược chiều (Response) khiến Thẩm phán phán Case B KHÔNG vi phạm -> Bắt lỗi đảo chiều!
        rule_reversed = {
            "article_id": "Article 8(1)",
            "template_name": "Response",
            "activation_activity": "A_Accepted",
            "target_activity": "O_Create Offer",
        }
        judge_disagree = _DummyBlindJudgeClient(
            {
                "case_a_complies": True,
                "case_b_violates": False,
                "is_unsupported_clause": False,
                "verdict": "REVERSED_ORDER",
                "explanation": "Article 8(1) only requires assessment before offer creation; it does not force an offer to be created after every acceptance.",
            }
        )
        ok_rev, msg_rev = verify_via_counterfactual_probing(
            rule_reversed, chunk_8_1, judge_disagree, process_schema=self.process_schema
        )
        self.assertFalse(ok_rev)
        self.assertIn("Counterfactual Mutation Disagreement", msg_rev)
        self.assertIn("REVERSED_ORDER", msg_rev)


if __name__ == "__main__":
    unittest.main()
