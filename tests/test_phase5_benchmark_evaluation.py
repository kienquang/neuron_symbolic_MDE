"""
Unit Tests cho Bộ Benchmark Chuẩn & Bộ Chạy Thực nghiệm Tự động (RQ1, RQ2, RQ3 Evaluation Runner):
- Kiểm tra cấu trúc 28 quy tắc chuẩn (Tier 1, Tier 2, Group 3 Baseless Traps)
- Kiểm tra lấy mẫu phân tầng 3 nhãn (ENTAILED, CONTRADICTED, BASELESS)
- Kiểm tra công tắc cấu hình Ablation Study (enable_l1_l2, enable_self_correction, enable_l3_roundtrip)
"""

import json
import unittest
from pathlib import Path
import pandas as pd

from src.evaluation.benchmark_builder import (
    build_normative_rule_benchmark,
    build_stratified_trace_benchmark,
)
from src.evaluation.experiment_runner import (
    BenchmarkExperimentLLMClient,
    evaluate_rq1_complexity_tiers,
    run_ablation_experiment,
    run_vanilla_rag_baseline,
)


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
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T08:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "W_Complete application",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T09:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Create Offer",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": 10000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-01T10:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Sent (mail and online)",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-01T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "W_Call after offers",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-02T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Returned",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-05T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "W_Validate application",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-06T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Entailed_1",
                    "concept:name": "O_Accepted",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": float("nan"),
                    "CreditScore": float("nan"),
                    "NumberOfTerms": float("nan"),
                    "time:timestamp": pd.Timestamp("2016-05-07T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Aux_Events",
                    "concept:name": "A_Pending",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": 10000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-08T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Aux_Events",
                    "concept:name": "A_Denied",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": 10000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-09T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Aux_Events",
                    "concept:name": "A_Cancelled",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": 10000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-10T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Aux_Events",
                    "concept:name": "A_Incomplete",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": 10000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-11T11:00:00Z"),
                },
                {
                    "case:concept:name": "Case_Aux_Events",
                    "concept:name": "A_Accepted",
                    "case:RequestedAmount": 10000.0,
                    "OfferedAmount": 10000.0,
                    "CreditScore": 800.0,
                    "NumberOfTerms": 24.0,
                    "time:timestamp": pd.Timestamp("2016-05-12T11:00:00Z"),
                },
            ]
        )
        cls.df_propagated = cls.df_raw.copy()
        cls.df_propagated[["OfferedAmount", "CreditScore", "NumberOfTerms"]] = (
            cls.df_propagated[["OfferedAmount", "CreditScore", "NumberOfTerms"]].ffill().bfill()
        )

    def test_normative_rule_benchmark_structure(self) -> None:
        """Kiểm tra Bộ Quy tắc Kiểm chứng có đúng 10 Tier 1, 12 Tier 2 và 6 Group 3 Baseless Traps."""
        self.assertEqual(len(self.normative_rules), 28)
        t1 = [r for r in self.normative_rules if r["complexity_tier"] == "Tier 1: Control-Flow Only"]
        t2 = [r for r in self.normative_rules if r["complexity_tier"] == "Tier 2: Temporal & Data-Aware"]
        g3 = [r for r in self.normative_rules if r.get("is_baseless_trap")]
        self.assertEqual(len(t1), 10)
        self.assertEqual(len(t2), 12)
        self.assertEqual(len(g3), 6)

    def test_rq1_and_rq2_ablation_switches(self) -> None:
        """Kiểm tra Full Pipeline vượt trội hơn các cấu hình bị cắt bỏ thành phần (Ablation Study)."""
        mini_benchmark = build_stratified_trace_benchmark(
            df_propagated=self.df_propagated,
            df_raw=self.df_raw,
            normative_rules=self.normative_rules,
            target_total_items=30,
        )
        self.assertEqual(len(mini_benchmark), 30)

        llm_client = BenchmarkExperimentLLMClient(log_df=self.df_propagated)

        res_b1 = run_vanilla_rag_baseline(mini_benchmark)
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

        # Full pipeline đạt 100% Eq_Rate và F1 cao hơn các cấu hình bị cắt giảm
        self.assertEqual(res_full["Eq_Rate (%)"], 100.0)
        self.assertGreater(res_full["Macro_F1"], res_b1["Macro_F1"])
        self.assertGreater(res_full["Eq_Rate (%)"], res_no_sc["Eq_Rate (%)"])
        self.assertGreaterEqual(res_full["Executable_Rate (%)"], res_no_l12["Executable_Rate (%)"])

        # Kiểm tra RQ1 Tier evaluation
        rq1_full = evaluate_rq1_complexity_tiers(
            self.normative_rules,
            self.df_propagated,
            self.process_schema,
            enable_self_correction=True,
        )
        self.assertEqual(rq1_full["Overall Pipeline"]["Eq. (%)"], 100.0)


if __name__ == "__main__":
    unittest.main()
