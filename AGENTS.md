# SalesAgent Agent Guide

## Project map

- `backend/`: FastAPI + SQLAlchemy 2 application. API routers are in `backend/app/api/v1/`; realtime practice traffic is handled by `backend/app/main.py` and `backend/app/websocket/`.
- `frontend/`: React 18 + TypeScript + Vite client.
- `backend/tests/`: offline behavior regressions. Do not require a production database, MiniMax credentials, or live network access.

## Required skills

- Before reviewing Python changes, use `$code-review`.
- When investigating a failure, exception, regression, or log, use `$debugging` before proposing a fix.
- Before adding or substantially changing backend tests, API tests, or Agent-flow tests, use `$test-generation`.

## Guardrails

- Keep business-code changes minimal and scoped to the request. Never place keys, tokens, passwords, or user audio in source, tests, logs, or commits.
- Mock MiniMax, HTTPX, WebSocket, embeddings, ASR/TTS, and other external services in automated tests. Use a temporary SQLite database for persistence tests.
- Preserve the `/api/v1` routing contract and WebSocket message shapes unless the task explicitly changes them.

## Verification

- Backend syntax: `cd backend; .\\.venv\\Scripts\\python.exe -m compileall -q app` (or an activated environment matching `requirements.txt`)
- Backend regression suite: `cd backend; .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p 'test_*.py' -v` (or an activated environment matching `requirements.txt`)
- Frontend: `cd frontend; npm run build`; use `npm run lint` when frontend code is changed.
- If a relevant command cannot run, report the exact blocker and do not claim verification passed.
