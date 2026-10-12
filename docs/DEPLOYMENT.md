# Deployment Guide

| Option | Cost | Best for | Persistence |
|---|---|---|---|
| [Local](#1-local) | Free | Development | ✅ disk |
| [Docker](#2-docker) | Free | Reproducible runs, any VM | ✅ volume |
| [Streamlit Community Cloud](#3-streamlit-community-cloud-recommended-for-portfolio) | Free | **Portfolio demo link** | ⚠️ resets on reboot |
| [Hugging Face Spaces](#4-hugging-face-spaces) | Free (16 GB RAM CPU) | Demo with more RAM | ⚠️ unless persistent storage enabled |
| [Render / Railway / VM](#5-render-railway-or-any-vm) | Paid tiers | Always-on, persistent | ✅ disk/volume |

**Before any deploy:** get an LLM key. [Groq](https://console.groq.com/keys) is free and fast.

---

## 1. Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set GROQ_API_KEY
streamlit run app.py
```

First run downloads the embedding model (~90 MB) to `~/.cache/huggingface`.

**Fully offline:** install [Ollama](https://ollama.com), `ollama pull llama3.2`, set
`LLM_PROVIDER=ollama`.

**Smaller install (CPU-only torch):**
```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt
```

## 2. Docker

```bash
cp .env.example .env            # set GROQ_API_KEY
docker compose up --build -d
docker compose logs -f
```

- The image uses CPU-only PyTorch and pre-downloads the embedding model, so containers start
  without network calls to Hugging Face.
- The ChromaDB index lives in the `documind-data` named volume and survives restarts.
- Health check: `GET /_stcore/health`.

Plain Docker:
```bash
docker build -t documind .
docker run -p 8501:8501 --env-file .env -v documind-data:/app/data documind
```

## 3. Streamlit Community Cloud (recommended for portfolio)

1. Push the repo to GitHub (public).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app** → pick the repo,
   branch `main`, main file `app.py`.
3. **Advanced settings → Python version 3.11**.
4. **Secrets** (TOML):
   ```toml
   GROQ_API_KEY = "gsk_..."
   LLM_PROVIDER = "groq"
   ```
   `app.py` copies secrets into environment variables, so no code changes are needed.
5. Deploy. Copy the `*.streamlit.app` URL into the README's **Live demo** link.

Notes
- Free apps have ~1 GB RAM. MiniLM + Chroma fit comfortably; avoid large embedding models.
- Storage is ephemeral — uploaded documents are wiped when the app sleeps/reboots. For a demo,
  that's fine (and a good privacy story).
- Workspaces are visible to every visitor (there is no login). Use a dedicated demo workspace and
  don't upload confidential documents to a public deployment.

## 4. Hugging Face Spaces

1. Create a Space → SDK **Docker** (uses this repo's `Dockerfile`).
2. Spaces expects port **7860**: add `ENV PORT=7860` and change the `CMD` port, or set
   `app_port: 8501` in the Space's `README.md` front-matter:
   ```yaml
   ---
   title: DocuMind
   sdk: docker
   app_port: 8501
   ---
   ```
3. **Settings → Variables and secrets** → add `GROQ_API_KEY`.
4. Push the repo to the Space's git remote.

## 5. Render, Railway or any VM

**Render** (Web Service, Docker runtime): connect the repo, add env vars, attach a
**persistent disk** mounted at `/app/data`. Use at least the 2 GB RAM instance.

**Railway:** New project → Deploy from GitHub → it detects the Dockerfile. Add env vars and a
volume at `/app/data`.

**VM (EC2 / GCP / Azure / DigitalOcean):**
```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
git clone https://github.com/Ajayvishal23/documind-rag.git && cd documind-rag
cp .env.example .env && nano .env
sudo docker compose up -d --build
```
Put Nginx/Caddy in front for HTTPS. Streamlit needs WebSocket support:
```nginx
location / {
    proxy_pass http://localhost:8501;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;
}
```

## Production checklist

- [ ] API keys only in secrets/env — never committed (`.env` is git-ignored)
- [ ] Persistent volume for `CHROMA_PERSIST_DIR`
- [ ] Per-user collections or authentication if documents are private
- [ ] `MAX_FILE_MB` and `server.maxUploadSize` set to sensible limits
- [ ] Health check wired to `/_stcore/health`
- [ ] LLM provider rate limits understood (Groq free tier has per-minute limits)
- [ ] Logs collected (`LOG_LEVEL=INFO`)

## Troubleshooting

| Symptom | Fix |
|---|---|
| `GROQ_API_KEY is not set` | Add it to `.env` or Streamlit secrets; restart the app |
| "no extractable text" on upload | The PDF is scanned images — run OCR first (e.g. `ocrmypdf in.pdf out.pdf`) |
| App killed / out of memory on free host | Use CPU torch, keep MiniLM, lower `CHUNK_SIZE` batch, or upgrade instance |
| Slow first question | Embedding model loading; cached after the first run |
| `sqlite3` version error from Chroma (some Linux hosts) | `pip install pysqlite3-binary` and add at the top of `app.py`: `__import__('pysqlite3'); import sys; sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')` |
| Answers ignore new uploads | Click **Index documents** after selecting files |
