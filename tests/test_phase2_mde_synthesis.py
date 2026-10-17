import json
import unittest
from pathlib import Path
from src.mde.constraint_ast import DeclareConstraintAST, validate_layer1_ast
from src.mde.typing_environment import ProcessTypingEnvironment, check_layer1_and_layer2
from src.neural.rag_retriever import DirectiveRAGRetriever
from src.neural.synthesis_loop import (
    NeuroSymbolicLegalSynthesizerClient,
    generate_with_ovas_and_req2ltl_loop,
)


class TestPhase2MDESynthesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]
        with open(
            cls.project_root / "data" / "processed" / "process_schema.json",
            "r",
            encoding="utf-8",
        ) as f:
            cls.process_schema = json.load(f)
        with open(
            cls.project_root / "data" / "processed" / "directive_chunks.json",
            "r",
            encoding="utf-8",
        ) as f:
            cls.directive_chunks = json.load(f)
        cls.gamma = ProcessTypingEnvironment(cls.process_schema)

    def test_step2_1_declare4py_compilation_and_closed_enum(self) -> None:
        """Kiểm thử Bước 2.1: Biên dịch AST sang dòng lệnh chuẩn của Declare4Py & chặn tên Template lạ."""
        ast = DeclareConstraintAST(
            article_id="Article 14(1)",
            template_name="Response",
            activation_activity="O_Sent (mail and online)",
            target_activity="O_Returned",
            time_min=0,
            time_max=14,
            time_unit="d",
        )
        self.assertEqual(
            ast.to_declare4py_line(),
            "Response[O_Sent (mail and online), O_Returned] |  | | 0,14,d",
        )

        # Kiểm tra Closed Enumeration chặn template không thuộc Declare4Py
        ok, err = validate_layer1_ast(
            {
                "article_id": "Article 14(1)",
                "template_name": "InvalidHallucinatedTemplate",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "O_Returned",
            }
        )
        self.assertFalse(ok)
        self.assertIn("Layer 1 Schema/Enumeration Violation", str(err))

    def test_step2_2_delta_lookup_and_type_conformance(self) -> None:
        """Kiểm thử Bước 2.2: Hàm tra cứu δ(C, p) và quy tắc tương thích kiểu của OVAS."""
        # 1. Chặn hoạt động không tồn tại trong process_schema.json
        ok_act, msg_act = self.gamma.delta_activity("W_Fake_Activity")
        self.assertFalse(ok_act)
        self.assertIn("Navigational Violation", str(msg_act))

        # 2. Chặn toán tử '>=' trên thuộc tính kiểu String (case:LoanGoal)
        ok_type, msg_type = self.gamma.check_type_conformance(
            "case:LoanGoal", ">=", "Car"
        )
        self.assertFalse(ok_type)
        self.assertIn("Type Conformance Violation", str(msg_type))

        # 3. Cho phép toán tử '>=' trên thuộc tính kiểu Float (OfferedAmount)
        ok_float, msg_float = self.gamma.check_type_conformance(
            "OfferedAmount", ">=", 200.0
        )
        self.assertTrue(ok_float)
        self.assertIsNone(msg_float)

    def test_step2_3_rag_and_self_correction_loop(self) -> None:
        """Kiểm thử Bước 2.3: Truy xuất BM25 RAG & Vòng lặp tự sửa lỗi OVAS + Req2LTL + Role-tagged feedback."""
        retriever = DirectiveRAGRetriever(self.directive_chunks)
        hits = retriever.retrieve_top_k("14 calendar days withdraw right of withdrawal", top_k=3)
        hit_ids = [h["article_id"] for h in hits]
        self.assertIn("Article 14(1)", hit_ids)

        # Kiểm tra vòng lặp tự sửa lỗi khi Attempt 1 mắc lỗi Tầng 2 trên Article 8(1)
        chunk_8_1 = next(c for c in self.directive_chunks if c["article_id"] == "Article 8(1)")
        client = NeuroSymbolicLegalSynthesizerClient(simulate_self_correction=True)
        ast_obj, trace = generate_with_ovas_and_req2ltl_loop(
            retrieved_chunk=chunk_8_1,
            process_schema=self.process_schema,
            llm_client=client,
            max_retry=5,
            record_trace=True,
        )
        self.assertEqual(len(trace), 2)
        self.assertFalse(trace[0]["is_valid"])
        self.assertIn("Navigational Violation", trace[0]["feedback"])
        self.assertIn("Type Conformance Violation", trace[0]["feedback"])
        self.assertTrue(trace[1]["is_valid"])
        self.assertEqual(ast_obj.template_name, "Precedence")
        self.assertEqual(ast_obj.activation_activity, "W_Validate application")


if __name__ == "__main__":
    unittest.main()
