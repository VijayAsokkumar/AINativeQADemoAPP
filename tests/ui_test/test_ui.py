import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_ui_environment() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env.ui"
    if not env_file.exists():
        return

    for line in env_file.read_text().splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
            continue

        key, value = stripped_line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_ui_environment()

UI_BASE_URL = os.getenv("UI_BASE_URL", "http://localhost:3000")
VALID_USERNAME = os.getenv("VALID_USERNAME", "test")
VALID_PASSWORD = os.getenv("VALID_PASSWORD", "test123")
SEARCH_ADDRESS = "8 Waterloo Quay"


def test_ui_user_can_log_in_and_start_address_lookup(page):
    logger.info("Starting UI test: user can log in and access address checker")
    page.goto(UI_BASE_URL)
    logger.info("Opened UI at %s", UI_BASE_URL)

    page.get_by_label("Username").fill(VALID_USERNAME)
    page.get_by_label("Password").fill(VALID_PASSWORD)
    logger.info("Filled login form for user %s", VALID_USERNAME)
    page.get_by_role("button", name="Login").click()
    logger.info("Clicked login")

    page.get_by_text(f"Logged in as {VALID_USERNAME}").wait_for()
    logger.info("Verified logged-in state")
    page.get_by_label("Address").fill(SEARCH_ADDRESS)
    logger.info("Searching for address: %s", SEARCH_ADDRESS)
    page.get_by_role("button", name="Check Address").click()
    logger.info("Clicked address check")
    page.wait_for_timeout(3000)

    search_message = page.locator("#resultMessage")
    search_message.wait_for()
    result_summary = page.locator("#resultSummary").text_content()
    table_rows = page.locator("#resultsTableBody tr").all_text_contents()

    logger.info("Search message text: %s", search_message.text_content())
    logger.info("Search summary text: %s", result_summary)
    logger.info("Search table rows: %s", table_rows)
    assert "Searching NZ Post matches" in search_message.text_content()


def test_ui_logged_out_user_cannot_use_address_checker(page):
    logger.info("Starting UI test: logged-out user cannot use address checker")
    page.goto(UI_BASE_URL)
    logger.info("Opened UI at %s", UI_BASE_URL)

    page.get_by_label("Address").fill(SEARCH_ADDRESS)
    logger.info("Filled address field while logged out with address: %s", SEARCH_ADDRESS)
    page.get_by_role("button", name="Check Address").click()
    logger.info("Clicked address check while logged out")

    login_message = page.locator("#loginMessage")
    login_message.wait_for()
    logger.info("Login message text: %s", login_message.text_content())
    assert "Please login first." in login_message.text_content()
