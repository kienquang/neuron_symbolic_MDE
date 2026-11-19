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
import sys
import time
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False

from src.mde.constraint_ast import (
    BINARY_TEMPLATES,
    UNARY_TEMPLATES,
    DeclareConstraintAST,
    validate_layer1_ast,
)
from src.mde.deontic_mde_compiler import (
    UNMAPPED_ATTR_TOKEN,
    build_constrained_deontic_schema,
    format_behavioral_profile_for_prompt,
    validate_and_compile_deontic_or_ast,
)
from src.evaluation.experiment_runner import check_layer1_and_layer2
from src.symbolic.counterfactual_prober import verify_via_counterfactual_probing
from src.symbolic.verbalizer_roundtrip import (
    check_roundtrip_fidelity,
    extract_clause_numeric_entities,
)
from src.evaluation.grounded_auditor import DeterministicAuditNarratorClient

ALLOWED_DECLARE_TEMPLATES = UNARY_TEMPLATES | BINARY_TEMPLATES

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_api_keys(explicit_key: Optional[str] = None) -> List[str]:
    """Tự động nạp danh sách API keys từ .env (hỗ trợ xoay tua GROQ_API_KEYS khi chạm giới hạn)."""
    if explicit_key:
        return [explicit_key]
    project_env = PROJECT_ROOT / ".env"
    home_env = Path.home() / ".env"
    if project_env.exists():
        load_dotenv(dotenv_path=project_env, override=True)
    if home_env.exists():
        load_dotenv(dotenv_path=home_env, override=False)

    keys: List[str] = []
    multi_env = os.environ.get("GROQ_API_KEYS")
    if multi_env:
        for k in multi_env.split(","):
            k = k.strip().strip('"').strip("'")
            if k and k not in keys:
                keys.append(k)

    for var_name in ("GROQ_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "API_KEY"):
        val = os.environ.get(var_name)
        if val and val.strip():
            k = val.strip().strip('"').strip("'")
            if k and k not in keys:
                keys.append(k)

    for env_file in (project_env, home_env):
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    matches = re.findall(r"(gsk_[A-Za-z0-9]+|sk-[A-Za-z0-9]+)", line)
                    for k in matches:
                        if k not in keys:
                            keys.append(k)
            except Exception:
                pass
    return keys


def _resolve_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    keys = _resolve_api_keys(explicit_key)
    return keys[0] if keys else None


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
        use_real_llm_narrator: bool = True,
    ) -> None:
        self.api_keys = _resolve_api_keys(api_key)
        if not self.api_keys:
            raise ValueError(
                "Missing API key! Please set GROQ_API_KEY (or OPENAI_API_KEY / GEMINI_API_KEY) in .env."
            )
        self.current_key_idx = 0

        from openai import OpenAI

        self.model_name = model_name
        self.base_url = base_url
        self.bypass_cache = bypass_cache
        self.use_real_llm_narrator = use_real_llm_narrator
        self.cache_path = Path(cache_file)
        if not self.cache_path.is_absolute():
            self.cache_path = PROJECT_ROOT / self.cache_path
        self.cache: Dict[str, str] = self._load_cache()
        self.narrator = DeterministicAuditNarratorClient()
        self.client = OpenAI(api_key=self.api_keys[self.current_key_idx], base_url=base_url, timeout=30.0)

    def _rotate_api_key(self) -> None:
        if len(self.api_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            from openai import OpenAI
            new_masked = self.api_keys[self.current_key_idx][:10] + "..."
            print(f"      [GROQ KEY ROTATED]: Switched to backup key ({new_masked}) due to rate limit.")
            self.client = OpenAI(api_key=self.api_keys[self.current_key_idx], base_url=self.base_url, timeout=30.0)

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

    def _make_key(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        response_mode: str = "json",
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload_obj: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temp": temperature,
        }
        if response_mode != "json":
            payload_obj["mode"] = response_mode
        if json_schema is not None:
            schema_raw = json.dumps(json_schema, sort_keys=True, ensure_ascii=False)
            payload_obj["schema_sha"] = hashlib.sha256(schema_raw.encode("utf-8")).hexdigest()
        payload = json.dumps(payload_obj, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _call_groq_with_cache(
        self,
        msg_list: List[Dict[str, str]],
        temperature: float = 0.0,
        json_schema: Optional[Dict[str, Any]] = None,
        response_mode: str = "json",
    ) -> str:
        """Shared Groq API caller with disk caching, key rotation, and 429 cooldown."""
        cache_key = self._make_key(
            msg_list,
            temperature,
            response_mode=response_mode,
            json_schema=json_schema,
        )
        if not self.bypass_cache and cache_key in self.cache:
            return self.cache[cache_key]

        last_err: Optional[Exception] = None
        default_empty = "{}" if response_mode == "json" else ""
        content = default_empty
        print(f"      [LIVE GROQ API CALL ({response_mode.upper()})] Sending request to Groq model '{self.model_name}'...")
        total_retries = 60
        key_cooldown_until: Dict[int, float] = {}
        use_json_schema = json_schema is not None
        is_qwen_model = "qwen" in self.model_name.lower()
        qwen_max_tokens = 650

        for retry_i in range(total_retries):
            try:
                create_kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": msg_list,
                    "temperature": temperature,
                    "timeout": 35.0,
                }
                if is_qwen_model:
                    create_kwargs["max_tokens"] = qwen_max_tokens
                    create_kwargs["reasoning_effort"] = "none"
                if response_mode == "json":
                    resp_fmt: Dict[str, Any] = {"type": "json_object"}
                    if use_json_schema and json_schema is not None:
                        resp_fmt = {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "DeonticNormativeFrame",
                                "strict": False,
                                "schema": json_schema,
                            },
                        }
                    create_kwargs["response_format"] = resp_fmt
                try:
                    response = self.client.chat.completions.create(**create_kwargs)
                except Exception as schema_exc:
                    schema_err_l = str(schema_exc).lower()
                    if "reasoning_effort" in schema_err_l:
                        create_kwargs.pop("reasoning_effort", None)
                        response = self.client.chat.completions.create(**create_kwargs)
                    elif (
                        response_mode == "json"
                        and use_json_schema
                        and ("json_schema" in schema_err_l or "response_format" in schema_err_l)
                    ):
                        use_json_schema = False
                        create_kwargs["response_format"] = {"type": "json_object"}
                        response = self.client.chat.completions.create(**create_kwargs)
                    else:
                        raise schema_exc

                content = (response.choices[0].message.content or default_empty).strip()
                if response_mode == "json" and content in ("", "{}", "[]") and retry_i < 3:
                    try:
                        fb_kwargs: Dict[str, Any] = {
                            "model": self.model_name,
                            "messages": msg_list,  # type: ignore[arg-type]
                            "temperature": temperature,
                        }
                        if is_qwen_model:
                            fb_kwargs["max_tokens"] = qwen_max_tokens
                            fb_kwargs["reasoning_effort"] = "none"
                        resp_fb = self.client.chat.completions.create(**fb_kwargs)
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
                print(f"      [GROQ RETRY {retry_i+1}/{total_retries}]: Error: {exc}")
                if response_mode == "json" and ("json_validate_failed" in err_str or "failed to generate json" in err_str):
                    try:
                        fb_kwargs = {
                            "model": self.model_name,
                            "messages": msg_list,  # type: ignore[arg-type]
                            "temperature": temperature,
                        }
                        if is_qwen_model:
                            fb_kwargs["max_tokens"] = qwen_max_tokens
                            fb_kwargs["reasoning_effort"] = "none"
                        resp_fb = self.client.chat.completions.create(**fb_kwargs)
                        raw_txt = (resp_fb.choices[0].message.content or "{}").strip()
                        json_m = re.search(r"\{.*\}", raw_txt, re.DOTALL)
                        content = json_m.group(0) if json_m else "{}"
                        last_err = None
                        break
                    except Exception as fb_exc:
                        last_err = fb_exc
                        break
                if "please reduce your message size" in err_str:
                    raise RuntimeError(f"RealLLMClient payload exceeds single-request token limit (413): {exc}")
                if "rate limit" in err_str or "429" in err_str or "tpm" in err_str or "tpd" in err_str or "otpm" in err_str:
                    if ("otpm" in err_str or "output tokens per minute" in err_str) and is_qwen_model:
                        qwen_max_tokens = max(400, qwen_max_tokens - 100)
                    wait_match = re.search(r"try again in (?:(\d+)m)?([\d\.]+)s", err_str)
                    if wait_match:
                        mins = float(wait_match.group(1)) if wait_match.group(1) else 0.0
                        secs = float(wait_match.group(2)) if wait_match.group(2) else 0.0
                        total_wait = mins * 60.0 + secs
                    elif "otpm" in err_str or "output tokens per minute" in err_str:
                        total_wait = 15.0
                    else:
                        total_wait = 5.0 * (retry_i + 1)

                    key_cooldown_until[self.current_key_idx] = time.time() + total_wait

                    if len(self.api_keys) > 1:
                        now = time.time()
                        ready_keys = [i for i in range(len(self.api_keys)) if now >= key_cooldown_until.get(i, 0.0)]
                        if ready_keys:
                            next_k = ready_keys[0]
                            self.current_key_idx = next_k
                            from openai import OpenAI
                            self.client = OpenAI(api_key=self.api_keys[self.current_key_idx], base_url=self.base_url, timeout=35.0)
                            print(f"      [GROQ KEY ROTATED]: Switched to ready key ({self.api_keys[self.current_key_idx][:10]}...).", flush=True)
                            time.sleep(0.5)
                        else:
                            earliest_idx = min(range(len(self.api_keys)), key=lambda i: key_cooldown_until.get(i, 0.0))
                            sleep_needed = max(key_cooldown_until[earliest_idx] - time.time() + 2.0, 2.0)
                            print(f"      [GROQ ALL KEYS LIMITED]: All {len(self.api_keys)} keys hit quota. Waiting up to {sleep_needed:.1f}s for key ({self.api_keys[earliest_idx][:10]}...) to reset...", flush=True)
                            sleep_end = time.time() + sleep_needed
                            while time.time() < sleep_end:
                                time.sleep(min(5.0, max(0.5, sleep_end - time.time())))
                                now_c = time.time()
                                any_ready = [i for i in range(len(self.api_keys)) if now_c >= key_cooldown_until.get(i, 0.0)]
                                if any_ready:
                                    earliest_idx = any_ready[0]
                                    break
                            self.current_key_idx = earliest_idx
                            from openai import OpenAI
                            self.client = OpenAI(api_key=self.api_keys[self.current_key_idx], base_url=self.base_url, timeout=35.0)
                    else:
                        sleep_s = max(total_wait + 2.0, 3.0)
                        print(f"      [GROQ COOLDOWN]: Sleeping {sleep_s:.1f}s until quota resets...")
                        time.sleep(sleep_s)
                else:
                    time.sleep(1.5)

        if last_err is not None:
            raise RuntimeError(f"RealLLMClient call failed after {total_retries} retries: {last_err}")

        time.sleep(0.15 if len(self.api_keys) > 1 else 0.5)

        if content.strip() not in ("", "{}", "[]"):
            self.cache[cache_key] = content
            self._save_cache()

        return content

    def chat_json(
        self,
        messages: Union[List[Dict[str, str]], str],
        temperature: float = 0.0,
        json_schema: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call Groq JSON completion with temperature=0.0 and deterministic disk caching.
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
        return self._call_groq_with_cache(
            msg_list,
            temperature=temperature,
            json_schema=json_schema,
            response_mode="json",
        )

    def chat(self, prompt_or_messages: Any, temperature: float = 0.0) -> str:
        """
        Generate Step 4.3 natural-language audit explanation grounded in Justification Tree.
        Calls live/cached Groq LLM when `use_real_llm_narrator=True` (no template bypass).
        """
        if not self.use_real_llm_narrator:
            return self.narrator.chat(prompt_or_messages, temperature=temperature)

        if isinstance(prompt_or_messages, str):
            msg_list: List[Dict[str, str]] = [
                {
                    "role": "system",
                    "content": (
                        "You are a Process Compliance Auditor. Write a concise, natural-language audit "
                        "explanation strictly citing the exact case_id, article_id, verdict label, and numerical "
                        "metrics from the provided Justification Tree without altering or fabricating any citation."
                    ),
                },
                {"role": "user", "content": prompt_or_messages},
            ]
        elif isinstance(prompt_or_messages, list):
            msg_list = prompt_or_messages
        else:
            msg_list = [{"role": "user", "content": str(prompt_or_messages)}]
        return self._call_groq_with_cache(msg_list, temperature=temperature, response_mode="text")


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
    Thực thi vòng lặp tổng hợp và kiểm chứng với RealLLMClient:
      - Khi `enable_l1_l2=True` (Kiến trúc Đề xuất): Sử dụng Deontic MDE Intermediate Frame +
        Grammar-Constrained Decoding + Behavioral Profile Grounding.
      - Khi `enable_l1_l2=False` (Ablation tắt Tiền kiểm chứng): Sinh trực tiếp JSON DECLARE AST không qua Deontic MDE.
      - Khi `enable_l3_roundtrip=True`: Kiểm chứng Ngữ nghĩa bằng Đột biến Vết Đối chứng (Counterfactual Trace Mutation Probing).
    Chỉ truyền duy nhất thông tin nguyên bản từ Văn bản luật (`retrieved_chunk['text']`), Yêu cầu chính sách
    và Lược đồ quy trình (`process_schema`), tuyệt đối không chứa bất kỳ câu mớm bẫy viết cứng nào.
    """
    raw_desc = str(rule_item.get("description") or "").strip()
    policy_req = re.sub(
        r"^(?:Quy định gài bẫy|Quy định bẫy|Gài bẫy|Bẫy|Trap)[^:\-]*[:\-]\s*",
        "",
        raw_desc,
        flags=re.IGNORECASE,
    ).strip()
    req_line = f"Compliance Policy Requirement: {policy_req}\n" if policy_req else ""

    act_desc_map = process_schema.get("activity_descriptions", {})
    if act_desc_map:
        activities_formatted = "\n".join(
            [f"  - {act}: {act_desc_map.get(act, 'Activity in process log')}" for act in process_schema["valid_activities"]]
        )
        activities_str = f"Allowed Activities (with operational domain definitions):\n{activities_formatted}"
    else:
        activities_str = f"Allowed Activities: {process_schema['valid_activities']}"

    deontic_json_schema: Optional[Dict[str, Any]] = None

    if enable_l1_l2:
        DeonticSchemaCls = build_constrained_deontic_schema(process_schema)
        deontic_json_schema = DeonticSchemaCls.model_json_schema()
        behavioral_profile_str = format_behavioral_profile_for_prompt(process_schema, top_k=110)
        bp_block = f"{behavioral_profile_str}\n" if behavioral_profile_str else ""
        allowed_case_attrs = list(process_schema["case_attributes"].keys())
        allowed_event_attrs = list(process_schema["event_attributes"].keys()) + [UNMAPPED_ATTR_TOKEN]
        attr_meta_lines: List[str] = []
        for cname, cinfo in process_schema.get("case_attributes", {}).items():
            if isinstance(cinfo, dict) and cname != "case:concept:name":
                attr_meta_lines.append(
                    f"  - {cname} ({cinfo.get('type', 'Any')}, case-level, samples={cinfo.get('samples', [])[:2]})"
                )
        for ename, einfo in process_schema.get("event_attributes", {}).items():
            if isinstance(einfo, dict) and einfo.get("type") in ("Float", "Integer", "Boolean"):
                attr_meta_lines.append(
                    f"  - {ename} ({einfo.get('type')}, on {einfo.get('applicable_activities', [])}, samples={einfo.get('samples', [])[:2]})"
                )
        attr_meta_block = (
            "Schema Data Attribute Details:\n" + "\n".join(attr_meta_lines) + "\n"
            if attr_meta_lines
            else ""
        )

        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are a Deontic Model-Driven Engineering (MDE) compliance extractor for financial workflows.\n"
                    "Extract a structured DeonticNormativeFrame in JSON format from the cited EU Directive clause and "
                    "the bank's operational compliance policy requirement.\n"
                    "Required JSON keys: article_id, deontic_modality, temporal_relation, anchor_activity, "
                    "consequent_activity, attribute_guard, guard_operator, guard_threshold, deadline_days, unsupported_by_text.\n"
                    "DEONTIC MDE EXTRACTION PRINCIPLES:\n"
                    "1. deontic_modality:\n"
                    "   - 'OBLIGATION': Mandatory duty, precondition, or required quantitative bound on workflow execution ('shall', 'must', 'required').\n"
                    "   - 'PROHIBITION': Forbidden workflow execution or forbidden sequential/attribute condition ('shall not', 'must not', 'prohibited', 'forbidden').\n"
                    "     Note how PROHIBITION composes with temporal_relation:\n"
                    "     * PROHIBITION + 'MANDATORY_RESPONSE' compiles to Not Response[A, B] (when A occurs, B must NOT subsequently follow).\n"
                    "     * PROHIBITION + 'PREREQUISITE_BEFORE' compiles to Not Precedence[A, B] (A must NOT occur prior to B).\n"
                    "     * PROHIBITION + 'MUTUAL_EXCLUSION' compiles to Not Co-Existence[A, B] (A and B cannot coexist in ANY order).\n"
                    "   - 'PERMISSION_RIGHT': Conditional or time-bounded discretionary right of a party ('may', 'is entitled to', 'has the right to').\n"
                    "   - 'EXEMPTION_OUT_OF_SCOPE': Set ONLY when the cited Directive clause itself is an explicit statutory scope exclusion/exemption (e.g., 'shall not apply', 'exempt') stating no enforceable credit workflow requirement; whenever the policy specifies a concrete process rule on schema activities under the clause, ALWAYS extract the workflow frame (OBLIGATION/PROHIBITION/PERMISSION_RIGHT) and set unsupported_by_text=false so semantic verification can audit alignment.\n"
                    "2. temporal_relation:\n"
                    "   - 'PREREQUISITE_BEFORE': anchor_activity (A) is a mandatory precondition that must precede "
                    "any occurrence of consequent_activity (B) (whenever B happens, A must have occurred earlier; B not occurring is still compliant). Compiles to Precedence[A, B] (or Not Precedence[A, B] under PROHIBITION).\n"
                    "   - 'IMMEDIATE_PREREQUISITE': anchor_activity (A) must occur IMMEDIATELY before consequent_activity (B) "
                    "as a direct transition (Direct DFG > 0). Compiles to Chain Precedence[A, B].\n"
                    "   - 'MANDATORY_RESPONSE': When trigger anchor_activity (A) occurs, consequent_activity (B) must subsequently "
                    "occur (within deadline_days if specified). Compiles to Response[A, B] (or Not Response[A, B] under PROHIBITION).\n"
                    "   - 'IMMEDIATE_RESPONSE': When trigger anchor_activity (A) occurs, consequent_activity (B) must occur IMMEDIATELY "
                    "as the very next step (Direct DFG > 0). Compiles to Chain Response[A, B].\n"
                    "   - 'MUTUAL_EXCLUSION': Symmetric ban where anchor_activity (A) and consequent_activity (B) cannot both occur in ANY order. "
                    "Compiles to Not Co-Existence[A, B].\n"
                    "   - 'UNARY_CONDITION': Single-activity data constraint on anchor_activity (A) with consequent_activity=null (do NOT use UNARY_CONDITION when the policy requires a relation between two distinct workflow events). "
                    "With 'OBLIGATION', guard_operator + guard_threshold specifies the REQUIRED valid bound (e.g. '>= 500.0', '<= 50000.0'). "
                    "With 'PROHIBITION', it specifies the FORBIDDEN bound (e.g. '< 500.0', '> 50000.0').\n"
                    "3. Grounding in Behavioral Profile & Attributes:\n"
                    "   - Consult the Empirical Process Behavioral Profile and the Allowed Activities definitions in the schema to align (anchor_activity, consequent_activity) at the exact lifecycle stage (e.g., distinguishing initial intake vs. formal acceptance vs. validation, drafting vs. document persistence vs. dispatch/communication to the customer, customer acceptance vs. final approval, and official state milestones vs. repeatable human work-items, strictly according to each activity's definition in the schema).\n"
                    "   - Only set attribute_guard, guard_operator, guard_threshold, or deadline_days if explicitly required; otherwise set to null.\n"
                    f"   - Only set attribute_guard='{UNMAPPED_ATTR_TOKEN}' when the policy explicitly checks a quantitative/data attribute predicate "
                    "(paired with guard_operator and guard_threshold) whose metric is absent from Schema Data Attribute Details and Allowed Case/Event Attributes; "
                    "for pure ordering or calendar-day deadline rules with no data threshold, keep attribute_guard=null."
                ),
            },
            # Neutral In-Context Example 1: Control-Flow Prerequisite
            {
                "role": "user",
                "content": (
                    "Directive Clause (Article Example-1): The creditor shall verify the identity of the consumer before granting the credit.\n"
                    "Compliance Policy Requirement: Identity verification must precede loan account opening.\n"
                    "Allowed Activities: ['Identity_Verification', 'Account_Opening']\n"
                    "Allowed Case Attributes: ['case:RequestedAmount']\n"
                    "Allowed Event Attributes: ['Action', 'UNMAPPED_MISSING_IN_LOG']"
                ),
            },
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "article_id": "Article Example-1",
                        "deontic_modality": "OBLIGATION",
                        "temporal_relation": "PREREQUISITE_BEFORE",
                        "anchor_activity": "Identity_Verification",
                        "consequent_activity": "Account_Opening",
                        "attribute_guard": None,
                        "guard_operator": None,
                        "guard_threshold": None,
                        "deadline_days": None,
                        "unsupported_by_text": False,
                    }
                ),
            },
            # Neutral In-Context Example 2: Temporal & Data-Aware Response
            {
                "role": "user",
                "content": (
                    "Directive Clause (Article Example-2): For credit transactions exceeding EUR 10,000, confirmation shall be provided within 2 days.\n"
                    "Compliance Policy Requirement: When offered amount exceeds 10000, confirmation must follow within 2 days.\n"
                    "Allowed Activities: ['Create_Offer', 'Send_Confirmation']\n"
                    "Allowed Case Attributes: ['case:RequestedAmount']\n"
                    "Allowed Event Attributes: ['OfferedAmount', 'UNMAPPED_MISSING_IN_LOG']"
                ),
            },
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "article_id": "Article Example-2",
                        "deontic_modality": "OBLIGATION",
                        "temporal_relation": "MANDATORY_RESPONSE",
                        "anchor_activity": "Create_Offer",
                        "consequent_activity": "Send_Confirmation",
                        "attribute_guard": "OfferedAmount",
                        "guard_operator": ">",
                        "guard_threshold": 10000.0,
                        "deadline_days": 2,
                        "unsupported_by_text": False,
                    }
                ),
            },
            # Actual User Query
            {
                "role": "user",
                "content": (
                    f"Directive Clause ({retrieved_chunk['article_id']}): {retrieved_chunk['text']}\n"
                    f"{req_line}"
                    f"{activities_str}\n"
                    f"{bp_block}"
                    f"{attr_meta_block}"
                    f"Allowed Case Attributes: {allowed_case_attrs}\n"
                    f"Allowed Event Attributes: {allowed_event_attrs}\n"
                    "Return the DeonticNormativeFrame as a valid JSON object."
                ),
            },
        ]
    else:
        allowed_templates = sorted(list(ALLOWED_DECLARE_TEMPLATES))
        allowed_event_attrs = list(process_schema["event_attributes"].keys())
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a formal compliance assistant for financial workflows. "
                    "Translate the business compliance policy requirement and its cited EU Directive clause "
                    "into a formal DECLARE constraint in JSON format.\n"
                    f"Allowed DECLARE templates: {allowed_templates}\n"
                    "Return valid JSON with keys: article_id, template_name, activation_activity, target_activity, "
                    "activation_attr, activation_op, activation_val, time_min, time_max, time_unit, unsupported_by_text.\n"
                    "IMPORTANT RULES:\n"
                    "1. Only specify activation_attr, activation_op, activation_val, or time_max if explicitly stated in the compliance policy requirement or directive; otherwise, you MUST set them to null.\n"
                    "2. Numeric monetary thresholds (e.g. 500, 10000) belong to activation_val as a float (e.g. 10000.0) with activation_op (e.g. '<=', '>=').\n"
                    "3. Durations (e.g. 14 days) belong to time_max (e.g. 14) with time_unit ('s', 'm', 'h', 'd').\n"
                    "4. DECLARE constraints define the REQUIRED condition for valid/compliant execution (not the violation trigger). E.g., an upper bound uses '<=' and a lower bound uses '>='.\n"
                    "5. Affirmative trigger-response obligations (whenever A occurs, B must subsequently follow) use template 'Response(activation_activity=A, target_activity=B)'.\n"
                    "6. Backward prerequisite constraints (whenever B occurs, A must have occurred beforehand) use template 'Precedence(activation_activity=A, target_activity=B)'.\n"
                    "7. Universal prohibitions forbidding an entire event condition (e.g. an explicit 'shall not occur' prohibition) use template 'Absence(activation_activity=...)'; positive minimum or maximum eligibility/disclosure bounds (e.g. amount > 0, cost > 0) MUST use 'Existence' or 'Precedence' with the required positive bound so traces lacking the condition are flagged.\n"
                    "8. Mutual exclusion between two events uses template 'Not Co-Existence'.\n"
                    "9. 'article_id' must match the exact clause ID provided in the prompt header.\n"
                    "10. Set unsupported_by_text=true ONLY if the cited Directive clause provides no enforceable workflow obligation for the stated policy (e.g., an exemption, excluded scope, or unrelated subject); otherwise synthesize the DECLARE rule using exact activity and attribute names from the schema and set unsupported_by_text=false."
                ),
            },
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
                        "unsupported_by_text": False,
                    }
                ),
            },
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
                        "unsupported_by_text": False,
                    }
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Directive Clause ({retrieved_chunk['article_id']}): {retrieved_chunk['text']}\n"
                    f"{req_line}"
                    f"{activities_str}\n"
                    f"Allowed Case Attributes: {list(process_schema['case_attributes'].keys())}\n"
                    f"Allowed Event Attributes: {allowed_event_attrs}\n"
                    "Return the DECLARE constraint as a valid JSON object."
                ),
            },
        ]

    trajectory: List[Dict[str, Any]] = []
    ast_field_keys = set(DeclareConstraintAST.model_fields.keys())

    for attempt in range(1, max_retry + 1):
        raw_output = llm.chat_json(messages, temperature=0.0, json_schema=deontic_json_schema)
        raw_output_str = (
            raw_output if isinstance(raw_output, str) else json.dumps(raw_output, ensure_ascii=False)
        )

        # Giai đoạn 1: Kiểm tra và biên dịch Deontic MDE + Grammar-Constrained Schema + Behavioral Profile
        if enable_l1_l2:
            ok_l12, res_or_err = validate_and_compile_deontic_or_ast(
                raw_output, process_schema, retrieved_chunk
            )
            if not ok_l12:
                trajectory.append(
                    {
                        "round": attempt,
                        "output": raw_output,
                        "status": "FAILED_L1_L2",
                        "error": str(res_or_err),
                    }
                )
                print(f"      [Round {attempt} Feedback (Deontic MDE / Γ)]: {res_or_err}")
                messages.append({"role": "assistant", "content": raw_output_str})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Validation failed: {res_or_err}. Please fix the JSON.",
                    }
                )
                continue
            assert isinstance(res_or_err, dict)
            compiled_dict = res_or_err
            ast_dict = {k: v for k, v in compiled_dict.items() if k in ast_field_keys}
        else:
            from src.mde.constraint_ast import extract_json_payload

            parsed_direct: Dict[str, Any] = {}
            if isinstance(raw_output, dict):
                parsed_direct = dict(raw_output)
            else:
                try:
                    parsed_direct = json.loads(extract_json_payload(raw_output))
                except Exception:
                    parsed_direct = {}

            raw_unsupported = bool(parsed_direct.get("unsupported_by_text", False))
            raw_attr = parsed_direct.get("activation_attr")
            # Strip optional abstention flags before Pydantic extra='forbid' check on DeclareConstraintAST
            clean_ast_payload = {
                k: v
                for k, v in parsed_direct.items()
                if k in ast_field_keys
            }
            if raw_unsupported and not clean_ast_payload.get("activation_activity"):
                valid_acts = process_schema.get("valid_activities", [])
                clean_ast_payload.setdefault("article_id", str(retrieved_chunk.get("article_id", "")))
                clean_ast_payload.setdefault("template_name", "Existence")
                if valid_acts:
                    clean_ast_payload["activation_activity"] = valid_acts[0]

            ok_l1, res_l1 = validate_layer1_ast(clean_ast_payload if parsed_direct else raw_output)
            if not ok_l1:
                trajectory.append(
                    {
                        "round": attempt,
                        "output": raw_output,
                        "status": "FAILED_L1_SYNTAX",
                        "error": str(res_l1),
                    }
                )
                if attempt == max_retry:
                    break
                messages.append({"role": "assistant", "content": raw_output_str})
                messages.append(
                    {
                        "role": "user",
                        "content": f"JSON syntax validation failed: {res_l1}. Please output a valid DeclareConstraintAST JSON.",
                    }
                )
                continue
            ast_dict = res_l1.model_dump()
            compiled_dict = dict(ast_dict)
            if raw_attr == UNMAPPED_ATTR_TOKEN:
                compiled_dict["deontic_baseless_reason"] = (
                    f"BASELESS (Model Abstained -> MISSING_LOG_EVIDENCE_PHI_VIOLATION): "
                    f"Model marked attribute as '{UNMAPPED_ATTR_TOKEN}'."
                )
            elif raw_unsupported:
                compiled_dict["deontic_baseless_reason"] = (
                    f"BASELESS (Model Abstained -> UNSUPPORTED_BY_DIRECTIVE_TEXT): "
                    f"Model marked clause '{retrieved_chunk.get('article_id', '')}' as unsupported or out-of-scope."
                )

        # Phase 2: Semantic Verification via Counterfactual Trace Mutation Probing
        if enable_l3_roundtrip:
            if not enable_l1_l2 and compiled_dict.get("deontic_baseless_reason"):
                rt_msg = str(compiled_dict["deontic_baseless_reason"])
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
            ok_rt, rt_msg = verify_via_counterfactual_probing(
                compiled_dict,
                retrieved_chunk,
                llm,
                rule_meta=rule_item,
                process_schema=process_schema,
            )
            if not ok_rt:
                is_compiler_terminal = (
                    "Deontic MDE Compiler ->" in rt_msg
                    or "POLICY_STATUTE_NUMERIC_CONFLICT" in rt_msg
                    or "Counterfactual Probe -> BASELESS" in rt_msg
                )
                status_lbl = "DETECTED_BASELESS_TRAP" if "BASELESS" in rt_msg else "FAILED_L3_ROUNDTRIP"
                print(f"      [Round {attempt} Feedback (Counterfactual Probe)]: {rt_msg}")
                trajectory.append(
                    {
                        "round": attempt,
                        "output": raw_output,
                        "status": status_lbl,
                        "error": rt_msg,
                    }
                )
                if is_compiler_terminal or attempt == max_retry:
                    return {
                        "final_ast": ast_dict,
                        "rounds_needed": attempt - 1,
                        "trajectory": trajectory,
                        "roundtrip_ok": False,
                        "roundtrip_msg": rt_msg,
                    }

                messages.append({"role": "assistant", "content": raw_output_str})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Counterfactual semantic verification failed: {rt_msg}. "
                            f"Please revise the JSON to address this feedback."
                        ),
                    }
                )
                continue
        else:
            if compiled_dict.get("deontic_baseless_reason"):
                rt_msg = str(compiled_dict["deontic_baseless_reason"])
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
            ok_rt = True
            rt_msg = "Counterfactual probe disabled."

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
