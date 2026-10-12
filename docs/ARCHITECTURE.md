# Architecture

DocuMind is a two-phase RAG system: an **ingestion pipeline** that turns PDFs into
searchable vectors, and a **conversational query pipeline** that answers questions
grounded in those vectors.

## 1. Layered design

```mermaid
flowchart TB
    UI["Presentation — app.py, ui/<br/>app shell · views · design system · dialogs"]
    APP["Application — pipeline.py · activity.py<br/>RAGPipeline: ingest_pdf · condense · retrieve · ask_stream"]
    DOM["Domain — schemas.py · prompts.py · memory.py"]
    INF["Infrastructure — ingestion/ · embeddings.py · vectorstore.py · llm.py"]
    CFG["config.py — env-driven Settings"]
    UI --> APP --> DOM
    APP --> INF
    CFG -.-> APP & INF
```

| Layer | Responsibility | Depends on Streamlit? |
|---|---|---|
| Presentation | Navigation, pages, design system, dialogs, session state | Yes |
| Application | Orchestrates the RAG flow; returns typed results | No |
| Domain | Data objects, prompts, memory | No |
| Infrastructure | PDF parsing, embeddings, ChromaDB, LLM providers | No |

Keeping Streamlit out of everything below the presentation layer means the pipeline is
unit-testable with fakes and can be put behind FastAPI or a CLI without changes.

## 2. Ingestion pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit
    participant P as RAGPipeline
    participant L as loader.py
    participant C as chunker.py
    participant V as ChromaDB
    U->>UI: upload PDFs, click "Index"
    loop each file
        UI->>P: ingest_pdf(bytes, name)
        P->>P: size check, SHA-256
        P->>V: has_file(hash)?
        alt already indexed
            P-->>UI: skipped
        else new
            P->>L: load_pdf_bytes → one Document per page
            P->>C: chunk_documents (recursive, overlap)
            P->>V: add_chunks(ids = hash-page-offset)
            Note over V: embeds with Sentence-Transformers,<br/>stores in HNSW (cosine)
            P-->>UI: IngestReport(pages, chunks)
        end
    end
```

**Key choices**

- **Per-page documents** — page numbers survive chunking, enabling `file.pdf — p.7` citations.
- **Cleaning** — joins words hyphenated across line breaks, collapses whitespace, strips NULs.
- **Chunking** — `RecursiveCharacterTextSplitter` with separators
  `\n\n → \n → . → ? → ! → ; → , → space`. Default 1000 chars / 150 overlap (~200 tokens),
  which suits MiniLM's 256-token window while keeping enough context per chunk.
- **Deterministic chunk IDs** (`<hash16>-p<page>-<start_index>`) make ingestion idempotent.
- **Batching** — writes in batches of 256 to stay under Chroma's max batch size.
- **Failure handling** — corrupt, encrypted or text-less (scanned) PDFs are skipped with a
  reason; one bad page doesn't abort the whole file.

## 3. Query pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant P as RAGPipeline
    participant M as Memory
    participant LLM
    participant V as ChromaDB
    U->>P: question
    P->>M: history?
    alt has history
        P->>LLM: CONDENSE_PROMPT(history, question)
        LLM-->>P: standalone question
    end
    P->>V: MMR search(standalone, k, fetch_k, file filter)
    V-->>P: top-k chunks
    P->>LLM: ANSWER_PROMPT(numbered context, history, question)
    LLM-->>U: streamed tokens
    P->>P: parse [n] → SourceCitation(file, page, snippet)
    P->>M: add_turn(question, answer)
```

**Why condense?** Follow-ups are usually not self-contained. Embedding "and its limitations?"
matches random chunks; rewriting it to "What are the limitations of solar power?" retrieves
the right page. The condense step is skipped on the first turn (no extra latency/cost) and
falls back to the raw question if it errors.

**Why MMR?** Maximal Marginal Relevance (`λ = 0.6`) re-ranks `fetch_k = 20` candidates to
pick `k` that are relevant *and* mutually diverse — important when several PDFs repeat the
same boilerplate. Switch to `SEARCH_TYPE=similarity` (+ `SCORE_THRESHOLD`) for strict relevance.

**Grounding & citations.** The system prompt restricts the model to the numbered context,
requires `[n]` citations, and defines an explicit "couldn't find it" response. After
streaming, citations are parsed with a regex, validated against the number of retrieved
chunks (hallucinated `[9]` is ignored), and mapped back to file/page/snippet. If the model
cites nothing, all retrieved chunks are shown so evidence is never hidden.

**Memory.** A sliding window of the last `MEMORY_WINDOW` turns is stored per Streamlit
session and passed to both prompts. This bounds prompt size; a summary-buffer memory is a
natural extension for very long chats.

## 4. Data model (Chroma metadata per chunk)

| Field | Example | Used for |
|---|---|---|
| `source` | `annual_report.pdf` | Citation label, file list |
| `page` | `7` | Citation label |
| `total_pages` | `42` | Sidebar stats |
| `file_hash` | `9f86d0…` | Dedupe, delete, search filter |
| `start_index` | `1840` | Chunk id, ordering |
| `chunk_id` | `9f86d08188…-p7-1840` | Primary key |

## 5. Trade-offs & limitations

| Decision | Upside | Cost / limitation |
|---|---|---|
| MiniLM-L6 embeddings | Free, fast on CPU, private | Lower recall than `bge-large`/OpenAI embeddings; English-centric |
| pypdf | Pure Python, no system deps | No OCR, weak on complex tables/multi-column layouts |
| Workspaces = Chroma collections | Simple isolation per client/project | No authentication: anyone with the URL can open any workspace |
| Window memory | Predictable cost | Forgets older turns |
| Regex citations | Transparent, cheap | Relies on model following the format (strong models do) |

## 6. Extension points

- **Re-ranking:** insert a cross-encoder between `retrieve()` and prompt building.
- **Hybrid search:** combine BM25 (`rank_bm25`) with vector hits via reciprocal-rank fusion.
- **Evaluation:** RAGAS / a golden Q&A set run in CI to catch retrieval regressions.
- **API:** wrap `RAGPipeline` in FastAPI; the Streamlit app becomes one client.
- **Multi-tenant:** add authentication and map users to their own workspaces.

## 7. Presentation layer

```mermaid
flowchart LR
    APP[app.py<br/>st.navigation · top bar · sidebar] --> V1[views/dashboard]
    APP --> V2[views/documents]
    APP --> V3[views/analysis]
    APP --> V4[views/activity]
    APP --> V5[views/settings]
    V1 & V2 & V3 & V4 & V5 --> C[components.py<br/>stat cards · tables · badges · feeds · skeletons]
    V1 & V2 & V3 & V5 --> A[actions.py<br/>upload flow · modal dialogs]
    V1 & V2 & V3 & V4 & V5 --> S[state.py<br/>session · cached pipeline per workspace · prefs]
    C --> CSS[styles.py<br/>design tokens + component CSS]
```

- **Pages** are functions registered with `st.navigation`, grouped into Workspace / Insights /
  Administration sections. `DOCUMIND_START_PAGE` sets the landing page (also used by the UI tests).
- **Cards** are keyed containers (`st.container(key="card-…")`) styled through the `st-key-*` class
  Streamlit adds, so real widgets (buttons, charts, inputs) can live inside styled surfaces.
- **The document table** is built from zero-gap containers and columns, so every row can hold real
  action buttons. Secondary columns are hidden on small screens.
- **Static HTML** (stat cards, feeds, references) goes through `st.html`, which sanitises markup. Icons
  are therefore data-URI images rather than inline SVG. All interpolated values are HTML-escaped.
- **Model output** is rendered as Markdown after escaping `<` and `&`; `[n]` markers become styled
  citation chips.
- **Per-session preferences** (model, top-k, strategy, display name) are passed into the shared cached
  pipeline per call, never written to it.
