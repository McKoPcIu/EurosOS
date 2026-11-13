"""Fail the HA API suite if a test is skipped or xfailed.

No hardware or network fixture belongs in this suite. Explicitly failing
on skips avoids presenting an incomplete validation as a green release gate.
"""
from __future__ import annotations

import pytest


def pytest_sessionfinish(session, exitstatus):
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    stats = reporter.stats
    incomplete = sum(len(stats.get(key, ())) for key in ("skipped", "xfailed", "xpassed"))
    if incomplete:
        reporter.write_line(f"HA API suite incomplete: {incomplete} skipped/xfail/xpass cases")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
