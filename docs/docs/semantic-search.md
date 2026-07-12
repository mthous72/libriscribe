---
sidebar_position: 7
---

# Semantic Search & Local Embeddings

LibriScribe retrieves your lore (characters, locations, world entries, prose) to ground
brainstorming and generation. By default it uses **keyword** search. You can optionally turn on
**semantic** or **hybrid** search, which matches by *meaning* rather than exact words — so a
query like "who rules the coastal cities?" can surface the right lore even when it never uses
those exact terms.

Semantic search needs an **embedding model**. You can use a cloud provider (OpenAI) or run
embeddings **fully offline** on a local server (LM Studio or Ollama). Nothing leaves your
machine when you use a local embedding model.

## Search modes

| Mode | What it does | Needs embeddings? |
|------|--------------|-------------------|
| **Keyword** | BM25 / TF-IDF keyword match + cross-references (the default) | No |
| **Semantic** | Cosine similarity over embeddings — matches by meaning | Yes |
| **Hybrid** | Combines keyword and semantic, then re-ranks | Yes |

If semantic/hybrid is selected but no embedding source is configured (or the local server
isn't reachable), search **silently falls back to keyword** — it never breaks.

## Step 1 — Choose an embedding source (Settings)

Go to **Settings → Embeddings (semantic search)** and pick a source:

- **Off** — keyword only.
- **OpenAI (cloud)** — uses your OpenAI API key. Simple, high quality; costs a small amount per
  re-index.
- **Local (OpenAI-compatible server)** — LM Studio / Ollama / llama.cpp. Free and fully
  offline.

Then set the **Embedding model**. Click **Load** to fetch the available models from the source
and pick one from the list — likely embedding models (nomic / bge / e5 / gte / minilm) are
sorted to the top and tagged `— embedding`.

## Step 2a — Local embeddings with LM Studio

1. In LM Studio, open the model search and download a **dedicated embedding model** (they're
   tagged **Embedding**). Recommended:

   | Model | Dims | Notes |
   |-------|------|-------|
   | **nomic-embed-text-v1.5** | 768 | Best default — small, fast, strong quality |
   | bge-small-en-v1.5 | 384 | Fastest / lightest |
   | bge-base / bge-large-en-v1.5 | 768 / 1024 | Higher quality, heavier |
   | e5-base / e5-large-v2 | 768 / 1024 | Solid alternatives |

2. Start LM Studio's **local server** (the same one you use for chat, e.g.
   `http://localhost:1234`). Enable **Just-In-Time (JIT) model loading** in the server settings
   so an embeddings request auto-loads the embedding model. You can keep both a chat model and
   an embedding model available.
3. In LibriScribe **Settings**: set the Local provider **Base URL** (there's an **LM Studio**
   preset button = `http://localhost:1234/v1`), choose **Embeddings → Local**, click **Load**,
   and select your embedding model. **Save**.

:::tip Finding the exact model id
The model id must match what the server exposes. **Load** fetches it for you; if you'd rather
check by hand, open `http://localhost:1234/v1/models` in a browser. LM Studio only lists a model
there once it's **downloaded** (and, on some versions, once loaded) — so if it's missing from
**Load**, download it / enable JIT and try again.
:::

## Step 2b — Local embeddings with Ollama

1. Pull an embedding model:

   ```bash
   ollama pull nomic-embed-text
   ```

2. In LibriScribe **Settings**: use the **Ollama** preset for the Base URL
   (`http://localhost:11434/v1`), choose **Embeddings → Local**, **Load**, and pick
   `nomic-embed-text`. **Save**.

## Step 2c — OpenAI (cloud)

Add your OpenAI API key under **API Configuration**, then **Embeddings → OpenAI**, **Load**, and
choose a model (e.g. `text-embedding-3-small` for a great cost/quality balance, or
`text-embedding-3-large` for higher quality).

## Step 3 — Turn it on per book

Semantic search is chosen **per project**, so different books can use different modes.

1. Open a project's **Automation** page (top-right in the workbench).
2. In **Search (lore retrieval)**, set the mode to **Semantic** or **Hybrid**.
3. Click **Apply & rebuild index** — this embeds the project's lore and prose. Larger projects
   take a little longer the first time.

The card shows live status: whether an embedding source is configured, whether the semantic
index is **ready**, and how many chunks are indexed.

## Gotchas

- **The model id must be exact.** If it's wrong or the model isn't loaded, the embeddings call
  fails and search falls back to keyword. The Automation page will show *"Embeddings configured, but
  the semantic index isn't built"* — re-check the id / that the model is loaded, then **Apply &
  rebuild**.
- **Don't swap embedding models without rebuilding.** Different models produce different vector
  spaces (and dimensions). LibriScribe stores a signature with the index and will ignore a
  mismatched index (falling back to keyword) until you **Apply & rebuild** again.
- **Fully offline:** with a local embedding model, both generation *and* retrieval stay on your
  machine.
