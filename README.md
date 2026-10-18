# Neuro-Symbolic + MDE for Trustworthy Reasoning in Process Mining

Dự án nghiên cứu kết hợp **Neuro-Symbolic AI** và **Model-Driven Engineering (MDE)** nhằm phục vụ suy luận tin cậy (Trustworthy Reasoning), kiểm tra tuân thủ (Compliance Checking) chống ảo giác 3 trạng thái (`ENTAILED`, `CONTRADICTED`, `BASELESS`) và sinh báo cáo giải trình tất định (Accountable Audit Trail) trong **Khai phá quy trình (Process Mining)** trên bộ dữ liệu thực tế **BPI Challenge 2017** và văn bản luật tín dụng tiêu dùng châu Âu **Directive 2008/48/EC**.

---

## Cấu trúc thư mục dự án

```text
neuron_symbolic_reasoning/
├── .venv/                              # Môi trường ảo Python (Python 3.13)
├── configs/
│   └── config.yaml                     # Cấu hình đường dẫn dữ liệu & tham số 4 giai đoạn
├── datasets/                           # Dữ liệu gốc (Raw Datasets)
│   ├── directive_2008_48_EC.pdf        # Văn bản luật EU Consumer Credit Directive 2008/48/EC
│   └── BPI Challenge 2017.xes          # Nhật ký sự kiện quy trình cho vay (31,509 hồ sơ, 1.2M+ sự kiện)
├── data/
│   ├── interim/                        # Dữ liệu trung gian (Parquet cache tăng tốc đọc XES)
│   │   └── bpic2017_events.parquet     # Bộ nhớ đệm DataFrame chuẩn pm4py
│   └── processed/                      # Dữ liệu đã qua tiền xử lý & tổng hợp MDE
│       ├── directive_chunks.json       # Bước 1A: Phân đoạn điều khoản (Articles 1–24)
│       ├── process_schema.json         # Bước 1B: Lược đồ Quy trình & Typing Environment Γ
│       ├── verified_constraints.json   # Bước 2: Ràng buộc DECLARE đã qua kiểm tra tĩnh Tầng 1 & Tầng 2
│       └── verified_constraints.decl   # Bước 2: File mô hình chuẩn Declare4Py (.decl)
├── src/                                # Mã nguồn chính của dự án
│   ├── __init__.py
│   ├── preprocessing/                  # Bước 1: Tiền xử lý văn bản luật & Event Log
│   │   ├── __init__.py
│   │   ├── parse_directive.py          # Bước 1A: Bóc tách điều khoản nghiệp vụ (Articles 1–24)
│   │   └── extract_process_schema.py   # Bước 1B: Trích xuất Process Metamodel từ XES
│   ├── mde/                            # Bước 2 (Tầng 1 & 2): Metamodel AST & Kiểm tra kiểu tĩnh
│   │   ├── __init__.py
│   │   ├── constraint_ast.py           # Bước 2.1: Khuôn mẫu AST Pydantic (OVAS + Declare4Py)
│   │   └── typing_environment.py       # Bước 2.2: Context-Bound Typing Environment Γ & δ(C, p)
│   ├── neural/                         # Bước 2.3: Truy xuất RAG BM25 & Vòng lặp CEGIS
│   │   ├── __init__.py
│   │   ├── rag_retriever.py            # Bước 2.3a: Truy xuất điều khoản BM25Okapi
│   │   └── synthesis_loop.py           # Bước 2.3b: Vòng lặp tổng hợp & tự sửa lỗi MDE
│   ├── symbolic/                       # Bước 3 (Tầng 3): Trọng tài Kiểm chứng Tất định & Tự sửa Ngữ nghĩa
│   │   ├── __init__.py
│   │   ├── verbalizer_roundtrip.py     # Bước 3.1: Dịch ngược tất định & kiểm tra đối chiếu Round-trip
│   │   └── declare4py_verifier.py      # Bước 3.2 & 3.3: Kiểm tra Vacuity, Conformance & Semantic Repair
│   └── evaluation/                     # Bước 4: Gán nhãn 3 Trạng thái & Báo cáo Giải trình Tất định
│       ├── __init__.py
│       ├── trace_safety_classifier.py  # Bước 4.1: Tập điều kiện an toàn Φ & nhãn ENTAILED/CONTRADICTED/BASELESS
│       ├── justification_tree.py       # Bước 4.2: Cây biện minh tất định (xpSHACL) & Minimal Correction (MCS)
│       └── grounded_auditor.py         # Bước 4.3: Sinh báo cáo giải trình khóa nguồn & Hậu kiểm trích dẫn
├── scripts/
│   ├── run_phase1a.py                  # Thực thi Bước 1A
│   ├── run_phase1b.py                  # Thực thi Bước 1B
│   ├── run_phase2.py                   # Thực thi Bước 2 (Tầng 1 + Tầng 2 + CEGIS)
│   ├── run_phase3.py                   # Thực thi Bước 3 (Tầng 3: Vacuity + Round-trip + Declare4Py)
│   └── run_phase4.py                   # Thực thi Bước 4 (3-Valued Labeling + Justification Tree + Audit Report)
├── tests/
│   ├── test_parse_directive.py         # Unit tests Bước 1A
│   ├── test_extract_process_schema.py  # Unit tests Bước 1B
│   ├── test_phase2_mde_synthesis.py    # Unit tests Bước 2
│   ├── test_phase3_layer3_verifier.py  # Unit tests Bước 3
│   └── test_phase4_accountable_audit.py# Unit tests Bước 4
├── results/
│   ├── layer3_conformance_report.json          # Kết quả kiểm chứng tuân thủ Bước 3 trên 31,509 hồ sơ
│   └── step4_accountable_audit_reports.json    # Kết quả giải trình kiểm toán tất định Bước 4
├── requirements.txt                    # Danh sách thư viện Python
└── README.md                           # Tài liệu hướng dẫn dự án
```

---

## Hướng dẫn chạy toàn bộ Pipeline (trong môi trường `.venv`)

```powershell
# Bước 1A: Phân rã văn bản luật Directive 2008/48/EC -> directive_chunks.json
.\.venv\Scripts\python.exe scripts\run_phase1a.py

# Bước 1B: Trích xuất Process Metamodel từ BPI Challenge 2017 -> process_schema.json
.\.venv\Scripts\python.exe scripts\run_phase1b.py

# Bước 2: Tổng hợp ràng buộc DECLARE có hướng dẫn của MDE (Tầng 1 & Tầng 2)
.\.venv\Scripts\python.exe scripts\run_phase2.py

# Bước 3: Kiểm chứng tất định Tầng 3 (Vacuity + Round-trip + Declare4Py Conformance)
.\.venv\Scripts\python.exe scripts\run_phase3.py

# Bước 4: Gán nhãn chống ảo giác 3 trạng thái & Sinh báo cáo giải trình tất định
.\.venv\Scripts\python.exe scripts\run_phase4.py

# Chạy toàn bộ bộ kiểm thử tự động (Unit Tests cho cả 4 bước)
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
