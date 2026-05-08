from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from services.data_loader import backend_analytics, load_bills, load_database_context


TICKER_SECTOR_MAP = {
    "AAPL": "Information Technology",
    "MSFT": "Information Technology",
    "NVDA": "Information Technology",
    "AMD": "Information Technology",
    "GOOGL": "Communication Services",
    "GOOG": "Communication Services",
    "META": "Communication Services",
    "NFLX": "Communication Services",
    "DIS": "Communication Services",
    "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary",
    "HD": "Consumer Discretionary",
    "NKE": "Consumer Discretionary",
    "WMT": "Consumer Staples",
    "COST": "Consumer Staples",
    "PG": "Consumer Staples",
    "KO": "Consumer Staples",
    "PEP": "Consumer Staples",
    "JPM": "Financials",
    "BAC": "Financials",
    "GS": "Financials",
    "MS": "Financials",
    "V": "Financials",
    "MA": "Financials",
    "LLY": "Health Care",
    "JNJ": "Health Care",
    "PFE": "Health Care",
    "MRK": "Health Care",
    "UNH": "Health Care",
    "ABBV": "Health Care",
    "XOM": "Energy",
    "CVX": "Energy",
    "COP": "Energy",
    "NEE": "Utilities",
    "DUK": "Utilities",
    "SO": "Utilities",
    "CAT": "Industrials",
    "BA": "Industrials",
    "GE": "Industrials",
    "RTX": "Industrials",
    "LIN": "Materials",
    "APD": "Materials",
    "SHW": "Materials",
    "PLD": "Real Estate",
    "AMT": "Real Estate",
    "SPG": "Real Estate",
}

SECTOR_ETFS = {
    "XLK": "Information Technology",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLE": "Energy",
    "XLU": "Utilities",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
}

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMD": "Advanced Micro Devices, Inc.",
    "GOOGL": "Alphabet Inc.",
    "GOOG": "Alphabet Inc.",
    "META": "Meta Platforms, Inc.",
    "NFLX": "Netflix, Inc.",
    "DIS": "The Walt Disney Company",
    "AMZN": "Amazon.com, Inc.",
    "TSLA": "Tesla, Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "BAC": "Bank of America Corporation",
    "LLY": "Eli Lilly and Company",
    "JNJ": "Johnson & Johnson",
    "PFE": "Pfizer Inc.",
    "UNH": "UnitedHealth Group Incorporated",
    "XOM": "Exxon Mobil Corporation",
    "CVX": "Chevron Corporation",
    "NEE": "NextEra Energy, Inc.",
    "DUK": "Duke Energy Corporation",
    "BA": "The Boeing Company",
}

COMPANY_INDUSTRIES = {
    "AAPL": "Consumer Electronics",
    "MSFT": "Software - Infrastructure",
    "NVDA": "Semiconductors",
    "AMD": "Semiconductors",
    "GOOGL": "Internet Content and Information",
    "GOOG": "Internet Content and Information",
    "META": "Internet Content and Information",
    "NFLX": "Entertainment",
    "DIS": "Entertainment",
    "AMZN": "Internet Retail",
    "TSLA": "Auto Manufacturers",
    "JPM": "Banks - Diversified",
    "BAC": "Banks - Diversified",
    "LLY": "Drug Manufacturers - General",
    "JNJ": "Drug Manufacturers and Medical Devices",
    "PFE": "Drug Manufacturers - General",
    "UNH": "Healthcare Plans",
    "XOM": "Oil and Gas Integrated",
    "CVX": "Oil and Gas Integrated",
    "NEE": "Utilities - Regulated Electric",
    "DUK": "Utilities - Regulated Electric",
    "BA": "Aerospace and Defense",
}

SECTOR_EXPOSURE_THEMES = {
    "Information Technology": {
        "themes": ["antitrust", "privacy", "cybersecurity", "artificial intelligence", "semiconductors", "supply chain"],
        "keywords": [
            "technology",
            "software",
            "hardware",
            "semiconductor",
            "chip",
            "ai",
            "artificial intelligence",
            "cyber",
            "privacy",
            "data",
            "digital",
            "internet",
            "app",
            "platform",
        ],
    },
    "Communication Services": {
        "themes": ["content moderation", "media regulation", "telecom", "broadband", "privacy"],
        "keywords": ["telecommunications", "broadband", "media", "platform", "content", "internet", "communications", "privacy"],
    },
    "Consumer Discretionary": {
        "themes": ["consumer protection", "labor", "trade", "transportation", "product safety"],
        "keywords": ["consumer", "retail", "vehicle", "automobile", "transportation", "labor", "trade", "tariff", "safety"],
    },
    "Consumer Staples": {
        "themes": ["food safety", "agriculture", "labeling", "consumer protection"],
        "keywords": ["food", "agriculture", "beverage", "tobacco", "label", "consumer", "safety", "nutrition"],
    },
    "Financials": {
        "themes": ["bank capital rules", "consumer finance", "credit", "payments", "crypto", "market structure"],
        "keywords": [
            "bank",
            "banking",
            "finance",
            "financial",
            "credit",
            "loan",
            "mortgage",
            "capital",
            "securities",
            "payment",
            "crypto",
            "insurance",
            "consumer finance",
        ],
    },
    "Health Care": {
        "themes": ["drug pricing", "Medicare", "Medicaid", "FDA", "clinical trials", "insurance reimbursement"],
        "keywords": [
            "health",
            "healthcare",
            "drug",
            "pharmaceutical",
            "medicare",
            "medicaid",
            "fda",
            "hospital",
            "clinical",
            "patient",
            "insurance",
            "prescription",
            "biotech",
            "medical",
        ],
    },
    "Energy": {
        "themes": ["oil and gas permitting", "emissions", "energy taxes", "renewables", "pipeline regulation"],
        "keywords": ["energy", "oil", "gas", "coal", "pipeline", "emission", "carbon", "renewable", "fuel", "drilling", "electricity"],
    },
    "Utilities": {
        "themes": ["rate regulation", "grid reliability", "renewable standards", "water regulation"],
        "keywords": ["utility", "utilities", "electric", "grid", "power", "water", "renewable", "rate", "transmission", "reliability"],
    },
    "Industrials": {
        "themes": ["infrastructure", "defense procurement", "transportation safety", "labor", "manufacturing"],
        "keywords": ["infrastructure", "rail", "railroad", "transportation", "defense", "aerospace", "manufacturing", "labor", "construction"],
    },
    "Materials": {
        "themes": ["mining", "chemical safety", "critical minerals", "construction materials"],
        "keywords": ["mining", "mineral", "chemical", "materials", "steel", "aluminum", "construction", "metals", "supply chain"],
    },
    "Real Estate": {
        "themes": ["housing policy", "REIT taxation", "commercial property", "zoning", "mortgage finance"],
        "keywords": ["housing", "real estate", "property", "rent", "mortgage", "zoning", "commercial", "reits", "land"],
    },
}

COMPANY_EXPOSURE_PROFILES = {
    "AAPL": {
        "business_lines": ["iPhone", "App Store", "consumer electronics", "services", "privacy", "supply chain"],
        "keywords": ["apple", "iphone", "app store", "mobile", "smartphone", "privacy", "data", "platform", "china", "supply chain"],
        "policy_themes": ["antitrust", "privacy", "digital markets", "supply chain", "consumer electronics"],
    },
    "MSFT": {
        "business_lines": ["cloud", "enterprise software", "AI", "cybersecurity", "gaming"],
        "keywords": ["microsoft", "cloud", "software", "ai", "artificial intelligence", "cybersecurity", "gaming", "data center"],
        "policy_themes": ["AI regulation", "cybersecurity", "cloud procurement", "antitrust", "data privacy"],
    },
    "NVDA": {
        "business_lines": ["AI chips", "GPUs", "data centers", "semiconductors"],
        "keywords": ["nvidia", "gpu", "semiconductor", "chip", "ai", "artificial intelligence", "export control", "data center"],
        "policy_themes": ["semiconductor policy", "export controls", "AI infrastructure", "supply chain"],
    },
    "JPM": {
        "business_lines": ["consumer banking", "investment banking", "credit cards", "markets", "payments"],
        "keywords": ["jpmorgan", "bank", "banking", "capital", "credit", "loan", "mortgage", "payments", "consumer finance", "securities"],
        "policy_themes": ["bank capital rules", "consumer finance", "payments", "market structure", "credit regulation"],
    },
    "BAC": {
        "business_lines": ["consumer banking", "mortgages", "credit cards", "wealth management"],
        "keywords": ["bank of america", "bank", "banking", "mortgage", "credit", "loan", "consumer finance", "wealth"],
        "policy_themes": ["consumer finance", "bank capital rules", "mortgage regulation", "credit regulation"],
    },
    "LLY": {
        "business_lines": ["pharmaceuticals", "diabetes drugs", "obesity drugs", "insulin", "clinical trials"],
        "keywords": ["eli lilly", "lilly", "drug", "pharmaceutical", "prescription", "insulin", "diabetes", "medicare", "fda", "clinical", "patent"],
        "policy_themes": ["drug pricing", "Medicare reimbursement", "FDA approvals", "patents", "clinical trials"],
    },
    "JNJ": {
        "business_lines": ["pharmaceuticals", "medical devices", "surgical products", "consumer health"],
        "keywords": ["johnson", "medical device", "drug", "pharmaceutical", "hospital", "patient", "fda", "device", "surgery"],
        "policy_themes": ["FDA regulation", "medical devices", "drug pricing", "product liability", "hospital reimbursement"],
    },
    "PFE": {
        "business_lines": ["pharmaceuticals", "vaccines", "oncology", "clinical trials"],
        "keywords": ["pfizer", "vaccine", "drug", "pharmaceutical", "clinical", "fda", "medicare", "patent", "prescription"],
        "policy_themes": ["drug pricing", "vaccines", "FDA approvals", "patents", "Medicare reimbursement"],
    },
    "UNH": {
        "business_lines": ["health insurance", "Medicare Advantage", "pharmacy benefits", "care delivery"],
        "keywords": ["unitedhealth", "health insurance", "insurance", "medicare advantage", "medicaid", "pharmacy benefit", "reimbursement"],
        "policy_themes": ["Medicare Advantage", "insurance reimbursement", "Medicaid", "PBM regulation"],
    },
    "XOM": {
        "business_lines": ["oil production", "gas", "refining", "chemicals", "carbon capture"],
        "keywords": ["exxon", "oil", "gas", "drilling", "pipeline", "refining", "carbon", "emission", "fuel", "lease"],
        "policy_themes": ["oil and gas permitting", "emissions", "carbon policy", "leases", "fuel standards"],
    },
    "CVX": {
        "business_lines": ["oil production", "gas", "refining", "LNG", "carbon capture"],
        "keywords": ["chevron", "oil", "gas", "lng", "drilling", "pipeline", "refining", "carbon", "emission", "fuel"],
        "policy_themes": ["oil and gas permitting", "emissions", "LNG exports", "leases", "fuel standards"],
    },
    "NEE": {
        "business_lines": ["regulated electric utility", "renewables", "grid", "power generation"],
        "keywords": ["nextera", "utility", "electric", "renewable", "solar", "wind", "grid", "transmission", "power"],
        "policy_themes": ["renewable tax credits", "grid reliability", "transmission", "utility regulation"],
    },
    "DUK": {
        "business_lines": ["regulated electric utility", "natural gas utility", "grid", "power generation"],
        "keywords": ["duke energy", "utility", "electric", "gas", "grid", "power", "rate", "transmission"],
        "policy_themes": ["utility regulation", "grid reliability", "rate policy", "emissions"],
    },
    "BA": {
        "business_lines": ["commercial aircraft", "defense", "space", "aviation safety"],
        "keywords": ["boeing", "aircraft", "aviation", "aerospace", "defense", "faa", "airline", "safety"],
        "policy_themes": ["aviation safety", "defense procurement", "FAA oversight", "manufacturing"],
    },
    "TSLA": {
        "business_lines": ["electric vehicles", "batteries", "charging", "autonomous driving"],
        "keywords": ["tesla", "electric vehicle", "ev", "battery", "charging", "autonomous", "vehicle", "emissions"],
        "policy_themes": ["EV tax credits", "battery supply chain", "vehicle safety", "emissions"],
    },
}


def parse_tickers(raw: str) -> list[str]:
    tickers = [ticker.strip().upper() for ticker in raw.replace("\n", ",").split(",")]
    clean = []
    for ticker in tickers:
        if ticker and ticker not in clean:
            clean.append(ticker)
    return clean or ["AAPL", "JPM", "LLY"]


def ticker_profile(ticker: str) -> dict[str, Any]:
    exposure = COMPANY_EXPOSURE_PROFILES.get(ticker, {})
    db_ticker = load_database_context()["tickers"].get(ticker)
    if db_ticker:
        return {
            "ticker": ticker,
            "company_name": db_ticker.get("company_name") or ticker,
            "sector": db_ticker.get("sector") or "Industrials",
            "industry": db_ticker.get("industry") or "Unknown industry",
            "market_cap": db_ticker.get("market_cap"),
            "source": "database",
            "business_lines": exposure.get("business_lines", []),
            "keywords": exposure.get("keywords", []),
            "policy_themes": exposure.get("policy_themes", []),
        }

    sector = TICKER_SECTOR_MAP.get(ticker, SECTOR_ETFS.get(ticker, "Industrials"))
    sector_profile = SECTOR_EXPOSURE_THEMES.get(sector, {})
    return {
        "ticker": ticker,
        "company_name": COMPANY_NAMES.get(ticker, ticker),
        "sector": sector,
        "industry": COMPANY_INDUSTRIES.get(ticker, "Mapped by fallback sector model"),
        "market_cap": None,
        "source": "fallback",
        "business_lines": exposure.get("business_lines", []),
        "keywords": exposure.get("keywords", sector_profile.get("keywords", [])),
        "policy_themes": exposure.get("policy_themes", sector_profile.get("themes", [])),
    }


def analyze_portfolio(tickers: list[str]) -> dict[str, Any]:
    bills = load_bills()
    stock_results = []
    known_tickers = sorted(load_database_context()["tickers"].keys())

    for ticker in tickers:
        profile = ticker_profile(ticker)
        sector = profile["sector"]
        relevant = score_stock_relevance(bills, profile)
        relevant = relevant[relevant["stock_relevance_score"] >= 20].copy()
        relevant = relevant.sort_values("stock_adjusted_risk", ascending=False)
        top_bills = relevant.head(5)
        risk_score = compute_stock_score(relevant)

        stock_results.append(
            {
                "ticker": ticker,
                "company_name": profile["company_name"],
                "sector": sector,
                "industry": profile["industry"],
                "market_cap": profile["market_cap"],
                "source": profile["source"],
                "business_lines": profile["business_lines"][:5],
                "policy_themes": profile["policy_themes"][:5],
                "why_this_stock": stock_explanation(profile, top_bills),
                "risk_score": round(risk_score, 1),
                "risk_label": risk_label(risk_score),
                "affecting_bills": int(len(relevant)),
                "top_bills": [bill_to_card(row) for _, row in top_bills.iterrows()],
                "breakdown": risk_breakdown(top_bills if len(top_bills) else relevant),
            }
        )

    stock_results = sorted(stock_results, key=lambda item: item["risk_score"], reverse=True)
    portfolio_score = round(sum(item["risk_score"] for item in stock_results) / max(len(stock_results), 1), 1)
    sector_counts = Counter(item["sector"] for item in stock_results)
    most_exposed_sector = sector_counts.most_common(1)[0][0] if sector_counts else "None"
    highest_risk_stock = stock_results[0] if stock_results else None
    top_driver = top_policy_driver(stock_results)

    return {
        "tickers": tickers,
        "portfolio_score": portfolio_score,
        "portfolio_label": risk_label(portfolio_score),
        "hero_summary": hero_summary(portfolio_score, top_driver, stock_results),
        "highest_risk_stock": highest_risk_stock,
        "most_exposed_sector": most_exposed_sector,
        "sector_exposure": sector_exposure(sector_counts, len(stock_results)),
        "stocks": stock_results,
        "all_stocks": stock_results,
        "activity_feed": recent_activity(bills, stock_results),
        "top_driver": top_driver,
        "known_tickers": known_tickers,
        "backend_analytics": backend_analytics(),
    }


def compute_stock_score(relevant) -> float:
    if relevant.empty:
        return 0.0
    top = relevant.nlargest(8, "risk_score")
    weights = top["confidence"].clip(lower=0.2) * top["stock_relevance_score"].clip(lower=20) / 100
    weighted = (top["stock_adjusted_risk"] * weights).sum()
    denominator = weights.sum()
    return min(100.0, float(weighted / denominator))


def risk_label(score: float) -> str:
    if score >= 55:
        return "High"
    if score >= 35:
        return "Moderate"
    return "Low"


def bill_to_card(row) -> dict[str, Any]:
    database = load_database_context()
    bill_id_key = row.get("bill_id", "")
    db_bill = database["bills"].get(bill_id_key, {})
    subjects = [item.get("subject_name") for item in database["subjects"].get(bill_id_key, []) if item.get("subject_name")]
    sponsors = database["sponsors"].get(bill_id_key, [])[:4]
    actions = database["actions"].get(bill_id_key, [])[:4]
    bill_id = f"{str(row.get('type', '')).upper()}.{row.get('number', '')}"
    score = float(row.get("stock_adjusted_risk", row.get("risk_score", 0)))
    return {
        "id": bill_id,
        "bill_key": bill_id_key,
        "title": row.get("title") or "Untitled bill",
        "risk_score": round(score, 1),
        "risk_label": risk_label(score),
        "status": db_bill.get("latest_action_text") or row.get("latest_action_text") or "No recent action available",
        "date": row.get("latest_action_date") or row.get("introducedDate") or "",
        "impact": row.get("stock_match_explanation") or f"Likely to affect {row.get('gics_sectors') or 'mapped sectors'}",
        "base_bill_risk": round(float(row.get("risk_score", 0)), 1),
        "stock_relevance": int(round(float(row.get("stock_relevance_score", 0)))),
        "match_reasons": row.get("stock_match_reasons", []),
        "url": db_bill.get("legislation_url") or row.get("legislationUrl") or "",
        "policy_area": db_bill.get("policy_area") or row.get("policy_area_name") or "Unspecified",
        "subjects": subjects[:6],
        "sponsors": sponsors,
        "actions": actions,
        "classification": {
            "industry": db_bill.get("classified_industry") or row.get("gics_sectors") or "Unclassified",
            "confidence": round(float(db_bill.get("classification_confidence") or row.get("confidence") or 0), 2),
            "method": db_bill.get("classification_method") or "risk parquet",
        },
    }


def risk_breakdown(frame) -> dict[str, int]:
    if frame.empty:
        return {"Legislative Stage": 0, "Cosponsors": 0, "Recency": 0, "Bipartisan Support": 0}
    return {
        "Legislative Stage": int(round(frame["stage_score"].mean())),
        "Cosponsors": int(round(frame["cosponsor_score"].mean())),
        "Recency": int(round(frame["recency_score"].mean())),
        "Bipartisan Support": int(round(frame["bipartisan_score"].mean())),
    }


def score_stock_relevance(bills, profile: dict[str, Any]):
    frame = bills.copy()
    scored = frame.apply(lambda row: bill_stock_relevance(row, profile), axis=1)
    frame["stock_relevance_score"] = scored.apply(lambda item: item["score"])
    frame["stock_match_reasons"] = scored.apply(lambda item: item["reasons"])
    frame["stock_match_explanation"] = scored.apply(lambda item: item["explanation"])
    frame["stock_adjusted_risk"] = (
        frame["risk_score"] * (0.45 + 0.55 * frame["stock_relevance_score"] / 100)
    ).clip(upper=100)
    return frame


def bill_stock_relevance(row, profile: dict[str, Any]) -> dict[str, Any]:
    sector = profile["sector"]
    sector_profile = SECTOR_EXPOSURE_THEMES.get(sector, {})
    text = searchable_bill_text(row)
    bill_sectors = row.get("sector_list", [])
    reasons = []
    score = 0

    if sector in bill_sectors:
        score += 35
        reasons.append(f"sector match: {sector}")

    industry_terms = tokenize_terms([profile.get("industry", "")])
    industry_hits = matched_terms(industry_terms, text)
    if industry_hits:
        score += min(20, 8 + 4 * len(industry_hits))
        reasons.append(f"industry terms: {', '.join(industry_hits[:3])}")

    company_hits = matched_terms(profile.get("keywords", []), text)
    if company_hits:
        score += min(30, 10 + 5 * len(company_hits))
        reasons.append(f"company exposure terms: {', '.join(company_hits[:4])}")

    theme_hits = matched_terms(profile.get("policy_themes", []), text)
    if theme_hits:
        score += min(20, 8 + 4 * len(theme_hits))
        reasons.append(f"policy themes: {', '.join(theme_hits[:3])}")

    sector_hits = matched_terms(sector_profile.get("keywords", []), text)
    if sector_hits and sector not in bill_sectors:
        score += min(18, 6 + 3 * len(sector_hits))
        reasons.append(f"sector issue terms: {', '.join(sector_hits[:3])}")
    elif sector_hits:
        score += min(12, 2 * len(sector_hits))
        reasons.append(f"sector issue terms: {', '.join(sector_hits[:3])}")

    if not reasons and sector in bill_sectors:
        reasons.append(f"general {sector} exposure")

    score = min(100, score)
    return {
        "score": score,
        "reasons": reasons,
        "explanation": explain_bill_match(profile, row, reasons, score),
    }


def searchable_bill_text(row) -> str:
    parts = [
        row.get("title", ""),
        row.get("policy_area_name", ""),
        row.get("latest_action_text", ""),
        row.get("gics_sectors", ""),
    ]
    database = load_database_context()
    bill_id = row.get("bill_id", "")
    parts.extend(item.get("subject_name", "") for item in database["subjects"].get(bill_id, []))
    parts.extend(item.get("action_text", "") for item in database["actions"].get(bill_id, [])[:8])
    return " ".join(str(part) for part in parts if part).lower()


def tokenize_terms(values: list[str]) -> list[str]:
    terms = []
    for value in values:
        for part in str(value).replace("-", " ").replace("/", " ").split():
            clean = part.strip().lower()
            if len(clean) >= 4 and clean not in {"mapped", "fallback", "sector", "model", "unknown"}:
                terms.append(clean)
    return terms


def matched_terms(terms: list[str], text: str) -> list[str]:
    hits = []
    for term in terms:
        clean = str(term).lower().strip()
        if clean and clean in text and clean not in hits:
            hits.append(clean)
    return hits


def explain_bill_match(profile: dict[str, Any], row, reasons: list[str], score: float) -> str:
    company = profile.get("company_name") or profile["ticker"]
    if reasons:
        return f"{company} exposure is specific because this bill matches {', '.join(reasons[:3])}."
    return f"{company} has limited direct exposure signals for this bill beyond broad market context."


def stock_explanation(profile: dict[str, Any], top_bills) -> str:
    company = profile.get("company_name") or profile["ticker"]
    if top_bills.empty:
        return f"{company} has no strong bill matches in the current dataset."
    reasons = []
    for reason_list in top_bills["stock_match_reasons"].head(3):
        for reason in reason_list:
            if reason not in reasons:
                reasons.append(reason)
    if not reasons:
        return f"{company} risk is currently based on broad {profile['sector']} exposure."
    return f"{company} is flagged because its {profile['industry']} profile matches {', '.join(reasons[:4])}."


def sector_exposure(sector_counts: Counter, total: int) -> list[dict[str, Any]]:
    if total == 0:
        return []
    return [
        {"sector": sector, "percentage": round(count / total * 100, 1), "count": count}
        for sector, count in sector_counts.most_common()
    ]


def top_policy_driver(stocks: list[dict[str, Any]]) -> str:
    policies = defaultdict(float)
    for stock in stocks:
        for bill in stock["top_bills"][:3]:
            policies[bill["policy_area"]] += bill["risk_score"]
    if not policies:
        return "No active legislative driver"
    return max(policies.items(), key=lambda item: item[1])[0]


def hero_summary(score: float, top_driver: str, stocks: list[dict[str, Any]]) -> str:
    high_bills = sum(1 for stock in stocks for bill in stock["top_bills"] if bill["risk_score"] >= 55)
    label = risk_label(score).upper()
    return (
        f"Your portfolio is exposed to {label} regulatory risk (Score: {score:.1f}). "
        f"Biggest driver: {top_driver}. {high_bills} high-risk bills are close enough to monitor."
    )


def recent_activity(bills, stocks: list[dict[str, Any]]) -> list[str]:
    sectors = {stock["sector"] for stock in stocks}
    relevant = bills[bills["sector_list"].apply(lambda bill_sectors: bool(sectors.intersection(bill_sectors)))].copy()
    if relevant.empty:
        return ["No recent legislative activity matched this portfolio."]
    relevant = relevant.sort_values(["introducedDate", "risk_score"], ascending=[False, False]).head(5)
    feed = []
    for _, row in relevant.iterrows():
        bill_id = f"{str(row.get('type', '')).upper()}.{row.get('number', '')}"
        feed.append(f"{row.get('latest_action_date') or row.get('introducedDate')}: {bill_id} - {row.get('title')}")
    return feed
