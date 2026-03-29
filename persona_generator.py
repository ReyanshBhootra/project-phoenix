import os
import json
import networkx as nx
from groq import Groq
from dotenv import load_dotenv
from graph_builder import extract_entities_and_relations, build_graph

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PERSONA_TYPES = [
    "retail_trader",
    "institutional_analyst",
    "wsb_style_trader",
    "cautious_long_term_investor",
    "day_trader",
]

BEARISH_WORDS = [
    "fall", "falls", "falling", "drop", "drops", "dropping", "decline", "declines",
    "correction", "slide", "slides", "sliding", "down", "lower", "lose", "losses",
    "recession", "fears", "concern", "concerns", "risk", "crash", "selloff",
    "sell-off", "plunge", "plunges", "tumble", "tumbles", "slump", "weakness",
    "bearish", "negative", "worries", "uncertainty", "volatile", "volatility"
]

BULLISH_WORDS = [
    "rise", "rises", "rising", "gain", "gains", "surge", "surges", "rally",
    "rallies", "up", "higher", "growth", "beat", "beats", "strong", "strength",
    "bullish", "positive", "optimism", "recovery", "rebound", "boom", "soar",
    "soars", "jump", "jumps", "record", "high", "exceed", "exceeds"
]


def detect_news_sentiment(headline: str) -> str:
    headline_lower = headline.lower()
    bearish_count = sum(1 for word in BEARISH_WORDS if word in headline_lower)
    bullish_count = sum(1 for word in BULLISH_WORDS if word in headline_lower)

    if bearish_count > bullish_count:
        return "NEGATIVE/BEARISH"
    elif bullish_count > bearish_count:
        return "POSITIVE/BULLISH"
    else:
        return "MIXED/NEUTRAL"


def generate_personas(G: nx.DiGraph, data: dict, num_personas: int = 10, headline: str = "") -> list:
    entities = [e["name"] for e in data["entities"]]
    edges = []
    id_to_name = {e["id"]: e["name"] for e in data["entities"]}

    for source, target, attrs in G.edges(data=True):
        src_name = id_to_name.get(source, source)
        tgt_name = id_to_name.get(target, target)
        edges.append(f"{src_name} --[{attrs['relation']}]--> {tgt_name}")

    graph_summary = f"""
Entities involved: {", ".join(entities)}
Relationships: {chr(10).join(edges)}
"""

    news_sentiment = detect_news_sentiment(headline) if headline else "MIXED/NEUTRAL"

    if news_sentiment == "NEGATIVE/BEARISH":
        stance_instruction = f"The market event sentiment is: {news_sentiment}. At least 3 out of {num_personas} personas must have an initial_stance of 'bearish'. Only 1 persona may be bullish as a contrarian. The rest should be neutral or uncertain."
    elif news_sentiment == "POSITIVE/BULLISH":
        stance_instruction = f"The market event sentiment is: {news_sentiment}. At least 3 out of {num_personas} personas must have an initial_stance of 'bullish'. Only 1 persona may be bearish as a contrarian. The rest should be neutral or uncertain."
    else:
        stance_instruction = f"The market event sentiment is: {news_sentiment}. Mix stances realistically -- some bullish, some bearish, some neutral or uncertain."

    prompt = f"""
You are simulating a financial market. Based on this knowledge graph of a market event, generate {num_personas} unique trader personas who will react to this event.

Knowledge graph:
{graph_summary}

Headline context: "{headline[:200] if headline else 'Market event'}"

{stance_instruction}

Generate exactly {num_personas} personas. Respond ONLY with valid JSON, nothing else:
{{
  "personas": [
    {{
      "id": "p1",
      "name": "Marcus Webb",
      "type": "wsb_style_trader",
      "age": 24,
      "risk_tolerance": "very_high",
      "portfolio_focus": "SPY options",
      "initial_stance": "bearish",
      "personality": "impulsive, follows momentum, easily influenced by social media",
      "likely_action": "buying put options on SPY immediately",
      "influence_level": "low"
    }}
  ]
}}

Types to use: {", ".join(PERSONA_TYPES)}
Risk tolerance options: low, medium, high, very_high
Initial stance options: bullish, bearish, neutral, uncertain
Influence level options: low, medium, high (high = opinion leader, influences others)
Make each persona distinctly different. Use realistic names.
"""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)["personas"]


def print_personas(personas: list):
    print(f"\n--- GENERATED {len(personas)} TRADER PERSONAS ---")
    for p in personas:
        print(f"\n[{p['type'].upper()}] {p['name']}, Age {p['age']}")
        print(f"  Risk tolerance : {p['risk_tolerance']}")
        print(f"  Portfolio focus: {p['portfolio_focus']}")
        print(f"  Initial stance : {p['initial_stance']}")
        print(f"  Personality    : {p['personality']}")
        print(f"  Likely action  : {p['likely_action']}")
        print(f"  Influence level: {p['influence_level']}")
    print(f"\n--- END OF PERSONAS ---\n")


if __name__ == "__main__":
    headline = "Federal Reserve raises interest rates by 50 basis points as inflation hits 40-year high, sending SPY and QQQ lower"

    print(f"Building knowledge graph from headline...\n")
    data = extract_entities_and_relations(headline)
    G = build_graph(data)

    print(f"Detected sentiment: {detect_news_sentiment(headline)}")
    print(f"Generating trader personas...\n")
    personas = generate_personas(G, data, num_personas=5, headline=headline)
    print_personas(personas)