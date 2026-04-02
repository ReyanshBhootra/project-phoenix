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


def generate_personas(G: nx.DiGraph, data: dict, num_personas: int = 10, headline: str = "", all_headlines: list = None) -> list:
    entities = [e["name"] for e in data["entities"]]
    edges = []
    id_to_name = {e["id"]: e["name"] for e in data["entities"]}

    for source, target, attrs in G.edges(data=True):
        src_name = id_to_name.get(source, source)
        tgt_name = id_to_name.get(target, target)
        edges.append(f"{src_name} --[{attrs['relation']}]--> {tgt_name}")

    graph_summary = f"""
Entities involved: {", ".join(entities[:20])}
Key relationships: {chr(10).join(edges[:15])}
"""

    # Use all headlines for richer context if provided
    if all_headlines and len(all_headlines) > 1:
        headlines_context = f"""
FULL NEWS CONTEXT ({len(all_headlines)} headlines from today/yesterday):
{chr(10).join([f'- {h}' for h in all_headlines[:10]])}

Primary headline: "{headline}"
"""
    else:
        headlines_context = f'Headline: "{headline}"'

    # Score all headlines together for sentiment
    combined_text = " ".join(all_headlines) if all_headlines else headline
    news_sentiment = detect_news_sentiment(combined_text)

    majority = max(3, int(num_personas * 0.6))
    minority = max(1, int(num_personas * 0.15))

    if news_sentiment == "NEGATIVE/BEARISH":
        stance_instruction = f"""Overall market sentiment from ALL headlines is: {news_sentiment}.
STRICT REQUIREMENTS:
- At least {majority} personas MUST start as 'bearish'
- Maximum {minority} persona can be 'bullish' (contrarian only)
- Remaining can be 'neutral' or 'uncertain'"""
    elif news_sentiment == "POSITIVE/BULLISH":
        stance_instruction = f"""Overall market sentiment from ALL headlines is: {news_sentiment}.
STRICT REQUIREMENTS:
- At least {majority} personas MUST start as 'bullish'
- Maximum {minority} persona can be 'bearish' (contrarian only)
- Remaining can be 'neutral' or 'uncertain'"""
    else:
        stance_instruction = f"Overall market sentiment is: {news_sentiment}. Mix stances realistically."

    prompt = f"""You are simulating a financial market with FULL NEWS CONTEXT.

{headlines_context}

Knowledge graph ({G.number_of_nodes()} entities, {G.number_of_edges()} relationships):
{graph_summary}

{stance_instruction}

Generate exactly {num_personas} unique trader personas who have READ ALL the news above.
Each persona should reference specific events from the full news context in their personality/likely_action.

Respond ONLY with valid JSON:
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
      "personality": "impulsive, follows momentum, reacting to Fed news and tech selloff",
      "likely_action": "buying put options given multiple bearish catalysts today",
      "influence_level": "low"
    }}
  ]
}}

Types: {", ".join(PERSONA_TYPES)}
Make each persona distinctly different with realistic names.
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