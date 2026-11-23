"""
Model-Driven Engineering (MDE) & Behavioral-Aware Process Compilation module:
- DeonticNormativeFrame (PIM) -> Behavioral-Aware M2M Compiler -> DeclareConstraintAST (PSM)
- ProcessSchemaValidator & Causal Attribute Availability Checking
- Behavioral Profile Grounding (DFG Adjacency, Strict Causal Direction, Mutual Exclusion, Lifecycle Consistency)
"""

from .constraint_ast import (
    BINARY_TEMPLATES,
    UNARY_TEMPLATES,
    DeclareConstraintAST,
    SemanticDecomposition,
    validate_declare_ast,
    validate_layer1_ast,
)
from .typing_environment import (
    ProcessSchemaValidator,
    ProcessTypingEnvironment,
    check_layer1_and_layer2,
    validate_ast_against_process_schema,
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
    "validate_declare_ast",
    "validate_layer1_ast",
    "ProcessSchemaValidator",
    "ProcessTypingEnvironment",
    "validate_ast_against_process_schema",
    "check_layer1_and_layer2",
    "UNMAPPED_ATTR_TOKEN",
    "build_constrained_deontic_schema",
    "check_behavioral_profile_grounding",
    "compile_deontic_to_declare4py",
    "format_behavioral_profile_for_prompt",
    "validate_and_compile_deontic_or_ast",
]
