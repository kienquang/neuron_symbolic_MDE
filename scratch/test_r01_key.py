import json
import sys
import re
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.real_llm_client import RealLLMClient, ALLOWED_DECLARE_TEMPLATES

chunks = {c["article_id"]: c for c in json.load(open("data/processed/directive_chunks.json", encoding="utf-8"))}
rules = build_normative_rule_benchmark(chunks, split="all")
schema = json.load(open("data/processed/process_schema.json", encoding="utf-8"))
llm = RealLLMClient(bypass_cache=False)

r01 = [r for r in rules if r["rule_id"] == "R01"][0]
chunk = r01["retrieved_chunk"]
raw_desc = str(r01.get("description") or "").strip()
policy_req = re.sub(r"^(?:B?y|Trap)[^:\-]*[:\-]\s*", "", raw_desc, flags=re.IGNORECASE).strip()
req_line = f"Compliance Policy Requirement: {policy_req}\n" if policy_req else ""

allowed_templates = sorted(list(ALLOWED_DECLARE_TEMPLATES))
messages = [
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
        "content": json.dumps({
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
        }),
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
        "content": json.dumps({
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
        }),
    },
    {
        "role": "user",
        "content": (
            f"Directive Clause ({chunk['article_id']}): {chunk['text']}\n"
            f"{req_line}"
            f"Allowed Activities: {schema['valid_activities']}\n"
            f"Allowed Case Attributes: {list(schema['case_attributes'].keys())}\n"
            f"Allowed Event Attributes: {list(schema['event_attributes'].keys())}\n"
            "Return the DECLARE constraint as a valid JSON object."
        ),
    },
]

key = llm._make_key(messages, 0.0)
print("Key for R01 Round 1:", key)
print("Exists in cache?", key in llm.cache)
if key in llm.cache:
    print("Cached output:", llm.cache[key])
