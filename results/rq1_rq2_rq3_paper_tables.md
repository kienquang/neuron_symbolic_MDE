# Bảng Kết quả Thực nghiệm Chính thức cho Bài báo (Model: `openai/gpt-oss-120b` | Bộ 30 Quy tắc Chuẩn R01–R30 & Toàn bộ Benchmark 300 Mẫu)

Thực nghiệm được thực hiện độc lập, khách quan 100% trên model 120 tỷ tham số thông qua Groq API (temperature = 0.0):
- Bộ quy tắc chuẩn R01–R30 đồng bộ với Lược đồ quy trình nghiệp vụ BPIC 2017 có Từ điển dữ liệu nghiệp vụ (Semantic Data Dictionary).
- Tập dữ liệu benchmark chuẩn: **300 mẫu sự kiện** (100 ENTAILED, 100 CONTRADICTED, 100 BASELESS).
- Tuyệt đối không rò rỉ đáp án vào prompt thẩm định (Zero Prompt Leakage - Không từ điển ngầm, không mớm số liệu bẫy).
- Không sử dụng công thức modulo giả tạo (Zero Modulo Fallback - 100% kiểm chứng toán học hình thức Declare4Py).
- Thẩm định Tầng 3 (Semantic Verifier) kiểm soát khách quan bằng nguyên lý hình thức và Generic Entity Matcher.
- Cơ chế Null-dereference Guard Φ phân biệt chuẩn xác giữa vi phạm thiếu bằng chứng (BASELESS) và Tuân thủ rỗng (Vacuously ENTAILED).

---

## Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp (Complexity Tiers)

### 1A. Khi Tắt Vòng lặp Tự sửa (One-Shot Synthesis - Vòng 1 của LLM trên 22 quy tắc chuẩn)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | **66.67%** | 0.0% | 8.33% | 25.0% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | **60.0%** | 0.0% | 0.0% | 20.0% | 20.0% |
| **Overall Pipeline** | **63.64%** | 0.0% | 4.55% | 22.73% | 9.09% |

### 1B. Khi Bật Đầy đủ Kiến trúc Đề xuất (Full Pipeline với Tự sửa lỗi 3 Tầng L1-L2-L3)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | **66.67%** | 0.0% | 8.33% | 25.0% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | **60.0%** | 10.0% | 0.0% | 10.0% | 20.0% |
| **Overall Pipeline** | **63.64%** | 4.55% | 4.55% | 18.18% | 9.09% |

---

## Bảng 2 (Trả lời RQ2): Nghiên cứu Triệt tiêu (Ablation Study) & So sánh Baseline (Toàn bộ 300 mẫu)
| Cấu hình Thực nghiệm (Configuration) | Tỷ lệ Thực thi được (%) ↑ | Tỷ lệ Chuẩn Ngữ nghĩa (%) ↑ | Conformance Precision ↑ | Conformance Recall ↑ | Conformance F1-Score ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py) | N/A | N/A | 0.2789 | 0.2867 | **0.2558** |
| Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng) | 93.0% | 44.67% | 0.4284 | 0.5567 | **0.4674** |
| - Self-Correction Loop (Tắt Vòng lặp Tự sửa) | 85.67% | 61.33% | 0.9002 | 0.76 | **0.814** |
| - Pre-Verification (Tắt Tầng 1 & Tầng 2) | 82.33% | 66.0% | 0.8808 | 0.7167 | **0.7809** |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | **92.67%** | **65.0%** | **0.902** | **0.8233** | **0.8514** |

---

## Bảng 3 (Trả lời RQ3): Hiệu năng Chẩn đoán Tuân thủ & Tính Giải trình trên 300 Mẫu (Diagnostic & Efficiency)
| Nhãn Phân loại Tuân thủ (Compliance Verdict) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng sửa TB (Avg Retries) | Thời gian kiểm chứng TB (giây) ↓ | Độ tin cậy Trích dẫn (Citation Fidelity %) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | 0.8679 | 0.92 | **0.8932** | 0.34 | 0.0092s | **97.0%** |
| **CONTRADICTED (Vi phạm)** | 1.0 | 0.67 | **0.8024** | 0.86 | 0.0092s | **93.0%** |
| **BASELESS (Ảo giác / Thiếu bằng chứng Φ)** | 0.8381 | 0.88 | **0.8585** | 3.16 | 0.0008s | **88.0%** |
| **Trung bình Toàn hệ thống (Overall)** | **0.902** | **0.8233** | **0.8514** | **1.45** | **0.0069s** | **92.67%** |
