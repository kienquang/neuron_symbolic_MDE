"""
Model-Driven Engineering (MDE) module:
- Bước 2.1: DeclareConstraintAST, SemanticDecomposition & Layer 1 Schema Validator (OVAS + Declare4Py + Req2LTL)
- Bước 2.2: ProcessTypingEnvironment (Γ), δ(C, p) lookup & Layer 2 Type Conformance Checker (OVAS)
"""

from .constraint_ast import (
    BINARY_TEMPLATES,
    UNARY_TEMPLATES,
    DeclareConstraintAST,
    SemanticDecomposition,
    validate_layer1_ast,
)
from .typing_environment import (
    ProcessTypingEnvironment,
    check_layer1_and_layer2,
)

__all__ = [
    "UNARY_TEMPLATES",
    "BINARY_TEMPLATES",
    "SemanticDecomposition",
    "DeclareConstraintAST",
    "validate_layer1_ast",
    "ProcessTypingEnvironment",
    "check_layer1_and_layer2",
]
