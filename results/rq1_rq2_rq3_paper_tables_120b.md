# Bảng Kết quả Thực nghiệm Chuẩn cho Bài báo (Model Thật: `openai/gpt-oss-120b` — Bộ 30 Quy tắc R01–R30)

## Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp

### 1A. Khi tắt Vòng lặp Tự sửa (One-Shot Synthesis - Phân bố kết quả vòng đầu của LLM trên R01–R22)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | 41.67% | 0.0% | 0.0% | 58.33% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | 0.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| **Overall Pipeline** | 33.33% | 0.0% | 0.0% | 66.67% | 0.0% |

### 1B. Full Neuro-Symbolic Pipeline (Sau khi qua Kiến trúc 3 Tầng & Vòng lặp Tự sửa)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Lỏng - Weakened (%) ↓ | Quá Chặt - Strengthened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | 75.0% | 8.33% | 8.33% | 8.33% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | 33.33% | 0.0% | 0.0% | 33.33% | 33.33% |
| **Overall Pipeline** | 66.67% | 6.67% | 6.67% | 13.33% | 6.67% |

---

## Bảng 2 (Trả lời RQ2): Nghiên cứu Cắt bỏ Thành phần (Ablation Study)

| Cấu hình Hệ thống (Configuration) | Tỷ lệ Ràng buộc Hợp lệ Thực thi được (%) ↑ | Tỷ lệ Đúng Ngữ nghĩa - Eq. Rate (%) ↑ | Độ chính xác Kiểm tra Tuân thủ trên Log (F1-Score) ↑ |
| :--- | :---: | :---: | :---: |
| **Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)** | N/A | N/A | 0.291 |
| **Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)** | 51.67% | 38.33% | 0.7614 |
| **- Pre-Verification (Tắt Tầng 1 & Tầng 2)** | 45.0% | 31.67% | 0.6791 |
| **- Self-Correction Loop (Tắt Vòng lặp Tự sửa)** | 23.33% | 23.33% | 0.5463 |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | 83.33% | 53.33% | 0.7094 |

---

## Bảng 3 (Trả lời RQ3): Hiệu quả Phát hiện Ảo giác 3 Trạng thái, Giải trình & Chi phí Thời gian

| Nhãn Chẩn đoán (Diagnostic Class) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng Tự sửa TB (Avg. Retries) ↓ | Thời gian Kiểm chứng Declare4Py (s) ↓ | Độ chuẩn xác Trích dẫn Giải trình (Citation Fidelity %) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | 0.7143 | 0.75 | 0.7317 | 0.9 | 0.0069s | 100.0% |
| **CONTRADICTED (Vi phạm)** | 1.0 | 0.65 | 0.7879 | 1.05 | 0.0055s | 100.0% |
| **BASELESS (Ảo giác / Thiếu bằng chứng Φ)** | 0.5385 | 0.7 | 0.6087 | 4.0 | 0.003s | 50.0% |
| **Trung bình Toàn hệ thống (Overall)** | 0.7509 | 0.7 | 0.7094 | 1.98 | 0.0061s | 100.0% |
