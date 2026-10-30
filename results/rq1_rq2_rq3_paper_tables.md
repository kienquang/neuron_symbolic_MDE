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
| **Baseline 1: Vanilla RAG + LLM Direct QA (Không dùng Declare4Py)** | N/A | N/A | 0.2243 |
| **Baseline 2: One-Shot LLM-to-DECLARE (Không có kiểm tra 3 tầng)** | 75.0% | 56.67% | 0.4901 |
| **- Pre-Verification (Tắt Tầng 1 & Tầng 2)** | 75.0% | 70.0% | 0.7313 |
| **- Self-Correction Loop (Tắt Vòng lặp Tự sửa)** | 85.0% | 80.0% | 0.7884 |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | 100.0% | 95.0% | 0.8997 |

---

## Bảng 3 (Trả lời RQ3): Hiệu quả Phát hiện Ảo giác 3 Trạng thái, Giải trình & Chi phí Thời gian

| Nhãn Chẩn đoán (Diagnostic Class) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng Tự sửa TB (Avg. Retries) ↓ | Thời gian Kiểm chứng Declare4Py (s) ↓ | Độ chuẩn xác Trích dẫn Giải trình (Citation Fidelity %) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | 0.8696 | 1.0 | 0.9302 | 0.0 | 0.0286s | 100.0% |
| **CONTRADICTED (Vi phạm)** | 1.0 | 0.85 | 0.9189 | 0.0 | 0.0248s | 100.0% |
| **BASELESS (Ảo giác / Thiếu bằng chứng Φ)** | 0.85 | 0.85 | 0.85 | 0.85 | 0.0028s | 100.0% |
| **Trung bình Toàn hệ thống (Overall)** | 0.9065 | 0.9 | 0.8997 | 0.28 | 0.0187s | 100.0% |
