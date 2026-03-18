import os
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def load_test_environment() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env.test"
    if not env_file.exists():
        return

    for line in env_file.read_text().splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
            continue

        key, value = stripped_line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_test_environment()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
VALID_USERNAME = os.getenv("VALID_USERNAME", "test")
VALID_PASSWORD = os.getenv("VALID_PASSWORD", "test123")


def login(username: str = VALID_USERNAME, password: str = VALID_PASSWORD) -> requests.Response:
    logger.info("POST /login with username=%s", username)
    return requests.post(
        f"{BASE_URL}/login",
        json={"username": username, "password": password},
        timeout=15,
    )


def get_auth_headers() -> dict[str, str]:
    response = login()
    assert response.status_code == 200, response.text

    token = response.json()["token"]
    logger.info("Received auth token from /login")
    return {"Authorization": f"Bearer {token}"}


def test_login_with_valid_credentials():
    logger.info("Starting API test: valid login returns token")
    response = login()

    logger.info("Login response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 200
    body = response.json()
    assert "token" in body
    assert isinstance(body["token"], str)
    assert body["token"]


def test_login_with_invalid_credentials():
    logger.info("Starting API test: invalid login should be rejected")
    response = login(username="wrong", password="wrong")

    logger.info("Login response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_with_empty_fields():
    logger.info("Starting API test: empty login should return validation error")
    response = login(username="", password="")

    logger.info("Login response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username and password are required"


def test_protected_address_endpoint_blocked_without_authentication():
    logger.info("Starting API test: unauthenticated address check should be blocked")
    response = requests.get(
        f"{BASE_URL}/address-check",
        params={"q": "8 Waterloo Quay"},
        timeout=15,
    )

    logger.info("Address check response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 401
    assert response.json()["detail"] == "Please login first"


def test_address_check_with_valid_full_address():
    logger.info("Starting API test: valid full address should return matches")
    response = requests.get(
        f"{BASE_URL}/address-check",
        params={"q": "8 Waterloo Quay"},
        headers=get_auth_headers(),
        timeout=30,
    )

    logger.info("Address check response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "valid"
    assert body["total_matches"] >= 1
    assert len(body["addresses"]) >= 1
    assert "full_address" in body["addresses"][0]


def test_address_check_with_partial_address():
    logger.info("Starting API test: partial address should return a valid or invalid response")
    response = requests.get(
        f"{BASE_URL}/address-check",
        params={"q": "Waterloo"},
        headers=get_auth_headers(),
        timeout=30,
    )

    logger.info("Address check response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"valid", "invalid"}
    if body["status"] == "valid":
        assert body["total_matches"] >= 1
        assert len(body["addresses"]) >= 1


def test_address_check_with_empty_input():
    logger.info("Starting API test: empty address input should return bad request")
    response = requests.get(
        f"{BASE_URL}/address-check",
        params={"q": "   "},
        headers=get_auth_headers(),
        timeout=15,
    )

    logger.info("Address check response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 400
    assert response.json()["detail"] == "Address query is required"


def test_address_check_with_invalid_non_existent_address():
    logger.info("Starting API test: invalid address should return not found")
    response = requests.get(
        f"{BASE_URL}/address-check",
        params={"q": "zzzzzzzzzz definitely not a real nz address 999999"},
        headers=get_auth_headers(),
        timeout=30,
    )

    logger.info("Address check response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 200
    assert response.json() == {"status": "invalid", "message": "Address not found"}


def test_address_check_when_backend_or_nzpost_is_unavailable():
    logger.info("Starting API test: simulated backend/NZ Post failure should return 503")
    response = requests.get(
        f"{BASE_URL}/address-check",
        params={"q": "please fail now"},
        headers=get_auth_headers(),
        timeout=15,
    )

    logger.info("Address check response status=%s body=%s", response.status_code, response.text)
    assert response.status_code == 503
    assert response.json()["detail"] == "Address service unavailable"
