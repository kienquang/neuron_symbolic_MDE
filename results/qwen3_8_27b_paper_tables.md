# Bảng Kết quả Thực nghiệm Sạch & Khách quan (Model: `qwen/qwen3.8-27b` | R01–R30 & 300 Mẫu)

Thực nghiệm được tái chạy toàn bộ từ đầu sau kiểm toán liêm chính khoa học (tắt Baseline 1, `temperature = 0.0`):
- **Phân tách phân tầng chuẩn (Stratified Split)**: **DEV (15 quy tắc: 6 Tier 1 + 5 Tier 2 + 4 Tier 3; 150 mẫu = 50/50/50)** và **HELDOUT_TEST (15 quy tắc: 6 Tier 1 + 5 Tier 2 + 4 Tier 3; 150 mẫu = 50/50/50)** với **0 quy tắc trùng lặp** và **0 mã hồ sơ trùng lặp**.
- **Độ thực tế dữ liệu (`benchmark_items.json`)**: **224/300 (74.7%)** là vết quy trình thực tế nguyên bản từ BPIC 2017; bỏ `bfill()` (chỉ dùng `ffill()` nhân quả).
- **Công bằng & Chuẩn hóa**: Không từ khóa khớp luật trong `process_schema.json`, không bảng ánh xạ tay; `CRASH` phạt thẳng vào Precision/F1; `Citation Fidelity (%)` để `N/A` do tắt giải trình Bước 4.3 (`--with-explanations` không bật). *(Các chỉ số chẩn đoán rã nhỏ lưu đầy đủ trong `results/rq1_rq2_rq3_evaluation_tables.json`.)*

---

## Bảng 1 (Trả lời RQ1): Kiểm chứng Ngữ nghĩa Ràng buộc theo Độ phức tạp (`R01–R22`)

### 1A. Round-1 MDE Synthesis (Tắt vòng lặp L3 & tự sửa)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt (%) ↓ | Quá Lỏng (%) ↓ | Đảo Chiều (%) ↓ | Sai Hoạt động (%) ↓ | Từ chối / Lỗi khác (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | **75.0%** | 0.0% | 8.33% | 0.0% | 16.67% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | **50.0%** | 10.0% | 0.0% | 20.0% | 20.0% | 0.0% |
| **Overall Pipeline** | **63.64%** | 4.55% | 4.55% | 9.09% | 18.18% | 0.0% |

### 1B. Full Pipeline (Bật đầy đủ Kiến trúc 3 tầng L1–L2–L3 & tự sửa)
| Độ phức tạp Ràng buộc (Complexity Tier) | Đúng Ngữ nghĩa - Eq. (%) ↑ | Quá Chặt (%) ↓ | Quá Lỏng (%) ↓ | Đảo Chiều (%) ↓ | Sai Hoạt động (%) ↓ | Từ chối / Lỗi khác (%) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Control-Flow Only** | **75.0%** | 0.0% | 8.33% | 0.0% | 16.67% | 0.0% |
| **Tier 2: Temporal & Data-Aware** | **50.0%** | 10.0% | 0.0% | 10.0% | 20.0% | 10.0% |
| **Overall Pipeline** | **63.64%** | 4.55% | 4.55% | 4.55% | 18.18% | 4.55% |

> *Ghi chú Bảng 1*: Cột "Từ chối / Lỗi khác" gộp `Abstained + Crash + Vacuous`; cả 1A và 1B đều có `Crash = 0.0%` và `Vacuous = 0.0%` (`Abstained = 4.55%` ở 1B).

---

## Bảng 2 (Trả lời RQ2): Nghiên cứu Triệt tiêu (Ablation Study) & So sánh Baseline (300 mẫu)
| Cấu hình Thực nghiệm (Configuration) | Thực thi Hợp lệ (%) ↑ | Norm Eq (`R01–R22` %) ↑ | Trap Detect (`R23–R30` %) ↑ | Accuracy (%) ↑ | Macro-F1 ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Baseline 1: Vanilla RAG + LLM Direct QA *(Excluded / Not re-run)* | N/A | N/A | N/A | N/A | **Excluded** |
| Baseline 2: One-Shot LLM-to-DECLARE *(Không kiểm tra 3 tầng)* | 100.0% | 72.0% | 24.0% | 61.0% | **0.4878** |
| - Self-Correction Loop *(Tắt Vòng lặp Tự sửa)* | 100.0% | 65.0% | 75.0% | 83.33% | **0.832** |
| - Pre-Verification *(Tắt Tầng 1 & Tầng 2)* | 100.0% | 72.0% | 75.0% | 83.0% | **0.8298** |
| **Full Neuro-Symbolic Pipeline (Đề xuất)** | **100.0%** | **65.0%** | **75.0%** | **83.33%** | **0.832** |

> *Ghi chú Bảng 2*:
> - **Tách phân tầng `DEV` vs `HELDOUT_TEST` (Full Pipeline, 150 mẫu/tập)**: `DEV` đạt `Accuracy = 82.0%`, `Macro-F1 = 0.8184` (`Trap = 74.0%`); `HELDOUT_TEST` đạt `Accuracy = 84.67%`, `Macro-F1 = 0.8457` (`Trap = 76.0%`).
> - **Chi tiết bẫy `R23–R30` (Full Pipeline)**: `Rule/Schema Trap = 67.11%` (`4/6` loại bẫy luật/lược đồ: `R23, R24, R26, R27`), `Trace Φ = 100.0%` (`2/2` loại bẫy log: `R29, R30`); tổng hợp `Trap Detect = 75.0%`.
> - **Tỷ lệ `Crash`**: Baseline 2 và `- Pre-Verification` có `Crash = 0.0%` (`100% - Exec`); Full Pipeline và `- Self-Correction` có `Crash = 0.0%`.

---

## Bảng 3 (Trả lời RQ3): Hiệu năng Chẩn đoán Tuân thủ & Độ tin cậy Giải trình (300 mẫu)
| Nhãn Phân loại Tuân thủ (Compliance Verdict) | Precision ↑ | Recall ↑ | F1-Score ↑ | Số vòng sửa TB | Thời gian TB (s) ↓ | Citation Fidelity (%) ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ENTAILED (Tuân thủ)** | 0.8142 | 0.92 | **0.8638** | 0.16 | 0.0079s | **N/A** |
| **CONTRADICTED (Vi phạm)** | 0.8646 | 0.83 | **0.8469** | 0.16 | 0.0052s | **N/A** |
| **BASELESS (Ảo giác / Thiếu Φ)** | 0.8242 | 0.75 | **0.7853** | 0.0 | 0.0023s | **N/A** |
| **Trung bình Toàn hệ thống (Overall)** | **0.8343** | **0.8333** | **0.832** | **0.11** | **0.0051s** | **N/A** |
