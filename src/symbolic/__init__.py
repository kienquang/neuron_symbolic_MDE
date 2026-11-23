"""
Symbolic reasoning & verification module (Giai đoạn 3):
- Counterfactual Semantic Probing & Deterministic Verbalization (counterfactual_prober.py, verbalizer_roundtrip.py)
- Declare4Py Symbolic Conformance Engine & Log-Grounded Vacuity Check (declare4py_verifier.py)
- Deterministic Counterexample Snapshots (extract_concrete_trace_snapshots)
"""

from .verbalizer_roundtrip import (
    check_roundtrip_fidelity,
    verbalize_declare_ast,
)
from .counterfactual_prober import (
    generate_counterfactual_trace_mutant,
    verify_via_counterfactual_probing,
)
from .declare4py_verifier import (
    Declare4Py,
    RuleCheckResult,
    extract_concrete_trace_snapshots,
    run_layer3_declare4py_verifier,
)

__all__ = [
    "verbalize_declare_ast",
    "check_roundtrip_fidelity",
    "generate_counterfactual_trace_mutant",
    "verify_via_counterfactual_probing",
    "Declare4Py",
    "RuleCheckResult",
    "extract_concrete_trace_snapshots",
    "run_layer3_declare4py_verifier",
]
