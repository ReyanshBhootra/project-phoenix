# Project Phoenix 🔥

> Simulate how the market reacts before you trade.

## Live Demo
🔥 [project-phoenix.up.railway.app](https://project-phoenix.up.railway.app)

Project Phoenix is an AI-powered market sentiment simulator that spawns multiple trader personas, lets them react to live market news, and produces a directional signal before you place a trade.

## How it works

1. **Enter a ticker** — SPY, QQQ, AAPL, NVDA, or any stock
2. **Live news is fetched** — real headlines pulled automatically
3. **Knowledge graph is built** — entities and relationships extracted from the headline
4. **Trader personas are spawned** — 5 distinct AI personas with unique personalities
5. **Simulation runs** — personas react, argue, and influence each other over 3 rounds
6. **Sentiment report generated** — bullish/bearish/neutral signal with full breakdown

## What makes it different

- **Multimodel architecture** — different AI models power different persona types. WSB traders run on a fast impulsive model, institutional analysts on a careful reasoning model, day traders on an aggressive model. Each persona genuinely thinks differently.
- **45x faster than sequential** — async parallel simulation runs all personas simultaneously each round
- **Backtested** — 73% overall accuracy across 15 historical market events

## Tech stack

- **Backend** — Python, Flask, AsyncIO, aiohttp
- **AI/LLM** — Groq API (multi-model: Llama 3.1, Llama 4 Scout, Kimi K2)
- **Knowledge graphs** — NetworkX, GraphRAG-style entity extraction
- **Market data** — yfinance, Polygon.io
- **Frontend** — Vanilla JS, DM Serif Display + DM Sans fonts
- **Hosting** — Vercel (frontend), Railway (backend)

## Persona types & models

| Persona | Model | Characteristics |
|---|---|---|
| WSB style trader | Llama 3.1 8B | Impulsive, momentum-driven, high risk |
| Day trader | Llama 4 Scout | Technical, fast-moving, contrarian |
| Institutional analyst | Llama 4 Scout | Data-driven, methodical, large-cap focused |
| Retail trader | Llama 4 Scout | Balanced, dividend-focused, cautious |
| Cautious long-term investor | Llama 3.1 8B | Conservative, patient, macro-aware |

## Setup
```bash
git clone https://github.com/ReyanshBhootra/project-phoenix
cd project-phoenix
pip install -r requirements.txt
cp .env.example .env  # add your API keys
python app.py
```

## Environment variables
```
GROQ_API_KEY=your_groq_key
```

## Status

Building in public. Work in progress.

**Completed:**
- Live news fetching
- Knowledge graph construction
- Multi-model persona generation
- Async parallel simulation engine
- Backtesting layer
- Full web dashboard

**Coming soon:**
- Deployment to Vercel + Railway
- Historical RAG system for smarter personas
- Expanded backtest dataset
- Signal accuracy dashboard

## Author

Reyansh Bhootra | CS @ NJIT | Class of 2028

Built in public follow the journey on [LinkedIn](https://linkedin.com/in/reyanshbhootra)