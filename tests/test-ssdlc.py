#!/usr/bin/env python3
"""
SSDLC module test suite — unit tests for ssdlc.py.
Run: python3 test-ssdlc.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Point WORKSPACE at a temp dir so tests don't touch real state
TMP = Path(tempfile.mkdtemp(prefix="ssdlc_test_"))
os.environ["WORKSPACE"] = str(TMP)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent-container"))
import ssdlc
# Force module to use our temp dir
ssdlc.WORKSPACE = TMP
ssdlc.SSDLC_DIR = TMP / ".parapet" / "ssdlc"


def _clean(project):
    """Delete SSDLC state for a project to ensure test isolation."""
    path = ssdlc.SSDLC_DIR / f"{project}.json"
    if path.exists():
        path.unlink()

_counter = 0

def _project(name):
    """Generate a unique project name for test isolation."""
    global _counter
    _counter += 1
    return f"{name}_{_counter}"


class TestStateInit(unittest.TestCase):
    """State initialization and persistence."""

    def setUp(self):
        self.project = _project("init")
        ssdlc.SSDLC_DIR = TMP / ".parapet" / "ssdlc"
        _clean(self.project)

    def test_fresh_state_has_six_phases(self):
        state = ssdlc.load_state(self.project)
        self.assertEqual(len(state["phases"]), 6)
        self.assertEqual(state["overall_status"], "not_started")
        self.assertIsNone(state["current_phase"])

    def test_fresh_state_has_correct_checklist_counts(self):
        state = ssdlc.load_state(self.project)
        counts = {
            "planning": 8, "analysis": 8, "design": 9,
            "implementation": 10, "maintenance": 9, "retirement": 8,
        }
        for phase, expected in counts.items():
            actual = len(state["phases"][phase]["checklist"])
            self.assertEqual(actual, expected, f"{phase}: expected {expected}, got {actual}")

    def test_state_is_persisted(self):
        state = ssdlc.load_state(self.project)
        ssdlc.save_state(self.project, state)
        path = ssdlc.SSDLC_DIR / f"{self.project}.json"
        self.assertTrue(path.exists())

    def test_reload_preserves_data(self):
        state = ssdlc.load_state(self.project)
        state["metadata"]["owner"] = "alice"
        ssdlc.save_state(self.project, state)
        reloaded = ssdlc.load_state(self.project)
        self.assertEqual(reloaded["metadata"]["owner"], "alice")

    def test_total_checklist_items(self):
        state = ssdlc.load_state(self.project)
        total = sum(len(p["checklist"]) for p in state["phases"].values())
        self.assertEqual(total, 52)

    def test_all_phases_initially_pending(self):
        state = ssdlc.load_state(self.project)
        for key, ps in state["phases"].items():
            self.assertEqual(ps["status"], "pending", f"{key} should be pending")


class TestPhaseLifecycle(unittest.TestCase):
    """Phase start, complete, and gating."""

    def setUp(self):
        self.project = _project("lifecycle")
        _clean(self.project)
        ssdlc.load_state(self.project)

    def test_start_first_phase_succeeds(self):
        r = ssdlc.start_phase(self.project, "planning")
        self.assertTrue(r["ok"])
        state = ssdlc.load_state(self.project)
        self.assertEqual(state["phases"]["planning"]["status"], "in_progress")
        self.assertEqual(state["current_phase"], "planning")

    def test_cannot_start_phase_out_of_order(self):
        r = ssdlc.start_phase(self.project, "implementation")
        self.assertFalse(r["ok"])
        self.assertIn("blocked_by", r)

    def test_cannot_complete_phase_not_in_progress(self):
        r = ssdlc.complete_phase(self.project, "planning")
        self.assertFalse(r["ok"])

    def test_cannot_complete_with_missing_required_items(self):
        ssdlc.start_phase(self.project, "planning")
        r = ssdlc.complete_phase(self.project, "planning")
        self.assertFalse(r["ok"])
        self.assertIn("missing_items", r)

    def test_complete_phase_with_all_required(self):
        ssdlc.start_phase(self.project, "planning")
        # Check all required items (P1-P5, P8)
        for item_id in ["P1", "P2", "P3", "P4", "P5", "P8"]:
            ssdlc.check_item(self.project, "planning", item_id, True, "done")
        r = ssdlc.complete_phase(self.project, "planning")
        self.assertTrue(r["ok"])
        self.assertEqual(r["next_phase"], "analysis")

    def test_optional_items_not_required_for_completion(self):
        ssdlc.start_phase(self.project, "planning")
        for item_id in ["P1", "P2", "P3", "P4", "P5", "P8"]:
            ssdlc.check_item(self.project, "planning", item_id, True, "done")
        # P6 and P7 are optional — leave unchecked
        r = ssdlc.complete_phase(self.project, "planning")
        self.assertTrue(r["ok"])

    def test_complete_last_phase_sets_overall_completed(self):
        for phase in ["planning", "analysis", "design", "implementation", "maintenance", "retirement"]:
            ssdlc.start_phase(self.project, phase)
            for c in ssdlc.PHASES[phase]["checklist"]:
                if c["required"]:
                    ssdlc.check_item(self.project, phase, c["id"], True, "auto")
            ssdlc.complete_phase(self.project, phase)
        state = ssdlc.load_state(self.project)
        self.assertEqual(state["overall_status"], "completed")

    def test_start_unknown_phase_fails(self):
        r = ssdlc.start_phase(self.project, "nonexistent")
        self.assertFalse(r["ok"])


class TestChecklistOperations(unittest.TestCase):
    """Checklist item toggling."""

    def setUp(self):
        self.project = _project("checklist")
        _clean(self.project)
        ssdlc.load_state(self.project)

    def test_check_item_sets_checked_true(self):
        r = ssdlc.check_item(self.project, "planning", "P1", True, "done")
        self.assertTrue(r["ok"])
        state = ssdlc.load_state(self.project)
        c = state["phases"]["planning"]["checklist"]["P1"]
        self.assertTrue(c["checked"])
        self.assertEqual(c["notes"], "done")
        self.assertIsNotNone(c["checked_at"])

    def test_uncheck_item(self):
        ssdlc.check_item(self.project, "planning", "P1", True, "done")
        r = ssdlc.check_item(self.project, "planning", "P1", False)
        self.assertTrue(r["ok"])
        state = ssdlc.load_state(self.project)
        self.assertFalse(state["phases"]["planning"]["checklist"]["P1"]["checked"])

    def test_check_unknown_item_fails(self):
        r = ssdlc.check_item(self.project, "planning", "ZZ99", True)
        self.assertFalse(r["ok"])

    def test_check_unknown_phase_fails(self):
        r = ssdlc.check_item(self.project, "nonexistent", "P1", True)
        self.assertFalse(r["ok"])

    def test_check_item_persists_across_loads(self):
        ssdlc.check_item(self.project, "analysis", "A3", True, "GDPR classification")
        state = ssdlc.load_state(self.project)
        self.assertTrue(state["phases"]["analysis"]["checklist"]["A3"]["checked"])


class TestRiskManagement(unittest.TestCase):
    """Risk scoring and STRIDE categories."""

    def setUp(self):
        self.project = _project("risks")
        _clean(self.project)
        ssdlc.load_state(self.project)
        ssdlc.load_state(self.project)

    def test_add_risk_basic(self):
        r = ssdlc.add_risk(self.project, "design", "SQL injection risk",
                           "User input not parameterized", 4, 5,
                           "tampering", "Use prepared statements")
        self.assertTrue(r["ok"])
        risk = r["risk"]
        self.assertEqual(risk["title"], "SQL injection risk")
        self.assertEqual(risk["level"], "critical")
        self.assertEqual(risk["score"], 20)

    def test_risk_scoring_boundaries(self):
        cases = [
            (1, 1, "info"),     # score 1: info (1-4)
            (2, 3, "low"),      # score 6: low (5-9)
            (3, 4, "medium"),   # score 12: medium (10-14)
            (4, 4, "high"),     # score 16: high (15-19)
            (4, 5, "critical"), # score 20: critical (20+)
            (5, 5, "critical"), # score 25: critical
        ]
        for likelihood, impact, expected_level in cases:
            r = ssdlc.add_risk(self.project, "analysis", f"Risk {likelihood}x{impact}",
                               "test", likelihood, impact)
            self.assertEqual(r["risk"]["level"], expected_level,
                             f"{likelihood}x{impact} should be {expected_level}, got {r['risk']['level']}")
            self.assertEqual(r["risk"]["score"], likelihood * impact)

    def test_risk_clamped_to_valid_range(self):
        r = ssdlc.add_risk(self.project, "analysis", "Over scale", "test", 99, -5)
        self.assertEqual(r["risk"]["likelihood"], 5)
        self.assertEqual(r["risk"]["impact"], 1)

    def test_risks_persist_in_phase(self):
        ssdlc.add_risk(self.project, "implementation", "R1", "desc", 3, 3)
        ssdlc.add_risk(self.project, "implementation", "R2", "desc", 2, 4)
        state = ssdlc.load_state(self.project)
        self.assertEqual(len(state["phases"]["implementation"]["risks"]), 2)

    def test_risk_has_stride_category(self):
        r = ssdlc.add_risk(self.project, "design", "Spoof test", "desc", 3, 3,
                           "spoofing", "MFA required")
        self.assertEqual(r["risk"]["stride_category"], "spoofing")

    def test_risk_status_is_open_by_default(self):
        r = ssdlc.add_risk(self.project, "planning", "Budget risk", "desc", 3, 3)
        self.assertEqual(r["risk"]["status"], "open")


class TestArtifacts(unittest.TestCase):
    """Artifact recording."""

    def setUp(self):
        self.project = _project("artifacts")
        _clean(self.project)
        ssdlc.load_state(self.project)

    def test_record_artifact(self):
        r = ssdlc.record_artifact(self.project, "design",
                                  "security_architecture.md",
                                  "/workspace/ssdlc/security_architecture.md",
                                  "sha256:abc123")
        self.assertTrue(r["ok"])
        state = ssdlc.load_state(self.project)
        art = state["phases"]["design"]["artifacts"]["security_architecture.md"]
        self.assertTrue(art["created"])
        self.assertEqual(art["hash"], "sha256:abc123")

    def test_unknown_artifact_fails(self):
        r = ssdlc.record_artifact(self.project, "design", "bogus.md", "/tmp/bogus.md")
        self.assertFalse(r["ok"])


class TestProgress(unittest.TestCase):
    """Progress calculation."""

    def setUp(self):
        self.project = _project("progress")
        _clean(self.project)
        ssdlc.load_state(self.project)

    def test_empty_project_zero_pct(self):
        p = ssdlc.get_progress(self.project)
        self.assertEqual(p["overall_pct"], 0.0)
        self.assertEqual(p["checked_items"], 0)

    def test_progress_after_checking_items(self):
        ssdlc.check_item(self.project, "planning", "P1", True)
        ssdlc.check_item(self.project, "planning", "P2", True)
        p = ssdlc.get_progress(self.project)
        self.assertEqual(p["checked_items"], 2)
        self.assertGreater(p["overall_pct"], 0)

    def test_progress_after_completing_phase(self):
        ssdlc.start_phase(self.project, "planning")
        for item_id in ["P1", "P2", "P3", "P4", "P5", "P8"]:
            ssdlc.check_item(self.project, "planning", item_id, True, "done")
        ssdlc.complete_phase(self.project, "planning")
        p = ssdlc.get_progress(self.project)
        self.assertEqual(p["phases"]["planning"]["status"], "completed")
        self.assertEqual(p["current_phase"], "analysis")


class TestReports(unittest.TestCase):
    """Report generation."""

    def setUp(self):
        self.project = _project("reports")
        _clean(self.project)
        ssdlc.load_state(self.project)

    def test_generate_report_basic(self):
        report = ssdlc.generate_report(self.project)
        self.assertEqual(report["project"], self.project)
        self.assertIn("progress", report)
        self.assertIn("risks_summary", report)
        self.assertIn("risks", report)

    def test_report_includes_risks(self):
        ssdlc.add_risk(self.project, "implementation", "Critical bug", "desc", 5, 5)
        report = ssdlc.generate_report(self.project)
        self.assertEqual(report["risks_summary"]["total"], 1)
        self.assertEqual(len(report["risks"]["critical"]), 1)

    def test_markdown_report_contains_phases(self):
        md = ssdlc.export_report_markdown(self.project)
        self.assertIn("# SSDLC Report", md)
        self.assertIn("## Phase Progress", md)
        self.assertIn("Planning", md)
        self.assertIn("Retirement", md)

    def test_markdown_report_contains_risk_table(self):
        ssdlc.add_risk(self.project, "design", "Design flaw", "Bad architecture", 4, 4,
                       "tampering", "Redesign module")
        md = ssdlc.export_report_markdown(self.project)
        self.assertIn("Design flaw", md)
        self.assertIn("Redesign module", md)


class TestMetadata(unittest.TestCase):
    """Project metadata management."""

    def setUp(self):
        self.project = _project("metadata")
        _clean(self.project)
        ssdlc.load_state(self.project)

    def test_set_metadata_owner(self):
        r = ssdlc.set_metadata(self.project, "owner", "bob@example.com")
        self.assertTrue(r["ok"])
        state = ssdlc.load_state(self.project)
        self.assertEqual(state["metadata"]["owner"], "bob@example.com")

    def test_set_metadata_compliance(self):
        r = ssdlc.set_metadata(self.project, "compliance_frameworks", ["GDPR", "ISO 27001"])
        self.assertTrue(r["ok"])
        state = ssdlc.load_state(self.project)
        self.assertIn("GDPR", state["metadata"]["compliance_frameworks"])

    def test_compliance_checks_in_report(self):
        ssdlc.set_metadata(self.project, "compliance_frameworks", ["GDPR"])
        report = ssdlc.generate_report(self.project)
        checks = report.get("framework_compliance", [])
        self.assertTrue(any(c["framework"] == "GDPR" for c in checks))


class TestEdgeCases(unittest.TestCase):
    """Edge cases and error handling."""

    def setUp(self):
        self.project = _project("edges")
        _clean(self.project)
        ssdlc.load_state(self.project)

    def test_start_phase_twice(self):
        ssdlc.start_phase(self.project, "planning")
        # Starting again just re-sets started_at timestamp — should still be ok
        r = ssdlc.start_phase(self.project, "planning")
        self.assertTrue(r["ok"])

    def test_complete_phase_twice_fails(self):
        ssdlc.start_phase(self.project, "planning")
        for item_id in ["P1", "P2", "P3", "P4", "P5", "P8"]:
            ssdlc.check_item(self.project, "planning", item_id, True, "done")
        ssdlc.complete_phase(self.project, "planning")
        r = ssdlc.complete_phase(self.project, "planning")
        self.assertFalse(r["ok"])  # already completed, not in_progress

    def test_check_item_on_completed_phase_still_works(self):
        ssdlc.start_phase(self.project, "planning")
        for item_id in ["P1", "P2", "P3", "P4", "P5", "P8"]:
            ssdlc.check_item(self.project, "planning", item_id, True, "done")
        ssdlc.complete_phase(self.project, "planning")
        # Checking after completion should still work (allows corrections)
        r = ssdlc.check_item(self.project, "planning", "P6", True, "optional after")
        self.assertTrue(r["ok"])

    def test_multiple_projects_isolated(self):
        ssdlc.load_state("project_a")
        ssdlc.load_state("project_b")
        ssdlc.check_item("project_a", "planning", "P1", True, "a")
        ssdlc.check_item("project_b", "planning", "P1", True, "b")
        state_a = ssdlc.load_state("project_a")
        state_b = ssdlc.load_state("project_b")
        self.assertEqual(state_a["phases"]["planning"]["checklist"]["P1"]["notes"], "a")
        self.assertEqual(state_b["phases"]["planning"]["checklist"]["P1"]["notes"], "b")

    def test_stride_categories_complete(self):
        self.assertEqual(len(ssdlc.STRIDE), 6)
        expected = ["spoofing", "tampering", "repudiation",
                    "information_disclosure", "denial_of_service",
                    "elevation_of_privilege"]
        for cat in expected:
            self.assertIn(cat, ssdlc.STRIDE)

    def test_risk_matrix_levels(self):
        self.assertEqual(len(ssdlc.RISK_MATRIX), 5)
        for level in ["critical", "high", "medium", "low", "info"]:
            self.assertIn(level, ssdlc.RISK_MATRIX)

    def test_full_run_all_phases(self):
        """End-to-end: run all 6 phases sequentially."""
        for phase_key in ["planning", "analysis", "design",
                          "implementation", "maintenance", "retirement"]:
            r = ssdlc.start_phase(self.project, phase_key)
            self.assertTrue(r["ok"], f"start {phase_key} failed: {r}")

            for c in ssdlc.PHASES[phase_key]["checklist"]:
                    ssdlc.check_item(self.project, phase_key, c["id"], True,
                                     f"auto-{phase_key}")

            r = ssdlc.complete_phase(self.project, phase_key)
            self.assertTrue(r["ok"], f"complete {phase_key} failed: {r}")

        state = ssdlc.load_state(self.project)
        self.assertEqual(state["overall_status"], "completed")
        for ps in state["phases"].values():
            self.assertEqual(ps["status"], "completed")

        p = ssdlc.get_progress(self.project)
        self.assertEqual(p["overall_pct"], 100.0)


if __name__ == "__main__":
    # Clean up any previous temp files
    import shutil
    try:
        shutil.rmtree(TMP, ignore_errors=True)
    except OSError:
        pass

    # Run tests
    unittest.main(verbosity=2, exit=False)

    # Print summary
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors:   {len(result.errors)}")
    if result.wasSuccessful():
        print("RESULT: ALL TESTS PASSED")
    else:
        print("RESULT: FAILURES DETECTED")
        for test, traceback in result.failures + result.errors:
            print(f"  - {test}: {traceback.split(chr(10))[-2]}")

    # Cleanup
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(0 if result.wasSuccessful() else 1)
