import os
import time

import requests
from fastapi import FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


APP_USERNAME = "test"
APP_PASSWORD = "test123"
NZPOST_CLIENT_ID = os.getenv("NZPOST_CLIENT_ID", "c951758c3a9b48e284838a66315daa23")
NZPOST_CLIENT_SECRET = os.getenv("NZPOST_CLIENT_SECRET", "23AA93661039439aBA84e52D9E8FFE8a")
NZPOST_USER_NAME = os.getenv("NZPOST_USER_NAME", "")
NZPOST_TOKEN_URL = "https://oauth.nzpost.co.nz/as/token.oauth2"
NZPOST_FIND_URL = "https://api.nzpost.co.nz/addresschecker/1.0/find"

token_cache = {
    "access_token": "",
    "expires_at": 0.0,
}

app = FastAPI()
bearer_scheme = HTTPBearer(auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str | None = None
    password: str | None = None


def extract_error_message(payload: dict) -> str:
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        first_error = errors[0]
        if isinstance(first_error, dict):
            return first_error.get("details") or first_error.get("message") or "Request failed"

    return payload.get("message") or payload.get("detail") or "Request failed"


def extract_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if not credentials:
        return ""

    if credentials.scheme.lower() != "bearer":
        return ""

    token = credentials.credentials.strip()
    if not token:
        return ""

    return token


def require_logged_in(credentials: HTTPAuthorizationCredentials | None) -> str:
    provided_token = extract_bearer_token(credentials)
    if not provided_token:
        raise HTTPException(status_code=401, detail="Please login first")

    cached_token = token_cache["access_token"]
    expires_at = token_cache["expires_at"]

    if not cached_token or expires_at <= time.time():
        clear_cached_token()
        raise HTTPException(status_code=401, detail="Session expired. Please login again")

    if provided_token != cached_token:
        raise HTTPException(status_code=401, detail="Session expired. Please login again")

    return provided_token


def clear_cached_token() -> None:
    token_cache["access_token"] = ""
    token_cache["expires_at"] = 0.0


def require_nzpost_config() -> None:
    if not NZPOST_CLIENT_ID or not NZPOST_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="NZ Post credentials are not configured")


def get_nzpost_token() -> str:
    if token_cache["access_token"] and token_cache["expires_at"] > time.time():
        return token_cache["access_token"]

    require_nzpost_config()

    try:
        response = requests.post(
            NZPOST_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": NZPOST_CLIENT_ID,
                "client_secret": NZPOST_CLIENT_SECRET,
            },
            timeout=15,
        )
    except requests.RequestException as error:
        raise HTTPException(status_code=503, detail="Unable to reach NZ Post OAuth service") from error

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if not response.ok:
        raise HTTPException(status_code=503, detail=extract_error_message(payload))

    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=503, detail="NZ Post token was not returned")

    expires_in = int(payload.get("expires_in", 300))
    token_cache["access_token"] = access_token
    token_cache["expires_at"] = time.time() + max(expires_in - 30, 0)
    return access_token


def fetch_addresses(query: str) -> list[dict]:
    access_token = get_nzpost_token()
    print(f"Using NZ Post token: {access_token[:4]}... (expires at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(token_cache['expires_at']))})")
    headers = {
        "client_id": NZPOST_CLIENT_ID,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if NZPOST_USER_NAME:
        headers["user_name"] = NZPOST_USER_NAME

    try:
        response = requests.get(
            NZPOST_FIND_URL,
            headers=headers,
            params={"address_line_1": query},
            timeout=15,
        )
    except requests.RequestException as error:
        raise HTTPException(status_code=503, detail="Unable to reach NZ Post address service") from error

    print("NZ Post find response object:", response)
    print("NZ Post find request URL:", response.request.url)
    print("NZ Post find response status:", response.status_code)
    print("NZ Post find response headers:", dict(response.headers))
    print("NZ Post find response body:", response.text)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    print("NZ Post find parsed response:", payload)

    if not response.ok:
        raise HTTPException(status_code=503, detail=extract_error_message(payload))

    addresses = payload.get("addresses")
    if isinstance(addresses, list):
        print(f"NZ Post find returned {len(addresses)} addresses")
        return addresses

    return []


@app.post("/login")
def login(payload: LoginRequest):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    if payload.username != APP_USERNAME or payload.password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": get_nzpost_token()}


@app.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme)):
    require_logged_in(credentials)
    clear_cached_token()
    return {"message": "Logged out successfully"}


@app.get("/address-check")
def address_check(
    q: str = Query(...),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
):
    print("Received address check request with query:", q)
    print("Authorization header:", credentials)
    require_logged_in(credentials)

    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Address query is required")

    if "fail" in query.lower():
        raise HTTPException(status_code=503, detail="Address service unavailable")

    addresses = fetch_addresses(query)
    if not addresses:
        return {"status": "invalid", "message": "Address not found"}

    matches = []
    for address in addresses:
        matches.append(
            {
                "full_address": address.get("FullAddress") or query,
                "source": address.get("SourceDesc") or "",
                "dpid": address.get("DPID") or "",
            }
        )

    return {
        "status": "valid",
        "total_matches": len(matches),
        "addresses": matches,
    }
