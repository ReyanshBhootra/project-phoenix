from news_fetcher import get_latest_news
from graph_builder import extract_entities_and_relations, build_graph
from persona_generator import generate_personas
from simulation import run_simulation, calculate_sentiment, print_report


def run_pipeline(ticker: str = "QQQ", num_personas: int = 5, rounds: int = 3):
    print(f"\n========================================")
    print(f"   PROJECT PHOENIX -- LIVE SIMULATION")
    print(f"========================================\n")

    print(f"Step 1: Fetching latest {ticker} news...")
    articles = get_latest_news(ticker, max_articles=5)

    if not articles:
        print("No news found. Exiting.")
        return

    print(f"\nFound {len(articles)} articles. Selecting most relevant...\n")
    selected = articles[0]
    headline = selected["title"]

    if selected["summary"]:
        headline = headline + ". " + selected["summary"][:200]

    print(f"Selected headline:\n'{selected['title']}'")
    print(f"Source: {selected['source']}\n")

    print(f"Step 2: Building knowledge graph...")
    data = extract_entities_and_relations(headline)
    G = build_graph(data)
    print(f"Graph built -- {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

    print(f"Step 3: Generating {num_personas} trader personas...")
    personas = generate_personas(G, data, num_personas=num_personas, headline=headline)
    print(f"Personas generated\n")

    print(f"Step 4: Running simulation ({rounds} rounds)...")
    messages_log = run_simulation(personas, headline, rounds=rounds)

    print(f"Step 5: Generating sentiment report...")
    sentiment = calculate_sentiment(messages_log)
    print_report(sentiment, selected["title"])

    return sentiment


if __name__ == "__main__":
    run_pipeline(ticker="SPY", num_personas=5, rounds=3)
    run_pipeline(ticker="QQQ", num_personas=5, rounds=3)