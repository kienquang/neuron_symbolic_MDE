import json, sys
sys.stdout.reconfigure(encoding="utf-8")

j1 = json.load(open("results/completed_experiment_summary.json", encoding="utf-8"))
j2 = json.load(open("results/rq1_rq2_rq3_evaluation_tables.json", encoding="utf-8"))
assert j1 == j2, "Mismatch between summary files!"

print("Files match 100%!")
print("Table 1 One-Shot Overall:", j1["table1_rq1_oneshot"]["Overall Pipeline"])
print("Table 1 Full Overall:", j1["table1_rq1_full"]["Overall Pipeline"])
for cfg in j1["table2_rq2_ablation"]:
    print(f"Table 2 Config: {cfg['Configuration']} | Exec: {cfg['Executable_Rate (%)']} | Eq: {cfg['Eq_Rate (%)']} | F1: {cfg['Conformance_F1']}")
print("Table 3 Overall:", j1["table3_metrics"]["Trung bình Toàn hệ thống (Overall)"])
