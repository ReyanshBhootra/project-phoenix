import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockLatestQuoteRequest, StockSnapshotRequest
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)


def get_realtime_quote(ticker: str) -> dict:
    try:
        request = StockLatestQuoteRequest(symbol_or_symbols=ticker.upper())
        quote = client.get_stock_latest_quote(request)
        q = quote[ticker.upper()]
        return {
            "ticker": ticker.upper(),
            "ask": float(q.ask_price),
            "bid": float(q.bid_price),
            "mid": round((float(q.ask_price) + float(q.bid_price)) / 2, 2),
        }
    except Exception as e:
        print(f"Alpaca quote error: {e}")
        return None


def get_snapshot(ticker: str) -> dict:
    try:
        request = StockSnapshotRequest(symbol_or_symbols=ticker.upper())
        snap = client.get_stock_snapshot(request)
        s = snap[ticker.upper()]

        daily = s.daily_bar
        prev = s.previous_daily_bar
        quote = s.latest_quote

        price = round((float(quote.ask_price) + float(quote.bid_price)) / 2, 2)
        prev_close = float(prev.close) if prev else None
        change = round(price - prev_close, 2) if prev_close else None
        change_pct = round((change / prev_close) * 100, 2) if prev_close and change else None

        return {
            "ticker": ticker.upper(),
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "volume": int(daily.volume) if daily else None,
            "open": float(daily.open) if daily else None,
            "high": float(daily.high) if daily else None,
            "low": float(daily.low) if daily else None,
            "vwap": float(daily.vwap) if daily else None,
        }
    except Exception as e:
        print(f"Alpaca snapshot error: {e}")
        return None


if __name__ == "__main__":
    print("Testing Alpaca real-time data...")
    quote = get_realtime_quote("SPY")
    print(f"SPY quote: {quote}")
    snap = get_snapshot("SPY")
    print(f"SPY snapshot: {snap}")