import os
import json
import time
from datetime import datetime, timedelta
import yfinance as yf
from dotenv import load_dotenv
from news_fetcher import get_latest_news
from graph_builder import extract_entities_and_relations, build_graph
from persona_generator import generate_personas
from simulation import run_simulation, calculate_sentiment

load_dotenv()


def get_price_movement(ticker: str, date_str: str, days_after: int = 1) -> dict:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="60d")

        if hist.empty:
            return None

        hist.index = hist.index.tz_localize(None) if hist.index.tz is not None else hist.index
        hist.index = hist.index.normalize()

        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        dates = [d.to_pydatetime() for d in hist.index]

        base_date = None
        for d in dates:
            if d >= target_date:
                base_date = d
                break

        if not base_date:
            base_date = dates[-2]

        base_idx = dates.index(base_date)
        future_idx = min(base_idx + days_after, len(dates) - 1)

        if future_idx == base_idx:
            open_price = hist.loc[hist.index[base_idx], "Open"]
            close_price = hist.loc[hist.index[base_idx], "Close"]
            pct_change = ((close_price - open_price) / open_price) * 100
            base_price = float(open_price)
            future_price = float(close_price)
            future_date = str(dates[base_idx].date()) + " (close)"
        else:
            base_price = float(hist.loc[hist.index[base_idx], "Close"])
            future_price = float(hist.loc[hist.index[future_idx], "Close"])
            pct_change = ((future_price - base_price) / base_price) * 100
            future_date = str(dates[future_idx].date())

        actual_direction = "bullish" if pct_change > 0.3 else "bearish" if pct_change < -0.3 else "neutral"

        return {
            "base_date": str(dates[base_idx].date()),
            "future_date": future_date,
            "base_price": round(base_price, 2),
            "future_price": round(future_price, 2),
            "pct_change": round(pct_change, 2),
            "actual_direction": actual_direction
        }

    except Exception as e:
        print(f"Error getting price movement: {e}")
        return None


def run_backtest(ticker: str = "SPY", num_articles: int = 3, num_personas: int = 3, rounds: int = 2):
    print(f"\n{'='*60}")
    print(f"  PROJECT PHOENIX -- BACKTESTER")
    print(f"  Ticker: {ticker} | Articles: {num_articles}")
    print(f"{'='*60}\n")

    print(f"Fetching news articles for {ticker}...")
    articles = get_latest_news(ticker, max_articles=num_articles)

    if not articles:
        print("No articles found.")
        return

    results = []
    correct = 0
    total = 0

    for i, article in enumerate(articles):
        print(f"\n[{i+1}/{len(articles)}] Processing: {article['title'][:60]}...")

        headline = article["title"]
        if article.get("summary"):
            headline = headline + ". " + article["summary"][:150]

        pub_date = article.get("published", "")
        if pub_date:
            try:
                if "T" in pub_date:
                    date_str = pub_date.split("T")[0]
                else:
                    date_str = datetime.now().strftime("%Y-%m-%d")
            except:
                date_str = datetime.now().strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        try:
            print(f"  Building knowledge graph...")
            data = extract_entities_and_relations(headline)
            G = build_graph(data)

            print(f"  Generating {num_personas} personas...")
            personas = generate_personas(G, data, num_personas=num_personas, headline=headline)

            print(f"  Running simulation ({rounds} rounds)...")
            messages_log = run_simulation(personas, headline, rounds=rounds)
            sentiment = calculate_sentiment(messages_log)
            predicted = sentiment["dominant_sentiment"]

            print(f"  Getting price movement for {date_str}...")
            price_data = get_price_movement(ticker, date_str, days_after=1)

            if price_data:
                actual = price_data["actual_direction"]
                is_correct = predicted == actual or (
                    predicted in ["bullish", "bearish"] and actual == predicted
                )

                if actual != "neutral":
                    total += 1
                    if is_correct:
                        correct += 1

                result = {
                    "headline": article["title"][:80],
                    "source": article["source"],
                    "date": date_str,
                    "predicted": predicted,
                    "actual": actual,
                    "pct_change": price_data["pct_change"],
                    "correct": is_correct,
                    "base_price": price_data["base_price"],
                    "future_price": price_data["future_price"]
                }

                results.append(result)

                status = "✓ CORRECT" if is_correct else "✗ WRONG"
                print(f"\n  Headline : {article['title'][:60]}...")
                print(f"  Predicted: {predicted.upper()}")
                print(f"  Actual   : {actual.upper()} ({price_data['pct_change']:+.2f}%)")
                print(f"  Result   : {status}")
            else:
                print(f"  Could not get price data for {date_str}")

            time.sleep(1)

        except Exception as e:
            print(f"  Error processing article: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"  BACKTEST RESULTS -- {ticker}")
    print(f"{'='*60}")

    if total > 0:
        accuracy = (correct / total) * 100
        print(f"\n  Accuracy : {correct}/{total} = {accuracy:.1f}%")
    else:
        print(f"\n  No directional predictions to evaluate")

    print(f"\n  Detailed Results:")
    print(f"  {'Headline':<45} {'Pred':<10} {'Actual':<10} {'Change':<10} {'Result'}")
    print(f"  {'-'*85}")

    for r in results:
        status = "✓" if r["correct"] else "✗"
        print(f"  {r['headline'][:44]:<45} {r['predicted']:<10} {r['actual']:<10} {r['pct_change']:>+6.2f}%   {status}")

    print(f"\n{'='*60}\n")

    return {
        "ticker": ticker,
        "total_tested": total,
        "correct": correct,
        "accuracy": round((correct / total * 100), 1) if total > 0 else 0,
        "results": results
    }

def manual_backtest(cases: list):
    print(f"\n{'='*60}")
    print(f"  PROJECT PHOENIX -- MANUAL BACKTEST")
    print(f"{'='*60}\n")

    results = []
    correct = 0
    total = 0

    for i, case in enumerate(cases):
        ticker = case["ticker"]
        headline = case["headline"]
        date_str = case["date"]
        num_personas = case.get("num_personas", 5)
        rounds = case.get("rounds", 3)

        print(f"\n[{i+1}/{len(cases)}] {ticker} -- {date_str}")
        print(f"  Headline: {headline[:70]}...")

        try:
            print(f"  Building knowledge graph...")
            data = extract_entities_and_relations(headline)
            G = build_graph(data)

            print(f"  Generating {num_personas} personas...")
            personas = generate_personas(G, data, num_personas=num_personas, headline=headline)

            print(f"  Running simulation ({rounds} rounds)...")
            messages_log = run_simulation(personas, headline, rounds=rounds)
            sentiment = calculate_sentiment(messages_log)
            predicted = sentiment["dominant_sentiment"]

            print(f"  Getting price movement for {date_str}...")
            price_data = get_price_movement(ticker, date_str, days_after=1)

            if price_data:
                actual = price_data["actual_direction"]

                if actual != "neutral":
                    total += 1
                    if predicted == actual:
                        correct += 1
                        is_correct = True
                    else:
                        is_correct = False
                else:
                    is_correct = predicted == "neutral"

                result = {
                    "ticker": ticker,
                    "headline": headline[:80],
                    "date": date_str,
                    "predicted": predicted,
                    "actual": actual,
                    "pct_change": price_data["pct_change"],
                    "base_price": price_data["base_price"],
                    "future_price": price_data["future_price"],
                    "correct": is_correct
                }

                results.append(result)

                status = "✓ CORRECT" if is_correct else "✗ WRONG"
                print(f"\n  Predicted : {predicted.upper()}")
                print(f"  Actual    : {actual.upper()} ({price_data['pct_change']:+.2f}%)")
                print(f"  Price     : ${price_data['base_price']} → ${price_data['future_price']}")
                print(f"  Result    : {status}")

            time.sleep(2)

        except Exception as e:
            print(f"  Error: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"  MANUAL BACKTEST SUMMARY")
    print(f"{'='*60}")

    if total > 0:
        accuracy = (correct / total) * 100
        print(f"\n  Accuracy  : {correct}/{total} = {accuracy:.1f}%")
        print(f"  Correct   : {correct}")
        print(f"  Wrong     : {total - correct}")
    else:
        print(f"\n  No directional predictions to evaluate")

    print(f"\n  {'Ticker':<6} {'Date':<12} {'Headline':<40} {'Pred':<10} {'Actual':<10} {'Change':<8} Result")
    print(f"  {'-'*95}")
    for r in results:
        status = "✓" if r["correct"] else "✗"
        print(f"  {r['ticker']:<6} {r['date']:<12} {r['headline'][:39]:<40} {r['predicted']:<10} {r['actual']:<10} {r['pct_change']:>+6.2f}%  {status}")

    print(f"\n{'='*60}\n")

    return {
        "total_tested": total,
        "correct": correct,
        "accuracy": round((correct / total * 100), 1) if total > 0 else 0,
        "results": results
    }

if __name__ == "__main__":
    test_cases = [
        # Week of March 24-27 2026 (recent, we know outcomes)
        {
            "ticker": "SPY",
            "headline": "Federal Reserve raises interest rates by 50 basis points amid inflation concerns",
            "date": "2026-03-24",
            "num_personas": 5,
            "rounds": 3
        },
        {
            "ticker": "QQQ",
            "headline": "Nasdaq 100 enters correction territory falling more than 10% from recent highs as big tech stocks slide on AI spending concerns",
            "date": "2026-03-25",
            "num_personas": 5,
            "rounds": 3
        },
        {
            "ticker": "SPY",
            "headline": "US markets drop sharply as new tariff announcements spark recession fears among investors",
            "date": "2026-03-26",
            "num_personas": 5,
            "rounds": 3
        },
        {
            "ticker": "QQQ",
            "headline": "Big tech stocks slide as geopolitical tensions rise and AI spending concerns weigh on market sentiment",
            "date": "2026-03-27",
            "num_personas": 5,
            "rounds": 3
        },
        # February 2026
        {
            "ticker": "QQQ",
            "headline": "Nvidia earnings disappoint investors as AI chip demand growth slows sending tech stocks lower",
            "date": "2026-02-18",
            "num_personas": 5,
            "rounds": 3
        },
        {
            "ticker": "SPY",
            "headline": "Markets rally as Fed signals potential pause in rate hikes citing cooling inflation data",
            "date": "2026-02-24",
            "num_personas": 5,
            "rounds": 3
        },
        # January 2026
        {
            "ticker": "SPY",
            "headline": "Strong jobs report beats expectations with 300000 jobs added sending stocks higher",
            "date": "2026-01-09",
            "num_personas": 5,
            "rounds": 3
        },
        {
            "ticker": "QQQ",
            "headline": "Apple misses revenue estimates as iPhone sales decline sending tech sector lower",
            "date": "2026-01-28",
            "num_personas": 5,
            "rounds": 3
        },
        # December 2025
        {
            "ticker": "SPY",
            "headline": "Santa Claus rally continues as markets hit record highs on strong consumer spending data",
            "date": "2025-12-19",
            "num_personas": 5,
            "rounds": 3
        },
    ]

    manual_backtest(test_cases)