# F.R.I.D.A.Y. V2 — Fully Responsive Intelligent Digital Assistant for You

> *"A trusted aide who's been awake while the boss slept — precise, warm, and sharp."*

An enterprise-grade, Tony Stark-inspired AI voice assistant built with:
- **FastMCP & LiveKit Agents** (Real-time voice streaming with SSE tool communication)
- **Multi-Provider Resilience** (Sarvam AI STT, Google Gemini 2.5 Flash / OpenAI LLM, OpenAI Nova / Sarvam TTS with automatic failover)
- **Real Web Search Engine** (DuckDuckGo live scraping — zero API key required)
- **Dual-Layer Persistent Memory** (Short-term working session buffer + Long-term facts & preferences with Supabase & local JSON fallback)
- **Task Management Engine** (Full CRUD task tracking with priority, due date, and status)
- **System Telemetry & Health Diagnostics** (`/health`, `/health/live`, `/health/ready`, `/metrics`)
- **React 19 + TypeScript Frontend** (LiveKit audio renderer, wave visualizer, system health monitors, and quick directives)

---

## 🏗️ Architecture & Data Flow

Project class and voice request sequence diagrams are available in
[DIAGRAMS.md](./DIAGRAMS.md).

```
┌─────────────────────────────────────────────────────────────┐
│                   React 19 + Vite Frontend                  │
│       (Wave Visualizer, Token Auth, HUD Directives)         │
└───────────────────────▲─────────────────────────────────────┘
                        │ Token / Health (:8080)
┌───────────────────────┴─────────────────────────────────────┐
│             Token & Health Server (aiohttp)                 │
│      - Sliding Window Rate Limiting (IP-based)              │
│      - CORS Security & Identity Sanitization                │
│      - Health Probes (/health, /metrics)                    │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────┐               ┌──────────────────────────┐
│   User Audio     │               │  F.R.I.D.A.Y. MCP Server │
│   Microphone     │               │        (FastMCP)         │
└────────┬─────────┘               └────────────▲─────────────┘
         │                                      │ SSE (:8000)
         ▼                                      │
┌───────────────────────────────────────────────┴─────────────┐
│                 LiveKit Voice Agent V2                      │
│                                                             │
│  1. STT Pipeline: Sarvam Saaras v3  ──► Fallback: Whisper   │
│  2. LLM Engine  : Gemini 2.5 Flash  ──► Fallback: GPT-4o    │
│  3. TTS Audio   : OpenAI Nova       ──► Fallback: Bulbul v3 │
│  4. FastMCP Tool Execution & Confirmation System            │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Registered MCP Tools                     │
├──────────────────────┬──────────────────────┬───────────────┤
│ Intelligence & Web   │ Memory & Context     │ Operations    │
├──────────────────────┼──────────────────────┼───────────────┤
│ • get_world_news     │ • remember           │ • create_task │
│ • search_web (live)  │ • recall             │ • list_tasks  │
│ • fetch_url (safe)   │ • forget             │ • update_task │
│ • open_world_monitor │ • clear_session      │ • delete_task │
│ • get_system_info    │ • conversation_log   │ • diagnostics │
└──────────────────────┴──────────────────────┴───────────────┘
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python ≥ 3.11
- Node.js ≥ 18
- [`uv`](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- LiveKit Cloud account (free tier)

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/SAGAR-TAMANG/friday-tony-stark-demo.git
cd friday-tony-stark-demo

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Setup environment variables
cp .env.example .env
# Edit .env with your LiveKit, Google, and Sarvam/OpenAI keys
```

### 3. Pre-flight Diagnostic Audit
Verify all providers, ports, and credentials before launching:
```bash
python main.py --audit
```

### 4. Running F.R.I.D.A.Y. V2

#### Option A: Unified Launcher (Recommended)
Starts the FastMCP server (:8000) and Token & Health server (:8080) concurrently:
```bash
python main.py
```

Then in a second terminal, start the LiveKit Voice Agent:
```bash
uv run agent_friday.py dev
```

And in a third terminal, start the React frontend:
```bash
cd frontend && npm run dev
```

#### Option B: Individual Service Launchers
- **FastMCP Server**: `python main.py --mcp` (or `uv run friday`)
- **Token Server**: `python main.py --token`
- **Voice Agent**: `python main.py --agent` (or `uv run friday_voice`)

---

## 🧪 Testing Suite

Run the unit test suite covering configuration, URL safety, permissions, memory store, tasks, and health probes:
```bash
python tests/run_tests.py
```

---

## 🛡️ Security & Reliability Features

1. **Origin Verification & Safe CORS**: Restricts access in production while enabling smooth development.
2. **Rate Limiting**: Sliding window request throttler on `/api/token`.
3. **Database Dual-Engine**: Connects to Supabase PostgreSQL when credentials exist; automatically degrades to a persistent local JSON store if offline.
4. **Action Confirmation**: Consequential actions (such as task deletion) are guarded with permission requirements.
5. **Circuit Breakers & Retries**: Built-in exponential backoff for web requests, RSS feeds, and tool executions.

---

## 📄 License
MIT
