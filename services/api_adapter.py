from __future__ import annotations

import json
from collections import Counter
from typing import Any
from urllib.request import Request, urlopen

from flask import current_app

from services.risk_engine import (
    COMPANY_EXPOSURE_PROFILES,
    COMPANY_INDUSTRIES,
    COMPANY_NAMES,
)


BILL_TYPE_PATHS = {
    "hr": "house-bill",
    "s": "senate-bill",
    "hjres": "house-joint-resolution",
    "sjres": "senate-joint-resolution",
    "hconres": "house-concurrent-resolution",
    "sconres": "senate-concurrent-resolution",
    "hres": "house-resolution",
    "sres": "senate-resolution",
}


def risk_label(score: float) -> str:
    if score >= 55:
        return "High"
    if score >= 35:
        return "Moderate"
    return "Low"


def call_risk_api(tickers: list[str], analyze_impact: bool) -> dict[str, Any]:
    url = current_app.config["RISK_API_URL"]
    timeout = current_app.config["RISK_API_TIMEOUT"]
    payload = json.dumps({"tickers": tickers, "analyze_impact": analyze_impact}).encode("utf-8")
    request = Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def congress_bill_url(bill_type: str, bill_number: str | int, congress: int = 119) -> str:
    path = BILL_TYPE_PATHS.get(str(bill_type).lower())
    if not path or not bill_number:
        return ""
    return f"https://www.congress.gov/bill/{congress}th-congress/{path}/{bill_number}"


def pretty_company_name(ticker: str, api_company: str | None) -> str:
    if ticker in COMPANY_NAMES:
        return COMPANY_NAMES[ticker]
    if api_company:
        cleaned = api_company.strip()
        # API returns ALL CAPS like "APPLE INC."; title-case while preserving common suffixes
        return cleaned.title().replace("Inc.", "Inc.").replace("Llc", "LLC").replace("Plc", "PLC")
    return ticker


def adapt_bill(api_bill: dict[str, Any], stock_industry: str) -> dict[str, Any]:
    p_passage = float(api_bill.get("p_passage") or 0)
    materiality = float(api_bill.get("materiality") or 0)
    similarity = float(api_bill.get("similarity") or 0)
    effective_p = float(api_bill.get("effective_p") or 0)

    bill_industry = api_bill.get("industry") or stock_industry or "Unclassified"

    # Per-bill display score uses cosine similarity (0-1) scaled to 0-100. Above the
    # API's SIM_THRESHOLD (0.20) similarities span ~20-80, which lines up with the
    # existing Low/Moderate/High pill thresholds and gives the cards visible spread.
    score = round(similarity * 100, 1)
    base_score = round(p_passage * 100, 1)

    bill_type = (api_bill.get("bill_type") or "").lower()
    bill_number = api_bill.get("bill_number") or ""
    bill_id = f"{bill_type.upper()}.{bill_number}" if bill_type else str(bill_number)

    rationale = api_bill.get("impact_rationale") or ""
    impact_label = api_bill.get("impact")
    if impact_label and rationale:
        impact_text = f"{impact_label.capitalize()} - {rationale}"
    elif impact_label:
        impact_text = impact_label.capitalize()
    elif rationale:
        impact_text = rationale
    else:
        impact_text = (
            f"Effective probability {effective_p:.2%} "
            f"(passage {p_passage:.0%}, materiality {materiality:.2f}, similarity {similarity:.2f})"
        )

    match_reasons = [
        f"similarity {similarity:.2f}",
        f"materiality {materiality:.2f}",
        f"effective {effective_p:.3f}",
    ]
    if impact_label:
        match_reasons.append(f"impact: {impact_label}")

    return {
        "id": bill_id,
        "bill_key": f"{bill_type}-{bill_number}",
        "title": api_bill.get("title") or "Untitled bill",
        "risk_score": score,
        "risk_label": risk_label(score),
        "status": f"Passage probability {p_passage:.1%} - materiality {materiality:.2f}",
        "date": "",
        "impact": impact_text,
        "base_bill_risk": base_score,
        "stock_relevance": int(round(similarity * 100)),
        "match_reasons": match_reasons,
        "url": congress_bill_url(bill_type, bill_number),
        "policy_area": bill_industry,
        "subjects": [],
        "sponsors": [],
        "actions": [],
        "classification": {
            "industry": bill_industry,
            "confidence": round(similarity, 2),
            "method": "AWS LegisRisk API",
        },
    }


def stock_explanation(name: str, industry: str, top_bills: list[dict[str, Any]], note: str | None) -> str:
    if note:
        return f"{name}: {note}"
    if not top_bills:
        return f"{name} has no bills above the similarity threshold for its {industry} business right now."
    titles = [bill["title"] for bill in top_bills[:2] if bill.get("title")]
    if not titles:
        return f"{name} is exposed to active {industry} legislation."
    snippet = " / ".join(t[:90] for t in titles)
    return f"{name} ({industry}) is matched to bills including: {snippet}."


def breakdown_from(top_bills: list[dict[str, Any]]) -> dict[str, int]:
    if not top_bills:
        return {"Legislative Stage": 0, "Cosponsors": 0, "Recency": 0, "Bipartisan Support": 0}
    similarities = [bill["stock_relevance"] for bill in top_bills]
    avg_sim = int(round(sum(similarities) / len(similarities)))
    max_sim = int(round(max(similarities)))
    avg_passage = int(round(sum(bill["base_bill_risk"] for bill in top_bills) / len(top_bills)))
    return {
        "Legislative Stage": avg_passage,
        "Cosponsors": avg_sim,
        "Recency": max_sim,
        "Bipartisan Support": avg_sim,
    }


def adapt_stock(api_result: dict[str, Any]) -> dict[str, Any]:
    ticker = (api_result.get("ticker") or "").upper()
    api_industry = (api_result.get("industry") or "").strip()
    industry = api_industry or COMPANY_INDUSTRIES.get(ticker) or "Unknown industry"
    sector = api_industry or "Unclassified"

    company_name = pretty_company_name(ticker, api_result.get("company"))

    raw_risk = api_result.get("risk_score")
    risk_score = round(float(raw_risk) * 100, 1) if raw_risk is not None else 0.0

    profile = COMPANY_EXPOSURE_PROFILES.get(ticker, {})
    top_bills = [adapt_bill(bill, sector) for bill in (api_result.get("top_bills") or [])]

    note = api_result.get("note")
    why = stock_explanation(company_name, sector, top_bills, note)

    affecting = api_result.get("n_bills_above_threshold")
    if affecting is None:
        affecting = api_result.get("n_bills") or 0  # backward compat

    return {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        "market_cap": None,
        "source": "aws_api",
        "business_lines": profile.get("business_lines", [])[:5],
        "policy_themes": profile.get("policy_themes", [])[:5],
        "why_this_stock": why,
        "risk_score": risk_score,
        "risk_label": risk_label(risk_score),
        "affecting_bills": int(affecting),
        "top_bills": top_bills,
        "breakdown": breakdown_from(top_bills),
        "_n_bills_scored": int(api_result.get("n_bills_scored") or 0),
        "_note": note,
    }


def hero_summary(score: float, top_driver: str, stocks: list[dict[str, Any]]) -> str:
    high_bills = sum(1 for s in stocks for b in s["top_bills"] if b["risk_score"] >= 55)
    label = risk_label(score).upper()
    return (
        f"Your portfolio is exposed to {label} regulatory risk (Score: {score:.1f}). "
        f"Biggest driver: {top_driver}. {high_bills} high-relevance bills are close enough to monitor."
    )


def sector_exposure(counts: Counter, total: int) -> list[dict[str, Any]]:
    if total == 0:
        return []
    return [
        {"sector": sector, "percentage": round(count / total * 100, 1), "count": count}
        for sector, count in counts.most_common()
    ]


def top_policy_driver(stocks: list[dict[str, Any]]) -> str:
    if not stocks:
        return "No active legislative driver"
    sector_score: Counter = Counter()
    for stock in stocks:
        sector_score[stock["sector"]] += stock["risk_score"]
    return sector_score.most_common(1)[0][0]


def activity_feed(stocks: list[dict[str, Any]]) -> list[str]:
    feed: list[str] = []
    for stock in stocks:
        for bill in stock["top_bills"][:2]:
            feed.append(f"{stock['ticker']} ({stock['sector']}) - {bill['id']}: {bill['title']}")
    return feed[:10] or ["No recent legislative activity matched this portfolio."]


def backend_analytics(stocks: list[dict[str, Any]]) -> dict[str, Any]:
    bills = [bill for stock in stocks for bill in stock["top_bills"]]
    bill_count = max((stock.get("_n_bills_scored", 0) for stock in stocks), default=0)
    classified_count = sum(stock["affecting_bills"] for stock in stocks)
    if not bills:
        return {
            "bill_count": int(bill_count),
            "classified_count": int(classified_count),
            "risk_mean": 0,
            "risk_max": 0,
            "component_averages": {
                "Legislative Stage": 0,
                "Cosponsors": 0,
                "Recency": 0,
                "Bipartisan Support": 0,
            },
        }
    risk_values = [bill["risk_score"] for bill in bills]
    passage_values = [bill["base_bill_risk"] for bill in bills]
    risk_mean = round(sum(risk_values) / len(risk_values), 1)
    risk_max = round(max(risk_values), 1)
    passage_mean = round(sum(passage_values) / len(passage_values), 1)
    return {
        "bill_count": int(bill_count),
        "classified_count": int(classified_count),
        "risk_mean": risk_mean,
        "risk_max": risk_max,
        "component_averages": {
            "Legislative Stage": passage_mean,
            "Cosponsors": risk_mean,
            "Recency": risk_max,
            "Bipartisan Support": risk_mean,
        },
    }


def analyze_portfolio_via_api(tickers: list[str], analyze_impact: bool | None = None) -> dict[str, Any]:
    if analyze_impact is None:
        analyze_impact = current_app.config.get("RISK_API_ANALYZE_IMPACT", True)

    payload = call_risk_api(tickers, analyze_impact=analyze_impact)
    results = payload.get("results") or []
    stocks = [adapt_stock(item) for item in results]
    stocks.sort(key=lambda s: s["risk_score"], reverse=True)

    portfolio_score = round(
        sum(s["risk_score"] for s in stocks) / max(len(stocks), 1), 1
    )
    sector_counts: Counter = Counter(s["sector"] for s in stocks if s["sector"])
    most_exposed = sector_counts.most_common(1)[0][0] if sector_counts else "None"
    highest = stocks[0] if stocks else None
    driver = top_policy_driver(stocks)

    return {
        "tickers": tickers,
        "portfolio_score": portfolio_score,
        "portfolio_label": risk_label(portfolio_score),
        "hero_summary": hero_summary(portfolio_score, driver, stocks),
        "highest_risk_stock": highest,
        "most_exposed_sector": most_exposed,
        "sector_exposure": sector_exposure(sector_counts, len(stocks)),
        "stocks": stocks,
        "all_stocks": stocks,
        "activity_feed": activity_feed(stocks),
        "top_driver": driver,
        "known_tickers": sorted(COMPANY_NAMES.keys()),
        "backend_analytics": backend_analytics(stocks),
    }
