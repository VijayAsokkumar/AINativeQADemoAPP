import os
from pathlib import Path


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


def test_ui_user_can_log_in_and_start_address_lookup(page):
    page.goto(UI_BASE_URL)

    page.get_by_label("Username").fill(VALID_USERNAME)
    page.get_by_label("Password").fill(VALID_PASSWORD)
    page.get_by_role("button", name="Login").click()

    page.get_by_text(f"Logged in as {VALID_USERNAME}").wait_for()
    page.get_by_role("button", name="Check Address").click()

    search_message = page.locator("#resultMessage")
    search_message.wait_for()
    assert "Searching NZ Post matches" in search_message.text_content()


def test_ui_logged_out_user_cannot_use_address_checker(page):
    page.goto(UI_BASE_URL)

    page.get_by_label("Address").fill("8 Waterloo Quay")
    page.get_by_role("button", name="Check Address").click()

    login_message = page.locator("#loginMessage")
    login_message.wait_for()
    assert "Please login first." in login_message.text_content()
