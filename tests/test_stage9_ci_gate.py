"""Self-tests for the strict regression and pull-request CI release gate."""
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
from pathlib import Path
import re
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class CIGateTests(unittest.TestCase):
    def test_pr_workflow_and_python_matrix_include_ha_baseline(self):
        workflow = (
            ROOT / ".github" / "workflows" / "euros-os-stage4-tests.yml"
        ).read_text(encoding="utf-8")
        self.assertRegex(workflow, r"(?m)^  pull_request:\s*$")
        self.assertRegex(workflow, r"(?m)^  workflow_dispatch:\s*$")
        self.assertIn('"feature/**"', workflow)
        self.assertIn('"fix/**"', workflow)
        self.assertIn('python-version: ["3.12", "3.13", "3.14"]', workflow)
        self.assertIn('"homeassistant==2026.11.0"', workflow)
        self.assertIn("scripts/run_unit_tests_strict.py", workflow)
        self.assertIn("Verify GEO/EMS entry registration", workflow)

    def test_strict_runner_fails_if_a_test_is_skipped(self):
        strict_runner = ROOT / "scripts" / "run_unit_tests_strict.py"
        spec = importlib.util.spec_from_file_location(
            "test_strict_runner_module", strict_runner
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class FakeSkippedTest(unittest.TestCase):
            @unittest.skip("Must not silently pass the CI gate")
            def test_skip(self):
                self.fail("Should never execute")

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(FakeSkippedTest)
        with (
            patch.object(module.unittest.TestLoader, "discover", return_value=suite),
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()),
        ):
            result = module.main()
        self.assertEqual(result, 1)

    def test_real_ha_fixture_has_explicit_skip_guard(self):
        source = (ROOT / "tests_ha" / "conftest.py").read_text(encoding="utf-8")
        self.assertIn("pytest_sessionfinish", source)
        self.assertIn('"skipped"', source)
        self.assertIn('"xfailed"', source)
        self.assertIn("session.exitstatus = pytest.ExitCode.TESTS_FAILED", source)


if __name__ == "__main__":
    unittest.main()
