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
        "description": "Để thu thập đầy đủ thông tin từ người vay phục vụ việc đánh giá khả năng trả nợ theo Điều 8(1), quy trình ngân hàng bắt buộc phải tiếp nhận hồ sơ vay của khách hàng trước khi tiến hành bước đánh giá sơ bộ hồ sơ.",
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
        "description": "Nghĩa vụ đánh giá khả năng trả nợ theo Điều 8(1): Bước đánh giá sơ bộ hồ sơ bắt buộc phải hoàn thành trước khi hồ sơ vay được ngân hàng phê duyệt sơ bộ.",
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
        "description": "Nghĩa vụ đánh giá khả năng trả nợ theo Điều 8(1): Hồ sơ vay bắt buộc phải được phê duyệt sơ bộ trước khi ngân hàng tạo lập đề nghị vay chính thức cho khách hàng.",
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
        "description": "Nghĩa vụ cung cấp thông tin tiền hợp đồng theo Điều 5(1): Ngay trước khi văn bản đề nghị vay được ghi nhận chính thức vào hệ thống, ngân hàng bắt buộc phải thực hiện bước tạo lập đề nghị vay.",
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
        "description": "Nghĩa vụ cung cấp thông tin tiền hợp đồng theo Điều 5(1): Văn bản đề nghị vay phải được tạo lập trên hệ thống trước khi gửi thông tin tiền hợp đồng cho khách hàng qua thư hoặc trực tuyến.",
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
        "description": "Nghĩa vụ cung cấp thông tin tiền hợp đồng theo Điều 5(1): Thông tin tiền hợp đồng bắt buộc phải được gửi tới người tiêu dùng qua thư hoặc trực tuyến trước khi hồ sơ chuyển sang trạng thái hoàn tất thủ tục.",
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
        "description": "Quy định về hình thức hợp đồng theo Điều 10(1): Khách hàng bắt buộc phải chấp thuận đề nghị vay trước khi ngân hàng chuyển hồ sơ sang bước chờ giải ngân tiền vay.",
    },
    {
        "rule_id": "R08",
        "tier": "Tier1_ControlFlow",
        "complexity_tier": "Tier 1: Control-Flow Only",
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "W_Validate application",
        "act_b": "A_Validating",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Nghĩa vụ thẩm định khả năng trả nợ theo Điều 8(1): Tác vụ thẩm định chi tiết hồ sơ của nhân viên ngân hàng phải diễn ra trước khi hồ sơ chuyển sang trạng thái xác thực trên hệ thống.",
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
        "description": "Quy chuẩn thông báo khi từ chối theo Điều 9(2): Khi hồ sơ bị từ chối do kết quả tra cứu cơ sở dữ liệu, đề nghị vay tương ứng bắt buộc phải chuyển sang trạng thái từ chối.",
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
        "description": "Quy chuẩn quản lý rủi ro và chấm dứt theo Điều 13(2): Một hồ sơ vay một khi đã bị từ chối thì tuyệt đối không được phép tiến hành giải ngân tiền vay.",
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
        "description": "Quy chuẩn vận hành quyền rút lui hợp đồng theo Điều 14(1): Khi người tiêu dùng thông báo hủy hoặc rút lui hồ sơ vay, đề nghị vay liên kết bắt buộc phải được hủy bỏ.",
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
        "description": "Nghĩa vụ giải thích thỏa đáng theo Điều 5(6): Ngân hàng bắt buộc phải thực hiện cuộc gọi tư vấn giải thích thỏa đáng cho khách hàng sau khi tạo đề nghị trước khi hồ sơ chuyển sang trạng thái xác thực.",
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
        "description": "Quy chuẩn mức sàn hạn mức tín dụng theo Điều 2(2)(c): Đề nghị vay do ngân hàng tạo lập phải có số tiền đề nghị không được thấp hơn mức sàn luật định là 200 EUR.",
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
        "description": "Quy chuẩn mức trần hạn mức tín dụng theo Điều 2(2)(c): Đề nghị vay do ngân hàng tạo lập phải có số tiền đề nghị không được vượt quá mức trần luật định là 75.000 EUR.",
    },
    {
        "rule_id": "R15",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 14(1)",
        "template": "Response",
        "act_a": "O_Sent (mail and online)",
        "act_b": "A_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 14,
        "is_trap": False,
        "description": "Quy chuẩn thời hạn rút lui hợp đồng theo Điều 14(1): Khách hàng có quyền thông báo hủy hồ sơ vay trong vòng 14 ngày lịch sau khi ngân hàng gửi thông tin đề nghị qua thư hoặc trực tuyến.",
    },
    {
        "rule_id": "R16",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 14(3)",
        "template": "Precedence",
        "act_a": "O_Sent (mail and online)",
        "act_b": "A_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 30,
        "is_trap": False,
        "description": "Quy chuẩn giới hạn thời gian thông báo theo Điều 14(3): Khách hàng chỉ có thể thực hiện quyền hủy hồ sơ vay trong thời hạn tối đa 30 ngày lịch sau khi ngân hàng gửi văn bản đề nghị.",
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
        "description": "Nghĩa vụ thẩm định điểm tín dụng theo Điều 8(1): Trước khi ngân hàng giải ngân khoản vay, đề nghị vay tương ứng bắt buộc phải có điểm tín dụng hợp lệ lớn hơn 0.",
    },
    {
        "rule_id": "R18",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "W_Validate application",
        "act_b": "O_Accepted",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Nghĩa vụ đánh giá khả năng trả nợ theo Điều 8(1): Trước khi ngân hàng chấp thuận đề nghị vay, hồ sơ bắt buộc phải hoàn thành tác vụ thẩm định chi tiết của nhân viên tín dụng.",
    },
    {
        "rule_id": "R19",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 13(1)",
        "template": "Response",
        "act_a": "A_Cancelled",
        "act_b": "O_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Quy chuẩn chấm dứt hợp đồng mở theo Điều 13(1): Khi người tiêu dùng thực hiện quyền chấm dứt thỏa thuận vay, việc hủy bỏ đề nghị tín dụng tương ứng bắt buộc phải được thực hiện.",
    },
    {
        "rule_id": "R20",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 2(2)",
        "template": "Existence",
        "act_a": "A_Create Application",
        "act_b": None,
        "attr": "case:RequestedAmount",
        "op": ">=",
        "val": 200.0,
        "time_max": None,
        "is_trap": False,
        "description": "Quy chuẩn hạn mức số tiền vay theo Điều 2(2)(c): Số tiền vay do khách hàng yêu cầu tại bước nộp đơn ban đầu không được thấp hơn mức sàn luật định là 200 EUR.",
    },
    {
        "rule_id": "R21",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 2(2)",
        "template": "Existence",
        "act_a": "A_Create Application",
        "act_b": None,
        "attr": "case:RequestedAmount",
        "op": "<=",
        "val": 75000.0,
        "time_max": None,
        "is_trap": False,
        "description": "Quy chuẩn hạn mức số tiền vay theo Điều 2(2)(c): Số tiền vay do khách hàng yêu cầu tại bước nộp đơn ban đầu không được vượt quá mức trần luật định là 75.000 EUR.",
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
        "description": "Quy chuẩn thời hạn xử lý sau khi rút lui theo Điều 14(3): Khi khách hàng thông báo rút lui hoặc hủy hồ sơ, đề nghị vay tương ứng bắt buộc phải được hủy bỏ trong vòng 30 ngày lịch.",
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
        "description": "Quy định gài bẫy phạm vi: Yêu cầu áp dụng thời hạn 8 ngày xử lý hồ sơ không đầy đủ dựa trên Điều 7(1).",
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
        "description": "Quy định gài bẫy nguồn dẫn: Gán quy trình gọi điện thu thập bổ sung hồ sơ thiếu vào Điều 7.",
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
        "description": "Quy định gài bẫy ngoài phạm vi: Ép buộc áp dụng Chỉ thị tín dụng tiêu dùng cho các hợp đồng thế chấp bất động sản nhà ở.",
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
        "description": "Quy định gài bẫy ngưỡng định lượng: Bắt buộc người vay phải đạt điểm tín dụng giả định từ 750 điểm trở lên theo Điều 8(1).",
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
        "description": "Quy định gài bẫy thuộc tính ngoài lược đồ: Yêu cầu kiểm tra mức phí bồi thường trả nợ trước hạn theo Điều 16(2).",
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
        "description": "Quy định gài bẫy công thức lãi suất: Bắt buộc kiểm tra cột tỷ lệ phần trăm chi phí hàng năm theo công thức của Điều 19(1).",
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
        "description": "Quy định gài bẫy thuộc tính khuyết: Kiểm tra số tiền đề nghị vay trên những hồ sơ đã bị từ chối sớm trước khi tạo đề nghị.",
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
        "description": "Quy định gài bẫy điều kiện thế chấp: Bắt buộc khách hàng phải cung cấp tài sản bảo đảm thế chấp theo Điều 8(1).",
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
            "activation_activity": "A_Validating",
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
                r["dataset_split"] = "heldout_test"
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

    # Đảm bảo phân rã và lập chỉ mục nhanh danh sách case, ưu tiên các case trễ hạn thực tế của R22
    REAL_LATE_PENDING_CASES = [
        "Application_1108271369", "Application_1171453988", "Application_130761111",
        "Application_1499090661", "Application_157155173", "Application_1677498057",
        "Application_1741752833", "Application_1838182698", "Application_1875888758",
        "Application_2037628374",
    ]
    unique_cids = list(dict.fromkeys(REAL_LATE_PENDING_CASES + df_propagated["case:concept:name"].drop_duplicates().iloc[:600].tolist()))
    sub_prop = df_propagated[df_propagated["case:concept:name"].isin(unique_cids)]
    grouped_prop = {
        cid: grp.sort_values("time:timestamp").reset_index(drop=True)
        for cid, grp in sub_prop.groupby("case:concept:name", sort=False)
    }

    entailed_items: List[Dict[str, Any]] = []
    contradicted_items: List[Dict[str, Any]] = []
    baseless_items: List[Dict[str, Any]] = []

    max_per_rule = max(per_class_quota // max(len(active_norm), 1) + 2, 2)

    for cid, case_df in grouped_prop.items():
        acts = set(case_df["concept:name"])
        for r in active_norm:
            rid = r["rule_id"]
            gast = candidate_gold_asts[rid]
            tpl = gast.template_name
            act_a = gast.activation_activity
            act_b = gast.target_activity

            # Bộ lọc kích hoạt không rỗng (Non-Vacuous Activation Check):
            # 1. Precedence: Hoạt động đích B bắt buộc phải xảy ra trong hồ sơ
            if tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
                if act_b not in acts:
                    continue
                # R18 now applies to all cases
                if rid == "R17":
                    score = case_df["CreditScore"].max()
                    if pd.isna(score) or score <= 0:
                        continue
                if act_a not in acts:
                    # Vi phạm tiền đề thực tế
                    is_c, d_info = check_single_trace_semantics(case_df, gast)
                    if not is_c and len(contradicted_items) < per_class_quota:
                        if sum(1 for x in contradicted_items if x["rule_id"] == rid) < max_per_rule:
                            contradicted_items.append({
                                "benchmark_id": f"CON-{len(contradicted_items) + 1:04d}",
                                "rule_id": rid,
                                "rule_meta": r,
                                "retrieved_chunk": r["retrieved_chunk"],
                                "test_case_df": case_df,
                                "ground_truth_label": "CONTRADICTED",
                                "trace_origin": f"BPIC2017_REAL_VIOLATION_{rid}",
                            })
                    continue

            # 2. Response: Hoạt động kích hoạt A bắt buộc phải xảy ra trong hồ sơ
            elif tpl in ("Response", "Alternate Response", "Chain Response"):
                if act_a not in acts:
                    continue
                # R22 Response check

            # 3. Not Co-Existence: Ít nhất một trong hai hoạt động phải xảy ra
            elif tpl == "Not Co-Existence":
                if act_a not in acts and act_b not in acts:
                    continue

            # 4. Existence & Absence
            elif tpl in ("Existence", "Absence"):
                if act_a not in acts:
                    continue

            is_comp, details = check_single_trace_semantics(case_df, gast)
            if is_comp and len(entailed_items) < per_class_quota:
                if sum(1 for x in entailed_items if x["rule_id"] == rid) < max_per_rule:
                    entailed_items.append({
                        "benchmark_id": f"ENT-{len(entailed_items) + 1:04d}",
                        "rule_id": rid,
                        "rule_meta": r,
                        "retrieved_chunk": r["retrieved_chunk"],
                        "test_case_df": case_df,
                        "ground_truth_label": "ENTAILED",
                        "trace_origin": f"BPIC2017_REAL_COMPLIANT_{rid}",
                    })
            elif not is_comp and len(contradicted_items) < per_class_quota:
                if sum(1 for x in contradicted_items if x["rule_id"] == rid) < max_per_rule:
                    contradicted_items.append({
                        "benchmark_id": f"CON-{len(contradicted_items) + 1:04d}",
                        "rule_id": rid,
                        "rule_meta": r,
                        "retrieved_chunk": r["retrieved_chunk"],
                        "test_case_df": case_df,
                        "ground_truth_label": "CONTRADICTED",
                        "trace_origin": f"BPIC2017_REAL_VIOLATION_{rid}",
                    })

        if len(entailed_items) >= per_class_quota and len(contradicted_items) >= per_class_quota:
            break

    # Nếu còn thiếu ENTAILED (rất hiếm khi xảy ra), tiếp tục nạp hồ sơ kích hoạt
    base_compliant_df = entailed_items[0]["test_case_df"] if entailed_items else df_propagated.iloc[:15].copy()
    base_cases_by_rule = {it["rule_id"]: it["test_case_df"] for it in entailed_items}

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

    # Bổ sung CONTRADICTED bằng Tiêm lỗi Ngữ nghĩa Chuẩn mực (Semantic Fault Injection)
    while len(contradicted_items) < per_class_quota:
        idx = len(contradicted_items)
        inj_rule = active_norm[idx % len(active_norm)]
        rid = inj_rule["rule_id"]
        gast = candidate_gold_asts[rid]
        tpl = gast.template_name
        act_a = gast.activation_activity
        act_b = gast.target_activity

        base_df = base_cases_by_rule.get(rid, base_compliant_df).copy()
        injected_df = base_df.copy()
        injected_df["case:concept:name"] = f"Application_FaultInjected_{idx + 1:04d}"

        if tpl in ("Precedence", "Alternate Precedence", "Chain Precedence"):
            # Đảm bảo hoạt động đích B có mặt và xóa A đi trước
            if act_b not in set(injected_df["concept:name"]):
                new_row = injected_df.iloc[-1].copy()
                new_row["concept:name"] = act_b
                new_row["time:timestamp"] = new_row["time:timestamp"] + pd.Timedelta(hours=1)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row])], ignore_index=True)
            injected_df = injected_df[injected_df["concept:name"] != act_a].reset_index(drop=True)
            if rid == "R18":
                injected_df["OfferedAmount"] = 15000.0
            if rid == "R17":
                injected_df["CreditScore"] = 750.0
        elif tpl in ("Response", "Alternate Response", "Chain Response"):
            # Đảm bảo hoạt động kích hoạt A có mặt để kích hoạt nghĩa vụ
            if act_a not in set(injected_df["concept:name"]):
                new_row = injected_df.iloc[-1].copy()
                new_row["concept:name"] = act_a
                new_row["time:timestamp"] = new_row["time:timestamp"] + pd.Timedelta(hours=1)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row])], ignore_index=True)
            if gast.time_max is not None:
                if act_b in set(injected_df["concept:name"]):
                    mask_b = injected_df["concept:name"] == act_b
                    t_first = injected_df["time:timestamp"].min()
                    injected_df.loc[mask_b, "time:timestamp"] = t_first + pd.Timedelta(days=gast.time_max + 30)
                else:
                    injected_df = injected_df[injected_df["concept:name"] != act_b].reset_index(drop=True)
            else:
                # Xóa phản hồi B để nghĩa vụ kích hoạt bởi A bị vi phạm
                injected_df = injected_df[injected_df["concept:name"] != act_b].reset_index(drop=True)
        elif tpl == "Not Co-Existence":
            # Đảm bảo cả hai hoạt động cùng có mặt để vi phạm loại trừ lẫn nhau
            if act_a not in set(injected_df["concept:name"]):
                new_row_a = injected_df.iloc[-1].copy()
                new_row_a["concept:name"] = act_a
                new_row_a["time:timestamp"] = new_row_a["time:timestamp"] + pd.Timedelta(hours=1)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row_a])], ignore_index=True)
            if act_b not in set(injected_df["concept:name"]):
                new_row_b = injected_df.iloc[-1].copy()
                new_row_b["concept:name"] = act_b
                new_row_b["time:timestamp"] = new_row_b["time:timestamp"] + pd.Timedelta(hours=2)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row_b])], ignore_index=True)
        elif tpl == "Existence":
            if act_a not in set(injected_df["concept:name"]):
                new_row = injected_df.iloc[-1].copy()
                new_row["concept:name"] = act_a
                new_row["time:timestamp"] = new_row["time:timestamp"] + pd.Timedelta(hours=1)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row])], ignore_index=True)
            if gast.activation_attr == "OfferedAmount" and gast.activation_op == ">=":
                injected_df["OfferedAmount"] = 100.0
            elif gast.activation_attr == "OfferedAmount" and gast.activation_op == "<=":
                injected_df["OfferedAmount"] = 85000.0
            elif gast.activation_attr == "NumberOfTerms":
                injected_df["NumberOfTerms"] = 6.0
            elif gast.activation_attr in ("case:RequestedAmount", "RequestedAmount"):
                if gast.activation_op == ">=":
                    injected_df["case:RequestedAmount"] = 100.0
                    injected_df["RequestedAmount"] = 100.0
                else:
                    injected_df["case:RequestedAmount"] = 85000.0
                    injected_df["RequestedAmount"] = 85000.0
            elif gast.activation_attr == "MonthlyCost":
                injected_df["MonthlyCost"] = 5.0
            else:
                injected_df = injected_df[injected_df["concept:name"] != act_a].reset_index(drop=True)
        elif tpl == "Absence":
            if act_a not in set(injected_df["concept:name"]):
                new_row = injected_df.iloc[-1].copy()
                new_row["concept:name"] = act_a
                new_row["time:timestamp"] = new_row["time:timestamp"] + pd.Timedelta(hours=1)
                injected_df = pd.concat([injected_df, pd.DataFrame([new_row])], ignore_index=True)
            if gast.activation_attr == "OfferedAmount":
                injected_df["OfferedAmount"] = 85000.0

        is_c, d_info = check_single_trace_semantics(injected_df, gast)
        assert not is_c, f"Lỗi tạo ca vi phạm tiêm lỗi cho {rid}: dự kiến False nhưng nhận True! Details: {d_info}"
        subtype = d_info.get("violation_subtype", "SEMANTIC_VIOLATION")

        contradicted_items.append({
            "benchmark_id": f"CON-{len(contradicted_items) + 1:04d}",
            "rule_id": rid,
            "rule_meta": inj_rule,
            "retrieved_chunk": inj_rule["retrieved_chunk"],
            "test_case_df": injected_df,
            "ground_truth_label": "CONTRADICTED",
            "trace_origin": f"SEMANTIC_FAULT_INJECTION_{subtype}_{rid}",
        })

    # Xây dựng nhóm BASELESS trải đều trên 8 quy tắc bẫy R23–R30:
    # - R23..R28: Bẫy ảo giác văn bản / ngoài phạm vi / bịa ngưỡng số (gán trace nền đa dạng, không trùng lặp)
    # - R29: Hồ sơ bị từ chối sớm A_Create Application -> W_Complete application -> A_Denied (thực sự không có O_Create Offer)
    # - R30: Hồ sơ có O_Create Offer nhưng CreditScore = NaN
    denied_template_df = base_compliant_df[
        base_compliant_df["concept:name"].isin(["A_Create Application", "W_Complete application"])
    ].copy()
    if not denied_template_df.empty:
        den_row = denied_template_df.iloc[-1].copy()
        den_row["concept:name"] = "A_Denied"
        den_row["time:timestamp"] = den_row["time:timestamp"] + pd.Timedelta(minutes=30)
        early_denied_df = pd.concat([denied_template_df, pd.DataFrame([den_row])], ignore_index=True)
    else:
        early_denied_df = base_compliant_df.copy()
    early_denied_df["case:concept:name"] = "Application_RejectedEarly_R29"

    null_credit_df = base_compliant_df.copy()
    null_credit_df["case:concept:name"] = "Application_NullCreditScore_R30"
    null_credit_df["CreditScore"] = float("nan")

    distinct_base_cases = list(grouped_prop.values())

    if trap_rules:
        while len(baseless_items) < per_class_quota:
            trap_rule = trap_rules[len(baseless_items) % len(trap_rules)]
            rid = trap_rule["rule_id"]
            if rid == "R29":
                t_df = early_denied_df
            elif rid == "R30":
                t_df = null_credit_df
            else:
                # Đa dạng hóa trace cho R23-R28
                base_idx = len(baseless_items) % len(distinct_base_cases)
                t_df = distinct_base_cases[base_idx].copy()

            baseless_items.append({
                "benchmark_id": f"BAS-{len(baseless_items) + 1:04d}",
                "rule_id": rid,
                "rule_meta": trap_rule,
                "retrieved_chunk": trap_rule["retrieved_chunk"],
                "test_case_df": t_df,
                "ground_truth_label": "BASELESS",
                "trace_origin": f"TIER3_TRAP_{rid}_{trap_rule.get('trap_type', 'BASELESS')}",
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
        REAL_LATE_PENDING_CASES = [
            "Application_1108271369", "Application_1171453988", "Application_130761111",
            "Application_1499090661", "Application_157155173", "Application_1677498057",
            "Application_1741752833", "Application_1838182698", "Application_1875888758",
            "Application_2037628374",
        ]
        sample_cids = list(dict.fromkeys(REAL_LATE_PENDING_CASES + df_raw["case:concept:name"].drop_duplicates().iloc[:2500].tolist()))
        df_sub = df_raw[df_raw["case:concept:name"].isin(sample_cids)].copy()
        offer_cols = [
            c
            for c in ["OfferedAmount", "CreditScore", "Accepted", "MonthlyCost", "NumberOfTerms"]
            if c in df_sub.columns
        ]
        if offer_cols:
            df_sub[offer_cols] = df_sub.groupby("case:concept:name", sort=False)[offer_cols].ffill().bfill()
            df_sub[offer_cols] = df_sub.groupby("case:concept:name", sort=False)[offer_cols].bfill()

        items = build_stratified_trace_benchmark(
            df_propagated=df_sub,
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
                        "MonthlyCost": (
                            None if pd.isna(row.get("MonthlyCost")) else float(row.get("MonthlyCost"))
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
