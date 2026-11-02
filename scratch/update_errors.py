with open('src/evaluation/benchmark_builder.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_err = """        "R15": {
            "article_id": "Article 5(1)",
            "template_name": "Response",
            "activation_activity": "O_Sent (mail and online)",
            "target_activity": "O_Returned",
            "time_min": 0,
            "time_max": 30,
            "time_unit": "d",
        },
        "R18": {
            "article_id": "Article 8(1)",
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
        },"""

new_err = """        "R15": {
            "article_id": "Article 14(1)",
            "template_name": "Response",
            "activation_activity": "O_Sent (mail and online)",
            "target_activity": "A_Cancelled",
            "time_min": 0,
            "time_max": 30,
            "time_unit": "d",
        },
        "R18": {
            "article_id": "Article 8(1)",
            "template_name": "Response",
            "activation_activity": "O_Accepted",
            "target_activity": "W_Validate application",
            "time_min": 0,
            "time_max": None,
            "time_unit": "d",
        },
        "R19": {
            "article_id": "Article 13(1)",
            "template_name": "Precedence",
            "activation_activity": "A_Cancelled",
            "target_activity": "O_Cancelled",
            "time_min": 0,
            "time_max": 30,
            "time_unit": "d",
        },"""

assert old_err in c, "old_err not found!"
c = c.replace(old_err, new_err)
with open('src/evaluation/benchmark_builder.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Updated initial_llm_errors successfully!")
