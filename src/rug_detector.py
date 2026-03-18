from datetime import datetime, timezone


def analyse_rug_risk(token_data: dict) -> dict:
    """
    Analyses a token for rug pull and dump signals.
    Returns a risk report with flags, score, and verdict.
    """

    flags = []       # Red flags found
    warnings = []    # Yellow warnings
    positives = []   # Green signals

    risk_score = 0   # 0 = safe, 100 = certain rug

    # ── Guard: if fetcher returned an error ──────────────────────────
    if "error" in token_data:
        return {
            "verdict":    "UNKNOWN",
            "risk_score": 100,
            "flags":      ["Could not fetch token data"],
            "warnings":   [],
            "positives":  [],
        }

    liquidity   = token_data.get("liquidity_usd", 0) or 0
    volume_24h  = token_data.get("volume_24h", 0)    or 0
    volume_1h   = token_data.get("volume_1h", 0)     or 0
    change_24h  = token_data.get("price_change_24h", 0) or 0
    change_1h   = token_data.get("price_change_1h", 0)  or 0
    buys        = token_data.get("buys_24h", 0)      or 0
    sells       = token_data.get("sells_24h", 0)     or 0
    market_cap  = token_data.get("market_cap", 0)    or 0
    created_at  = token_data.get("pair_created_at", 0) or 0

    # ── 1. Liquidity checks ──────────────────────────────────────────
    if liquidity < 5_000:
        flags.append(f"🔴 Extremely low liquidity (${liquidity:,.0f}) — easy rug")
        risk_score += 35
    elif liquidity < 20_000:
        flags.append(f"🔴 Very low liquidity (${liquidity:,.0f}) — high risk")
        risk_score += 20
    elif liquidity < 50_000:
        warnings.append(f"🟡 Low liquidity (${liquidity:,.0f}) — trade carefully")
        risk_score += 10
    else:
        positives.append(f"🟢 Healthy liquidity (${liquidity:,.0f})")

    # ── 2. Token age check ───────────────────────────────────────────
    if created_at > 0:
        created_dt  = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
        now         = datetime.now(tz=timezone.utc)
        age_hours   = (now - created_dt).total_seconds() / 3600

        if age_hours < 1:
            flags.append(f"🔴 Token is only {age_hours:.1f}h old — extremely new")
            risk_score += 30
        elif age_hours < 24:
            warnings.append(f"🟡 Token is only {age_hours:.1f}h old — very new")
            risk_score += 15
        elif age_hours < 72:
            warnings.append(f"🟡 Token is {age_hours:.1f}h old — still quite new")
            risk_score += 5
        else:
            days = age_hours / 24
            positives.append(f"🟢 Token is {days:.1f} days old")

    # ── 3. Volume checks ─────────────────────────────────────────────
    if volume_24h < 1_000:
        flags.append(f"🔴 Near-zero 24h volume (${volume_24h:,.0f}) — likely dead/fake")
        risk_score += 25
    elif volume_24h < 10_000:
        warnings.append(f"🟡 Low 24h volume (${volume_24h:,.0f})")
        risk_score += 10
    else:
        positives.append(f"🟢 Active 24h volume (${volume_24h:,.0f})")

    # ── 4. Price crash check ─────────────────────────────────────────
    if change_24h <= -60:
        flags.append(f"🔴 Price crashed {change_24h}% in 24h — likely already dumped")
        risk_score += 30
    elif change_24h <= -30:
        flags.append(f"🔴 Price down {change_24h}% in 24h — heavy selling")
        risk_score += 15
    elif change_24h <= -15:
        warnings.append(f"🟡 Price down {change_24h}% in 24h — watch closely")
        risk_score += 5
    elif change_24h >= 100:
        warnings.append(f"🟡 Price up {change_24h}% in 24h — possible pump in progress")
        risk_score += 10
    else:
        positives.append(f"🟢 Price change healthy ({change_24h}% in 24h)")

    # ── 5. Buy/sell ratio ────────────────────────────────────────────
    total_txns = buys + sells
    if total_txns > 0:
        ratio = buys / sells if sells > 0 else 99
        if ratio < 0.4:
            flags.append(f"🔴 Heavy sell pressure — only {buys} buys vs {sells} sells")
            risk_score += 20
        elif ratio < 0.7:
            warnings.append(f"🟡 More sells than buys ({buys} vs {sells})")
            risk_score += 8
        elif ratio > 2.0:
            positives.append(f"🟢 Strong buy pressure ({buys} buys vs {sells} sells)")
        else:
            positives.append(f"🟢 Balanced trading ({buys} buys / {sells} sells)")

    # ── 6. Market cap sanity ─────────────────────────────────────────
    if 0 < market_cap < 10_000:
        flags.append(f"🔴 Micro market cap (${market_cap:,.0f}) — extremely speculative")
        risk_score += 10
    elif market_cap > 1_000_000:
        positives.append(f"🟢 Established market cap (${market_cap:,.0f})")

    # ── Cap score at 100 ─────────────────────────────────────────────
    risk_score = min(risk_score, 100)

    # ── Verdict ──────────────────────────────────────────────────────
    if risk_score >= 70:
        verdict = "🔴 HIGH RISK — AVOID"
    elif risk_score >= 40:
        verdict = "🟡 MEDIUM RISK — CAUTION"
    else:
        verdict = "🟢 LOWER RISK — PROCEED WITH CARE"

    return {
        "verdict":    verdict,
        "risk_score": risk_score,
        "flags":      flags,
        "warnings":   warnings,
        "positives":  positives,
    }


def format_rug_report(token_data: dict, rug_result: dict) -> str:
    name   = token_data.get("name", "Unknown")
    symbol = token_data.get("symbol", "???")
    score  = rug_result["risk_score"]

    lines = [
        f"\n{'═'*42}",
        f"  RUG PULL ANALYSIS — {name} (${symbol})",
        f"{'═'*42}",
        f"  Risk Score : {score}/100",
        f"  Verdict    : {rug_result['verdict']}",
        "",
    ]

    if rug_result["flags"]:
        lines.append("  RED FLAGS:")
        for f in rug_result["flags"]:
            lines.append(f"    {f}")
        lines.append("")

    if rug_result["warnings"]:
        lines.append("  WARNINGS:")
        for w in rug_result["warnings"]:
            lines.append(f"    {w}")
        lines.append("")

    if rug_result["positives"]:
        lines.append("  POSITIVES:")
        for p in rug_result["positives"]:
            lines.append(f"    {p}")

    lines.append(f"{'═'*42}\n")
    return "\n".join(lines)