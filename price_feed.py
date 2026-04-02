import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockLatestQuoteRequest, StockSnapshotRequest
from dotenv import load_dotenv
import yfinance as yf

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

        mid = round((float(quote.ask_price) + float(quote.bid_price)) / 2, 2)
        bar_close = float(daily.close) if daily else None

        # Use bar close if mid price looks wrong (more than 5% off from bar close)
        if bar_close and mid and abs(mid - bar_close) / bar_close > 0.05:
            price = bar_close
        else:
            price = mid

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


def get_options_chain(ticker: str, expiration_date: str = None) -> str:
    try:
        import pandas as pd
        stock = yf.Ticker(ticker.upper())

        expirations = stock.options
        if not expirations:
            return None

        if expiration_date and expiration_date in expirations:
            exp = expiration_date
        else:
            exp = expirations[0]

        chain = stock.option_chain(exp)
        calls = chain.calls
        puts = chain.puts

        snap = get_snapshot(ticker)
        current_price = snap['price'] if snap else None

        result_lines = [f"Options chain for {ticker.upper()} expiring {exp}:"]

        if current_price:
            margin = current_price * 0.05
            calls_atm = calls[
                (calls['strike'] >= current_price - margin) &
                (calls['strike'] <= current_price + margin)
                ].head(8)
            puts_atm = puts[
                (puts['strike'] >= current_price - margin) &
                (puts['strike'] <= current_price + margin)
                ].head(8)
        else:
            calls_atm = calls.head(5)
            puts_atm = puts.head(5)

        result_lines.append(f"Current Price: ${current_price:.2f}")
        result_lines.append("\nCALLS (near ATM):")
        for _, row in calls_atm.iterrows():
            vol = int(row['volume']) if not pd.isna(row['volume']) else 0
            result_lines.append(
                f"  Strike ${row['strike']:.0f} | Bid ${row['bid']:.2f} Ask ${row['ask']:.2f} | "
                f"IV {row['impliedVolatility']:.1%} | Volume {vol}"
            )

        result_lines.append("\nPUTS (near ATM):")
        for _, row in puts_atm.iterrows():
            vol = int(row['volume']) if not pd.isna(row['volume']) else 0
            result_lines.append(
                f"  Strike ${row['strike']:.0f} | Bid ${row['bid']:.2f} Ask ${row['ask']:.2f} | "
                f"IV {row['impliedVolatility']:.1%} | Volume {vol}"
            )

        return "\n".join(result_lines)

    except Exception as e:
        print(f"Options chain error: {e}")
        return None

def get_options_chain_multi(ticker: str, num_expirations: int = 4) -> str:
    try:
        import pandas as pd
        from datetime import datetime
        stock = yf.Ticker(ticker.upper())
        expirations = stock.options
        if not expirations:
            return None

        friday_exps = [
            exp for exp in expirations
            if datetime.strptime(exp, "%Y-%m-%d").weekday() == 4
        ][:num_expirations]

        all_exps = list(dict.fromkeys(expirations[:2] + friday_exps))[:num_expirations+1]

        snap = get_snapshot(ticker)
        current_price = snap['price'] if snap else None

        result_lines = [f"Live Options Data for {ticker.upper()} | Current Price: ${current_price:.2f}\n"]

        for exp in all_exps:
            chain = stock.option_chain(exp)
            calls = chain.calls
            puts = chain.puts

            if current_price:
                margin = current_price * 0.03
                calls_atm = calls[
                    (calls['strike'] >= current_price - margin) &
                    (calls['strike'] <= current_price + margin)
                ].head(5)
                puts_atm = puts[
                    (puts['strike'] >= current_price - margin) &
                    (puts['strike'] <= current_price + margin)
                ].head(5)
            else:
                calls_atm = calls.head(5)
                puts_atm = puts.head(5)

            result_lines.append(f"--- Expiration: {exp} ---")
            result_lines.append("CALLS:")
            for _, row in calls_atm.iterrows():
                vol = int(row['volume']) if not pd.isna(row['volume']) else 0
                result_lines.append(
                    f"  Strike ${row['strike']:.0f} | Ask ${row['ask']:.2f} | "
                    f"IV {row['impliedVolatility']:.1%} | Vol {vol}"
                )
            result_lines.append("PUTS:")
            for _, row in puts_atm.iterrows():
                vol = int(row['volume']) if not pd.isna(row['volume']) else 0
                result_lines.append(
                    f"  Strike ${row['strike']:.0f} | Ask ${row['ask']:.2f} | "
                    f"IV {row['impliedVolatility']:.1%} | Vol {vol}"
                )
            result_lines.append("")

        return "\n".join(result_lines)

    except Exception as e:
        print(f"Options chain error: {e}")
        return None


if __name__ == "__main__":
    print("Testing Alpaca real-time data...")
    quote = get_realtime_quote("SPY")
    print(f"SPY quote: {quote}")
    snap = get_snapshot("SPY")
    print(f"SPY snapshot: {snap}")
