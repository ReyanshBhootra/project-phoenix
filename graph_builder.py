import os
import json
import networkx as nx
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_entities_and_relations(headline: str) -> dict:
    prompt = f"""
You are a financial knowledge graph builder.
Given this market news headline, extract entities and relationships.

Headline: "{headline}"

Respond ONLY with valid JSON in exactly this format, nothing else:
{{
  "entities": [
    {{"id": "e1", "name": "Federal Reserve", "type": "organization"}},
    {{"id": "e2", "name": "interest rates", "type": "economic_concept"}}
  ],
  "relationships": [
    {{"source": "e1", "target": "e2", "relation": "raises"}}
  ]
}}

Entity types can be: organization, person, market_instrument, economic_concept, event
Keep it to the most important 5-8 entities and relationships only.
"""
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)


def build_graph(data: dict) -> nx.DiGraph:
    G = nx.DiGraph()

    for entity in data["entities"]:
        G.add_node(entity["id"], name=entity["name"], type=entity["type"])

    for rel in data["relationships"]:
        if rel.get("source") and rel.get("target") and rel.get("relation"):
            G.add_edge(rel["source"], rel["target"], relation=rel["relation"])
    return G


def print_graph_summary(G: nx.DiGraph, data: dict):
    id_to_name = {e["id"]: e["name"] for e in data["entities"]}

    print("\n--- KNOWLEDGE GRAPH SUMMARY ---")
    print(f"Nodes ({G.number_of_nodes()}):")
    for node, attrs in G.nodes(data=True):
        print(f"  [{attrs['type']}] {attrs['name']}")

    print(f"\nEdges ({G.number_of_edges()}):")
    for source, target, attrs in G.edges(data=True):
        src_name = id_to_name.get(source, source)
        tgt_name = id_to_name.get(target, target)
        print(f"  {src_name} --[{attrs['relation']}]--> {tgt_name}")
    print("-------------------------------\n")


if __name__ == "__main__":
    headline = "Federal Reserve raises interest rates by 50 basis points as inflation hits 40-year high, sending SPY and QQQ lower"

    print(f"Processing headline:\n'{headline}'\n")

    data = extract_entities_and_relations(headline)
    G = build_graph(data)
    print_graph_summary(G, data)