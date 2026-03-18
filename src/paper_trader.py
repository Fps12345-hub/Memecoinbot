import os
import json
import time
from datetime import datetime, timezone
from src.token_fetcher import get_token_data

# ── File where all trades are saved ───────────────────────────────
TRADES_FILE = os.path.expanduser("~/memecoin-agent/paper_trades.json")


def load_trades() -> list:
    """Load existing paper trades from disk."""
    if not os.path.exists(TRADES_FILE):
        return []
    try:
        with open(TRADES_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_trades(trades: list):
    """Save trades to disk."""
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)


def log_signal(token_data: dict, rug_result: dict, ai_result: dict):
    """
    Log a new signal as a paper trade entry.
    Called automatically whenever the monitor fires an alert.
    """
    trades = load_trades()

    entry = {
        "id":             len(trades) + 1,
        "logged_at":      datetime.now(tz=timezone.utc).isoformat(),
        "name":           token_data.get("name"),
        "symbol":         token_data.get("symbol"),
        "address":        token_data.get("address"),
        "signal":         ai_result.get("signal"),
        "confidence":     ai_result.get("confidence"),
        "entry_risk":     ai_result.get("entry_risk"),
        "rug_score":      rug_result.get("risk_score"),
        "price_at_entry": float(token_data.get("price_usd", 0) or 0),
        "mcap_at_entry":  token_data.get("market_cap", 0),
        "liq_at_entry":   token_data.get("liquidity_usd", 0),
        "summary":        ai_result.get("summary"),
        "price_1h":       None,
        "price_6h":       None,
        "price_24h":      None,
        "result_1h":      None,
        "result_6h":      None,
        "result_24h":     None,
        "status":         "open",
    }

    trades.append(entry)
    save_trades(trades)
    print(f"  📝 Paper trade logged — #{entry['id']} {entry['name']} @ ${entry['price_at_entry']}")
    return entry


def update_prices():
    """
    Check all open trades and update their 1h/6h/24h prices.
    Call this on every monitor scan.
    """
    trades = load_trades()
    updated = False

    for trade in trades:
        if trade["status"] == "closed":
            continue

        logged_at    = datetime.fromisoformat(trade["logged_at"])
        now          = datetime.now(tz=timezone.utc)
        hours_passed = (now - logged_at).total_seconds() / 3600
        address      = trade["address"]
        entry_price  = trade["price_at_entry"]

        if entry_price <= 0:
            continue

        # Fetch current price
        try:
            current_data  = get_token_data(address)
            current_price = float(current_data.get("price_usd", 0) or 0)
        except Exception:
            continue

        if current_price <= 0:
            continue

        change_pct = round(((current_price - entry_price) / entry_price) * 100, 2)

        # Update 1h result
        if hours_passed >= 1 and trade["price_1h"] is None:
            trade["price_1h"]  = current_price
            trade["result_1h"] = change_pct
            updated = True
            print(f"  Updated 1h result for {trade['name']}: {change_pct:+.1f}%")

        # Update 6h result
        if hours_passed >= 6 and trade["price_6h"] is None:
            trade["price_6h"]  = current_price
            trade["result_6h"] = change_pct
            updated = True
            print(f"  Updated 6h result for {trade['name']}: {change_pct:+.1f}%")

        # Update 24h result and close trade
        if hours_passed >= 24 and trade["price_24h"] is None:
            trade["price_24h"]  = current_price
            trade["result_24h"] = change_pct
            trade["status"]     = "closed"
            updated = True
            print(f"  Closed 24h trade for {trade['name']}: {change_pct:+.1f}%")

    if updated:
        save_trades(trades)


def print_scorecard():
    """Print a full performance report of all paper trades."""
    trades = load_trades()

    if not trades:
        print("\nNo paper trades logged yet.")
        return

    closed = [t for t in trades if t["status"] == "closed"]
    open_t = [t for t in trades if t["status"] == "open"]

    print(f"""
{'═'*60}
  PAPER TRADING SCORECARD
{'═'*60}
  Total signals : {len(trades)}
  Closed trades : {len(closed)}
  Open trades   : {len(open_t)}
""")

    if closed:
        wins_24h   = [t for t in closed if (t["result_24h"] or 0) > 0]
        losses_24h = [t for t in closed if (t["result_24h"] or 0) <= 0]
        avg_24h    = sum(t["result_24h"] or 0 for t in closed) / len(closed)

        print(f"  24h Win Rate  : {len(wins_24h)}/{len(closed)} ({round(len(wins_24h)/len(closed)*100)}%)")
        print(f"  Avg 24h Return: {avg_24h:+.1f}%")
        print(f"  Best trade    : {max(closed, key=lambda t: t['result_24h'] or 0)['name']} ({max(t['result_24h'] or 0 for t in closed):+.1f}%)")
        print(f"  Worst trade   : {min(closed, key=lambda t: t['result_24h'] or 0)['name']} ({min(t['result_24h'] or 0 for t in closed):+.1f}%)")

    print(f"\n{'─'*60}")
    print(f"  {'#':<4} {'Token':<22} {'Signal':<7} {'Conf':<6} {'1h':>6} {'6h':>6} {'24h':>7} {'Status'}")
    print(f"{'─'*60}")

    for t in trades:
        r1h  = f"{t['result_1h']:+.1f}%"  if t['result_1h']  is not None else "..."
        r6h  = f"{t['result_6h']:+.1f}%"  if t['result_6h']  is not None else "..."
        r24h = f"{t['result_24h']:+.1f}%" if t['result_24h'] is not None else "..."

        icon = "✅" if (t.get("result_24h") or 0) > 0 else "❌" if t["status"] == "closed" else "⏳"

        print(f"  {t['id']:<4} {t['name']:<22} {t['signal']:<7} {t['confidence']:<6} {r1h:>6} {r6h:>6} {r24h:>7} {icon}")

    print(f"{'═'*60}\n")