import sys
import json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open('scratch/results_300_ablation.json', 'r', encoding='utf-8') as f:
    abl = json.load(f)

with open('scratch/results_baseline1_300.json', 'r', encoding='utf-8') as f:
    b1 = json.load(f)

print("=== BASELINE 1 (300 samples) ===")
print("Configuration:", b1.get("Configuration"))
print("Total Items:", b1.get("Total_Items"))
print("Macro Precision:", b1.get("Macro_Precision"))
print("Macro Recall:", b1.get("Macro_Recall"))
print("Macro F1:", b1.get("Macro_F1"))
print("Per-class:", json.dumps(b1.get("Per_Class_Metrics"), indent=2))

print("\n=== ABLATIONS & PROPOSED PIPELINE (300 samples) ===")
for k, v in abl.items():
    print(f"\nConfiguration: {k}")
    print(f"  Exec: {v.get('Executable_Rate (%)')}% | Eq: {v.get('Eq_Rate (%)')}%")
    print(f"  Macro P: {v.get('Macro_Precision')} | Macro R: {v.get('Macro_Recall')} | Macro F1: {v.get('Macro_F1')}")
    print(f"  Avg Retries: {v.get('Avg_Retry_Rounds')} | Time: {v.get('Avg_Verification_Time (s)')}s | Fidelity: {v.get('Citation_Fidelity (%)')}%")
    if "Per_Class_Metrics" in v:
        print("  Per Class:")
        for cls, m in v["Per_Class_Metrics"].items():
            print(f"    {cls}: P={m.get('Precision')}, R={m.get('Recall')}, F1={m.get('F1-Score')}")
