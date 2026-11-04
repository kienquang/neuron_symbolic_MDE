"""
Bước 2.3 & Bước 3.3: Phân rã Ngữ nghĩa (Req2LTL) & Vòng lặp Tự sửa lỗi 3 Tầng (Three-Layer Defense Loop)
Tích hợp:
1. Req2LTL (ASE 2025, arXiv:2512.17334): Prompt phân rã câu luật thành Tiền đề (Activation) -
   Hệ quả (Target) - Chiều thời gian (Precedence vs Response) trước khi ánh xạ vào AST.
2. OVAS (OCL2026 - Hình 1): Vòng lặp Three-Layer Defense (Layer 1 Syntax -> Layer 2 Static Type Γ ->
   Layer 3 Roundtrip, Vacuity & Declare4Py Conformance Verification) với Max_Retry = 5, temperature = 0.0.
3. arXiv:2510.07161 (Janus): Cấu trúc phân vai thông điệp Role = {'domain-expert', 'assistant', 'service'}.
"""

import json
import re
from typing import Any, Dict, List, Optional, Protocol, Tuple
import pandas as pd
from src.mde.constraint_ast import DeclareConstraintAST
from src.mde.typing_environment import check_layer1_and_layer2
from src.neural.rag_retriever import DirectiveRAGRetriever
from src.symbolic.declare4py_verifier import Declare4Py, run_layer3_declare4py_verifier
from src.symbolic.verbalizer_roundtrip import check_roundtrip_fidelity, verbalize_declare_ast


class LLMClientProtocol(Protocol):
    """Giao diện chuẩn cho LLM Client (hỗ trợ OpenAI/Gemini/Ollama hoặc Rule-Guided Client)."""

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
    ) -> str:
        ...


def build_role_tagged_message(
    llm_role: str,
    domain_role: str,
    content: str,
) -> Dict[str, str]:
    """
    Đóng gói thông điệp theo kiến trúc phân vai của bài arXiv:2510.07161:
    domain_role ∈ {'domain-expert', 'assistant', 'service'}
    """
    return {
        "role": llm_role,
        "domain_role": domain_role,
        "content": f"[Role: {domain_role}]\n{content}",
    }


def generate_with_ovas_and_req2ltl_loop(
    retrieved_chunk: Dict[str, Any],
    process_schema: Dict[str, Any],
    llm_client: LLMClientProtocol,
    max_retry: int = 5,
    record_trace: bool = False,
) -> Any:
    """
    Vòng lặp Bước 2 (Tầng 1 + Tầng 2): Kết hợp cơ chế Role-tagged Message của arXiv:2510.07161,
    Semantic Decomposition của Req2LTL và Static Checkers của repo OVAS.
    """
    filtered_ctx = DirectiveRAGRetriever.filter_relevant_schema(
        retrieved_chunk, process_schema
    )
    all_attrs_summary = {
        **{k: v["type"] for k, v in process_schema.get("case_attributes", {}).items()},
        **{k: v["type"] for k, v in process_schema.get("event_attributes", {}).items()},
    }

    messages: List[Dict[str, str]] = [
        build_role_tagged_message(
            llm_role="system",
            domain_role="domain-expert",
            content=(
                "You are a formal verification assistant translating EU legal clauses into Declare4Py constraints.\n"
                "Step 1 (Req2LTL Decomposition): Identify whether the rule mandates a Prerequisite "
                "(Precedence: Target B requires prior Activation A) or a Consequence "
                "(Response: Activation A triggers subsequent Target B).\n"
                "Step 2 (OVAS AST Instantiation): Output strictly valid JSON matching DeclareConstraintAST."
            ),
        ),
        build_role_tagged_message(
            llm_role="user",
            domain_role="domain-expert",
            content=(
                f"Legal Clause ({retrieved_chunk['article_id']} - {retrieved_chunk.get('article_title', '')}): "
                f"{retrieved_chunk['text']}\n"
                f"Recommended Process Activities (RAG-filtered): {filtered_ctx['recommended_activities']}\n"
                f"All Valid Process Activities (Γ): {process_schema['valid_activities']}\n"
                f"Valid Attributes & Types (Γ): {json.dumps(all_attrs_summary, ensure_ascii=False)}"
            ),
        ),
    ]

    synthesis_trace: List[Dict[str, Any]] = []

    for attempt in range(1, max_retry + 1):
        raw_response = llm_client.chat(messages=messages, temperature=0.0)

        is_valid, feedback_or_ast = check_layer1_and_layer2(
            raw_response, process_schema, retrieved_chunk
        )
        synthesis_trace.append(
            {
                "attempt": attempt,
                "raw_response": raw_response,
                "is_valid": is_valid,
                "feedback": None if is_valid else str(feedback_or_ast),
            }
        )

        if is_valid:
            assert isinstance(feedback_or_ast, DeclareConstraintAST)
            if record_trace:
                return feedback_or_ast, synthesis_trace
            return feedback_or_ast

        messages.append(
            build_role_tagged_message(
                llm_role="assistant",
                domain_role="assistant",
                content=raw_response,
            )
        )
        messages.append(
            build_role_tagged_message(
                llm_role="user",
                domain_role="service",
                content=(
                    f"[Automated Verification Service Feedback - Attempt {attempt}/{max_retry}]:\n"
                    f"{feedback_or_ast}\n"
                    f"Please repair the JSON AST strictly adhering to the Process Schema Γ."
                ),
            )
        )

    raise RuntimeError(
        f"Failed to synthesize a verified DeclareConstraintAST for {retrieved_chunk.get('article_id')} "
        f"after {max_retry} attempts. Last feedback:\n{synthesis_trace[-1]['feedback']}"
    )


def generate_with_three_layer_defense_loop(
    retrieved_chunk: Dict[str, Any],
    process_schema: Dict[str, Any],
    d4py_engine: Declare4Py,
    log_df: pd.DataFrame,
    llm_client: Any,
    max_retry: int = 5,
) -> Dict[str, Any]:
    """
    Vòng lặp Tự sửa 3 Tầng hợp nhất (Hình 1 của bài OCL2026 - OVAS):
      - Tầng 1: JSON Schema & Closed Enumeration (constraint_ast.py)
      - Tầng 2: Typing Environment Γ & δ(C, p) Type Conformance (typing_environment.py)
      - Tầng 3.1: Deterministic Verbalization & Roundtrip Check (verbalizer_roundtrip.py)
      - Tầng 3.2: Declare4Py Conformance Check, Log-Grounded Vacuity Check & Counterexample Snapshot (declare4py_verifier.py)
    """
    filtered_ctx = DirectiveRAGRetriever.filter_relevant_schema(
        retrieved_chunk, process_schema
    )
    all_attrs_summary = {
        **{k: v["type"] for k, v in process_schema.get("case_attributes", {}).items()},
        **{k: v["type"] for k, v in process_schema.get("event_attributes", {}).items()},
    }

    messages: List[Dict[str, str]] = [
        build_role_tagged_message(
            llm_role="system",
            domain_role="domain-expert",
            content=(
                "You are a formal verification assistant translating EU legal clauses into Declare4Py constraints.\n"
                "Step 1 (Req2LTL Decomposition): Identify whether the rule mandates a Prerequisite "
                "(Precedence: Target B requires prior Activation A) or a Consequence "
                "(Response: Activation A triggers subsequent Target B).\n"
                "Step 2 (OVAS AST Instantiation): Output strictly valid JSON matching DeclareConstraintAST."
            ),
        ),
        build_role_tagged_message(
            llm_role="user",
            domain_role="domain-expert",
            content=(
                f"Legal Clause ({retrieved_chunk['article_id']} - {retrieved_chunk.get('article_title', '')}): "
                f"{retrieved_chunk['text']}\n"
                f"Recommended Process Activities (RAG-filtered): {filtered_ctx['recommended_activities']}\n"
                f"All Valid Process Activities (Γ): {process_schema['valid_activities']}\n"
                f"Valid Attributes & Types (Γ): {json.dumps(all_attrs_summary, ensure_ascii=False)}"
            ),
        ),
    ]

    verification_trace: List[Dict[str, Any]] = []

    for attempt in range(1, max_retry + 1):
        raw_response = llm_client.chat(messages=messages, temperature=0.0)

        # --- TẦNG 1 & TẦNG 2: Kiểm tra cú pháp JSON Schema & Kiểu dữ liệu tĩnh trên Γ ---
        is_l12_valid, l12_res = check_layer1_and_layer2(
            raw_response, process_schema, retrieved_chunk
        )
        if not is_l12_valid:
            feedback_msg = str(l12_res)
            verification_trace.append(
                {
                    "attempt": attempt,
                    "failed_layer": "Layer 1/2 (Syntax & Static Typing Γ)",
                    "is_valid": False,
                    "feedback": feedback_msg,
                }
            )
            messages.append(build_role_tagged_message("assistant", "assistant", raw_response))
            messages.append(
                build_role_tagged_message(
                    "user",
                    "service",
                    f"[Automated Verification Service Feedback - Attempt {attempt}/{max_retry}]:\n"
                    f"{feedback_msg}\nPlease repair the JSON AST strictly adhering to the Process Schema Γ.",
                )
            )
            continue

        ast_obj = l12_res
        assert isinstance(ast_obj, DeclareConstraintAST)
        ast_dict = ast_obj.model_dump()

        # --- TẦNG 3.1: Kiểm tra Dịch ngược & Đối chiếu Ngữ nghĩa (Roundtrip Check) ---
        rt_ok, rt_feedback = check_roundtrip_fidelity(ast_dict, retrieved_chunk, llm_client)
        if not rt_ok:
            verification_trace.append(
                {
                    "attempt": attempt,
                    "failed_layer": "Layer 3.1 (Roundtrip Semantic Fidelity)",
                    "is_valid": False,
                    "feedback": rt_feedback,
                }
            )
            # Nếu BASELESS (Điều khoản luật không chứa ràng buộc quy trình): Dừng vòng lặp ngay
            if "BASELESS" in rt_feedback:
                return {
                    "status": "BASELESS",
                    "article_id": retrieved_chunk["article_id"],
                    "article_title": retrieved_chunk.get("article_title", ""),
                    "attempts_used": attempt,
                    "diagnostic_feedback": rt_feedback,
                    "verification_trace": verification_trace,
                }

            # Nếu REVERSED_ORDER hoặc THRESHOLD_MISMATCH -> Gửi Error Feedback về cho LLM sửa AST
            messages.append(build_role_tagged_message("assistant", "assistant", raw_response))
            messages.append(
                build_role_tagged_message(
                    "user",
                    "service",
                    f"[Automated Verification Service Feedback - Attempt {attempt}/{max_retry}]:\n"
                    f"{rt_feedback}\nPlease repair the temporal order or numeric threshold in the JSON AST.",
                )
            )
            continue

        # --- TẦNG 3.2 & 3.3: Kiểm tra Declare4Py Conformance, Vacuity Check & Trích xuất Counterexample ---
        decl_line = ast_obj.to_declare4py_line()
        l3_ok, l3_report = run_layer3_declare4py_verifier(
            d4py_engine=d4py_engine,
            log_df=log_df,
            ast_obj=ast_obj,
            decl_line=decl_line,
        )
        if not l3_ok:
            vacuity_feedback = str(l3_report.get("feedback", "Vacuous constraint"))
            verification_trace.append(
                {
                    "attempt": attempt,
                    "failed_layer": "Layer 3.2 (Log-Grounded Vacuity Check)",
                    "is_valid": False,
                    "feedback": vacuity_feedback,
                }
            )
            messages.append(build_role_tagged_message("assistant", "assistant", raw_response))
            messages.append(
                build_role_tagged_message(
                    "user",
                    "service",
                    f"[Automated Verification Service Feedback - Attempt {attempt}/{max_retry}]:\n"
                    f"{vacuity_feedback}\nPlease select an activation activity or attribute threshold present in BPIC 2017.",
                )
            )
            continue

        # Đã vượt qua cả 3 Tầng kiểm chứng!
        verbalized = verbalize_declare_ast(ast_dict)
        verification_trace.append(
            {
                "attempt": attempt,
                "failed_layer": None,
                "is_valid": True,
                "feedback": "Passed Layer 1, Layer 2, Layer 3.1 (Roundtrip), and Layer 3.2 (Declare4Py Non-Vacuous Conformance).",
            }
        )
        return {
            "status": "VERIFIED",
            "article_id": retrieved_chunk["article_id"],
            "article_title": retrieved_chunk.get("article_title", ""),
            "attempts_used": attempt,
            "verbalized_constraint": verbalized,
            "ast": ast_dict,
            "declare4py": ast_obj.to_declare4py_dict(),
            "conformance_report": l3_report,
            "verification_trace": verification_trace,
        }

    return {
        "status": "FAILED_MAX_RETRY",
        "article_id": retrieved_chunk["article_id"],
        "article_title": retrieved_chunk.get("article_title", ""),
        "attempts_used": max_retry,
        "diagnostic_feedback": verification_trace[-1]["feedback"] if verification_trace else "Max retries exceeded",
        "verification_trace": verification_trace,
    }


# =========================================================================
# Mock Synthesizer Client for Offline Unit Testing
# All empirical evaluations in the paper use RealLLMClient with live Groq models.
# The mock client below is imported from tests/mocks/ strictly for offline test passes.
# =========================================================================
from tests.mocks.mock_synthesizer import NeuroSymbolicLegalSynthesizerClient

__all__ = [
    "LLMClientProtocol",
    "build_role_tagged_message",
    "generate_with_ovas_and_req2ltl_loop",
    "generate_with_three_layer_defense",
    "NeuroSymbolicLegalSynthesizerClient",
]
