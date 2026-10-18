"""
Evaluation, 3-Valued Safety Classification, Accountable Audit Trail & Benchmark Runner module (Bước 4 & Thực nghiệm RQ1-RQ3):
- Bước 4.1: evaluate_trace_safety_and_status (OVAS Value-Condition Separation <v, Φ> + RT4CHART 3-Valued Labeling)
- Bước 4.2: check_single_trace_semantics & build_justification_tree (xpSHACL Justification Tree + VERGE Minimal Correction)
- Bước 4.3: generate_accountable_explanation & verify_posthoc_grounding (CEUR Vol-4259 + Know Your Limits Grounding Guard)
- Thực nghiệm RQ1, RQ2, RQ3: build_normative_rule_benchmark, build_stratified_trace_benchmark, run_ablation_experiment
"""

from .trace_safety_classifier import evaluate_trace_safety_and_status
from .justification_tree import (
    build_justification_tree,
    check_single_trace_semantics,
)
from .grounded_auditor import (
    DeterministicAuditNarratorClient,
    generate_accountable_explanation,
    verify_posthoc_grounding,
)
from .benchmark_builder import (
    build_normative_rule_benchmark,
    build_stratified_trace_benchmark,
)
from .experiment_runner import (
    BenchmarkExperimentLLMClient,
    check_layer1_and_layer2,
    classify_semantic_equivalence,
    evaluate_rq1_complexity_tiers,
    run_ablation_experiment,
    run_vanilla_rag_baseline,
)

__all__ = [
    "evaluate_trace_safety_and_status",
    "check_single_trace_semantics",
    "build_justification_tree",
    "DeterministicAuditNarratorClient",
    "generate_accountable_explanation",
    "verify_posthoc_grounding",
    "build_normative_rule_benchmark",
    "build_stratified_trace_benchmark",
    "BenchmarkExperimentLLMClient",
    "check_layer1_and_layer2",
    "classify_semantic_equivalence",
    "evaluate_rq1_complexity_tiers",
    "run_ablation_experiment",
    "run_vanilla_rag_baseline",
]
