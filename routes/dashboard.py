from flask import Blueprint, current_app, jsonify, render_template
from flask_login import login_required, current_user

from services.api_adapter import analyze_portfolio_via_api
from services.insights import generate_insights
from services.risk_engine import parse_tickers
from models import Portfolio

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/", methods=["GET"])
@login_required
def dashboard():
    portfolio = Portfolio.query.filter_by(user_id=current_user.id).first()
    tickers_list = portfolio.get_tickers_list() if portfolio else []

    # If no portfolio tickers, use default
    if not tickers_list:
        tickers_list = parse_tickers(current_app.config["DEFAULT_TICKERS"])

    try:
        analysis = analyze_portfolio_via_api(tickers_list)
        analysis["insights"] = generate_insights(analysis)
    except Exception:
        current_app.logger.exception("Dashboard analysis failed")
        analysis = {
            "portfolio_label": "Low",
            "portfolio_score": 0,
            "hero_summary": "Unable to load dashboard analysis at this time.",
            "highest_risk_stock": None,
            "most_exposed_sector": "N/A",
            "top_driver": "No active legislative driver",
            "stocks": [],
            "all_stocks": [],
            "activity_feed": ["Dashboard data is unavailable."],
            "insights": [
                {
                    "level": "error",
                    "title": "Analysis unavailable",
                    "body": "The dashboard is temporarily unavailable due to a backend data issue.",
                }
            ],
            "backend_analytics": {
                "bill_count": 0,
                "classified_count": 0,
                "risk_mean": 0,
                "risk_max": 0,
                "component_averages": {},
            },
            "sector_exposure": [],
        }

    return render_template(
        "dashboard.html",
        ticker_input=", ".join(tickers_list),
        analysis=analysis,
    )


@dashboard_bp.route("/api/analyze", methods=["GET"])
@login_required
def analyze_api():
    portfolio = Portfolio.query.filter_by(user_id=current_user.id).first()
    tickers_list = portfolio.get_tickers_list() if portfolio else []
    tickers_list = tickers_list or parse_tickers(current_app.config["DEFAULT_TICKERS"])

    analysis = analyze_portfolio_via_api(tickers_list)
    analysis["insights"] = generate_insights(analysis)
    return jsonify(analysis)
