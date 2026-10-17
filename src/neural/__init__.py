"""
Neural + Neuro-Symbolic Synthesis module (Bước 2.3 & Bước 3.3):
- DirectiveRAGRetriever: Truy xuất BM25 & lọc Metamodel theo bài Optimizing RAG for OCL (arXiv:2505.13129)
- generate_with_ovas_and_req2ltl_loop: Phân rã Req2LTL + Vòng lặp tự sửa lỗi OVAS (Tầng 1 & Tầng 2)
- generate_with_three_layer_defense_loop: Vòng lặp tự sửa lỗi 3 Tầng hợp nhất (Tầng 1 + Tầng 2 + Tầng 3 Roundtrip, Vacuity & Declare4Py Conformance)
"""

from .rag_retriever import DirectiveRAGRetriever
from .synthesis_loop import (
    LLMClientProtocol,
    NeuroSymbolicLegalSynthesizerClient,
    build_role_tagged_message,
    generate_with_ovas_and_req2ltl_loop,
    generate_with_three_layer_defense_loop,
)

__all__ = [
    "DirectiveRAGRetriever",
    "LLMClientProtocol",
    "NeuroSymbolicLegalSynthesizerClient",
    "build_role_tagged_message",
    "generate_with_ovas_and_req2ltl_loop",
    "generate_with_three_layer_defense_loop",
]
