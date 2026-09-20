import httpx

client = httpx.Client(timeout=10, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

# 1. Test Yahoo Finance API for ^NSEI (NIFTY 50), ^BSESN (SENSEX), ^NSEBANK (BANK NIFTY)
tickers = ["^NSEI", "^BSESN", "^NSEBANK", "^INDIAVIX"]
for ticker in tickers:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        res = client.get(url)
        if res.status_code == 200:
            data = res.json()
            meta = data["chart"]["result"][0]["meta"]
            px = meta.get("regularMarketPrice")
            prev = meta.get("previousClose") or meta.get("chartPreviousClose")
            chg = px - prev if px and prev else 0
            pct = (chg / prev * 100) if prev else 0
            print(f"{ticker}: Price={px}, PrevClose={prev}, Chg={chg:+.2f} ({pct:+.2f}%)")
        else:
            print(f"{ticker}: HTTP {res.status_code}")
    except Exception as e:
        print(f"{ticker} failed:", e)

# 2. Check if yfinance package is installed
try:
    import yfinance as yf
    print("yfinance is installed!")
except ImportError:
    print("yfinance not installed")
