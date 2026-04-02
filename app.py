from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import threading
import queue
import json
import os
from price_feed import get_snapshot, get_options_chain_multi
from ember import ask_ember



from news_fetcher import get_latest_news, get_all_news
from graph_builder import extract_entities_and_relations, build_graph, build_unified_graph
from persona_generator import generate_personas
from simulation import run_simulation, calculate_sentiment

from collections import defaultdict
import time

request_counts = defaultdict(list)

def is_rate_limited(ip):
    if ip in ('127.0.0.1', 'localhost', '::1'):
        return False
    now = time.time()
    hour_ago = now - 3600
    request_counts[ip] = [t for t in request_counts[ip] if t > hour_ago]
    if len(request_counts[ip]) >= 3:
        return True
    request_counts[ip].append(now)
    return False

app = Flask(__name__, static_folder='static')
CORS(app)

simulation_queue = queue.Queue()
simulation_results = {}


def run_pipeline_async(run_id: str, ticker: str, num_personas: int, rounds: int):
    try:
        simulation_results[run_id] = {"status": "running", "steps": [], "messages": [], "report": None}

        # Step 1 -- Fetch ALL news from today + yesterday
        simulation_results[run_id]["steps"].append(f"Fetching latest {ticker} news...")
        from news_fetcher import get_all_news
        articles = get_all_news(ticker, max_articles=12)

        if not articles:
            simulation_results[run_id]["status"] = "error"
            simulation_results[run_id]["error"] = "No news found"
            return

        # Primary headline + all headlines for context
        primary = articles[0]
        all_headlines = [a["title"] for a in articles]
        headline = primary["title"]
        if primary["summary"]:
            headline = headline + ". " + primary["summary"][:200]

        simulation_results[run_id]["headline"] = primary["title"]
        simulation_results[run_id]["source"] = primary["source"]
        simulation_results[run_id]["steps"].append(f"Found headline: {primary['title']}")

        # Step 2 -- Build unified knowledge graph from ALL headlines
        simulation_results[run_id]["steps"].append(f"Building knowledge graph from {len(all_headlines)} headlines...")
        from graph_builder import build_unified_graph
        G, graph_data = build_unified_graph(all_headlines)
        simulation_results[run_id]["graph"] = {
            "nodes": [{"id": n, **d} for n, d in G.nodes(data=True)],
            "edges": graph_data["relationships"]
        }
        simulation_results[run_id]["steps"].append(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        # Step 3 -- Generate personas with full context
        simulation_results[run_id]["steps"].append(f"Generating {num_personas} trader personas...")
        personas = generate_personas(G, graph_data, num_personas=num_personas, headline=headline, all_headlines=all_headlines)
        simulation_results[run_id]["personas"] = personas
        simulation_results[run_id]["steps"].append("Personas generated")

        # Step 4 -- Run simulation with full headlines context
        simulation_results[run_id]["steps"].append("Running simulation...")
        messages_log = run_simulation(personas, headline, rounds=rounds, all_headlines=all_headlines)
        simulation_results[run_id]["messages"] = messages_log

        # Step 5 -- Calculate sentiment
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
    ip = request.remote_addr
    if is_rate_limited(ip):
        return jsonify({"error": "Rate limit exceeded. Max 3 simulations per hour."}), 429
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

@app.route('/api/price/<ticker>')
def get_price(ticker):
    try:
        snap = get_snapshot(ticker.upper())
        if not snap:
            return jsonify({"error": "no data"}), 404
        return jsonify(snap)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/api/ember', methods=['POST'])
def ember_chat():
    try:
        data = request.json
        question = data.get('question', '')
        simulation_data = data.get('simulation_data', {})
        conversation_history = data.get('conversation_history', [])

        if not question:
            return jsonify({"error": "No question provided"}), 400

        # Fetch live options chain if trading related question
        options_keywords = ['option', 'call', 'put', 'strike', 'expir', 'premium', 'signal', 'entry', 'trade']
        if any(kw in question.lower() for kw in options_keywords):
            ticker = simulation_data.get('ticker', 'SPY')
            chain = get_options_chain_multi(ticker, num_expirations=4)
            if chain:
                simulation_data['options_chain'] = chain

        response = ask_ember(question, simulation_data, conversation_history)
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ember/analyze-image', methods=['POST'])
def analyze_image():
    try:
        data = request.json
        image_base64 = data.get('image')
        question = data.get('question', 'What trading position is shown?')

        if not image_base64:
            return jsonify({"error": "No image provided"}), 400

        from groq import Groq
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        message = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": f"Analyze this trading screenshot. Extract: ticker, position type, entry price, current price, P&L, strike, expiration, quantity. Be specific and concise. User question: {question}"
                        }
                    ]
                }
            ],
            max_tokens=400
        )

        return jsonify({"analysis": message.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/options-chain', methods=['GET'])
def options_chain_endpoint():
    try:
        ticker = request.args.get('ticker', 'SPY').upper()
        expiration = request.args.get('expiration', None)
        chain = get_options_chain_multi(ticker, num_expirations=4)
        return jsonify({"chain": chain})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)