from flask import Blueprint, current_app, jsonify, render_template, request

from services.insights import generate_insights
from services.risk_engine import analyze_portfolio, parse_tickers


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/", methods=["GET"])
def dashboard():
    ticker_input = request.args.get("tickers", current_app.config["DEFAULT_TICKERS"])
    tickers = parse_tickers(ticker_input)
    analysis = analyze_portfolio(tickers)
    analysis["insights"] = generate_insights(analysis)

    return render_template(
        "dashboard.html",
        ticker_input=", ".join(tickers),
        analysis=analysis,
    )


@dashboard_bp.route("/api/analyze", methods=["GET"])
def analyze_api():
    ticker_input = request.args.get("tickers", current_app.config["DEFAULT_TICKERS"])
    tickers = parse_tickers(ticker_input)
    analysis = analyze_portfolio(tickers)
    analysis["insights"] = generate_insights(analysis)
    return jsonify(analysis)
