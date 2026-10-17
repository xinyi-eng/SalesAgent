---
name: test-generation
description: Generate focused pytest-style tests for SalesAgent FastAPI APIs, agent and WebSocket flows, and error handling; use when adding coverage or protecting a bug fix without calling external AI services.
---

# Generate SalesAgent Tests

Generate tests that prove observable behavior and safely isolate external systems. Match the surrounding test style: this repository currently uses `unittest`, so pytest-style tests may be added only when pytest is available or explicitly introduced; otherwise use `unittest` equivalents without adding a dependency silently.

## Select the smallest useful test layer

| Target | Preferred scope |
| --- | --- |
| Pure utility, security, schema, or state rule | Unit test |
| FastAPI route and auth/validation contract | API test with dependency overrides and temporary SQLite |
| Conversation or voice lifecycle | Service/handler test with mocked MiniMax, ASR/TTS, HTTPX, and WebSocket manager |
| Failure, timeout, malformed input, or closed connection | Deterministic exception-path test |

## Required coverage

1. Cover one successful outcome, relevant authorization/input validation, and the important failure path.
2. For API tests, assert status code and stable response fields; do not assert volatile wording from an LLM.
3. For Agent flows, assert state transitions, one outbound message per input, cleanup/cancellation, and no external call when validation fails.
4. Mock all networked AI, vector, audio, and search services. Use `tmp_path`/temporary files and a temporary SQLite database; never touch `backend/salesagent.db`.

## Delivery and validation

State test placement, fixtures/mocks, and exact assertions before writing. Run the targeted test, then `cd backend; .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -p 'test_*.py' -v` when tests are runnable. If pytest is intentionally added, document its dependency and run it through the same environment explicitly.

## Avoid

- Live MiniMax calls, real API keys, sleeps, production databases, or assertions on model prose.
- Tests coupled to private implementation details when public behavior can be asserted.
