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

# Bản đồ ngữ nghĩa ánh xạ từ khóa trong Luật EU 2008/48/EC sang các phân hệ trong BPI Challenge 2017
DOMAIN_CONCEPT_ALIGNMENT: Dict[str, Dict[str, List[str]]] = {
    "creditworthiness": {
        "keywords": ["creditworthiness", "assess", "database", "consultation", "before the conclusion"],
        "activities": [
            "A_Create Application",
            "A_Submitted",
            "W_Assess potential fraud",
            "W_Validate application",
            "A_Validating",
            "A_Accepted",
            "O_Create Offer",
        ],
        "attributes": ["CreditScore", "case:RequestedAmount", "OfferedAmount"],
    },
    "pre_contractual_offer": {
        "keywords": ["pre-contractual", "offer", "bound", "draft credit agreement", "supplied", "information"],
        "activities": [
            "A_Accepted",
            "O_Create Offer",
            "O_Created",
            "O_Sent (mail and online)",
            "O_Sent (online only)",
            "W_Call after offers",
            "O_Returned",
            "O_Accepted",
        ],
        "attributes": ["OfferedAmount", "MonthlyCost", "NumberOfTerms", "case:RequestedAmount"],
    },
    "withdrawal_right": {
        "keywords": ["withdraw", "withdrawal", "14 calendar days", "30 calendar days", "cancelled"],
        "activities": [
            "O_Sent (mail and online)",
            "O_Sent (online only)",
            "O_Returned",
            "O_Accepted",
            "A_Cancelled",
            "O_Cancelled",
        ],
        "attributes": ["Accepted", "Selected", "FirstWithdrawalAmount", "OfferedAmount"],
    },
    "rejection_notification": {
        "keywords": ["rejected", "reject", "refused", "denied", "inform the consumer immediately"],
        "activities": [
            "W_Validate application",
            "A_Validating",
            "A_Denied",
            "O_Refused",
            "O_Cancelled",
        ],
        "attributes": ["Accepted", "CreditScore", "case:RequestedAmount"],
    },
    "scope_credit_amount": {
        "keywords": ["EUR 200", "EUR 75 000", "total amount of credit", "scope"],
        "activities": [
            "A_Create Application",
            "A_Submitted",
            "A_Accepted",
            "O_Create Offer",
            "A_Complete",
        ],
        "attributes": ["case:RequestedAmount", "OfferedAmount", "case:LoanGoal", "case:ApplicationType"],
    },
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


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
            has_numeric = bool(chunk.get("has_numeric_bound", False))

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
        Lọc các phần tử Schema gợi ý (Candidate Activities & Attributes) liên quan trực tiếp
        đến nội dung điều khoản, đồng thời giữ nguyên danh mục đầy đủ của Γ để kiểm tra tĩnh.
        """
        text_lower = f"{chunk.get('article_title', '')} {chunk.get('text', '')}".lower()
        candidate_acts: List[str] = []
        candidate_attrs: List[str] = []

        for concept_meta in DOMAIN_CONCEPT_ALIGNMENT.values():
            if any(kw.lower() in text_lower for kw in concept_meta["keywords"]):
                for act in concept_meta["activities"]:
                    if act in process_schema.get("valid_activities", []) and act not in candidate_acts:
                        candidate_acts.append(act)
                for attr in concept_meta["attributes"]:
                    if attr not in candidate_attrs:
                        candidate_attrs.append(attr)

        if not candidate_acts:
            candidate_acts = list(process_schema.get("valid_activities", []))
        if not candidate_attrs:
            candidate_attrs = list(process_schema.get("case_attributes", {}).keys()) + list(
                process_schema.get("event_attributes", {}).keys()
            )

        return {
            "recommended_activities": candidate_acts,
            "recommended_attributes": candidate_attrs,
            "valid_activities": process_schema.get("valid_activities", []),
            "case_attributes": process_schema.get("case_attributes", {}),
            "event_attributes": process_schema.get("event_attributes", {}),
        }
