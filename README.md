# Social – AI Social Media Analysis & Posting

An **Autonomous Political Accountability and Normative Discourse System** that monitors political news, analyses it with AI agents, and publishes fact-checked, AI-labelled posts to X (Twitter) – all with an optional Human-in-the-Loop review step.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Available Commands](#available-commands)
6. [Running Tests](#running-tests)
7. [Project Structure](#project-structure)

---

## Prerequisites

| Requirement | Minimum version |
|---|---|
| Python | 3.11+ |
| Redis | 7.x |
| (Optional) Apache Kafka | 3.x |

You will also need API keys for the services listed in the [Configuration](#configuration) section.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Kulde-epsingh25/Social.git
cd Social
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the spaCy language model

```bash
python -m spacy download en_core_web_sm
```

---

## Configuration

All runtime secrets and settings are loaded from a `.env` file in the project root.

### 1. Copy the example file

```bash
cp .env.example .env
```

### 2. Fill in your values

Open `.env` and replace every `your_*_here` placeholder with real credentials:

| Variable | Description |
|---|---|
| `NEWS_API_KEY` | [EventRegistry](https://eventregistry.org) API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model to use (default: `gpt-4o`) |
| `REDIS_URL` | Redis host URL (default: `redis://localhost`) |
| `REDIS_PORT` | Redis port (default: `6379`) |
| `X_API_KEY` | X (Twitter) API key |
| `X_API_SECRET` | X (Twitter) API secret |
| `X_ACCESS_TOKEN` | X (Twitter) access token |
| `X_ACCESS_TOKEN_SECRET` | X (Twitter) access token secret |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address (default: `localhost:9092`) |
| `OGD_API_KEY` | OGD Platform India key (for FIR data) |
| `ORIGINALITY_API_KEY` | Originality.ai key for fact-checking |
| `MAX_POSTS_PER_DAY` | Daily posting limit (default: `10`) |
| `POST_INTERVAL_MINUTES` | Minimum minutes between posts (default: `60`) |
| `HITL_ENABLED` | Set to `True` to require human approval before posting |

### 3. Start Redis

```bash
redis-server
```

> **Kafka is optional.** If you do not need the event-bus features, you can leave `KAFKA_BOOTSTRAP_SERVERS` pointing at a non-existent broker – the system will still run without it.

---

## Running the Application

### Full pipeline (fetch → analyse → review → post)

```bash
python main.py run --query "India parliament corruption"
```

### Launch the Streamlit monitoring dashboard

```bash
python main.py dashboard
```

### One-off topic analysis (no posting)

```bash
python main.py analyze "budget session 2025"
```

### Show posts pending Human-in-the-Loop review

```bash
python main.py review
```

---

## Available Commands

| Command | Description |
|---|---|
| `run` | Run the full pipeline for a news query |
| `analyze` | Analyze a topic without posting |
| `review` | List posts awaiting HITL approval |
| `dashboard` | Open the Streamlit monitoring UI |

Run `python main.py --help` or `python main.py <command> --help` for detailed options.

---

## Running Tests

```bash
pytest tests/
```

To see verbose output:

```bash
pytest -v tests/
```

---

## Project Structure

```
Social/
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── src/
│   ├── agents/              # AI agent definitions (fact-checker, philosopher, etc.)
│   ├── compliance/          # IT-Rules / SGI compliance checks
│   ├── config/              # Settings and configuration loader
│   ├── dashboard/           # Streamlit monitoring dashboard
│   ├── ingestion/           # News ingestion agent
│   ├── nlp/                 # NLP utilities
│   ├── orchestration/       # LangGraph workflow & CrewAI orchestrator
│   ├── publishing/          # X (Twitter) publisher & HITL queue
│   └── rag/                 # Retrieval-Augmented Generation helpers
└── tests/                   # Pytest test suite
```

---

## License

This project is provided as-is. See the repository owner for licensing details.