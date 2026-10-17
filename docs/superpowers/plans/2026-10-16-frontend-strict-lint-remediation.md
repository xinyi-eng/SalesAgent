# Frontend Strict Lint Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `npm run lint` pass with zero errors and warnings while preserving SalesAgent frontend behavior and contracts.

**Architecture:** Keep API interfaces as the type boundary, add one shared unknown-error parser, and replace local escape hatches with narrow types. Correct React Hook lifecycles through stable callback dependencies or refs; do not silence lint rules.

**Tech Stack:** React 18, TypeScript 5, Vite 5, ESLint 8, Axios, Zustand.

**Spec:** `docs/superpowers/specs/2026-10-16-frontend-lint-remediation-design.md`

## Global Constraints

- Do not weaken ESLint rules, add `eslint-disable` comments, or use `any` as a replacement for a missing type.
- Do not change backend API contracts, routes, authentication, WebSocket message formats, audio behavior, or product UI.
- Do not add dependencies or a frontend test framework.
- Preserve user-facing fallback messages while making caught errors type-safe.

## Review Focus

- Axios-like errors with a string `response.data.detail` must preserve the existing displayed error message.
- Non-Error throw values must fall back safely instead of causing a second error while rendering an error state.
- `useEffect` and `useCallback` dependency fixes must not cause repeated API calls, reconnect loops, or stale state.
- Browser audio-context fallbacks must still support both standard `AudioContext` and `webkitAudioContext`.
- Open-ended API metadata must remain JSON-compatible without permitting unsafe property access.

---

## File Structure

- Create `frontend/src/utils/errorMessage.ts`: narrow unknown caught values into stable display messages.
- Modify `frontend/src/api/knowledge.ts` and `frontend/src/api/practice.ts`: expose accurate JSON and session-context types.
- Modify `frontend/src/stores/practiceStore.ts`: consume typed practice and SPIN context values.
- Modify feature pages under `frontend/src/pages/`: use declared API types and `getErrorMessage`.
- Modify `frontend/src/hooks/`: type browser audio APIs and correct Hook lifecycles.
- Modify `frontend/src/contexts/AuthContext.tsx` and `frontend/src/components/common/Navigation.tsx`: remove unsafe casts and empty blocks.

### Task 1: Establish safe frontend type boundaries

**Files:**
- Create: `frontend/src/utils/errorMessage.ts`
- Modify: `frontend/src/api/knowledge.ts:23-29`
- Modify: `frontend/src/api/practice.ts:138-142,220-223`
- Modify: `frontend/src/stores/practiceStore.ts:1-80,147-180`

**Interfaces:**
- Produces `getErrorMessage(error: unknown, fallback: string): string`.
- Produces `JsonObject = Record<string, unknown>` and named types for practice session details and optional SPIN context.
- Consumes existing `CustomerContext`, `InvestigationResult`, `UserContext`, `RoleConfig`, and `SessionCreateResponse` exports.

- [x] **Step 1: Add the failing type-check examples to the task notes**

Record the current lint findings for explicit `any` in the listed files and the intended replacement types. The failure is the baseline `npm run lint` output containing these rule violations.

- [x] **Step 2: Run the baseline lint check**

Run: `cd frontend; npm run lint`

Expected: FAIL with explicit-`any` findings in `knowledge.ts`, `practice.ts`, and `practiceStore.ts`.

- [x] **Step 3: Implement `getErrorMessage(error: unknown, fallback: string): string` and typed API boundaries**

Use type guards for `Error`, `{ message: string }`, and `{ response: { data: { detail: string } } }`. Export `JsonObject` for unconstrained metadata; use named optional context interfaces rather than `any` in session creation and Zustand state.

- [x] **Step 4: Run focused static verification**

Run: `cd frontend; npm run lint -- --quiet`

Expected: the named files no longer emit explicit-`any` errors.

- [x] **Step 5: Commit the type-boundary task**

```bash
git add frontend/src/utils/errorMessage.ts frontend/src/api/knowledge.ts frontend/src/api/practice.ts frontend/src/stores/practiceStore.ts
git commit -m "refactor: tighten frontend API types"
```

### Task 2: Type feature-page data and error paths

**Files:**
- Modify: `frontend/src/pages/Dashboard/DashboardPage.tsx`
- Modify: `frontend/src/pages/Knowledge/KnowledgeBasePage.tsx`
- Modify: `frontend/src/pages/Briefs/BriefDetailPage.tsx`
- Modify: `frontend/src/pages/Briefs/BriefListPage.tsx`
- Modify: `frontend/src/pages/Practice/PracticePage.tsx`
- Modify: `frontend/src/pages/Practice/PracticeChatPage.tsx`
- Modify: `frontend/src/pages/Practice/PracticeReviewPage.tsx`
- Modify: `frontend/src/pages/Practice/ReportPage.tsx`
- Modify: `frontend/src/pages/User/ProfilePage.tsx`
- Modify: `frontend/src/pages/User/HistoryPage.tsx`
- Modify: `frontend/src/pages/User/SettingsPage.tsx`

**Interfaces:**
- Consumes `getErrorMessage` from Task 1 and existing API response interfaces.
- Produces typed component state and typed request parameters with unchanged rendered fallbacks.

- [x] **Step 1: Record each page's current lint violation and rendered fallback text**

The reference is the baseline lint report and the current page source. Ensure every `catch` fallback string remains unchanged after its type is narrowed.

- [x] **Step 2: Confirm the focused baseline fails**

Run: `cd frontend; npm run lint -- --quiet`

Expected: FAIL with explicit-`any` errors in the listed feature pages.

- [x] **Step 3: Replace page-local `any` values with API interfaces and `unknown` error handling**

Use existing page/API types where contracts exist. For truly dynamic maps, use a declared `Record<string, number | string | null>`-style shape that matches the rendered property access. Route caught values through `getErrorMessage`; do not cast an error to Axios types.

- [x] **Step 4: Correct page Hook dependencies without changing fetch timing**

Wrap loaders in `useCallback` where an effect invokes them, then list the callback in the effect dependency array. Do not add state values that would cause a loader to refire after it updates that state.

- [x] **Step 5: Run focused static verification**

Run: `cd frontend; npm run lint -- --quiet`

Expected: the listed pages no longer emit errors or Hook warnings.

- [x] **Step 6: Commit the page task**

```bash
git add frontend/src/pages
git commit -m "refactor: type frontend page error paths"
```

### Task 3: Repair navigation, auth, and realtime audio Hook lint findings

**Files:**
- Modify: `frontend/src/components/common/Navigation.tsx`
- Modify: `frontend/src/contexts/AuthContext.tsx`
- Modify: `frontend/src/hooks/useAudioRecorder.ts`
- Modify: `frontend/src/hooks/useAudioStream.ts`
- Modify: `frontend/src/hooks/useVAD.ts`
- Modify: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/components/business/practice/ChatContainer.tsx`

**Interfaces:**
- Consumes `getErrorMessage` from Task 1 where an error message is rendered.
- Preserves the public return types of all hooks and existing navigation/auth APIs.

- [x] **Step 1: Record lifecycle-sensitive baselines**

For each Hook dependency warning, note whether the callback performs connection, recording, VAD, audio playback, or authentication work. The baseline lint output must show the current warning before changing that Hook.

- [x] **Step 2: Resolve non-lifecycle TypeScript and ESLint violations**

Remove unused declarations, type `webkitAudioContext` through a narrow `Window` extension, replace `@ts-ignore` with a justified `@ts-expect-error` only when necessary, make non-reassigned variables `const`, and make ignored catches explicit.

- [x] **Step 3: Resolve Hook dependencies with stable semantics**

Use `useCallback` for loader/connection functions used by effects. Use refs only when a dependency must remain current without restarting an audio or WebSocket lifecycle. Re-check cleanup behavior after each change; never silence `exhaustive-deps`.

- [x] **Step 4: Run focused static verification**

Run: `cd frontend; npm run lint -- --quiet`

Expected: no findings in the listed components, context, or hooks.

- [x] **Step 5: Commit the realtime Hook task**

```bash
git add frontend/src/components/common/Navigation.tsx frontend/src/contexts/AuthContext.tsx frontend/src/hooks frontend/src/components/business/practice/ChatContainer.tsx
git commit -m "refactor: tighten realtime hook safety"
```

### Task 4: Verify strict lint and production build

**Files:**
- Verify: `frontend/.eslintrc.cjs`
- Verify: all changed frontend source files

**Interfaces:**
- Consumes the completed type, page, and Hook changes from Tasks 1-3.
- Produces a zero-finding lint baseline and a production Vite build.

- [x] **Step 1: Run strict lint**

Run: `cd frontend; npm run lint`

Expected: PASS with zero errors and zero warnings.

- [x] **Step 2: Run the production build**

Run: `cd frontend; npm run build`

Expected: PASS after TypeScript checks and Vite emits route-split assets.

- [x] **Step 3: Review the final diff for contract safety**

Run: `git diff --check` and inspect changed API, routing, WebSocket, and audio call sites.

Expected: no backend contract, route-path, WebSocket shape, or UI copy changes outside type-safe error handling.

- [x] **Step 4: Commit verification-ready implementation**

```bash
git add frontend
git commit -m "chore: pass strict frontend lint"
```

> Implementation note: the existing index contained unrelated CI, audio, database, and lock-file changes, so the frontend remediation was committed in scoped path sets instead of staging the entire `frontend/` tree.
