# Project Phoenix - Context Brief

## What it is
AI-powered market sentiment simulator for options traders. Multi-agent AI spawns trader personas reacting to live market news to produce directional signals before trades are placed.

## Live URL
https://project-phoenix.up.railway.app
GitHub: https://github.com/ReyanshBhootra/project-phoenix

## Stack
Python 3.12, Flask, AsyncIO, aiohttp, Groq API, Alpaca API, yfinance, NetworkX, D3.js v7, GSAP 3.12, Railway

## Key files
- app.py -- Flask backend, all endpoints
- simulation.py -- async parallel simulation engine
- graph_builder.py -- multi-headline unified async knowledge graph builder
- news_fetcher.py -- fetches + scores all news from today/yesterday (12 articles)
- persona_generator.py -- generates trader personas from unified graph
- ember.py -- Ember AI analyst chatbot with options flow
- price_feed.py -- Alpaca real-time prices + yfinance options chain
- static/index.html -- entire frontend (D3 graph, GSAP, particles)

## Architecture -- Pipeline order
1. news_fetcher.py -- get_all_news() fetches 12 scored headlines from today/yesterday
2. graph_builder.py -- build_unified_graph() extracts entities from ALL headlines in parallel async, merges into one NetworkX graph (39+ nodes, 33+ edges)
3. persona_generator.py -- personas see full graph + all headlines as context
4. simulation.py -- async parallel simulation, multi-model (Llama 3.1 8b + Llama 4 Scout 17b)
5. ember.py -- post-simulation AI analyst with real options chain data

## Multi-model setup
- wsb_style_trader → llama-3.1-8b-instant
- day_trader → meta/llama-4-scout-17b-16e-instruct
- institutional_analyst → meta/llama-4-scout-17b-16e-instruct
- retail_trader → meta/llama-4-scout-17b-16e-instruct
- cautious_long_term_investor → llama-3.1-8b-instant

## Ember AI
- Scope enforced: trading only, shuts down off-topic
- Image upload with Groq Llama 4 Scout vision
- FETCH_OPTIONS flow: Ember asks expiration → outputs FETCH_OPTIONS JSON trigger → frontend fetches real yfinance chain → Ember gives signal with real prices
- Signal format: Strike, Expiration, Entry Cost (real from chain), Entry Zone, TP, Stop Loss/Invalidation, Portfolio Risk %, Technical Reason, Fundamental Reason, Confidence
- Never guesses premiums -- always uses real bid/ask from yfinance
- Futures pricing rule: /ES = SPY x ~10, /NQ = QQQ x ~40
- Dynamic expiration dates from get_upcoming_expirations()

## Options Chain
- get_options_chain_multi() in price_feed.py
- Fetches Friday expirations only (weekly/monthly), 4 expirations
- Real bid/ask, IV, volume from yfinance
- /api/options-chain GET endpoint

## Frontend Features
- TradingView advanced chart (480px height)
- Stats bar: Price (count-up), Change (flash), Volume, Avg Vol, Market Cap, AUM, Beta, Div Yield, 52W High/Low, P/E, EPS -- Alpaca + yfinance
- Live price polling every 3 seconds via Alpaca
- D3.js v7 force-directed knowledge graph:
  - Nodes colored by type (org=blue, market=green, economic=yellow, person=orange, event=red)
  - Node size by connection count
  - Edge arrows with relation labels on hover
  - Zoom/pan free, no boundary lock
  - Hover highlights connected nodes, dims others
  - Tooltip shows name, type, relations
  - Isolated nodes pushed to periphery, dimmed
  - Auto-zoom to connected cluster after 2.5s
- GSAP 3.12 particle hero background (80 orange particles + connecting lines, fixed position)
- GSAP scroll animations: panels slide in from sides, agent cards animate on render
- Watchlist sidebar: drag-and-drop reorder, 34 ticker autocomplete, live prices, localStorage
- Ember chat panel: bottom right fixed, no blur overlay, + button for image upload, typing indicator, suggestion chips

## API Endpoints
- POST /api/run -- start simulation (rate limited 3/hr/IP, localhost exempt)
- GET /api/status/<run_id> -- poll simulation status
- GET /api/stats/<ticker> -- full stats (Alpaca + yfinance)
- GET /api/price/<ticker> -- real-time price only (Alpaca, 3s polling)
- POST /api/ember -- Ember chat
- POST /api/ember/analyze-image -- Groq vision image analysis
- GET /api/options-chain -- live options chain (yfinance)

## Price feed notes
- Alpaca paper trading (no SSN needed)
- If bid/ask mid is >5% off from bar close → uses bar close (stale after-hours fix)
- yfinance used for options chain and fundamentals

## Env vars
GROQ_API_KEY, ALPACA_API_KEY, ALPACA_SECRET_KEY in .env and Railway Variables

## Dev setup
- PyCharm on Windows, Python 3.12
- Run: python app.py
- Deploy: git push → Railway auto-deploys
- Never commit .env (global gitignore at C:/Users/reyan/.gitignore_global)

## TO DO list
Pages: /simulate(current), /markets, /history, /alerts, /backtest, /portfolio

DONE (1-8):
1. Deploy to Railway
2. TradingView chart
3. Stats panel with live polling
4. Watchlist sidebar
5. Watchlist fixes (drag-drop, autocomplete, prices)
6. Ember AI analyst (image upload, options flow, signal format)
7. Multi-headline async knowledge graph (12 headlines, parallel extraction)
8. D3 interactive knowledge graph (force-directed, zoom/pan, hover, tooltips)

PENDING:
9. Sentiment pre-scorer (fix signal accuracy)
10. Volume-weighted sentiment signal
11. Earnings calendar auto-detect
12. Persona memory across rounds
13. Contradiction detection
14. Confidence score
15. Persona chat (post-simulation)
16. News panel (show all 12 headlines used)
17. Markets hub page (/markets)
18. Simulation history + accuracy tracking (/history)
19. Price alerts (/alerts)
20. Backtester UI (/backtest)
21. Portfolio mode -- multi-ticker (/portfolio)
22. RAG personas (historical pattern memory)
23. Options flow improvement (better data source)
24. Signal caching (Redis)
25. Animations overhaul (Framer-style, spring physics, magnetic cursor, blur reveals)
26. Tour feature for first-time users

## Known issues / notes
- Signal variability between runs -- expected without RAG
- "Holding position" responses reduced via prompt update but not eliminated
- Alpaca paper trading only -- no live account (F1 visa, no SSN/ITIN)
- Reyansh: CS @ NJIT class 2028, GPA 3.95, F1 visa, PyCharm Windows
- Rate limiting: 3 simulations/IP/hour, localhost exempt
- LearnBridge AI is a separate project -- keep separate from Phoenix