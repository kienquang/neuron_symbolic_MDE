import json, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from src.evaluation.benchmark_builder import BENCHMARK_RULES

# 22 normative rules and their natural business descriptions
# Completely free of explicit variable names like A_Concept, OfferedAmount, etc.
NATURAL_POLICY_DESCRIPTIONS = {
    # --- TIER 1: CONTROL-FLOW CONSTRAINTS (12 rules: R01 - R12) ---
    "R01": "Để thu thập đầy đủ thông tin từ người vay phục vụ việc đánh giá khả năng trả nợ theo Điều 8(1), quy trình ngân hàng bắt buộc phải tiếp nhận hồ sơ vay của khách hàng trước khi tiến hành bước đánh giá sơ bộ hồ sơ.",
    "R02": "Nghĩa vụ đánh giá khả năng trả nợ theo Điều 8(1): Bước đánh giá sơ bộ hồ sơ bắt buộc phải hoàn thành trước khi hồ sơ vay được ngân hàng phê duyệt sơ bộ.",
    "R03": "Nghĩa vụ đánh giá khả năng trả nợ theo Điều 8(1): Hồ sơ vay bắt buộc phải được phê duyệt sơ bộ trước khi ngân hàng tạo lập đề nghị vay chính thức cho khách hàng.",
    "R04": "Nghĩa vụ cung cấp thông tin tiền hợp đồng theo Điều 5(1): Ngay trước khi văn bản đề nghị vay được ghi nhận chính thức vào hệ thống, ngân hàng bắt buộc phải thực hiện bước tạo lập đề nghị vay.",
    "R05": "Nghĩa vụ cung cấp thông tin tiền hợp đồng theo Điều 5(1): Văn bản đề nghị vay phải được tạo lập trên hệ thống trước khi gửi thông tin tiền hợp đồng cho khách hàng qua thư hoặc trực tuyến.",
    "R06": "Nghĩa vụ cung cấp thông tin tiền hợp đồng theo Điều 5(1): Thông tin tiền hợp đồng bắt buộc phải được gửi tới người tiêu dùng qua thư hoặc trực tuyến trước khi hồ sơ chuyển sang trạng thái hoàn tất thủ tục.",
    "R07": "Quy định về hình thức hợp đồng theo Điều 10(1): Khách hàng bắt buộc phải chấp thuận đề nghị vay trước khi ngân hàng chuyển hồ sơ sang bước chờ giải ngân tiền vay.",
    "R08": "Nghĩa vụ thẩm định khả năng trả nợ theo Điều 8(1): Tác vụ thẩm định chi tiết hồ sơ của nhân viên ngân hàng phải diễn ra trước khi hồ sơ chuyển sang trạng thái xác thực trên hệ thống.",
    "R09": "Quy chuẩn thông báo khi từ chối theo Điều 9(2): Khi hồ sơ bị từ chối do kết quả tra cứu cơ sở dữ liệu, đề nghị vay tương ứng bắt buộc phải chuyển sang trạng thái từ chối.",
    "R10": "Quy chuẩn quản lý rủi ro và chấm dứt theo Điều 13(2): Một hồ sơ vay một khi đã bị từ chối thì tuyệt đối không được phép tiến hành giải ngân tiền vay.",
    "R11": "Quy chuẩn vận hành quyền rút lui hợp đồng theo Điều 14(1): Khi người tiêu dùng thông báo hủy hoặc rút lui hồ sơ vay, đề nghị vay liên kết bắt buộc phải được hủy bỏ.",
    "R12": "Nghĩa vụ giải thích thỏa đáng theo Điều 5(6): Ngân hàng bắt buộc phải thực hiện cuộc gọi tư vấn giải thích thỏa đáng cho khách hàng sau khi tạo đề nghị trước khi hồ sơ chuyển sang trạng thái xác thực.",

    # --- TIER 2: TEMPORAL & DATA-AWARE CONSTRAINTS (10 rules: R13 - R22) ---
    "R13": "Quy chuẩn mức sàn hạn mức tín dụng theo Điều 2(2)(c): Đề nghị vay do ngân hàng tạo lập phải có số tiền đề nghị không được thấp hơn mức sàn luật định là 200 EUR.",
    "R14": "Quy chuẩn mức trần hạn mức tín dụng theo Điều 2(2)(c): Đề nghị vay do ngân hàng tạo lập phải có số tiền đề nghị không được vượt quá mức trần luật định là 75.000 EUR.",
    "R15": "Quy chuẩn thời hạn rút lui hợp đồng theo Điều 14(1): Khách hàng có quyền thông báo hủy hồ sơ vay trong vòng 14 ngày lịch sau khi ngân hàng gửi thông tin đề nghị qua thư hoặc trực tuyến.",
    "R16": "Quy chuẩn giới hạn thời gian thông báo theo Điều 14(3): Khách hàng chỉ có thể thực hiện quyền hủy hồ sơ vay trong thời hạn tối đa 30 ngày lịch sau khi ngân hàng gửi văn bản đề nghị.",
    "R17": "Nghĩa vụ thẩm định điểm tín dụng theo Điều 8(1): Trước khi ngân hàng giải ngân khoản vay, đề nghị vay tương ứng bắt buộc phải có điểm tín dụng hợp lệ lớn hơn 0.",
    "R18": "Nghĩa vụ đánh giá khả năng trả nợ theo Điều 8(1): Trước khi ngân hàng chấp thuận đề nghị vay, hồ sơ bắt buộc phải hoàn thành tác vụ thẩm định chi tiết của nhân viên tín dụng.",
    "R19": "Quy chuẩn chấm dứt hợp đồng mở theo Điều 13(1): Khi người tiêu dùng thực hiện quyền chấm dứt thỏa thuận vay, việc hủy bỏ đề nghị tín dụng tương ứng bắt buộc phải được thực hiện.",
    "R20": "Quy chuẩn hạn mức số tiền vay theo Điều 2(2)(c): Số tiền vay do khách hàng yêu cầu tại bước nộp đơn ban đầu không được thấp hơn mức sàn luật định là 200 EUR.",
    "R21": "Quy chuẩn hạn mức số tiền vay theo Điều 2(2)(c): Số tiền vay do khách hàng yêu cầu tại bước nộp đơn ban đầu không được vượt quá mức trần luật định là 75.000 EUR.",
    "R22": "Quy chuẩn thời hạn xử lý sau khi rút lui theo Điều 14(3): Khi khách hàng thông báo rút lui hoặc hủy hồ sơ, đề nghị vay tương ứng bắt buộc phải được hủy bỏ trong vòng 30 ngày lịch.",

    # --- TIER 3: BASELESS TRAPS (8 rules: R23 - R30) ---
    "R23": "Quy định gài bẫy phạm vi: Yêu cầu áp dụng thời hạn 8 ngày xử lý hồ sơ không đầy đủ dựa trên Điều 7(1).",
    "R24": "Quy định gài bẫy nguồn dẫn: Gán quy trình gọi điện thu thập bổ sung hồ sơ thiếu vào Điều 7.",
    "R25": "Quy định gài bẫy ngoài phạm vi: Ép buộc áp dụng Chỉ thị tín dụng tiêu dùng cho các hợp đồng thế chấp bất động sản nhà ở.",
    "R26": "Quy định gài bẫy ngưỡng định lượng: Bắt buộc người vay phải đạt điểm tín dụng giả định từ 750 điểm trở lên theo Điều 8(1).",
    "R27": "Quy định gài bẫy thuộc tính ngoài lược đồ: Yêu cầu kiểm tra mức phí bồi thường trả nợ trước hạn theo Điều 16(2).",
    "R28": "Quy định gài bẫy công thức lãi suất: Bắt buộc kiểm tra cột tỷ lệ phần trăm chi phí hàng năm theo công thức của Điều 19(1).",
    "R29": "Quy định gài bẫy thuộc tính khuyết: Kiểm tra số tiền đề nghị vay trên những hồ sơ đã bị từ chối sớm trước khi tạo đề nghị.",
    "R30": "Quy định gài bẫy điều kiện thế chấp: Bắt buộc khách hàng phải cung cấp tài sản bảo đảm thế chấp theo Điều 8(1).",
}

print(f"Total natural business descriptions: {len(NATURAL_POLICY_DESCRIPTIONS)}")
