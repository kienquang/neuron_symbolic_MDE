# Bảng Kết quả Thực nghiệm Sạch & Khách quan (Model: `openai/gpt-oss-20b` | R01–R30 & 300 Mẫu)

Thực nghiệm được tái chạy toàn bộ từ đầu sau kiểm toán liêm chính khoa học (tắt Baseline 1, `temperature = 0.0`):
- **Phân tách phân tầng chuẩn (Stratified Split)**: **DEV (15 quy tắc: 6 Tier 1 + 5 Tier 2 + 4 Tier 3; 150 mẫu = 50/50/50)** và **HELDOUT_TEST (15 quy tắc: 6 Tier 1 + 5 Tier 2 + 4 Tier 3; 150 mẫu = 50/50/50)** với **0 quy tắc trùng lặp** và **0 mã hồ sơ trùng lặp**.
- **Độ thực tế dữ liệu (`benchmark_items.json`)**: **224/300 (74.7%)** là vết quy trình thực tế nguyên bản từ BPIC 2017; bỏ `bfill()` (chỉ dùng `ffill()` nhân quả).
- **Công bằng & Chuẩn hóa**: Không từ khóa khớp luật trong `process_schema.json`, không bảng ánh xạ tay; `CRASH` phạt thẳng vào Precision/F1; `Citation Fidelity (%)` để `N/A` do tắt giải trình Bước 4.3 (`--with-explanations` không bật). *(Các chỉ số chẩn đoán rã nhỏ lưu đầy đủ trong `results/rq1_rq2_rq3_evaluation_tables.json`.)*

---

## Bảng 1 (Trả lời RQ1): Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp (`R01–R22`)

### 1A. Round-1 Behavioral Deontic Synthesis (Tắt Counterfactual Probe & tự sửa)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt (%) ↓ | Quá Lỏng (%) ↓ | Đảo Chiều (%) ↓ | Sai Hoạt động (%) ↓ | Từ chối / Lỗi khác (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | **66.67%** | 0.0% | 0.0% | 0.0% | 25.0% | 8.33% |
| **Tier 2: Temporal & Data-Aware** | **90.0%** | 0.0% | 0.0% | 0.0% | 10.0% | 0.0% |
| **Overall Pipeline** | **77.27%** | 0.0% | 0.0% | 0.0% | 18.18% | 4.55% |

### 1B. Full Pipeline (Bật Behavioral Deontic Compiler + Counterfactual Probe + Tự sửa)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt (%) ↓ | Quá Lỏng (%) ↓ | Đảo Chiều (%) ↓ | Sai Hoạt động (%) ↓ | Từ chối / Lỗi khác (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | **58.33%** | 0.0% | 8.33% | 0.0% | 25.0% | 8.33% |
| **Tier 2: Temporal & Data-Aware** | **100.0%** | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| **Overall Pipeline** | **77.27%** | 0.0% | 4.55% | 0.0% | 13.64% | 4.55% |

> *Ghi chú Bảng 1*: Cột "Từ chối / Lỗi khác" gộp `Abstained + Crash + Vacuous`; cả 1A và 1B đều có `Crash = 0.0%` và `Vacuous = 0.0%` (`Abstained = 4.55%` ở 1B).

---

## Bảng 2 (Trả lời RQ2): Nghiên cứu Triệt tiêu (Ablation Study) & So sánh Baseline (300 mẫu)
| Cấu hình Thực nghiệm (Configuration) | Thực thi Hợp lệ (%) ↑ | Norm Eq (`R01–R22` %) ↑ | Trap Detect (`R23–R30` %) ↑ | Accuracy (%) ↑ | Macro-F1 ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline 1: Vanilla RAG + LLM Direct QA *(Excluded / Not re-run)* | N/A | N/A | N/A | N/A | **Excluded** |
| Baseline 2: One-Shot LLM-to-DECLARE *(Không qua Compiler & Counterfactual)* | 93.33% | 67.0% | 25.0% | 58.0% | **0.5262** |
| - Self-Correction Loop *(Tắt Vòng lặp Tự sửa)* | 96.67% | 71.0% | 36.0% | 63.67% | **0.6213** |
| - Behavioral Deontic Compiler *(Tắt Biên dịch Deontic & Behavioral Profile)* | 96.0% | 71.0% | 25.0% | 66.0% | **0.6484** |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | **100.0%** | **75.0%** | **36.0%** | **70.67%** | **0.6824** |

> *Ghi chú Bảng 2*:
> - **Tách phân tầng `DEV` vs `HELDOUT_TEST` (Full Pipeline, 150 mẫu/tập)**: `DEV` đạt `Accuracy = 71.33%`, `Macro-F1 = 0.7044` (`Trap = 48.0%`); `HELDOUT_TEST` đạt `Accuracy = 70.0%`, `Macro-F1 = 0.6509` (`Trap = 24.0%`).
> - **Chi tiết bẫy `R23–R30` (Full Pipeline)**: `Rule/Schema Trap = 15.79%` (`1/6` loại bẫy luật/lược đồ: `R27`), `Trace Φ = 100.0%` (`2/2` loại bẫy log: `R29, R30`); tổng hợp `Trap Detect = 36.0%`.
> - **Tỷ lệ `Crash`**: Baseline 2 và `- Behavioral Deontic Compiler` có `Crash = 6.67%` (`100% - Exec`); Full Pipeline và `- Self-Correction` có `Crash = 0.0%`.

---

## Bảng 3 (Trả lời RQ3): Hiệu năng Chẩn đoán Tuân thủ & Độ tin cậy Giải trình (300 mẫu)
| Nhãn Phân loại Tuân thủ (Compliance Verdict) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng sửa TB | Thời gian TB (s) ↓ | Citation Fidelity (%) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | 0.637 | 0.93 | **0.7561** | 0.29 | 0.0062s | **N/A** |
| **CONTRADICTED (Vi phạm)** | 0.7685 | 0.83 | **0.7981** | 0.29 | 0.0048s | **N/A** |
| **BASELESS (Ảo giác / Thiếu Φ)** | 0.7826 | 0.36 | **0.4932** | 0.0 | 0.0043s | **N/A** |
| **Trung bình Toàn hệ thống (Overall)** | **0.7294** | **0.7067** | **0.6824** | **0.19** | **0.0051s** | **N/A** |
