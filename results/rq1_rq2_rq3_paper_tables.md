# Bảng Kết quả Thực nghiệm Chuẩn cho Bài báo (Model Thật: `openai/gpt-oss-120b` — Bộ 30 Quy tắc R01–R30)

## Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp

### 1A. Khi tắt Vòng lặp Tự sửa (One-Shot Synthesis - Phân bố kết quả vòng đầu của LLM trên R01–R22)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Overall Pipeline** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |

### 1B. Full Neuro-Symbolic Pipeline (Sau khi qua Kiến trúc 3 Tầng & Vòng lặp Tự sửa)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Lỏng - Weakened (%) ↓ | Quá Chặt - Strengthened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | 33.33% | 0.0% | 0.0% | 33.33% | 33.33% |
| **Overall Pipeline** | 86.67% | 0.0% | 0.0% | 6.67% | 6.67% |

---

## Bảng 2 (Trả lời RQ2): Nghiên cứu Cắt bỏ Thành phần (Ablation Study)

| Cấu hình Hệ thống (Configuration) | Tỷ lệ Ràng buộc Hợp lệ Thực thi được (%) ↑ | Tỷ lệ Đúng Ngữ nghĩa - Eq. Rate (%) ↑ | Độ chính xác Kiểm tra Tuân thủ trên Log (F1-Score) ↑ |
| :--- | :---: | :---: | :---: |
| **Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)** | N/A | N/A | 0.2194 |
| **Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)** | 85.0% | 66.67% | 0.5862 |
| **- Pre-Verification (Tắt Tầng 1 & Tầng 2)** | 76.67% | 68.33% | 0.8576 |
| **- Self-Correction Loop (Tắt Vòng lặp Tự sửa)** | 73.33% | 68.33% | 0.8381 |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | 91.67% | 83.33% | 0.9544 |

---

## Bảng 3 (Trả lời RQ3): Hiệu quả Phát hiện Ảo giác 3 Trạng thái, Giải trình & Chi phí Thời gian

| Nhãn Chẩn đoán (Diagnostic Class) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng Tự sửa TB (Avg. Retries) ↓ | Thời gian Kiểm chứng Declare4Py (s) ↓ | Độ chuẩn xác Trích dẫn Giải trình (Citation Fidelity %) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | 1.0 | 0.95 | 0.9744 | 0.35 | 0.0156s | 95.0% |
| **CONTRADICTED (Vi phạm)** | 1.0 | 0.8 | 0.8889 | 1.1 | 0.0094s | 80.0% |
| **BASELESS (Ảo giác / Thiếu bằng chứng Φ)** | 1.0 | 1.0 | 1.0 | 0.85 | 0.0005s | 100.0% |
| **Trung bình Toàn hệ thống (Overall)** | 1.0 | 0.9167 | 0.9544 | 0.77 | 0.0093s | 100.0% |
