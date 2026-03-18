import requests
import time

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_trending_solana() -> list:
    """
    Fetch trending Solana tokens from DexScreener.
    Returns list of token addresses sorted by volume spike.
    """
    try:
        url = "https://api.dexscreener.com/token-boosts/top/v1"
        r   = requests.get(url, headers=HEADERS, timeout=20).json()
        
        addresses = []
        for item in r if isinstance(r, list) else []:
            if item.get("chainId") == "solana":
                addr = item.get("tokenAddress")
                if addr:
                    addresses.append(addr)
        
        print(f"  🔥 Found {len(addresses)} trending Solana tokens")
        return addresses[:20]  # top 20
    except Exception as e:
        print(f"  Trending fetch error: {e}")
        return []


def get_new_solana_tokens() -> list:
    """
    Fetch newest Solana token pairs from DexScreener.
    Returns list of token addresses just launched.
    """
    try:
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        r   = requests.get(url, headers=HEADERS, timeout=20).json()
        
        addresses = []
        for item in r if isinstance(r, list) else []:
            if item.get("chainId") == "solana":
                addr = item.get("tokenAddress")
                if addr:
                    addresses.append(addr)
        
        print(f"  🆕 Found {len(addresses)} new Solana tokens")
        return addresses[:20]
    except Exception as e:
        print(f"  New tokens fetch error: {e}")
        return []


def get_biggest_movers() -> list:
    """
    Fetch Solana tokens with biggest price moves right now.
    """
    try:
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        r   = requests.get(url, headers=HEADERS, timeout=20).json()
        pairs = r.get("pairs", [])

        # Filter Solana only, sort by 1h price change
        solana_pairs = [
            p for p in pairs
            if p.get("chainId") == "solana"
            and p.get("priceChange", {}).get("h1") is not None
            and p.get("volume", {}).get("h24", 0) > 10000
        ]

        # Sort by absolute 1h price change (biggest movers up or down)
        solana_pairs.sort(
            key=lambda p: abs(float(p.get("priceChange", {}).get("h1", 0) or 0)),
            reverse=True
        )

        addresses = [p["baseToken"]["address"] for p in solana_pairs[:20]]
        print(f"  📈 Found {len(addresses)} big movers")
        return addresses

    except Exception as e:
        print(f"  Movers fetch error: {e}")
        return []


def discover_tokens() -> list:
    """
    Master discovery function — pulls from all 3 sources,
    deduplicates, and returns a clean list of addresses to scan.
    """
    print("\n🔍 Discovering tokens...")

    trending = get_trending_solana()
    time.sleep(1)
    new      = get_new_solana_tokens()
    time.sleep(1)
    movers   = get_biggest_movers()

    # Combine and deduplicate
    seen      = set()
    all_tokens = []
    for addr in trending + new + movers:
        if addr and addr not in seen:
            seen.add(addr)
            all_tokens.append(addr)

    print(f"  ✅ {len(all_tokens)} unique tokens to scan")
    return all_tokens