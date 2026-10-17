# Neuro-Symbolic + MDE for Trustworthy Reasoning in Process Mining

Dự án nghiên cứu kết hợp **Neuro-Symbolic AI** và **Model-Driven Engineering (MDE)** nhằm phục vụ suy luận tin cậy (Trustworthy Reasoning) và kiểm tra tuân thủ (Compliance Checking) trong **Khai phá quy trình (Process Mining)** trên bộ dữ liệu thực tế **BPI Challenge 2017** và văn bản luật tín dụng tiêu dùng châu Âu **Directive 2008/48/EC**.

---

## Cấu trúc thư mục dự án

```text
neuron_symbolic_reasoning/
├── .venv/                              # Môi trường ảo Python (Python 3.13)
├── configs/
│   └── config.yaml                     # Cấu hình đường dẫn dữ liệu & tham số pipeline
├── datasets/                           # Dữ liệu gốc (Raw Datasets)
│   ├── directive_2008_48_EC.pdf        # Văn bản luật EU Consumer Credit Directive 2008/48/EC
│   └── BPI Challenge 2017.xes          # Nhật ký sự kiện quy trình cho vay (Event Log)
├── data/
│   ├── interim/                        # Dữ liệu trung gian (Parquet cache tăng tốc đọc XES)
│   │   └── bpic2017_events.parquet     # Bộ nhớ đệm DataFrame chuẩn pm4py
│   └── processed/                      # Dữ liệu đã qua tiền xử lý
│       ├── directive_chunks.json       # Kết quả Phần 1A: Phân đoạn điều khoản (Articles 1–24)
│       └── process_schema.json         # Kết quả Phần 1B: Lược đồ Quy trình & Typing Environment Γ
├── src/                                # Mã nguồn chính của dự án
│   ├── __init__.py
│   ├── preprocessing/                  # Giai đoạn 1: Tiền xử lý văn bản luật & Event Log
│   │   ├── __init__.py
│   │   ├── parse_directive.py          # Phần 1A: Bóc tách điều khoản nghiệp vụ (Articles 1–24)
│   │   └── extract_process_schema.py   # Phần 1B: Trích xuất Process Metamodel từ XES
│   ├── mde/                            # Metamodels & Model Transformations (MDE)
│   │   └── __init__.py
│   ├── neural/                         # Trích xuất tri thức luật & ánh xạ ngữ nghĩa bằng LLM/NLP
│   │   └── __init__.py
│   ├── symbolic/                       # Suy luận hình thức & kiểm chứng ràng buộc (Declare/LTLf/SMT)
│   │   └── __init__.py
│   └── evaluation/                     # Đánh giá độ tin cậy, kiểm tra tuân thủ & giải thích
│       └── __init__.py
├── scripts/
│   ├── run_phase1a.py                  # Script thực thi Phần 1A
│   └── run_phase1b.py                  # Script thực thi Phần 1B
├── notebooks/                          # Jupyter Notebooks phân tích khám phá & trực quan hóa
├── tests/
│   ├── test_parse_directive.py         # Unit tests kiểm thử Phần 1A
│   └── test_extract_process_schema.py  # Unit tests kiểm thử Phần 1B
├── results/                            # Kết quả thực nghiệm, bảng biểu, báo cáo
├── requirements.txt                    # Danh sách thư viện Python
└── README.md                           # Tài liệu hướng dẫn dự án
```

---

## Hướng dẫn chạy (trong môi trường `.venv`)

### 1. Cài đặt thư viện
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Chạy Phần 1A: Phân rã Văn bản Luật theo Cấu trúc Điều khoản (`directive_2008_48_EC.pdf` $\rightarrow$ `directive_chunks.json`)
```powershell
.\.venv\Scripts\python.exe scripts\run_phase1a.py
```

### 3. Chạy Phần 1B: Trích xuất Lược đồ Quy trình từ Event Log (`BPI Challenge 2017.xes` $\rightarrow$ `process_schema.json`)
```powershell
.\.venv\Scripts\python.exe scripts\run_phase1b.py
```

### 4. Chạy bộ kiểm thử tự động (Unit Tests)
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
