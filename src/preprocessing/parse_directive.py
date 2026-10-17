import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Union
import pymupdf as fitz  # Cài đặt: pip install pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _clean_pdf_noise(text: str) -> str:
    """Làm sạch header/footer của Official Journal, chú thích cuối trang và tiêu đề Chapter."""
    # Xóa dòng tiêu đề trang (Running headers) của Official Journal
    text = re.sub(
        r"\d{1,2}\.\d{1,2}\.\d{4}\s+EN\s+Official Journal of the European Union\s+L\s+\d+/\d+",
        "",
        text,
    )
    text = re.sub(
        r"L\s+\d+/\d+\s+EN\s+Official Journal of the European Union\s+\d{1,2}\.\d{1,2}\.\d{4}",
        "",
        text,
    )
    # Xóa footnotes ở cuối trang dạng (1) OJ L ... (kể cả phần nối tiếp sang dòng thứ 2)
    text = re.sub(
        r"\n\(\s*\d+\)\s*OJ\s+[LC]\s+\d+[^\n]*(?:\n[^\n]*OJ\s+[LC]\s+\d+[^\n]*)*",
        "\n",
        text,
    )
    # Xóa các tiêu đề CHAPTER I..VIII nằm xen giữa các Article
    text = re.sub(
        r"(?:^|\n)CHAPTER\s+[IVXLCDM]+\s*\n(?:[A-Z\s,]+\n)+",
        "\n",
        text,
    )
    # Giữ dấu gạch ngang cho các từ ghép tiếng Anh khi xuống dòng (open-end, out-of-court, pre-contractual, non-discriminatory)
    text = re.sub(
        r"\b(open|out|pre|non|cross|self|co|sub|inter|over|under|multi)[\-\ufffd]\s*\n\s*([a-zA-Z])",
        r"\1-\2",
        text,
        flags=re.IGNORECASE,
    )
    # Nối các từ bình thường bị ngắt dòng bằng dấu gạch ngang hoặc ký tự \ufffd
    text = re.sub(r"([a-zA-Z])[\-\ufffd]\s*\n\s*([a-zA-Z])", r"\1\2", text)
    return text


def parse_eu_directive(
    pdf_path: Union[str, Path],
    output_json_path: Union[str, Path]
) -> List[Dict[str, Any]]:
    """
    Phần 1A: Phân rã Văn bản Luật theo Cấu trúc Điều khoản (Articles 1–24)
    từ tệp PDF Directive 2008/48/EC sang định dạng JSON.
    """
    pdf_path = Path(pdf_path)
    output_json_path = Path(output_json_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file PDF tại: {pdf_path}")

    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text("text") + "\n"
    doc.close()

    # Chỉ lấy từ CHAPTER I (Article 1) đến hết Article 24 (bỏ phần Whereas ở đầu và thủ tục hành chính ở cuối)
    start_match = re.search(r"CHAPTER\s+I\b", full_text)
    if start_match:
        full_text = full_text[start_match.start():]

    full_text = _clean_pdf_noise(full_text)

    # Tách theo từng tiêu đề Article đứng độc lập trên dòng riêng (Article 1 -> Article 24)
    article_header_pattern = re.compile(r"(?:^|\n)[ \t]*(Article\s+(\d+))[ \t]*\n")
    all_matches = list(article_header_pattern.finditer(full_text))

    # Lọc đúng thứ tự Article 1 -> 32 (tránh bắt nhầm chữ "Article 15" hay "Article 5" bị xuống dòng trong câu)
    valid_headers = []
    expected_num = 1
    for m in all_matches:
        num = int(m.group(2))
        if num == expected_num:
            valid_headers.append(m)
            expected_num += 1

    numeric_bound_pattern = re.compile(
        r"(?:\b\d+(?:[.,]\d+)?\s*(?:calendar\s+|working\s+)?(?:days?|months?|years?|weeks?|EUR|%|percent)"
        r"|\bEUR\s*\d+(?:[\s.,]\d+)*\b"
        r"|\b(?:one|two|three|four|five|six|twelve)\s+(?:calendar\s+|working\s+)?(?:days?|months?|years?|weeks?)\b)",
        re.IGNORECASE,
    )

    chunks: List[Dict[str, Any]] = []
    for idx, match in enumerate(valid_headers):
        art_num = int(match.group(2))
        if art_num > 24:  # Bỏ qua các điều khoản hành chính cấp nhà nước (Article 25-32)
            continue

        block_start = match.end()
        if idx + 1 < len(valid_headers):
            block_end = valid_headers[idx + 1].start()
        else:
            annex_match = re.search(r"\nANNEX\s+I\b", full_text[block_start:])
            block_end = block_start + annex_match.start() if annex_match else len(full_text)

        raw_block = full_text[block_start:block_end].strip()
        lines = [line.strip() for line in raw_block.splitlines() if line.strip()]

        # Tách tiêu đề Article (có thể dài 1-3 dòng) và phần thân (art_body)
        title_lines = []
        body_start_idx = 0
        for i, line in enumerate(lines):
            if re.match(r"^1\.(?:\s+|$)", line):
                body_start_idx = i
                break
            if i > 0 and line.startswith((
                "The purpose of this Directive",
                "For the purposes of this Directive",
                "Articles 5 and 6 shall not apply",
                "Member States shall ensure",
                "Member States shall lay down",
            )):
                body_start_idx = i
                break
            title_lines.append(line)
            body_start_idx = i + 1

        art_title = " ".join(title_lines).strip()
        art_body = "\n".join(lines[body_start_idx:]).strip()

        # Tách nhỏ hơn theo từng Khoản (1., 2., 3...) trong mỗi Article
        paragraphs = re.split(r"\n(?=\d+\.(?:\s+|\n|$))", art_body)
        for p in paragraphs:
            p_clean = re.sub(r"\s+", " ", p).strip()
            if not p_clean:
                continue
            p_num_match = re.match(r"^(\d+)\.\s+", p_clean)
            p_id = f"Article {art_num}({p_num_match.group(1)})" if p_num_match else f"Article {art_num}"

            # Lưu các điều khoản có chứa từ khóa quy trình/ràng buộc (shall, must, may not, within, before, EUR, %)
            chunks.append({
                "article_id": p_id,
                "article_title": art_title,
                "text": p_clean,
                "has_numeric_bound": bool(numeric_bound_pattern.search(p_clean))
            })

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"Đã trích xuất {len(chunks)} phân đoạn điều khoản vào {output_json_path}")
    return chunks


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    default_pdf = project_root / "datasets" / "directive_2008_48_EC.pdf"
    default_output = project_root / "data" / "processed" / "directive_chunks.json"
    parse_eu_directive(default_pdf, default_output)
