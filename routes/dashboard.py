from flask import Blueprint, current_app, jsonify, render_template
from flask_login import login_required, current_user

from services.insights import generate_insights
from services.risk_engine import analyze_portfolio, parse_tickers
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

    analysis = analyze_portfolio(tickers_list)
    analysis["insights"] = generate_insights(analysis)

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

    analysis = analyze_portfolio(tickers_list)
    analysis["insights"] = generate_insights(analysis)
    return jsonify(analysis)
