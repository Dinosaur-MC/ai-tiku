# Query Reliability and Heartbeat Streaming Design

Date: 2026-05-05

## Goal

Improve query reliability and timeout resilience for the main question lookup API.

The system must:
- add limited retries for unstable provider calls
- apply retries only to explicitly allowed transient failures
- keep provider retry logic centralized in `src/utils/llm.py`
- add a dual-mode query interface where `GET /api/v1/query` keeps its current JSON behavior by default
- add an opt-in streaming mode via `stream=true`
- emit heartbeat events every 15 seconds during long-running streamed queries
- emit the final query result as the same complete JSON payload structure currently returned by the non-streaming API

## Scope

In scope:
- retry classification and retry execution for provider-backed LLM calls
- synchronous and asynchronous retry support where needed by the current helper surfaces
- dual-mode handling for `GET /api/v1/query`
- SSE heartbeat streaming for long-running query requests
- documentation updates for the new `stream=true` mode
- focused tests for retry logic and streaming behavior

Out of scope:
- token-by-token answer streaming
- changing the default response shape of `GET /api/v1/query`
- per-request dynamic retry policy overrides
- background task queues or task-id polling workflows
- provider branching in service or agent files
- extending the same heartbeat protocol to unrelated endpoints in this change

## Current State

`GET /api/v1/query` currently returns a single JSON response after the full lookup path completes.

The main flow in `src/routers/api_v1.py` is:
1. validate token
2. search similar questions
3. if no match, call `ai_service.generate_answer(...)`
4. return a `QueryResponse`

The LLM layer in `src/utils/llm.py` now supports multiple providers, but provider invocations do not yet have a unified transient retry mechanism. Long-running requests can also exceed frontend timeout budgets because the route currently stays silent until the final JSON body is ready.

## Design Summary

Use two coordinated changes:

1. **Centralized limited retry in `src/utils/llm.py`**
   - classify retryable vs non-retryable provider failures
   - apply bounded retry with the approved backoff strategy
   - keep this logic below agents and services

2. **Opt-in SSE heartbeat mode in `GET /api/v1/query`**
   - add `stream=true` as a query parameter
   - default behavior remains unchanged JSON
   - streamed mode sends heartbeat events every 15 seconds while work is in progress
   - final SSE event carries the same complete JSON payload structure used by the non-streaming route

This preserves backward compatibility while giving timeout-sensitive clients an explicit long-running mode.

## Retry Policy

### Retry limits

- maximum retries: 10 total attempts
- backoff policy:
  - attempts 1-3: fixed 1 second delay
  - attempts 4-10: exponential backoff

### Retryable failures

Retry only on:
- timeout failures
- connection failures
- HTTP `429`
- HTTP `529`
- HTTP `401`
- HTTP `502`

### Non-retryable failures

Do not retry on:
- HTTP `403`
- HTTP `404`
- HTTP `500`
- parameter/validation errors
- schema/output parsing errors

### Rationale

This policy intentionally treats provider instability as retryable while still failing fast on deterministic request/configuration problems. The unusual inclusion of `401` in retryable failures is taken as a project-specific requirement rather than a generic best practice.

## Retry Architecture

All retry behavior should live in `src/utils/llm.py`.

### New internal responsibilities

`src/utils/llm.py` should gain internal helpers for:
- deciding whether an exception is retryable
- computing the delay for a given attempt number
- executing sync calls with retry
- executing async calls with retry

### Integration points

Wrap provider-backed operations at the LLM abstraction layer rather than in agents:
- chat invoke paths
- completion invoke paths
- embedding request paths if they are used through helper/factory-owned objects

The exact wrapping mechanism can differ by client type, but the policy source of truth must be centralized in `src/utils/llm.py`.

### Boundary rule

Agents and services should continue expressing business intent only:
- `completion.invoke(...)`
- `chat.invoke(...)`
- `embedder...`

They should not know:
- which exceptions are retryable
- how long delays are
- how many attempts remain

## Query Streaming Mode

### Route contract

Enhance `GET /api/v1/query` with a new optional query parameter:
- `stream: bool = False`

Behavior:
- `stream=false` or omitted -> current JSON behavior unchanged
- `stream=true` -> return `text/event-stream`

### Event format

Use SSE events with two event types:

1. **Heartbeat event**

```text
event: heartbeat
data: {}

```

2. **Result event**

```text
event: result
data: <complete JSON response>

```

The `result` payload should be the same full response object the JSON route would have returned, serialized as JSON.

### Heartbeat cadence

- emit heartbeat every 15 seconds while the query is still running
- if the query finishes before the first heartbeat window, send only the final `result`

### Final result shape

The streamed final event must preserve the current `QueryResponse` semantics, including fields such as:
- `code`
- `message`
- `data.question`
- `data.answer`
- `data.times`
- `data.ai`

This avoids forcing business-layer changes in frontend consumers that only need timeout resilience.

## Streaming Execution Model

### Controller behavior in `src/routers/api_v1.py`

For `stream=true`:
- create an async generator for the response body
- run the same query logic used by the non-streaming path
- while the work is incomplete, emit heartbeat events every 15 seconds
- once the result is ready, emit a single `result` event with the complete JSON payload
- then terminate the stream cleanly

### Query logic reuse

Do not duplicate the business decision tree.

The route should reuse a shared internal query execution routine for both modes so the following logic stays consistent:
- title/q/question precedence
- option parsing
- similar-question hit handling
- `force_ai` behavior
- final `QueryResponse` construction
- error handling behavior

If needed, refactor `api_v1.py` so that both the JSON and SSE modes call a shared helper that returns the final response object before transport-specific formatting.

## Error Handling

### Non-streaming mode

Keep current behavior:
- route errors still surface as current HTTP/JSON error responses

### Streaming mode

If an error occurs before the final result is emitted:
- emit a terminal `result` event containing the same error-style payload shape the frontend can parse consistently, if practical
- otherwise close the stream after logging and let the HTTP status reflect failure if headers are not yet committed

The chosen implementation should favor consistency with existing frontend expectations over protocol cleverness.

### Retry exhaustion

If retryable failures persist until the retry budget is exhausted:
- raise the final exception out of the LLM layer
- let the route convert it into the existing error path for non-streaming mode
- in streaming mode, convert it into the terminal failure response for the stream path

## File Changes

### Modify
- `src/utils/llm.py`
  - add retry classification helpers
  - add retry execution helpers
  - route provider-backed operations through retry wrappers
- `src/routers/api_v1.py`
  - add `stream` query parameter
  - add SSE response path
  - share query execution logic across JSON and stream modes
- `src/schemas/v1.py`
  - document the new `stream` request parameter if request models remain relevant to generated docs
- `README.md`
  - document `stream=true`
  - document SSE heartbeat behavior

### Create
- `tests/routers/test_api_v1_query_stream.py`
  - route-level tests for non-streaming vs streaming mode

### Update tests
- `tests/utils/test_llm.py`
  - add retry classification tests
  - add retry scheduling tests
  - add retry exhaustion tests where practical

## Testing Strategy

### LLM retry tests

Add focused unit tests for:
1. retryable exceptions are retried
2. non-retryable exceptions fail immediately
3. attempt count is capped at 10
4. first 3 delays are fixed at 1 second
5. later delays follow exponential growth
6. schema/output parsing errors are not retried
7. HTTP 401 is treated as retryable for this project

These tests should use mocks and avoid real sleeps by patching delay functions.

### Route tests

Add route-level tests for:
1. `GET /api/v1/query` without `stream` still returns current JSON shape
2. `GET /api/v1/query?stream=true` returns an SSE response
3. long-running stream mode emits heartbeat events before completion
4. streamed final `result` event contains complete JSON
5. similar-question hit path still works in both modes
6. `force_ai=true` path still works in both modes
7. failure paths in streamed mode produce a terminal failure outcome rather than hanging silently

### Regression boundary

The existing non-streaming API behavior should be treated as a regression boundary. The new feature is additive, not a contract rewrite.

## Alternatives Considered

### Option 1: Recommended — query parameter + SSE + centralized retry

- `stream=true` enables SSE
- retry logic stays in `src/utils/llm.py`
- result event carries full JSON

Why recommend it:
- backward-compatible
- minimal frontend breakage
- clear layering
- supports timeout-sensitive clients without forcing all clients to migrate

### Option 2: Same route, plain text chunking instead of SSE

Pros:
- simpler transport

Cons:
- less structured
- harder for clients to consume reliably
- weaker event typing than SSE

Not recommended.

### Option 3: Separate streaming endpoint

Pros:
- strongest compatibility isolation

Cons:
- duplicates API surface
- extra documentation and client branching
- unnecessary if query parameter mode is acceptable

Not recommended given the explicit preference for dual-mode compatibility on the main route.

## Risks and Mitigations

### Risk: retry logic amplifies provider load
Mitigation:
- strict retryable error allowlist
- bounded attempts
- deterministic backoff policy

### Risk: heartbeat stream and JSON path diverge
Mitigation:
- shared internal query execution helper
- route tests covering both modes

### Risk: frontends mis-handle SSE final payload
Mitigation:
- use a stable `event: result`
- keep final payload as full JSON response object
- document format clearly in README

### Risk: long-running stream hangs silently on exception
Mitigation:
- explicitly test streamed failure termination behavior
- ensure exceptions become a terminal outcome, not an abandoned connection

## Success Criteria

The change is successful when:
- provider-backed LLM calls retry only within the approved limits and error classes
- `GET /api/v1/query` remains backward-compatible by default
- `GET /api/v1/query?stream=true` emits heartbeat events every 15 seconds while work is pending
- the stream ends with one full JSON result event
- timeout-sensitive frontends can keep the connection alive beyond 3 minutes
- tests cover retry policy and dual-mode route behavior without relying on real provider calls
