# AI Native QA Demo App

Simple demo app with:
- a plain HTML + vanilla JavaScript frontend
- a Python FastAPI backend
- NZ Post address lookup integration
- API and UI test coverage with `pytest`

## What The App Does

The app lets a user:
1. log in with demo credentials
2. search for an address
3. view matching address results returned by the backend

The backend:
- validates demo login credentials
- requests a real NZ Post access token using environment variables
- calls the NZ Post address lookup API
- returns matching addresses to the frontend

## Project Structure

```text
backend/
  main.py

frontend/
  index.html

tests/
  .env.test
  .env.ui
  api_test/
    test_api.py
  ui_test/
    conftest.py
    test_ui.py

.github/workflows/
  ci.yml
```

## Requirements

- Python 3.11+
- NZ Post credentials
- Playwright browser binaries for UI tests

Install dependencies:

```bash
pip install -r requirements.txt
python -m playwright install
```

## Environment Variables

The backend needs:

```bash
export NZPOST_CLIENT_ID=your_client_id
export NZPOST_CLIENT_SECRET=your_client_secret
```

Optional test values are already stored in:
- [tests/.env.test](tests/.env.test)
- [tests/.env.ui](tests/.env.ui)

## Run Locally

Start the backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

Start the frontend:

```bash
python3 -m http.server 3000 --directory frontend
```

Open:

```text
http://localhost:3000
```

Demo login:

```text
Username: test
Password: test123
```

## Run Tests Locally

API tests:

```bash
pytest tests/api_test/test_api.py
```

UI tests:

```bash
pytest tests/ui_test/test_ui.py
```

If you want to run both app servers and tests together, use:

```bash
./run_local_tests.sh
```

Generated local reports:
- [API report](test-results/api-report.html)
- [UI report](test-results/ui-report.html)

## CI Pipeline

GitHub Actions workflow:
- [.github/workflows/ci.yml](.github/workflows/ci.yml)

The pipeline:
- runs on pushes and pull requests
- starts backend on `127.0.0.1:8000`
- starts frontend on `127.0.0.1:3000`
- runs API tests
- runs UI tests
- publishes JUnit test summaries
- uploads logs and test artifacts

GitHub environment used by CI:
- `ci`

Required GitHub environment secrets:
- `NZPOST_CLIENT_ID`
- `NZPOST_CLIENT_SECRET`

## Test Artifacts

CI uploads:
- API test report
- UI test report
- backend log
- frontend log
- Playwright failure artifacts such as screenshots and page HTML

Generated report files:
- [test-results/api-report.html](test-results/api-report.html)
- [test-results/ui-report.html](test-results/ui-report.html)

## Notes

- The frontend is intentionally simple and framework-free.
- The backend currently logs NZ Post request/response details for debugging.
- The UI tests use Playwright through `pytest-playwright`.
