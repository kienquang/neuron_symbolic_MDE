"""
Symbolic reasoning & verification module (Bước 3 - Tầng 3):
- Bước 3.1: verbalize_declare_ast & check_roundtrip_fidelity (OVAS + IJCAI 2025 + arXiv:2604.25031)
- Bước 3.2: Declare4Py & run_layer3_declare4py_verifier (Declare4Py + OVAS Vacuity Check + Janus stats)
- Bước 3.3: extract_concrete_trace_snapshots (OVAS Mục 3.4.6 Concrete Counterexample Snapshots)
"""

from .verbalizer_roundtrip import (
    check_roundtrip_fidelity,
    verbalize_declare_ast,
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
    "Declare4Py",
    "RuleCheckResult",
    "extract_concrete_trace_snapshots",
    "run_layer3_declare4py_verifier",
]
