# Bảng Kết quả Thực nghiệm Chuẩn cho Bài báo (Model Thật: `openai/gpt-oss-120b` — Bộ 30 Quy tắc R01–R30)

## Bảng 1 (Trả lời RQ1): Kết quả Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp

### 1A. Khi tắt Vòng lặp Tự sửa (One-Shot Synthesis - Phân bố kết quả vòng đầu của LLM trên R01–R22)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt - Strengthened (%) ↓ | Quá Lỏng - Weakened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | 83.33% | 0.0% | 0.0% | 16.67% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Overall Pipeline** | 86.67% | 0.0% | 0.0% | 13.33% | 0.0% |

### 1B. Full Neuro-Symbolic Pipeline (Sau khi qua Kiến trúc 3 Tầng & Vòng lặp Tự sửa)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Lỏng - Weakened (%) ↓ | Quá Chặt - Strengthened (%) ↓ | Lệch Hướng / Đảo Chiều (%) ↓ | Rỗng - Vacuous (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | 83.33% | 0.0% | 0.0% | 16.67% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Overall Pipeline** | 86.67% | 0.0% | 0.0% | 13.33% | 0.0% |

---

## Bảng 2 (Trả lời RQ2): Nghiên cứu Cắt bỏ Thành phần (Ablation Study)

| Cấu hình Hệ thống (Configuration) | Tỷ lệ Ràng buộc Hợp lệ Thực thi được (%) ↑ | Tỷ lệ Đúng Ngữ nghĩa - Eq. Rate (%) ↑ | Độ chính xác Kiểm tra Tuân thủ trên Log (F1-Score) ↑ |
| :--- | :---: | :---: | :---: |
| **Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)** | N/A | N/A | 0.1903 |
| **Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)** | 93.33% | 56.67% | 0.5133 |
| **- Pre-Verification (Tắt Tầng 1 & Tầng 2)** | 93.33% | 78.33% | 0.824 |
| **- Self-Correction Loop (Tắt Vòng lặp Tự sửa)** | 88.33% | 78.33% | 0.8297 |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | 100.0% | 85.0% | 0.8666 |

---

## Bảng 3 (Trả lời RQ3): Hiệu quả Phát hiện Ảo giác 3 Trạng thái, Giải trình & Chi phí Thời gian

| Nhãn Chẩn đoán (Diagnostic Class) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng Tự sửa TB (Avg. Retries) ↓ | Thời gian Kiểm chứng Declare4Py (s) ↓ | Độ chuẩn xác Trích dẫn Giải trình (Citation Fidelity %) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | 0.8571 | 0.9 | 0.878 | 0.1 | 0.0121s | 100.0% |
| **CONTRADICTED (Vi phạm)** | 0.8947 | 0.85 | 0.8718 | 0.05 | 0.0094s | 100.0% |
| **BASELESS (Ảo giác / Thiếu bằng chứng Φ)** | 0.85 | 0.85 | 0.85 | 0.3 | 0.0008s | 100.0% |
| **Trung bình Toàn hệ thống (Overall)** | 0.8673 | 0.8667 | 0.8666 | 0.15 | 0.0074s | 100.0% |
