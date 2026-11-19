"""
Bộ 30 Quy tắc Chuẩn (Ground-Truth Benchmark Suite R01–R30) & Trích xuất Hồ sơ Kiểm thử Phân tầng
từ Chỉ thị 2008/48/EC (directive_2008_48_EC.pdf) và Nhật ký Sự kiện BPI Challenge 2017 (BPIC 2017):
- Tier 1 (Tier1_ControlFlow, R01–R12): 12 Quy tắc Luồng điều khiển Cơ bản (Control-Flow Constraints)
- Tier 2 (Tier2_TemporalData, R13–R22): 10 Quy tắc Thời gian Định lượng & Thuộc tính Dữ liệu (Metric Temporal & Data-Aware)
- Tier 3 (Tier3_BaselessTrap, R23–R30): 8 Quy tắc Bẫy Ảo giác & Thiếu bằng chứng (BASELESS Trap Rules)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
from src.mde.constraint_ast import DeclareConstraintAST
from src.evaluation.justification_tree import check_single_trace_semantics



# Định nghĩa bộ 30 quy tắc chuẩn (Ground-Truth Benchmark Rules R01-R30)
BENCHMARK_RULES: List[Dict[str, Any]] = [
    # --- TIER 1: CONTROL-FLOW CONSTRAINTS (12 RULES: R01 - R12) ---
    {
        "rule_id": "R01",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "A_Create Application",
        "act_b": "A_Concept",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Creditworthiness intake under Article 8(1): Prior to conducting an initial risk assessment on a borrowing file, the institution must register the customer's loan request in its system.",
    },
    {
        "rule_id": "R02",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(1)",
        "template": "Not Response",
        "act_a": "A_Denied",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Prohibition on concluding a declined request under Article 5(1): Where the creditor formally denies the loan request and is unwilling to proceed to conclude the credit agreement, final active funding approval must not subsequently follow.",
    },
    {
        "rule_id": "R03",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 10(1)",
        "template": "Chain Response",
        "act_a": "O_Accepted",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Immediate agreement transition under Article 10(1): Once the consumer formally accepts the finalized credit offer drawn up on a durable medium, the very next workflow step must move the case directly into final active agreement status.",
    },
    {
        "rule_id": "R04",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(1)",
        "template": "Chain Precedence",
        "act_a": "O_Create Offer",
        "act_b": "O_Created",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Offer issuance sequencing under Article 5(1): As soon as a credit proposal is drafted, the immediately following step must be system registration of the finalized offer record.",
    },
    {
        "rule_id": "R05",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(1)",
        "template": "Response",
        "act_a": "O_Created",
        "act_b": "O_Sent (mail and online)",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Mandatory dispatch of created offer under Article 5(1): Whenever a formalized credit offer record is persisted in the system, pre-contractual terms must subsequently be transmitted to the prospective borrower.",
    },
    {
        "rule_id": "R06",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 8(1)",
        "template": "Not Precedence",
        "act_a": "O_Refused",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Prohibition on approving a refused offer under Article 8(1): Prior to granting final credit agreement activation on an application, a previously refused loan offer must not precede final funding approval.",
    },
    {
        "rule_id": "R07",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(1)",
        "template": "Precedence",
        "act_a": "O_Sent (mail and online)",
        "act_b": "O_Accepted",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Pre-contractual binding safeguard under Article 5(1): In good time before the consumer signs and accepts the financing offer, pre-contractual information must be provided to them.",
    },
    {
        "rule_id": "R08",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(1)",
        "template": "Response",
        "act_a": "A_Accepted",
        "act_b": "O_Create Offer",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Offer formulation upon acceptance under Article 5(1): Whenever a credit application completes formal intake acceptance for processing, a tailored financing offer must subsequently be structured for comparison.",
    },
    {
        "rule_id": "R09",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 10(1)",
        "template": "Response",
        "act_a": "O_Create Offer",
        "act_b": "O_Sent (mail and online)",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Durable-medium contract copy under Article 10(1): Whenever a financing proposal is drafted, all contracting consumers must subsequently receive a copy on paper or another durable medium.",
    },
    {
        "rule_id": "R10",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 14(4)",
        "template": "Not Co-Existence",
        "act_a": "A_Cancelled",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Post-withdrawal non-binding safeguard under Article 14(4): If an applicant withdraws and cancels the credit application, that cancelled dossier cannot remain active alongside final credit release.",
    },
    {
        "rule_id": "R11",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 15(1)",
        "template": "Response",
        "act_a": "A_Cancelled",
        "act_b": "O_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Linked offer revocation under Article 15(1): Whenever a consumer withdraws and cancels a credit application, any associated financing proposal must also be revoked.",
    },
    {
        "rule_id": "R12",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(6)",
        "template": "Precedence",
        "act_a": "W_Call after offers",
        "act_b": "A_Validating",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Adequate explanations under Article 5(6): Clarifying product terms with the applicant after an offer is issued must precede formal back-office validation of the file.",
    },
    # --- TIER 2: TEMPORAL & DATA-AWARE CONSTRAINTS (10 RULES: R13 - R22) ---
    {
        "rule_id": "R13",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 8(2)",
        "template": "Response",
        "act_a": "A_Create Application",
        "act_b": "A_Accepted",
        "attr": "case:ApplicationType",
        "op": "==",
        "val": "Limit raise",
        "time_max": None,
        "is_trap": False,
        "description": "Re-assessment on credit limit increase under Article 8(2): Whenever a loan application is opened to increase the existing total credit amount (ApplicationType == 'Limit raise'), updated creditworthiness intake acceptance must subsequently take place.",
    },
    {
        "rule_id": "R14",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 10(2)",
        "template": "Precedence",
        "act_a": "O_Create Offer",
        "act_b": "A_Pending",
        "attr": "OfferedAmount",
        "op": ">",
        "val": 0.0,
        "time_max": None,
        "is_trap": False,
        "description": "Contractual principal specification under Article 10(2)(d): Before an application receives final funding sign-off, a loan offer stating a valid non-zero credit sum (> 0) must have been drafted.",
    },
    {
        "rule_id": "R15",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 14(1)",
        "template": "Precedence",
        "act_a": "O_Sent (mail and online)",
        "act_b": "A_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 14,
        "is_trap": False,
        "description": "Right of withdrawal window under Article 14(1): A consumer may cancel the credit application only within 14 calendar days after receiving the transmitted offer terms.",
    },
    {
        "rule_id": "R16",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 13(1)",
        "template": "Precedence",
        "act_a": "O_Sent (mail and online)",
        "act_b": "O_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 30,
        "is_trap": False,
        "description": "Open-end termination notice window under Article 13(1): Standard termination of an issued loan offer by the consumer may occur only up to one month (30 calendar days) after the offer was communicated.",
    },
    {
        "rule_id": "R17",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "O_Create Offer",
        "act_b": "A_Pending",
        "attr": "CreditScore",
        "op": ">",
        "val": 0,
        "time_max": None,
        "is_trap": False,
        "description": "Creditworthiness scoring prerequisite under Article 8(1): Prior to granting final funding sign-off on an application, the lender must have generated a loan proposal recording a positive applicant credit rating (> 0).",
    },
    {
        "rule_id": "R18",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 5(1)",
        "template": "Precedence",
        "act_a": "O_Create Offer",
        "act_b": "O_Sent (mail and online)",
        "attr": "NumberOfTerms",
        "op": ">",
        "val": 0,
        "time_max": None,
        "is_trap": False,
        "description": "Pre-contractual repayment count under Article 5(1): Prior to delivering a loan proposal to the borrower, the lender must create an offer setting out a positive count of repayment installments (> 0).",
    },
    {
        "rule_id": "R19",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 5(1)",
        "template": "Precedence",
        "act_a": "O_Create Offer",
        "act_b": "A_Pending",
        "attr": "Selected",
        "op": "==",
        "val": True,
        "time_max": None,
        "is_trap": False,
        "description": "Consumer-selected offer prerequisite under Article 5(1): Prior to granting final funding sign-off on an application, the lender must have created a loan proposal marked as selected in line with the borrower's expressed preferences (Selected == True).",
    },
    {
        "rule_id": "R20",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 8(1)",
        "template": "Existence",
        "act_a": "A_Create Application",
        "act_b": None,
        "attr": "case:RequestedAmount",
        "op": ">",
        "val": 0.0,
        "time_max": None,
        "is_trap": False,
        "description": "Creditworthiness intake data under Article 8(1): When opening a credit application, the lender must capture sufficient consumer preference data specifying a positive requested loan size (> 0).",
    },
    {
        "rule_id": "R21",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 5(1)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "MonthlyCost",
        "op": ">",
        "val": 0.0,
        "time_max": None,
        "is_trap": False,
        "description": "Pre-contractual installment disclosure under Article 5(1)(h): Every credit proposal drafted for consumer comparison must specify a positive periodic monthly installment amount (> 0).",
    },
    {
        "rule_id": "R22",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 14(3)",
        "template": "Response",
        "act_a": "A_Cancelled",
        "act_b": "O_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 30,
        "is_trap": False,
        "description": "Post-withdrawal settlement deadline under Article 14(3): Whenever the borrower cancels a credit application, the related credit proposal must subsequently be cancelled within 30 calendar days.",
    },
    # --- TIER 3: ADVERSARIAL SEMANTIC, SCHEMA & TRACE-SAFETY TRAPS (8 BASELESS RULES: R23 - R30) ---
    {
        "rule_id": "R23",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 14(1)",
        "template": "Response",
        "act_a": "O_Accepted",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 14,
        "is_trap": True,
        "trap_scope": "rule",
        "trap_type": "UNSUPPORTED_BY_DIRECTIVE_TEXT",
        "description": "Post-acceptance funding SLA under Article 14(1): Whenever a consumer accepts a finalized credit offer, the creditor must transition the loan into active disbursement approval within 14 calendar days.",
    },
    {
        "rule_id": "R24",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 16(4)",
        "template": "Precedence",
        "act_a": "O_Create Offer",
        "act_b": "A_Pending",
        "attr": "OfferedAmount",
        "op": ">",
        "val": 10000.0,
        "time_max": None,
        "is_trap": True,
        "trap_scope": "rule",
        "trap_type": "UNSUPPORTED_BY_DIRECTIVE_TEXT",
        "description": "Minimum financed principal threshold under Article 16(4): Prior to granting final funding approval on any credit agreement, the lender must have drafted a loan offer specifying a principal exceeding EUR 10,000 (OfferedAmount > 10000).",
    },
    {
        "rule_id": "R25",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 18(2)",
        "template": "Response",
        "act_a": "A_Validating",
        "act_b": "W_Call incomplete files",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 30,
        "is_trap": True,
        "trap_scope": "rule",
        "trap_type": "UNSUPPORTED_BY_DIRECTIVE_TEXT",
        "description": "Post-validation outreach window under Article 18(2): Whenever a credit application enters formal back-office validation, staff outreach regarding incomplete borrower files must take place within 30 calendar days (one month).",
    },
    {
        "rule_id": "R26",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 9(2)",
        "template": "Response",
        "act_a": "A_Denied",
        "act_b": "O_Create Offer",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": True,
        "trap_scope": "rule",
        "trap_type": "UNSUPPORTED_BY_DIRECTIVE_TEXT",
        "description": "Post-rejection offer remediation under Article 9(2): Whenever a credit application is formally rejected, the creditor must subsequently generate a revised credit offer with updated terms for the applicant.",
    },
    {
        "rule_id": "R27",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 16(2)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "EarlyRepaymentCompensationFee",
        "op": "<=",
        "val": 1.0,
        "time_max": None,
        "is_trap": True,
        "trap_scope": "schema",
        "trap_type": "MISSING_LOG_EVIDENCE_PHI_VIOLATION",
        "description": "Early repayment compensation limit under Article 16(2): Every generated loan proposal must record an early repayment compensation fee not exceeding 1.0% of the repaid amount.",
    },
    {
        "rule_id": "R28",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 2(3)",
        "template": "Response",
        "act_a": "O_Sent (mail and online)",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 90,
        "is_trap": True,
        "trap_scope": "rule",
        "trap_type": "UNSUPPORTED_BY_DIRECTIVE_TEXT",
        "description": "Short-term credit activation window under Article 2(3): Whenever pre-contractual offer terms have been sent out to the borrower, final active credit approval must follow within 90 calendar days (three months).",
    },
    {
        "rule_id": "R29",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 5(6)",
        "template": "Response",
        "act_a": "O_Sent (mail and online)",
        "act_b": "W_Call after offers",
        "attr": "case:RequestedAmount",
        "op": ">",
        "val": 0,
        "time_max": None,
        "is_trap": True,
        "trap_scope": "trace",
        "trap_type": "INAPPLICABLE_TRACE_NO_ACTIVATION",
        "description": "Adequate explanations duty under Article 5(6): Whenever a credit proposal involving a positive borrowing request (> 0) has been sent out to the consumer, staff follow-up to provide adequate explanations must subsequently take place.",
    },
    {
        "rule_id": "R30",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 10(2)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "NumberOfTerms",
        "op": ">",
        "val": 0,
        "time_max": None,
        "is_trap": True,
        "trap_scope": "trace",
        "trap_type": "MISSING_LOG_EVIDENCE_PHI_VIOLATION",
        "description": "Contractual duration disclosure under Article 10(2): Any credit proposal generated for a borrower must specify a positive repayment schedule duration (> 0 installments).",
    },
]


ANNEX_I_TEXT = (
    "Annex I, Part II - Additional assumptions for the calculation of the annual percentage rate of charge: "
    "(d) if there is no fixed timetable for repayment, a credit is provided for a period of one year (12 monthly terms); "
    "(g) if no credit ceiling has yet been agreed, that ceiling is assumed to be EUR 1 500; "
    "(h) in the case of an overdraft facility, the credit is drawn down in full and for the whole duration of the credit agreement."
)


def _rule_to_ast_dict(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "article_id": r["article_id"],
        "template_name": r["template"],
        "activation_activity": r["act_a"],
        "target_activity": r["act_b"],
        "activation_attr": r["attr"],
        "activation_op": r["op"],
        "activation_val": r["val"],
        "time_min": 0,
        "time_max": r["time_max"],
        "time_unit": "d",
    }


# Stratified Development vs Held-Out Test Split across all 3 complexity tiers (15 rules each):
# - Development (15 rules): 6 Tier 1 + 5 Tier 2 + 4 Tier 3
# - Held-out Test (15 rules): 6 Tier 1 + 5 Tier 2 + 4 Tier 3
DEV_RULE_IDS = {
    "R01", "R02", "R04", "R07", "R09", "R11",
    "R13", "R15", "R17", "R19", "R20",
    "R23", "R25", "R27", "R29",
}
HELDOUT_TEST_RULE_IDS = {
    "R03", "R05", "R06", "R08", "R10", "R12",
    "R14", "R16", "R18", "R21", "R22",
    "R24", "R26", "R28", "R30",
}


def split_benchmark_rules(
    normative_rules: List[Dict[str, Any]],
    split: str = "all",
) -> List[Dict[str, Any]]:
    """
    Filter rule list by split:
    - split='dev': 15 stratified Development rules (6 Tier 1, 5 Tier 2, 4 Tier 3).
    - split='heldout_test': 15 stratified Held-out Blind Test rules (6 Tier 1, 5 Tier 2, 4 Tier 3).
    - split='all': all 30 rules R01-R30.
    """
    norm_split = split.lower().strip()
    if norm_split == "dev":
        return [r for r in normative_rules if r["rule_id"] in DEV_RULE_IDS]
    if norm_split in ("heldout_test", "test", "heldout"):
        return [r for r in normative_rules if r["rule_id"] in HELDOUT_TEST_RULE_IDS]
    return list(normative_rules)


def build_normative_rule_benchmark(
    chunks_by_id: Dict[str, Dict[str, Any]],
    split: str = "all",
) -> List[Dict[str, Any]]:
    """
    Khởi tạo bộ quy tắc chuẩn gắn kèm đoạn văn bản gốc từ directive_chunks.json
    và nhãn phân tập `dataset_split` theo phân tầng `DEV_RULE_IDS` (R01–R05, R08–R13, R23–R26)
    và `HELDOUT_TEST_RULE_IDS` (15 quy tắc còn lại across all tiers).
    """
    enriched_chunks = dict(chunks_by_id)
    if "Annex I(II)" not in enriched_chunks:
        enriched_chunks["Annex I(II)"] = {
            "article_id": "Annex I(II)",
            "article_title": "Additional assumptions for calculating APR (Annex I Part II)",
            "text": ANNEX_I_TEXT,
            "has_numeric_bound": True,
        }

    initial_llm_errors: Dict[str, Dict[str, Any]] = {
        "R05": {
            "article_id": "Article 5(1)",
            "template_name": "Precedence",
            "activation_activity": "O_Created",
            "target_activity": "O_Send_Offer",
            "time_min": 0,
            "time_max": None,
            "time_unit": "d",
        },
        "R06": {
            "article_id": "Article 5(1)",
            "template_name": "Chain Precedence",
            "activation_activity": "O_Sent (mail and online)",
            "target_activity": "A_Complete",
            "time_min": 0,
            "time_max": None,
            "time_unit": "d",
        },
        "R08": {
            "article_id": "Article 8(1)",
            "template_name": "Response",
            "activation_activity": "A_Validating",
            "target_activity": "W_Validate application",
            "time_min": 0,
            "time_max": None,
            "time_unit": "d",
        },
        "R13": {
            "article_id": "Article 4(2)",
            "template_name": "Precedence",
            "activation_activity": "O_Create Offer",
            "target_activity": "O_Sent (mail and online)",
            "activation_attr": "TotalCreditEUR",
            "activation_op": ">",
            "activation_val": 0.0,
            "time_min": 0,
            "time_max": None,
            "time_unit": "d",
        },
        "R15": {
            "article_id": "Article 14(1)",
            "template_name": "Response",
            "activation_activity": "O_Sent (mail and online)",
            "target_activity": "A_Cancelled",
            "time_min": 0,
            "time_max": 30,
            "time_unit": "d",
        },
    }

    rules_out: List[Dict[str, Any]] = []
    for raw_r in BENCHMARK_RULES:
        r = dict(raw_r)
        art_id = r["article_id"]
        chunk = enriched_chunks.get(
            art_id,
            {
                "article_id": art_id,
                "article_title": art_id,
                "text": r["description"],
                "has_numeric_bound": r["time_max"] is not None or r["val"] is not None,
            },
        )
        ast_dict = _rule_to_ast_dict(r)
        r["dataset_split"] = "dev" if r["rule_id"] in DEV_RULE_IDS else "heldout_test"
        r["retrieved_chunk"] = chunk
        r["is_baseless_trap"] = bool(r["is_trap"])
        r["gold_ast"] = None if r["is_trap"] else ast_dict
        r["raw_attempt_1"] = initial_llm_errors.get(r["rule_id"], ast_dict)
        r["repaired_attempt_2"] = ast_dict
        rules_out.append(r)

    return split_benchmark_rules(rules_out, split=split)


def load_annotated_trace_benchmark(
    annotations_path: str,
    df_propagated: pd.DataFrame,
    normative_rules: List[Dict[str, Any]],
    split: str = "all",
) -> List[Dict[str, Any]]:
    """
    Cơ chế nạp nhãn thực tế từ file gán nhãn độc lập (`bpic2017_annotated_traces.json` hoặc `.csv`):
    Mỗi bản ghi gán nhãn chứa:
      - `benchmark_id` (tùy chọn)
      - `case_id` (mã hồ sơ thực trong `BPI Challenge 2017.xes` hoặc mảng `events` đã trích xuất)
      - `rule_id` (`R01`..`R30`)
      - `ground_truth_label` (`ENTAILED` | `CONTRADICTED` | `BASELESS`)
      - `annotator_notes` / `trace_origin` (tùy chọn)
    Hàm tự động lọc theo `split` ('dev': 15 quy tắc `DEV_RULE_IDS`, 'heldout_test': 15 quy tắc `HELDOUT_TEST_RULE_IDS`, hoặc 'all').
    """
    ann_file = Path(annotations_path)
    if not ann_file.exists():
        raise FileNotFoundError(f"Annotated benchmark file not found: {annotations_path}")

    active_rules = split_benchmark_rules(normative_rules, split=split)
    rules_by_id = {r["rule_id"]: r for r in active_rules}

    if ann_file.suffix.lower() == ".csv":
        ann_records = pd.read_csv(ann_file).to_dict(orient="records")
    else:
        with open(ann_file, "r", encoding="utf-8") as f:
            ann_records = json.load(f)

    # Lập chỉ mục các case_id cần lấy từ df_propagated
    needed_cids = {str(rec.get("case_id", "")) for rec in ann_records if rec.get("case_id")}
    grouped_cases: Dict[str, pd.DataFrame] = {}
    if needed_cids and not df_propagated.empty:
        sub_df = df_propagated[df_propagated["case:concept:name"].astype(str).isin(needed_cids)]
        grouped_cases = {
            str(cid): grp.sort_values("time:timestamp").reset_index(drop=True)
            for cid, grp in sub_df.groupby("case:concept:name", sort=False)
        }

    loaded_items: List[Dict[str, Any]] = []
    for idx, rec in enumerate(ann_records, start=1):
        rid = str(rec.get("rule_id", "")).strip()
        if rid not in rules_by_id:
            continue
        rule_meta = rules_by_id[rid]

        if "events" in rec and isinstance(rec["events"], list) and rec["events"]:
            case_df = pd.DataFrame(rec["events"])
            if "time:timestamp" in case_df.columns:
                case_df["time:timestamp"] = pd.to_datetime(case_df["time:timestamp"], format="ISO8601")
        else:
            cid = str(rec.get("case_id", ""))
            if cid not in grouped_cases:
                continue
            case_df = grouped_cases[cid]

        loaded_items.append(
            {
                "benchmark_id": str(rec.get("benchmark_id") or f"ANN-{idx:04d}"),
                "rule_id": rid,
                "dataset_split": rule_meta["dataset_split"],
                "rule_meta": rule_meta,
                "retrieved_chunk": rule_meta["retrieved_chunk"],
                "test_case_df": case_df,
                "ground_truth_label": str(rec["ground_truth_label"]).upper().strip(),
                "trace_origin": str(rec.get("trace_origin") or "HUMAN_ANNOTATED_BPIC2017"),
            }
        )

    return loaded_items


def build_stratified_trace_benchmark(
    df_propagated: pd.DataFrame,
    df_raw: pd.DataFrame,
    normative_rules: List[Dict[str, Any]],
    target_total_items: int = 1200,
    split: str = "all",
    annotations_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Xây dựng hoặc nạp Bộ Hồ sơ Kiểm thử Phân tầng (Stratified Trace Benchmark) hỗ trợ tách tập
    `split` ('dev': 15 quy tắc `DEV_RULE_IDS`, 'heldout_test': 15 quy tắc `HELDOUT_TEST_RULE_IDS`, hoặc 'all'):
    - Nếu `annotations_path` được cung cấp (hoặc tệp `data/processed/bpic2017_annotated_traces.json` tồn tại),
      ưu tiên nạp trực tiếp nhãn thực tế từ file gán nhãn độc lập (`load_annotated_trace_benchmark`).
    - Nếu chưa có file gán nhãn thủ công (ví dụ khi chạy unit test), trích xuất phân tầng từ `df_propagated`
      và lọc theo đúng tập `split`.
    """
    default_ann_path = Path("data/processed/bpic2017_annotated_traces.json")
    resolved_ann_path = annotations_path or (str(default_ann_path) if default_ann_path.exists() else None)
    if resolved_ann_path and Path(resolved_ann_path).exists():
        return load_annotated_trace_benchmark(
            annotations_path=resolved_ann_path,
            df_propagated=df_propagated,
            normative_rules=normative_rules,
            split=split,
        )

    norm_split = split.lower().strip()
    if norm_split == "all":
        total_per_class = target_total_items // 3
        dev_per_class = total_per_class // 2
        test_per_class = total_per_class - dev_per_class
        if dev_per_class > 0 and test_per_class > 0:
            dev_items = build_stratified_trace_benchmark(
                df_propagated=df_propagated,
                df_raw=df_raw,
                normative_rules=normative_rules,
                target_total_items=dev_per_class * 3,
                split="dev",
                annotations_path=annotations_path,
            )
            test_items = build_stratified_trace_benchmark(
                df_propagated=df_propagated,
                df_raw=df_raw,
                normative_rules=normative_rules,
                target_total_items=test_per_class * 3,
                split="heldout_test",
                annotations_path=annotations_path,
            )
            combined_ent = [x for x in dev_items + test_items if x["ground_truth_label"] == "ENTAILED"]
            combined_con = [x for x in dev_items + test_items if x["ground_truth_label"] == "CONTRADICTED"]
            combined_bas = [x for x in dev_items + test_items if x["ground_truth_label"] == "BASELESS"]
            for i, it in enumerate(combined_ent, 1):
                it["benchmark_id"] = f"ENT-{i:04d}"
            for i, it in enumerate(combined_con, 1):
                it["benchmark_id"] = f"CON-{i:04d}"
            for i, it in enumerate(combined_bas, 1):
                it["benchmark_id"] = f"BAS-{i:04d}"
            return combined_ent + combined_con + combined_bas

    per_class_quota = target_total_items // 3
    active_rules = split_benchmark_rules(normative_rules, split=split)
    active_norm = [r for r in active_rules if not r.get("is_trap") and not r.get("is_baseless_trap")]
    if not active_norm:
        active_norm = [r for r in normative_rules if not r.get("is_trap") and not r.get("is_baseless_trap")]

    trap_rules = [r for r in active_rules if r.get("is_trap") or r.get("is_baseless_trap")]
    if not trap_rules:
        fallback_traps = []
        enriched_chunks = {
            r["article_id"]: r.get("retrieved_chunk")
            for r in normative_rules
            if isinstance(r.get("retrieved_chunk"), dict)
        }
        for raw_r in BENCHMARK_RULES:
            if raw_r.get("is_trap"):
                r = dict(raw_r)
                art_id = r["article_id"]
                chunk = enriched_chunks.get(
                    art_id,
                    {
                        "article_id": art_id,
                        "article_title": art_id,
                        "text": r["description"],
                        "has_numeric_bound": r.get("time_max") is not None or r.get("val") is not None,
                    },
                )
                r["dataset_split"] = "dev" if r["rule_id"] in DEV_RULE_IDS else "heldout_test"
                r["retrieved_chunk"] = chunk
                r["is_baseless_trap"] = True
                r["gold_ast"] = None
                ast_dict = _rule_to_ast_dict(r)
                r["raw_attempt_1"] = ast_dict
                r["repaired_attempt_2"] = ast_dict
                fallback_traps.append(r)
        trap_rules = fallback_traps

    candidate_gold_asts = {
        r["rule_id"]: DeclareConstraintAST(**_rule_to_ast_dict(r))
        for r in active_norm
    }

    # Index cases across df_propagated; keep DEV and HELDOUT_TEST case-disjoint on full datasets (>= 200 cases)
    all_cids = df_propagated["case:concept:name"].drop_duplicates().tolist()
    norm_s = split.lower().strip()
    if len(all_cids) >= 200:
        half = len(all_cids) // 2
        if norm_s == "dev":
            unique_cids = all_cids[:half]
        elif norm_s in ("heldout_test", "test", "heldout"):
            unique_cids = all_cids[half:]
        else:
            unique_cids = all_cids[:5000]
    else:
        unique_cids = all_cids[:5000]
    sub_prop = df_propagated[df_propagated["case:concept:name"].isin(unique_cids)]
    grouped_prop = {
        cid: grp.sort_values("time:timestamp").reset_index(drop=True)
        for cid, grp in sub_prop.groupby("case:concept:name", sort=False)
    }

    entailed_items: List[Dict[str, Any]] = []
    contradicted_items: List[Dict[str, Any]] = []
    baseless_items: List[Dict[str, Any]] = []

    strict_unique_cids = len(grouped_prop) >= max(200, per_class_quota * 2)
    n_norm = max(len(active_norm), 1)
    base_q, rem_q = divmod(per_class_quota, n_norm)
    ent_targets = {r["rule_id"]: base_q + (1 if i < rem_q else 0) for i, r in enumerate(active_norm)}
    con_targets = {r["rule_id"]: base_q + (1 if i < rem_q else 0) for i, r in enumerate(active_norm)}

    def _scarcity_rank(rule_dict: Dict[str, Any]) -> Tuple[int, str]:
        tpl = rule_dict.get("template", "")
        acts_str = f"{rule_dict.get('act_a') or ''} {rule_dict.get('act_b') or ''}"
        if rule_dict.get("time_max") is not None:
            return (0, rule_dict["rule_id"])
        if tpl == "Not Co-Existence":
            return (1, rule_dict["rule_id"])
        if any(tok in acts_str for tok in ("A_Cancelled", "O_Accepted", "W_Call after offers", "O_Cancelled")):
            return (2, rule_dict["rule_id"])
        if rule_dict.get("attr") is not None:
            return (3, rule_dict["rule_id"])
        return (4, rule_dict["rule_id"])

    def _is_non_vacuous_match(case_df: pd.DataFrame, acts: set, gast: DeclareConstraintAST) -> Tuple[bool, Optional[bool]]:
        tpl = gast.template_name
        act_a = gast.activation_activity
        act_b = gast.target_activity
        if tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
            if act_b not in acts:
                return False, None
            if act_a not in acts:
                is_c, _ = check_single_trace_semantics(case_df, gast)
                return (not is_c), (False if not is_c else None)
        elif tpl in ("Response", "Alternate Response", "Chain Response"):
            if act_a not in acts:
                return False, None
        elif tpl == "Not Co-Existence":
            if act_a not in acts and act_b not in acts:
                return False, None
        elif tpl in ("Existence", "Absence"):
            if act_a not in acts:
                return False, None
        is_comp, _ = check_single_trace_semantics(case_df, gast)
        return True, is_comp

    used_real_cids: set[str] = set()
    ent_counts = {r["rule_id"]: 0 for r in active_norm}
    con_counts = {r["rule_id"]: 0 for r in active_norm}
    rule_ent_dfs: Dict[str, List[pd.DataFrame]] = {r["rule_id"]: [] for r in active_norm}
    rules_ordered_scarce = sorted(active_norm, key=_scarcity_rank)

    if strict_unique_cids:
        # Pass 1A: Reserve 1 real BPIC 2017 trace with `act_a in acts and act_b not in acts` per Precedence-family rule
        # (when target quota >= 4) so wrongly reversing Precedence -> Response cannot score 100% on ENTAILED.
        for r in rules_ordered_scarce:
            rid = r["rule_id"]
            gast = candidate_gold_asts[rid]
            if gast.template_name not in ("Precedence", "Alternate Precedence", "Chain Precedence"):
                continue
            if ent_targets[rid] < 4:
                continue
            act_a = gast.activation_activity
            act_b = gast.target_activity
            for cid, case_df in grouped_prop.items():
                if cid in used_real_cids:
                    continue
                acts = set(case_df["concept:name"])
                if act_a in acts and act_b and act_b not in acts:
                    is_comp, _ = check_single_trace_semantics(case_df, gast)
                    if is_comp:
                        used_real_cids.add(cid)
                        ent_counts[rid] += 1
                        rule_ent_dfs[rid].append(case_df)
                        entailed_items.append({
                            "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
                            "rule_id": rid,
                            "rule_meta": r,
                            "retrieved_chunk": r["retrieved_chunk"],
                            "test_case_df": case_df,
                            "ground_truth_label": "ENTAILED",
                            "trace_origin": f"BPIC2017_REAL_COMPLIANT_A_ONLY_{rid}",
                        })
                        break

        # Pass 1A-bis: For Not Co-Existence(A, B) rules, reserve up to 2 real A-only traces (A present, B absent)
        # so ENTAILED covers both A-only and B-only compliant sides rather than collapsing onto only B-side co-occurring events.
        for r in rules_ordered_scarce:
            rid = r["rule_id"]
            gast = candidate_gold_asts[rid]
            if gast.template_name != "Not Co-Existence" or ent_targets[rid] < 4:
                continue
            act_a = gast.activation_activity
            act_b = gast.target_activity
            reserved_a_only = 0
            for cid, case_df in grouped_prop.items():
                if reserved_a_only >= 2 or ent_counts[rid] >= ent_targets[rid]:
                    break
                if cid in used_real_cids:
                    continue
                acts = set(case_df["concept:name"])
                if act_a in acts and act_b and act_b not in acts:
                    is_comp, _ = check_single_trace_semantics(case_df, gast)
                    if is_comp:
                        used_real_cids.add(cid)
                        ent_counts[rid] += 1
                        reserved_a_only += 1
                        rule_ent_dfs[rid].append(case_df)
                        entailed_items.append({
                            "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
                            "rule_id": rid,
                            "rule_meta": r,
                            "retrieved_chunk": r["retrieved_chunk"],
                            "test_case_df": case_df,
                            "ground_truth_label": "ENTAILED",
                            "trace_origin": f"BPIC2017_REAL_COMPLIANT_A_ONLY_{rid}",
                        })

        # Pass 1A-ter: For directional prohibitions (Not Response / Not Precedence), inject up to 2 compliant
        # B-before-A boundary traces (if no real B-before-A case exists) so stricter Not Co-Existence fails on ENTAILED.
        distinct_prop_list = list(grouped_prop.items())
        for r in rules_ordered_scarce:
            rid = r["rule_id"]
            gast = candidate_gold_asts[rid]
            if gast.template_name not in ("Not Response", "Not Precedence") or ent_targets[rid] < 4:
                continue
            act_a = gast.activation_activity
            act_b = gast.target_activity
            if not act_b:
                continue
            b_before_a_added = 0
            for cid, case_df in distinct_prop_list:
                if b_before_a_added >= 2 or ent_counts[rid] >= ent_targets[rid]:
                    break
                acts = set(case_df["concept:name"])
                if act_a not in acts:
                    continue
                cand_df = case_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
                if act_b not in acts:
                    t_min = cand_df["time:timestamp"].min()
                    new_b = cand_df.iloc[0].copy()
                    new_b["concept:name"] = act_b
                    new_b["time:timestamp"] = t_min - pd.Timedelta(hours=1)
                    cand_df = pd.concat([pd.DataFrame([new_b]), cand_df], ignore_index=True)
                    cand_df = cand_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
                is_comp, _ = check_single_trace_semantics(cand_df, gast)
                if is_comp:
                    t_first_a = cand_df.loc[cand_df["concept:name"] == act_a, "time:timestamp"].min()
                    has_b_before_a = bool(((cand_df["concept:name"] == act_b) & (cand_df["time:timestamp"] < t_first_a)).any())
                    if has_b_before_a:
                        seed_b4a = (abs(hash(f"{cid}_b_before_a_{rid}_{b_before_a_added}")) % 900000000) + 100000000
                        cand_df["case:concept:name"] = f"Application_{seed_b4a}"
                        ent_counts[rid] += 1
                        b_before_a_added += 1
                        rule_ent_dfs[rid].append(cand_df)
                        entailed_items.append({
                            "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
                            "rule_id": rid,
                            "rule_meta": r,
                            "retrieved_chunk": r["retrieved_chunk"],
                            "test_case_df": cand_df,
                            "ground_truth_label": "ENTAILED",
                            "trace_origin": f"SYNTHETIC_COMPLIANT_B_BEFORE_A_{rid}",
                        })

        # Pass 1B: Assign at most ONE ENTAILED item per real trace (scarce rules get priority first)
        # Guaranteeing balanced coverage across all rules AND 100% unique Case IDs.
        for cid, case_df in grouped_prop.items():
            if cid in used_real_cids:
                continue
            if len(entailed_items) >= per_class_quota:
                break
            needing_ent = [r for r in rules_ordered_scarce if ent_counts[r["rule_id"]] < ent_targets[r["rule_id"]]]
            if not needing_ent:
                break
            acts = set(case_df["concept:name"])
            for r in needing_ent:
                rid = r["rule_id"]
                ok_act, is_comp = _is_non_vacuous_match(case_df, acts, candidate_gold_asts[rid])
                if ok_act and is_comp is True:
                    used_real_cids.add(cid)
                    ent_counts[rid] += 1
                    rule_ent_dfs[rid].append(case_df)
                    entailed_items.append({
                        "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
                        "rule_id": rid,
                        "rule_meta": r,
                        "retrieved_chunk": r["retrieved_chunk"],
                        "test_case_df": case_df,
                        "ground_truth_label": "ENTAILED",
                        "trace_origin": f"BPIC2017_REAL_COMPLIANT_{rid}",
                    })
                    break

        # Pass 2: Scan up to 1,500 UNUSED real traces for natural CONTRADICTED items (scarce rules first)
        unused_scan_count = 0
        for cid, case_df in grouped_prop.items():
            if cid in used_real_cids:
                continue
            unused_scan_count += 1
            if len(contradicted_items) >= per_class_quota or unused_scan_count > 1500:
                break
            needing_con = sorted(
                [r for r in rules_ordered_scarce if con_counts[r["rule_id"]] < con_targets[r["rule_id"]]],
                key=lambda r: (con_counts[r["rule_id"]], _scarcity_rank(r)),
            )
            if not needing_con:
                break
            acts = set(case_df["concept:name"])
            for r in needing_con:
                rid = r["rule_id"]
                ok_act, is_comp = _is_non_vacuous_match(case_df, acts, candidate_gold_asts[rid])
                if ok_act and is_comp is False:
                    used_real_cids.add(cid)
                    con_counts[rid] += 1
                    contradicted_items.append({
                        "benchmark_id": f"CON-{len(contradicted_items) + 1:04d}",
                        "rule_id": rid,
                        "rule_meta": r,
                        "retrieved_chunk": r["retrieved_chunk"],
                        "test_case_df": case_df,
                        "ground_truth_label": "CONTRADICTED",
                        "trace_origin": f"BPIC2017_REAL_VIOLATION_{rid}",
                    })
                    break
    else:
        # Small synthetic logs (e.g. unit tests with 4-10 cases): reuse traces cleanly per rule quota
        ent_cands_small: Dict[str, List[pd.DataFrame]] = {r["rule_id"]: [] for r in active_norm}
        con_cands_small: Dict[str, List[pd.DataFrame]] = {r["rule_id"]: [] for r in active_norm}
        for _, case_df in grouped_prop.items():
            acts = set(case_df["concept:name"])
            for r in active_norm:
                rid = r["rule_id"]
                ok_act, is_comp = _is_non_vacuous_match(case_df, acts, candidate_gold_asts[rid])
                if not ok_act:
                    continue
                if is_comp is True:
                    ent_cands_small[rid].append(case_df)
                elif is_comp is False:
                    con_cands_small[rid].append(case_df)
        for r in active_norm:
            rid = r["rule_id"]
            if ent_cands_small[rid]:
                rule_ent_dfs[rid] = list(ent_cands_small[rid])
                for k in range(ent_targets[rid]):
                    ent_counts[rid] += 1
                    entailed_items.append({
                        "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
                        "rule_id": rid,
                        "rule_meta": r,
                        "retrieved_chunk": r["retrieved_chunk"],
                        "test_case_df": ent_cands_small[rid][k % len(ent_cands_small[rid])],
                        "ground_truth_label": "ENTAILED",
                        "trace_origin": f"BPIC2017_REAL_COMPLIANT_{rid}",
                    })
            for cdf in con_cands_small[rid][: con_targets[rid]]:
                con_counts[rid] += 1
                contradicted_items.append({
                    "benchmark_id": f"CON-{len(contradicted_items) + 1:04d}",
                    "rule_id": rid,
                    "rule_meta": r,
                    "retrieved_chunk": r["retrieved_chunk"],
                    "test_case_df": cdf,
                    "ground_truth_label": "CONTRADICTED",
                    "trace_origin": f"BPIC2017_REAL_VIOLATION_{rid}",
                })

    base_cases_by_rule = {rid: dfs[0] for rid, dfs in rule_ent_dfs.items() if dfs}
    base_compliant_df = (
        entailed_items[0]["test_case_df"]
        if entailed_items
        else df_propagated.iloc[:15].copy()
    )

    while len(entailed_items) < per_class_quota:
        r_choice = active_norm[len(entailed_items) % len(active_norm)]
        rid = r_choice["rule_id"]
        chosen_df = base_cases_by_rule.get(rid, base_compliant_df)
        entailed_items.append({
            "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
            "rule_id": rid,
            "rule_meta": r_choice,
            "retrieved_chunk": r_choice["retrieved_chunk"],
            "test_case_df": chosen_df,
            "ground_truth_label": "ENTAILED",
            "trace_origin": f"BPIC2017_COMPLIANT_{rid}",
        })

    def _sample_near_boundary_violation_value(
        op: Optional[str],
        val: Any,
        seed_num: int,
    ) -> Any:
        if isinstance(val, bool):
            return not bool(val)
        if isinstance(val, str):
            return "__INVALID_STR_VAL__" if op == "==" else val
        try:
            num_val = float(val)
        except (TypeError, ValueError):
            return 0.0
        if op == ">":
            if num_val <= 0.0:
                return 0.0
            if num_val < 50.0:
                step = float(1 + (seed_num % max(1, min(4, int(num_val)))))
                return max(0.0, num_val - step)
            if num_val < 1000.0:
                return max(0.0, num_val - float(10 + (seed_num % 7) * 5))
            return max(0.0, num_val - float(500 + (seed_num % 7) * 500))
        if op == ">=":
            if num_val <= 0.0:
                return 0.0
            step = 1.0 if num_val < 50.0 else (float(10 + (seed_num % 5) * 10) if num_val < 1000.0 else float(250 + (seed_num % 5) * 250))
            return max(0.0, num_val - step)
        if op in ("<", "<="):
            step = 1.0 if num_val < 50.0 else (float(10 + (seed_num % 5) * 10) if num_val < 1000.0 else float(500 + (seed_num % 9) * 500))
            return num_val + step
        return num_val + 1.0

    def _realistic_offset(seed_num: int, min_minutes: int = 19, span_minutes: int = 135) -> pd.Timedelta:
        mins = min_minutes + (seed_num % span_minutes)
        secs = 7 + ((seed_num // 13) % 49)
        return pd.Timedelta(minutes=mins, seconds=secs)

    # Supplement CONTRADICTED strictly for rules with insufficient natural violations via counterfactual fault injection
    rules_needing_con: List[Dict[str, Any]] = []
    for r in active_norm:
        deficit = con_targets[r["rule_id"]] - con_counts[r["rule_id"]]
        for _ in range(max(deficit, 0)):
            rules_needing_con.append(r)
    if not rules_needing_con:
        rules_needing_con = list(active_norm)
    con_fill_idx = 0
    while len(contradicted_items) < per_class_quota:
        idx = len(contradicted_items)
        inj_rule = rules_needing_con[con_fill_idx % len(rules_needing_con)]
        con_fill_idx += 1
        rid = inj_rule["rule_id"]
        gast = candidate_gold_asts[rid]
        tpl = gast.template_name
        act_a = gast.activation_activity
        act_b = gast.target_activity

        rule_cand_list = rule_ent_dfs.get(rid, [])
        if rule_cand_list:
            base_df = rule_cand_list[con_fill_idx % len(rule_cand_list)].copy()
        else:
            base_df = base_cases_by_rule.get(rid, base_compliant_df).copy()
        injected_df = base_df.copy()
        orig_cid = str(base_df["case:concept:name"].iloc[0])
        seed_num = (abs(hash(f"{orig_cid}_{idx}_{con_fill_idx}")) % 900000000) + 100000000
        injected_df["case:concept:name"] = f"Application_{seed_num}"

        if tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
            mode_idx = con_counts[rid]
            injected_done = False

            # Ensure act_b exists in trace so Precedence can actually trigger
            if act_b not in set(injected_df["concept:name"]):
                new_row = injected_df.iloc[-1].copy()
                new_row["concept:name"] = act_b
                new_row["time:timestamp"] = new_row["time:timestamp"] + _realistic_offset(seed_num)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row])], ignore_index=True)

            if gast.activation_attr:
                attr_col = gast.activation_attr
                if attr_col in injected_df.columns and injected_df[attr_col].isna().all():
                    injected_df[attr_col] = 750.0 if attr_col == "CreditScore" else 100.0

            # Mode A (Tier 2 data-aware Precedence, round % 3 == 0): violate attribute guard while preserving A -> B order
            if (
                tpl in ("Precedence", "Alternate Precedence")
                and gast.activation_attr
                and mode_idx % 3 == 0
                and act_a in set(injected_df["concept:name"])
            ):
                cand_df = injected_df.copy()
                bad_val = _sample_near_boundary_violation_value(gast.activation_op, gast.activation_val, seed_num)
                if gast.activation_attr in ("case:RequestedAmount", "RequestedAmount"):
                    cand_df["case:RequestedAmount"] = bad_val
                    if "RequestedAmount" in cand_df.columns:
                        cand_df["RequestedAmount"] = bad_val
                else:
                    cand_df[gast.activation_attr] = bad_val
                is_c_attr, _ = check_single_trace_semantics(cand_df, gast)
                if not is_c_attr:
                    injected_df = cand_df
                    injected_done = True

            # Mode B (Chain Precedence, even rounds): insert an intervening event between A and B
            # so Precedence(A,B) falsely accepts while Chain Precedence(A,B) detects the direct-adjacency break.
            if (
                not injected_done
                and tpl == "Chain Precedence"
                and mode_idx % 2 == 0
                and act_a in set(injected_df["concept:name"])
            ):
                cand_df = injected_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
                non_ab_idxs = cand_df.index[~cand_df["concept:name"].isin([act_a, act_b])].tolist()
                if non_ab_idxs:
                    a_idxs = cand_df.index[cand_df["concept:name"] == act_a].tolist()
                    b_idxs = cand_df.index[cand_df["concept:name"] == act_b].tolist()
                    # Insert a non-(A,B) filler between every direct A->B pair
                    new_rows = []
                    filler_row = cand_df.loc[non_ab_idxs[0]].copy()
                    for b_i in b_idxs:
                        prev_rows = [ai for ai in a_idxs if ai < b_i]
                        if prev_rows:
                            a_i = prev_rows[-1]
                            t_a = cand_df.at[a_i, "time:timestamp"]
                            t_b = cand_df.at[b_i, "time:timestamp"]
                            if t_b <= t_a:
                                cand_df.at[b_i, "time:timestamp"] = t_a + pd.Timedelta(seconds=4)
                                t_b = cand_df.at[b_i, "time:timestamp"]
                            f_copy = filler_row.copy()
                            f_copy["time:timestamp"] = t_a + (t_b - t_a) / 2
                            new_rows.append(f_copy)
                    if new_rows:
                        cand_df = (
                            pd.concat([cand_df, pd.DataFrame(new_rows)], ignore_index=True)
                            .sort_values("time:timestamp", kind="mergesort")
                            .reset_index(drop=True)
                        )
                        is_c_gap, _ = check_single_trace_semantics(cand_df, gast)
                        if not is_c_gap:
                            injected_df = cand_df
                            injected_done = True

            # Mode C (Precedence / Alternate Precedence):
            # ORDER_INVERSION — move first act_b BEFORE first act_a while keeping act_a (and valid attrs) intact.
            # This catches wrong target_activity substitutions and unary Existence collapses on data-aware rules.
            order_inv_turn = (mode_idx % 3 == 1) if gast.activation_attr else (mode_idx % 2 == 0)
            if (
                not injected_done
                and tpl in ("Precedence", "Alternate Precedence")
                and order_inv_turn
                and act_a in set(injected_df["concept:name"])
            ):
                cand_df = injected_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
                t_first_a = cand_df.loc[cand_df["concept:name"] == act_a, "time:timestamp"].min()
                t_min_trace = cand_df["time:timestamp"].min()
                early_t = min(t_first_a, t_min_trace) - pd.Timedelta(hours=1)
                first_b_idx = cand_df.index[cand_df["concept:name"] == act_b].tolist()[0]
                cand_df.at[first_b_idx, "time:timestamp"] = early_t
                cand_df = cand_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
                is_c_inv, _ = check_single_trace_semantics(cand_df, gast)
                if not is_c_inv:
                    injected_df = cand_df
                    injected_done = True

            # Fallback / Odd rounds: delete act_a (MISSING_PREREQUISITE)
            if not injected_done:
                injected_df = injected_df[injected_df["concept:name"] != act_a].reset_index(drop=True)
        elif tpl in ("Response", "Alternate Response", "Chain Response"):
            if act_a not in set(injected_df["concept:name"]):
                new_row = injected_df.iloc[-1].copy()
                new_row["concept:name"] = act_a
                new_row["time:timestamp"] = new_row["time:timestamp"] + _realistic_offset(seed_num)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row])], ignore_index=True)
            if gast.activation_attr and gast.activation_val is not None:
                attr_col = gast.activation_attr
                if attr_col not in injected_df.columns:
                    injected_df[attr_col] = None
                if gast.activation_op == "==":
                    injected_df.loc[injected_df["concept:name"] == act_a, attr_col] = gast.activation_val
                    if attr_col.startswith("case:"):
                        injected_df[attr_col] = gast.activation_val
                elif gast.activation_op in (">", ">="):
                    try:
                        injected_df.loc[injected_df["concept:name"] == act_a, attr_col] = float(gast.activation_val) + 100.0
                    except (ValueError, TypeError):
                        pass
            injected_df = injected_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
            if tpl == "Chain Response" and gast.time_max is None and (con_counts[rid] % 2 == 1) and act_b in set(injected_df["concept:name"]):
                idx_a_list = injected_df.index[injected_df["concept:name"] == act_a].tolist()
                if idx_a_list:
                    ia = idx_a_list[0]
                    t_a = injected_df.loc[ia, "time:timestamp"]
                    other_acts = [c for c in injected_df["concept:name"].tolist() if c not in (act_a, act_b)]
                    gap_row = injected_df.loc[ia].copy()
                    gap_row["concept:name"] = other_acts[seed_num % len(other_acts)] if other_acts else "W_Complete application"
                    gap_row["time:timestamp"] = t_a + pd.Timedelta(seconds=5 + (seed_num % 11))
                    # Shift any events strictly after t_a forward so gap sits immediately after act_a
                    after_mask = injected_df.index > ia
                    if after_mask.any():
                        injected_df.loc[after_mask, "time:timestamp"] = injected_df.loc[after_mask, "time:timestamp"] + pd.Timedelta(seconds=20 + (seed_num % 15))
                    injected_df = pd.concat([injected_df, pd.DataFrame([gap_row])], ignore_index=True)
                    injected_df = injected_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
            elif gast.time_max is not None:
                if act_b in set(injected_df["concept:name"]):
                    mask_b = injected_df["concept:name"] == act_b
                    a_mask = injected_df["concept:name"] == act_a
                    t_anchor_a = (
                        injected_df.loc[a_mask, "time:timestamp"].max()
                        if a_mask.any()
                        else injected_df["time:timestamp"].min()
                    )
                    u_norm = str(getattr(gast, "time_unit", None) or "d").strip().lower()
                    u_scale = {"s": 1.0 / 86400.0, "sec": 1.0 / 86400.0, "m": 1.0 / 1440.0, "min": 1.0 / 1440.0, "h": 1.0 / 24.0, "hr": 1.0 / 24.0, "hour": 1.0 / 24.0, "hours": 1.0 / 24.0, "d": 1.0, "day": 1.0, "days": 1.0, "w": 7.0, "wk": 7.0, "week": 7.0, "weeks": 7.0, "month": 30.0, "months": 30.0}.get(u_norm, 1.0)
                    limit_days = float(gast.time_max) * u_scale
                    extra_days = float(2 + (seed_num % 5)) if limit_days >= 1.0 else max(0.5, limit_days * 0.5)
                    target_ts = t_anchor_a + pd.Timedelta(
                        days=limit_days + extra_days,
                        hours=1 + (seed_num % 7),
                        minutes=3 + ((seed_num // 7) % 47),
                        seconds=1 + ((seed_num // 17) % 53),
                    )
                    if target_ts.weekday() >= 5:
                        target_ts = target_ts + pd.Timedelta(days=7 - target_ts.weekday())
                    b_indices = injected_df.index[mask_b].tolist()
                    for k_b, bi in enumerate(b_indices):
                        injected_df.at[bi, "time:timestamp"] = target_ts + pd.Timedelta(seconds=k_b * 17)
                    injected_df = injected_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
                else:
                    injected_df = injected_df[injected_df["concept:name"] != act_b].reset_index(drop=True)
            else:
                injected_df = injected_df[injected_df["concept:name"] != act_b].reset_index(drop=True)
        elif tpl in ("Not Response", "Not Precedence"):
            if act_a not in set(injected_df["concept:name"]):
                new_a = injected_df.iloc[0].copy()
                new_a["concept:name"] = act_a
                new_a["time:timestamp"] = injected_df["time:timestamp"].min() - _realistic_offset(seed_num)
                injected_df = pd.concat([pd.DataFrame([new_a]), injected_df], ignore_index=True)
                injected_df = injected_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
            t_first_a = injected_df.loc[injected_df["concept:name"] == act_a, "time:timestamp"].min()
            has_b_after_a = bool(
                ((injected_df["concept:name"] == act_b) & (injected_df["time:timestamp"] > t_first_a)).any()
            )
            if not has_b_after_a:
                new_b = injected_df.iloc[-1].copy()
                new_b["concept:name"] = act_b
                delta_h = _realistic_offset(seed_num + 31)
                t_cand = t_first_a + delta_h
                max_t = injected_df["time:timestamp"].max()
                if gast.time_max is None and max_t > t_cand:
                    t_cand = max_t + delta_h
                new_b["time:timestamp"] = t_cand
                injected_df = pd.concat([injected_df, pd.DataFrame([new_b])], ignore_index=True)
                injected_df = injected_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
        elif tpl == "Not Co-Existence":
            if rule_cand_list and act_b:
                a_only_cands = [
                    d for d in rule_cand_list
                    if act_a in set(d["concept:name"]) and act_b not in set(d["concept:name"])
                ]
                b_only_cands = [
                    d for d in rule_cand_list
                    if act_b in set(d["concept:name"]) and act_a not in set(d["concept:name"])
                ]
                if con_counts[rid] % 2 == 0 and a_only_cands:
                    injected_df = a_only_cands[(con_counts[rid] // 2) % len(a_only_cands)].copy()
                    injected_df["case:concept:name"] = f"Application_{seed_num}"
                elif b_only_cands:
                    injected_df = b_only_cands[con_counts[rid] % len(b_only_cands)].copy()
                    injected_df["case:concept:name"] = f"Application_{seed_num}"
            if act_a not in set(injected_df["concept:name"]):
                new_row_a = injected_df.iloc[-1].copy()
                new_row_a["concept:name"] = act_a
                new_row_a["time:timestamp"] = new_row_a["time:timestamp"] + _realistic_offset(seed_num)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row_a])], ignore_index=True)
            if act_b not in set(injected_df["concept:name"]):
                new_row_b = injected_df.iloc[-1].copy()
                new_row_b["concept:name"] = act_b
                new_row_b["time:timestamp"] = new_row_b["time:timestamp"] + _realistic_offset(seed_num + 97, min_minutes=45, span_minutes=180)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row_b])], ignore_index=True)
        elif tpl == "Existence":
            if act_a not in set(injected_df["concept:name"]):
                new_row = injected_df.iloc[-1].copy()
                new_row["concept:name"] = act_a
                new_row["time:timestamp"] = new_row["time:timestamp"] + _realistic_offset(seed_num)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row])], ignore_index=True)
            if gast.activation_attr in ("case:RequestedAmount", "RequestedAmount"):
                bad_val = _sample_near_boundary_violation_value(gast.activation_op, gast.activation_val, seed_num)
                injected_df["case:RequestedAmount"] = bad_val
                injected_df["RequestedAmount"] = bad_val
            elif gast.activation_attr in ("OfferedAmount", "NumberOfTerms", "MonthlyCost", "CreditScore"):
                bad_val = _sample_near_boundary_violation_value(gast.activation_op, gast.activation_val, seed_num)
                injected_df[gast.activation_attr] = bad_val
            else:
                injected_df = injected_df[injected_df["concept:name"] != act_a].reset_index(drop=True)
        elif tpl == "Absence":
            if act_a not in set(injected_df["concept:name"]):
                new_row = injected_df.iloc[-1].copy()
                new_row["concept:name"] = act_a
                new_row["time:timestamp"] = new_row["time:timestamp"] + _realistic_offset(seed_num)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row])], ignore_index=True)
            if gast.activation_attr == "OfferedAmount":
                base_thr = float(gast.activation_val) if gast.activation_val is not None else 50000.0
                injected_df["OfferedAmount"] = base_thr + float(1500 + (seed_num % 7) * 500)

        injected_df = injected_df.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
        is_c, d_info = check_single_trace_semantics(injected_df, gast)
        assert not is_c, f"Failed to synthesize violating counterexample for {rid}: {d_info}"
        subtype = d_info.get("violation_subtype", "SEMANTIC_VIOLATION")

        con_counts[rid] += 1
        contradicted_items.append({
            "benchmark_id": f"CON-{len(contradicted_items) + 1:04d}",
            "rule_id": rid,
            "rule_meta": inj_rule,
            "retrieved_chunk": inj_rule["retrieved_chunk"],
            "test_case_df": injected_df,
            "ground_truth_label": "CONTRADICTED",
            "trace_origin": f"SEMANTIC_FAULT_INJECTION_{subtype}_{rid}",
        })

    # Construct BASELESS traces uniformly across trap rules based on trap_scope & trap_type
    # Prefer unused real BPIC 2017 Case IDs so BASELESS items don't recycle cases already used in ENTAILED/CONTRADICTED
    unused_base_cases = [
        (cid, cdf)
        for cid, cdf in grouped_prop.items()
        if not strict_unique_cids or cid not in used_real_cids
    ] or list(grouped_prop.items())
    distinct_base_cases = [cdf for _, cdf in unused_base_cases]

    if trap_rules:
        trace_inapp_counter = 0
        trace_null_counter = 0
        other_counter = 0
        while len(baseless_items) < per_class_quota:
            b_idx = len(baseless_items)
            trap_rule = trap_rules[b_idx % len(trap_rules)]
            rid = trap_rule["rule_id"]
            trap_scope = trap_rule.get("trap_scope", "")
            trap_type = trap_rule.get("trap_type", "")
            req_act = trap_rule.get("act_a") or ""
            req_attr = trap_rule.get("attr")
            origin_tag = f"TIER3_TRAP_{rid}_{trap_type or 'BASELESS'}"

            if trap_scope == "trace" and trap_type == "INAPPLICABLE_TRACE_NO_ACTIVATION" and req_act:
                matching_no_act = [
                    (cid, cdf)
                    for cid, cdf in grouped_prop.items()
                    if req_act not in set(cdf["concept:name"])
                    and (not strict_unique_cids or cid not in used_real_cids)
                ]
                if not matching_no_act and strict_unique_cids:
                    matching_no_act = [
                        (cid, cdf)
                        for cid, cdf in grouped_prop.items()
                        if req_act not in set(cdf["concept:name"])
                    ]
                if trace_inapp_counter < len(matching_no_act) and not strict_unique_cids:
                    t_cid, t_raw = matching_no_act[trace_inapp_counter]
                    t_df = t_raw.copy()
                    origin_tag = f"BPIC2017_REAL_INAPPLICABLE_{rid}"
                elif strict_unique_cids and any(cid not in used_real_cids for cid, _ in matching_no_act):
                    avail = [(cid, cdf) for cid, cdf in matching_no_act if cid not in used_real_cids]
                    t_cid, t_raw = avail[0]
                    used_real_cids.add(t_cid)
                    t_df = t_raw.copy()
                    origin_tag = f"BPIC2017_REAL_INAPPLICABLE_{rid}"
                else:
                    src_df = distinct_base_cases[trace_inapp_counter % len(distinct_base_cases)]
                    filtered = src_df[src_df["concept:name"] != req_act].copy()
                    if filtered.empty:
                        filtered = src_df.iloc[:1].copy()
                        filtered["concept:name"] = "A_Create Application"
                    orig_cid = str(src_df["case:concept:name"].iloc[0])
                    seed_no_act = (abs(hash(f"{orig_cid}_no_act_{rid}_{trace_inapp_counter}")) % 900000000) + 100000000
                    filtered["case:concept:name"] = f"Application_{seed_no_act}"
                    t_df = filtered.reset_index(drop=True)
                    origin_tag = f"SYNTHETIC_NO_ACTIVATION_{rid}"
                trace_inapp_counter += 1
            elif trap_scope == "trace" and trap_type == "MISSING_LOG_EVIDENCE_PHI_VIOLATION" and req_act and req_attr:
                matching_with_act = [
                    cdf for cdf in distinct_base_cases if req_act in set(cdf["concept:name"])
                ] or distinct_base_cases
                src_df = matching_with_act[trace_null_counter % len(matching_with_act)].copy()
                orig_cid = str(src_df["case:concept:name"].iloc[0])
                seed_null = (abs(hash(f"{orig_cid}_null_attr_{rid}_{trace_null_counter}")) % 900000000) + 100000000
                src_df["case:concept:name"] = f"Application_{seed_null}"
                src_df[req_attr] = float("nan")
                t_df = src_df
                origin_tag = f"SYNTHETIC_MISSING_ATTR_{rid}"
                trace_null_counter += 1
            else:
                avail_other = [
                    (cid, cdf) for cid, cdf in unused_base_cases if not strict_unique_cids or cid not in used_real_cids
                ]
                if avail_other:
                    t_cid, t_raw = avail_other[other_counter % len(avail_other)] if not strict_unique_cids else avail_other[0]
                    used_real_cids.add(t_cid)
                    t_df = t_raw.copy()
                else:
                    src_df = distinct_base_cases[other_counter % len(distinct_base_cases)].copy()
                    orig_cid = str(src_df["case:concept:name"].iloc[0])
                    seed_other = (abs(hash(f"{orig_cid}_baseless_{rid}_{other_counter}")) % 900000000) + 100000000
                    src_df["case:concept:name"] = f"Application_{seed_other}"
                    t_df = src_df
                origin_tag = f"BPIC2017_REAL_TRAP_{rid}_{trap_type or 'BASELESS'}"
                other_counter += 1

            baseless_items.append({
                "benchmark_id": f"BAS-{len(baseless_items) + 1:04d}",
                "rule_id": rid,
                "rule_meta": trap_rule,
                "retrieved_chunk": trap_rule["retrieved_chunk"],
                "test_case_df": t_df,
                "ground_truth_label": "BASELESS",
                "trace_origin": origin_tag,
            })

    return entailed_items[:per_class_quota] + contradicted_items[:per_class_quota] + baseless_items[:per_class_quota]


def export_benchmark_json(
    output_rules_path: str = "data/processed/benchmark_rules_30.json",
    output_items_path: str = "data/processed/benchmark_items.json",
    chunks_path: str = "data/processed/directive_chunks.json",
    parquet_path: str = "data/interim/bpic2017_events.parquet",
    max_serialized_items: int = 300,
    force_rebuild: bool = False,
) -> Dict[str, Any]:
    """
    Xuất cả 2 file chuẩn:
    1. `benchmark_rules_30.json`: Chứa nguyên bản 30 quy tắc chuẩn (R01–R30).
    2. `benchmark_items.json`: Đóng gói các hồ sơ thực tế từ BPIC 2017 (đủ 3 nhãn ENTAILED, CONTRADICTED, BASELESS)
       kèm đoạn điều khoản luật và chuỗi sự kiện thực tế để kiểm chứng độc lập.
    """
    out_rules = Path(output_rules_path)
    out_rules.parent.mkdir(parents=True, exist_ok=True)
    with open(out_rules, "w", encoding="utf-8") as f:
        json.dump(BENCHMARK_RULES, f, indent=2, ensure_ascii=False)

    # Đồng thời lưu bản sao tại thư mục gốc nếu người dùng gọi trực tiếp
    root_copy = Path("benchmark_rules_30.json")
    with open(root_copy, "w", encoding="utf-8") as f:
        json.dump(BENCHMARK_RULES, f, indent=2, ensure_ascii=False)

    chunks_file = Path(chunks_path)
    parquet_file = Path(parquet_path)
    out_items = Path(output_items_path)
    serialized_count = 0

    if not force_rebuild and out_items.exists() and out_items.stat().st_size > 1000:
        try:
            with open(out_items, "r", encoding="utf-8") as f:
                serializable_items = json.load(f)
            return {
                "rules_count": len(BENCHMARK_RULES),
                "rules_path": str(out_rules),
                "items_count": len(serializable_items),
                "items_path": output_items_path,
            }
        except Exception:
            pass

    if chunks_file.exists() and parquet_file.exists():
        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        chunks_by_id = {c["article_id"]: c for c in chunks}
        normative_rules = build_normative_rule_benchmark(chunks_by_id)

        df_raw = pd.read_parquet(parquet_file)
        df_raw["time:timestamp"] = pd.to_datetime(df_raw["time:timestamp"], utc=True)
        # Sort deterministically before causal forward-fill; take a wide 12,000-case slice
        # so real BPIC 2017 violations and rare scenarios (e.g. R15 compliant, missing O_Sent, CreditScore=0) are surfaced naturally.
        sample_cids = df_raw["case:concept:name"].drop_duplicates().iloc[:12000].tolist()
        df_sub = (
            df_raw[df_raw["case:concept:name"].isin(sample_cids)]
            .sort_values(["case:concept:name", "time:timestamp"], kind="mergesort")
            .copy()
        )
        offer_cols = [
            c
            for c in ["OfferedAmount", "CreditScore", "Accepted", "Selected", "MonthlyCost", "NumberOfTerms", "FirstWithdrawalAmount"]
            if c in df_sub.columns
        ]
        if offer_cols:
            # Strict causal forward-fill only (no bfill() backward leakage onto pre-offer events)
            df_sub[offer_cols] = df_sub.groupby("case:concept:name", sort=False)[offer_cols].ffill()

        items = build_stratified_trace_benchmark(
            df_propagated=df_sub,
            df_raw=df_raw,
            normative_rules=normative_rules,
            target_total_items=max_serialized_items,
        )

        serializable_items = []
        for it in items:
            cdf: pd.DataFrame = it["test_case_df"]
            if "time:timestamp" in cdf.columns and not cdf.empty:
                cdf = cdf.sort_values("time:timestamp", kind="mergesort").reset_index(drop=True)
            events_list = []
            for _, row in cdf.iterrows():
                events_list.append(
                    {
                        "case:concept:name": str(row.get("case:concept:name", "")),
                        "concept:name": str(row.get("concept:name", "")),
                        "time:timestamp": str(row.get("time:timestamp", "")),
                        "case:RequestedAmount": (
                            None if pd.isna(row.get("case:RequestedAmount")) else float(row.get("case:RequestedAmount"))
                        ),
                        "OfferedAmount": (
                            None if pd.isna(row.get("OfferedAmount")) else float(row.get("OfferedAmount"))
                        ),
                        "CreditScore": (
                            None if pd.isna(row.get("CreditScore")) else float(row.get("CreditScore"))
                        ),
                        "NumberOfTerms": (
                            None if pd.isna(row.get("NumberOfTerms")) else float(row.get("NumberOfTerms"))
                        ),
                        "case:LoanGoal": (
                            None if pd.isna(row.get("case:LoanGoal")) else str(row.get("case:LoanGoal"))
                        ),
                        "case:ApplicationType": (
                            None if pd.isna(row.get("case:ApplicationType")) else str(row.get("case:ApplicationType"))
                        ),
                        "MonthlyCost": (
                            None if pd.isna(row.get("MonthlyCost")) else float(row.get("MonthlyCost"))
                        ),
                        "Selected": (
                            None if pd.isna(row.get("Selected")) else bool(row.get("Selected"))
                        ),
                        "Accepted": (
                            None if pd.isna(row.get("Accepted")) else bool(row.get("Accepted"))
                        ),
                    }
                )
            serializable_items.append(
                {
                    "benchmark_id": it["benchmark_id"],
                    "rule_id": it["rule_id"],
                    "dataset_split": it["rule_meta"].get("dataset_split"),
                    "ground_truth_label": it["ground_truth_label"],
                    "trace_origin": it["trace_origin"],
                    "retrieved_chunk": it["retrieved_chunk"],
                    "events": events_list,
                }
            )

        out_items = Path(output_items_path)
        out_items.parent.mkdir(parents=True, exist_ok=True)
        with open(out_items, "w", encoding="utf-8") as f:
            json.dump(serializable_items, f, indent=2, ensure_ascii=False)
        serialized_count = len(serializable_items)

    return {
        "rules_count": len(BENCHMARK_RULES),
        "rules_path": str(out_rules),
        "items_count": serialized_count,
        "items_path": output_items_path,
    }
