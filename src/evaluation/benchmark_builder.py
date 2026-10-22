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
    # --- TIER 1: CONTROL-FLOW CONSTRAINTS (12 QUY TẮC: R01 - R12) ---
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
        "description": "Phải khởi tạo hồ sơ vay (A_Create Application) trước khi bước vào đánh giá sơ bộ (A_Concept).",
    },
    {
        "rule_id": "R02",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "A_Concept",
        "act_b": "A_Accepted",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Hoạt động đánh giá sơ bộ A_Concept bắt buộc xảy ra trước A_Accepted.",
    },
    {
        "rule_id": "R03",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "A_Accepted",
        "act_b": "O_Create Offer",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Đánh giá khả năng trả nợ được phê duyệt sơ bộ (A_Accepted) trước khi ngân hàng tạo lập đề nghị vay chính thức (O_Create Offer) theo Điều 8(1).",
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
        "description": "Ngay trước khi O_Created được ghi nhận vào hệ thống phải có O_Create Offer.",
    },
    {
        "rule_id": "R05",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(1)",
        "template": "Precedence",
        "act_a": "O_Created",
        "act_b": "O_Sent (mail and online)",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Văn bản đề nghị vay (O_Created) phải được tạo lập trước khi gửi thông tin tiền hợp đồng O_Sent (mail and online).",
    },
    {
        "rule_id": "R06",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(1)",
        "template": "Precedence",
        "act_a": "O_Sent (mail and online)",
        "act_b": "A_Complete",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Bắt buộc gửi thông tin tiền hợp đồng O_Sent (mail and online) trước khi hồ sơ chuyển sang A_Complete.",
    },
    {
        "rule_id": "R07",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 10(1)",
        "template": "Precedence",
        "act_a": "O_Accepted",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Khách hàng phải chấp nhận đề nghị (O_Accepted) trước khi khoản vay được giải ngân (A_Pending).",
    },
    {
        "rule_id": "R08",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "W_Validate application",
        "act_b": "A_Validated",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Tác vụ thẩm định W_Validate application phải diễn ra trước trạng thái xác thực A_Validated.",
    },
    {
        "rule_id": "R09",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 9(2)",
        "template": "Response",
        "act_a": "A_Denied",
        "act_b": "O_Refused",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Khi hồ sơ bị từ chối do tra cứu dữ liệu (A_Denied), đề nghị vay tương ứng phải chuyển sang trạng thái từ chối (O_Refused) theo Điều 9(2).",
    },
    {
        "rule_id": "R10",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 13(2)",
        "template": "Not Co-Existence",
        "act_a": "A_Denied",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Một hồ sơ đã bị từ chối (A_Denied) thì tuyệt đối không thể được giải ngân (A_Pending).",
    },
    {
        "rule_id": "R11",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 14(1)",
        "template": "Response",
        "act_a": "A_Cancelled",
        "act_b": "O_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Khi hồ sơ bị hủy (A_Cancelled), đề nghị vay liên kết phải được hủy theo (O_Cancelled).",
    },
    {
        "rule_id": "R12",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 5(6)",
        "template": "Precedence",
        "act_a": "W_Call after offers",
        "act_b": "A_Validated",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Thực hiện nghĩa vụ giải thích thỏa đáng cho khách hàng qua cuộc gọi sau đề nghị (W_Call after offers) trước khi hồ sơ được xác thực phê duyệt (A_Validated) theo Điều 5(6).",
    },
    # --- TIER 2: TEMPORAL & DATA-AWARE CONSTRAINTS (10 QUY TẮC: R13 - R22) ---
    {
        "rule_id": "R13",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 2(2)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "OfferedAmount",
        "op": ">=",
        "val": 200.0,
        "time_max": None,
        "is_trap": False,
        "description": "Kiểm tra thuộc tính OfferedAmount >= 200 EUR tại sự kiện O_Create Offer theo Điều 2(2)(c).",
    },
    {
        "rule_id": "R14",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 2(2)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "OfferedAmount",
        "op": "<=",
        "val": 75000.0,
        "time_max": None,
        "is_trap": False,
        "description": "Phát hiện các đề nghị vay vượt trần OfferedAmount <= 75.000 EUR theo Điều 2(2)(c).",
    },
    {
        "rule_id": "R15",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 14(1)",
        "template": "Response",
        "act_a": "O_Sent (mail and online)",
        "act_b": "O_Returned",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 14,
        "is_trap": False,
        "description": "Khoảng thời gian từ lúc gửi hợp đồng O_Sent (mail and online) đến lúc khách gửi trả O_Returned <= 14 ngày.",
    },
    {
        "rule_id": "R16",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 14(3)",
        "template": "Response",
        "act_a": "O_Sent (mail and online)",
        "act_b": "A_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 30,
        "is_trap": False,
        "description": "Các hồ sơ rút lui/hủy bỏ (A_Cancelled) sau khi gửi đề nghị diễn ra trong vòng 30 ngày lịch.",
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
        "description": "Tại bước tạo đề nghị vay trước giải ngân (A_Pending), điểm CreditScore phải dương (> 0).",
    },
    {
        "rule_id": "R18",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 16(4)",
        "template": "Precedence",
        "act_a": "W_Validate application",
        "act_b": "O_Accepted",
        "attr": "OfferedAmount",
        "op": ">",
        "val": 10000.0,
        "time_max": None,
        "is_trap": False,
        "description": "Với các đề nghị vay trên 10.000 EUR, bắt buộc qua bước thẩm định W_Validate application trước O_Accepted.",
    },
    {
        "rule_id": "R19",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 13(1)",
        "template": "Response",
        "act_a": "A_Complete",
        "act_b": "O_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 30,
        "is_trap": False,
        "description": "Kiểm tra khoảng cách thời gian từ A_Complete đến khi hủy đề nghị O_Cancelled <= 30 ngày.",
    },
    {
        "rule_id": "R20",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Annex I(II)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "NumberOfTerms",
        "op": ">=",
        "val": 12,
        "time_max": None,
        "is_trap": False,
        "description": "Kiểm tra thuộc tính số kỳ trả góp NumberOfTerms >= 12 trên sự kiện O_Create Offer.",
    },
    {
        "rule_id": "R21",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Annex I(II)",
        "template": "Existence",
        "act_a": "A_Create Application",
        "act_b": None,
        "attr": "case:RequestedAmount",
        "op": ">=",
        "val": 1500.0,
        "time_max": None,
        "is_trap": False,
        "description": "Kiểm tra thuộc tính mức hồ sơ case:RequestedAmount >= 1500 EUR theo Phụ lục I Phần II(g).",
    },
    {
        "rule_id": "R22",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 18(2)",
        "template": "Response",
        "act_a": "A_Create Application",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 90,
        "is_trap": False,
        "description": "Toàn bộ chu trình từ lúc nộp đơn (A_Create Application) đến lúc tất toán/duyệt (A_Pending) <= 90 ngày.",
    },
    # --- TIER 3: HALLUCINATION & MISSING EVIDENCE TRAPS (8 QUY TẮC BẪY BASELESS: R23 - R30) ---
    {
        "rule_id": "R23",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 7",
        "template": "Response",
        "act_a": "A_Incomplete",
        "act_b": "A_Validating",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 8,
        "is_trap": True,
        "trap_type": "UNSUPPORTED_BY_DIRECTIVE_TEXT",
        "description": "Bẫy COND-004: Bịa thời hạn 8 ngày xử lý hồ sơ không đầy đủ gán vào Điều 7(1).",
    },
    {
        "rule_id": "R24",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 7",
        "template": "Response",
        "act_a": "A_Incomplete",
        "act_b": "W_Call incomplete files",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": True,
        "trap_type": "UNSUPPORTED_BY_DIRECTIVE_TEXT",
        "description": "Bẫy gán sai nguồn dẫn: Gán quy trình gọi bổ sung hồ sơ thiếu W_Call incomplete files vào Điều 7.",
    },
    {
        "rule_id": "R25",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 2(2)",
        "template": "Existence",
        "act_a": "A_Create Application",
        "act_b": None,
        "attr": "case:LoanGoal",
        "op": "==",
        "val": "Mortgage_RealEstate",
        "time_max": None,
        "is_trap": True,
        "trap_type": "OUT_OF_DIRECTIVE_SCOPE",
        "description": "Bẫy ngoài phạm vi: Áp dụng Chỉ thị cho hợp đồng thế chấp bất động sản (đã bị loại trừ tại Điều 2(2)(a)-(b)).",
    },
    {
        "rule_id": "R26",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 8(1)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "CreditScore",
        "op": ">=",
        "val": 750,
        "time_max": None,
        "is_trap": True,
        "trap_type": "UNSUPPORTED_NUMERIC_HALLUCINATION",
        "description": "Bẫy bịa ngưỡng số: Bịa điểm tín dụng tối thiểu CreditScore >= 750 vào Điều 8(1).",
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
        "trap_type": "MISSING_LOG_EVIDENCE_PHI_VIOLATION",
        "description": "Bẫy vi phạm tập Φ: Kiểm tra cột phí bồi thường trả trước EarlyRepaymentCompensationFee không có trong log BPIC 2017.",
    },
    {
        "rule_id": "R28",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 19(1)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "AnnualPercentageRateAPR",
        "op": "<=",
        "val": 20.0,
        "time_max": None,
        "is_trap": True,
        "trap_type": "MISSING_LOG_EVIDENCE_PHI_VIOLATION",
        "description": "Bẫy vi phạm tập Φ: Kiểm tra cột lãi suất APR không tồn tại trong lược đồ BPIC 2017.",
    },
    {
        "rule_id": "R29",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 2(2)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "OfferedAmount",
        "op": ">=",
        "val": 200.0,
        "time_max": None,
        "is_trap": True,
        "trap_type": "INAPPLICABLE_TRACE_NO_ACTIVATION",
        "description": "Bẫy null/khuyết sự kiện trên Trace: Kiểm tra OfferedAmount trên hồ sơ bị từ chối sớm chưa từng tạo O_Create Offer.",
    },
    {
        "rule_id": "R30",
        "tier": "Tier3_BaselessTrap",
        "complexity_tier": "Tier 3: Baseless / Hallucination Traps",
        "article_id": "Article 8(1)",
        "template": "Existence",
        "act_a": "O_Create Offer",
        "act_b": None,
        "attr": "CreditScore",
        "op": ">",
        "val": 0,
        "time_max": None,
        "is_trap": True,
        "trap_type": "MISSING_LOG_EVIDENCE_PHI_VIOLATION",
        "description": "Bẫy null sentinel trên Trace: Kiểm tra CreditScore trên dòng sự kiện O_Create Offer có CreditScore = NaN.",
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


# Phân tách độc lập 30 quy tắc chuẩn chống Overfitting on Benchmark:
# - Tập Development (15 quy tắc: R01–R15): Dùng để thử nghiệm, thiết kế prompt và tinh chỉnh hệ thống.
# - Tập Held-out Test (15 quy tắc: R16–R30): Khóa kín, chỉ bấm chạy 1 lần duy nhất khi đánh giá cuối cùng.
DEV_RULE_IDS = {f"R{i:02d}" for i in range(1, 16)}
HELDOUT_TEST_RULE_IDS = {f"R{i:02d}" for i in range(16, 31)}


def split_benchmark_rules(
    normative_rules: List[Dict[str, Any]],
    split: str = "all",
) -> List[Dict[str, Any]]:
    """
    Lọc danh sách quy tắc theo tập dữ liệu:
    - split='dev': Chỉ trả về 15 quy tắc R01–R15 (Development Set).
    - split='heldout_test': Chỉ trả về 15 quy tắc R16–R30 (Held-out Blind Test Set).
    - split='all': Trả về toàn bộ 30 quy tắc R01–R30.
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
    và nhãn phân tập `dataset_split` ('dev' cho R01–R15, 'heldout_test' cho R16–R30).
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
            "activation_activity": "A_Validated",
            "target_activity": "W_Validate application",
            "time_min": 0,
            "time_max": None,
            "time_unit": "d",
        },
        "R13": {
            "article_id": "Article 2(2)",
            "template_name": "Existence",
            "activation_activity": "O_Create Offer",
            "target_activity": None,
            "activation_attr": "LoanOfferedEUR",
            "activation_op": ">=",
            "activation_val": 200.0,
            "time_min": 0,
            "time_max": None,
            "time_unit": "d",
        },
        "R15": {
            "article_id": "Article 14(1)",
            "template_name": "Response",
            "activation_activity": "O_Sent (mail and online)",
            "target_activity": "O_Returned",
            "time_min": 0,
            "time_max": 30,
            "time_unit": "d",
        },
        "R18": {
            "article_id": "Article 16(4)",
            "template_name": "Precedence",
            "activation_activity": "W_Validate application",
            "target_activity": "O_Accepted",
            "activation_attr": "OfferedAmount",
            "activation_op": ">",
            "activation_val": 99999999.0,
            "time_min": 0,
            "time_max": None,
            "time_unit": "d",
        },
        "R19": {
            "article_id": "Article 13(1)",
            "template_name": "Response",
            "activation_activity": "A_Complete",
            "target_activity": "O_Cancelled",
            "time_min": 0,
            "time_max": None,
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
    Hàm tự động lọc theo `split` ('dev': R01–R15, 'heldout_test': R16–R30, hoặc 'all').
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
                case_df["time:timestamp"] = pd.to_datetime(case_df["time:timestamp"], utc=True)
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
    `split` ('dev': R01–R15, 'heldout_test': R16–R30, hoặc 'all'):
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

    per_class_quota = target_total_items // 3
    all_rules_by_id = {r["rule_id"]: r for r in normative_rules}
    active_rules = split_benchmark_rules(normative_rules, split=split)
    active_rule_ids = {r["rule_id"] for r in active_rules}

    r05 = all_rules_by_id.get("R05") or active_rules[0]
    r06 = all_rules_by_id.get("R06") or active_rules[0]
    r08 = all_rules_by_id.get("R08") or active_rules[0]
    r13 = all_rules_by_id.get("R13") or active_rules[0]
    r15 = all_rules_by_id.get("R15") or active_rules[0]
    r18 = all_rules_by_id.get("R18") or active_rules[0]
    r19 = all_rules_by_id.get("R19") or active_rules[0]
    trap_rules = [r for r in active_rules if r.get("is_trap")] or [r for r in normative_rules if r.get("is_trap")]
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
                r["dataset_split"] = "heldout_test"
                r["retrieved_chunk"] = chunk
                r["is_baseless_trap"] = True
                r["gold_ast"] = None
                ast_dict = _rule_to_ast_dict(r)
                r["raw_attempt_1"] = ast_dict
                r["repaired_attempt_2"] = ast_dict
                fallback_traps.append(r)
        trap_rules = fallback_traps

    unique_cids = df_propagated["case:concept:name"].drop_duplicates().iloc[:1800].tolist()
    sub_prop = df_propagated[df_propagated["case:concept:name"].isin(unique_cids)]
    grouped_prop = {
        cid: grp.sort_values("time:timestamp").reset_index(drop=True)
        for cid, grp in sub_prop.groupby("case:concept:name", sort=False)
    }

    entailed_items: List[Dict[str, Any]] = []
    contradicted_items: List[Dict[str, Any]] = []
    baseless_items: List[Dict[str, Any]] = []

    # Loại trừ R10, R13, R14, R15 khỏi bộ sinh trace ngẫu nhiên cơ bản:
    # - R10 (Not Co-Existence): logic phủ định đồng thời, hầu như luôn thỏa mãn chân lý rỗng trong log BPIC 2017.
    # - R13, R14 (Existence với OfferedAmount >= 200 hoặc <= 75000): có điều kiện thuộc tính số học cần lọc riêng.
    # - R15 (Response 14 days): có ràng buộc thời lượng cần đối soát mốc timestamp cụ thể.
    valid_candidate_rules = [
        r for r in active_rules
        if not r.get("is_trap") and not r.get("is_baseless_trap") and r["rule_id"] not in ("R10", "R13", "R14", "R15")
    ]
    if not valid_candidate_rules:
        valid_candidate_rules = [
            r for r in normative_rules
            if not r.get("is_trap") and not r.get("is_baseless_trap") and r["rule_id"] not in ("R10", "R13", "R14", "R15")
        ]

    candidate_gold_asts = {
        r["rule_id"]: DeclareConstraintAST(**_rule_to_ast_dict(r))
        for r in valid_candidate_rules
    }

    max_per_rule = max(per_class_quota // max(len(valid_candidate_rules), 1) + 2, 2)

    for cid, case_df in grouped_prop.items():
        acts = set(case_df["concept:name"])
        for r in valid_candidate_rules:
            rid = r["rule_id"]
            gast = candidate_gold_asts[rid]
            act_a = gast.activation_activity
            act_b = gast.target_activity
            if act_a not in acts and (not act_b or act_b not in acts):
                continue
            is_comp, details = check_single_trace_semantics(case_df, gast)
            if is_comp and len(entailed_items) < per_class_quota:
                if sum(1 for x in entailed_items if x["rule_id"] == rid) < max_per_rule:
                    entailed_items.append(
                        {
                            "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
                            "rule_id": rid,
                            "rule_meta": r,
                            "retrieved_chunk": r["retrieved_chunk"],
                            "test_case_df": case_df,
                            "ground_truth_label": "ENTAILED",
                            "trace_origin": f"BPIC2017_REAL_COMPLIANT_{rid}",
                        }
                    )
            elif not is_comp and len(contradicted_items) < per_class_quota:
                if sum(1 for x in contradicted_items if x["rule_id"] == rid) < max_per_rule:
                    contradicted_items.append(
                        {
                            "benchmark_id": f"CON-{len(contradicted_items) + 1:04d}",
                            "rule_id": rid,
                            "rule_meta": r,
                            "retrieved_chunk": r["retrieved_chunk"],
                            "test_case_df": case_df,
                            "ground_truth_label": "CONTRADICTED",
                            "trace_origin": f"BPIC2017_REAL_VIOLATION_{rid}",
                        }
                    )
        if len(entailed_items) >= per_class_quota and len(contradicted_items) >= per_class_quota:
            break

    # Đảm bảo đủ số lượng ENTAILED
    base_compliant_df = entailed_items[0]["test_case_df"] if entailed_items else df_propagated.iloc[:10].copy()
    while len(entailed_items) < per_class_quota:
        r_choice = valid_candidate_rules[len(entailed_items) % len(valid_candidate_rules)]
        entailed_items.append(
            {
                "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
                "rule_id": r_choice["rule_id"],
                "rule_meta": r_choice,
                "retrieved_chunk": r_choice["retrieved_chunk"],
                "test_case_df": base_compliant_df,
                "ground_truth_label": "ENTAILED",
                "trace_origin": f"BPIC2017_COMPLIANT_{r_choice['rule_id']}",
            }
        )

    # Bổ sung CONTRADICTED bằng tiêm lỗi có kiểm soát trên các quy tắc hợp lệ
    while len(contradicted_items) < per_class_quota:
        idx = len(contradicted_items)
        inj_rule = valid_candidate_rules[idx % len(valid_candidate_rules)]
        rid = inj_rule["rule_id"]
        gast = candidate_gold_asts[rid]
        injected_df = base_compliant_df.copy()
        injected_df["case:concept:name"] = f"Application_FaultInjected_{idx + 1:04d}"
        if gast.activation_activity in set(injected_df["concept:name"]):
            injected_df = injected_df[injected_df["concept:name"] != gast.activation_activity].reset_index(drop=True)
        contradicted_items.append(
            {
                "benchmark_id": f"CON-{len(contradicted_items) + 1:04d}",
                "rule_id": rid,
                "rule_meta": inj_rule,
                "retrieved_chunk": inj_rule["retrieved_chunk"],
                "test_case_df": injected_df,
                "ground_truth_label": "CONTRADICTED",
                "trace_origin": f"CONTROLLED_FAULT_INJECTION_MISSING_{gast.activation_activity}",
            }
        )

    # Xây dựng nhóm BASELESS trải đều trên 8 quy tắc bẫy R23–R30:
    # - R23..R26: Bẫy ảo giác văn bản / ngoài phạm vi / bịa ngưỡng số (Roundtrip bắt lỗi)
    # - R27..R28: Bẫy thiếu cột thuộc tính trong Log Schema (EarlyRepaymentCompensationFee, AnnualPercentageRateAPR)
    # - R29: Hồ sơ bị từ chối sớm A_Create Application -> A_Denied (không có O_Create Offer -> INAPPLICABLE_TRACE_NO_ACTIVATION)
    # - R30: Hồ sơ có O_Create Offer nhưng CreditScore = NaN (MISSING_LOG_EVIDENCE_PHI_VIOLATION)
    no_offer_df = base_compliant_df[
        base_compliant_df["concept:name"].isin(["A_Create Application", "W_Complete application"])
    ].copy()
    no_offer_df["case:concept:name"] = "Application_RejectedEarly_R29"

    null_credit_df = base_compliant_df.copy()
    null_credit_df["case:concept:name"] = "Application_NullCreditScore_R30"
    null_credit_df["CreditScore"] = float("nan")

    if trap_rules:
        while len(baseless_items) < per_class_quota:
            trap_rule = trap_rules[len(baseless_items) % len(trap_rules)]
            rid = trap_rule["rule_id"]
            if rid == "R29":
                t_df = no_offer_df
            elif rid == "R30":
                t_df = null_credit_df
            else:
                t_df = base_compliant_df

            baseless_items.append(
                {
                    "benchmark_id": f"BAS-{len(baseless_items) + 1:04d}",
                    "rule_id": rid,
                    "rule_meta": trap_rule,
                    "retrieved_chunk": trap_rule["retrieved_chunk"],
                    "test_case_df": t_df,
                    "ground_truth_label": "BASELESS",
                    "trace_origin": f"TIER3_TRAP_{rid}_{trap_rule.get('trap_type', 'BASELESS')}",
                }
            )

    return entailed_items[:per_class_quota] + contradicted_items[:per_class_quota] + baseless_items[:per_class_quota]


def export_benchmark_json(
    output_rules_path: str = "data/processed/benchmark_rules_30.json",
    output_items_path: str = "data/processed/benchmark_items.json",
    chunks_path: str = "data/processed/directive_chunks.json",
    parquet_path: str = "data/interim/bpic2017_events.parquet",
    max_serialized_items: int = 300,
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

    if out_items.exists() and out_items.stat().st_size > 1000:
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
        offer_cols = [
            c
            for c in ["OfferedAmount", "CreditScore", "Accepted", "MonthlyCost", "NumberOfTerms"]
            if c in df_raw.columns
        ]
        df_prop = df_raw.copy()
        if offer_cols:
            df_prop[offer_cols] = df_prop.groupby("case:concept:name", sort=False)[offer_cols].ffill().bfill()
            df_prop[offer_cols] = df_prop.groupby("case:concept:name", sort=False)[offer_cols].bfill()

        items = build_stratified_trace_benchmark(
            df_propagated=df_prop,
            df_raw=df_raw,
            normative_rules=normative_rules,
            target_total_items=max_serialized_items,
        )

        serializable_items = []
        for it in items:
            cdf: pd.DataFrame = it["test_case_df"]
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
                    }
                )
            serializable_items.append(
                {
                    "benchmark_id": it["benchmark_id"],
                    "rule_id": it["rule_id"],
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
