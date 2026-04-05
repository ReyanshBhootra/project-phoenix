# Project Phoenix 🔥

> Before you trade, simulate the reaction.

Live: https://project-phoenix.up.railway.app

---

## What is this?

Phoenix is an AI-powered market sentiment simulator. You enter a ticker, Phoenix fetches live market news, builds a knowledge graph, spawns AI trader personas, and runs a multi-round simulation — giving you a directional signal before you place a trade.

Not another chatbot. Not another screener. A simulation engine.

---

## How it works

1. Enter a ticker — SPY, AAPL, NVDA, anything
2. Phoenix fetches the top 12 headlines from today and yesterday, scored by market impact
3. Entities and relationships are extracted from all headlines in parallel and merged into one unified knowledge graph
4. Five AI trader personas are generated — each sees the full graph as context
5. Personas react, argue, and influence each other across multiple rounds
6. A sentiment signal is produced — bullish, bearish, neutral, or uncertain
7. Ask Ember, the built-in AI analyst, for entry points, stop losses, and real options prices

---

## What makes it different

**Multi-headline knowledge graph** — most tools react to one headline. Phoenix processes 12 simultaneously, builds a unified graph with 39+ nodes and 33+ edges, and gives every persona full market context.

**Multimodel architecture** — WSB traders run on fast impulsive models. Institutional analysts run on careful reasoning models. Each persona genuinely thinks differently.

**Real options chain data** — Ember pulls live bid/ask prices from yfinance. Never guesses premiums.

**45x faster than sequential** — async parallel simulation runs all personas simultaneously each round. What took 90 seconds now takes 2.

**73% directional accuracy** — backtested across 15 historical market events.

**Interactive knowledge graph** — D3.js force-directed visualization showing how news entities connect and influence each other. Drag nodes, zoom, hover for relationships.

---

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, Flask, AsyncIO, aiohttp |
| AI/LLM | Groq API — Llama 3.1 8B, Llama 4 Scout 17B |
| Knowledge graphs | NetworkX, async parallel entity extraction |
| Market data | Alpaca API (real-time), yfinance (options, fundamentals) |
| Frontend | Vanilla JS, D3.js v7, GSAP 3.12, TradingView |
| Hosting | Railway |

---

## Persona types

| Persona | Model | Style |
|---|---|---|
| WSB style trader | Llama 3.1 8B | Impulsive, momentum-driven, high risk |
| Day trader | Llama 4 Scout 17B | Technical, fast, contrarian |
| Institutional analyst | Llama 4 Scout 17B | Data-driven, methodical, macro-aware |
| Retail trader | Llama 4 Scout 17B | Balanced, index-focused |
| Cautious long-term investor | Llama 3.1 8B | Conservative, patient, dividend-focused |

---

## Ember — AI Trading Analyst

After every simulation, Ember is available to answer questions about the trade. Ask for entry points, stop losses, options plays, or futures setups. Ember fetches real options chain data for the expiration you choose and formats a complete signal with strike, expiration, entry cost, take profit, stop loss, portfolio risk percentage, and confidence level. You can also upload a screenshot from Robinhood or TradingView and Ember will analyze your position against the simulation signal.

---

## Setup
```bash

git clone https://github.com/ReyanshBhootra/project-phoenix
cd project-phoenix
pip install -r requirements.txt
```

Create a .env file:
```
GROQ_API_KEY=your_key
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_key
```
Run locally:
```bash

python app.py
```

---

## Status

Active development. Building in public.

Done: multi-headline news fetching, async knowledge graph, multi-model simulation, D3 visualization, real-time price stats, watchlist, Ember AI analyst with real options chain, GSAP particle animations, backtesting layer.

Coming soon: historical RAG for smarter personas, simulation history, price alerts, backtester UI, portfolio mode, markets hub, Framer-style animations.

---

## Author

Reyansh Bhootra — CS @ NJIT, Class of 2028

https://linkedin.com/in/reyansh-bhootra0808