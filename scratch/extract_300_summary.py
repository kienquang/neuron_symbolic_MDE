import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

data = json.load(open("scratch/results_300_ablation.json", encoding="utf-8"))

print("=== TABLE 2: ABLATION ON 300 SAMPLES ===")
for name, res in data.items():
    print(f"{name:<60} | Exec: {res['Executable_Rate (%)']}% | Eq: {res['Eq_Rate (%)']}% | F1: {res['Macro_F1']:.4f}")

full = data["Full Neuro-Symbolic Pipeline (Đề xuất)"]
print("\n=== TABLE 3: PER-CLASS BREAKDOWN ON 300 SAMPLES (FULL PIPELINE) ===")
for cls_name in ["ENTAILED", "CONTRADICTED", "BASELESS"]:
    m = full["Per_Class_Metrics"][cls_name]
    print(f"{cls_name:<15}: P={m['Precision']:.4f}, R={m['Recall']:.4f}, F1={m['F1-Score']:.4f}, Retries={m['Avg_Retries']:.2f}, Time={m['Avg_Verification_Time (s)']:.4f}s, Cit={m['Citation_Fidelity (%)']:.1f}%")

print(f"\nOverall Macro: P={full['Macro_Precision']:.4f}, R={full['Macro_Recall']:.4f}, F1={full['Macro_F1']:.4f}, Retries={full['Avg_Retry_Rounds']:.2f}, Time={full['Avg_Verification_Time (s)']:.4f}s, Cit={full['Citation_Fidelity (%)']:.1f}%")
