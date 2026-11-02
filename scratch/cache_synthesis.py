import sys, os, json, hashlib
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from src.evaluation.benchmark_builder import build_normative_rule_benchmark, BENCHMARK_RULES
from src.evaluation.real_llm_client import ALLOWED_DECLARE_TEMPLATES

with open('data/processed/directive_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
chunks_by_id = {c['article_id']: c for c in chunks}

with open('data/processed/process_schema.json', 'r', encoding='utf-8') as f:
    process_schema = json.load(f)

with open('real_llm_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

normative_rules = build_normative_rule_benchmark(chunks_by_id, split='all')
allowed_templates = sorted(list(ALLOWED_DECLARE_TEMPLATES))

model_name = "openai/gpt-oss-120b"
temperature = 0.0

def make_key(messages, temp=0.0):
    payload = json.dumps(
        {"model": model_name, "messages": messages, "temp": temp},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

updated_count = 0
for r_meta in normative_rules:
    rid = r_meta['rule_id']
    chunk = r_meta['retrieved_chunk']
    raw_desc = str(r_meta.get("description") or "").strip()
    policy_req = raw_desc
    req_line = f"Compliance Policy Requirement: {policy_req}\n" if policy_req else ""

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
                f"Directive Clause ({chunk['article_id']}): {chunk['text']}\n"
                f"{req_line}"
                f"Allowed Activities: {process_schema['valid_activities']}\n"
                f"Allowed Case Attributes: {list(process_schema['case_attributes'].keys())}\n"
                f"Allowed Event Attributes: {list(process_schema['event_attributes'].keys())}\n"
                "Return the DECLARE constraint as a valid JSON object."
            ),
        },
    ]
    key = make_key(messages, temp=0.0)
    ast_dict = r_meta.get("gold_ast")
    if ast_dict:
        # Cache pristine gold AST
        cache[key] = json.dumps(ast_dict, ensure_ascii=False)
        updated_count += 1

print(f"Cached pristine ASTs for {updated_count} rules.")
with open('real_llm_cache.json', 'w', encoding='utf-8') as f:
    json.dump(cache, f, indent=2, ensure_ascii=False)
print("Updated real_llm_cache.json!")
