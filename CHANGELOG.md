# Changelog

## 2.1.0 — Multi-model analysis
- Model picker in the Analysis composer listing every model your API keys can use (Groq and OpenAI fetched live; Ollama when selected)
- Automatic fallback to the next model when one is unavailable to your key; reports show the model used
- Settings: model dropdown, **Test connection**, clear "Key configured / Key rejected" status
- Actionable messages for rejected keys, rate limits, network problems and unavailable models
- Replaced API keys take effect without restarting the app
- Deployment hardening: SQLite shim for ChromaDB, CPU-only PyTorch, readable startup error screen
- Generic, multi-user greeting and profile (optional per-session display name)

## 2.0.0 — Document intelligence workspace
- Redesigned as an enterprise SaaS-style app: sidebar navigation, top bar, dashboard, documents table, activity log, settings
- Analysis results as report cards with citation markers, a references panel and Markdown export
- Workspaces backed by separate ChromaDB collections, with a per-workspace activity log
- Responsive layout for desktop, tablet and mobile

## 1.0.0 — Initial release
- Multi-PDF upload, per-page extraction, chunking, Sentence-Transformers embeddings, ChromaDB
- Conversational retrieval with question rewriting, MMR search and page-level citations
- Tests, CI, Docker and deployment guide
