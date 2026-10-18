# Bảng Kết quả Thực nghiệm Chuẩn cho Bài báo (RQ1, RQ2, RQ3)

## Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp

### 1A. Khi tắt Vòng lặp Tự sửa (One-Shot Synthesis - Phân bố lỗi ban đầu của LLM)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | 70.0% | 10.0% | 0.0% | 20.0% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | 66.67% | 0.0% | 16.67% | 8.33% | 8.33% |
| **Overall Pipeline** | 68.18% | 4.55% | 9.09% | 13.64% | 4.55% |

### 1B. Full Neuro-Symbolic Pipeline (Sau khi qua Kiến trúc 3 Tầng & Vòng lặp Tự sửa)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Overall Pipeline** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |

---

## Bảng 2 (Trả lời RQ2): Nghiên cứu Cắt bỏ Thành phần (Ablation Study)

| Cấu hình Hệ thống (Configuration) | Tỷ lệ Ràng buộc Hợp lệ Thực thi được (%) ↑ | Tỷ lệ Đúng Ngữ nghĩa - Eq. Rate (%) ↑ | Độ chính xác Kiểm tra Tuân thủ trên Log (F1-Score) ↑ |
| :--- | :---: | :---: | :---: |
| **Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)** | N/A | N/A | 0.5111 |
| **Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)** | 82.42% | 16.67% | 0.3379 |
| **- Pre-Verification (Tắt Tầng 1 & Tầng 2)** | 82.42% | 82.42% | 0.8135 |
| **- Self-Correction Loop (Tắt Vòng lặp Tự sửa)** | 82.42% | 33.33% | 0.6773 |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | 100.0% | 100.0% | 0.9992 |

---

## Bảng 3 (Trả lời RQ3): Hiệu quả Phát hiện Ảo giác 3 Trạng thái, Giải trình & Chi phí Thời gian

| Nhãn Chẩn đoán (Diagnostic Class) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng Tự sửa TB (Avg. Retries) ↓ | Thời gian Kiểm chứng Declare4Py (s) ↓ | Độ chuẩn xác Trích dẫn Giải trình (Citation Fidelity %) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | 1.0 | 0.9975 | 0.9987 | 1.0 | 0.0077s | 100.0% |
| **CONTRADICTED (Vi phạm)** | 0.9975 | 1.0 | 0.9988 | 1.0 | 0.0072s | 100.0% |
| **BASELESS (Ảo giác / Thiếu bằng chứng Φ)** | 1.0 | 1.0 | 1.0 | 0.0 | 0.0017s | 100.0% |
| **Trung bình Toàn hệ thống (Overall)** | 0.9992 | 0.9992 | 0.9992 | 0.67 | 0.0056s | 100.0% |
