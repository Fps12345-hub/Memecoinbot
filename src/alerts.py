import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()


async def _send(message: str):
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    await bot.send_message(
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        text=message,
        parse_mode="HTML"
    )


def send_alert(message: str):
    """Send a Telegram message (sync wrapper)."""
    try:
        asyncio.run(_send(message))
    except Exception as e:
        print(f"  Telegram error: {e}")


def build_alert_message(token_data: dict, rug_result: dict, ai_result: dict) -> str:
    signal = ai_result.get("signal", "UNKNOWN")
    name   = token_data.get("name", "Unknown")
    symbol = token_data.get("symbol", "???")

    signal_icon = {"BUY": "🟢", "WATCH": "🟡", "AVOID": "🔴"}.get(signal, "⚪")
    risk_icon   = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "EXTREME": "💀"}.get(
                    ai_result.get("entry_risk", ""), "⚪")

    return f"""{signal_icon} <b>{signal}: {name} (${symbol})</b>

📊 Confidence : {ai_result.get('confidence')}/100
{risk_icon} Risk       : {ai_result.get('entry_risk')}
🛡 Rug Score  : {rug_result.get('risk_score')}/100
💼 Position   : {ai_result.get('suggested_position')}

💰 Price      : ${token_data.get('price_usd')}
📈 Mcap       : ${token_data.get('market_cap', 0):,.0f}
💧 Liquidity  : ${token_data.get('liquidity_usd', 0):,.0f}

📝 {ai_result.get('summary')}

🐂 Bull: {ai_result.get('bull_case')}
🐻 Bear: {ai_result.get('bear_case')}

🔗 <a href="https://dexscreener.com/solana/{token_data.get('address')}">View on DexScreener</a>"""