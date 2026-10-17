"""
Neural + Neuro-Symbolic Synthesis module (Bước 2.3):
- DirectiveRAGRetriever: Truy xuất BM25 & lọc Metamodel theo bài Optimizing RAG for OCL (arXiv:2505.13129)
- generate_with_ovas_and_req2ltl_loop: Phân rã Req2LTL + Vòng lặp tự sửa lỗi OVAS + Role-tagged messages (arXiv:2510.07161)
"""

from .rag_retriever import DirectiveRAGRetriever
from .synthesis_loop import (
    LLMClientProtocol,
    NeuroSymbolicLegalSynthesizerClient,
    build_role_tagged_message,
    generate_with_ovas_and_req2ltl_loop,
)

__all__ = [
    "DirectiveRAGRetriever",
    "LLMClientProtocol",
    "NeuroSymbolicLegalSynthesizerClient",
    "build_role_tagged_message",
    "generate_with_ovas_and_req2ltl_loop",
]
