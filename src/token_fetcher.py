import requests

def get_token_data(token_address: str) -> dict:
    """
    Fetches live market data for any Solana token from DexScreener.
    Returns a clean dict with all the key metrics we need.
    """
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        response = requests.get(url, timeout=30)
        data = response.json()

        if not data.get("pairs"):
            return {"error": "Token not found or has no trading pairs"}

        # Get the most liquid pair (first result = highest liquidity)
        pair = data["pairs"][0]

        return {
            "name":             pair.get("baseToken", {}).get("name", "Unknown"),
            "symbol":           pair.get("baseToken", {}).get("symbol", "???"),
            "address":          token_address,
            "price_usd":        pair.get("priceUsd", "0"),
            "liquidity_usd":    pair.get("liquidity", {}).get("usd", 0),
            "volume_1h":        pair.get("volume", {}).get("h1", 0),
            "volume_24h":       pair.get("volume", {}).get("h24", 0),
            "price_change_1h":  pair.get("priceChange", {}).get("h1", 0),
            "price_change_6h":  pair.get("priceChange", {}).get("h6", 0),
            "price_change_24h": pair.get("priceChange", {}).get("h24", 0),
            "buys_24h":         pair.get("txns", {}).get("h24", {}).get("buys", 0),
            "sells_24h":        pair.get("txns", {}).get("h24", {}).get("sells", 0),
            "market_cap":       pair.get("marketCap", 0),
            "dex":              pair.get("dexId", "unknown"),
            "pair_created_at":  pair.get("pairCreatedAt", 0),
        }

    except Exception as e:
        return {"error": str(e)}


def format_token_summary(data: dict) -> str:
    """
    Prints a clean readable summary of the token data.
    """
    if "error" in data:
        return f"Error: {data['error']}"

    buy_sell_ratio = (
        round(data['buys_24h'] / data['sells_24h'], 2)
        if data['sells_24h'] > 0 else "N/A"
    )

    return f"""
╔══════════════════════════════════════╗
  {data['name']} (${data['symbol']})
╚══════════════════════════════════════╝
  Price:          ${data['price_usd']}
  Market Cap:     ${data['market_cap']:,.0f}
  Liquidity:      ${data['liquidity_usd']:,.0f}

  Volume (1h):    ${data['volume_1h']:,.0f}
  Volume (24h):   ${data['volume_24h']:,.0f}

  Price Δ 1h:     {data['price_change_1h']}%
  Price Δ 6h:     {data['price_change_6h']}%
  Price Δ 24h:    {data['price_change_24h']}%

  Buys (24h):     {data['buys_24h']}
  Sells (24h):    {data['sells_24h']}
  Buy/Sell Ratio: {buy_sell_ratio}

  DEX:            {data['dex']}
"""