import json
import unittest
from pathlib import Path
from src.preprocessing.parse_directive import parse_eu_directive


class TestParseDirective(unittest.TestCase):
    def setUp(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.pdf_path = self.project_root / "datasets" / "directive_2008_48_EC.pdf"
        self.output_path = self.project_root / "data" / "processed" / "directive_chunks.json"

    def test_parse_articles_1_to_24(self) -> None:
        chunks = parse_eu_directive(self.pdf_path, self.output_path)
        self.assertTrue(self.output_path.exists())
        self.assertGreater(len(chunks), 50)

        # Kiểm tra chỉ có Article 1 -> 24
        article_nums = set()
        for chunk in chunks:
            art_id = chunk["article_id"]
            self.assertTrue(art_id.startswith("Article "))
            num_str = art_id.replace("Article ", "").split("(")[0]
            article_nums.add(int(num_str))

        self.assertEqual(article_nums, set(range(1, 25)))

        # Kiểm tra một số điều khoản quan trọng có ràng buộc thời gian/số lượng
        chunk_map = {c["article_id"]: c for c in chunks}
        self.assertIn("Article 14(1)", chunk_map)
        self.assertTrue(chunk_map["Article 14(1)"]["has_numeric_bound"])  # 14 calendar days
        self.assertIn("Article 14(3)", chunk_map)
        self.assertTrue(chunk_map["Article 14(3)"]["has_numeric_bound"])  # 30 calendar days


if __name__ == "__main__":
    unittest.main()
