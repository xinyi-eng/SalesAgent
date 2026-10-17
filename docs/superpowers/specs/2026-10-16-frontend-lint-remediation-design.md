# Frontend Strict Lint Remediation Design

## Goal

Make `frontend/npm run lint` pass without weakening ESLint rules or changing
the SalesAgent API, authentication, routing, WebSocket, or audio behavior.

The baseline after adding the ESLint configuration is 54 errors and 9 warnings
across 20 source files. The dominant findings are explicit `any` types and
React Hook dependency warnings.

## Scope

Included:

- Replace explicit `any` values with existing API types, narrow local types,
  `unknown`, or `Record<string, unknown>` where the server contract is truly
  open-ended.
- Add a small shared helper for extracting an error message from an `unknown`
  caught value without assuming an Axios response shape.
- Correct Hook dependency arrays using stable callbacks and refs where needed.
- Correct isolated TypeScript and ESLint findings: empty blocks, stale
  suppression comments, unused declarations, and mutable values that can be
  `const`.

Excluded:

- Changes to backend endpoints, request/response shapes, routes, auth rules,
  WebSocket message formats, or the product UI.
- Rule disablements, `eslint-disable` comments, and broad automatic rewrites.
- Introducing a new frontend test framework or dependency.

## Design

### Type boundaries

Existing contracts in `src/api/` remain the source of truth. API methods and
the practice store will use those types for sessions, personas, investigation
results, and user contexts. Values that originate outside a typed contract are
kept as `unknown` until checked; free-form JSON metadata uses
`Record<string, unknown>`.

Caught errors will flow through a shared error-message helper. It will first
recognize a plain `Error`, then a narrow object shape with a string `message`
or `response.data.detail`, and otherwise return the caller-provided fallback.
This removes unsafe property access while preserving current user-visible
error messages.

### React and browser APIs

Hook dependency warnings will be resolved by making callbacks stable with
`useCallback`, listing their actual dependencies, or using refs only where the
callback must read the latest mutable value without retriggering a lifecycle.
No dependency rule will be suppressed.

Audio context fallbacks will use a typed `Window` extension for
`webkitAudioContext`. The VAD browser-option suppression will be replaced by a
documented `@ts-expect-error` only if TypeScript still cannot express the
browser-specific option.

### Safe mechanical corrections

Empty `catch` blocks will contain an explicit ignored-error comment; unused
imports and variables will be removed; and variables never reassigned will be
made `const`. These changes do not alter control flow.

## Implementation Order

1. Add the shared error and JSON utility types; update API/store contracts.
2. Update feature pages and components to consume those types and narrow
   caught errors.
3. Repair audio hooks and Hook dependency warnings after reviewing each
   lifecycle for stale-closure risk.
4. Re-run lint after each group, then run the production build.

## Verification

The project has no frontend test runner, so this work uses static verification:

1. `npm run lint` must finish with zero errors and zero warnings.
2. `npm run build` must pass TypeScript and Vite production build steps.
3. Review the diff to confirm no backend contracts, route paths, or WebSocket
   message shapes changed.

Any runtime behavior uncertainty discovered while correcting Hook dependencies
will stop the remediation and be reported before a behavior-changing edit.
