# Warhammer: The Old World — Rules Bot

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about **Warhammer: The Old World** rules, army compositions, unit stats, spells, and more.

Ask it anything — it retrieves the most relevant rules passages from the vector database and uses GPT-4o to give you a precise, cited answer.

---

## How it works

```
tow.whfb.app          old-world-builder (GitHub)
     │                         │
     ▼                         ▼
  Playwright              httpx + JSON
  (headless browser)       (direct fetch)
     │                         │
     └──────────┬──────────────┘
                ▼
           Chunker (500 tokens, 50 overlap)
                ▼
       OpenAI text-embedding-3-small
                ▼
         Pinecone vector DB
                ▼
       Streamlit chat UI
          + GPT-4o RAG
```

**Data sources:**
- **Rules, FAQ & Errata** — scraped from [tow.whfb.app](https://tow.whfb.app) (~3,200 pages)
- **Army & unit data** — fetched as JSON from the [old-world-builder](https://github.com/nthiebes/old-world-builder) GitHub repo

---

## Repository structure

```
tow-rules-bot/
├── pipeline/
│   ├── scraper.py        # Async Playwright scraper for tow.whfb.app
│   │                     #   → checkpoint-based resume on crash
│   ├── army_data.py      # Fetches army/unit/spell JSON from old-world-builder
│   ├── chunker.py        # Token-aware text chunking
│   ├── embedder.py       # OpenAI embeddings with progress bar + retry
│   ├── ingest.py         # Pinecone upsert (idempotent, SHA-256 IDs)
│   └── run_pipeline.py   # CLI orchestrator — runs all steps end to end
├── app/
│   └── app.py            # Streamlit chat UI with login + RAG
├── tests/
│   ├── test_scraper.py   # Checkpoint mechanism tests
│   ├── test_chunker.py   # Chunking logic tests
│   ├── test_army_data.py # JSON parsing + HTTP fetch tests
│   ├── test_embedder.py  # Embedding batching + retry tests
│   └── test_ingest.py    # Pinecone upsert tests
├── auth_config.yaml      # Login credentials (password auto-hashed on first run)
├── tow-rules-bot.service # systemd unit file for running on a server
├── pyproject.toml        # Python dependencies (managed by uv)
└── .env                  # API keys — never committed (see setup below)
```

---

## Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) package manager
- An **OpenAI API key**
- A **Pinecone API key**

---

## Setup

### 1. Clone the repo

```bash
git clone git@github.com:Malou2m/tow-rules-bot.git
cd tow-rules-bot
```

### 2. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Install Playwright's Chromium browser

```bash
uv run playwright install chromium
```

On Amazon Linux / CentOS you also need the system libraries:

```bash
sudo dnf install -y atk at-spi2-atk at-spi2-core cups-libs libxkbcommon \
    libXcomposite libXdamage libXfixes libXrandr libgbm pango cairo alsa-lib nss nspr
```

### 5. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=tow-rules
```

### 6. (Optional) Change the login credentials

Edit `auth_config.yaml`:

```yaml
credentials:
  usernames:
    YOUR_USERNAME:
      email: your@email.com
      name: Your Name
      password: your_plain_text_password  # auto-hashed on first startup
```

---

## Running the data pipeline

The pipeline scrapes all rules pages, embeds them, and uploads them to Pinecone. **Run this once** before starting the UI.

```bash
uv run python -m pipeline.run_pipeline
```

This runs all four steps automatically:
1. Scrape ~3,200 pages from tow.whfb.app (takes ~30 min)
2. Fetch army/unit data from old-world-builder
3. Chunk and embed everything with OpenAI
4. Upsert all vectors to Pinecone

### Pipeline flags

| Flag | Description |
|---|---|
| `--force-scrape` | Re-scrape tow.whfb.app (ignores cache) |
| `--force-army` | Re-fetch army data from GitHub |
| `--skip-tow` | Skip tow.whfb.app, only process army data |
| `--skip-army` | Skip army data, only process rules |
| `--dry-run` | Chunk + embed but don't upsert to Pinecone |

### Crash recovery

The scraper writes a checkpoint after every successfully scraped page (`pipeline/cache/checkpoint.jsonl`). If the pipeline crashes or is interrupted, just rerun the same command — it will resume from where it left off automatically.

---

## Running the UI

### Locally (development)

```bash
uv run streamlit run app/app.py
```

Open `http://localhost:8501` in your browser.

### On a remote server (EC2 / VPS)

#### Option A — Run manually

```bash
uv run streamlit run app/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
```

Then open `http://<your-server-ip>:8501` in your browser.

Make sure **port 8501 is open** in your server's firewall / security group (TCP inbound).

#### Option B — Run as a systemd service (recommended for EC2)

This keeps the app running permanently and restarts it automatically on failure or reboot.

```bash
# Copy the service file
sudo cp tow-rules-bot.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable tow-rules-bot
sudo systemctl start tow-rules-bot
```

Check status:

```bash
sudo systemctl status tow-rules-bot
```

View logs:

```bash
sudo journalctl -u tow-rules-bot -f
```

Stop / restart:

```bash
sudo systemctl stop tow-rules-bot
sudo systemctl restart tow-rules-bot
```

> **AWS security group:** add an inbound rule for **TCP port 8501** from `0.0.0.0/0` (or your own IP for extra security).

---

## Running the tests

```bash
uv run pytest tests/ -v
```

76 unit tests covering all pipeline modules. No real API calls are made — all external services are mocked.

---

## Tech stack

| Component | Technology |
|---|---|
| Scraping | [Playwright](https://playwright.dev/python/) (async, headless Chromium) |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dimensions) |
| Vector DB | [Pinecone](https://www.pinecone.io/) (serverless, cosine similarity) |
| LLM | OpenAI `gpt-4o` |
| UI | [Streamlit](https://streamlit.io/) |
| Auth | [streamlit-authenticator](https://github.com/mkhorasani/Streamlit-Authenticator) |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Tests | pytest + pytest-mock + pytest-asyncio |
