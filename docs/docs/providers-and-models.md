---
sidebar_position: 4
---

# Providers & Models

LibriScribe speaks to many LLM providers through one unified client, with a configurable
fallback chain for resilience. Configure everything under **Settings**.

## Cloud providers

Supported out of the box: **OpenAI, Claude (Anthropic), Google AI Studio (Gemini), DeepSeek,
Mistral, OpenRouter**. Add an API key for a provider to enable it — providers stay disabled
until a real key is present.

### Live model lists

Instead of memorizing model IDs, click **Load** next to a provider's model field to fetch its
**current available models** directly from the provider's API. Free models (e.g. on OpenRouter)
are flagged and sorted first. This works with a just-typed key before you even save.

## Local / offline LLMs

Point LibriScribe at any **OpenAI-compatible** local server — **LM Studio, Ollama,
llama.cpp, vLLM** — for fully offline, private generation. Under Settings → the
**Local (OpenAI-compatible)** provider:

- Set the **Server Base URL** (presets provided: LM Studio `http://localhost:1234/v1`,
  Ollama `http://localhost:11434/v1`). If you paste a bare `host:port`, `/v1` is appended
  automatically.
- The API key is optional for local servers.
- Click **Load** to list the models your server currently serves.

Requests go only to that address, so nothing leaves your machine. For fully offline use, don't
add cloud providers to this provider's fallback chain.

## Per-project provider & model

The provider/model is chosen **per book** when you create a project, and can be changed later
from the **Automation page → AI configuration**. This lets different books use different
models — for example a local model for private drafts and a frontier cloud model for polish.

## Fallback chain

On recoverable failures (timeouts, rate limits, 5xx, empty/invalid responses), the client can
walk a configurable **fallback chain** and retry on the next route — so a transient provider
problem doesn't stop your run.

## Writing system prompt

A global **Writing System Prompt** (Settings) is injected into creative-writing calls to steer
prose quality (e.g. ASCII-only output, varied sentence structure, avoiding AI-obvious
patterns). Leave it blank to use the built-in default.

## Embeddings

For semantic search you also choose an **embedding source** (OpenAI or a local server) — see
[Semantic Search & Local Embeddings](./semantic-search).
