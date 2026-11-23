import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.evaluation.benchmark_builder import (
    BENCHMARK_RULES,
    build_normative_rule_benchmark,
    build_stratified_trace_benchmark,
)
from src.evaluation.experiment_runner import (
    classify_semantic_equivalence,
    evaluate_rq1_complexity_tiers,
    run_ablation_experiment,
)
from src.evaluation.justification_tree import check_single_trace_semantics
from src.evaluation.real_llm_client import RealLLMClient, run_single_rule_with_real_llm
from src.evaluation.trace_safety_classifier import evaluate_trace_safety_and_status
from src.mde.constraint_ast import DeclareConstraintAST
from src.mde.deontic_mde_compiler import validate_and_compile_deontic_or_ast
from src.symbolic.counterfactual_prober import (
    generate_counterfactual_trace_mutant,
    verify_via_counterfactual_probing,
)
from src.symbolic.declare4py_verifier import Declare4Py
from src.symbolic.verbalizer_roundtrip import verify_generic_numeric_entities


class _StubCounterfactualClient:
    def __init__(self, verdict_payload):
        self.verdict_payload = verdict_payload
        self.captured_prompts = []

    def chat_json(self, messages, **kwargs):
        self.captured_prompts.append(messages if isinstance(messages, str) else messages[-1]["content"])
        return self.verdict_payload


class _StubB2LLMClient:
    def __init__(self, response_payload):
        self.response_payload = response_payload

    def chat_json(self, messages, **kwargs):
        return dict(self.response_payload)


class TestAuditFixesRegression(unittest.TestCase):
    def test_counterfactual_prober_rejects_reversed_order_even_when_case_flags_agree(self):
        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)

        ast_obj = DeclareConstraintAST(
            article_id="Article 5(1)",
            template_name="Precedence",
            activation_activity="O_Accepted",
            target_activity="O_Sent (mail and online)",
        )
        client = _StubCounterfactualClient(
            {
                "case_a_complies": True,
                "case_b_violates": True,
                "verdict": "REVERSED_ORDER",
                "is_unsupported_clause": False,
                "explanation": "Prerequisite and target are inverted.",
            }
        )
        ok, msg = verify_via_counterfactual_probing(
            compiled_rule=ast_obj.model_dump(),
            retrieved_chunk={
                "article_id": "Article 5(1)",
                "text": "In good time before the consumer is bound by any credit agreement, terms must be sent.",
            },
            llm_client=client,
            rule_meta={"description": "O_Sent (mail and online) must precede O_Accepted."},
            process_schema=process_schema,
        )
        self.assertFalse(ok)
        self.assertNotIn("already passed a deterministic regex pre-filter", client.captured_prompts[0].lower())
        self.assertIn("REVERSED_ORDER", msg)

    def test_counterfactual_prober_routes_unsupported_equivalent_contradiction_to_baseless(self):
        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)

        ast_obj = DeclareConstraintAST(
            article_id="Article 7",
            template_name="Response",
            activation_activity="A_Incomplete",
            target_activity="A_Validating",
        )
        client = _StubCounterfactualClient(
            {
                "case_a_complies": True,
                "case_b_violates": True,
                "verdict": "EQUIVALENT",
                "is_unsupported_clause": True,
                "explanation": "Article 7 does not support this workflow constraint.",
            }
        )
        ok, msg = verify_via_counterfactual_probing(
            compiled_rule=ast_obj.model_dump(),
            retrieved_chunk={
                "article_id": "Article 7",
                "text": "This Directive is without prejudice to national rules.",
            },
            llm_client=client,
            rule_meta={"description": "Incomplete must reach Validating within 8 days."},
            process_schema=process_schema,
        )
        self.assertFalse(ok)
        self.assertIn("BASELESS", msg)

    def test_deontic_mde_exemption_with_null_temporal_relation_compiles_cleanly(self):
        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)

        exemption_frame = {
            "article_id": "Article 2(2)",
            "deontic_modality": "EXEMPTION_OUT_OF_SCOPE",
            "temporal_relation": None,
            "anchor_activity": None,
            "consequent_activity": None,
            "attribute_guard": None,
            "guard_operator": None,
            "guard_threshold": None,
            "deadline_days": None,
            "unsupported_by_text": True,
            "reasoning": "Mortgage credit secured by immovable property is exempt under Article 2(2).",
        }
        ok, payload = validate_and_compile_deontic_or_ast(
            exemption_frame, process_schema=process_schema
        )
        self.assertTrue(ok, msg=f"Expected clean compilation, got: {payload}")
        self.assertEqual(payload["deontic_status"], "BASELESS_OR_EXEMPT")
        self.assertEqual(payload["temporal_relation"], "UNARY_CONDITION")

        malformed_obligation = {
            "article_id": "Article 8(1)",
            "deontic_modality": "OBLIGATION",
            "temporal_relation": "None",
            "anchor_activity": "A_Create Application",
            "consequent_activity": None,
            "unsupported_by_text": True,
        }
        ok_bad, err_bad = validate_and_compile_deontic_or_ast(
            malformed_obligation, process_schema=process_schema
        )
        self.assertFalse(ok_bad)
        self.assertIn("Unknown temporal_relation", str(err_bad))

    def test_trace_safety_existence_vs_forward_response_on_missing_activation(self):
        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        trace_df = pd.DataFrame(
            [
                {
                    "case:concept:name": "Case_Missing_Offer",
                    "concept:name": "A_Create Application",
                    "time:timestamp": t0,
                    "case:RequestedAmount": 10000.0,
                },
                {
                    "case:concept:name": "Case_Missing_Offer",
                    "concept:name": "A_Denied",
                    "time:timestamp": t0 + pd.Timedelta(hours=1),
                    "case:RequestedAmount": 10000.0,
                },
            ]
        )

        # Unary Existence when the required event never occurs MUST be CONTRADICTED, not INAPPLICABLE_TRACE_NO_ACTIVATION
        existence_ast = DeclareConstraintAST(
            article_id="Article 5(1)",
            template_name="Existence",
            activation_activity="O_Create Offer",
            activation_attr="case:RequestedAmount",
            activation_op=">",
            activation_val=0.0,
        )
        res_exist = evaluate_trace_safety_and_status(
            trace_df, existence_ast, True, "Counterfactual Probe Passed"
        )
        self.assertEqual(res_exist["label"], "CONTRADICTED")

        # Forward binary Response with guarded activation that never fires -> INAPPLICABLE_TRACE_NO_ACTIVATION
        response_ast = DeclareConstraintAST(
            article_id="Article 5(1)",
            template_name="Response",
            activation_activity="O_Sent (mail and online)",
            target_activity="O_Returned",
            activation_attr="case:RequestedAmount",
            activation_op=">",
            activation_val=0.0,
        )
        res_resp = evaluate_trace_safety_and_status(
            trace_df, response_ast, True, "Counterfactual Probe Passed"
        )
        self.assertEqual(res_resp["label"], "BASELESS")
        self.assertEqual(res_resp["reason_type"], "INAPPLICABLE_TRACE_NO_ACTIVATION")

    def test_benchmark_rules_r07_article5_and_r29_response_uniqueness(self):
        by_id = {r["rule_id"]: r for r in BENCHMARK_RULES}
        self.assertEqual(by_id["R07"]["article_id"], "Article 5(1)")
        self.assertEqual(by_id["R07"]["template"], "Precedence")
        self.assertEqual(by_id["R07"]["act_a"], "O_Sent (mail and online)")
        self.assertEqual(by_id["R07"]["act_b"], "O_Accepted")

        self.assertEqual(by_id["R29"]["article_id"], "Article 5(6)")
        self.assertEqual(by_id["R29"]["template"], "Response")
        self.assertEqual(by_id["R29"]["act_a"], "O_Sent (mail and online)")
        self.assertEqual(by_id["R29"]["act_b"], "W_Call after offers")
        self.assertEqual(by_id["R29"]["trap_type"], "INAPPLICABLE_TRACE_NO_ACTIVATION")

        norm_sigs = [
            (r["template"], r["act_a"], r["act_b"], r.get("attr"), r.get("op"), r.get("val"), r.get("time_max"))
            for r in BENCHMARK_RULES
            if not r.get("is_trap")
        ]
        self.assertEqual(len(norm_sigs), len(set(norm_sigs)))

    def test_classify_semantic_equivalence_absence_not_marked_vacuous(self):
        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        sample_log = pd.DataFrame(
            [
                {
                    "case:concept:name": "C1",
                    "concept:name": "O_Create Offer",
                    "time:timestamp": t0,
                    "MonthlyCost": 250.0,
                    "OfferedAmount": 10000.0,
                }
            ]
        )
        cand_abs = DeclareConstraintAST(
            article_id="Article 5(1)",
            template_name="Absence",
            activation_activity="O_Create Offer",
            activation_attr="MonthlyCost",
            activation_op="<=",
            activation_val=0.0,
        )
        gold_ex = DeclareConstraintAST(
            article_id="Article 5(1)",
            template_name="Existence",
            activation_activity="O_Create Offer",
            activation_attr="MonthlyCost",
            activation_op=">",
            activation_val=0.0,
        )
        eq_status = classify_semantic_equivalence(cand_abs, gold_ex.model_dump(), sample_log)
        self.assertNotEqual(eq_status, "VACUOUS")

    def test_b2_without_l3_does_not_get_hidden_abstention_shortcut(self):
        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)
        chunk = {
            "article_id": "Article 16(2)",
            "article_title": "Early repayment",
            "text": "The creditor is entitled to compensation within 1%.",
        }
        rule_meta = {
            "rule_id": "R27",
            "retrieved_chunk": chunk,
            "description": "Every created loan offer must enforce an early repayment fee <= 1.0%.",
        }
        stub_client = _StubB2LLMClient(
            {
                "article_id": "Article 16(2)",
                "template_name": "Existence",
                "activation_activity": "O_Create Offer",
                "activation_attr": "UNMAPPED_MISSING_IN_LOG",
                "activation_op": "<=",
                "activation_val": 1.0,
                "unsupported_by_text": True,
            }
        )
        res_b2 = run_single_rule_with_real_llm(
            rule_item=rule_meta,
            retrieved_chunk=chunk,
            process_schema=process_schema,
            llm=stub_client,
            max_retry=1,
            enable_l1_l2=False,
            enable_l3_roundtrip=False,
        )
        self.assertIsNotNone(res_b2["final_ast"])
        self.assertNotIn("deontic_baseless_reason", res_b2["final_ast"])

        res_nopre = run_single_rule_with_real_llm(
            rule_item=rule_meta,
            retrieved_chunk=chunk,
            process_schema=process_schema,
            llm=stub_client,
            max_retry=1,
            enable_l1_l2=False,
            enable_l3_roundtrip=True,
        )
        self.assertFalse(res_nopre["roundtrip_ok"])
        self.assertIn("BASELESS", res_nopre["trajectory"][0]["error"] or "")

    def test_benchmark_descriptions_no_schema_leak_or_approval_contradiction(self):
        forbidden_leaks = [
            "provisional underwriting approval",
            "initial concept",
            "immediately precede",
            "postal and electronic channels",
            "in writing and electronically",
            "never co-occur",
            "payout-pending",
            "dual physical-and-digital delivery",
            "final disbursement-ready approval",
            "with no intervening workflow events",
        ]
        for rule in BENCHMARK_RULES:
            desc = str(rule.get("description", "")).lower()
            for leak in forbidden_leaks:
                self.assertNotIn(
                    leak,
                    desc,
                    f"Rule {rule['rule_id']} still contains schema paraphrase leak '{leak}'",
                )

    def test_deontic_mde_compiler_abstention_precedence_and_prohibition_immediate(self):
        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)

        ok_missing, compiled_missing = validate_and_compile_deontic_or_ast(
            {
                "article_id": "Article 10(2)(f)",
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "UNARY_CONDITION",
                "anchor_activity": "O_Create Offer",
                "consequent_activity": None,
                "attribute_guard": "UNMAPPED_MISSING_IN_LOG",
                "guard_operator": None,
                "guard_threshold": None,
                "deadline_days": None,
                "unsupported_by_text": True,
            },
            process_schema,
        )
        self.assertTrue(ok_missing)
        self.assertIn("MISSING_LOG_EVIDENCE_PHI_VIOLATION", str(compiled_missing.get("deontic_baseless_reason")))

        ok_exempt, compiled_exempt = validate_and_compile_deontic_or_ast(
            {
                "article_id": "Article 2(2)(a)",
                "deontic_modality": "EXEMPTION_OUT_OF_SCOPE",
                "temporal_relation": "UNARY_CONDITION",
                "anchor_activity": "O_Create Offer",
                "consequent_activity": None,
                "attribute_guard": "RequestedAmount",
                "guard_operator": None,
                "guard_threshold": None,
                "deadline_days": None,
                "unsupported_by_text": True,
            },
            process_schema,
        )
        self.assertTrue(ok_exempt)
        self.assertIn("OUT_OF_DIRECTIVE_SCOPE", str(compiled_exempt.get("deontic_baseless_reason")))

        ok_proh_imm, err_proh_imm = validate_and_compile_deontic_or_ast(
            {
                "article_id": "Article 14(4)",
                "deontic_modality": "PROHIBITION",
                "temporal_relation": "IMMEDIATE_PREREQUISITE",
                "anchor_activity": "A_Create Application",
                "consequent_activity": "A_Concept",
                "attribute_guard": None,
                "guard_operator": None,
                "guard_threshold": None,
                "deadline_days": None,
                "unsupported_by_text": False,
            },
            process_schema,
        )
        self.assertFalse(ok_proh_imm)
        self.assertIn("incompatible", str(err_proh_imm).lower())

    def test_numeric_guard_layer3_prefix_and_terminal_termination(self):
        ok_num, kind_num, msg_num = verify_generic_numeric_entities(
            ast_dict={
                "article_id": "Article 14(1)",
                "template_name": "Precedence",
                "activation_activity": "O_Sent (mail and online)",
                "target_activity": "A_Cancelled",
                "time_max": 90,
                "time_unit": "d",
            },
            retrieved_chunk={"article_id": "Article 14(1)", "text": "The consumer shall have 14 calendar days to withdraw."},
            policy_text="Withdrawal allowed up to 90 days.",
        )
        self.assertFalse(ok_num)
        self.assertEqual(kind_num, "BASELESS")
        self.assertIn("Numeric Entity Guard -> POLICY_STATUTE_NUMERIC_CONFLICT", msg_num)
        self.assertNotIn("Deontic MDE Compiler ->", msg_num)

        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)

        class _PolicyNumericTrapClient:
            def __init__(self):
                self.calls = 0

            def chat_json(self, messages, **kwargs):
                self.calls += 1
                return {
                    "article_id": "Article 14(1)",
                    "deontic_modality": "OBLIGATION",
                    "temporal_relation": "PREREQUISITE_BEFORE",
                    "anchor_activity": "O_Sent (mail and online)",
                    "consequent_activity": "A_Cancelled",
                    "attribute_guard": None,
                    "guard_operator": None,
                    "guard_threshold": None,
                    "deadline_days": 90,
                    "unsupported_by_text": False,
                }

        client = _PolicyNumericTrapClient()
        res = run_single_rule_with_real_llm(
            rule_item={
                "rule_id": "R23",
                "description": "Withdrawal allowed up to 90 days.",
            },
            retrieved_chunk={"article_id": "Article 14(1)", "text": "The consumer shall have 14 calendar days to withdraw."},
            process_schema=process_schema,
            llm=client,
            max_retry=5,
            enable_l1_l2=True,
            enable_l3_roundtrip=True,
        )
        self.assertFalse(res["roundtrip_ok"])
        self.assertEqual(client.calls, 1)

    def test_counterfactual_prober_mutations_and_nonjson_handling(self):
        re_mut = generate_counterfactual_trace_mutant(
            {"template_name": "Responded Existence", "activation_activity": "A_Create Application", "target_activity": "A_Concept"}
        )
        self.assertEqual(re_mut["mutation_operator"], "MISSING_COEXISTENT_TARGET_MUTATION")

        nr_mut = generate_counterfactual_trace_mutant(
            {"template_name": "Not Response", "activation_activity": "A_Cancelled", "target_activity": "A_Pending"}
        )
        np_mut = generate_counterfactual_trace_mutant(
            {"template_name": "Not Precedence", "activation_activity": "A_Cancelled", "target_activity": "A_Pending"}
        )
        self.assertEqual(nr_mut["mutation_operator"], "FORBIDDEN_SUBSEQUENT_RESPONSE_MUTATION")
        self.assertEqual(np_mut["mutation_operator"], "FORBIDDEN_PRECEDING_ANTECEDENT_MUTATION")

        abs_mut = generate_counterfactual_trace_mutant(
            {"template_name": "Absence", "activation_activity": "A_Denied"}
        )
        ex_mut = generate_counterfactual_trace_mutant(
            {"template_name": "Existence", "activation_activity": "A_Create Application"}
        )
        self.assertNotIn("None None None", abs_mut["tau_plus_story"] + abs_mut["tau_minus_story"])
        self.assertNotIn("None None None", ex_mut["tau_plus_story"] + ex_mut["tau_minus_story"])

        class _NonJsonJudge:
            def chat(self, messages, **kwargs):
                return "not valid json output"

        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)
        ok_probe, msg_probe = verify_via_counterfactual_probing(
            compiled_rule={
                "article_id": "Article 8(1)",
                "template_name": "Precedence",
                "activation_activity": "A_Create Application",
                "target_activity": "A_Concept",
            },
            retrieved_chunk={"article_id": "Article 8(1)", "text": "Assess creditworthiness before proceeding."},
            llm_client=_NonJsonJudge(),
            process_schema=process_schema,
        )
        self.assertFalse(ok_probe)
        self.assertIn("Counterfactual Probe Error", msg_probe)

    def test_real_llm_client_schema_cache_retry_and_prompt_neutrality(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = RealLLMClient(api_key="test-key", cache_file=Path(tmp) / "cache.json", bypass_cache=True)
            msgs = [{"role": "user", "content": "hi"}]
            s1 = {"type": "object", "properties": {"a": {"type": "string"}}}
            s2 = {"type": "object", "properties": {"b": {"type": "integer"}}}
            self.assertNotEqual(client._make_key(msgs, 0.0, json_schema=s1), client._make_key(msgs, 0.0, json_schema=s2))
            self.assertNotEqual(client._make_key(msgs, 0.0, json_schema=s1), client._make_key(msgs, 0.0, json_schema=None))

            seen_formats = []

            def _fake_create(**kwargs):
                seen_formats.append(kwargs.get("response_format"))
                if len(seen_formats) == 1:
                    raise RuntimeError("429 Too Many Requests: Rate limit reached")
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"a": "ok"}'))])

            client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create)))
            out = client._call_groq_with_cache(msgs, temperature=0.0, json_schema=s1, response_mode="json")
            self.assertEqual(out, '{"a": "ok"}')
            self.assertEqual(len(seen_formats), 2)
            self.assertEqual(seen_formats[1]["type"], "json_schema")

        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)

        captured_prompts = []

        class _CapturingClient:
            def chat_json(self, messages, **kwargs):
                captured_prompts.append((kwargs.get("json_schema") is not None, messages))
                return {
                    "article_id": "Article 14(1)",
                    "template_name": "Precedence",
                    "activation_activity": "O_Sent (mail and online)",
                    "target_activity": "A_Cancelled",
                    "unsupported_by_text": False,
                }

            def chat(self, messages, **kwargs):
                return json.dumps(
                    {
                        "verdict": "EQUIVALENT",
                        "case_a_complies": True,
                        "case_b_violates": True,
                        "is_unsupported_clause": False,
                        "explanation": "Matched",
                    }
                )

        run_single_rule_with_real_llm(
            rule_item={"rule_id": "R15", "description": "Cancel within 14 days."},
            retrieved_chunk={"article_id": "Article 14(1)", "text": "Consumer may withdraw within 14 days."},
            process_schema=process_schema,
            llm=_CapturingClient(),
            max_retry=1,
            enable_l1_l2=False,
            enable_l3_roundtrip=True,
        )
        sys_msg_nopre = captured_prompts[0][1][0]["content"]
        self.assertNotIn("UNMAPPED_MISSING_IN_LOG", sys_msg_nopre)
        self.assertNotIn("Optional abstention", sys_msg_nopre)
        for m in captured_prompts[0][1]:
            if m["role"] == "user":
                self.assertNotIn("UNMAPPED_MISSING_IN_LOG", m["content"])

        class _CapturingDeonticClient:
            def chat_json(self, messages, **kwargs):
                captured_prompts.append(("DEONTIC", messages))
                return {
                    "article_id": "Article 14(1)",
                    "deontic_modality": "OBLIGATION",
                    "temporal_relation": "PREREQUISITE_BEFORE",
                    "anchor_activity": "O_Sent (mail and online)",
                    "consequent_activity": "A_Cancelled",
                    "attribute_guard": None,
                    "guard_operator": None,
                    "guard_threshold": None,
                    "deadline_days": 14,
                    "unsupported_by_text": False,
                }

        run_single_rule_with_real_llm(
            rule_item={"rule_id": "R15", "description": "Cancel within 14 days."},
            retrieved_chunk={"article_id": "Article 14(1)", "text": "Consumer may withdraw within 14 days."},
            process_schema=process_schema,
            llm=_CapturingDeonticClient(),
            max_retry=1,
            enable_l1_l2=True,
            enable_l3_roundtrip=False,
        )
        self.assertNotIn("within deadline_days after", captured_prompts[-1][1][0]["content"])

    def test_experiment_runner_time_unit_self_corr_and_rq1(self):
        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        sample_log = pd.DataFrame(
            [
                {"case:concept:name": "C1", "concept:name": "O_Sent (mail and online)", "time:timestamp": t0},
                {"case:concept:name": "C1", "concept:name": "A_Cancelled", "time:timestamp": t0 + pd.Timedelta(hours=10)},
            ]
        )
        gold_14d = {
            "article_id": "Article 14(1)",
            "template_name": "Precedence",
            "activation_activity": "O_Sent (mail and online)",
            "target_activity": "A_Cancelled",
            "time_min": 0,
            "time_max": 14,
            "time_unit": "d",
        }
        cand_14h = DeclareConstraintAST(
            article_id="Article 14(1)",
            template_name="Precedence",
            activation_activity="O_Sent (mail and online)",
            target_activity="A_Cancelled",
            time_min=0,
            time_max=14,
            time_unit="h",
        )
        cand_24h = DeclareConstraintAST(
            article_id="Article 14(1)",
            template_name="Precedence",
            activation_activity="O_Sent (mail and online)",
            target_activity="A_Cancelled",
            time_min=0,
            time_max=24,
            time_unit="h",
        )
        gold_1d = dict(gold_14d, time_max=1)
        self.assertEqual(classify_semantic_equivalence(cand_14h, gold_14d, sample_log), "STRENGTHENED")
        self.assertEqual(classify_semantic_equivalence(cand_24h, gold_1d, sample_log), "EQ")

        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)

        chunk = {"article_id": "Article 14(1)", "article_title": "Withdrawal", "text": "14 calendar days"}
        gold_rule = {
            "rule_id": "R15",
            "complexity_tier": "Tier 2: Temporal & Data-Aware",
            "retrieved_chunk": chunk,
            "gold_ast": gold_14d,
        }

        class _RejectingMockLLM:
            def __init__(self, reject_kind: str):
                self.reject_kind = reject_kind
                self.attempt = 0

            def generate_ast(self, chunk, schema, feedback="", rule_meta=None):
                self.attempt += 1
                if self.attempt == 2 and self.reject_kind == "STALE_L1":
                    return "{bad json"
                return json.dumps(
                    {
                        "article_id": "Article 14(1)",
                        "template_name": "Precedence",
                        "activation_activity": "O_Sent (mail and online)",
                        "target_activity": "A_Cancelled",
                        "time_min": 0,
                        "time_max": 14,
                        "time_unit": "d",
                    }
                )

            def chat(self, messages, **kwargs):
                v = "BASELESS" if self.reject_kind == "BASELESS" else "SEMANTIC_MISMATCH"
                return json.dumps({"verdict": v, "diagnostic_feedback": f"rejected ({v})"})

            def verify_roundtrip(self, ast_dict, chunk):
                return False, (
                    "[Counterfactual Blind Judge -> SEMANTIC_MISMATCH]: rejected"
                    if self.reject_kind != "BASELESS"
                    else "[Counterfactual Blind Judge -> BASELESS]: baseless"
                )

            def explain_violation(self, *args, **kwargs):
                return "explanation"

        # 1) enable_self_correction=False must NOT overwrite roundtrip_ok=True or score Eq_Rate=100%
        bm_item = [
            {
                "item_id": "R15-01",
                "rule_id": "R15",
                "rule_meta": gold_rule,
                "retrieved_chunk": chunk,
                "test_case_df": sample_log,
                "ground_truth_label": "ENTAILED",
            }
        ]
        abl_res = run_ablation_experiment(
            benchmark_items=bm_item,
            log_df=sample_log,
            process_schema=process_schema,
            llm_client=_RejectingMockLLM("SEMANTIC_MISMATCH"),
            enable_l1_l2=True,
            enable_self_correction=False,
            enable_l3_roundtrip=True,
            evaluate_explanations=False,
        )
        self.assertEqual(abl_res["Eq_Rate (%)"], 0.0)
        self.assertEqual(abl_res["Trajectories"]["R15"][-1]["status"], "FAILED_L3_ROUNDTRIP")

        # 2) RQ1 rejects L3 SEMANTIC_MISMATCH from scoring EQ and clears stale ast_obj
        rq1_mismatch = evaluate_rq1_complexity_tiers(
            [gold_rule], sample_log, process_schema, enable_self_correction=True, enable_l3_roundtrip=True, llm_client=_RejectingMockLLM("SEMANTIC_MISMATCH")
        )
        self.assertEqual(rq1_mismatch["Overall Pipeline"]["Eq. (%)"], 0.0)
        self.assertEqual(rq1_mismatch["Overall Pipeline"]["Abstained (%)"], 100.0)

        rq1_stale = evaluate_rq1_complexity_tiers(
            [gold_rule], sample_log, process_schema, enable_self_correction=True, enable_l3_roundtrip=True, llm_client=_RejectingMockLLM("STALE_L1")
        )
        self.assertEqual(rq1_stale["Overall Pipeline"]["Eq. (%)"], 0.0)

    def test_declare4py_and_justification_tree_semantics_parity(self):
        t0 = pd.Timestamp("2026-01-01T00:00:00Z")

        def _make_df(rows):
            return pd.DataFrame(rows)

        def _eval_d4py(df, decl_line, consider_vacuity=False):
            d4py = Declare4Py(df)
            with tempfile.NamedTemporaryFile("w", suffix=".decl", delete=False, encoding="utf-8") as tmpf:
                tmpf.write(decl_line + "\n")
                p = tmpf.name
            try:
                d4py.parse_decl_model(p)
                res = d4py.conformance_checking(consider_vacuity=consider_vacuity)
                cid = df["case:concept:name"].iloc[0]
                key = next(k for k in res if k[1] == cid)
                return res[key][decl_line].state
            finally:
                Path(p).unlink(missing_ok=True)

        # 1) Not Precedence: [A, B] violates, [B, A] satisfies
        df_ab = _make_df(
            [
                {"case:concept:name": "C1", "concept:name": "A", "time:timestamp": t0},
                {"case:concept:name": "C1", "concept:name": "B", "time:timestamp": t0 + pd.Timedelta(hours=1)},
            ]
        )
        df_ba = _make_df(
            [
                {"case:concept:name": "C1", "concept:name": "B", "time:timestamp": t0},
                {"case:concept:name": "C1", "concept:name": "A", "time:timestamp": t0 + pd.Timedelta(hours=1)},
            ]
        )
        ast_np = DeclareConstraintAST(article_id="Art. 1", template_name="Not Precedence", activation_activity="A", target_activity="B")
        self.assertEqual(_eval_d4py(df_ab, "Not Precedence[A, B] | | |"), "Violated")
        self.assertEqual(_eval_d4py(df_ba, "Not Precedence[A, B] | | |"), "Satisfied")
        self.assertFalse(check_single_trace_semantics(df_ab, ast_np)[0])
        self.assertTrue(check_single_trace_semantics(df_ba, ast_np)[0])

        # 2) Not Co-Existence with [B] only must be Satisfied even with consider_vacuity=False
        df_b_only = _make_df([{"case:concept:name": "C1", "concept:name": "B", "time:timestamp": t0}])
        self.assertEqual(_eval_d4py(df_b_only, "Not Co-Existence[A, B] | | |", consider_vacuity=False), "Satisfied")

        # 3) Responded Existence: [B, A] satisfies, [A] violates in BOTH verifiers
        ast_re = DeclareConstraintAST(article_id="Art. 1", template_name="Responded Existence", activation_activity="A", target_activity="B")
        df_a_only = _make_df([{"case:concept:name": "C1", "concept:name": "A", "time:timestamp": t0}])
        self.assertEqual(_eval_d4py(df_ba, "Responded Existence[A, B] | | |"), "Satisfied")
        self.assertTrue(check_single_trace_semantics(df_ba, ast_re)[0])
        self.assertFalse(check_single_trace_semantics(df_a_only, ast_re)[0])

        # 4) Precedence/Alternate/Chain on 2nd B & valid prior A deadline
        df_abb = _make_df(
            [
                {"case:concept:name": "C1", "concept:name": "A", "time:timestamp": t0, "CreditScore": 700.0},
                {"case:concept:name": "C1", "concept:name": "B", "time:timestamp": t0 + pd.Timedelta(hours=1)},
                {"case:concept:name": "C1", "concept:name": "B", "time:timestamp": t0 + pd.Timedelta(hours=2)},
            ]
        )
        ast_alt_p = DeclareConstraintAST(article_id="Art. 1", template_name="Alternate Precedence", activation_activity="A", target_activity="B")
        ast_chain_p = DeclareConstraintAST(article_id="Art. 1", template_name="Chain Precedence", activation_activity="A", target_activity="B")
        self.assertFalse(check_single_trace_semantics(df_abb, ast_alt_p)[0])
        self.assertFalse(check_single_trace_semantics(df_abb, ast_chain_p)[0])

        df_invalid_later_a = _make_df(
            [
                {"case:concept:name": "C1", "concept:name": "A", "time:timestamp": t0, "CreditScore": 700.0},
                {"case:concept:name": "C1", "concept:name": "A", "time:timestamp": t0 + pd.Timedelta(days=10), "CreditScore": 0.0},
                {"case:concept:name": "C1", "concept:name": "B", "time:timestamp": t0 + pd.Timedelta(days=20)},
            ]
        )
        ast_p_attr_time = DeclareConstraintAST(
            article_id="Art. 1",
            template_name="Precedence",
            activation_activity="A",
            target_activity="B",
            activation_attr="CreditScore",
            activation_op=">",
            activation_val=0.0,
            time_min=0,
            time_max=14,
            time_unit="d",
        )
        self.assertFalse(check_single_trace_semantics(df_invalid_later_a, ast_p_attr_time)[0])

        # 5) Time unit normalization in justification_tree (24h == 1d; 30h > 24h)
        ast_p_24h = DeclareConstraintAST(
            article_id="Art. 1",
            template_name="Precedence",
            activation_activity="A",
            target_activity="B",
            time_min=0,
            time_max=24,
            time_unit="h",
        )
        df_30h = _make_df(
            [
                {"case:concept:name": "C1", "concept:name": "A", "time:timestamp": t0},
                {"case:concept:name": "C1", "concept:name": "B", "time:timestamp": t0 + pd.Timedelta(hours=30)},
            ]
        )
        self.assertFalse(check_single_trace_semantics(df_30h, ast_p_24h)[0])

        # 6) Activation condition respected on Response in justification_tree & T. corr_cond on Choice in Declare4Py
        df_resp_unactivated = _make_df(
            [{"case:concept:name": "C1", "concept:name": "A", "time:timestamp": t0, "OfferedAmount": 0.0}]
        )
        ast_resp_gt = DeclareConstraintAST(
            article_id="Art. 1",
            template_name="Response",
            activation_activity="A",
            target_activity="B",
            activation_attr="OfferedAmount",
            activation_op=">",
            activation_val=0.0,
        )
        self.assertTrue(check_single_trace_semantics(df_resp_unactivated, ast_resp_gt)[0])
        df_choice_corr = _make_df(
            [{"case:concept:name": "C1", "concept:name": "B", "time:timestamp": t0, "OfferedAmount": 0.0}]
        )
        self.assertEqual(
            _eval_d4py(df_choice_corr, "Choice[A, B] | A.OfferedAmount > 100 | T.OfferedAmount > 100 |", consider_vacuity=False),
            "Violated",
        )

    def test_posthoc_grounding_checks_activity_evidence_on_non_deadline_contradicted(self):
        from src.evaluation.grounded_auditor import verify_posthoc_grounding

        j_tree = {
            "audit_status": "CONTRADICTED",
            "reason_category": "PROCESS_COMPLIANCE_VIOLATION",
            "normative_node": {"directive": "Directive 2008/48/EC", "article_id": "Article 8(1)"},
            "symbolic_rule_node": {"declare_formula": "Precedence[A_Accepted, O_Create Offer]"},
            "trace_evidence_node": {
                "case_id": "Application_12345",
                "proof_or_counterexample": {
                    "violation_subtype": "MISSING_PREREQUISITE_ACTIVITY",
                    "missing_event": "A_Accepted",
                    "target_event": {"activity": "O_Create Offer", "timestamp": "2016-05-01T10:00:00Z"},
                },
            },
        }
        bad = "Case Application_12345 is CONTRADICTED under Article 8(1) due to missing prerequisite step."
        res_bad = verify_posthoc_grounding(j_tree, bad)
        self.assertFalse(res_bad["is_citation_verified"])
        self.assertTrue(any("missing_event" in m for m in res_bad["missing_anchors"]))
        self.assertTrue(any("target_event.activity" in m for m in res_bad["missing_anchors"]))

        good = (
            "Case Application_12345 is CONTRADICTED under Article 8(1): "
            "O_Create Offer occurred without prerequisite A_Accepted."
        )
        res_good = verify_posthoc_grounding(j_tree, good)
        self.assertTrue(res_good["is_citation_verified"], res_good)

    def test_unmapped_attr_without_operator_or_threshold_returns_compile_error(self) -> None:
        """Pure deadline/ordering rules with null operator & threshold must not false-abstain on UNMAPPED_MISSING_IN_LOG."""
        from src.mde.deontic_mde_compiler import UNMAPPED_ATTR_TOKEN, compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        status_err, msg_err = compile_deontic_to_declare4py(
            {
                "article_id": "Article 14(1)",
                "deontic_modality": "PERMISSION_RIGHT",
                "temporal_relation": "PREREQUISITE_BEFORE",
                "anchor_activity": "O_Sent (mail and online)",
                "consequent_activity": "A_Cancelled",
                "attribute_guard": UNMAPPED_ATTR_TOKEN,
                "guard_operator": None,
                "guard_threshold": None,
                "deadline_days": 14,
                "unsupported_by_text": False,
            },
            process_schema=schema,
        )
        self.assertEqual(status_err, "COMPILE_ERROR")
        self.assertIn("attribute_guard=null", str(msg_err))

        # Genuine unmapped quantitative metric with operator+threshold must still block as BASELESS_MISSING_ATTR
        status_phi, payload_phi = compile_deontic_to_declare4py(
            {
                "article_id": "Article 19(1)",
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "UNARY_CONDITION",
                "anchor_activity": "O_Create Offer",
                "attribute_guard": UNMAPPED_ATTR_TOKEN,
                "guard_operator": ">",
                "guard_threshold": 0.0,
                "unsupported_by_text": False,
            },
            process_schema=schema,
        )
        self.assertEqual(status_phi, "BASELESS_MISSING_ATTR")
        self.assertIsInstance(payload_phi, dict)

    def test_behavioral_profile_default_top_k_includes_all_bpic_strict_pairs(self) -> None:
        """Default behavioral profile formatting should not truncate key invariant edges such as A_Create Application -> A_Concept."""
        from src.mde.deontic_mde_compiler import format_behavioral_profile_for_prompt

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        formatted = format_behavioral_profile_for_prompt(schema)
        self.assertIn("A_Create Application -> A_Concept", formatted)
        self.assertIn("O_Sent (mail and online) -> O_Cancelled", formatted)

    def test_l3_baseless_abstention_with_unmapped_attr_not_penalized_as_crash(self) -> None:
        """L3 BASELESS rejection in -Pre (enable_l1_l2=False) with an unmapped attribute must count as BASELESS, not CRASH."""
        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        sample_log = pd.DataFrame(
            [
                {"case:concept:name": "C_R27", "concept:name": "O_Create Offer", "time:timestamp": t0},
            ]
        )
        chunk = {
            "article_id": "Article 16(2)",
            "article_title": "Early repayment",
            "text": "The creditor may claim fair compensation not exceeding 1%.",
        }
        rule_r27 = {
            "rule_id": "R27",
            "article_id": "Article 16(2)",
            "is_baseless_trap": True,
            "trap_type": "MISSING_LOG_EVIDENCE_PHI_VIOLATION",
            "trap_scope": "schema",
            "retrieved_chunk": chunk,
            "description": "Offer early repayment fee must not exceed 1.0%.",
        }
        bench_item = [
            {
                "item_id": "R27-01",
                "rule_id": "R27",
                "rule_meta": rule_r27,
                "retrieved_chunk": chunk,
                "test_case_df": sample_log,
                "ground_truth_label": "BASELESS",
            }
        ]

        class _NoPreL3CatchClient:
            def chat_json(self, messages, **kwargs):
                msg_text = str(messages)
                if "Counterfactual Trace Mutation Probing" in msg_text:
                    return json.dumps(
                        {
                            "case_a_complies": False,
                            "case_b_violates": False,
                            "is_unsupported_clause": True,
                            "verdict": "BASELESS",
                            "explanation": "Attribute missing in process log.",
                        }
                    )
                return json.dumps(
                    {
                        "article_id": "Article 16(2)",
                        "template_name": "Existence",
                        "activation_activity": "O_Create Offer",
                        "target_activity": None,
                        "activation_attr": "EarlyRepaymentCompensationFee",
                        "activation_op": "<=",
                        "activation_val": 1.0,
                        "unsupported_by_text": False,
                    }
                )

        res = run_ablation_experiment(
            benchmark_items=bench_item,
            log_df=sample_log,
            process_schema=schema,
            llm_client=_NoPreL3CatchClient(),
            enable_l1_l2=False,
            enable_self_correction=False,
            enable_l3_roundtrip=True,
            evaluate_explanations=False,
        )
        self.assertEqual(res["Crash_Rate (%)"], 0.0)
        self.assertEqual(res["Strict_Accuracy (%)"], 100.0)
        self.assertEqual(res["Executable_Rate (%)"], 100.0)

    def test_rq1_round1_reports_deontic_mde_false_abstention_as_abstained(self) -> None:
        """RQ1 when enable_l3_roundtrip=False must report MDE BASELESS rejections as ABSTAINED rather than hiding them."""
        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        sample_log = pd.DataFrame(
            [
                {"case:concept:name": "C_R13", "concept:name": "O_Create Offer", "OfferedAmount": 5000.0, "time:timestamp": t0},
                {"case:concept:name": "C_R13", "concept:name": "O_Sent (mail and online)", "OfferedAmount": 5000.0, "time:timestamp": t0 + pd.Timedelta(hours=1)},
            ]
        )
        chunk = {"article_id": "Article 4(2)", "article_title": "Standard info", "text": "Total credit shall be stated."}
        rule_r13 = {
            "rule_id": "R13",
            "complexity_tier": "Tier 2: Temporal & Data-Aware",
            "retrieved_chunk": chunk,
            "gold_ast": {
                "article_id": "Article 4(2)",
                "template_name": "Precedence",
                "activation_activity": "O_Create Offer",
                "target_activity": "O_Sent (mail and online)",
                "activation_attr": "OfferedAmount",
                "activation_op": ">",
                "activation_val": 0.0,
                "time_min": 0,
                "time_max": None,
                "time_unit": "d",
            },
        }

        class _FalseAbstainMDEClient:
            def chat_json(self, messages, **kwargs):
                return json.dumps(
                    {
                        "article_id": "Article 4(2)",
                        "deontic_modality": "OBLIGATION",
                        "temporal_relation": "PREREQUISITE_BEFORE",
                        "anchor_activity": "O_Create Offer",
                        "consequent_activity": "O_Sent (mail and online)",
                        "attribute_guard": "UNMAPPED_MISSING_IN_LOG",
                        "guard_operator": ">",
                        "guard_threshold": 0.0,
                        "deadline_days": None,
                        "unsupported_by_text": False,
                    }
                )

        rq1 = evaluate_rq1_complexity_tiers(
            [rule_r13],
            sample_log,
            schema,
            enable_self_correction=False,
            enable_l3_roundtrip=False,
            llm_client=_FalseAbstainMDEClient(),
        )
        self.assertEqual(rq1["Overall Pipeline"]["Abstained (%)"], 100.0)
        self.assertEqual(rq1["Overall Pipeline"]["Strengthened (%)"], 0.0)
        self.assertEqual(rq1["Overall Pipeline"]["Eq. (%)"], 0.0)

    def test_numeric_guard_hallucinated_time_max_not_in_policy_returns_threshold_mismatch(self) -> None:
        """Hallucinated time_max on a non-numeric clause where the number is NOT in policy must allow retry (THRESHOLD_MISMATCH)."""
        ok_num, kind_num, _ = verify_generic_numeric_entities(
            ast_dict={
                "article_id": "Article 10(1)",
                "template_name": "Response",
                "activation_activity": "O_Create Offer",
                "target_activity": "O_Sent (mail and online)",
                "time_max": 10,
                "time_unit": "d",
            },
            retrieved_chunk={"article_id": "Article 10(1)", "text": "Credit agreements shall be drawn up on paper."},
            policy_text="Whenever an offer is drafted, the consumer must receive a copy.",
        )
        self.assertFalse(ok_num)
        self.assertEqual(kind_num, "THRESHOLD_MISMATCH")

    def test_classify_semantic_equivalence_returns_wrong_activity_vs_reversed(self) -> None:
        """Activity mismatch must be labeled WRONG_ACTIVITY while swapped/negated rules stay REVERSED."""
        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        log_df = pd.DataFrame(
            [
                {"case:concept:name": "C1", "concept:name": "W_Call after offers", "time:timestamp": t0},
                {"case:concept:name": "C1", "concept:name": "A_Validating", "time:timestamp": t0 + pd.Timedelta(minutes=10)},
                {"case:concept:name": "C1", "concept:name": "W_Validate application", "time:timestamp": t0 + pd.Timedelta(minutes=20)},
            ]
        )
        gold_ast = {
            "article_id": "Article 8",
            "template_name": "Precedence",
            "activation_activity": "A_Validating",
            "target_activity": "W_Call after offers",
        }
        cand_wrong_act = DeclareConstraintAST(
            article_id="Article 8",
            template_name="Precedence",
            activation_activity="W_Validate application",
            target_activity="W_Call after offers",
        )
        cand_swapped = DeclareConstraintAST(
            article_id="Article 8",
            template_name="Precedence",
            activation_activity="W_Call after offers",
            target_activity="A_Validating",
        )
        self.assertEqual(classify_semantic_equivalence(cand_wrong_act, gold_ast, log_df), "WRONG_ACTIVITY")
        self.assertEqual(classify_semantic_equivalence(cand_swapped, gold_ast, log_df), "REVERSED")

    def test_rq1_table_includes_wrong_activity_column(self) -> None:
        """evaluate_rq1_complexity_tiers must report Wrong Activity (%) separately from Reversed (%)."""
        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        sample_log = pd.DataFrame(
            [
                {"case:concept:name": "C1", "concept:name": "O_Sent (mail and online)", "time:timestamp": t0},
                {"case:concept:name": "C1", "concept:name": "W_Call after offers", "time:timestamp": t0 + pd.Timedelta(minutes=5)},
                {"case:concept:name": "C1", "concept:name": "A_Validating", "time:timestamp": t0 + pd.Timedelta(minutes=10)},
            ]
        )
        chunk = {"article_id": "Article 8", "article_title": "Creditworthiness", "text": "Assessment prior to validation."}
        rule_r12 = {
            "rule_id": "R12",
            "complexity_tier": "Tier 1: Control-Flow Only",
            "retrieved_chunk": chunk,
            "gold_ast": {
                "article_id": "Article 8",
                "template_name": "Precedence",
                "activation_activity": "W_Call after offers",
                "target_activity": "A_Validating",
            },
        }

        class _WrongActivityClient:
            def chat_json(self, messages, **kwargs):
                return json.dumps(
                    {
                        "article_id": "Article 8",
                        "deontic_modality": "OBLIGATION",
                        "temporal_relation": "PREREQUISITE_BEFORE",
                        "anchor_activity": "O_Sent (mail and online)",
                        "consequent_activity": "A_Validating",
                        "unsupported_by_text": False,
                    }
                )

        rq1 = evaluate_rq1_complexity_tiers(
            [rule_r12],
            sample_log,
            schema,
            enable_self_correction=False,
            enable_l3_roundtrip=False,
            llm_client=_WrongActivityClient(),
        )
        self.assertEqual(rq1["Overall Pipeline"]["Wrong Activity (%)"], 100.0)
        self.assertEqual(rq1["Overall Pipeline"]["Reversed (%)"], 0.0)
        self.assertEqual(rq1["Overall Pipeline"]["Eq. (%)"], 0.0)

    def test_ablation_separates_normative_eq_and_trap_detection(self) -> None:
        """run_ablation_experiment must report Normative_Eq_Rate (%) cleanly apart from Trap_Detection_Rate (%)."""
        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        sample_log = pd.DataFrame(
            [
                {"case:concept:name": "C1", "concept:name": "A_Create Application", "time:timestamp": t0},
                {"case:concept:name": "C1", "concept:name": "A_Concept", "time:timestamp": t0 + pd.Timedelta(minutes=1)},
                {"case:concept:name": "C1", "concept:name": "A_Accepted", "time:timestamp": t0 + pd.Timedelta(minutes=2)},
            ]
        )
        norm_rule = {
            "rule_id": "R01",
            "complexity_tier": "Tier 1: Temporal Only",
            "gold_ast": {
                "article_id": "Article 5",
                "template_name": "Precedence",
                "activation_activity": "A_Accepted",
                "target_activity": "A_Concept",
            },
        }
        trap_rule = {
            "rule_id": "R23",
            "complexity_tier": "Trap",
            "is_baseless_trap": True,
            "gold_ast": None,
        }
        items = [
            {
                "item_id": "R01_ENT",
                "rule_id": "R01",
                "rule_meta": norm_rule,
                "retrieved_chunk": {"article_id": "Article 5", "text": "Concept precedes acceptance."},
                "test_case_df": sample_log,
                "ground_truth_label": "ENTAILED",
            },
            {
                "item_id": "R23_BAS",
                "rule_id": "R23",
                "rule_meta": trap_rule,
                "retrieved_chunk": {"article_id": "Article 99", "text": "Unenforceable trap clause."},
                "test_case_df": sample_log,
                "ground_truth_label": "BASELESS",
            },
        ]

        class _MixedClient:
            def chat_json(self, messages, **kwargs):
                msg_text = str(messages)
                if "Article 99" in msg_text:
                    return json.dumps({"unsupported_by_text": True, "article_id": "Article 99"})
                return json.dumps(
                    {
                        "article_id": "Article 5",
                        "template_name": "Precedence",
                        "activation_activity": "A_Create Application",
                        "target_activity": "A_Concept",
                        "unsupported_by_text": False,
                    }
                )

        res = run_ablation_experiment(
            benchmark_items=items,
            log_df=sample_log,
            process_schema=schema,
            llm_client=_MixedClient(),
            enable_l1_l2=False,
            enable_self_correction=False,
            enable_l3_roundtrip=False,
            evaluate_explanations=False,
        )
        self.assertEqual(res["Normative_Eq_Rate (%)"], 0.0)
        self.assertEqual(res["Trap_Detection_Rate (%)"], 100.0)
        self.assertIn("Eq_Rate (%)", res)

    def test_b2_and_no_pre_both_honor_unsupported_by_text_symmetrically(self) -> None:
        """Both B2 (L3 off) and -Pre (L3 on) must treat LLM unsupported_by_text=true identically."""
        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        trap_rule = {
            "rule_id": "R25",
            "complexity_tier": "Trap",
            "gold_ast": None,
        }
        chunk = {"article_id": "Article 19", "article_title": "Trap", "text": "Requires biometric signature."}
        payload = {"article_id": "Article 19", "unsupported_by_text": True}

        res_b2 = run_single_rule_with_real_llm(
            rule_item=trap_rule,
            retrieved_chunk=chunk,
            process_schema=schema,
            llm=_StubB2LLMClient(payload),
            enable_l1_l2=False,
            enable_l3_roundtrip=False,
        )
        res_no_pre = run_single_rule_with_real_llm(
            rule_item=trap_rule,
            retrieved_chunk=chunk,
            process_schema=schema,
            llm=_StubB2LLMClient(payload),
            enable_l1_l2=False,
            enable_l3_roundtrip=True,
        )
        self.assertFalse(res_b2["roundtrip_ok"])
        self.assertFalse(res_no_pre["roundtrip_ok"])
        self.assertIn("Model Abstained", res_b2["roundtrip_msg"])
        self.assertIn("Model Abstained", res_no_pre["roundtrip_msg"])

    def test_benchmark_builder_hardens_precedence_and_chain_precedence(self) -> None:
        """Fault injection must include ORDER_INVERSION, CHAIN_GAP_INJECTION, and A-only compliant traces."""
        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        rows = []
        # Create >=420 interleaved traces so both dev and heldout_test halves (>=200) activate strict_unique_cids & Pass 1A
        for i in range(420):
            cid = f"CASE_SYN_{i}"
            base = t0 + pd.Timedelta(hours=i)
            if i % 10 == 0:
                seq = [
                    ("A_Create Application", {}),
                    ("A_Concept", {}),
                    ("W_Complete application", {}),
                    ("O_Create Offer", {"OfferedAmount": 12000.0}),
                    ("O_Created", {"OfferedAmount": 12000.0}),
                    ("W_Call after offers", {"CreditScore": 650.0}),
                ]
            else:
                seq = [
                    ("A_Create Application", {}),
                    ("A_Concept", {}),
                    ("W_Complete application", {}),
                    ("A_Accepted", {}),
                    ("O_Create Offer", {"OfferedAmount": 12000.0}),
                    ("O_Created", {"OfferedAmount": 12000.0}),
                    ("O_Sent (mail and online)", {"OfferedAmount": 12000.0}),
                    ("O_Returned", {"OfferedAmount": 12000.0}),
                    ("W_Call after offers", {"CreditScore": 650.0, "OfferedAmount": 12000.0}),
                    ("A_Validating", {"CreditScore": 650.0, "OfferedAmount": 12000.0}),
                    ("W_Validate application", {"CreditScore": 650.0}),
                    ("O_Accepted", {}),
                ]
            for step, (act, attrs) in enumerate(seq):
                row = {"case:concept:name": cid, "concept:name": act, "time:timestamp": base + pd.Timedelta(minutes=step)}
                row.update(attrs)
                rows.append(row)

        synth_log = pd.DataFrame(rows)
        with open(ROOT_DIR / "data" / "processed" / "directive_chunks.json", "r", encoding="utf-8") as f:
            chunks_list = json.load(f)
        chunk_map = {c["article_id"]: c for c in chunks_list}
        sub_rules = [
            r for r in build_normative_rule_benchmark(chunk_map, split="all")
            if r["rule_id"] in ("R04", "R12", "R23", "R29")
        ]
        items = build_stratified_trace_benchmark(
            df_propagated=synth_log,
            df_raw=synth_log,
            normative_rules=sub_rules,
            target_total_items=36,
            split="all",
        )

        origins = [it.get("trace_origin", "") for it in items]
        self.assertTrue(any(o.startswith("BPIC2017_REAL_COMPLIANT_A_ONLY") for o in origins))

        # R12 CONTRADICTED must include order-inversion traces keeping both act_a and act_b (not just naive deletion)
        r12_con = [it for it in items if it["rule_id"] == "R12" and it["ground_truth_label"] == "CONTRADICTED"]
        self.assertTrue(
            any(
                {"W_Call after offers", "A_Validating"}.issubset(set(it["test_case_df"]["concept:name"]))
                for it in r12_con
            )
        )

        # R04 CONTRADICTED (Chain Precedence: O_Create Offer -> O_Created) must include gap traces with an intervening event
        r04_con = [it for it in items if it["rule_id"] == "R04" and it["ground_truth_label"] == "CONTRADICTED"]
        has_gap_trace = False
        for it in r04_con:
            acts = it["test_case_df"].sort_values("time:timestamp")["concept:name"].tolist()
            if "O_Create Offer" in acts and "O_Created" in acts:
                i_a = acts.index("O_Create Offer")
                i_b = acts.index("O_Created")
                if i_b - i_a > 1:
                    has_gap_trace = True
                    break
        self.assertTrue(has_gap_trace)

    def test_ablation_reports_normative_only_and_split_trap_metrics(self) -> None:
        """run_ablation_experiment must separate Normative_Accuracy/F1 (R01-R22) from Rule/Schema vs Trace Safety traps."""
        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        t0 = pd.Timestamp("2026-01-01T10:00:00Z")
        sample_log = pd.DataFrame(
            [
                {"case:concept:name": "C1", "concept:name": "A_Create Application", "time:timestamp": t0},
                {"case:concept:name": "C1", "concept:name": "A_Concept", "time:timestamp": t0 + pd.Timedelta(minutes=1)},
                {"case:concept:name": "C1", "concept:name": "O_Create Offer", "NumberOfTerms": 12.0, "time:timestamp": t0 + pd.Timedelta(minutes=2)},
            ]
        )
        nan_log = pd.DataFrame(
            [
                {"case:concept:name": "C2", "concept:name": "O_Create Offer", "NumberOfTerms": float("nan"), "time:timestamp": t0},
            ]
        )
        norm_rule = {
            "rule_id": "R01",
            "complexity_tier": "Tier 1: Control-Flow Only",
            "gold_ast": {
                "article_id": "Article 8(1)",
                "template_name": "Precedence",
                "activation_activity": "A_Create Application",
                "target_activity": "A_Concept",
            },
        }
        rule_trap = {"rule_id": "R23", "complexity_tier": "Trap", "is_baseless_trap": True, "trap_scope": "rule", "gold_ast": None}
        trace_trap = {"rule_id": "R30", "complexity_tier": "Trap", "is_baseless_trap": True, "trap_scope": "trace", "gold_ast": None}

        items = [
            {
                "item_id": "R01_ENT",
                "rule_id": "R01",
                "rule_meta": norm_rule,
                "retrieved_chunk": {"article_id": "Article 8(1)", "text": "Assess creditworthiness."},
                "test_case_df": sample_log,
                "ground_truth_label": "ENTAILED",
            },
            {
                "item_id": "R23_BAS",
                "rule_id": "R23",
                "rule_meta": rule_trap,
                "retrieved_chunk": {"article_id": "Article 7", "text": "Exemptions apply."},
                "test_case_df": sample_log,
                "ground_truth_label": "BASELESS",
            },
            {
                "item_id": "R30_BAS",
                "rule_id": "R30",
                "rule_meta": trace_trap,
                "retrieved_chunk": {"article_id": "Article 10(2)", "text": "Number of payments shall be specified."},
                "test_case_df": nan_log,
                "ground_truth_label": "BASELESS",
            },
        ]

        class _SplitMockClient:
            def chat_json(self, messages, **kwargs):
                msg_text = str(messages)
                if "Counterfactual Trace Mutation Probing" in msg_text:
                    return json.dumps(
                        {
                            "case_a_complies": True,
                            "case_b_violates": True,
                            "is_unsupported_clause": False,
                            "verdict": "EQUIVALENT",
                            "explanation": "Matches statutory rule.",
                        }
                    )
                if "Article 7" in msg_text:
                    return json.dumps({"unsupported_by_text": True, "article_id": "Article 7"})
                if "Article 10(2)" in msg_text:
                    return json.dumps(
                        {
                            "article_id": "Article 10(2)",
                            "template_name": "Existence",
                            "activation_activity": "O_Create Offer",
                            "activation_attr": "NumberOfTerms",
                            "activation_op": ">",
                            "activation_val": 0.0,
                            "unsupported_by_text": False,
                        }
                    )
                return json.dumps(
                    {
                        "article_id": "Article 8(1)",
                        "template_name": "Precedence",
                        "activation_activity": "A_Create Application",
                        "target_activity": "A_Concept",
                        "unsupported_by_text": False,
                    }
                )

        res = run_ablation_experiment(
            benchmark_items=items,
            log_df=sample_log,
            process_schema=schema,
            llm_client=_SplitMockClient(),
            enable_l1_l2=False,
            enable_self_correction=False,
            enable_l3_roundtrip=True,
            evaluate_explanations=False,
        )
        self.assertEqual(res["Normative_Accuracy (%)"], 100.0)
        self.assertEqual(res["Rule_Schema_Trap_Accuracy (%)"], 100.0)
        self.assertEqual(res["Trace_Safety_Trap_Accuracy (%)"], 100.0)
        self.assertIsNotNone(res["Normative_Macro_F1"])

    def test_schema_no_ordering_hints_and_benchmark_rebalanced_diversity(self) -> None:
        """Process schema activity descriptions must omit ordering leaks and R01-R22 must stay balanced."""
        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        act_descs = schema.get("activity_descriptions", {})
        self.assertNotIn("precedes ", act_descs.get("A_Concept", "").lower())
        self.assertNotIn("after offers", act_descs.get("A_Validating", "").lower())

        norm_rules = [r for r in BENCHMARK_RULES if not r["is_trap"]]
        precedence_cnt = sum(1 for r in norm_rules if r["template"] == "Precedence")
        self.assertLess(precedence_cnt / len(norm_rules), 0.5)

        templates = {r["template"] for r in norm_rules}
        self.assertIn("Chain Response", templates)
        self.assertIn("Not Response", templates)
        self.assertIn("Not Precedence", templates)

        attr_rules = [r for r in norm_rules if r.get("attr")]
        attrs = [r["attr"] for r in attr_rules]
        self.assertEqual(len(attrs), len(set(attrs)), "Each data attribute should appear at most once in R01-R22.")
        self.assertTrue(any(isinstance(r.get("val"), (bool, str)) for r in attr_rules))

        ok_cr, comp_cr = validate_and_compile_deontic_or_ast(
            {
                "article_id": "Article 10(1)",
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "IMMEDIATE_RESPONSE",
                "anchor_activity": "O_Accepted",
                "consequent_activity": "A_Pending",
                "unsupported_by_text": False,
            },
            process_schema=schema,
            retrieved_chunk={"article_id": "Article 10(1)", "text": "Credit agreements shall be drawn up on durable medium."},
        )
        self.assertTrue(ok_cr)
        self.assertEqual(comp_cr["template_name"], "Chain Response")

        items_path = ROOT_DIR / "data" / "processed" / "benchmark_items.json"
        if items_path.exists():
            with open(items_path, "r", encoding="utf-8") as f:
                bench_items = json.load(f)
            r13_items = [it for it in bench_items if it["rule_id"] == "R13"]
            r19_items = [it for it in bench_items if it["rule_id"] == "R19"]
            self.assertTrue(r13_items and all("case:ApplicationType" in ev for ev in r13_items[0]["events"]))
            self.assertTrue(r19_items and all("Selected" in ev for ev in r19_items[0]["events"]))

            r02_ent_origins = [it["trace_origin"] for it in bench_items if it["rule_id"] == "R02" and it["ground_truth_label"] == "ENTAILED"]
            r06_ent_origins = [it["trace_origin"] for it in bench_items if it["rule_id"] == "R06" and it["ground_truth_label"] == "ENTAILED"]
            r10_ent_origins = [it["trace_origin"] for it in bench_items if it["rule_id"] == "R10" and it["ground_truth_label"] == "ENTAILED"]
            r18_con_origins = [it["trace_origin"] for it in bench_items if it["rule_id"] == "R18" and it["ground_truth_label"] == "CONTRADICTED"]
            self.assertIn("SYNTHETIC_COMPLIANT_B_BEFORE_A_R02", r02_ent_origins)
            self.assertIn("SYNTHETIC_COMPLIANT_B_BEFORE_A_R06", r06_ent_origins)
            self.assertIn("BPIC2017_REAL_COMPLIANT_A_ONLY_R10", r10_ent_origins)
            self.assertIn("SEMANTIC_FAULT_INJECTION_TEMPORAL_ORDER_INVERSION_R18", r18_con_origins)

    def test_adversarial_traps_bypass_regex_and_prober_asymmetry(self):
        from src.evaluation.benchmark_builder import BENCHMARK_RULES
        from src.symbolic.verbalizer_roundtrip import verify_generic_numeric_entities

        chunks_path = ROOT_DIR / "data" / "processed" / "directive_chunks.json"
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks_by_id = {c["article_id"]: c for c in json.load(f)}

        by_id = {r["rule_id"]: r for r in BENCHMARK_RULES}
        for rid in ("R23", "R24", "R25", "R26", "R28"):
            rule = by_id[rid]
            self.assertTrue(rule["is_trap"])
            self.assertEqual(rule["trap_scope"], "rule")
            ast_dict = {
                "article_id": rule["article_id"],
                "template_name": rule["template"],
                "activation_activity": rule["act_a"],
                "target_activity": rule["act_b"],
                "activation_attr": rule["attr"],
                "activation_op": rule["op"],
                "activation_val": rule["val"],
                "time_min": 0 if rule["time_max"] is not None else None,
                "time_max": rule["time_max"],
                "time_unit": "d" if rule["time_max"] is not None else None,
            }
            ok_num, _, diag = verify_generic_numeric_entities(
                ast_dict, chunks_by_id[rule["article_id"]], policy_text=rule["description"]
            )
            self.assertTrue(ok_num, f"{rid} unexpectedly caught by regex guard: {diag}")

        for tpl, act_b in (
            ("Precedence", "A_Pending"),
            ("Response", "A_Cancelled"),
            ("Not Response", "A_Pending"),
            ("Not Precedence", "A_Pending"),
            ("Not Co-Existence", "A_Pending"),
            ("Existence", None),
        ):
            m = generate_counterfactual_trace_mutant(
                {
                    "template_name": tpl,
                    "activation_activity": "O_Create Offer",
                    "target_activity": act_b,
                    "time_max": 14 if tpl in ("Precedence", "Response") else None,
                }
            )
            self.assertIn("tau_asymmetry_story", m)
            self.assertTrue(m["tau_asymmetry_story"])

    def test_timed_response_fault_injection_monotonic_and_activation_anchored(self):
        import pandas as pd
        from src.evaluation.benchmark_builder import _rule_to_ast_dict, build_stratified_trace_benchmark
        from src.evaluation.justification_tree import check_single_trace_semantics
        from src.mde.constraint_ast import DeclareConstraintAST

        rule_r22 = {
            "rule_id": "R22",
            "article_id": "Article 14(3)",
            "dataset_split": "dev",
            "tier": 2,
            "template": "Response",
            "act_a": "A_Cancelled",
            "act_b": "O_Cancelled",
            "attr": None,
            "op": None,
            "val": None,
            "time_max": 14,
            "description": "Within 14 days of withdrawal, secondary settlement executes.",
            "retrieved_chunk": {
                "article_id": "Article 14(3)",
                "article_title": "Right of withdrawal",
                "text": "within 14 calendar days",
                "has_numeric_bound": True,
            },
            "is_trap": False,
            "is_baseless_trap": False,
        }
        t0 = pd.Timestamp("2016-01-04 09:00:00+00:00")
        rows = []
        for idx, cid in enumerate(("Case_Late_A_1", "Case_Late_A_2")):
            base = t0 + pd.Timedelta(days=idx * 2)
            rows.extend([
                {"case:concept:name": cid, "concept:name": "A_Create Application", "time:timestamp": base},
                {"case:concept:name": cid, "concept:name": "O_Create Offer", "time:timestamp": base + pd.Timedelta(days=3)},
                {"case:concept:name": cid, "concept:name": "A_Cancelled", "time:timestamp": base + pd.Timedelta(days=35, hours=2, minutes=11)},
                {"case:concept:name": cid, "concept:name": "O_Cancelled", "time:timestamp": base + pd.Timedelta(days=36, hours=4, minutes=17)},
                {"case:concept:name": cid, "concept:name": "W_Call after offers", "time:timestamp": base + pd.Timedelta(days=37)},
            ])
        df_syn = pd.DataFrame(rows)
        items = build_stratified_trace_benchmark(
            df_propagated=df_syn,
            df_raw=df_syn,
            normative_rules=[rule_r22],
            target_total_items=9,
            split="dev",
        )
        con_items = [it for it in items if it["ground_truth_label"] == "CONTRADICTED"]
        self.assertGreaterEqual(len(con_items), 2)
        gast = DeclareConstraintAST(**_rule_to_ast_dict(rule_r22))
        for it in con_items:
            cdf = it["test_case_df"]
            self.assertTrue(cdf["time:timestamp"].is_monotonic_increasing, "Injected trace timestamps must be monotonic")
            is_comp, details = check_single_trace_semantics(cdf, gast)
            self.assertFalse(is_comp)
            self.assertEqual(details.get("violation_subtype"), "DEADLINE_EXCEEDED")
            t_first = cdf["time:timestamp"].min()
            t_a = cdf.loc[cdf["concept:name"] == "A_Cancelled", "time:timestamp"].max()
            t_b = cdf.loc[cdf["concept:name"] == "O_Cancelled", "time:timestamp"].max()
            self.assertGreater((t_b - t_a).total_seconds() / 86400.0, 14.0)
            self.assertLess(t_b.weekday(), 5, "Shifted timestamp should avoid weekend")
            self.assertNotEqual(t_b.strftime("%H:%M:%S"), t_first.strftime("%H:%M:%S"))

    def test_behavioral_deontic_compiler_guards_and_permission_modality(self) -> None:
        """
        Verify Level-2 Behavioral-Aware Deontic M2M Compiler checks:
        1. PERMISSION_RIGHT + MANDATORY_RESPONSE -> Precedence (non-obligatory precondition semantics).
        2. Strict Causal Inversion Guard (Precedence/Response reversing strict_causal_pairs).
        3. Vacuous Reversed Prohibition Guard (Not Precedence on reversed strict causal pair).
        4. Behavioral Mutual-Exclusion Conflict & Lifecycle Contradiction guards.
        5. Causal Attribute Availability violation diagnostic via ProcessSchemaValidator.
        """
        from src.mde.deontic_mde_compiler import compile_deontic_to_declare4py

        with open(ROOT_DIR / "data" / "processed" / "process_schema.json", "r", encoding="utf-8") as f:
            process_schema = json.load(f)

        # 1. PERMISSION_RIGHT + MANDATORY_RESPONSE compiles to Precedence (time-bounded right)
        st_perm, res_perm = compile_deontic_to_declare4py(
            {
                "article_id": "Article 15(1)",
                "deontic_modality": "PERMISSION_RIGHT",
                "temporal_relation": "MANDATORY_RESPONSE",
                "anchor_activity": "O_Sent (mail and online)",
                "consequent_activity": "O_Cancelled",
                "deadline_days": 30,
                "unsupported_by_text": False,
            },
            process_schema=process_schema,
        )
        self.assertEqual(st_perm, "COMPILED_OK")
        self.assertIsInstance(res_perm, dict)
        self.assertEqual(res_perm["template_name"], "Precedence")
        self.assertEqual(res_perm["time_max"], 30)

        # 2. Strict Causal Inversion Guard: A_Accepted strictly follows A_Create Application (100%)
        st_inv, err_inv = compile_deontic_to_declare4py(
            {
                "article_id": "Article 8(1)",
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "PREREQUISITE_BEFORE",
                "anchor_activity": "A_Accepted",
                "consequent_activity": "A_Create Application",
                "unsupported_by_text": False,
            },
            process_schema=process_schema,
        )
        self.assertEqual(st_inv, "COMPILE_ERROR")
        self.assertIn("Behavioral Causal Inversion Violation", str(err_inv))

        # 3. Vacuous Reversed Prohibition Guard: Not Precedence(A_Cancelled, O_Sent (mail and online))
        st_vac, err_vac = compile_deontic_to_declare4py(
            {
                "article_id": "Article 14(1)",
                "deontic_modality": "PROHIBITION",
                "temporal_relation": "PREREQUISITE_BEFORE",
                "anchor_activity": "A_Cancelled",
                "consequent_activity": "O_Sent (mail and online)",
                "deadline_days": 14,
                "unsupported_by_text": False,
            },
            process_schema=process_schema,
        )
        self.assertEqual(st_vac, "COMPILE_ERROR")
        self.assertIn("Behavioral Vacuous Reversed Prohibition", str(err_vac))

        # 4. Behavioral Mutual-Exclusion Conflict: Response(O_Accepted, A_Cancelled)
        st_mut, err_mut = compile_deontic_to_declare4py(
            {
                "article_id": "Article 14(1)",
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "MANDATORY_RESPONSE",
                "anchor_activity": "O_Accepted",
                "consequent_activity": "A_Cancelled",
                "unsupported_by_text": False,
            },
            process_schema=process_schema,
        )
        self.assertEqual(st_mut, "COMPILE_ERROR")
        self.assertIn("Behavioral Mutual-Exclusion Conflict", str(err_mut))

        # 5. Behavioral Lifecycle Contradiction: Not Co-Existence(O_Create Offer, O_Created)
        st_lc, err_lc = compile_deontic_to_declare4py(
            {
                "article_id": "Article 10(1)",
                "deontic_modality": "PROHIBITION",
                "temporal_relation": "MUTUAL_EXCLUSION",
                "anchor_activity": "O_Create Offer",
                "consequent_activity": "O_Created",
                "unsupported_by_text": False,
            },
            process_schema=process_schema,
        )
        self.assertEqual(st_lc, "COMPILE_ERROR")
        self.assertIn("Behavioral Lifecycle Contradiction", str(err_lc))

        # 6. Causal Attribute Availability Violation: OfferedAmount anchored on A_Create Application
        st_attr, err_attr = compile_deontic_to_declare4py(
            {
                "article_id": "Article 2(2)(c)",
                "deontic_modality": "OBLIGATION",
                "temporal_relation": "UNARY_CONDITION",
                "anchor_activity": "A_Create Application",
                "attribute_guard": "OfferedAmount",
                "guard_operator": ">=",
                "guard_threshold": 200.0,
                "unsupported_by_text": False,
            },
            process_schema=process_schema,
        )
        self.assertEqual(st_attr, "COMPILE_ERROR")
        self.assertIn("Causal Attribute Availability Violation", str(err_attr))
        self.assertIn("O_Create Offer", str(err_attr))

        # 7. Zero false positives on valid rules (Precedence & Not Co-Existence)
        st_ok1, _ = compile_deontic_to_declare4py(
            {
                "article_id": "Article 14(1)",
                "deontic_modality": "PERMISSION_RIGHT",
                "temporal_relation": "PREREQUISITE_BEFORE",
                "anchor_activity": "O_Sent (mail and online)",
                "consequent_activity": "A_Cancelled",
                "deadline_days": 14,
                "unsupported_by_text": False,
            },
            process_schema=process_schema,
        )
        st_ok2, _ = compile_deontic_to_declare4py(
            {
                "article_id": "Article 14(3)",
                "deontic_modality": "PROHIBITION",
                "temporal_relation": "MUTUAL_EXCLUSION",
                "anchor_activity": "A_Cancelled",
                "consequent_activity": "A_Pending",
                "unsupported_by_text": False,
            },
            process_schema=process_schema,
        )
        self.assertEqual(st_ok1, "COMPILED_OK")
        self.assertEqual(st_ok2, "COMPILED_OK")


if __name__ == "__main__":
    unittest.main()
