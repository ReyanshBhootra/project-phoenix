import os
import json
import asyncio
import aiohttp
from groq import Groq
from dotenv import load_dotenv
from graph_builder import extract_entities_and_relations, build_graph
from persona_generator import generate_personas

load_dotenv()

MODEL_MAP = {
    "wsb_style_trader": "llama-3.1-8b-instant",
    "day_trader": "meta-llama/llama-4-scout-17b-16e-instruct",
    "institutional_analyst": "meta-llama/llama-4-scout-17b-16e-instruct",
    "retail_trader": "meta-llama/llama-4-scout-17b-16e-instruct",
    "cautious_long_term_investor": "llama-3.1-8b-instant",
}

DEFAULT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def get_model_for_persona(persona_type: str) -> str:
    return MODEL_MAP.get(persona_type, DEFAULT_MODEL)


def parse_raw_response(raw: str) -> dict:
    if "<think>" in raw:
        raw = raw.split("</think>")[-1].strip()

    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            if "{" in part:
                raw = part
                if raw.startswith("json"):
                    raw = raw[4:]
                break

    raw = raw.strip()

    if raw and raw[0] != "{":
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]

    if not raw:
        return {"message": "Holding current position.", "updated_stance": "neutral", "influenced_by": None}

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            start = raw.find("{")
            end = raw.find("}") + 1
            if start != -1 and end > start:
                return json.loads(raw[start:end])
        except:
            pass
        return {"message": "Analyzing market conditions.", "updated_stance": "neutral", "influenced_by": None}


def normalize_stance(result: dict) -> str:
    valid_stances = ["bullish", "bearish", "neutral", "uncertain"]
    stance = result.get("updated_stance", "neutral").lower()
    if stance not in valid_stances:
        if "bullish" in stance:
            return "bullish"
        elif "bearish" in stance:
            return "bearish"
        else:
            return "neutral"
    return stance


async def call_groq_async(session: aiohttp.ClientSession, model: str, prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
    }

    for attempt in range(3):
        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                data = await resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content
                await asyncio.sleep(1)
        except Exception as e:
            if attempt == 2:
                raise
            await asyncio.sleep(1)

    return '{"message": "Holding position.", "updated_stance": "neutral", "influenced_by": null}'


async def run_persona_async(
    session: aiohttp.ClientSession,
    persona: dict,
    headline: str,
    recent_activity: str,
    current_stance: str,
    all_headlines: list = None
) -> dict:
    model = get_model_for_persona(persona["type"])

    # Build full news context
    if all_headlines and len(all_headlines) > 1:
        news_context = f"""You are aware of ALL these market developments today:
{chr(10).join([f'- {h}' for h in all_headlines[:8]])}

Primary headline driving this simulation: "{headline}"
"""
    else:
        news_context = f'The market news is: "{headline}"'

    prompt = f"""You are {persona["name"]}, a {persona["type"].replace("_", " ")} trader.
Your personality: {persona["personality"]}
Your risk tolerance: {persona["risk_tolerance"]}
Your portfolio focus: {persona["portfolio_focus"]}
Your current stance: {current_stance}

{news_context}

Recent activity from other traders:
{recent_activity}

Based on your personality, ALL the news context above, and what others are saying, respond with a short 1-2 sentence market opinion.
Be specific -- reference actual events from the news, not generic statements.
You can be influenced by others or double down on your stance.

Respond ONLY with valid JSON:
{{
  "message": "your specific reaction referencing actual news events",
  "updated_stance": "MUST be exactly one of: bullish, bearish, neutral, uncertain",
  "influenced_by": "name of who influenced you or null"
}}
"""

    try:
        raw = await call_groq_async(session, model, prompt)
        result = parse_raw_response(raw)
        result["updated_stance"] = normalize_stance(result)
        return {
            "persona": persona,
            "model": model.split("/")[-1],
            "result": result
        }
    except Exception as e:
        return {
            "persona": persona,
            "model": model.split("/")[-1],
            "result": {
                "message": "Analyzing market conditions.",
                "updated_stance": "neutral",
                "influenced_by": None
            }
        }

async def run_simulation_async(personas: list, headline: str, rounds: int = 3, all_headlines: list = None) -> list:
    messages_log = []
    sentiment_tracker = {p["id"]: p["initial_stance"] for p in personas}

    print(f"\n--- SIMULATION STARTING ({rounds} rounds, async parallel) ---\n")
    print(f"Multi-model setup:")
    for p in personas:
        model = get_model_for_persona(p["type"])
        print(f"  {p['name']} ({p['type']}) → {model.split('/')[-1]}")
    print()

    async with aiohttp.ClientSession() as session:
        for round_num in range(1, rounds + 1):
            print(f"--- Round {round_num} (running {len(personas)} personas in parallel) ---")

            # Use messages from PREVIOUS rounds only for context
            # This way parallel personas within same round still get context
            previous_round_messages = [
                m for m in messages_log
                if m["round"] < round_num
            ]

            recent_activity = "\n".join([
                f'{m["name"]} ({m["type"]}): {m["message"]}'
                for m in previous_round_messages[-8:]
            ]) if previous_round_messages else "No activity yet. This is round 1 - share your initial reaction to the news."

            tasks = [
                run_persona_async(
                    session,
                    persona,
                    headline,
                    recent_activity,
                    sentiment_tracker[persona["id"]],
                    all_headlines
                )
                for persona in personas
            ]

            results = await asyncio.gather(*tasks)

            for r in results:
                persona = r["persona"]
                result = r["result"]
                model = r["model"]

                sentiment_tracker[persona["id"]] = result["updated_stance"]

                message_entry = {
                    "round": round_num,
                    "persona_id": persona["id"],
                    "name": persona["name"],
                    "type": persona["type"],
                    "model": model,
                    "message": result["message"],
                    "stance": result["updated_stance"],
                    "influenced_by": result.get("influenced_by")
                }

                messages_log.append(message_entry)

                influenced = f" (influenced by {result['influenced_by']})" if result.get("influenced_by") else ""
                print(f"  [{result['updated_stance'].upper()}]{influenced} {persona['name']} [{model.split('-')[0]}]: {result['message']}")

            print()

    return messages_log


def run_simulation(personas: list, headline: str, rounds: int = 3, all_headlines: list = None) -> list:
    return asyncio.run(run_simulation_async(personas, headline, rounds, all_headlines))


def calculate_sentiment(messages_log: list) -> dict:
    final_round = max(m["round"] for m in messages_log)
    final_messages = [m for m in messages_log if m["round"] == final_round]

    counts = {"bullish": 0, "bearish": 0, "neutral": 0, "uncertain": 0}
    for m in final_messages:
        stance = m["stance"]
        if stance in counts:
            counts[stance] += 1

    total = len(final_messages)
    percentages = {}
    remaining = 100
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    for i, (k, v) in enumerate(items):
        if i == len(items) - 1:
            percentages[k] = remaining
        else:
            pct = round((v / total) * 100)
            percentages[k] = pct
            remaining -= pct

    dominant = max(counts, key=counts.get)

    return {
        "total_personas": total,
        "sentiment_breakdown": percentages,
        "dominant_sentiment": dominant,
        "final_round_messages": final_messages
    }


def print_report(sentiment: dict, headline: str):
    print("\n========================================")
    print("         MARKET SENTIMENT REPORT")
    print("========================================")
    print(f"Headline: {headline[:60]}...")
    print(f"\nSimulated {sentiment['total_personas']} market participants\n")
    print("Sentiment breakdown:")
    for stance, pct in sentiment["sentiment_breakdown"].items():
        bar = "█" * (pct // 5)
        print(f"  {stance.upper():10} {bar} {pct}%")
    print(f"\nDominant sentiment: {sentiment['dominant_sentiment'].upper()}")
    print("========================================\n")


if __name__ == "__main__":
    import time
    headline = "Federal Reserve raises interest rates by 50 basis points as inflation hits 40-year high, sending SPY and QQQ lower"

    print("Building knowledge graph...")
    data = extract_entities_and_relations(headline)
    G = build_graph(data)

    print("Generating personas...")
    personas = generate_personas(G, data, num_personas=5, headline=headline)

    start = time.time()
    messages_log = run_simulation(personas, headline, rounds=3)
    elapsed = time.time() - start

    sentiment = calculate_sentiment(messages_log)
    print_report(sentiment, headline)
    print(f"Total simulation time: {elapsed:.1f} seconds")