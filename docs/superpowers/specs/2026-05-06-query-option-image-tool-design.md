# Query Option Image Tool Design

Date: 2026-05-06

## Goal

Improve `GET /api/v1/query` so it can handle question options that contain image links.

The system must:
- keep the existing `/api/v1/query` response contract unchanged
- apply the feature only to `GET /api/v1/query`
- extract and normalize image URLs from option text before LLM answering
- support duplicated or concatenated image URLs inside a single option string
- use an optional, separately configured multimodal model for option-image understanding
- inject baseline image understanding into the query context before answering
- preserve an on-demand image-analysis tool for the answering agent when baseline parsing is insufficient
- degrade gracefully when image download or multimodal parsing fails

## Scope

In scope:
- option preprocessing for `GET /api/v1/query`
- image URL extraction and deduplication from raw option text
- optional image download and baseline multimodal parsing
- agent-side on-demand image analysis for option images
- separate optional vision-model configuration in `src/utils/llm.py`
- focused tests for normalization, fallback behavior, and query-path routing

Out of scope:
- changes to `/api/v2/*` classification endpoints
- changing the default HTTP method, route path, or response schema of `/api/v1/query`
- general multimodal support across unrelated agents
- storing downloaded images permanently
- frontend changes or new client-side API parameters for this feature

## Current State

`GET /api/v1/query` in `src/routers/api_v1.py` currently:
1. resolves `title` / `q` / `question`
2. splits `options` by newline into `options_list`
3. tries vector similarity search unless `force_ai=true`
4. falls back to `ai_service.generate_answer(...)`
5. returns the usual `QueryResponse`

The query agent in `src/agents/query.py` receives `title`, `options`, and `question_type`, then performs type detection and answer generation via `completion.invoke(...)`.

This flow assumes option content is already plain text. It does not currently:
- detect image URLs inside options
- normalize malformed repeated URL strings
- call a multimodal model
- expose any image-analysis tool to the answering path

## Design Summary

Use a two-layer image-understanding path inside the existing `/api/v1/query` flow:

1. **Preprocess options before answering**
   - parse each option string
   - extract option label, residual text, and image URLs
   - normalize repeated or concatenated URLs
   - optionally run baseline multimodal analysis for extracted images
   - build enhanced option text that is still consumable by the current prompt-based answering flow

2. **Allow the answering path to inspect images on demand**
   - expose a read-only tool for per-image analysis
   - use it only when image-backed options exist and the baseline parse is not enough
   - keep tool failures non-fatal to the request

This keeps the normal path text-first, minimizes changes to route behavior, and adds multimodal capability only where it helps.

## Input Normalization

### Raw input shape

Some callers send option strings like this pattern:
- a label such as `A.`
- one or more image URLs
- duplicated copies of the same URL stuck together without separators
- inconsistent whitespace or `+`-decoded spacing artifacts

The design must tolerate this malformed-but-observed input format.

### Normalization responsibilities

Add an option-image preprocessing helper that transforms each raw option into a structured representation with:
- `label`: option label such as `A`, `B`, `C`, `D` when present
- `raw_text`: original option string after outer whitespace cleanup
- `plain_text`: non-URL text content remaining in the option
- `image_urls`: normalized unique image URLs in stable order
- `vision_summaries`: zero or more baseline multimodal summaries
- `parse_warnings`: non-fatal issues seen during extraction or image processing

### URL extraction rules

The helper should:
- detect HTTPS image URLs inside option text
- recover repeated URLs even when the same URL is concatenated back-to-back
- deduplicate identical URLs within the same option while preserving first-seen order
- leave unrelated non-URL text untouched

A practical normalization rule is:
- scan for URL-shaped substrings beginning with `https://`
- stop matches at known image suffix boundaries when possible, including `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`
- if the same exact URL repeats contiguously, collapse it to one instance in the normalized output

The implementation does not need to solve arbitrary malformed URLs. It only needs to robustly handle the observed provider format and similar variants.

## Vision Configuration

### Separate optional model config

Add a dedicated optional vision capability in `src/utils/llm.py`.

Suggested environment variables:
- `VISION_PROVIDER`
- `VISION_MODEL`
- `VISION_BASE_URL`
- `VISION_API_KEY`
- `VISION_TEMPERATURE` if needed by the chosen client surface

Behavior:
- if no valid vision config is present, option-image parsing is not activated
- the request continues through the existing text-only answer flow
- extracted URLs may still be preserved as plain references in enhanced option text if useful

### Provider rule

This design only requires a separate optional vision configuration surface. It does not require vision to share the same provider as `chat` or `completion`.

## Preprocessing Flow

### Route boundary

Keep `src/routers/api_v1.py` thin.

The route should continue to:
- resolve the query text
- split incoming `options` into a list
- call service-layer orchestration
- build the same `QueryResponse`

The route should not own image downloading, multimodal parsing, or tool wiring.

### Service orchestration

`src/services/ai_service.py` should orchestrate the image-aware answer path for `/api/v1/query`.

Suggested sequence:
1. receive `title`, `options_list`, and `question_type`
2. preprocess options into structured option-image data
3. build enhanced option strings from the structured data
4. decide whether to use plain answer generation or the image-tool-capable answer path
5. return the final answer text to the route

### Enhanced option text

For each option, produce a stable text form that can be inserted into the prompt.

Example shape:

```text
A. [图片选项]
原始文本：<plain text if any>
图片1解析：<baseline summary>
图片URL：<url>
```

Rules:
- include the option label if available
- include residual plain text when present
- include baseline vision summaries when available
- include source URLs when parsing succeeded but vision is unavailable or failed
- keep wording compact so prompts do not bloat unnecessarily

This lets the existing answering path benefit from image understanding even if no tool call happens later.

## On-Demand Image Analysis Tool

## Purpose

Baseline summaries may be too shallow for some image-based options. The answering path therefore needs a way to inspect an option image again on demand.

## Tool contract

Expose a read-only tool with a narrow surface, such as:
- `analyze_option_image(option_label: str, image_url: str) -> str`

The tool should:
- download the target image
- call the configured vision model
- return a concise structured textual description focused on question answering
- never mutate application state

Suggested output style:
- what the image contains
- any text, symbols, formulas, or diagrams visible in the image
- the likely semantic meaning of the option relative to the question

## Failure behavior

Tool failures must be non-fatal.

If the tool cannot finish, it should return a readable failure result such as:
- image download failed
- vision model unavailable
- image could not be parsed

The main query request must continue.

## Query-Agent Integration

### Default behavior

Keep the existing text-oriented answer path as the default because it is lower risk and already matches the current prompt design.

### Conditional tool path

When both of the following are true:
- at least one normalized option contains image URLs
- vision capability is configured or image-tool usage is otherwise meaningful

then the answering flow may use a tool-capable branch for answer generation.

The branch should still reuse the current query-agent logic for:
- question-type detection
- answer generation intent
- format correction
- final output checks

### Boundary rule

Do not force the entire query stack to become a general-purpose tool-calling agent.

The preferred architecture is:
- keep preprocessing as the primary source of image understanding
- use tool calling only as a targeted extension for image-backed options
- avoid changing unrelated query cases

## Error Handling and Fallbacks

### Approved fallback behavior

If image download fails or multimodal analysis fails:
- do not fail `/api/v1/query`
- preserve whatever text and URLs were successfully extracted
- continue with answer generation
- emit logs for diagnosis

### Fallback levels

Use the following degradation order:
1. baseline vision summary + optional tool access
2. URL-preserved enhanced option text without baseline summary
3. plain option text only

At no point should an option-image failure become a hard error for the whole query request.

## Logging

Add focused logs for:
- option image URLs extracted
- deduplication applied to malformed repeated URLs
- image download failures
- baseline vision parse failures
- on-demand tool invocation and failure

Logs should help diagnose provider behavior without dumping excessive image content into logs.

## File-Level Changes

### `src/routers/api_v1.py`
- keep the route contract unchanged
- continue initial option splitting
- delegate image-aware answer orchestration through the service layer
- avoid embedding image-processing logic directly in the route

### `src/services/ai_service.py`
- add orchestration for option preprocessing and image-aware answer selection
- decide whether the request stays on the plain path or uses the image-tool-capable path

### `src/agents/query.py`
- add or adapt an answer path that can use the option-image tool when needed
- reuse existing type-detection, answer, and correction logic where possible

### `src/utils/llm.py`
- add optional vision configuration parsing
- add a vision client/helper surface suitable for baseline parsing and tool use
- keep provider-specific config rules centralized here

### `src/utils/option_images.py`
- new helper module for option parsing, URL extraction, deduplication, image download, and baseline image summarization

A separate helper module is preferable to expanding `api_v1.py` or `query.py` with parsing and HTTP concerns.

## Testing

### Normalization tests

Add focused tests for:
- extracting one image URL from a normal option string
- collapsing the same concatenated URL repeated multiple times
- preserving non-URL option text alongside extracted URLs
- handling options with no image URLs

### Fallback tests

Add tests for:
- image download failure still allowing answer generation
- baseline vision parse failure still allowing answer generation
- missing vision configuration skipping baseline image parsing cleanly

### Routing/orchestration tests

Add tests for:
- `/api/v1/query` with image-backed options taking the preprocessing path
- non-image options staying on the normal path
- requests still returning the existing `QueryResponse` structure

### Tool tests

Add tests for:
- the on-demand image tool returning structured text on success
- the tool returning readable failure text instead of raising fatal request errors

## Alternatives Considered

### Option 1: Recommended — preprocess first, tool second

Pros:
- works with the current prompt-oriented answer flow
- gives the model useful image context immediately
- limits tool-calling complexity to image-backed cases
- best matches the requested behavior

Cons:
- requires both preprocessing and a narrow tool path
- slightly more moving parts than a pure text injection design

### Option 2: Preprocess only

Pros:
- simplest implementation
- easiest to test
- smallest behavioral change in the answer path

Cons:
- no way to re-inspect an image if the first summary is insufficient

### Option 3: Tool only

Pros:
- defers multimodal cost until the model truly needs it
- conceptually clean for agent-driven image inspection

Cons:
- requires a larger change from plain `completion.invoke(...)` semantics
- more invasive for the current query architecture
- weaker default context for image-backed options

## Recommendation

Implement Option 1.

It satisfies the requested behavior:
- light preprocessing first
- extracted image URLs normalized and deduplicated
- baseline multimodal understanding injected into the prompt
- on-demand agent tool retained as a fallback
- failures degrade gracefully without breaking `/api/v1/query`

## Acceptance Criteria

The change is complete when:
- `/api/v1/query` can accept options containing duplicated or concatenated image URLs
- image URLs are extracted and normalized per option
- a separately configured optional vision model can produce baseline summaries
- the answering path can inspect option images on demand through a narrow tool
- image-processing failures do not fail the whole request
- `/api/v1/query` keeps its current response shape and default behavior for non-image inputs
- `/api/v2/*` behavior remains unchanged
