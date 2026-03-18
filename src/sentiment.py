import requests
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_google_news(query: str) -> dict:
    """
    Fetch recent news headlines from Google News RSS.
    Completely free, no API key needed.
    """
    try:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        r   = requests.get(url, headers=HEADERS, timeout=15)
        root = ET.fromstring(r.content)

        headlines = []
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title", "")
            pub   = item.findtext("pubDate", "")
            if title:
                headlines.append({"title": title, "date": pub})

        return {
            "source":    "google_news",
            "query":     query,
            "count":     len(headlines),
            "headlines": headlines,
        }
    except Exception as e:
        return {"source": "google_news", "query": query, "count": 0, "headlines": [], "error": str(e)}


def get_reddit_mentions(token_name: str, symbol: str) -> dict:
    """
    Search Reddit for recent mentions of the token.
    Uses Reddit's free JSON API.
    """
    try:
        query = f"{token_name} OR {symbol} crypto"
        url   = f"https://www.reddit.com/search.json?q={quote(query)}&sort=new&limit=10&t=day"
        r     = requests.get(url, headers=HEADERS, timeout=15)
        data  = r.json()

        posts = []
        for post in data.get("data", {}).get("children", []):
            d = post.get("data", {})
            posts.append({
                "title":  d.get("title", ""),
                "score":  d.get("score", 0),
                "sub":    d.get("subreddit", ""),
                "comments": d.get("num_comments", 0),
            })

        total_score    = sum(p["score"] for p in posts)
        total_comments = sum(p["comments"] for p in posts)

        return {
            "source":         "reddit",
            "post_count":     len(posts),
            "total_upvotes":  total_score,
            "total_comments": total_comments,
            "posts":          posts[:5],
        }
    except Exception as e:
        return {"source": "reddit", "post_count": 0, "total_upvotes": 0, "total_comments": 0, "posts": [], "error": str(e)}


def get_coingecko_data(symbol: str) -> dict:
    """
    Fetch social + community data from CoinGecko free API.
    """
    try:
        # Search for the coin first
        search_url = f"https://api.coingecko.com/api/v3/search?query={quote(symbol)}"
        r          = requests.get(search_url, headers=HEADERS, timeout=15)
        results    = r.json().get("coins", [])

        if not results:
            return {"source": "coingecko", "found": False}

        coin_id = results[0]["id"]
        time.sleep(1)

        # Get detailed data
        detail_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=false&community_data=true&developer_data=false"
        r2         = requests.get(detail_url, headers=HEADERS, timeout=15)
        coin       = r2.json()

        community  = coin.get("community_data", {})
        sentiment  = coin.get("sentiment_votes_up_percentage", 0) or 0

        return {
            "source":              "coingecko",
            "found":               True,
            "coin_id":             coin_id,
            "sentiment_up_pct":    sentiment,
            "twitter_followers":   community.get("twitter_followers", 0) or 0,
            "reddit_subscribers":  community.get("reddit_subscribers", 0) or 0,
            "reddit_active":       community.get("reddit_accounts_active_48h", 0) or 0,
            "telegram_users":      community.get("telegram_channel_user_count", 0) or 0,
            "coingecko_rank":      coin.get("coingecko_rank", 999) or 999,
        }
    except Exception as e:
        return {"source": "coingecko", "found": False, "error": str(e)}


def score_narrative(token_name: str, headlines: list) -> dict:
    """
    Check if the token's name/theme matches any current trending narratives.
    The idea: a coin called 'World Peace' on a day of major peace talks = narrative match.
    """
    # Current hot narrative keywords — update these manually as trends change
    hot_narratives = [
        "ai", "artificial intelligence", "agent",
        "meme", "dog", "cat", "pepe",
        "rwa", "real world asset",
        "depin", "infrastructure",
        "gaming", "game",
        "trump", "election", "political",
        "elon", "tesla", "spacex",
        "bitcoin", "btc", "halving",
        "solana", "sol",
    ]

    name_lower = token_name.lower()
    matched    = [n for n in hot_narratives if n in name_lower]

    # Also check if any headlines mention the token name
    headline_hits = sum(
        1 for h in headlines
        if token_name.lower() in h.get("title", "").lower()
    )

    narrative_score = min(100, (len(matched) * 20) + (headline_hits * 15))

    return {
        "matched_narratives": matched,
        "headline_hits":      headline_hits,
        "narrative_score":    narrative_score,
    }


def get_full_sentiment(token_name: str, symbol: str) -> dict:
    """
    Master function — runs all sentiment sources and returns a combined report.
    """
    print(f"    Fetching sentiment for {token_name}...")

    news     = get_google_news(f"{token_name} {symbol} crypto coin")
    time.sleep(0.5)
    reddit   = get_reddit_mentions(token_name, symbol)
    time.sleep(0.5)
    gecko    = get_coingecko_data(symbol)
    narrative = score_narrative(token_name, news.get("headlines", []))

    # Build overall sentiment score 0-100
    score = 0

    # News volume (max 25 pts)
    news_count = news.get("count", 0)
    score += min(25, news_count * 3)

    # Reddit activity (max 25 pts)
    reddit_posts = reddit.get("post_count", 0)
    score += min(25, reddit_posts * 5)

    # CoinGecko sentiment (max 25 pts)
    if gecko.get("found"):
        cg_sentiment = gecko.get("sentiment_up_pct", 50)
        score += int((cg_sentiment / 100) * 25)

    # Narrative match (max 25 pts)
    score += min(25, narrative.get("narrative_score", 0) // 4)

    score = min(100, score)

    return {
        "overall_sentiment_score": score,
        "news":                    news,
        "reddit":                  reddit,
        "coingecko":               gecko,
        "narrative":               narrative,
        "summary": _build_summary(news, reddit, gecko, narrative, score),
    }


def _build_summary(news, reddit, gecko, narrative, score) -> str:
    parts = []

    if news.get("count", 0) > 5:
        parts.append(f"High news volume ({news['count']} articles)")
    elif news.get("count", 0) > 0:
        parts.append(f"{news['count']} recent news articles")
    else:
        parts.append("No recent news found")

    if reddit.get("post_count", 0) > 3:
        parts.append(f"Active Reddit buzz ({reddit['post_count']} posts, {reddit['total_upvotes']} upvotes)")
    elif reddit.get("post_count", 0) > 0:
        parts.append(f"Low Reddit activity ({reddit['post_count']} posts)")
    else:
        parts.append("No Reddit mentions")

    if gecko.get("found"):
        pct = gecko.get("sentiment_up_pct", 0)
        parts.append(f"CoinGecko sentiment {pct:.0f}% bullish")

    if narrative.get("matched_narratives"):
        parts.append(f"Narrative match: {', '.join(narrative['matched_narratives'])}")

    return " | ".join(parts)