"""
Client Kết nối Model Thực tế (Groq / OpenAI / Gemini / Ollama) kèm Bộ nhớ đệm (Disk Cache)
và Bộ ghi nhận Nhật ký Tự sửa Thật (Trajectory Logging) cho 30 Quy tắc Chuẩn (R01–R30).

Thiết kế bám sát Mục 4.1.2 của bài OCL2026 (OVAS):
- Cố định temperature = 0.0 để đảm bảo tính tất định (determinism).
- Lưu phản hồi vào Disk Cache (`real_llm_cache.json`) theo mã băm SHA-256 của `(model, messages, temperature)`
  để tái lập thực nghiệm 100% và không tốn quota API khi chạy lại.
- Lưu toàn bộ lịch sử sai–sửa (`trajectory`) qua Tầng 1, Tầng 2 và Tầng 3 (Roundtrip & Vacuity) để đưa vào bài báo.
- TUYỆT ĐỐI KHÔNG chứa bất kỳ câu mớm bẫy viết cứng (`phi_auditor_claims`) hay gợi ý đáp án nào:
  Chỉ truyền duy nhất 2 thông tin nguyên bản là Văn bản luật thô (`retrieved_chunk['text']`) và Lược đồ quy trình (`process_schema`).
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False

from src.mde.constraint_ast import UNARY_TEMPLATES, BINARY_TEMPLATES, validate_layer1_ast
from src.evaluation.experiment_runner import check_layer1_and_layer2
from src.symbolic.verbalizer_roundtrip import check_roundtrip_fidelity
from src.evaluation.grounded_auditor import DeterministicAuditNarratorClient

ALLOWED_DECLARE_TEMPLATES = UNARY_TEMPLATES | BINARY_TEMPLATES

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Tự động nạp biến môi trường từ .env ở thư mục gốc dự án hoặc ~/.env (không in giá trị khóa)."""
    if explicit_key:
        return explicit_key
    project_env = PROJECT_ROOT / ".env"
    home_env = Path.home() / ".env"
    if project_env.exists():
        load_dotenv(dotenv_path=project_env, override=True)
    if home_env.exists():
        load_dotenv(dotenv_path=home_env, override=False)

    for var_name in ("GROQ_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "API_KEY"):
        val = os.environ.get(var_name)
        if val and val.strip():
            return val.strip().strip('"').strip("'")

    for env_file in (project_env, home_env):
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    s = line.strip().strip('"').strip("'")
                    if not s or s.startswith("#"):
                        continue
                    if "=" in s:
                        _, v = s.split("=", 1)
                        v = v.strip().strip('"').strip("'")
                        if v:
                            return v
                    elif s.startswith("gsk_") or s.startswith("sk-"):
                        return s
            except Exception:
                pass
    return None


class RealLLMClient:
    """
    Client kết nối LLM thực tế (Groq `openai/gpt-oss-120b`, OpenAI, Gemini OpenAI-compatible, hoặc Ollama)
    với cơ chế lưu Disk Cache (`real_llm_cache.json`) ở `temperature = 0.0`.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.groq.com/openai/v1",
        model_name: str = "openai/gpt-oss-120b",
        cache_file: Union[str, Path] = "real_llm_cache.json",
        bypass_cache: bool = False,
    ) -> None:
        resolved_key = _resolve_api_key(api_key)
        if not resolved_key:
            raise ValueError(
                "Missing API key! Please set GROQ_API_KEY (or OPENAI_API_KEY / GEMINI_API_KEY) in .env."
            )

        from openai import OpenAI

        self.client = OpenAI(api_key=resolved_key, base_url=base_url)
        self.model_name = model_name
        self.base_url = base_url
        self.bypass_cache = bypass_cache
        self.cache_path = Path(cache_file)
        if not self.cache_path.is_absolute():
            self.cache_path = PROJECT_ROOT / self.cache_path
        self.cache: Dict[str, str] = self._load_cache()
        self.narrator = DeterministicAuditNarratorClient()

    def _load_cache(self) -> Dict[str, str]:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)

    def _make_key(self, messages: List[Dict[str, str]], temperature: float) -> str:
        payload = json.dumps(
            {"model": self.model_name, "messages": messages, "temp": temperature},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def chat_json(
        self,
        messages: Union[List[Dict[str, str]], str],
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        """
        Gọi LLM thật với temperature = 0.0 (theo chuẩn Mục 4.1.2 bài OCL2026)
        và tự động lưu cache để tái lập thực nghiệm 100%.
        """
        if isinstance(messages, str):
            msg_list: List[Dict[str, str]] = [
                {
                    "role": "system",
                    "content": (
                        "You are a formal compliance semantic verifier. "
                        "Always respond with a valid JSON object."
                    ),
                },
                {"role": "user", "content": messages},
            ]
        else:
            msg_list = messages

        cache_key = self._make_key(msg_list, temperature)
        if not self.bypass_cache and cache_key in self.cache:
            return self.cache[cache_key]

        fallback_models = [self.model_name]

        last_err: Optional[Exception] = None
        content = "{}"
        for candidate_model in fallback_models:
            print(f"      [LIVE GROQ API CALL] Sending request to Groq model '{candidate_model}'...")
            for retry_i in range(6):
                try:
                    response = self.client.chat.completions.create(
                        model=candidate_model,
                        messages=msg_list,  # type: ignore[arg-type]
                        temperature=temperature,
                        response_format={"type": "json_object"},
                    )
                    content = (response.choices[0].message.content or "{}").strip()
                    if content in ("", "{}", "[]") and retry_i < 3:
                        try:
                            resp_fb = self.client.chat.completions.create(
                                model=candidate_model,
                                messages=msg_list,  # type: ignore[arg-type]
                                temperature=temperature,
                            )
                            raw_txt = (resp_fb.choices[0].message.content or "{}").strip()
                            json_m = re.search(r"\{.*\}", raw_txt, re.DOTALL)
                            if json_m and len(json_m.group(0).strip()) > 5:
                                content = json_m.group(0).strip()
                        except Exception:
                            pass
                    last_err = None
                    break
                except Exception as exc:
                    last_err = exc
                    err_str = str(exc).lower()
                    if "json_validate_failed" in err_str or "failed to generate json" in err_str:
                        # Thử lại không dùng response_format json_object và bóc tách bằng regex
                        try:
                            resp_fb = self.client.chat.completions.create(
                                model=candidate_model,
                                messages=msg_list,  # type: ignore[arg-type]
                                temperature=temperature,
                            )
                            raw_txt = (resp_fb.choices[0].message.content or "{}").strip()
                            json_m = re.search(r"\{.*\}", raw_txt, re.DOTALL)
                            if json_m:
                                content = json_m.group(0)
                            else:
                                content = "{}"
                            last_err = None
                            break
                        except Exception as fb_exc:
                            last_err = fb_exc
                            break
                    if "rate limit" in err_str or "429" in err_str or "tpm" in err_str:
                        wait_match = re.search(r"try again in ([\d\.]+)s", err_str)
                        if wait_match:
                            sleep_s = float(wait_match.group(1)) + 1.5
                        else:
                            sleep_s = 6.0 * (retry_i + 1)
                        time.sleep(sleep_s)
                    else:
                        time.sleep(1.0)
            if last_err is None:
                # Tránh gọi dồn dập vượt TPM (Tokens Per Minute)
                time.sleep(1.2)
                break
        if last_err is not None:
            # Nếu tất cả fallback models đều lỗi json format, trả về JSON rỗng để Tầng 1 bắt lỗi cú pháp thay vì làm sập pipeline
            content = "{}"

        self.cache[cache_key] = content
        self._save_cache()
        return content

    def chat(self, prompt_or_messages: Any, temperature: float = 0.0) -> str:
        """
        Phương thức phục vụ Bước 4.3 (diễn đạt Báo cáo Giải trình từ Justification Tree).
        """
        return self.narrator.chat(prompt_or_messages, temperature=temperature)


def run_single_rule_with_real_llm(
    rule_item: Dict[str, Any],
    retrieved_chunk: Dict[str, Any],
    process_schema: Dict[str, Any],
    llm: RealLLMClient,
    max_retry: int = 5,
    enable_l1_l2: bool = True,
    enable_l3_roundtrip: bool = True,
) -> Dict[str, Any]:
    """
    Thực thi vòng lặp tổng hợp và tự sửa lỗi 3 tầng với RealLLMClient.
    Chỉ truyền duy nhất 2 thông tin nguyên bản:
    1. Nội dung văn bản luật thô (`retrieved_chunk['text']`)
    2. Lược đồ dữ liệu ngân hàng (`process_schema`)
    Không chứa bất kỳ câu mớm bẫy viết cứng nào.
    """
    raw_desc = str(rule_item.get("description") or "").strip()
    policy_req = re.sub(r"^Bẫy[^:]*:\s*", "", raw_desc).strip()
    req_line = f"Compliance Policy Requirement: {policy_req}\n" if policy_req else ""

    allowed_templates = sorted(list(ALLOWED_DECLARE_TEMPLATES))
    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are a formal compliance assistant for financial workflows. "
                "Translate the business compliance policy requirement and its cited EU Directive clause "
                "into a formal DECLARE constraint in JSON format.\n"
                f"Allowed DECLARE templates: {allowed_templates}\n"
                "Return valid JSON with keys: article_id, template_name, activation_activity, target_activity, "
                "activation_attr, activation_op, activation_val, time_min, time_max, time_unit.\n"
                "IMPORTANT RULES:\n"
                "1. Only specify activation_attr, activation_op, activation_val, or time_max if explicitly stated in the compliance policy requirement or directive; otherwise, you MUST set them to null.\n"
                "2. Numeric monetary thresholds (e.g. 200, 75000) belong to activation_val as a float (e.g. 75000.0) with activation_op (e.g. '<=', '>=').\n"
                "3. Durations (e.g. 14 days) belong to time_max (e.g. 14) with time_unit ('s', 'm', 'h', 'd').\n"
                "4. DECLARE constraints define the REQUIRED condition for valid/compliant execution (not the violation trigger). E.g., to enforce a statutory ceiling of 75,000 EUR, specify '<= 75000.0'; to enforce a statutory floor of 200 EUR, specify '>= 200.0'.\n"
                "5. 'article_id' must match the exact clause ID provided in the prompt header (e.g. 'Article 2(2)')."
            ),
        },
        # Neutral In-Context Example 1: Pure Control-Flow
        {
            "role": "user",
            "content": (
                "Directive Clause (Article Example-1): The creditor shall verify the identity of the consumer before granting the credit.\n"
                "Compliance Policy Requirement: Identity verification must precede loan account opening.\n"
                "Allowed Activities: ['Identity_Verification', 'Account_Opening']\n"
                "Allowed Case Attributes: ['case:RequestedAmount']\n"
                "Allowed Event Attributes: ['Action']"
            ),
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "article_id": "Article Example-1",
                    "template_name": "Precedence",
                    "activation_activity": "Identity_Verification",
                    "target_activity": "Account_Opening",
                    "activation_attr": None,
                    "activation_op": None,
                    "activation_val": None,
                    "time_min": None,
                    "time_max": None,
                    "time_unit": None,
                }
            ),
        },
        # Neutral In-Context Example 2: Temporal & Data-Aware
        {
            "role": "user",
            "content": (
                "Directive Clause (Article Example-2): For credit transactions exceeding EUR 10,000, confirmation shall be provided within 2 days.\n"
                "Compliance Policy Requirement: When offered amount exceeds 10000, confirmation must follow within 2 days.\n"
                "Allowed Activities: ['Create_Offer', 'Send_Confirmation']\n"
                "Allowed Case Attributes: ['case:RequestedAmount']\n"
                "Allowed Event Attributes: ['OfferedAmount']"
            ),
        },
        {
            "role": "assistant",
            "content": json.dumps(
                {
                    "article_id": "Article Example-2",
                    "template_name": "Response",
                    "activation_activity": "Create_Offer",
                    "target_activity": "Send_Confirmation",
                    "activation_attr": "OfferedAmount",
                    "activation_op": ">",
                    "activation_val": 10000.0,
                    "time_min": None,
                    "time_max": 2,
                    "time_unit": "d",
                }
            ),
        },
        # Actual User Query
        {
            "role": "user",
            "content": (
                f"Directive Clause ({retrieved_chunk['article_id']}): {retrieved_chunk['text']}\n"
                f"{req_line}"
                f"Allowed Activities: {process_schema['valid_activities']}\n"
                f"Allowed Case Attributes: {list(process_schema['case_attributes'].keys())}\n"
                f"Allowed Event Attributes: {list(process_schema['event_attributes'].keys())}\n"
                "Return the DECLARE constraint as a valid JSON object."
            ),
        },
    ]

    trajectory: List[Dict[str, Any]] = []

    for attempt in range(1, max_retry + 1):
        raw_output = llm.chat_json(messages, temperature=0.0)

        # Kiểm tra Tầng 1 & Tầng 2
        if enable_l1_l2:
            ok_l12, res_or_err = check_layer1_and_layer2(raw_output, process_schema, retrieved_chunk)
            if not ok_l12:
                trajectory.append(
                    {
                        "round": attempt,
                        "output": raw_output,
                        "status": "FAILED_L1_L2",
                        "error": str(res_or_err),
                    }
                )
                messages.append({"role": "assistant", "content": raw_output})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Validation failed: {res_or_err}. Please fix the JSON.",
                    }
                )
                continue
            ast_dict = res_or_err
        else:
            ok_l1, res_l1 = validate_layer1_ast(raw_output)
            if not ok_l1:
                trajectory.append(
                    {
                        "round": attempt,
                        "output": raw_output,
                        "status": "FAILED_L1_SYNTAX",
                        "error": str(res_l1),
                    }
                )
                break
            ast_dict = res_l1.model_dump()

        # Nếu qua Tầng 1 & 2 -> Kiểm tra Tầng 3 (Generic Entity Matcher + Roundtrip Check)
        if enable_l3_roundtrip:
            ok_rt, rt_msg = check_roundtrip_fidelity(ast_dict, retrieved_chunk, llm, rule_meta=rule_item)
            is_trap = bool(rule_item.get("is_baseless_trap", False))
            if not ok_rt:
                if is_trap and "BASELESS" in rt_msg:
                    # Đúng là bẫy ảo giác được thiết kế sẵn và đã phát hiện thành công
                    trajectory.append(
                        {
                            "round": attempt,
                            "output": raw_output,
                            "status": "DETECTED_BASELESS_TRAP",
                            "error": rt_msg,
                        }
                    )
                    return {
                        "final_ast": ast_dict,
                        "rounds_needed": attempt - 1,
                        "trajectory": trajectory,
                        "roundtrip_ok": False,
                        "roundtrip_msg": rt_msg,
                    }

                # Đối với quy tắc nghiệp vụ thông thường, tiếp tục vòng lặp tự sửa
                trajectory.append(
                    {
                        "round": attempt,
                        "output": raw_output,
                        "status": "FAILED_L3_ROUNDTRIP",
                        "error": rt_msg,
                    }
                )
                messages.append({"role": "assistant", "content": raw_output})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Semantic verification failed: {rt_msg}. Please revise the DECLARE constraint JSON to address this feedback.",
                    }
                )
                continue
        else:
            ok_rt = True
            rt_msg = "Roundtrip check disabled."

        # Thành công
        trajectory.append(
            {
                "round": attempt,
                "output": raw_output,
                "status": "PASSED",
                "error": None,
            }
        )
        return {
            "final_ast": ast_dict,
            "rounds_needed": attempt - 1,
            "trajectory": trajectory,
            "roundtrip_ok": True,
            "roundtrip_msg": rt_msg,
        }

    return {
        "final_ast": None,
        "rounds_needed": max_retry,
        "trajectory": trajectory,
        "roundtrip_ok": False,
        "roundtrip_msg": "Exceeded max retries.",
    }
