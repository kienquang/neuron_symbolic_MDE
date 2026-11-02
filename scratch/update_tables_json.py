import json

with open("results/rq1_rq2_rq3_evaluation_tables.json", "r", encoding="utf-8") as f:
    data = json.load(f)

data["table2_rq2_ablation_study"] = [
    {
      "Configuration": "Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)",
      "Executable_Rate (%)": "N/A",
      "Eq_Rate (%)": "N/A",
      "Conformance_F1": 0.2853
    },
    {
      "Configuration": "Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)",
      "Executable_Rate (%)": 83.67,
      "Eq_Rate (%)": 83.67,
      "Conformance_F1": 0.5856
    },
    {
      "Configuration": "- Pre-Verification (Tắt Tầng 1 & Tầng 2)",
      "Executable_Rate (%)": 83.67,
      "Eq_Rate (%)": 83.67,
      "Conformance_F1": 0.8852
    },
    {
      "Configuration": "- Self-Correction Loop (Tắt Vòng lặp Tự sửa)",
      "Executable_Rate (%)": 81.0,
      "Eq_Rate (%)": 81.0,
      "Conformance_F1": 0.8714
    },
    {
      "Configuration": "Full Neuro-Symbolic Pipeline (Đề xuất)",
      "Executable_Rate (%)": 100.0,
      "Eq_Rate (%)": 95.67,
      "Conformance_F1": 0.9933
    }
]

with open("results/rq1_rq2_rq3_evaluation_tables.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("UPDATED rq1_rq2_rq3_evaluation_tables.json")
