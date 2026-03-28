import os
import json
from groq import Groq
from dotenv import load_dotenv
from graph_builder import extract_entities_and_relations, build_graph
from persona_generator import generate_personas

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def run_simulation(personas: list, headline: str, rounds: int = 3) -> list:
    messages_log = []
    sentiment_tracker = {p["id"]: p["initial_stance"] for p in personas}

    print(f"\n--- SIMULATION STARTING ({rounds} rounds) ---\n")

    for round_num in range(1, rounds + 1):
        print(f"--- Round {round_num} ---")

        for persona in personas:
            other_messages = [
                m for m in messages_log
                if m["persona_id"] != persona["id"]
            ][-5:]

            recent_activity = "\n".join([
                f'{m["name"]} ({m["type"]}): {m["message"]}'
                for m in other_messages
            ]) if other_messages else "No activity yet."

            prompt = f"""
You are {persona["name"]}, a {persona["type"].replace("_", " ")} trader.
Your personality: {persona["personality"]}
Your risk tolerance: {persona["risk_tolerance"]}
Your portfolio focus: {persona["portfolio_focus"]}
Your current stance: {sentiment_tracker[persona["id"]]}

The market news is: "{headline}"

Recent activity from other traders:
{recent_activity}

Based on your personality and what others are saying, respond with a short 1-2 sentence market opinion or reaction. 
Be authentic to your character. You can be influenced by others or double down on your stance.
Then update your stance if it changed.

Respond ONLY with valid JSON:
{{
  "message": "your reaction here",
  "updated_stance": "bullish/bearish/neutral/uncertain",
  "influenced_by": "name of who influenced you or null"
}}
"""
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
            )

            raw = response.choices[0].message.content.strip()
            result = json.loads(raw)

            sentiment_tracker[persona["id"]] = result["updated_stance"]

            message_entry = {
                "round": round_num,
                "persona_id": persona["id"],
                "name": persona["name"],
                "type": persona["type"],
                "message": result["message"],
                "stance": result["updated_stance"],
                "influenced_by": result.get("influenced_by")
            }

            messages_log.append(message_entry)

            influenced = f" (influenced by {result['influenced_by']})" if result.get("influenced_by") else ""
            print(f"  [{result['updated_stance'].upper()}]{influenced} {persona['name']}: {result['message']}")

        print()

    return messages_log


def calculate_sentiment(messages_log: list) -> dict:
    final_round = max(m["round"] for m in messages_log)
    final_messages = [m for m in messages_log if m["round"] == final_round]

    counts = {"bullish": 0, "bearish": 0, "neutral": 0, "uncertain": 0}
    for m in final_messages:
        stance = m["stance"]
        if stance in counts:
            counts[stance] += 1

    total = len(final_messages)
    percentages = {k: round((v / total) * 100) for k, v in counts.items()}

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
    headline = "Federal Reserve raises interest rates by 50 basis points as inflation hits 40-year high, sending SPY and QQQ lower"

    print("Building knowledge graph...")
    data = extract_entities_and_relations(headline)
    G = build_graph(data)

    print("Generating personas...")
    personas = generate_personas(G, data, num_personas=5)

    messages_log = run_simulation(personas, headline, rounds=3)
    sentiment = calculate_sentiment(messages_log)
    print_report(sentiment, headline)