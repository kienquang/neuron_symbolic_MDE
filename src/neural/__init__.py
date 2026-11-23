"""
Neural + Neuro-Symbolic Synthesis module (Giai đoạn 2 & 3):
- DirectiveRAGRetriever: Truy xuất BM25 & lọc ngữ cảnh quy trình
- generate_with_mde_and_req2ltl_loop: Phân rã Req2LTL + Vòng lặp tự sửa với Process Schema Validator
- generate_with_three_layer_defense_loop: Vòng lặp tự sửa hợp nhất (Behavioral-Aware Deontic MDE + Counterfactual Probing + Declare4Py)
"""

from .rag_retriever import DirectiveRAGRetriever
from .synthesis_loop import (
    LLMClientProtocol,
    NeuroSymbolicLegalSynthesizerClient,
    build_role_tagged_message,
    generate_with_mde_and_req2ltl_loop,
    generate_with_three_layer_defense_loop,
)

__all__ = [
    "DirectiveRAGRetriever",
    "LLMClientProtocol",
    "NeuroSymbolicLegalSynthesizerClient",
    "build_role_tagged_message",
    "generate_with_mde_and_req2ltl_loop",
    "generate_with_three_layer_defense_loop",
]
