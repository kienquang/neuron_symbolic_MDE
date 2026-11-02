import sys
sys.path.insert(0, ".")
import json
import pandas as pd
from src.evaluation.benchmark_builder import build_normative_rule_benchmark
from src.evaluation.experiment_runner import evaluate_rq1_complexity_tiers, classify_semantic_equivalence, check_layer1_and_layer2, BenchmarkExperimentLLMClient
from src.symbolic.verbalizer_roundtrip import check_roundtrip_fidelity
from src.mde.constraint_ast import DeclareConstraintAST

with open("data/processed/directive_chunks.json", encoding="utf-8") as f:
    chunks = {c["article_id"]: c for c in json.load(f)}
with open("data/processed/process_schema.json", encoding="utf-8") as f:
    schema = json.load(f)

rules = build_normative_rule_benchmark(chunks)

df_mini = pd.DataFrame([
    {"case:concept:name": "1", "concept:name": "A_Create Application", "case:RequestedAmount": 15000.0, "OfferedAmount": float("nan"), "CreditScore": float("nan"), "NumberOfTerms": float("nan"), "time:timestamp": pd.Timestamp("2016-05-01T08:00:00Z")},
    {"case:concept:name": "1", "concept:name": "O_Create Offer", "case:RequestedAmount": 15000.0, "OfferedAmount": 15000.0, "CreditScore": 800.0, "NumberOfTerms": 24.0, "time:timestamp": pd.Timestamp("2016-05-01T10:00:00Z")},
    {"case:concept:name": "1", "concept:name": "O_Sent (mail and online)", "case:RequestedAmount": 15000.0, "OfferedAmount": float("nan"), "CreditScore": float("nan"), "NumberOfTerms": float("nan"), "time:timestamp": pd.Timestamp("2016-05-01T11:00:00Z")},
    {"case:concept:name": "1", "concept:name": "W_Validate application", "case:RequestedAmount": 15000.0, "OfferedAmount": float("nan"), "CreditScore": float("nan"), "NumberOfTerms": float("nan"), "time:timestamp": pd.Timestamp("2016-05-02T10:00:00Z")},
    {"case:concept:name": "1", "concept:name": "O_Accepted", "case:RequestedAmount": 15000.0, "OfferedAmount": float("nan"), "CreditScore": float("nan"), "NumberOfTerms": float("nan"), "time:timestamp": pd.Timestamp("2016-05-03T10:00:00Z")},
    {"case:concept:name": "1", "concept:name": "A_Cancelled", "case:RequestedAmount": 15000.0, "OfferedAmount": float("nan"), "CreditScore": float("nan"), "NumberOfTerms": float("nan"), "time:timestamp": pd.Timestamp("2016-05-04T10:00:00Z")},
    {"case:concept:name": "1", "concept:name": "O_Cancelled", "case:RequestedAmount": 15000.0, "OfferedAmount": float("nan"), "CreditScore": float("nan"), "NumberOfTerms": float("nan"), "time:timestamp": pd.Timestamp("2016-05-05T10:00:00Z")},
])

client = BenchmarkExperimentLLMClient(log_df=df_mini)

for r in rules:
    if r["tier"] in ("Tier1_ControlFlow", "Tier2_TemporalData"):
        chunk = r["retrieved_chunk"]
        feedback = ""
        ast_obj = None
        for attempt in range(5):
            raw = client.generate_ast(chunk, schema, feedback=feedback, rule_meta=r)
            ok_l12, res_l12 = check_layer1_and_layer2(raw, schema, chunk)
            if not ok_l12:
                feedback = str(res_l12)
                continue
            ast_cand = DeclareConstraintAST(**res_l12)
            rt_ok, rt_msg = check_roundtrip_fidelity(ast_cand.model_dump(), chunk, client)
            if rt_ok:
                ast_obj = ast_cand
                break
            feedback = rt_msg
        cat = classify_semantic_equivalence(ast_obj, r["gold_ast"], df_mini)
        print(f"{r['rule_id']}: {cat} (ast_obj is None: {ast_obj is None})")
