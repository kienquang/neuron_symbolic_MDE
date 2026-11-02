import sys, os

with open('src/evaluation/benchmark_builder.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_r15_r22 = """    {
        "rule_id": "R15",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 5(1)",
        "template": "Response",
        "act_a": "O_Sent (mail and online)",
        "act_b": "O_Returned",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 14,
        "is_trap": False,
        "description": "Quy chuẩn thông tin tiền hợp đồng theo Điều 5(1): Khoảng thời gian từ lúc gửi đề nghị O_Sent (mail and online) đến lúc khách gửi trả O_Returned <= 14 ngày lịch.",
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
        "description": "Thời hạn rút lui theo Điều 14(3): Khách hàng chỉ được hủy bỏ hồ sơ (A_Cancelled) trong vòng 30 ngày lịch sau khi nhận văn bản đề nghị O_Sent.",
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
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "W_Validate application",
        "act_b": "O_Accepted",
        "attr": "OfferedAmount",
        "op": ">",
        "val": 10000.0,
        "time_max": None,
        "is_trap": False,
        "description": "Thẩm định khả năng trả nợ nâng cao theo Điều 8(1): Với các đề nghị vay trên 10.000 EUR, bắt buộc qua bước thẩm định W_Validate application trước O_Accepted.",
    },
    {
        "rule_id": "R19",
        "tier": "Tier2_TemporalData",
        "complexity_tier": "Tier 2: Temporal & Data-Aware",
        "article_id": "Article 13(1)",
        "template": "Precedence",
        "act_a": "A_Complete",
        "act_b": "O_Cancelled",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 30,
        "is_trap": False,
        "description": "Thời hạn chấm dứt theo Điều 13(1): Việc hủy đề nghị vay O_Cancelled chỉ được diễn ra trong vòng 30 ngày sau khi hoàn tất hồ sơ A_Complete.",
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
        "article_id": "Article 2(3)",
        "template": "Response",
        "act_a": "A_Create Application",
        "act_b": "A_Pending",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": 90,
        "is_trap": False,
        "description": "Quy chuẩn thời hạn tín dụng thấu chi hoàn trả trong 3 tháng (90 ngày) theo Điều 2(3): Toàn bộ chu trình từ lúc nộp đơn (A_Create Application) đến lúc tất toán/duyệt (A_Pending) <= 90 ngày.",
    },"""

new_r15_r22 = """    {
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
        "description": "Quy chuẩn thời hạn rút lui theo Điều 14(1): Khách hàng có quyền hủy bỏ hồ sơ (A_Cancelled) trong vòng 14 ngày lịch sau khi nhận đề nghị O_Sent (mail and online).",
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
        "description": "Thời hạn rút lui theo Điều 14(3): Khách hàng chỉ được hủy bỏ hồ sơ (A_Cancelled) trong vòng 30 ngày lịch sau khi nhận văn bản đề nghị O_Sent.",
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
        "article_id": "Article 8(1)",
        "template": "Precedence",
        "act_a": "W_Validate application",
        "act_b": "O_Accepted",
        "attr": None,
        "op": None,
        "val": None,
        "time_max": None,
        "is_trap": False,
        "description": "Nghĩa vụ đánh giá khả năng trả nợ của người tiêu dùng theo Điều 8(1): Trước khi ngân hàng chấp thuận đề nghị vay (O_Accepted), hồ sơ bắt buộc phải hoàn thành bước thẩm định (W_Validate application).",
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
        "description": "Quy chuẩn chấm dứt hợp đồng mở theo Điều 13(1): Khi người tiêu dùng thực hiện quyền chấm dứt (A_Cancelled), việc hủy bỏ đề nghị tín dụng (O_Cancelled) phải được thực hiện.",
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
        "description": "Quy chuẩn mức sàn tín dụng theo Điều 2(2)(c): Số tiền đề nghị vay case:RequestedAmount tại A_Create Application không được thấp hơn mức sàn 200 EUR.",
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
        "description": "Quy chuẩn trần hạn mức tín dụng theo Điều 2(2)(c): Số tiền đề nghị vay case:RequestedAmount tại A_Create Application không được vượt quá mức trần 75.000 EUR.",
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
        "description": "Quy chuẩn thời hạn xử lý sau khi rút lui theo Điều 14(3): Khi khách hàng thông báo rút lui (A_Cancelled), đề nghị vay phải được hủy (O_Cancelled) trong vòng 30 ngày lịch.",
    },"""

# Normalize CRLF
content_norm = content.replace('\r\n', '\n')
old_norm = old_r15_r22.replace('\r\n', '\n')
new_norm = new_r15_r22.replace('\r\n', '\n')

assert old_norm in content_norm, "old_norm not found!"
content_norm = content_norm.replace(old_norm, new_norm)

# Update lines 820-823 (R18 OfferedAmount check)
old_r18_check = """                if rid == "R18":
                    amt = case_df["OfferedAmount"].max()
                    if pd.isna(amt) or amt <= 10000:
                        continue"""
if old_r18_check in content_norm:
    content_norm = content_norm.replace(old_r18_check, "                # R18 now applies to all cases")
    print("Replaced R18 check in build_stratified_trace_benchmark")

# Update lines 848-851 (R22 check)
old_r22_check = """                if rid == "R22" and act_b not in acts:
                    # R22 quy định thời hạn 90 ngày giải ngân. Để kiểm tra vi phạm thời hạn thực tế,
                    # sự kiện A_Pending bắt buộc phải xảy ra nhưng muộn hơn 90 ngày (không lấy hồ sơ bị huỷ sớm)
                    continue"""
if old_r22_check in content_norm:
    content_norm = content_norm.replace(old_r22_check, "                # R22 Response check")
    print("Replaced R22 check in build_stratified_trace_benchmark")

# Update fault injection for case:RequestedAmount
old_inj = """            elif gast.activation_attr in ("case:RequestedAmount", "RequestedAmount"):
                injected_df["case:RequestedAmount"] = 500.0
                injected_df["RequestedAmount"] = 500.0"""

new_inj = """            elif gast.activation_attr in ("case:RequestedAmount", "RequestedAmount"):
                if gast.activation_op == ">=":
                    injected_df["case:RequestedAmount"] = 100.0
                    injected_df["RequestedAmount"] = 100.0
                else:
                    injected_df["case:RequestedAmount"] = 85000.0
                    injected_df["RequestedAmount"] = 85000.0"""
if old_inj in content_norm:
    content_norm = content_norm.replace(old_inj, new_inj)
    print("Replaced injected RequestedAmount")

with open('src/evaluation/benchmark_builder.py', 'w', encoding='utf-8') as f:
    f.write(content_norm)

print("Successfully updated src/evaluation/benchmark_builder.py!")
