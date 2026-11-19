"""
Bước 2.3 (Phần đầu): Truy xuất RAG & Lọc Lược đồ Quy trình (Metamodel Pruning)
Tham khảo bài báo "Optimizing RAG for OCL" (arXiv:2505.13129):
- Sử dụng BM25 kết hợp trọng số từ khóa nghĩa vụ pháp lý (deontic keywords: shall, must, before, within, EUR, %)
  để truy xuất top-k điều khoản trong directive_chunks.json.
- Lọc tập con các hoạt động (activities) và thuộc tính (attributes) liên quan nhất từ process_schema.json.
"""

import re
from typing import Any, Dict, List, Optional
from rank_bm25 import BM25Okapi

DEONTIC_PROCESS_PATTERNS = re.compile(
    r"\b(shall|must|may not|before|within|immediately|without delay|calendar days|creditworthiness|withdraw|rejected|EUR|%)\b",
    re.IGNORECASE,
)

# Hand-crafted domain alignment hints removed to prevent benchmark/rule leakage;
# schema relevance is derived purely from neutral process schema symbols and descriptions.
DOMAIN_CONCEPT_ALIGNMENT: Dict[str, Dict[str, List[str]]] = {}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _split_identifier_tokens(name: str) -> List[str]:
    cleaned = re.sub(r"^(?:[AOW]_|case:)", "", name)
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    return [t for t in _tokenize(spaced) if len(t) > 2]


class DirectiveRAGRetriever:
    """
    Bộ truy xuất BM25 + Lọc lược đồ Metamodel theo bài báo Optimizing RAG for OCL (arXiv:2505.13129).
    """

    def __init__(self, directive_chunks: List[Dict[str, Any]]) -> None:
        self.chunks = directive_chunks
        corpus_tokens = [
            _tokenize(f"{c.get('article_id', '')} {c.get('article_title', '')} {c.get('text', '')}")
            for c in self.chunks
        ]
        self.bm25 = BM25Okapi(corpus_tokens)

    def retrieve_top_k(
        self,
        query: str,
        top_k: int = 5,
        require_deontic_or_numeric: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Truy xuất top-k điều khoản pháp lý phù hợp nhất với truy vấn nghiệp vụ.
        """
        query_tokens = _tokenize(query)
        scores = self.bm25.get_scores(query_tokens)

        scored_chunks = []
        for idx, chunk in enumerate(self.chunks):
            text = chunk.get("text", "")
            has_deontic = bool(DEONTIC_PROCESS_PATTERNS.search(text))
            # Tự động phát hiện ràng buộc số học từ văn bản nếu chunk chưa được gán nhãn trước
            has_numeric = bool(chunk.get("has_numeric_bound", False)) or bool(
                re.search(
                    r"\b(\d+(?:[.,]\d+)?)\s*(calendar\s+days|working\s+days|days|months|years|EUR|euro|euros|%)\b",
                    text,
                    re.IGNORECASE,
                )
            )

            if require_deontic_or_numeric and not (has_deontic or has_numeric):
                continue

            # Tăng trọng số cho các điều khoản có ràng buộc định lượng hoặc từ khóa quy trình
            boost = (1.5 if has_numeric else 0.0) + (1.0 if has_deontic else 0.0)
            scored_chunks.append((float(scores[idx]) + boost, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [
            {**item[1], "rag_score": round(item[0], 4)}
            for item in scored_chunks[:top_k]
        ]

    @staticmethod
    def filter_relevant_schema(
        chunk: Dict[str, Any],
        process_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Rank candidate schema activities and attributes using purely lexical overlap
        against the neutral process schema descriptions and identifier tokens, while
        retaining full valid schema metadata for closed-world type checking.
        """
        text_lower = f"{chunk.get('article_title', '')} {chunk.get('text', '')}".lower()
        clause_tokens = {t for t in _tokenize(text_lower) if len(t) > 2}

        valid_schema_acts = list(process_schema.get("valid_activities", []))
        act_descs = process_schema.get("activity_descriptions", {})
        act_scores = []
        for act in valid_schema_acts:
            desc_tokens = set(_split_identifier_tokens(act)) | {
                t for t in _tokenize(act_descs.get(act, "")) if len(t) > 3
            }
            overlap = len(clause_tokens & desc_tokens)
            if overlap > 0:
                act_scores.append((overlap, act))
        act_scores.sort(key=lambda x: (-x[0], x[1]))
        candidate_acts = [act for _, act in act_scores] if act_scores else list(valid_schema_acts)

        valid_schema_attrs = (
            list(process_schema.get("case_attributes", {}).keys())
            + list(process_schema.get("event_attributes", {}).keys())
        )
        attr_scores = []
        for attr in valid_schema_attrs:
            attr_tokens = set(_split_identifier_tokens(attr))
            overlap = len(clause_tokens & attr_tokens)
            if overlap > 0:
                attr_scores.append((overlap, attr))
        attr_scores.sort(key=lambda x: (-x[0], x[1]))
        candidate_attrs = [attr for _, attr in attr_scores] if attr_scores else valid_schema_attrs

        return {
            "recommended_activities": candidate_acts,
            "recommended_attributes": candidate_attrs,
            "valid_activities": process_schema.get("valid_activities", []),
            "case_attributes": process_schema.get("case_attributes", {}),
            "event_attributes": process_schema.get("event_attributes", {}),
        }
