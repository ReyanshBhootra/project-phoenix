import yfinance as yf
from datetime import datetime, timedelta
import re

MARKET_IMPACT_KEYWORDS = [
    "fed", "federal reserve", "rate", "inflation", "cpi", "gdp", "jobs",
    "earnings", "revenue", "guidance", "merger", "acquisition", "bankruptcy",
    "tariff", "trade", "sanction", "crash", "rally", "correction", "selloff",
    "recession", "interest rate", "powell", "sec", "investigation", "fraud",
    "beat", "miss", "downgrade", "upgrade", "layoff", "strike", "ipo"
]

NOISE_KEYWORDS = [
    "10 years ago", "history of", "did you know", "all-time", "anniversary",
    "throwback", "look back", "years ago", "what if", "hypothetical"
]


def score_headline(article: dict, ticker: str) -> float:
    title = article.get("title", "").lower()
    summary = article.get("summary", "").lower()
    text = title + " " + summary

    score = 0.0

    # Relevance to ticker
    if ticker.lower() in text:
        score += 3.0

    # Market impact keywords
    for kw in MARKET_IMPACT_KEYWORDS:
        if kw in text:
            score += 1.0

    # Noise penalty
    for kw in NOISE_KEYWORDS:
        if kw in text:
            score -= 3.0

    # Recency bonus -- today vs yesterday
    pub_date = article.get("published", "")
    if pub_date:
        try:
            # yfinance returns ISO format
            pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            hours_old = (datetime.now().astimezone() - pub_dt).total_seconds() / 3600
            if hours_old < 12:
                score += 2.0
            elif hours_old < 24:
                score += 1.0
        except:
            pass

    return score


def get_all_news(ticker: str, max_articles: int = 12) -> list:
    """
    Fetch ALL news from today and yesterday for the ticker.
    Score by relevance and market impact. Return top max_articles.
    """
    all_articles = []
    seen_titles = set()

    # Primary ticker + related tickers for broader context
    tickers_to_try = [ticker]

    # Add sector ETFs for context
    if ticker in ["SPY", "QQQ", "IWM", "VTI"]:
        tickers_to_try += ["SPY", "QQQ"]
    else:
        tickers_to_try += [ticker, "SPY"]

    # Deduplicate
    tickers_to_try = list(dict.fromkeys(tickers_to_try))

    for t in tickers_to_try:
        try:
            stock = yf.Ticker(t)
            news = stock.news
            if not news:
                continue

            for item in news:
                content = item.get("content", {})
                title = content.get("title", "").strip()
                summary = content.get("summary", "")
                pub_date = content.get("pubDate", "")
                provider = content.get("provider", {}).get("displayName", "Unknown")

                if not title or title in seen_titles:
                    continue

                seen_titles.add(title)

                article = {
                    "title": title,
                    "summary": summary,
                    "published": pub_date,
                    "source": provider,
                    "ticker": t,
                    "score": 0.0
                }

                # Score the headline
                article["score"] = score_headline(article, ticker)

                # Only keep positive scoring articles
                if article["score"] > 0:
                    all_articles.append(article)

        except Exception as e:
            print(f"Error fetching {t}: {e}")
            continue

    # Sort by score descending
    all_articles.sort(key=lambda x: x["score"], reverse=True)

    # Return top articles
    top = all_articles[:max_articles]

    print(f"[NewsFilter] Fetched {len(all_articles)} articles, keeping top {len(top)} for {ticker}")
    for a in top:
        print(f"  [score={a['score']:.1f}] {a['title'][:80]}")

    return top


def get_latest_news(ticker: str = "SPY", max_articles: int = 5) -> list:
    """Legacy function kept for compatibility."""
    return get_all_news(ticker, max_articles)


def print_news(articles: list):
    print(f"\n--- LATEST MARKET NEWS ({len(articles)} articles) ---")
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}] {article['title']}")
        print(f"    Source   : {article['source']}")
        print(f"    Published: {article['published']}")
        print(f"    Score    : {article['score']:.1f}")
        if article['summary']:
            print(f"    Summary  : {article['summary'][:150]}...")
    print(f"\n--- END OF NEWS ---\n")


if __name__ == "__main__":
    print("Fetching ALL SPY news from today + yesterday...\n")
    articles = get_all_news("SPY", max_articles=12)
    print_news(articles)