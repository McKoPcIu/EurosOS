"""Run all offline Euros OS tests; fail on errors, skipped or expected failures.

This is intentionally isolated from tests_ha/: legacy tests provide fake
homeassistant modules in sys.modules and must not mix with real HA imports.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    suite = unittest.TestLoader().discover(
        start_dir=str(root / "tests"), pattern="test_*.py", top_level_dir=str(root / "tests")
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    if result.testsRun == 0:
        print("ERROR: no tests discovered", file=sys.stderr)
        return 1
    if result.skipped or result.expectedFailures or result.unexpectedSuccesses:
        print(
            "ERROR: incomplete test suite; "
            f"skipped={len(result.skipped)} "
            f"expectedFailures={len(result.expectedFailures)} "
            f"unexpectedSuccesses={len(result.unexpectedSuccesses)}",
            file=sys.stderr,
        )
        return 1
    print(f"STRICT RESULT: {result.testsRun} tests, 0 skipped, 0 failures, 0 errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
