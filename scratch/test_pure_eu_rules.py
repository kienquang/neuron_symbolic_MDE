import sys, os, json
sys.path.insert(0, os.path.abspath('.'))
sys.stdout.reconfigure(encoding='utf-8')

from src.symbolic.verbalizer_roundtrip import check_roundtrip_fidelity
from src.evaluation.real_llm_client import RealLLMClient

with open('data/processed/directive_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
chunks_by_id = {c['article_id']: c for c in chunks}

llm = RealLLMClient(cache_file='real_llm_cache.json')

test_cases = [
    # R15: Article 14(1) with 14 calendar days
    {
        'rule_id': 'R15',
        'article_id': 'Article 14(1)',
        'template_name': 'Response',
        'activation_activity': 'O_Sent (mail and online)',
        'target_activity': 'A_Cancelled',
        'activation_attr': None,
        'activation_op': None,
        'activation_val': None,
        'time_min': None,
        'time_max': 14,
        'time_unit': 'd',
        'desc': 'Quy chuẩn thời hạn rút lui theo Điều 14(1): Khách hàng có quyền hủy bỏ hồ sơ (A_Cancelled) trong vòng 14 ngày lịch sau khi nhận đề nghị O_Sent (mail and online).'
    },
    # R18: Article 8(1) without 10,000 threshold
    {
        'rule_id': 'R18',
        'article_id': 'Article 8(1)',
        'template_name': 'Precedence',
        'activation_activity': 'W_Validate application',
        'target_activity': 'O_Accepted',
        'activation_attr': None,
        'activation_op': None,
        'activation_val': None,
        'time_min': None,
        'time_max': None,
        'time_unit': None,
        'desc': 'Nghĩa vụ đánh giá khả năng trả nợ theo Điều 8(1): Trước khi chấp nhận đề nghị vay (O_Accepted), ngân hàng bắt buộc phải qua bước thẩm định (W_Validate application).'
    },
    # R19: Article 13(1) without 30-day restriction
    {
        'rule_id': 'R19',
        'article_id': 'Article 13(1)',
        'template_name': 'Precedence',
        'activation_activity': 'A_Complete',
        'target_activity': 'O_Cancelled',
        'activation_attr': None,
        'activation_op': None,
        'activation_val': None,
        'time_min': None,
        'time_max': None,
        'time_unit': None,
        'desc': 'Quy chuẩn quyền chấm dứt hợp đồng mở theo Điều 13(1): Việc hủy đề nghị vay O_Cancelled chỉ được diễn ra sau khi hoàn tất hồ sơ A_Complete.'
    },
    # R20: Article 2(2) floor 200 EUR on case:RequestedAmount
    {
        'rule_id': 'R20',
        'article_id': 'Article 2(2)',
        'template_name': 'Existence',
        'activation_activity': 'A_Create Application',
        'target_activity': None,
        'activation_attr': 'case:RequestedAmount',
        'activation_op': '>=',
        'activation_val': 200.0,
        'time_min': None,
        'time_max': None,
        'time_unit': None,
        'desc': 'Quy chuẩn mức sàn tín dụng theo Điều 2(2)(c): Số tiền đề nghị vay case:RequestedAmount tại A_Create Application không được thấp hơn mức sàn 200 EUR.'
    },
    # R21: Article 2(2) ceiling 75,000 EUR on case:RequestedAmount
    {
        'rule_id': 'R21',
        'article_id': 'Article 2(2)',
        'template_name': 'Existence',
        'activation_activity': 'A_Create Application',
        'target_activity': None,
        'activation_attr': 'case:RequestedAmount',
        'activation_op': '<=',
        'activation_val': 75000.0,
        'time_min': None,
        'time_max': None,
        'time_unit': None,
        'desc': 'Quy chuẩn trần hạn mức tín dụng theo Điều 2(2)(c): Số tiền đề nghị vay case:RequestedAmount tại A_Create Application không được vượt quá mức trần 75.000 EUR.'
    },
    # R22: Article 14(3) 30 days settlement after withdrawal
    {
        'rule_id': 'R22',
        'article_id': 'Article 14(3)',
        'template_name': 'Response',
        'activation_activity': 'A_Cancelled',
        'target_activity': 'O_Cancelled',
        'activation_attr': None,
        'activation_op': None,
        'activation_val': None,
        'time_min': None,
        'time_max': 30,
        'time_unit': 'd',
        'desc': 'Quy chuẩn thời hạn xử lý sau khi rút lui theo Điều 14(3): Khi khách hàng thông báo rút lui (A_Cancelled), đề nghị vay phải được hủy (O_Cancelled) trong vòng 30 ngày lịch.'
    },
]

for tc in test_cases:
    rid = tc['rule_id']
    chunk = chunks_by_id.get(tc['article_id'])
    rule_meta = {'rule_id': rid, 'description': tc['desc'], 'is_baseless_trap': False}
    ast_dict = {
        'article_id': tc['article_id'],
        'template_name': tc['template_name'],
        'activation_activity': tc['activation_activity'],
        'target_activity': tc['target_activity'],
        'activation_attr': tc['activation_attr'],
        'activation_op': tc['activation_op'],
        'activation_val': tc['activation_val'],
        'time_min': tc['time_min'],
        'time_max': tc['time_max'],
        'time_unit': tc['time_unit'],
    }
    ok, msg = check_roundtrip_fidelity(ast_dict, chunk, llm, rule_meta=rule_meta)
    print(f"Rule {rid} ({tc['article_id']}): ok={ok}")
    if not ok:
        print(f"   Error: {msg[:120]}...")
