from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import threading
import queue
import json
import os
from price_feed import get_snapshot


from news_fetcher import get_latest_news
from graph_builder import extract_entities_and_relations, build_graph
from persona_generator import generate_personas
from simulation import run_simulation, calculate_sentiment

app = Flask(__name__, static_folder='static')
CORS(app)

simulation_queue = queue.Queue()
simulation_results = {}


def run_pipeline_async(run_id: str, ticker: str, num_personas: int, rounds: int):
    try:
        simulation_results[run_id] = {"status": "running", "steps": [], "messages": [], "report": None}

        simulation_results[run_id]["steps"].append(f"Fetching latest {ticker} news...")
        articles = get_latest_news(ticker, max_articles=5)

        if not articles:
            simulation_results[run_id]["status"] = "error"
            simulation_results[run_id]["error"] = "No news found"
            return

        selected = articles[0]
        headline = selected["title"]
        if selected["summary"]:
            headline = headline + ". " + selected["summary"][:200]

        simulation_results[run_id]["headline"] = selected["title"]
        simulation_results[run_id]["source"] = selected["source"]
        simulation_results[run_id]["steps"].append(f"Found headline: {selected['title']}")

        simulation_results[run_id]["steps"].append("Building knowledge graph...")
        data = extract_entities_and_relations(headline)
        G = build_graph(data)
        simulation_results[run_id]["graph"] = {
            "nodes": [{"id": n, **d} for n, d in G.nodes(data=True)],
            "edges": data["relationships"]
        }
        simulation_results[run_id]["steps"].append(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        simulation_results[run_id]["steps"].append(f"Generating {num_personas} trader personas...")
        personas = generate_personas(G, data, num_personas=num_personas, headline=headline)
        simulation_results[run_id]["personas"] = personas
        simulation_results[run_id]["steps"].append("Personas generated")

        simulation_results[run_id]["steps"].append("Running simulation...")
        messages_log = run_simulation(personas, headline, rounds=rounds)
        simulation_results[run_id]["messages"] = messages_log

        sentiment = calculate_sentiment(messages_log)
        simulation_results[run_id]["report"] = sentiment
        simulation_results[run_id]["status"] = "complete"
        simulation_results[run_id]["steps"].append("Simulation complete")

    except Exception as e:
        import traceback
        simulation_results[run_id]["status"] = "error"
        simulation_results[run_id]["error"] = str(e)
        print(f"PIPELINE ERROR: {traceback.format_exc()}")


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/run', methods=['POST'])
def run_simulation_endpoint():
    data = request.json
    ticker = data.get('ticker', 'SPY').upper()
    num_personas = int(data.get('num_personas', 5))
    rounds = int(data.get('rounds', 3))

    run_id = f"{ticker}_{os.urandom(4).hex()}"
    simulation_results[run_id] = {"status": "starting"}

    thread = threading.Thread(
        target=run_pipeline_async,
        args=(run_id, ticker, num_personas, rounds)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"run_id": run_id})


@app.route('/api/status/<run_id>')
def get_status(run_id):
    result = simulation_results.get(run_id, {"status": "not_found"})
    return jsonify(result)


@app.route('/api/news/<ticker>')
def get_news(ticker):
    articles = get_latest_news(ticker.upper(), max_articles=5)
    return jsonify(articles)

@app.route('/api/stats/<ticker>')
def get_stats(ticker):
    try:
        # Real-time price from Alpaca
        alpaca_data = get_snapshot(ticker.upper())

        # Fundamentals from yfinance
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        # Use Alpaca price if available, fall back to yfinance
        price = alpaca_data["price"] if alpaca_data else (info.get("currentPrice") or info.get("regularMarketPrice"))
        change = alpaca_data["change"] if alpaca_data else info.get("regularMarketChange")
        change_pct = alpaca_data["change_pct"] if alpaca_data else info.get("regularMarketChangePercent")

        stats = {
            "name": info.get("longName", ticker),
            "exchange": info.get("exchange", ""),
            "sector": info.get("sector", info.get("category", "")),
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "volume": alpaca_data["volume"] if alpaca_data else info.get("regularMarketVolume"),
            "avg_volume": info.get("averageVolume"),
            "market_cap": info.get("marketCap"),
            "aum": info.get("totalAssets"),
            "beta": info.get("beta3Year") or info.get("beta"),
            "dividend_yield": info.get("dividendYield"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "realtime": alpaca_data is not None,
        }

        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)