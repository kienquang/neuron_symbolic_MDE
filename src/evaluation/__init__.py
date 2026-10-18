"""
Evaluation, 3-Valued Safety Classification & Accountable Audit Trail module (Bước 4):
- Bước 4.1: evaluate_trace_safety_and_status (OVAS Value-Condition Separation <v, Φ> + RT4CHART 3-Valued Labeling)
- Bước 4.2: check_single_trace_semantics & build_justification_tree (xpSHACL Justification Tree + VERGE Minimal Correction)
- Bước 4.3: generate_accountable_explanation & verify_posthoc_grounding (CEUR Vol-4259 + Know Your Limits Grounding Guard)
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

__all__ = [
    "evaluate_trace_safety_and_status",
    "check_single_trace_semantics",
    "build_justification_tree",
    "DeterministicAuditNarratorClient",
    "generate_accountable_explanation",
    "verify_posthoc_grounding",
]
