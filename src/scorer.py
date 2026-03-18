import os
import time
import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    timeout=httpx.Timeout(60.0, connect=30.0)
)


def analyse_with_ai(token_data: dict, rug_result: dict, sentiment: dict = None) -> dict:

    token_summary = f"""
TOKEN: {token_data.get('name')} (${token_data.get('symbol')})
Address: {token_data.get('address')}

MARKET DATA:
- Price: ${token_data.get('price_usd')}
- Market Cap: ${token_data.get('market_cap', 0):,.0f}
- Liquidity: ${token_data.get('liquidity_usd', 0):,.0f}
- Volume (1h): ${token_data.get('volume_1h', 0):,.0f}
- Volume (24h): ${token_data.get('volume_24h', 0):,.0f}

PRICE MOVEMENT:
- 1h change:  {token_data.get('price_change_1h', 0)}%
- 6h change:  {token_data.get('price_change_6h', 0)}%
- 24h change: {token_data.get('price_change_24h', 0)}%

TRADING ACTIVITY:
- Buys (24h):  {token_data.get('buys_24h', 0)}
- Sells (24h): {token_data.get('sells_24h', 0)}
- DEX: {token_data.get('dex')}

RUG PULL ANALYSIS:
- Risk Score: {rug_result.get('risk_score')}/100
- Verdict: {rug_result.get('verdict')}
- Red Flags: {', '.join(rug_result.get('flags', [])) or 'None'}
- Warnings:  {', '.join(rug_result.get('warnings', [])) or 'None'}
- Positives: {', '.join(rug_result.get('positives', [])) or 'None'}
"""

    # Build sentiment block separately OUTSIDE the f-string
    sentiment_block = ""
    if sentiment:
        s = sentiment
        headlines_text = ""
        for h in s.get("news", {}).get("headlines", [])[:5]:
            headlines_text += f"- {h.get('title', '')}\n"

        sentiment_block = f"""
SENTIMENT & NARRATIVE:
- Overall sentiment score: {s.get('overall_sentiment_score', 0)}/100
- News articles (24h): {s.get('news', {}).get('count', 0)}
- Reddit posts (24h): {s.get('reddit', {}).get('post_count', 0)} posts, {s.get('reddit', {}).get('total_upvotes', 0)} upvotes
- Narrative matches: {', '.join(s.get('narrative', {}).get('matched_narratives', [])) or 'None'}
- Headline hits: {s.get('narrative', {}).get('headline_hits', 0)}
- CoinGecko sentiment: {s.get('coingecko', {}).get('sentiment_up_pct', 'N/A')}% bullish
- Summary: {s.get('summary', 'N/A')}

RECENT HEADLINES:
{headlines_text}"""

    prompt = f"""You are an expert meme coin analyst. Analyse this Solana meme coin and give a trading recommendation.

{token_summary}
{sentiment_block}

Respond in EXACTLY this format — no extra text:

SIGNAL: [BUY or WATCH or AVOID]
CONFIDENCE: [number 1-100]
ENTRY_RISK: [LOW or MEDIUM or HIGH or EXTREME]
SUMMARY: [2-3 sentences max explaining your call]
BULL_CASE: [1 sentence — best case scenario]
BEAR_CASE: [1 sentence — worst case scenario]
SUGGESTED_POSITION: [e.g. "1-2% of portfolio" or "Skip entirely"]
"""

    last_error = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            return parse_ai_response(raw)
        except Exception as e:
            last_error = e
            print(f"  Attempt {attempt + 1} failed, retrying in 5s...")
            time.sleep(5)

    return {
        "signal": "UNKNOWN",
        "confidence": 0,
        "entry_risk": "UNKNOWN",
        "summary": f"AI unavailable: {last_error}",
        "bull_case": "",
        "bear_case": "",
        "suggested_position": "Skip",
        "raw": ""
    }


def parse_ai_response(raw: str) -> dict:
    result = {
        "signal":             "UNKNOWN",
        "confidence":         0,
        "entry_risk":         "UNKNOWN",
        "summary":            "",
        "bull_case":          "",
        "bear_case":          "",
        "suggested_position": "",
        "raw":                raw,
    }
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("SIGNAL:"):
            result["signal"] = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("ENTRY_RISK:"):
            result["entry_risk"] = line.split(":", 1)[1].strip()
        elif line.startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
        elif line.startswith("BULL_CASE:"):
            result["bull_case"] = line.split(":", 1)[1].strip()
        elif line.startswith("BEAR_CASE:"):
            result["bear_case"] = line.split(":", 1)[1].strip()
        elif line.startswith("SUGGESTED_POSITION:"):
            result["suggested_position"] = line.split(":", 1)[1].strip()
    return result


def format_ai_report(token_data: dict, ai_result: dict) -> str:
    name   = token_data.get("name", "Unknown")
    symbol = token_data.get("symbol", "???")
    signal = ai_result.get("signal", "UNKNOWN")

    signal_icon = {"BUY": "🟢", "WATCH": "🟡", "AVOID": "🔴"}.get(signal, "⚪")
    risk_icon   = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "EXTREME": "💀"}.get(
                    ai_result.get("entry_risk", ""), "⚪")

    return f"""
{'█'*42}
  AI RECOMMENDATION — {name} (${symbol})
{'█'*42}

  {signal_icon}  SIGNAL   : {signal}
  {risk_icon}  RISK     : {ai_result.get('entry_risk')}
  📊  CONFIDENCE: {ai_result.get('confidence')}/100
  💼  POSITION  : {ai_result.get('suggested_position')}

  ANALYSIS:
  {ai_result.get('summary')}

  BULL CASE: {ai_result.get('bull_case')}
  BEAR CASE: {ai_result.get('bear_case')}

{'█'*42}
"""