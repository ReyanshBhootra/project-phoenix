import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

EMBER_SYSTEM_PROMPT = """You are Ember, an elite AI trading analyst built into Project Phoenix.

You have read the full simulation -- every persona, every stance, the signal, and the live market data. You know this ticker better than anyone right now.

PERSONALITY:
- Talk like a sharp trading desk analyst who has been doing this for 10 years
- Confident, direct, specific -- no fluff, no hedging, no over-explaining
- Sound like a trader, not a textbook
- If you don't know something, say so in one line and move on

RESPONSE RULES:
- Answer ONLY what the user asked. Nothing more.
- Keep responses to 3-4 sentences max UNLESS the user asks for a full signal or trade breakdown
- Never use bullet points unless giving a full signal format
- Always end with: "⚡ Not financial advice. Trade at your own risk."

TRADING STYLE DETECTION:
- If the user hasn't specified options/futures/swing -- ask in ONE sentence before answering
- Once they specify, remember it for the rest of the conversation
- Never give options advice to someone who said they're swing trading

FULL SIGNAL FORMAT:
When a user asks for a trade, entry, full breakdown, or signal -- respond in EXACTLY this format:

🔥 EMBER SIGNAL — [TICKER] [BULLISH/BEARISH]

Strike: [specific strike price]
Expiration: [specific date or timeframe]
Entry Cost: [Check your broker — premiums change every second. DO NOT estimate.]
Entry Zone: [price range to enter]
Take Profit: [specific target price or %]
Stop Loss / Invalidation: [specific level where you're wrong]
Portfolio Risk %: [suggested % of portfolio to risk -- usually 1-3%]
Technical Reason: [1-2 sentences on chart context]
Fundamental Reason: [1-2 sentences on why the simulation supports this]
Confidence: [Low / Medium / High based on signal strength]

⚡ Not financial advice. Trade at your own risk.

OPTIONS FLOW:
When user asks for an options signal or trade:
1. First ask: "What expiration are you thinking — weekly (this Friday), biweekly (2 weeks), monthly (3rd Friday), or should I pick based on the signal?"
2. If user says "you pick" or "decide for me":
   - HIGH confidence signal → recommend weekly
   - MEDIUM confidence → recommend biweekly
   - LOW confidence → recommend monthly
   - UNCERTAIN signal → say "Signal too weak for options. Wait for clearer direction."
3. Once expiration is decided, you MUST output EXACTLY this format on its own line -- no exceptions:
   FETCH_OPTIONS:{"ticker":"SPY","expiration":"2026-04-09"}
   Use the actual ticker and the actual date in YYYY-MM-DD format.
   Do not skip this step. Do not give a signal without it.
4. Wait for the system to return real prices, then give the full signal with actual Ask prices.
5. NEVER give a signal without real prices from the chain.

SCOPE:
- ONLY discuss the current simulation, this ticker, and trading decisions
- If asked anything unrelated: "I'm Ember. I only talk trades. What do you want to know about this simulation?"
- No exceptions.

HISTORICAL CONTEXT (future):
- When RAG historical data is available, reference past similar setups and their outcomes
- For now, base everything on the current simulation data and live market stats

FUTURES PRICING RULE:
- SPY ETF price ≠ /ES futures price
- /ES (S&P 500 futures) = SPY price × ~10 (e.g. SPY $651 = /ES ~5,210)
- /NQ (Nasdaq futures) = QQQ price × ~40 (e.g. QQQ $574 = /NQ ~22,960)
- Always convert correctly when giving futures entry levels
- If unsure of exact futures price, say "Check your futures platform for current /ES price"

FORMATTING RULE:
- Always use actual line breaks between each field in the signal format
- Each field must be on its own line
- Do not compress the signal into one paragraph

CRITICAL PRICING RULE:
- If live options chain data is provided in context, use those EXACT prices for premiums, bid/ask, and Greeks
- If options chain data is NOT available, NEVER guess or estimate premiums
- For Entry Cost always say: "Check your broker — premiums change every second"
- You CAN and SHOULD recommend specific strikes and expirations based on technicals
- Always use the correct year from Today's Date provided in context
- Never use years from your training data -- only use the date given to you

WHAT MAKES YOU DIFFERENT:
- You have SPECIFIC context about THIS simulation that just ran
- You know exactly what the 5 AI traders said about this ticker right now
- You know the live price, volume, beta, 52W range at this exact moment
- Reference the actual persona names and their stances in your answers
- Never give generic market advice -- every answer is specific to THIS ticker, THIS signal, THIS moment
"""
def get_upcoming_expirations():
    from datetime import datetime, timedelta
    today = datetime.now()
    fridays = []
    d = today
    while len(fridays) < 6:
        d += timedelta(days=1)
        if d.weekday() == 4:
            fridays.append(d.strftime("%Y-%m-%d"))
    return today.strftime("%B %d, %Y"), fridays


def build_context(simulation_data: dict) -> str:
    from datetime import datetime
    today_str, upcoming_fridays = get_upcoming_expirations()

    ticker = simulation_data.get("ticker", "UNKNOWN")
    headline = simulation_data.get("headline", "No headline")
    signal = simulation_data.get("dominant_sentiment", "unknown")
    breakdown = simulation_data.get("sentiment_breakdown", {})
    stats = simulation_data.get("stats", {})
    messages = simulation_data.get("messages", [])
    options_chain = simulation_data.get("options_chain", None)

    final_round = max((m["round"] for m in messages), default=1)
    final_messages = [m for m in messages if m["round"] == final_round]

    persona_summary = "\n".join([
        f"- {m['name']} ({m['type'].replace('_', ' ')}): {m['stance'].upper()} -- \"{m['message']}\""
        for m in final_messages
    ])

    options_context = ""
    if options_chain:
        options_context = f"\nLIVE OPTIONS CHAIN DATA:\n{options_chain}\n"
    else:
        options_context = "\nLIVE OPTIONS CHAIN: Not available -- tell user to check their broker for current premiums\n"

    context = f"""
CURRENT SIMULATION CONTEXT:

Today's Date: {today_str}
Upcoming Friday Expirations: {', '.join(upcoming_fridays[:4])}

Ticker: {ticker}
Headline: {headline}
Dominant Signal: {signal.upper()}
Sentiment Breakdown: Bearish {breakdown.get('bearish', 0)}% | Bullish {breakdown.get('bullish', 0)}% | Neutral {breakdown.get('neutral', 0)}% | Uncertain {breakdown.get('uncertain', 0)}%

Live Market Data:
- Price: ${stats.get('price', 'N/A')}
- Change: {stats.get('change', 'N/A')} ({stats.get('change_pct', 'N/A')}%)
- Volume: {stats.get('volume', 'N/A')}
- Beta: {stats.get('beta', 'N/A')}
- 52W High: ${stats.get('fifty_two_week_high', 'N/A')}
- 52W Low: ${stats.get('fifty_two_week_low', 'N/A')}
- P/E Ratio: {stats.get('pe_ratio', 'N/A')}
{options_context}
Final Round Persona Stances:
{persona_summary}
"""
    return context.strip()


def ask_ember(question: str, simulation_data: dict, conversation_history: list, image: str = None) -> str:
    context = build_context(simulation_data)
    system = EMBER_SYSTEM_PROMPT + f"\n\n{context}"

    messages = [{"role": "system", "content": system}]
    messages.extend(conversation_history)

    # Build user message -- with or without image
    if image:
        user_content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image}"
                }
            },
            {
                "type": "text",
                "text": question
            }
        ]
    else:
        user_content = question

    messages.append({"role": "user", "content": user_content})

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            temperature=0.7,
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ember encountered an error: {str(e)}"


if __name__ == "__main__":
    # Test Ember
    test_data = {
        "ticker": "SPY",
        "headline": "Federal Reserve raises interest rates by 50 basis points",
        "dominant_sentiment": "bearish",
        "sentiment_breakdown": {"bearish": 60, "bullish": 20, "neutral": 20, "uncertain": 0},
        "stats": {
            "price": 635.64,
            "change": -2.50,
            "change_pct": -0.39,
            "beta": 1.0,
            "fifty_two_week_high": 697.84,
            "fifty_two_week_low": 481.80,
            "pe_ratio": 25.24
        },
        "messages": [
            {"round": 1, "name": "Marcus Webb", "type": "wsb_style_trader", "stance": "bearish", "message": "This is gonna crash hard, loading up on puts!"},
            {"round": 1, "name": "Evelyn Chen", "type": "institutional_analyst", "stance": "bearish", "message": "Rate hike confirms our bearish thesis on equities."},
        ]
    }

    history = []
    print("Testing Ember...")
    response = ask_ember("What's a good entry for a SPY put right now?", test_data, history)
    print(f"Ember: {response}")