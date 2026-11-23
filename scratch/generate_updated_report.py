"""Generate the updated, publication-grade Word (.docx) report synchronized with the current
Behavioral-Aware Deontic Neuro-Symbolic architecture and clean 3-model experimental results."""

from pathlib import Path
import docx
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

OUT_PATH = Path(r"d:\AI Project\neuron_symbolic_reasoning\reports\Neuro-Symbolic_for_Trustworthy_Reasoning_in_Process_Mining_Updated.docx")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

PRIMARY_HEX = "1B365D"      # Deep academic navy
ACCENT_HEX = "2B5B84"       # Medium steel blue
LIGHT_BG_HEX = "EEF3F8"     # Soft blue-gray tint
ZEBRA_HEX = "F8FAFC"        # Very light table alternating row
BORDER_HEX = "CBD5E1"       # Subtle slate border
CALLOUT_BG_HEX = "F1F5F9"   # Callout box fill

NAVY_RGB = RGBColor(0x1B, 0x36, 0x5D)
ACCENT_RGB = RGBColor(0x2B, 0x5B, 0x84)
TEXT_RGB = RGBColor(0x1E, 0x29, 0x3B)
MUTED_RGB = RGBColor(0x47, 0x55, 0x69)


def set_cell_shading(cell, fill_hex: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def set_table_borders(table, color: str = BORDER_HEX) -> None:
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{PRIMARY_HEX}"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{PRIMARY_HEX}"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideV w:val="none"/>'
        f"</w:tblBorders>"
    )
    tblPr.append(borders)


def add_heading_1(doc: docx.Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="8" w:space="4" w:color="{ACCENT_HEX}"/></w:pBdr>'
    )
    pPr.append(pBdr)
    r = p.add_run(text)
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(14)
    r.font.color.rgb = NAVY_RGB


def add_heading_2(doc: docx.Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(11.5)
    r.font.color.rgb = ACCENT_RGB


def add_body(doc: docx.Document, text: str, bold_prefix: str = "", italic: bool = False) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        rb.bold = True
        rb.font.name = "Calibri"
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = TEXT_RGB
    r = p.add_run(text)
    r.italic = italic
    r.font.name = "Calibri"
    r.font.size = Pt(10.5)
    r.font.color.rgb = MUTED_RGB if italic else TEXT_RGB


def add_bullet(doc: docx.Document, bold_prefix: str, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_before = Pt(1.5)
    p.paragraph_format.space_after = Pt(2.5)
    p.paragraph_format.line_spacing = 1.12
    if bold_prefix:
        rb = p.add_run(bold_prefix)
        rb.bold = True
        rb.font.name = "Calibri"
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = TEXT_RGB
    r = p.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(10.5)
    r.font.color.rgb = TEXT_RGB


def add_code_block(doc: docx.Document, code_text: str) -> None:
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_shading(cell, CALLOUT_BG_HEX)
    set_cell_margins(cell, top=90, bottom=90, left=150, right=150)
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(
        parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:left w:val="single" w:sz="18" w:space="0" w:color="{ACCENT_HEX}"/>'
            f'<w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>'
            f"</w:tcBorders>"
        )
    )
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    r = p.add_run(code_text)
    r.font.name = "Consolas"
    r.font.size = Pt(9)
    r.font.color.rgb = TEXT_RGB
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(4)


def add_callout(doc: docx.Document, title: str, text: str) -> None:
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_shading(cell, LIGHT_BG_HEX)
    set_cell_margins(cell, top=100, bottom=100, left=160, right=160)
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(
        parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:left w:val="single" w:sz="20" w:space="0" w:color="{PRIMARY_HEX}"/>'
            f'<w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>'
            f"</w:tcBorders>"
        )
    )
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    rt = p.add_run(title + " ")
    rt.bold = True
    rt.font.name = "Calibri"
    rt.font.size = Pt(10)
    rt.font.color.rgb = NAVY_RGB
    rb = p.add_run(text)
    rb.font.name = "Calibri"
    rb.font.size = Pt(10)
    rb.font.color.rgb = TEXT_RGB
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(4)


def add_styled_table(
    doc: docx.Document,
    headers: list[str],
    rows: list[list[str]],
    col_widths_cm: list[float] | None = None,
    bold_last_row: bool = False,
    bold_rows: set[int] | None = None,
    left_cols: set[int] | None = None,
) -> None:
    left_cols = left_cols or {0}
    bold_rows = bold_rows or set()
    tbl = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    # Header row
    hdr_tr = tbl.rows[0]._tr
    trPr = hdr_tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:tblHeader"))
    for ci, h in enumerate(headers):
        cell = tbl.cell(0, ci)
        set_cell_shading(cell, PRIMARY_HEX)
        set_cell_margins(cell, top=80, bottom=80, left=80, right=80)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci in left_cols else WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(h)
        r.bold = True
        r.font.name = "Calibri"
        r.font.size = Pt(9.2)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Data rows
    for ri, row_vals in enumerate(rows):
        is_emph = (bold_last_row and ri == len(rows) - 1) or (ri in bold_rows)
        fill = LIGHT_BG_HEX if is_emph else (ZEBRA_HEX if ri % 2 == 1 else "FFFFFF")
        for ci, val in enumerate(row_vals):
            cell = tbl.cell(ri + 1, ci)
            if fill != "FFFFFF":
                set_cell_shading(cell, fill)
            set_cell_margins(cell, top=65, bottom=65, left=80, right=80)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci in left_cols else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val)
            r.bold = is_emph
            r.font.name = "Calibri"
            r.font.size = Pt(9.2)
            r.font.color.rgb = NAVY_RGB if is_emph else TEXT_RGB

    if col_widths_cm:
        for row in tbl.rows:
            for ci, w in enumerate(col_widths_cm):
                row.cells[ci].width = Cm(w)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(4)


def build_report() -> None:
    doc = docx.Document()

    # Page setup (A4, balanced margins)
    for sec in doc.sections:
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(2.0)
        sec.left_margin = Cm(2.0)
        sec.right_margin = Cm(2.0)

    # Default Normal style
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = TEXT_RGB

    # =========================================================================
    # TITLE BLOCK
    # =========================================================================
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(6)
    title_p.paragraph_format.space_after = Pt(4)
    rt = title_p.add_run("Neuro-Symbolic + MDE for Trustworthy Reasoning in Process Mining")
    rt.bold = True
    rt.font.name = "Calibri"
    rt.font.size = Pt(18)
    rt.font.color.rgb = NAVY_RGB

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(10)
    rs = sub_p.add_run(
        "Báo cáo Kỹ thuật & Kết quả Thực nghiệm — Kiến trúc Biên dịch Deontic Hướng Hành vi "
        "(Behavioral-Aware Deontic MDE), Thẩm định Phản thực tế và Chốt An toàn Tri thức Φ"
    )
    rs.italic = True
    rs.font.name = "Calibri"
    rs.font.size = Pt(10.5)
    rs.font.color.rgb = MUTED_RGB

    add_body(
        doc,
        "Dự án nghiên cứu kết hợp Trí tuệ nhân tạo Tượng trưng – Nơ-ron (Neuro-Symbolic AI) và Kỹ nghệ Hướng mô hình "
        "(Model-Driven Engineering – MDE) nhằm giải quyết các bài toán cốt lõi khi ứng dụng Mô hình ngôn ngữ lớn (LLM) "
        "vào kiểm tra tuân thủ quy trình kinh doanh (Business Process Compliance Checking): ảo giác quy tắc/ngưỡng số, "
        "đảo ngược quan hệ thời gian, thiếu khả năng giải trình toán học và chi phí suy luận cao trên vết sự kiện dài.",
    )
    add_body(
        doc,
        "Hệ thống được kiểm chứng thực nghiệm trên văn bản pháp lý tín dụng tiêu dùng châu Âu (EU Consumer Credit "
        "Directive 2008/48/EC) và nhật ký sự kiện ngân hàng thực tế quy mô lớn (BPI Challenge 2017 gồm 31.509 hồ sơ và "
        "hơn 1,2 triệu sự kiện), đánh giá chéo trên 3 mô hình LLM mã nguồn mở thuộc 3 kích cỡ/kiến trúc khác nhau: "
        "openai/gpt-oss-120b (mô hình chính, đầy đủ Baseline 1 và giải trình XAI), qwen/qwen3.8-27b và openai/gpt-oss-20b.",
    )

    # =========================================================================
    # OVERVIEW OF 5 STAGES
    # =========================================================================
    add_heading_1(doc, "TỔNG QUAN KIẾN TRÚC HỆ THỐNG (5 GIAI ĐOẠN HỢP NHẤT)")
    add_body(
        doc,
        "Khác với mô hình kiểm tra cú pháp/kiểu tĩnh chia tầng truyền thống trên sơ đồ lớp tĩnh, kiến trúc mới được tổ "
        "chức thành một quy trình biên dịch mô hình hướng hành vi quy trình (Behavioral-Aware Deontic Neuro-Symbolic "
        "Pipeline) gồm 5 giai đoạn liên hoàn:",
    )
    add_styled_table(
        doc,
        headers=["Giai đoạn", "Tên thành phần", "Đầu vào / Đầu ra chính", "Mã nguồn"],
        rows=[
            [
                "Giai đoạn 1",
                "Tiền xử lý Luật & Khai phá Behavioral Profile",
                "EU Directive PDF + BPIC 2017 XES → directive_chunks.json (77 đoạn) & process_schema.json (DFG, Causal, Mutex)",
                "src/preprocessing/",
            ],
            [
                "Giai đoạn 2",
                "Tổng hợp Deontic PIM & Biên dịch Hướng Hành vi",
                "Điều khoản luật + Behavioral Profile → DeonticNormativeFrame (PIM) → Behavioral-Aware M2M Compiler → DeclareConstraintAST (PSM)",
                "src/mde/, src/neural/",
            ],
            [
                "Giai đoạn 3",
                "Thẩm định Phản thực tế & Thực thi Tượng trưng",
                "DECLARE PSM → Numeric Entity Guard + Counterfactual Trace Probing (τ+/τ−/Case C) + Vacuity Check + Declare4Py",
                "src/symbolic/",
            ],
            [
                "Giai đoạn 4",
                "Phán quyết 3 Trạng thái (Φ) & Giải trình Minh bạch",
                "Hồ sơ vay + Kết quả Declare4Py → Safety Guard Φ (ENTAILED / CONTRADICTED / BASELESS) → Justification Tree → Post-hoc Grounding Guard",
                "src/evaluation/",
            ],
            [
                "Giai đoạn 5",
                "Thiết kế Thực nghiệm Sạch & Đánh giá Đa mô hình",
                "30 quy tắc R01–R30 (DEV/HELDOUT) & 300 mẫu phân tầng → RQ1, RQ2 Ablation, RQ3 XAI & Cross-Model Evaluation",
                "src/evaluation/, scripts/",
            ],
        ],
        col_widths_cm=[2.3, 4.3, 7.6, 2.8],
        left_cols={0, 1, 2, 3},
    )

    # =========================================================================
    # STAGE 1
    # =========================================================================
    add_heading_1(doc, "GIAI ĐOẠN 1: TIỀN XỬ LÝ LUẬT & KHAI PHÁ BEHAVIORAL PROFILE")

    add_heading_2(doc, "Bước 1: Phân rã văn bản pháp lý (Legal Clause Decomposition)")
    add_body(
        doc,
        "Bóc tách văn bản EU Consumer Credit Directive 2008/48/EC thành các đoạn điều khoản độc lập, lưu tại "
        "data/processed/directive_chunks.json gồm 77 phân đoạn điều khoản (Articles 1–24). Mỗi đối tượng gồm:",
    )
    add_bullet(doc, "article_id: ", 'Mã định danh điều khoản (ví dụ: "Article 14(1)").')
    add_bullet(doc, "article_title: ", 'Tiêu đề điều khoản (ví dụ: "Right of withdrawal").')
    add_bullet(doc, "text: ", "Nguyên văn nội dung pháp lý.")
    add_bullet(doc, "has_numeric_bound: ", "Cờ boolean đánh dấu điều khoản có chứa mốc thời gian hoặc ngưỡng số định lượng.")

    add_heading_2(doc, "Bước 2: Khai phá Lược đồ Quy trình & Ma trận Hành vi (Process Behavioral Profile)")
    add_body(
        doc,
        "Sử dụng pm4py và pandas nạp toàn bộ 31.509 hồ sơ vay từ BPIC 2017 (lưu bản đệm tăng tốc "
        "data/interim/bpic2017_events.parquet) để trích xuất siêu mô hình quy trình vào data/processed/process_schema.json. "
        "Điểm nâng cấp trọng tâm so với lược đồ tĩnh thông thường là việc khai phá trực tiếp hành vi động của Event Log:",
    )
    add_bullet(
        doc,
        "Danh mục 26 hoạt động hợp lệ & từ điển trung lập (activity_descriptions): ",
        "Phân tách theo 3 phân hệ Application (A_*), Offer (O_*), Workflow (W_*). Toàn bộ 26 mô tả đều chỉ giải thích "
        "nghiệp vụ hệ thống thuần túy (0 từ khóa pháp lý như Directive, Article, 14 days, creditworthiness, withdrawal).",
    )
    add_bullet(
        doc,
        "Thuộc tính Case & Event kèm miền hoạt động áp dụng (applicable_activities): ",
        "Ghi nhận kiểu dữ liệu (String, Float, Boolean, Timestamp), giá trị mẫu và tập hoạt động thực sự có ghi nhận "
        "thuộc tính (ví dụ: OfferedAmount, CreditScore, NumberOfTerms, MonthlyCost, Selected chỉ xuất hiện trên O_Create Offer).",
    )
    add_bullet(
        doc,
        "Ma trận Quan hệ Hành vi (behavioral_profile): ",
        "Khai phá 98 cặp nhân quả nghiêm ngặt (strict_causal_pairs: from -> to kèm order_ratio, P(to|from), P(from|to), "
        "direct_dfg_count, median_days) và 8 cặp nhánh loại trừ lẫn nhau (mutually_exclusive_pairs với co_occurrence_rate <= 0.01 "
        "như O_Accepted vs A_Cancelled, A_Pending vs A_Denied).",
    )
    add_code_block(
        doc,
        '"behavioral_profile": {\n'
        '  "total_cases": 31509,\n'
        '  "strict_causal_pairs": [\n'
        '    {"from": "O_Create Offer", "to": "O_Created", "order_ratio": 1.0, "prob_to_given_from": 1.0, "direct_dfg_count": 42995},\n'
        '    {"from": "O_Sent (mail and online)", "to": "A_Cancelled", "order_ratio": 1.0, "prob_to_given_from": 0.329, "prob_from_given_to": 0.980}\n'
        '  ],\n'
        '  "mutually_exclusive_pairs": [\n'
        '    {"act_a": "O_Accepted", "act_b": "A_Cancelled", "co_occurrence_cases": 0, "co_occurrence_rate": 0.0}\n'
        '  ]\n'
        '}',
    )

    add_heading_2(doc, "Bước 3: Khởi tạo Chỉ mục Ngược BM25 (DirectiveRAGRetriever)")
    add_body(
        doc,
        "Tokenize toàn bộ 77 điều khoản luật và lập chỉ mục bằng thuật toán BM25Okapi để truy xuất điều khoản phù hợp "
        "theo truy vấn nghiệp vụ mà không dùng bất kỳ bảng ánh xạ thủ công nào.",
    )

    # =========================================================================
    # STAGE 2
    # =========================================================================
    add_heading_1(doc, "GIAI ĐOẠN 2: TỔNG HỢP DEONTIC PIM & BIÊN DỊCH HƯỚNG HÀNH VI")
    add_body(
        doc,
        "Thay vì để LLM viết trực tiếp cú pháp ràng buộc đích rồi hậu kiểm qua nhiều tầng kiểu tĩnh, Giai đoạn 2 tách "
        "biệt rạch ròi giữa (i) trích xuất Mô hình Chuẩn tắc Độc lập Nền tảng (Deontic PIM) có khóa văn phạm và "
        "(ii) Trình biên dịch Mô hình sang Mô hình Hướng Hành vi (Behavioral-Aware Deontic M2M Compiler) chuyển PIM sang "
        "DeclareConstraintAST (PSM).",
    )

    add_heading_2(doc, "Bước 1: Đóng gói Ngữ cảnh & Giải mã Ép Văn phạm (Grammar-Constrained Deontic PIM)")
    add_bullet(
        doc,
        "Đầu vào trung lập (Zero Prompt Leakage): ",
        "Chỉ truyền nguyên văn điều khoản luật, yêu cầu chính sách vận hành, từ điển 26 hoạt động, tóm tắt Behavioral "
        "Profile và danh mục thuộc tính kèm kiểu/miền áp dụng; kèm đúng 2 ví dụ trung lập ngoài BPIC 2017 "
        "(Identity_Verification -> Account_Opening và Create_Offer -> Send_Confirmation). Không có ví dụ bẫy BASELESS.",
    )
    add_bullet(
        doc,
        "Khóa không gian sinh động (build_constrained_deontic_schema): ",
        "Tự động biên dịch process_schema.json thành Pydantic Literal Enum (ValidActEnum, ValidAttrEnum) bổ sung token "
        "đặc biệt UNMAPPED_MISSING_IN_LOG để mô hình khai báo tường minh khi chính sách đòi thuộc tính không tồn tại trong log.",
    )
    add_bullet(
        doc,
        "Mô hình Trung gian DeonticNormativeFrame (PIM): ",
        "Tách riêng thái độ chuẩn tắc pháp lý (deontic_modality ∈ {OBLIGATION, PROHIBITION, PERMISSION_RIGHT, "
        "EXEMPTION_OUT_OF_SCOPE}) khỏi quan hệ thời gian (temporal_relation ∈ {PREREQUISITE_BEFORE, IMMEDIATE_PREREQUISITE, "
        "MANDATORY_RESPONSE, IMMEDIATE_RESPONSE, MUTUAL_EXCLUSION, UNARY_CONDITION}), giúp LLM không phải tự suy luận cú pháp DECLARE.",
    )
    add_code_block(
        doc,
        '{\n'
        '  "article_id": "Article 14(1)",\n'
        '  "deontic_modality": "PERMISSION_RIGHT",\n'
        '  "temporal_relation": "PREREQUISITE_BEFORE",\n'
        '  "anchor_activity": "O_Sent (mail and online)",\n'
        '  "consequent_activity": "A_Cancelled",\n'
        '  "attribute_guard": null, "guard_operator": null, "guard_threshold": null,\n'
        '  "deadline_days": 14, "unsupported_by_text": false\n'
        '}',
    )

    add_heading_2(doc, "Bước 2: Trình biên dịch Deontic Hướng Hành vi (Behavioral-Aware M2M Compiler)")
    add_body(
        doc,
        "Hàm compile_deontic_to_declare4py() và check_behavioral_profile_grounding() trong src/mde/deontic_mde_compiler.py "
        "kết hợp ProcessSchemaValidator (src/mde/typing_environment.py) thực thi 5 cơ chế biên dịch và kiểm chứng đặc thù "
        "cho Process Mining trước khi chuyển sang Giai đoạn 3:",
    )
    add_bullet(
        doc,
        "1. Deontic-Temporal Modality Compilation (PIM → PSM): ",
        "Ánh xạ tất định cả 4 thái độ chuẩn tắc: OBLIGATION giữ quan hệ dương; PROHIBITION chuyển sang tập cấm đoán "
        "(Absence, Not Response, Not Precedence); PERMISSION_RIGHT (quyền tự nguyện có điều kiện/thời hạn như quyền rút "
        "khỏi hợp đồng — không bắt buộc xảy ra sau mọi kích hoạt) tự động biên dịch MANDATORY_RESPONSE → Precedence và "
        "IMMEDIATE_RESPONSE → Chain Precedence; EXEMPTION_OUT_OF_SCOPE và UNMAPPED_MISSING_IN_LOG dừng ngay ở chế độ "
        "Zero-Retry BASELESS.",
    )
    add_bullet(
        doc,
        "2. Process Schema & Causal Attribute Availability Validation (ProcessSchemaValidator): ",
        "Kiểm tra tên hoạt động hợp lệ, chặn self-loop (A == B), kiểm tra tương thích kiểu toán tử – giá trị, và kiểm "
        "tra tính khả dụng nhân quả của thuộc tính sự kiện (nếu thuộc tính chỉ phát sinh ở hoạt động xảy ra sau anchor_activity "
        "theo strict_causal_pairs, trả về Causal Attribute Availability Violation kèm gợi ý hoạt động neo đúng).",
    )
    add_bullet(
        doc,
        "3. Direct DFG Adjacency Check: ",
        "Ràng buộc liền kề tức thời (Chain Precedence / Chain Response) bắt buộc cặp (A, B) phải có chuyển tiếp trực "
        "tiếp (direct_dfg_count > 0) trong DFG của Event Log.",
    )
    add_bullet(
        doc,
        "4. Strict Causal Direction Invariant Check: ",
        "Dựa trên strict_causal_pairs (order_ratio >= 0.99, co_occurrence_cases >= 100), chặn lỗi Causal Direction "
        "Inversion khi công thức đòi A trước B ngược chiều bất biến của hệ thống (B luôn trước A), đồng thời chặn "
        "Vacuous Reversed Prohibition đối với Not Precedence(A, B) khi B luôn xảy ra trước A.",
    )
    add_bullet(
        doc,
        "5. Behavioral Mutual-Exclusion & Lifecycle Co-Occurrence Check: ",
        "Chặn các ràng buộc đồng xuất hiện dương trên cặp nhánh loại trừ (co_occurrence_rate <= 0.01) và chặn "
        "Not Co-Existence trên các cặp bất biến luôn cùng xảy ra (order_ratio >= 0.99, hỗ trợ hai chiều >= 99%, >= 1.000 hồ sơ).",
    )
    add_body(
        doc,
        "Khi trình biên dịch phát hiện vi phạm (COMPILE_ERROR), thông điệp chẩn đoán hành vi chi tiết được phản hồi lại "
        "cho LLM trong vòng lặp tự sửa CEGIS (tối đa max_retry = 5 lượt ở temperature = 0.0).",
    )

    # =========================================================================
    # STAGE 3
    # =========================================================================
    add_heading_1(doc, "GIAI ĐOẠN 3: THẨM ĐỊNH PHẢN THỰC TẾ & THỰC THI TƯỢNG TRƯNG")
    add_body(
        doc,
        "Đảm bảo công thức DECLARE sau biên dịch trung thực tuyệt đối về ngữ nghĩa pháp lý, không bịa đặt ngưỡng số, "
        "không nhầm chiều tiền đề/hệ quả và không rỗng trên dữ liệu thật trước khi đưa vào động cơ kiểm tra tuân thủ.",
    )

    add_heading_2(doc, "Bước 1: Dịch ngược Tất định & Chốt Thực thể Định lượng (Numeric Entity Guard)")
    add_bullet(
        doc,
        "Dịch ngược tất định (verbalize_declare_ast): ",
        'Biến đổi công thức AST thành câu tiếng Anh chuẩn xác theo ngữ nghĩa toán học DECLARE (ví dụ: Precedence(A, B) '
        '→ "Whenever B occurs, A must have occurred BEFORE it").',
    )
    add_bullet(
        doc,
        "Numeric Entity Guard (verify_generic_numeric_entities): ",
        "Trích xuất tất cả thực thể số và đơn vị thời gian trong nguyên văn điều khoản luật bằng Regex (tự quy đổi đơn "
        "vị như 1 month ↔ 30 days, 3 months ↔ 90 days). Nếu công thức chứa con số xuất hiện trong yêu cầu chính sách nhưng "
        "không tồn tại trong điều khoản luật (POLICY_STATUTE_NUMERIC_CONFLICT), dừng ngay và gán BASELESS với 0 lượt gọi API.",
    )

    add_heading_2(doc, "Bước 2: Thẩm định bằng Đột biến Vết Đối chứng (Counterfactual Trace Mutation Probing)")
    add_body(
        doc,
        "Hàm verify_via_counterfactual_probing() trong src/symbolic/counterfactual_prober.py sinh tất định bộ kịch bản "
        "tổng hợp từ công thức DECLARE để thẩm định không cần đáp án chuẩn:",
    )
    add_bullet(doc, "Case A (Vết tuân thủ τ+): ", "Kịch bản tối thiểu thỏa mãn công thức ứng viên.")
    add_bullet(
        doc,
        "Case B (Vết đột biến vi phạm τ−): ",
        "Áp dụng toán tử đột biến chuyên biệt (đảo thứ tự, bỏ sự kiện tiền đề/hệ quả, vượt ngưỡng thời gian +5 ngày, "
        "hoặc vi phạm ngưỡng thuộc tính) để tạo ca vi phạm đặc trưng.",
    )
    add_bullet(
        doc,
        "Case C (Kiểm tra tính bất đối xứng τ_asym): ",
        "Phân biệt rạch ròi các cặp mẫu dễ nhầm (Precedence cho phép A không có B, trong khi Response cấm A không có B; "
        "Not Co-Existence đối xứng cấm cả B trước A, trong khi Not Response có hướng).",
    )
    add_body(
        doc,
        "Thẩm phán Độc lập (Blind Legal Judge ở temperature = 0.0) đọc nguyên văn điều khoản luật, yêu cầu chính sách, "
        "từ điển hoạt động và bộ kịch bản (Case A, B, C) để phán quyết một trong 5 nhãn: EQUIVALENT, REVERSED_ORDER, "
        "SEMANTIC_MISMATCH, THRESHOLD_MISMATCH hoặc BASELESS. Nếu phát hiện lỗi ngữ nghĩa (không phải BASELESS kết thúc), "
        "phản hồi đột biến được gửi ngược về LLM để sửa ở vòng lặp kế tiếp.",
    )

    add_heading_2(doc, "Bước 3: Kiểm tra Độ rỗng (Log-Grounded Vacuity Check) & Thực thi Declare4Py")
    add_body(
        doc,
        "Công thức đạt thẩm định được biên dịch sang dòng lệnh .decl chuẩn của Declare4Py (ví dụ: "
        "Precedence[O_Sent (mail and online), A_Cancelled] | | | 0,14,d). Hệ thống đếm số lần kích hoạt trên nhật ký sự "
        "kiện để phát hiện ràng buộc rỗng (0 kích hoạt) và chỉ dùng lan truyền thuộc tính nhân quả theo chiều tiến "
        "(forward-fill ffill, tuyệt đối không bfill dữ liệu tương lai ngược về quá khứ).",
    )

    # =========================================================================
    # STAGE 4
    # =========================================================================
    add_heading_1(doc, "GIAI ĐOẠN 4: PHÁN QUYẾT 3 TRẠNG THÁI (Φ) & GIẢI TRÌNH MINH BẠCH")

    add_heading_2(doc, "Bước 1: Tập Điều kiện An toàn Tri thức Φ & Phân loại 3 Trạng thái")
    add_body(
        doc,
        "Hàm evaluate_trace_safety_and_status() (src/evaluation/trace_safety_classifier.py) áp dụng cơ chế tách Giá trị – "
        "Điều kiện An toàn <v, Φ> để đưa ra phán quyết 3 giá trị cho từng hồ sơ vay:",
    )
    add_bullet(
        doc,
        "BASELESS (Thiếu căn cứ pháp lý / Thiếu bằng chứng log Φ): ",
        "Kích hoạt khi quy tắc bị chặn là bẫy luật/lược đồ ở Giai đoạn 2–3 (OUT_OF_DIRECTIVE_SCOPE, "
        "MISSING_LOG_EVIDENCE_PHI_VIOLATION, POLICY_STATUTE_NUMERIC_CONFLICT), hoặc khi hồ sơ thiếu thuộc tính bắt buộc "
        "(NaN) / không chứa sự kiện kích hoạt để đánh giá (INAPPLICABLE_TRACE).",
    )
    add_bullet(
        doc,
        "ENTAILED (Tuân thủ): ",
        "Điều kiện an toàn Φ được thỏa mãn và động cơ Declare4Py xác nhận vết sự kiện thỏa mãn công thức.",
    )
    add_bullet(
        doc,
        "CONTRADICTED (Vi phạm): ",
        "Điều kiện an toàn Φ được thỏa mãn nhưng động cơ Declare4Py phát hiện vi phạm (vượt hạn ngày, đảo thứ tự, "
        "thiếu sự kiện bắt buộc, hoặc vi phạm ngưỡng dữ liệu), kèm trích xuất tập hiệu chỉnh tối thiểu (MCS) và bản chụp "
        "phản ví dụ cụ thể (Concrete Counterexample Snapshot).",
    )

    add_heading_2(doc, "Bước 2: Cây Biện minh Tất định & Chốt chặn Hậu kiểm (Post-hoc Grounding Guard)")
    add_body(
        doc,
        "Cây biện minh tất định (build_justification_tree) đóng gói chuỗi chứng cứ bất biến: Mã điều luật → Công thức "
        "DECLARE → Mốc thời gian và hoạt động thực tế trong log → Phán quyết & MCS. LLM chỉ đóng vai trò diễn đạt Cây "
        "biện minh thành văn bản kiểm toán tự nhiên ở temperature = 0.0 (generate_accountable_explanation), sau đó bắt "
        "buộc đi qua chốt hậu kiểm verify_posthoc_grounding() đối chiếu hai chiều mã case_id, nhãn phán quyết (chặn phủ "
        "định/mâu thuẫn), số hiệu Article (chặn bịa điều khoản ngoài), các con số độ lệch thời gian và tên hoạt động vi "
        "phạm (có 1 vòng tự sửa nếu thiếu neo trích dẫn).",
    )

    # =========================================================================
    # STAGE 5
    # =========================================================================
    add_heading_1(doc, "GIAI ĐOẠN 5: THIẾT KẾ BENCHMARK SẠCH & QUY TRÌNH ĐÁNH GIÁ")

    add_heading_2(doc, "Bước 1: Bộ 30 Quy tắc Chuẩn R01–R30 phân tầng DEV / HELDOUT_TEST")
    add_body(
        doc,
        "Toàn bộ 30 quy tắc xây dựng từ EU Directive 2008/48/EC được tách phân tầng chặt chẽ thành DEV (15 quy tắc: "
        "6 Tier 1 + 5 Tier 2 + 4 Tier 3) và HELDOUT_TEST (15 quy tắc: 6 Tier 1 + 5 Tier 2 + 4 Tier 3) với 0 quy tắc "
        "trùng lặp về chữ ký chuẩn tắc:",
    )
    add_bullet(
        doc,
        "Tier 1 — Luồng điều khiển (R01–R12, 12 quy tắc): ",
        "Precedence, Chain Precedence, Response, Chain Response, Not Response, Not Precedence, Not Co-Existence giữa các "
        "mốc nghiệp vụ lõi của quy trình tín dụng.",
    )
    add_bullet(
        doc,
        "Tier 2 — Thời gian & Dữ liệu (R13–R22, 10 quy tắc): ",
        "Giới hạn 14 ngày / 30 ngày (quyền rút lui Điều 14, chấm dứt hợp đồng Điều 13) và các điều kiện dữ liệu "
        "(ApplicationType == 'Limit raise', RequestedAmount > 0, OfferedAmount > 0, CreditScore > 0, NumberOfTerms > 0, "
        "MonthlyCost > 0, Selected == True).",
    )
    add_bullet(
        doc,
        "Tier 3 — Bẫy Ảo giác & An toàn Tri thức (R23–R30, 8 quy tắc): ",
        "Gồm 6 bẫy luật/lược đồ (Rule/Schema Traps) được thiết kế tinh vi dùng chính các con số/điều khoản thật nhưng "
        "bóp méo ngữ nghĩa pháp lý, và 2 bẫy thiếu dữ kiện trên hồ sơ (Trace Safety Traps Φ):",
    )
    add_styled_table(
        doc,
        headers=["Mã", "Điều khoản", "Loại bẫy", "Bản chất bẫy kiểm thử mù"],
        rows=[
            ["R23", "Article 14(1)", "Rule Trap (DEV)", "Bóp méo quyền rút lui 14 ngày của khách hàng thành nghĩa vụ ngân hàng duyệt giải ngân trong 14 ngày."],
            ["R24", "Article 16(4)", "Rule Trap (HELDOUT)", "Biến ngưỡng ngoại lệ EUR 10.000 của trả nợ trước hạn thành ngưỡng bắt buộc mọi hợp đồng phải vượt EUR 10.000."],
            ["R25", "Article 18(2)", "Rule Trap (DEV)", "Bóp méo mốc 1 tháng (30 ngày) chuyển giao quyền thành nghĩa vụ gọi bổ sung hồ sơ trong 30 ngày sau thẩm định."],
            ["R26", "Article 9(2)", "Rule Trap (HELDOUT)", "Bóp méo nghĩa vụ thông báo kết quả tra cứu khi từ chối thành nghĩa vụ tạo đề nghị vay mới sau khi từ chối."],
            ["R27", "Article 16(2)", "Schema Trap (DEV)", "Yêu cầu kiểm tra phí bồi thường trả nợ trước hạn <= 1.0% (thuộc tính không tồn tại trong log BPIC 2017)."],
            ["R28", "Article 2(3)", "Rule Trap (HELDOUT)", "Bóp méo miễn trừ 3 tháng (90 ngày) của tín dụng ngắn hạn thành hạn mức duyệt khoản vay trong 90 ngày."],
            ["R29", "Article 5(6)", "Trace Φ (DEV)", "Hồ sơ không có sự kiện gửi đề nghị vay nên không áp dụng được điều kiện đánh giá (INAPPLICABLE_TRACE)."],
            ["R30", "Article 10(2)", "Trace Φ (HELDOUT)", "Hồ sơ bị khuyết giá trị số kỳ trả góp NumberOfTerms = NaN (MISSING_LOG_EVIDENCE_PHI_VIOLATION)."],
        ],
        col_widths_cm=[1.3, 2.5, 3.3, 9.9],
        left_cols={2, 3},
    )

    add_heading_2(doc, "Bước 2: Bộ Benchmark 300 Mẫu Hồ sơ Phân tầng")
    add_body(
        doc,
        "Bộ dữ liệu data/processed/benchmark_items.json gồm đúng 300 mẫu (100 ENTAILED, 100 CONTRADICTED, 100 BASELESS), "
        "chia đều 150 DEV (50/50/50) và 150 HELDOUT_TEST (50/50/50) với 300/300 mã hồ sơ (case_id) hoàn toàn duy nhất:",
    )
    add_bullet(
        doc,
        "Độ thực tế dữ liệu cao (224/300 = 74.7% vết nguyên bản từ BPIC 2017): ",
        "100% nhóm tuân thủ (trừ 4 mẫu kiểm tra thứ tự nghịch B-trước-A cho Not Response/Not Precedence) và toàn bộ "
        "các ca vi phạm có sẵn trong log thực tế (như trễ hạn 14/30 ngày, thiếu tiền đề) đều trích trực tiếp từ BPIC 2017.",
    )
    add_bullet(
        doc,
        "Tiêm lỗi ngữ nghĩa chuẩn mực cho các ca hiếm vi phạm: ",
        "Áp dụng tiêm lỗi có kiểm soát (đảo chiều thời gian, chèn bước xen giữa phá vỡ Chain, xóa sự kiện bắt buộc, "
        "vượt ngưỡng dữ liệu hoặc xóa giá trị thuộc tính cho R30) trên nền hồ sơ thực để đảm bảo phủ đều đủ 22/22 quy tắc chuẩn.",
    )

    # =========================================================================
    # EXPERIMENTAL RESULTS
    # =========================================================================
    add_heading_1(doc, "KẾT QUẢ THỰC NGHIỆM (RQ1, RQ2, RQ3 & ĐA MÔ HÌNH)")
    add_body(
        doc,
        "Toàn bộ thực nghiệm được chạy sạch ở mức temperature = 0.0, phạt thẳng các ca không thực thi được (CRASH) vào "
        "Macro Precision/F1, và lưu đệm đầy đủ phản hồi theo mã băm SHA-256 để đảm bảo tái lập 100%.",
    )

    # --- TABLE 1: RQ1 ---
    add_heading_2(doc, "1. Bảng 1 (RQ1): Năng lực Tổng hợp & Kiểm chứng Ngữ nghĩa theo Độ phức tạp (openai/gpt-oss-120b, R01–R22)")
    add_styled_table(
        doc,
        headers=[
            "Độ phức tạp Ràng buộc (Complexity Tier)",
            "Đúng Ngữ nghĩa Eq. (%) ↑",
            "Quá Chặt (%) ↓",
            "Quá Lỏng (%) ↓",
            "Đảo Chiều (%) ↓",
            "Sai Hoạt động (%) ↓",
            "Từ chối / Lỗi khác (%) ↓",
        ],
        rows=[
            ["1A. Round-1 Behavioral Deontic Synthesis (Tắt Counterfactual Probe & tự sửa)", "", "", "", "", "", ""],
            ["  • Tier 1: Control-Flow Only (12 quy tắc)", "58.33%", "0.0%", "8.33%", "0.0%", "33.33%", "0.0%"],
            ["  • Tier 2: Temporal & Data-Aware (10 quy tắc)", "100.0%", "0.0%", "0.0%", "0.0%", "0.0%", "0.0%"],
            ["  • Overall Pipeline (One-Shot Deontic)", "77.27%", "0.0%", "4.55%", "0.0%", "18.18%", "0.0%"],
            ["1B. Full Pipeline (Behavioral Deontic Compiler + Counterfactual Probe + Tự sửa)", "", "", "", "", "", ""],
            ["  • Tier 1: Control-Flow Only (12 quy tắc)", "66.67%", "0.0%", "8.33%", "0.0%", "25.0%", "0.0%"],
            ["  • Tier 2: Temporal & Data-Aware (10 quy tắc)", "90.0%", "0.0%", "0.0%", "0.0%", "0.0%", "10.0%"],
            ["  • Overall Pipeline (Full Proposed)", "77.27%", "0.0%", "4.55%", "0.0%", "13.64%", "4.55%"],
        ],
        col_widths_cm=[6.5, 2.0, 1.5, 1.5, 1.6, 1.9, 2.0],
        bold_rows={0, 3, 4, 7},
    )
    add_body(
        doc,
        "Nhận xét RQ1: Nhờ quy tắc biên dịch Deontic cho PERMISSION_RIGHT và phân tích Behavioral Profile, tỷ lệ lỗi "
        "Đảo chiều (Reversed) giảm tuyệt đối về 0.0%, Crash = 0.0% và Vacuous = 0.0%. Vòng lặp Counterfactual Probing "
        "giúp Tier 1 tăng từ 58.33% lên 66.67% (giảm Sai Hoạt động từ 33.33% xuống 25.0%), trong khi Tier 2 đạt 90.0% "
        "ở Full Pipeline và 100.0% ngay ở Round 1.",
        italic=True,
    )

    # --- TABLE 2: RQ2 ---
    add_heading_2(doc, "2. Bảng 2 (RQ2): Nghiên cứu Triệt tiêu (Ablation Study) & So sánh Baseline (openai/gpt-oss-120b, 300 mẫu)")
    add_styled_table(
        doc,
        headers=[
            "Cấu hình Thực nghiệm (Configuration)",
            "Thực thi Hợp lệ (%) ↑",
            "Norm Eq R01–R22 (%) ↑",
            "Trap Detect R23–R30 (%) ↑",
            "Accuracy (%) ↑",
            "Macro-F1 ↑",
        ],
        rows=[
            ["Baseline 1: Vanilla RAG + LLM Direct QA", "N/A", "N/A", "57.0%", "55.67%", "0.5532"],
            ["Baseline 2: One-Shot LLM-to-DECLARE (Không qua Compiler & Counterfactual)", "90.67%", "67.0%", "63.0%", "67.67%", "0.6772"],
            ["- Behavioral Deontic Compiler (Tắt Biên dịch Deontic & Behavioral Profile)", "90.67%", "54.0%", "76.0%", "76.0%", "0.7586"],
            ["- Self-Correction Loop (Tắt Vòng lặp Tự sửa)", "100.0%", "71.0%", "87.0%", "85.0%", "0.8500"],
            ["Full Neuro-Symbolic Pipeline (Kiến trúc Đề xuất)", "100.0%", "76.0%", "87.0%", "88.33%", "0.8836"],
        ],
        col_widths_cm=[7.0, 2.0, 2.0, 2.1, 1.9, 2.0],
        bold_last_row=True,
    )
    add_bullet(
        doc,
        "Vượt trội toàn diện trước các Baseline: ",
        "Full Pipeline đạt Macro-F1 = 0.8836 (Accuracy = 88.33%), vượt +0.3304 F1 so với Baseline 1 (0.5532) và "
        "+0.2064 F1 so với Baseline 2 (0.6772).",
    )
    add_bullet(
        doc,
        "Vai trò then chốt của Behavioral Deontic Compiler: ",
        "Khi tắt trình biên dịch Deontic & Behavioral Profile (- Behavioral Deontic Compiler), tỷ lệ thực thi rơi xuống "
        "90.67% (phát sinh 9.33% Crash), Norm Eq giảm mạnh từ 76.0% xuống 54.0% và Macro-F1 giảm từ 0.8836 xuống 0.7586 "
        "(-0.1250 F1). Khi bật lại Compiler nhưng tắt tự sửa (- Self-Correction), Macro-F1 đạt 0.8500, và bật đầy đủ "
        "tự sửa CEGIS đẩy tiếp lên 0.8836 (+0.0336 F1).",
    )
    add_bullet(
        doc,
        "Khả năng tổng quát hóa DEV vs HELDOUT_TEST (150 mẫu/tập): ",
        "Tập DEV đạt Accuracy = 92.67%, Macro-F1 = 0.9258 (Trap = 100.0%); tập kiểm thử ẩn HELDOUT_TEST đạt Accuracy = "
        "84.0%, Macro-F1 = 0.8391 (Trap = 74.0%). Chi tiết bẫy: bắt 5/6 bẫy luật/lược đồ (82.89%: R23, R24, R25, R27, R28) "
        "và 2/2 bẫy log Φ (100.0%: R29, R30).",
    )

    # --- TABLE 3: RQ3 ---
    add_heading_2(doc, "3. Bảng 3 (RQ3): Độ Tin cậy Chẩn đoán 3 Trạng thái, Giải trình & Hiệu năng (openai/gpt-oss-120b, 300 mẫu)")
    add_styled_table(
        doc,
        headers=[
            "Nhãn Phân loại (Compliance Verdict)",
            "Precision ↑",
            "Recall ↑",
            "F1-Score ↑",
            "Số vòng sửa TB ↓",
            "Thời gian TB ↓",
            "Citation Fidelity ↑",
        ],
        rows=[
            ["ENTAILED (Tuân thủ — 100 mẫu)", "0.8067", "0.9600", "0.8767", "0.05", "6.7 ms", "76.0%"],
            ["CONTRADICTED (Vi phạm — 100 mẫu)", "0.9535", "0.8200", "0.8817", "0.05", "4.6 ms", "76.0%"],
            ["BASELESS (Ảo giác / Thiếu Φ — 100 mẫu)", "0.9158", "0.8700", "0.8923", "0.00", "1.3 ms", "87.0%"],
            ["Trung bình Toàn hệ thống (Overall — 300 mẫu)", "0.8920", "0.8833", "0.8836", "0.03", "4.2 ms", "79.67%"],
        ],
        col_widths_cm=[5.6, 1.8, 1.7, 1.8, 2.0, 2.0, 2.1],
        bold_last_row=True,
    )
    add_body(
        doc,
        "Nhận xét RQ3: Hệ thống đạt cân bằng cao trên cả 3 lớp (F1 từ 0.8767 đến 0.8923), đặc biệt CONTRADICTED đạt "
        "Precision = 0.9535 (rất ít cảnh báo vi phạm giả) và BASELESS đạt F1 = 0.8923. Thời gian kiểm chứng tượng trưng "
        "chỉ trung bình 4.2 ms/hồ sơ với số vòng sửa trung bình 0.03 lượt; độ trung thực trích dẫn (Citation Fidelity) "
        "được LLM thật diễn giải qua Post-hoc Grounding Guard đạt 79.67% trên toàn bộ 300 mẫu (riêng lớp BASELESS đạt 87.0%).",
        italic=True,
    )

    # --- TABLE 4: CROSS-MODEL ---
    add_heading_2(doc, "4. Bảng 4: Khái quát hóa Đa mô hình (Cross-Model Generalization, 300 mẫu)")
    add_styled_table(
        doc,
        headers=[
            "Mô hình (LLM)",
            "Baseline 2 F1",
            "- Deontic Comp. F1",
            "- SelfCorr F1",
            "Full Exec (%) ↑",
            "Full Rev. (%) ↓",
            "Full Trap (%) ↑",
            "Trace Φ (%) ↑",
            "Full Acc (%) ↑",
            "Full Macro-F1 ↑",
        ],
        rows=[
            ["openai/gpt-oss-20b", "0.5262", "0.6484", "0.6213", "100.0%", "0.0%", "36.0%", "100.0%", "70.67%", "0.6824"],
            ["qwen/qwen3.8-27b", "0.4878", "0.8298", "0.8582", "100.0%", "0.0%", "75.0%", "100.0%", "86.00%", "0.8582"],
            ["openai/gpt-oss-120b", "0.6772", "0.7586", "0.8500", "100.0%", "0.0%", "87.0%", "100.0%", "88.33%", "0.8836"],
        ],
        col_widths_cm=[3.2, 1.5, 1.7, 1.5, 1.5, 1.4, 1.5, 1.5, 1.6, 1.6],
        bold_last_row=True,
    )
    add_callout(
        doc,
        "4 Bất biến Thực nghiệm trên cả 3 Mô hình (20B, 27B, 120B):",
        "(1) 100.0% Thực thi hợp lệ (0.0% Crash) trên Full Pipeline; "
        "(2) 0.0% lỗi Đảo chiều (Reversed) ở RQ1 trên cả 3 mô hình (riêng 20B đạt 100.0% Eq. ở Tier 2); "
        "(3) 100.0% bắt bẫy Trace Safety Guard Φ; và "
        "(4) Full Pipeline vượt vượt trội Baseline 2 trên mọi mô hình (+0.1562 F1 trên 20B, +0.3704 F1 trên Qwen 27B, "
        "+0.2064 F1 trên 120B) cũng như vượt cấu hình tắt Behavioral Deontic Compiler.",
    )

    add_heading_2(doc, "5. Minh họa Case Study Thực tế từ Nhật ký Tự sửa (Trajectories)")
    add_body(
        doc,
        "Bảng dưới đây trích trực tiếp từ các tệp nhật ký thực nghiệm (results/real_llm_trajectories.json và "
        "results/gpt_oss_20b_trajectories.json), minh họa cụ thể cách Trình biên dịch Deontic Hướng Hành vi và "
        "Thẩm định Phản thực tế sửa lỗi thực tế ở từng cơ chế:",
    )
    add_styled_table(
        doc,
        headers=["Ca / Model", "Vòng 1 (Đầu ra ban đầu)", "Cơ chế phát hiện / biên dịch", "Kết quả cuối cùng"],
        rows=[
            [
                "R15 (Art. 14(1))\ngpt-oss-20b",
                "PERMISSION_RIGHT + MANDATORY_RESPONSE (O_Sent, A_Cancelled, 14d)",
                "Deontic-Temporal Modality Compiler (Zero-Retry)",
                "Biên dịch tất định sang Precedence(O_Sent (mail and online), A_Cancelled, 14d) — khớp tuyệt đối chuẩn vàng (0 lượt sửa).",
            ],
            [
                "R05 (Art. 5(1))\ngpt-oss-120b",
                "Response(O_Create Offer, O_Sent (mail and online))",
                "Counterfactual Probe (MISSING_RESPONSE_MUTATION)",
                "Vòng 2 tự sửa thành Response(O_Created, O_Sent (mail and online)) — phân biệt đúng pha draft vs persisted.",
            ],
            [
                "R18 (Art. 5(1))\ngpt-oss-20b",
                "Existence(O_Create Offer, NumberOfTerms > 0)",
                "Counterfactual Probe (ATTRIBUTE_BOUNDARY_MUTATION)",
                "Vòng 2 tự sửa thành Precedence(O_Create Offer, O_Sent (mail and online), NumberOfTerms > 0) — khớp chuẩn vàng.",
            ],
            [
                "R03 (Art. 10(1))\ngpt-oss-20b",
                "Chain Response(O_Accepted, A_Complete) → Response / Precedence đảo chiều",
                "Behavioral DFG Adjacency + Causal Inversion Guard (17.228 ca)",
                "Chặn đứng cả lỗi không liền kề DFG lẫn lỗi đảo chiều nhân quả A_Complete → O_Accepted (100% log); Vòng 5 chuyển sang Precedence(A_Complete, O_Accepted) hợp lệ hành vi nhưng vẫn còn lỗi Wrong Activity so với A_Pending.",
            ],
        ],
        col_widths_cm=[2.6, 4.4, 4.2, 5.8],
        left_cols={0, 1, 2, 3},
    )

    # =========================================================================
    # SCIENTIFIC INTEGRITY & THREATS TO VALIDITY
    # =========================================================================
    add_heading_1(doc, "KIỂM TOÁN LIÊM CHÍNH KHOA HỌC & GIỚI HẠN NGHIÊN CỨU")
    add_bullet(
        doc,
        "Kiểm chứng Tự động & Tái lập: ",
        "Toàn bộ 57/57 unit tests trong thư mục tests/ (bao gồm bộ hồi quy test_audit_fixes_regression.py và kiểm thử "
        "5 chốt hành vi mới test_behavioral_deontic_compiler_guards_and_permission_modality) đều pass 100%. Toàn bộ kết "
        "quả đều có thể tái lập tức thì từ Disk Cache (real_llm_cache.json, vanilla_rag_real_cache.json) bằng cờ --cache-only.",
    )
    add_bullet(
        doc,
        "Đảm bảo Không lộ Đáp án (Zero Leakage Audit): ",
        "0/30 mô tả quy tắc chứa tên hoạt động BPIC 2017 hoặc nhãn bẫy; 0/26 mô tả hoạt động trong process_schema.json "
        "chứa từ khóa pháp lý; 0 ánh xạ quy tắc viết cứng trong mã nguồn thực thi; tỷ lệ bắt bẫy luật phân hóa tự nhiên "
        "theo năng lực mô hình (15.79% ở 20B → 67.11% ở 27B → 82.89% ở 120B).",
    )
    add_bullet(
        doc,
        "Giới hạn & Đe dọa Tính hợp lệ (Threats to Validity): ",
        "(i) Ba mô tả quy tắc (R13, R19, R24) có ghi tên trường dữ liệu nghiệp vụ trong ngoặc đơn và ví dụ trung lập "
        "Article Example-2 sử dụng tên thuộc tính OfferedAmount; (ii) Baseline 1 (Vanilla RAG) nhận văn bản luật, yêu cầu "
        "chính sách và vết sự kiện thô mà không có từ điển mô tả hoạt động (đúng bản chất Vanilla RAG không qua pha khai "
        "phá siêu mô hình); (iii) Nghiên cứu hiện tập trung vào miền tín dụng tiêu dùng (EU Directive 2008/48/EC & BPIC "
        "2017) — việc mở rộng sang quy trình y tế/hành chính công và giải quyết sâu hơn lỗi Sai Hoạt động (Wrong Activity "
        "13.64%–22.73%) bằng mô hình hóa pha vòng đời hai bước là hướng phát triển tiếp theo.",
    )

    doc.save(str(OUT_PATH))
    print(f"Saved updated report successfully: {OUT_PATH}")


if __name__ == "__main__":
    build_report()
