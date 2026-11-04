"""
Mock Synthesizer Client for Offline Demonstration and Unit Testing.
This class is strictly used for offline CI/CD unit tests (test_phase2, test_phase3)
when live LLM API keys (Groq/OpenAI) are not configured.
All empirical benchmark experiments in the paper use RealLLMClient with live Groq models.
"""

import json
import re
from typing import Any, Dict, List, Optional


class NeuroSymbolicLegalSynthesizerClient:
    """
    Mock synthesizer client for offline testing of the 3-layer verification pipeline.
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
        if retrieved_chunk is not None and ast_dict is not None:
            art_id = retrieved_chunk.get("article_id", "")
            text = retrieved_chunk.get("text", "")
            tpl = ast_dict.get("template_name", "")
            time_max = ast_dict.get("time_max")

            if art_id in ("Article 20", "Article 22(1)", "Article 23", "Article 24(1)"):
                return {
                    "verdict": "BASELESS",
                    "diagnostic_feedback": (
                        f"{art_id} regulates macro-level Member State supervision and does not "
                        f"prescribe an operational event-level constraint on individual loan traces."
                    ),
                }

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

        if self.simulate_self_correction and not has_service_feedback:
            if article_id == "Article 8(1)":
                return json.dumps(
                    {
                        "article_id": "Article 8(1)",
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
                        "template_name": "Precedence",
                        "activation_activity": "O_Sent (mail and online)",
                        "target_activity": "O_Cancelled",
                        "time_min": 0,
                        "time_max": 14,
                        "time_unit": "d",
                    },
                    indent=2,
                )

        if self.simulate_layer3_correction and not has_service_feedback:
            if article_id == "Article 14(1)":
                return json.dumps(
                    {
                        "article_id": "Article 14(1)",
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
                return json.dumps(
                    {
                        "article_id": "Article 16(4)",
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

        knowledge_base: Dict[str, Dict[str, Any]] = {
            "Article 2(2)": {
                "article_id": "Article 2(2)",
                "template_name": "Response",
                "activation_activity": "A_Create Application",
                "target_activity": "W_Complete application",
                "activation_attr": "case:RequestedAmount",
                "activation_op": ">=",
                "activation_val": 200.0,
            },
            "Article 5(1)": {
                "article_id": "Article 5(1)",
                "template_name": "Precedence",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "O_Accepted",
                "activation_attr": "OfferedAmount",
                "activation_op": ">=",
                "activation_val": 200.0,
            },
            "Article 8(1)": {
                "article_id": "Article 8(1)",
                "template_name": "Precedence",
                "activation_activity": "W_Validate application",
                "target_activity": "O_Create Offer",
            },
            "Article 10(1)": {
                "article_id": "Article 10(1)",
                "template_name": "Precedence",
                "activation_activity": "O_Accepted",
                "target_activity": "A_Pending",
            },
            "Article 14(1)": {
                "article_id": "Article 14(1)",
                "template_name": "Response",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "O_Returned",
                "time_min": 0,
                "time_max": 14,
                "time_unit": "d",
            },
            "Article 16(4)": {
                "article_id": "Article 16(4)",
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

        default_obj = {
            "article_id": article_id,
            "template_name": "Precedence",
            "activation_activity": "W_Validate application",
            "target_activity": "O_Create Offer",
        }
        res_obj = knowledge_base.get(article_id, default_obj)
        return json.dumps(res_obj, indent=2)
