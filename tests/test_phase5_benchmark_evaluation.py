"""
Unit Tests cho Bộ 30 Quy tắc Chuẩn (R01–R30) & Bộ Chạy Thực nghiệm Tự động (RQ1, RQ2, RQ3 Evaluation Runner):
- Kiểm tra cấu trúc 30 quy tắc chuẩn (12 Tier 1 Control-Flow, 10 Tier 2 Temporal & Data-Aware, 8 Tier 3 Baseless Traps)
- Kiểm tra lấy mẫu phân tầng 3 nhãn (ENTAILED, CONTRADICTED, BASELESS)
- Kiểm tra công tắc cấu hình Ablation Study (enable_l1_l2, enable_self_correction, enable_l3_roundtrip)
"""

import json
import tempfile
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
    classify_semantic_equivalence,
    evaluate_rq1_complexity_tiers,
    is_executable_against_log_schema,
    run_ablation_experiment,
    run_vanilla_rag_baseline,
)
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status
from src.mde.constraint_ast import DeclareConstraintAST


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestPhase5BenchmarkEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(PROJECT_ROOT / "data" / "processed" / "directive_chunks.json", "r", encoding="utf-8") as f:
            chunks = json.load(f)
        cls.chunks_by_id = {c["article_id"]: c for c in chunks}

        with open(PROJECT_ROOT / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            cls.process_schema = json.load(f)

        cls.normative_rules = build_normative_rule_benchmark(cls.chunks_by_id)

        # Tạo bộ DataFrame mini giả lập chuẩn BPIC 2017 để chạy unit test cực nhanh (< 0.1s)
        cls.df_raw = pd.DataFrame(
            [
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "A_Create Application",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T08:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "A_Concept",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T08:30:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "A_Accepted",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T09:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "W_Complete application",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T09:30:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Create Offer",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": 15000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "MonthlyCost": 675.0,
                    "time:timestamp": pd.Timestamp("2016-05-01T10:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Created",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T10:05:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Sent (mail and online)",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "W_Call after offers",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-02T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "A_Complete",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-03T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Returned",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-05T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "W_Validate application",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-06T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "A_Validating",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-06T12:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Accepted",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-07T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "A_Pending",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-08T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Aux_Events",
                    "concept:name": "A_Denied",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": 15000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-09T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Aux_Events",
                    "concept:name": "A_Cancelled",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": 15000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-10T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Aux_Events",
                    "concept:name": "A_Incomplete",
                    "case:RequestedAmount": 15000.0,
                    "OfferedAmount": 15000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-11T11:00:00Z"),
                },
            ]
        )
        cls.df_propagated = cls.df_raw.copy()
        if "MonthlyCost" not in cls.df_propagated.columns:
            cls.df_propagated["MonthlyCost"] = float("nan")
        cls.df_propagated[["OfferedAmount", "CreditScore", "NumberOfTerms", "MonthlyCost"]] = (
            cls.df_propagated[["OfferedAmount", "CreditScore", "NumberOfTerms", "MonthlyCost"]].ffill().bfill()
        )

    def test_normative_rule_benchmark_structure(self) -> None:
        """Kiểm tra Bộ 30 Quy tắc Chuẩn (R01–R30) có đúng 12 Tier 1, 10 Tier 2 và 8 Tier 3 Baseless Traps."""
        self.assertEqual(len(BENCHMARK_RULES), 30)
        self.assertEqual(len(self.normative_rules), 30)
        t1 = [r for r in self.normative_rules if r["tier"] == "Tier1_ControlFlow"]
        t2 = [r for r in self.normative_rules if r["tier"] == "Tier2_TemporalData"]
        t3 = [r for r in self.normative_rules if r["tier"] == "Tier3_BaselessTrap"]
        self.assertEqual(len(t1), 12)
        self.assertEqual(len(t2), 10)
        self.assertEqual(len(t3), 8)

    def test_rq1_and_rq2_ablation_switches(self) -> None:
        """Kiểm tra Full Pipeline vượt trội hơn các cấu hình bị cắt bỏ thành phần (Ablation Study) trên R01–R30."""
        mini_benchmark = build_stratified_trace_benchmark(
            df_propagated=self.df_propagated,
            df_raw=self.df_raw,
            normative_rules=self.normative_rules,
            target_total_items=48,
        )
        self.assertEqual(len(mini_benchmark), 48)

        llm_client = BenchmarkExperimentLLMClient(log_df=self.df_propagated)

        with tempfile.TemporaryDirectory() as tmp_dir:
            res_b1 = run_vanilla_rag_baseline(
                mini_benchmark,
                llm_client=llm_client,
                cache_file=str(Path(tmp_dir) / "vanilla_rag_test_cache.json"),
            )
        res_no_l12 = run_ablation_experiment(
            mini_benchmark,
            self.df_propagated,
            self.process_schema,
            llm_client=llm_client,
            enable_l1_l2=False,
            enable_self_correction=True,
        )
        res_no_sc = run_ablation_experiment(
            mini_benchmark,
            self.df_propagated,
            self.process_schema,
            llm_client=llm_client,
            enable_l1_l2=True,
            enable_self_correction=False,
        )
        res_full = run_ablation_experiment(
            mini_benchmark,
            self.df_propagated,
            self.process_schema,
            llm_client=llm_client,
            enable_l1_l2=True,
            enable_self_correction=True,
        )

        self.assertGreaterEqual(res_full["Normative_Eq_Rate (%)"], 80.0)
        self.assertGreaterEqual(res_full["Eq_Rate (%)"], 65.0)
        self.assertGreater(res_full["Macro_F1"], res_b1["Macro_F1"])
        self.assertGreater(res_full["Eq_Rate (%)"], res_no_sc["Eq_Rate (%)"])
        self.assertGreaterEqual(res_full["Executable_Rate (%)"], res_no_l12["Executable_Rate (%)"])

        rq1_full = evaluate_rq1_complexity_tiers(
            self.normative_rules,
            self.df_propagated,
            self.process_schema,
            enable_self_correction=True,
        )
        self.assertGreaterEqual(rq1_full["Overall Pipeline"]["Eq. (%)"], 85.0)

    def test_precedence_missing_prerequisite_is_contradicted_not_baseless(self) -> None:
        """Precedence(A[attr>0], B) when B occurs without A must be CONTRADICTED, not INAPPLICABLE BASELESS."""
        ast_prec = DeclareConstraintAST(
            article_id="Article 10(2)",
            template_name="Precedence",
            activation_activity="O_Create Offer",
            target_activity="A_Pending",
            activation_attr="MonthlyCost",
            activation_op=">",
            activation_val=0.0,
        )
        case_missing_prereq = pd.DataFrame(
            [
                {
                    "case:concept:name": "Case_Missing_Prereq",
                    "concept:name": "A_Create Application",
                    "MonthlyCost": 675.0,
                    "time:timestamp": pd.Timestamp("2016-05-01T08:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Missing_Prereq",
                    "concept:name": "A_Pending",
                    "MonthlyCost": 675.0,
                    "time:timestamp": pd.Timestamp("2016-05-02T08:00:00Z"),
                },
            ]
        )
        res = evaluate_trace_safety_and_status(case_missing_prereq, ast_prec, True, "OK")
        self.assertEqual(res["label"], "CONTRADICTED")
        self.assertEqual(res["reason_type"], "PROCESS_COMPLIANCE_VIOLATION")

    def test_absence_not_equivalent_to_existence_and_type_safety(self) -> None:
        """Absence(A, x < 200) must NOT equal Existence(A, x >= 200); String > Float & self-loops fail exec."""
        abs_ast = DeclareConstraintAST(
            article_id="Article 2(2)",
            template_name="Absence",
            activation_activity="O_Create Offer",
            activation_attr="OfferedAmount",
            activation_op="<",
            activation_val=200.0,
        )
        gold_ex = {
            "article_id": "Article 2(2)",
            "template_name": "Existence",
            "activation_activity": "O_Create Offer",
            "target_activity": None,
            "activation_attr": "OfferedAmount",
            "activation_op": ">=",
            "activation_val": 200.0,
            "time_max": None,
        }
        self.assertEqual(classify_semantic_equivalence(abs_ast, gold_ex, self.df_propagated), "REVERSED")

        str_cmp_ast = DeclareConstraintAST(
            article_id="Article 16(2)",
            template_name="Existence",
            activation_activity="O_Create Offer",
            activation_attr="Action",
            activation_op=">",
            activation_val=1.0,
        )
        self.assertFalse(is_executable_against_log_schema(str_cmp_ast, self.process_schema))

        self_loop_ast = DeclareConstraintAST(
            article_id="Article 8(1)",
            template_name="Precedence",
            activation_activity="A_Concept",
            target_activity="A_Concept",
        )
        self.assertFalse(is_executable_against_log_schema(self_loop_ast, self.process_schema))

    def test_benchmark_rules_unique_between_dev_and_heldout(self) -> None:
        """Zero duplicate canonical rule signatures in R01-R22, valid trap_scope on R23-R30, and stratified DEV/HELDOUT splits."""
        from src.evaluation.benchmark_builder import DEV_RULE_IDS, HELDOUT_TEST_RULE_IDS

        norm_rules = [r for r in self.normative_rules if not r["is_trap"]]
        sigs = [
            (r["article_id"], r["template"], r["act_a"], r["act_b"], r["attr"], r["op"], r["val"], r["time_max"])
            for r in norm_rules
        ]
        self.assertEqual(len(sigs), len(set(sigs)))
        for r in [x for x in self.normative_rules if x["is_trap"]]:
            self.assertIn(r.get("trap_scope"), {"rule", "schema", "trace"})

        # Both splits must be strictly disjoint and cover all 3 tiers (6 T1 + 5 T2 + 4 T3 each)
        self.assertEqual(len(DEV_RULE_IDS & HELDOUT_TEST_RULE_IDS), 0)
        self.assertEqual(len(DEV_RULE_IDS | HELDOUT_TEST_RULE_IDS), 30)
        for sp_name in ("dev", "heldout_test"):
            sp_rules = [r for r in self.normative_rules if r["dataset_split"] == sp_name]
            self.assertEqual(sum(1 for r in sp_rules if r["tier"] == "Tier1_ControlFlow"), 6)
            self.assertEqual(sum(1 for r in sp_rules if r["tier"] == "Tier2_TemporalData"), 5)
            self.assertEqual(sum(1 for r in sp_rules if r["tier"] == "Tier3_BaselessTrap"), 4)

    def test_strict_causal_ffill_and_crash_penalized_metrics(self) -> None:
        """Verify Declare4Py log loader does not bfill future offer attrs backwards and CRASH penalizes Macro Precision."""
        from src.symbolic.declare4py_verifier import Declare4Py

        d4py = Declare4Py(log_df=self.df_raw)
        app_create_row = d4py.log_df[d4py.log_df["concept:name"] == "A_Create Application"].iloc[0]
        o_sent_row = d4py.log_df[d4py.log_df["concept:name"] == "O_Sent (mail and online)"].iloc[0]
        # Pre-offer A_Create Application must NOT inherit future OfferedAmount via bfill()
        self.assertTrue(pd.isna(app_create_row["OfferedAmount"]))
        # Post-offer O_Sent inherits OfferedAmount causally via ffill()
        self.assertEqual(float(o_sent_row["OfferedAmount"]), 15000.0)

        # Verify CRASH counts penalize Macro Precision rather than getting dropped
        mini_bench = build_stratified_trace_benchmark(
            df_propagated=self.df_propagated,
            df_raw=self.df_raw,
            normative_rules=self.normative_rules,
            target_total_items=18,
        )
        res = run_ablation_experiment(
            mini_bench,
            self.df_propagated,
            self.process_schema,
            llm_client=BenchmarkExperimentLLMClient(log_df=self.df_propagated),
            enable_l1_l2=False,
            enable_self_correction=False,
            enable_l3_roundtrip=False,
            evaluate_explanations=False,
        )
        self.assertIn("Crash_Rate (%)", res)
        self.assertIn("Strict_Accuracy (%)", res)
        self.assertIsNone(res["Citation_Fidelity (%)"])
        if res["Crash_Rate (%)"] > 0:
            self.assertLessEqual(res["Macro_Precision"], res["Unpenalized_3Class_Macro_Precision"])

    def test_out_of_directive_scope_abstention_vs_genuine_crash(self) -> None:
        """Verify OUT_OF_DIRECTIVE_SCOPE abstention counts as safe BASELESS + Eq while genuine compiler/activity failures still crash."""
        r24 = next(r for r in self.normative_rules if r["rule_id"] == "R24")
        case_df = self.df_propagated[self.df_propagated["case:concept:name"] == "Case_Entailed_1"].copy()
        bench = [
            {
                "item_id": "test_r24_item",
                "rule_id": "R24",
                "rule_meta": r24,
                "retrieved_chunk": r24["retrieved_chunk"],
                "test_case_df": case_df,
                "ground_truth_label": "BASELESS",
            }
        ]
        art_unicode = r24["retrieved_chunk"]["article_id"].replace(" ", "\u202f")

        class _StubOutOfScopeLLM:
            def __init__(self, payload: dict) -> None:
                self.payload = payload
                self.chat_calls = 0

            def chat_json(self, messages, temperature=0.0, json_schema=None) -> str:
                return json.dumps(self.payload)

            def chat(self, prompt, temperature=0.0) -> str:
                self.chat_calls += 1
                return f"Case Case_Entailed_1 verdict is BASELESS under {art_unicode} (out of scope)."

        # 1. Valid EXEMPTION_OUT_OF_SCOPE (anchor_activity=None -> activation_activity='None') must abstain cleanly, not crash
        good_stub = _StubOutOfScopeLLM(
            {
                "article_id": r24["retrieved_chunk"]["article_id"],
                "deontic_modality": "EXEMPTION_OUT_OF_SCOPE",
                "temporal_relation": "UNARY_CONDITION",
                "anchor_activity": None,
                "consequent_activity": None,
                "unsupported_by_text": True,
            }
        )
        res_good = run_ablation_experiment(
            bench,
            self.df_propagated,
            self.process_schema,
            llm_client=good_stub,
            enable_l1_l2=True,
            enable_self_correction=True,
            enable_l3_roundtrip=True,
            evaluate_explanations=True,
        )
        self.assertEqual(res_good["Crash_Rate (%)"], 0.0)
        self.assertEqual(res_good["Executable_Rate (%)"], 100.0)
        self.assertEqual(res_good["Raw_Log_Executable_Rate (%)"], 0.0)
        self.assertEqual(res_good["Eq_Rate (%)"], 100.0)
        self.assertEqual(res_good["Strict_Accuracy (%)"], 100.0)
        self.assertEqual(res_good["Citation_Fidelity (%)"], 100.0)
        self.assertEqual(res_good["Per_Class_Metrics"]["BASELESS"]["Crash_Count"], 0)
        self.assertEqual(good_stub.chat_calls, 1)

        # 2. Genuine unrecovered compiler failure (ast_obj=None on max_retry=1) must remain CRASH
        crash_stub = _StubOutOfScopeLLM(
            {
                "article_id": r24["retrieved_chunk"]["article_id"],
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "None",
                "anchor_activity": "A_Create Application",
                "consequent_activity": None,
                "unsupported_by_text": True,
            }
        )
        res_crash = run_ablation_experiment(
            bench,
            self.df_propagated,
            self.process_schema,
            llm_client=crash_stub,
            enable_l1_l2=True,
            enable_self_correction=False,
            enable_l3_roundtrip=True,
            evaluate_explanations=False,
        )
        self.assertEqual(res_crash["Crash_Rate (%)"], 100.0)
        self.assertEqual(res_crash["Per_Class_Metrics"]["BASELESS"]["Crash_Count"], 1)

        # 3. Direct AST mode (enable_l1_l2=False) with hallucinated activity must remain CRASH
        hallucinated_act_stub = _StubOutOfScopeLLM(
            {
                "article_id": r24["retrieved_chunk"]["article_id"],
                "template_name": "Existence",
                "activation_activity": "Fake_Hallucinated_Activity",
                "target_activity": None,
                "unsupported_by_text": True,
            }
        )
        res_bad_act = run_ablation_experiment(
            bench,
            self.df_propagated,
            self.process_schema,
            llm_client=hallucinated_act_stub,
            enable_l1_l2=False,
            enable_self_correction=False,
            enable_l3_roundtrip=True,
            evaluate_explanations=False,
        )
        self.assertEqual(res_bad_act["Crash_Rate (%)"], 100.0)


if __name__ == "__main__":
    unittest.main()
