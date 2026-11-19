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
from .deontic_mde_compiler import (
    UNMAPPED_ATTR_TOKEN,
    build_constrained_deontic_schema,
    check_behavioral_profile_grounding,
    compile_deontic_to_declare4py,
    format_behavioral_profile_for_prompt,
    validate_and_compile_deontic_or_ast,
)

__all__ = [
    "UNARY_TEMPLATES",
    "BINARY_TEMPLATES",
    "SemanticDecomposition",
    "DeclareConstraintAST",
    "validate_layer1_ast",
    "ProcessTypingEnvironment",
    "check_layer1_and_layer2",
    "UNMAPPED_ATTR_TOKEN",
    "build_constrained_deontic_schema",
    "check_behavioral_profile_grounding",
    "compile_deontic_to_declare4py",
    "format_behavioral_profile_for_prompt",
    "validate_and_compile_deontic_or_ast",
]
