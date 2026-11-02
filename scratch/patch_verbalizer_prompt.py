from pathlib import Path

file_path = Path("src/symbolic/verbalizer_roundtrip.py")
content = file_path.read_text(encoding="utf-8")

old_text = '''Context:

In business process modeling for financial institutions, statutory principles (such as creditworthiness assessments under Article 8, pre-contractual disclosures under Article 5, contract formalization and agreement execution before credit performance under Article 10, statutory withdrawal under Article 14, and agreement termination under Article 13) are operationalized into concrete workflow steps and lifecycle state transitions.

- Legitimate Operational Implementations (Classify as EQUIVALENT):

   1. Workflow state transitions and prerequisite steps that record, prepare, or execute statutory actions and policy requirements.

   2. Positive operationalization of statutory scope thresholds: When Article 2(2)(c) excludes credit agreements < 200 EUR or > 75 000 EUR from consumer credit rules, an atomic DECLARE constraint enforcing EITHER the statutory floor (OfferedAmount >= 200.0) OR the statutory ceiling (OfferedAmount <= 75000.0) is EACH an independent, fully legitimate operationalization. You MUST classify each single-bound constraint as EQUIVALENT (do NOT require both bounds in a single constraint, as DECLARE ASTs represent atomic rules).

   3. If the candidate constraint faithfully operationalizes the stated Bank Operational Policy Requirement (e.g. establishing contract execution through customer acceptance prior to loan disbursement under contract formalization rules), you MUST classify it as EQUIVALENT.

- Do NOT classify a constraint as BASELESS simply because specific concrete IT activity names do not appear verbatim in the Directive text, provided the operationalization aligns with the policy intent.

- STRICTLY classify as BASELESS if and only if:

   1. The constraint invents arbitrary, unauthorized quantitative thresholds (e.g. minimum CreditScore >= 750 or fabricated interest rates/penalties);

   2. The transaction or product is entirely unrelated to consumer credit (e.g. real estate mortgage loans or pawnshop pledges);

   3. The claimed rule directly contradicts the legal text.



Provide compiler-style diagnostic feedback WITHOUT revealing any benchmark ground-truth answers.

Return JSON only: {{"verdict": "EQUIVALENT" | "REVERSED_ORDER" | "THRESHOLD_MISMATCH" | "BASELESS", "diagnostic_feedback": "..."}}'''

new_text = '''Context:

In business process modeling for financial institutions, statutory principles (such as creditworthiness assessments under Article 8, pre-contractual disclosures under Article 5, contract formalization and agreement execution before credit performance under Article 10, statutory withdrawal under Article 14, and agreement termination under Article 13) are operationalized into concrete workflow steps and lifecycle state transitions.

DECLARE Template Semantics:
- 'Precedence(A, B)': Activity A is a required prerequisite for Activity B (A must happen before B). Back-translated as: "Whenever 'B' occurs, 'A' must have occurred BEFORE it." This means A occurs before B. Do NOT classify as reversed when the policy specifies A before B.
- 'Chain Precedence(A, B)': Activity A must occur IMMEDIATELY before Activity B.
- 'Response(A, B)': Activity A triggers Activity B (B must occur after A).
- 'Not Co-Existence(A, B)': Activities A and B cannot both occur in the same case.

Lifecycle Activity Mapping & Disambiguation:
- Preliminary assessment / intake concept evaluation ('đánh giá sơ bộ'): corresponds to 'A_Concept' (application concept state), NOT detailed staff verification 'W_Validate application'.
- Preliminary application approval ('phê duyệt sơ bộ hồ sơ'): corresponds to 'A_Accepted', NOT validation state 'A_Validating'.
- Offer recorded on system ('văn bản đề nghị vay được ghi nhận chính thức vào hệ thống'): corresponds to 'O_Created' (offer recorded state), preceded immediately by 'O_Create Offer' ('Chain Precedence').
- Dispatch of pre-contractual terms ('gửi thông tin tiền hợp đồng'): corresponds to 'O_Sent (mail and online)'.
- Staff advice call ('cuộc gọi tư vấn giải thích thỏa đáng'): corresponds to 'W_Call after offers'.
- Customer acceptance of offer ('khách hàng chấp thuận đề nghị vay'): corresponds to 'O_Accepted' (offer accepted), NOT 'A_Accepted' (application intake accepted).
- Loan disbursement ('giải ngân tiền vay' / credit performance): corresponds to 'A_Pending'.
- Offer rejection upon denial ('đề nghị vay chuyển sang từ chối'): corresponds to 'O_Refused' following 'A_Denied'.
- Offer cancellation upon withdrawal ('đề nghị vay liên kết phải được hủy bỏ'): corresponds to 'O_Cancelled' following 'A_Cancelled'.

Legitimate Operational Implementations (Classify as EQUIVALENT):
1. Candidate AST uses the exact workflow steps and lifecycle state transitions aligned with the Bank Operational Policy Requirement.
2. Scope thresholds: When Article 2(2)(c) excludes credit agreements < 200 EUR or > 75 000 EUR, an atomic DECLARE constraint enforcing EITHER the floor (OfferedAmount >= 200.0) OR ceiling (OfferedAmount <= 75000.0) is EACH an independent, legitimate operationalization. Classify each single-bound constraint as EQUIVALENT.

Classify as SEMANTIC_MISMATCH or REVERSED_ORDER if:
1. The candidate AST confuses preliminary concept evaluation ('A_Concept') with detailed verification ('W_Validate application'), or confuses 'O_Accepted' with 'A_Accepted', or selects the wrong workflow step. Provide clear diagnostic feedback explaining the lifecycle distinction so the model can correct its choice.
2. The candidate AST inverts prerequisite/consequence order.

STRICTLY classify as BASELESS if and only if:
1. The constraint invents arbitrary, unauthorized quantitative thresholds (e.g. minimum CreditScore >= 750, fabricated interest rates/penalties, or 8-day deadlines without basis in the directive);
2. The transaction or product is entirely unrelated to consumer credit (e.g. real estate mortgage loans or pawnshop pledges);
3. The claimed rule directly contradicts the legal text.

Provide compiler-style diagnostic feedback WITHOUT revealing any benchmark ground-truth answers.
Return JSON only: {{"verdict": "EQUIVALENT" | "REVERSED_ORDER" | "SEMANTIC_MISMATCH" | "THRESHOLD_MISMATCH" | "BASELESS", "diagnostic_feedback": "..."}}'''

assert old_text in content, "old_text not found in content"
content = content.replace(old_text, new_text)

# Also update the verdict check line
old_verdict_line = 'if verdict not in ("REVERSED_ORDER", "THRESHOLD_MISMATCH", "BASELESS"):'
new_verdict_line = 'if verdict not in ("REVERSED_ORDER", "THRESHOLD_MISMATCH", "BASELESS", "SEMANTIC_MISMATCH"):'
assert old_verdict_line in content, "old_verdict_line not found in content"
content = content.replace(old_verdict_line, new_verdict_line)

file_path.write_text(content, encoding="utf-8")
print("Successfully patched src/symbolic/verbalizer_roundtrip.py!")
