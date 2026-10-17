import unittest
from pathlib import Path
from src.preprocessing.extract_process_schema import extract_bpic2017_schema


class TestExtractProcessSchema(unittest.TestCase):
    def setUp(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.xes_path = self.project_root / "datasets" / "BPI Challenge 2017.xes"
        self.output_path = self.project_root / "data" / "processed" / "process_schema.json"
        self.cache_path = self.project_root / "data" / "interim" / "bpic2017_events.parquet"

    def test_schema_structure_and_domains(self) -> None:
        schema = extract_bpic2017_schema(
            self.xes_path,
            self.output_path,
            parquet_cache_path=self.cache_path,
        )
        self.assertTrue(self.output_path.exists())
        self.assertEqual(schema["dataset"], "BPI Challenge 2017 (Consumer Loan Process)")

        # Kiểm tra 3 phân hệ hoạt động chính: Application, Offer, Workflow
        origins = schema["activities_by_origin"]
        self.assertIn("Application", origins)
        self.assertIn("Offer", origins)
        self.assertIn("Workflow", origins)

        # Kiểm tra một số hoạt động tiêu biểu
        self.assertIn("A_Create Application", origins["Application"])
        self.assertIn("O_Create Offer", origins["Offer"])
        self.assertIn("W_Validate application", origins["Workflow"])

        # Kiểm tra các thuộc tính mức Case và mức Event
        self.assertIn("case:RequestedAmount", schema["case_attributes"])
        self.assertIn("case:LoanGoal", schema["case_attributes"])
        self.assertIn("OfferedAmount", schema["event_attributes"])
        self.assertIn("CreditScore", schema["event_attributes"])
        self.assertIn("time:timestamp", schema["event_attributes"])
        self.assertEqual(schema["event_attributes"]["time:timestamp"]["type"], "Timestamp")

        # Kiểm tra DFG transitions
        self.assertGreater(len(schema["frequent_transitions"]), 0)
        self.assertLessEqual(len(schema["frequent_transitions"]), 30)


if __name__ == "__main__":
    unittest.main()
