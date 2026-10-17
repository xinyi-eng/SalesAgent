---
name: code-review
description: Review SalesAgent Python changes for correctness, security, FastAPI and SQLAlchemy risks, and AI-agent or WebSocket flow defects; use for pull requests, diffs, or code-review requests.
---

# Review SalesAgent Python Code

Review the supplied diff first; inspect adjacent code only when needed to establish behavior. Do not modify code unless the user explicitly asks for a fix.

## SalesAgent focus

- FastAPI routes must preserve `/api/v1` contracts, validate untrusted input with Pydantic, enforce the appropriate auth dependency, and avoid leaking internals in errors.
- SQLAlchemy work must close or roll back sessions reliably; SQLite access must not be held across slow external calls.
- Treat MiniMax credentials, JWT secrets, uploads, audio payloads, retrieved documents, and LLM output as untrusted. Flag secrets, permissive CORS/auth changes, unsafe file paths, SSRF-capable URLs, prompt-injection paths, and logging of sensitive content.
- For Agent and voice flows, trace state transitions through route/handler, conversation service, LLM/ASR/TTS call, persistence, and WebSocket send. Flag missing cancellation, duplicate sends, blocked event loops, retries without bounds, and failures that leave the client in a processing state.

## Method

1. Establish the changed behavior and its callers.
2. Check Python correctness and local conventions: imports, async/await, exception paths, resource cleanup, types, input validation, and tests.
3. Review security and Agent-flow invariants above.
4. Return findings only; list the most severe first. Omit praise and speculative nits.

## Required output

For each finding use: `SEVERITY | path:line | problem | impact | concrete fix`.

Use `Critical`, `High`, `Medium`, or `Low`. End with `Residual risks` and `Verification gaps`; say `None identified` only after checking.

## Common mistakes

- Do not report an issue without a reproducible path or a clear invariant it violates.
- Do not call a stylistic preference a bug.
- Do not recommend live MiniMax calls as test verification.
