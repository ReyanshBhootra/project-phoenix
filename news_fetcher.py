import yfinance as yf
from datetime import datetime


def get_latest_news(ticker: str = "SPY", max_articles: int = 5) -> list:
    fallback_tickers = [ticker, "QQQ", "SPY", "AAPL"]

    for t in fallback_tickers:
        try:
            stock = yf.Ticker(t)
            news = stock.news
            if not news:
                continue

            articles = []
            for item in news[:max_articles]:
                content = item.get("content", {})
                title = content.get("title", "No title")
                summary = content.get("summary", "")
                pub_date = content.get("pubDate", "")
                provider = content.get("provider", {}).get("displayName", "Unknown")

                if title and title != "No title":
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "published": pub_date,
                        "source": provider,
                        "ticker": t
                    })

            if articles:
                return articles

        except Exception as e:
            print(f"Error fetching {t}: {e}")
            continue

    return []


def print_news(articles: list):
    print(f"\n--- LATEST MARKET NEWS ---")
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}] {article['title']}")
        print(f"    Source : {article['source']}")
        print(f"    Published: {article['published']}")
        if article['summary']:
            print(f"    Summary: {article['summary'][:150]}...")
    print(f"\n--- END OF NEWS ---\n")


if __name__ == "__main__":
    print("Fetching latest SPY news...\n")
    articles = get_latest_news("SPY", max_articles=5)
    print_news(articles)

    print("Fetching latest QQQ news...\n")
    articles = get_latest_news("QQQ", max_articles=3)
    print_news(articles)