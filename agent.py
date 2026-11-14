import os, re, requests
import xml.etree.ElementTree as ET

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send(text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": text})

coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
bases = ["https://data-api.binance.vision", "https://api.binance.com", "https://api1.binance.com"]
feeds = ["https://www.coindesk.com/arc/outboundfeeds/rss/", "https://cointelegraph.com/rss"]
names = {"BTCUSDT": ["bitcoin", "btc"], "ETHUSDT": ["ethereum", "ether", "eth"],
         "SOLUSDT": ["solana", "sol"], "BNBUSDT": ["bnb"],
         "XRPUSDT": ["xrp", "ripple"], "DOGEUSDT": ["dogecoin", "doge"]}

def get_candles(symbol):
    for base in bases:
        try:
            r = requests.get(base + "/api/v3/klines",
                             params={"symbol": symbol, "interval": "5m", "limit": 30},
                             timeout=10)
            data = r.json()
            if isinstance(data, list):
                return data[:-1]
            print(symbol, "problem from", base, ":", data)
        except Exception as e:
            print(symbol, "could not reach", base, ":", e)
    return None

def analyze(candles, i):
    last = candles[i]
    prev = candles[i - 20:i]
    close = float(last[4])
    volume = float(last[5])
    avg_volume = sum(float(c[5]) for c in prev) / len(prev)
    recent_high = max(float(c[2]) for c in prev)
    ratio = volume / avg_volume
    return close, ratio, (close > recent_high and ratio > 2)

def get_headlines():
    titles = []
    for url in feeds:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            for item in root.iter("item"):
                t = item.find("title")
                if t is not None and t.text:
                    titles.append(t.text)
        except Exception:
            pass
    return titles

def news_for(coin, titles):
    found = [t for t in titles
             if any(re.search(r"\b" + w + r"\b", t.lower()) for w in names[coin])]
    return found[:3]

titles = None
for coin in coins:
    candles = get_candles(coin)
    if candles is None:
        print(coin, "- no data")
        continue
    close, ratio, flagged_now = analyze(candles, -1)
    _, _, flagged_before = analyze(candles, -2)
    print(coin, close, "volume", round(ratio, 1), "x", "FLAGGED" if flagged_now else "")
    if flagged_now and not flagged_before:
        if titles is None:
            titles = get_headlines()
        news = news_for(coin, titles)
        news_text = "\n".join("• " + n for n in news) if news else "No recent headlines found."
        send(f"🟢 {coin} possible bullish breakout\nPrice: {close}\nVolume: {ratio:.1f}x normal\n\nNews:\n{news_text}\n\nCheck the chart before acting.")
