from pathlib import Path
import re

import pytest


ARTIFACT_DIR = Path("test-results/playwright")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(autouse=True)
def capture_ui_failure_artifacts(request, page):
    yield

    report = getattr(request.node, "rep_call", None)
    if report is None or not report.failed:
        return

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    test_name = _safe_name(request.node.nodeid)

    screenshot_path = ARTIFACT_DIR / f"{test_name}.png"
    html_path = ARTIFACT_DIR / f"{test_name}.html"

    page.screenshot(path=str(screenshot_path), full_page=True)
    html_path.write_text(page.content(), encoding="utf-8")
