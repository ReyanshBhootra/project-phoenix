import os
import json
import asyncio
import aiohttp
import networkx as nx
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


async def extract_entities_async(session: aiohttp.ClientSession, headline: str, headline_id: int) -> dict:
    """Extract entities from a single headline asynchronously."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""You are a financial knowledge graph builder.
Given this market news headline, extract entities and relationships.

Headline: "{headline}"

Respond ONLY with valid JSON in exactly this format, nothing else:
{{
  "entities": [
    {{"id": "h{headline_id}_e1", "name": "Federal Reserve", "type": "organization"}},
    {{"id": "h{headline_id}_e2", "name": "interest rates", "type": "economic_concept"}}
  ],
  "relationships": [
    {{"source": "h{headline_id}_e1", "target": "h{headline_id}_e2", "relation": "raises"}}
  ]
}}

Entity types: organization, person, market_instrument, economic_concept, event, monetary_value
Keep to the most important 4-6 entities and relationships only.
Use unique IDs prefixed with h{headline_id}_ to avoid conflicts."""

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    for attempt in range(3):
        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                data = await resp.json()
                raw = data["choices"][0]["message"]["content"].strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()
                return json.loads(raw)
        except Exception as e:
            if attempt == 2:
                print(f"Graph extraction failed for headline {headline_id}: {e}")
                return {"entities": [], "relationships": []}
            await asyncio.sleep(1)

    return {"entities": [], "relationships": []}


async def build_unified_graph_async(headlines: list) -> tuple:
    """
    Extract entities from ALL headlines in parallel.
    Merge into one unified graph, deduplicating same entities.
    Returns (graph, merged_data)
    """
    print(f"[GraphBuilder] Extracting entities from {len(headlines)} headlines in parallel...")

    async with aiohttp.ClientSession() as session:
        tasks = [
            extract_entities_async(session, h, i)
            for i, h in enumerate(headlines)
        ]
        results = await asyncio.gather(*tasks)

    # Merge all entities and relationships
    all_entities = []
    all_relationships = []
    entity_name_to_id = {}  # For deduplication

    for result in results:
        for entity in result.get("entities", []):
            name_key = entity["name"].lower().strip()

            if name_key not in entity_name_to_id:
                # New entity -- add it
                entity_name_to_id[name_key] = entity["id"]
                all_entities.append(entity)
            # If duplicate entity name, use existing ID

        for rel in result.get("relationships", []):
            if rel.get("source") and rel.get("target") and rel.get("relation"):
                # Remap IDs to deduplicated IDs
                src_entity = next((e for e in result["entities"] if e["id"] == rel["source"]), None)
                tgt_entity = next((e for e in result["entities"] if e["id"] == rel["target"]), None)

                if src_entity and tgt_entity:
                    src_key = src_entity["name"].lower().strip()
                    tgt_key = tgt_entity["name"].lower().strip()

                    remapped_rel = {
                        "source": entity_name_to_id.get(src_key, rel["source"]),
                        "target": entity_name_to_id.get(tgt_key, rel["target"]),
                        "relation": rel["relation"]
                    }
                    all_relationships.append(remapped_rel)

    merged_data = {
        "entities": all_entities,
        "relationships": all_relationships
    }

    # Build NetworkX graph
    G = nx.DiGraph()
    for entity in all_entities:
        G.add_node(entity["id"], name=entity["name"], type=entity["type"])

    for rel in all_relationships:
        if rel.get("source") and rel.get("target"):
            G.add_edge(rel["source"], rel["target"], relation=rel["relation"])

    print(f"[GraphBuilder] Unified graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G, merged_data


def build_unified_graph(headlines: list) -> tuple:
    """Sync wrapper for async graph building."""
    return asyncio.run(build_unified_graph_async(headlines))


# Legacy functions for compatibility
def extract_entities_and_relations(headline: str) -> dict:
    prompt = f"""You are a financial knowledge graph builder.
Given this market news headline, extract entities and relationships.

Headline: "{headline}"

Respond ONLY with valid JSON:
{{
  "entities": [
    {{"id": "e1", "name": "Federal Reserve", "type": "organization"}}
  ],
  "relationships": [
    {{"source": "e1", "target": "e2", "relation": "raises"}}
  ]
}}

Entity types: organization, person, market_instrument, economic_concept, event
Keep to 5-8 entities max."""

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
    return json.loads(raw.strip())


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
    print(f"\n--- KNOWLEDGE GRAPH: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges ---")
    for node, attrs in G.nodes(data=True):
        print(f"  [{attrs['type']}] {attrs['name']}")
    for source, target, attrs in G.edges(data=True):
        print(f"  {id_to_name.get(source, source)} --[{attrs['relation']}]--> {id_to_name.get(target, target)}")


if __name__ == "__main__":
    headlines = [
        "Federal Reserve raises interest rates by 50 basis points amid inflation concerns",
        "S&P 500 falls sharply as recession fears grow after Fed decision",
        "Tech stocks slide as rising rates hurt growth valuations"
    ]
    G, data = build_unified_graph(headlines)
    print_graph_summary(G, data)