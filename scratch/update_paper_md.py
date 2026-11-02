with open("results/rq1_rq2_rq3_paper_tables.md", "r", encoding="utf-8") as f:
    text = f.read()

old_table = """| **Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)** | N/A | N/A | 0.2853 |
| **Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)** | 100.0% | 95.67% | 0.5285 |
| **- Pre-Verification (Tắt Tầng 1 & Tầng 2)** | 100.0% | 95.67% | 0.9933 |
| **- Self-Correction Loop (Tắt Vòng lặp Tự sửa)** | 100.0% | 95.67% | 0.9933 |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | 100.0% | 95.67% | 0.9933 |"""

new_table = """| **Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)** | N/A | N/A | 0.2853 |
| **Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)** | 83.67% | 83.67% | 0.5856 |
| **- Pre-Verification (Tắt Tầng 1 & Tầng 2)** | 83.67% | 83.67% | 0.8852 |
| **- Self-Correction Loop (Tắt Vòng lặp Tự sửa)** | 81.0% | 81.0% | 0.8714 |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | 100.0% | 95.67% | 0.9933 |"""

assert old_table in text, "old_table not found"
text = text.replace(old_table, new_table, 1)

with open("results/rq1_rq2_rq3_paper_tables.md", "w", encoding="utf-8") as f:
    f.write(text)

print("UPDATED rq1_rq2_rq3_paper_tables.md")
