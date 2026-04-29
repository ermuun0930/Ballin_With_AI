from __future__ import annotations


def generate_insights(analysis: dict) -> list[dict[str, str]]:
    insights = []
    score = analysis["portfolio_score"]
    most_exposed = analysis["most_exposed_sector"]
    highest = analysis.get("highest_risk_stock")

    if score >= 55:
        insights.append(
            {
                "level": "high",
                "title": "High regulatory exposure detected",
                "body": "Review position sizing and watch late-stage bills before adding more exposure.",
            }
        )
    elif score >= 35:
        insights.append(
            {
                "level": "medium",
                "title": "Moderate legislative risk",
                "body": "The portfolio has several active policy links, but risk is not concentrated enough to require urgent action.",
            }
        )
    else:
        insights.append(
            {
                "level": "low",
                "title": "Low near-term regulatory pressure",
                "body": "Current bills do not point to severe portfolio-wide exposure.",
            }
        )

    if highest:
        insights.append(
            {
                "level": "high" if highest["risk_score"] >= 55 else "medium",
                "title": f"{highest['ticker']} is the main stock to monitor",
                "body": f"{highest['ticker']} maps to {highest['sector']} and has {highest['affecting_bills']} relevant bills.",
            }
        )

    sector_share = max((item["percentage"] for item in analysis["sector_exposure"]), default=0)
    if sector_share >= 50:
        insights.append(
            {
                "level": "medium",
                "title": f"High exposure to {most_exposed} regulation",
                "body": "Consider diversifying sector exposure or setting alerts for bills in this area.",
            }
        )

    late_stage_count = sum(
        1
        for stock in analysis["stocks"]
        for bill in stock["top_bills"]
        if bill["risk_score"] >= 50
    )
    if late_stage_count:
        insights.append(
            {
                "level": "high",
                "title": f"{late_stage_count} higher-risk bill signals detected",
                "body": "Prioritize the stock drilldown cards and read the bill status before making allocation changes.",
            }
        )

    insights.append(
        {
            "level": "idea",
            "title": "Suggested action",
            "body": "Use this dashboard as a screening layer, then validate bill impact against position size, earnings sensitivity, and sector alternatives.",
        }
    )

    return insights[:5]
