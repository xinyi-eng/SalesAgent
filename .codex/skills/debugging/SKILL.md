---
name: debugging
description: Diagnose SalesAgent errors, stack traces, failed tests, API failures, and WebSocket or AI-agent regressions; use before editing code to find the root cause and verify a minimal repair.
---

# Debug SalesAgent Failures

Start from observable evidence. Keep the repair narrow; do not refactor unrelated business code while diagnosing.

## Triage

1. Capture the exact error, traceback, request or WebSocket event, environment, and last known good behavior. Redact credentials, tokens, audio, and customer data.
2. Identify the failing file and line, then trace its caller chain. For API behavior include the router, dependency/auth layer, schema, service, and database boundary. For realtime behavior also include connection state, background task, LLM/ASR/TTS adapter, and outbound WebSocket message.
3. State the root-cause hypothesis, supporting evidence, alternatives ruled out, and the smallest safe fix. Do not mistake a downstream exception for its cause.

## Repair and verification

After user authorization to change code, add or update a regression test first when practical. Apply the minimal repair, then run the narrowest relevant check and expand only as needed:

| Changed area | Required verification |
| --- | --- |
| Python module | `cd backend; .\\.venv\\Scripts\\python.exe -m compileall -q app` |
| Existing backend behavior | `cd backend; .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p 'test_*.py' -v` |
| Frontend TypeScript | `cd frontend; npm run build` |

If `.venv` is absent, use an activated environment matching `backend/requirements.txt`. Mock MiniMax, HTTPX, ASR/TTS, embeddings, and network I/O. Never validate a fix with production credentials or real user data.

## Required report

Return: `Symptom`, `Failure location`, `Root cause`, `Fix`, `Verification`, and `Remaining risk`. Mark an unrun command as blocked or failed, never passed.
