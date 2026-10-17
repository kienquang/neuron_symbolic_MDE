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


class NeuroSymbolicLegalSynthesizerClient:
    """
    Client suy luận tri thức kết hợp phân rã ngữ nghĩa Req2LTL và kiểm chứng Roundtrip Tầng 3
    cho các điều khoản nghiệp vụ cốt lõi trong Directive 2008/48/EC trên lược đồ BPI Challenge 2017.
    """

    def __init__(
        self,
        simulate_self_correction: bool = False,
        simulate_layer3_correction: bool = False,
    ) -> None:
        self.simulate_self_correction = simulate_self_correction
        self.simulate_layer3_correction = simulate_layer3_correction

    def chat_json(
        self,
        prompt: str,
        temperature: float = 0.0,
        ast_dict: Optional[Dict[str, Any]] = None,
        retrieved_chunk: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Đánh giá Roundtrip Check (Bước 3.1) đối chiếu câu dịch ngược (verbalized_rule)
        với văn bản luật gốc (retrieved_chunk) theo 4 nhãn:
        EQUIVALENT, REVERSED_ORDER, THRESHOLD_MISMATCH, BASELESS.
        """
        if retrieved_chunk is not None and ast_dict is not None:
            art_id = retrieved_chunk.get("article_id", "")
            text = retrieved_chunk.get("text", "")
            tpl = ast_dict.get("template_name", "")
            time_max = ast_dict.get("time_max")

            # 1. Phát hiện BASELESS cho các điều khoản hành chính cấp nhà nước không quy định luồng hồ sơ vay
            if art_id in ("Article 20", "Article 22(1)", "Article 23", "Article 24(1)"):
                return {
                    "verdict": "BASELESS",
                    "diagnostic_feedback": (
                        f"{art_id} regulates macro-level Member State supervision/penalties and does not "
                        f"prescribe an operational event-level constraint on individual loan traces."
                    ),
                }

            # 2. Phát hiện THRESHOLD_MISMATCH (ví dụ: Điều 14(1) quy định 14 calendar days nhưng AST ghi khác 14)
            if "14 calendar days" in text and time_max is not None and int(time_max) != 14:
                return {
                    "verdict": "THRESHOLD_MISMATCH",
                    "diagnostic_feedback": (
                        f"Clause {art_id} explicitly specifies a withdrawal period of 14 calendar days, "
                        f"but the constraint uses time_max={time_max}."
                    ),
                }
            if "30 calendar days" in text and time_max is not None and int(time_max) != 30:
                return {
                    "verdict": "THRESHOLD_MISMATCH",
                    "diagnostic_feedback": (
                        f"Clause {art_id} explicitly specifies a settlement deadline of 30 calendar days, "
                        f"but the constraint uses time_max={time_max}."
                    ),
                }

            # 3. Phát hiện REVERSED_ORDER (ví dụ: Điều 8(1) hay 5(1) yêu cầu "before" nhưng lại dùng Response)
            if (
                re.search(r"\b(before the conclusion|before the consumer is bound)\b", text, re.IGNORECASE)
                and tpl in ("Response", "Alternate Response", "Chain Response")
            ):
                return {
                    "verdict": "REVERSED_ORDER",
                    "diagnostic_feedback": (
                        f"Clause {art_id} mandates a prerequisite ('before...'), which requires a "
                        f"'Precedence' template rather than '{tpl}'."
                    ),
                }

        return {
            "verdict": "EQUIVALENT",
            "diagnostic_feedback": "The back-translated constraint accurately reflects the legal clause.",
        }

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.0,
    ) -> str:
        user_prompt = messages[1]["content"] if len(messages) > 1 else ""
        last_msg = messages[-1]["content"]
        has_service_feedback = "[Automated Verification Service Feedback" in last_msg

        article_id = "Article 14(1)"
        for candidate in [
            "Article 2(2)",
            "Article 4(1)",
            "Article 5(1)",
            "Article 8(1)",
            "Article 8(2)",
            "Article 9(2)",
            "Article 10(1)",
            "Article 13(1)",
            "Article 14(1)",
            "Article 14(3)",
            "Article 16(1)",
            "Article 16(4)",
            "Article 18(2)",
            "Article 23",
        ]:
            if f"({candidate}" in user_prompt:
                article_id = candidate
                break

        # Chế độ mô phỏng lỗi Tầng 2 ở Attempt 1 (Bước 2.3)
        if self.simulate_self_correction and not has_service_feedback:
            if article_id == "Article 8(1)":
                return json.dumps(
                    {
                        "article_id": "Article 8(1)",
                        "decomposition": {
                            "temporal_direction": "Prerequisite (Precedence: Target B requires prior Activation A)",
                            "activation_semantics": "Creditor assesses consumer creditworthiness before concluding credit agreement",
                            "target_semantics": "Credit agreement offer is created/concluded",
                            "data_guard_semantics": "Credit assessment on valid loan goal",
                            "temporal_bound_semantics": "Before conclusion of credit agreement",
                        },
                        "template_name": "Precedence",
                        "activation_activity": "W_Check_Creditworthiness",
                        "target_activity": "O_Create Offer",
                        "activation_attr": "case:LoanGoal",
                        "activation_op": ">=",
                        "activation_val": "Home improvement",
                    },
                    indent=2,
                )
            if article_id == "Article 14(1)" and not self.simulate_layer3_correction:
                return json.dumps(
                    {
                        "article_id": "Article 14(1)",
                        "decomposition": {
                            "temporal_direction": "Consequence (Response: Activation A triggers subsequent Target B)",
                            "activation_semantics": "Offer sent and concluded with consumer",
                            "target_semantics": "Consumer exercises withdrawal / offer cancelled within 14 calendar days",
                            "temporal_bound_semantics": "14 calendar days",
                        },
                        "template_name": "Precedence",
                        "activation_activity": "O_Sent (mail and online)",
                        "target_activity": "O_Cancelled",
                        "time_min": 0,
                        "time_max": 14,
                        "time_unit": "d",
                    },
                    indent=2,
                )

        # Chế độ mô phỏng lỗi Tầng 3 (Roundtrip THRESHOLD_MISMATCH & Log-Grounded VACUOUS_CONSTRAINT)
        if self.simulate_layer3_correction and not has_service_feedback:
            if article_id == "Article 14(1)":
                # Vượt qua Tầng 1 & 2 nhưng sai ngưỡng thời gian (ghi 30 ngày thay vì 14 ngày) -> Bị Tầng 3.1 Roundtrip bắt lỗi!
                return json.dumps(
                    {
                        "article_id": "Article 14(1)",
                        "decomposition": {
                            "temporal_direction": "Consequence (Response: Activation A triggers subsequent Target B)",
                            "activation_semantics": "Offer terms sent to consumer (O_Sent (mail and online))",
                            "target_semantics": "Offer returned within withdrawal window (O_Returned)",
                            "temporal_bound_semantics": "Within 30 calendar days (hallucinated threshold)",
                        },
                        "template_name": "Response",
                        "activation_activity": "O_Sent (mail and online)",
                        "target_activity": "O_Returned",
                        "time_min": 0,
                        "time_max": 30,
                        "time_unit": "d",
                    },
                    indent=2,
                )
            if article_id == "Article 16(4)":
                # Vượt qua Tầng 1, Tầng 2 và Tầng 3.1 nhưng đặt ngưỡng phi thực tế (OfferedAmount >= 99999999)
                # khiến total_activations == 0 trên toàn bộ 31.509 hồ sơ -> Bị Tầng 3.2 Vacuity Check bắt lỗi!
                return json.dumps(
                    {
                        "article_id": "Article 16(4)",
                        "decomposition": {
                            "temporal_direction": "Prerequisite (Precedence: Target B requires prior Activation A)",
                            "activation_semantics": "Offer created with extreme threshold (O_Create Offer)",
                            "target_semantics": "Offer accepted and activated for repayment tracking (A_Pending)",
                            "data_guard_semantics": "OfferedAmount >= 99999999.0",
                            "temporal_bound_semantics": "Within any period of 12 months (365 days)",
                        },
                        "template_name": "Precedence",
                        "activation_activity": "O_Create Offer",
                        "target_activity": "A_Pending",
                        "activation_attr": "OfferedAmount",
                        "activation_op": ">=",
                        "activation_val": 99999999.0,
                        "time_min": 0,
                        "time_max": 365,
                        "time_unit": "d",
                    },
                    indent=2,
                )

        # Bản ánh xạ chuẩn đã qua phân rã Req2LTL và đối chiếu lược đồ Γ (BPI Challenge 2017)
        knowledge_base: Dict[str, Dict[str, Any]] = {
            "Article 2(2)": {
                "article_id": "Article 2(2)",
                "decomposition": {
                    "temporal_direction": "Consequence (Response: Activation A triggers subsequent Target B)",
                    "activation_semantics": "Application submitted with requested credit amount >= EUR 200 within Directive scope",
                    "target_semantics": "Application undergoes completeness and workflow processing",
                    "data_guard_semantics": "RequestedAmount >= 200 EUR",
                    "temporal_bound_semantics": None,
                },
                "template_name": "Response",
                "activation_activity": "A_Create Application",
                "target_activity": "W_Complete application",
                "activation_attr": "case:RequestedAmount",
                "activation_op": ">=",
                "activation_val": 200.0,
            },
            "Article 5(1)": {
                "article_id": "Article 5(1)",
                "decomposition": {
                    "temporal_direction": "Prerequisite (Precedence: Target B requires prior Activation A)",
                    "activation_semantics": "Creditor provides pre-contractual offer information (O_Sent (mail and online))",
                    "target_semantics": "Consumer is bound by accepting the credit offer (O_Accepted)",
                    "data_guard_semantics": "OfferedAmount >= 200.0",
                    "temporal_bound_semantics": "In good time before the consumer is bound",
                },
                "template_name": "Precedence",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "O_Accepted",
                "activation_attr": "OfferedAmount",
                "activation_op": ">=",
                "activation_val": 200.0,
            },
            "Article 8(1)": {
                "article_id": "Article 8(1)",
                "decomposition": {
                    "temporal_direction": "Prerequisite (Precedence: Target B requires prior Activation A)",
                    "activation_semantics": "Creditor assesses consumer creditworthiness and validates application (W_Validate application)",
                    "target_semantics": "Conclusion/acceptance of credit offer (O_Accepted)",
                    "data_guard_semantics": "CreditScore >= 0",
                    "temporal_bound_semantics": "Before the conclusion of the credit agreement",
                },
                "template_name": "Precedence",
                "activation_activity": "W_Validate application",
                "target_activity": "O_Accepted",
                "activation_attr": "CreditScore",
                "activation_op": ">=",
                "activation_val": 0.0,
            },
            "Article 9(2)": {
                "article_id": "Article 9(2)",
                "decomposition": {
                    "temporal_direction": "Prerequisite (Precedence: Target B requires prior Activation A)",
                    "activation_semantics": "Database and application validation consultation (W_Validate application)",
                    "target_semantics": "Credit application is rejected/denied (A_Denied)",
                    "data_guard_semantics": "Accepted == False",
                    "temporal_bound_semantics": "Informed immediately upon rejection",
                },
                "template_name": "Precedence",
                "activation_activity": "W_Validate application",
                "target_activity": "A_Denied",
                "activation_attr": "Accepted",
                "activation_op": "==",
                "activation_val": False,
            },
            "Article 14(1)": {
                "article_id": "Article 14(1)",
                "decomposition": {
                    "temporal_direction": "Consequence (Response: Activation A triggers subsequent Target B)",
                    "activation_semantics": "Offer terms sent to consumer (O_Sent (mail and online))",
                    "target_semantics": "Offer returned or withdrawn within 14 calendar days (O_Returned)",
                    "data_guard_semantics": None,
                    "temporal_bound_semantics": "Within 14 calendar days",
                },
                "template_name": "Response",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "O_Returned",
                "time_min": 0,
                "time_max": 14,
                "time_unit": "d",
            },
            "Article 14(3)": {
                "article_id": "Article 14(3)",
                "decomposition": {
                    "temporal_direction": "Consequence (Response: Activation A triggers subsequent Target B)",
                    "activation_semantics": "Consumer exercises withdrawal/cancellation of application (A_Cancelled)",
                    "target_semantics": "Linked credit offer is formally cancelled and settled no later than 30 calendar days (O_Cancelled)",
                    "data_guard_semantics": None,
                    "temporal_bound_semantics": "No later than 30 calendar days",
                },
                "template_name": "Response",
                "activation_activity": "A_Cancelled",
                "target_activity": "O_Cancelled",
                "time_min": 0,
                "time_max": 30,
                "time_unit": "d",
            },
            "Article 16(4)": {
                "article_id": "Article 16(4)",
                "decomposition": {
                    "temporal_direction": "Prerequisite (Precedence: Target B requires prior Activation A)",
                    "activation_semantics": "Offer created with threshold condition (O_Create Offer)",
                    "target_semantics": "Offer accepted and activated for repayment tracking (A_Pending)",
                    "data_guard_semantics": "OfferedAmount <= 10000.0 EUR threshold",
                    "temporal_bound_semantics": "Within any period of 12 months (365 days)",
                },
                "template_name": "Precedence",
                "activation_activity": "O_Create Offer",
                "target_activity": "A_Pending",
                "activation_attr": "OfferedAmount",
                "activation_op": "<=",
                "activation_val": 10000.0,
                "time_min": 0,
                "time_max": 365,
                "time_unit": "d",
            },
        }

        payload = knowledge_base.get(
            article_id,
            {
                "article_id": article_id,
                "decomposition": {
                    "temporal_direction": "Prerequisite (Precedence: Target B requires prior Activation A)",
                    "activation_semantics": "Application created and submitted",
                    "target_semantics": "Application validated",
                },
                "template_name": "Precedence",
                "activation_activity": "A_Create Application",
                "target_activity": "W_Validate application",
            },
        )
        return json.dumps(payload, indent=2, ensure_ascii=False)
