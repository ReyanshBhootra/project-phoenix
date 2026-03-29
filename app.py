from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import threading
import queue
import json
import os

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
        simulation_results[run_id]["status"] = "error"
        simulation_results[run_id]["error"] = str(e)


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


if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    app.run(debug=True, port=5000)