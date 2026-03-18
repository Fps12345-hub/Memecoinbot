from src.sentiment import get_full_sentiment
import time
import schedule
from datetime import datetime
from src.token_fetcher import get_token_data
from src.rug_detector  import analyse_rug_risk
from src.scorer        import analyse_with_ai
from src.alerts        import send_alert, build_alert_message
from src.paper_trader  import log_signal, update_prices
from src.discoverer    import discover_tokens

# ── Your static watchlist (always scanned) ────────────────────────
WATCHLIST = []

# ── Filters ───────────────────────────────────────────────────────
MIN_LIQUIDITY    = 20_000
MAX_RUG_SCORE    = 50
MIN_CONFIDENCE   = 55
ALERT_ON_SIGNALS = ["BUY", "WATCH"]

# ── How often to run each scan type ──────────────────────────────
WATCHLIST_INTERVAL  = 5    # every 5 mins
DISCOVERY_INTERVAL  = 15   # every 15 mins

# ── Dedup tracker ─────────────────────────────────────────────────
alerted_this_session = set()


def scan_token(address: str, source: str = "watchlist"):
    """Scan one token through the full pipeline."""
    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [{source}] Scanning {address[:12]}...")

        data = get_token_data(address)
        if "error" in data:
            print(f"  Skipped — {data['error']}")
            return

        name      = data.get("name", "Unknown")
        liquidity = data.get("liquidity_usd", 0) or 0
        print(f"  Token: {name} | Liquidity: ${liquidity:,.0f}")

        if liquidity < MIN_LIQUIDITY:
            print(f"  Skipped — liquidity too low")
            return

        rug_result = analyse_rug_risk(data)
        rug_score  = rug_result.get("risk_score", 100)
        if rug_score > MAX_RUG_SCORE:
            print(f"  Skipped — rug score {rug_score}/100")
            return

        sentiment  = get_full_sentiment(
            data.get("name", ""),
            data.get("symbol", "")
        )
        print(f"  Sentiment score: {sentiment.get('overall_sentiment_score', 0)}/100")
        ai_result  = analyse_with_ai(data, rug_result, sentiment)
        signal     = ai_result.get("signal", "UNKNOWN")
        confidence = ai_result.get("confidence", 0)
        print(f"  Signal: {signal} | Confidence: {confidence} | Rug: {rug_score}")

        if signal not in ALERT_ON_SIGNALS:
            print(f"  Skipped — signal is {signal}")
            return

        if confidence < MIN_CONFIDENCE:
            print(f"  Skipped — confidence {confidence}")
            return

        alert_key = f"{address}:{signal}"
        if alert_key in alerted_this_session:
            print(f"  Skipped — already alerted")
            return

        print(f"  ✅ ALERT — {signal} {name} [{source.upper()}]")
        message = build_alert_message(data, rug_result, ai_result)
        send_alert(message)
        log_signal(data, rug_result, ai_result)
        alerted_this_session.add(alert_key)

    except Exception as e:
        print(f"  Error: {e}")


def scan_watchlist():
    """Scan your fixed watchlist tokens."""
    print(f"\n{'─'*40}")
    print(f"📋 WATCHLIST SCAN — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'─'*40}")
    for address in WATCHLIST:
        scan_token(address, source="watchlist")
        time.sleep(2)
    update_prices()
    print(f"\nNext watchlist scan in {WATCHLIST_INTERVAL} mins...")


def scan_discovered():
    """Discover and scan new tokens automatically."""
    print(f"\n{'─'*40}")
    print(f"🤖 AUTO-DISCOVERY SCAN — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'─'*40}")

    tokens = discover_tokens()

    if not tokens:
        print("  No tokens discovered this round.")
        return

    print(f"  Scanning {len(tokens)} discovered tokens...\n")
    passed  = 0
    skipped = 0

    for address in tokens:
        # Skip if already in watchlist
        if address in WATCHLIST:
            continue
        scan_token(address, source="discovery")
        time.sleep(1.5)  # be kind to the API
        skipped += 1

    update_prices()
    print(f"\nNext discovery scan in {DISCOVERY_INTERVAL} mins...")


def run_monitor():
    """Start the full monitoring loop."""
    print("""
╔══════════════════════════════════════╗
  🤖 Meme Coin AI Agent — RUNNING
╚══════════════════════════════════════╝""")
    print(f"  Watchlist  : {len(WATCHLIST)} tokens (every {WATCHLIST_INTERVAL} mins)")
    print(f"  Discovery  : auto-finds new tokens (every {DISCOVERY_INTERVAL} mins)")
    print(f"  Filters    : liq>${MIN_LIQUIDITY:,} | rug<{MAX_RUG_SCORE} | conf>{MIN_CONFIDENCE}")
    print(f"  Alerts on  : {ALERT_ON_SIGNALS}")
    print(f"\n  Press Ctrl+C to stop\n")

    # Run both immediately on start
    scan_watchlist()
    scan_discovered()

    # Schedule repeating scans
    schedule.every(WATCHLIST_INTERVAL).minutes.do(scan_watchlist)
    schedule.every(DISCOVERY_INTERVAL).minutes.do(scan_discovered)

    while True:
        schedule.run_pending()
        time.sleep(30)