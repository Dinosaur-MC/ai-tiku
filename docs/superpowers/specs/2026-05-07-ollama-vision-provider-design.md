# Ollama Vision Provider Design

Date: 2026-05-07

## Goal

Extend the existing vision capability so `VISION_PROVIDER` supports both `openai_compatible` and `ollama` while keeping the current `VISION_*` environment variable names unchanged.

The system must:
- preserve the existing `VISION_*` configuration surface
- keep current `VISION_PROVIDER=openai_compatible` behavior working
- add `VISION_PROVIDER=ollama`
- keep the upper-layer API unchanged as `analyze_images(prompt, image_urls)`
- support Ollama vision through either direct URL image input or downloaded-and-encoded image input, depending on the underlying client path
- keep business-layer callers unaware of provider-specific multimodal input differences

## Scope

In scope:
- `src/utils/llm.py` vision configuration and adapter design
- Ollama vision adapter behavior
- image input preparation for Ollama vision requests
- focused tests for vision config parsing and provider-specific adapter behavior
- regression checks for the existing image-backed query flow

Out of scope:
- renaming `VISION_*` environment variables
- changing the `AIService` or `option_images` public calling surface for vision
- adding new unrelated providers beyond `openai_compatible` and `ollama`
- broad refactors of chat/completion/embedding config beyond what is needed to make vision provider handling consistent

## Current State

The current implementation already has a dedicated `VisionConfig` in `src/utils/llm.py`, but it is hard-coded to:
- `provider = openai_compatible`
- a single `OpenAICompatibleVisionAdapter`
- a single request-shape assumption based on OpenAI-style multimodal message blocks

Upper layers currently call a unified helper:
- `analyze_images(prompt, image_urls)`

That helper is already used by:
- `src/services/ai_service.py` for option-image summarization and the on-demand image tool

This means the business layer is already correctly abstracted, but the provider layer is not yet general enough to support Ollama vision.

## Design Summary

Adopt a provider-general vision abstraction with a stable top-level entrypoint.

1. Keep the current `VISION_*` env names unchanged.
2. Expand `VisionConfig.provider` to support both:
   - `openai_compatible`
   - `ollama`
3. Make `build_vision_model()` return a provider-specific adapter.
4. Keep `analyze_images(prompt, image_urls)` unchanged so higher layers do not need to branch on provider.
5. For Ollama, support two internal image input strategies:
   - direct URL input when the active client path supports it
   - downloaded-and-encoded input as a fallback or compatibility path

This gives users a compatible migration path while keeping the business layer isolated from provider differences.

## Configuration Strategy

### Compatibility rule

Preserve the existing env names:
- `VISION_PROVIDER`
- `VISION_MODEL`
- `VISION_BASE_URL`
- `VISION_API_KEY`
- `VISION_TEMPERATURE`

### Provider behavior

#### `VISION_PROVIDER=openai_compatible`

Behavior remains unchanged:
- require `VISION_MODEL`
- require `VISION_BASE_URL`
- require `VISION_API_KEY`
- build the OpenAI-style vision adapter

#### `VISION_PROVIDER=ollama`

Behavior:
- require `VISION_MODEL`
- `VISION_BASE_URL` remains optional, consistent with existing Ollama patterns elsewhere in the repo
- do not require `VISION_API_KEY`
- build an Ollama-specific vision adapter

### Why preserve env names

The user explicitly chose compatibility. Existing setups that already use `VISION_*` should continue working without renaming or migration steps.

## Vision Abstraction

### Config model

`VisionConfig` should become a provider-general config model rather than a single-provider special case.

It should answer the same kinds of questions that `ChatConfig` and `CompletionConfig` already answer:
- which provider
- which model
- where the provider endpoint lives
- whether credentials are needed
- what temperature to use

### Adapter boundary

The business-layer contract should remain:
- input: `prompt: str`, `image_urls: list[str]`
- output: `str`

Provider-specific differences must stay inside adapter implementations.

Recommended adapters:
- `OpenAICompatibleVisionAdapter`
- `OllamaVisionAdapter`

### Shared helper surface

The public helper remains:
- `vision_enabled()`
- `analyze_images(prompt, image_urls)`

This keeps `src/services/ai_service.py` and any future multimodal callers free of provider branching.

## Ollama Vision Input Strategy

The two referenced docs imply slightly different low-level paths:
- Ollama docs say Python SDK can accept file paths, URLs, or raw bytes in image input lists
- LangChain Ollama docs show a base64-oriented multimodal binding pattern

That means the backend should not assume a single universal image input format for Ollama.

### Internal preparation layer

Add an internal image-input preparation step for Ollama that can choose between:

1. **URL pass-through**
   - use the original image URL directly when the current client surface supports it

2. **Downloaded-and-encoded input**
   - download the image bytes
   - convert to the format expected by the chosen Ollama client path
   - pass the prepared image payload into the request

This selection should be invisible to callers.

### Recommended decision rule

Prefer:
1. URL pass-through when the chosen adapter/client path can safely consume it
2. downloaded-and-encoded fallback when URL pass-through is unsupported or incompatible with the current integration surface

This preserves flexibility without exposing the difference above the adapter boundary.

## Image Preparation Helper

A small internal helper should own Ollama-specific input preparation.

Responsibilities:
- accept one or more remote image URLs
- fetch image bytes when needed
- produce provider-ready image inputs for Ollama
- fail with clear provider-layer exceptions when an image cannot be prepared

This helper belongs below the service layer and above the raw model invocation.

## Error Handling

### Configuration errors

Fail fast at config load time when required values are missing for the chosen provider.

Examples:
- `VISION_PROVIDER=openai_compatible` without `VISION_API_KEY` should still raise
- `VISION_PROVIDER=ollama` without `VISION_MODEL` should raise

### Runtime image preparation errors

Provider/runtime failures from `analyze_images(...)` should keep current higher-level semantics:
- the adapter raises
- upper layers such as `AIService` continue applying their existing graceful fallback behavior

This is important because the current business-layer fallback logic is already correct and should not be duplicated in `llm.py`.

## File-Level Changes

### `src/utils/llm.py`

This is the primary file to modify.

Changes:
- make `VisionConfig.provider` support both `openai_compatible` and `ollama`
- update optional vision config parsing to validate provider-specific requirements
- add `OllamaVisionAdapter`
- update `build_vision_model()` to dispatch by provider
- add internal Ollama image preparation helpers
- keep `vision_enabled()` and `analyze_images(...)` stable

### `.env.example`

Document:
- `VISION_PROVIDER=ollama` as a supported value
- `VISION_API_KEY` is not required for Ollama
- `VISION_BASE_URL` is optional for Ollama, consistent with other Ollama config in the repo

### `tests/utils/test_llm.py`

Extend current vision tests to cover:
- valid `VISION_PROVIDER=ollama` config loading
- Ollama not requiring `VISION_API_KEY`
- provider-specific config validation differences between `openai_compatible` and `ollama`
- provider-specific adapter request preparation
- stable `analyze_images(...)` behavior across providers

## Testing

### Config tests

Add tests for:
- `VISION_PROVIDER=ollama` with `VISION_MODEL` loads successfully
- `VISION_PROVIDER=ollama` does not require `VISION_API_KEY`
- `VISION_PROVIDER=ollama` can omit `VISION_BASE_URL`
- `VISION_PROVIDER=ollama` still rejects missing `VISION_MODEL`
- `VISION_PROVIDER=openai_compatible` regression behavior remains intact

### Adapter tests

Add focused tests for:
- OpenAI-compatible vision request shape remains unchanged
- Ollama adapter can produce a provider-ready request from raw URLs or prepared image payloads
- the top-level `analyze_images(...)` helper continues returning plain text

### Regression tests

Keep the existing image-backed query tests green so the following remain true:
- image-backed `/api/v1/query` flow still works with `VISION_PROVIDER=openai_compatible`
- the same upper-layer flow can run with `VISION_PROVIDER=ollama` without caller-side API changes

## Alternatives Considered

### Option 1: Ollama-only special case in the current vision code

Pros:
- smallest patch
- fastest implementation

Cons:
- keeps vision as a one-off branch instead of a provider-general capability
- becomes harder to extend later

### Option 2: Provider-general vision config with provider-specific adapters

Pros:
- aligns vision with the existing provider-based design direction
- keeps upper-layer multimodal callers unchanged
- cleanest long-term structure

Cons:
- larger change to `src/utils/llm.py` than a one-off patch

### Option 3: General vision config plus separate input-preparation layer

Pros:
- best separation between provider invocation and image payload preparation
- especially useful because Ollama input paths vary between URL/raw-bytes/base64-oriented client patterns

Cons:
- introduces one more internal concept

## Recommendation

Implement Option 2 with Option 3’s internal image-preparation split.

That means:
- preserve current `VISION_*` env names
- expand vision to a provider-general config model
- add `ollama` support in `VisionConfig` and `build_vision_model()`
- keep `analyze_images(prompt, image_urls)` unchanged for higher layers
- hide Ollama URL-vs-encoded image handling inside the adapter stack

## Acceptance Criteria

The change is complete when:
- `VISION_PROVIDER=ollama` is accepted by config parsing
- current `VISION_PROVIDER=openai_compatible` behavior still works
- `VISION_PROVIDER=ollama` does not require `VISION_API_KEY`
- `analyze_images(prompt, image_urls)` keeps the same caller-facing API
- `AIService` and option-image logic do not need provider-specific branching
- Ollama vision requests can use either direct URL input or downloaded-and-encoded image input internally, depending on adapter compatibility
- focused config and adapter tests pass for both providers
