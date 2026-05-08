from difflib import get_close_matches

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

from models import db, Portfolio
from services.risk_engine import COMPANY_NAMES, TICKER_SECTOR_MAP

portfolio_bp = Blueprint("portfolio", __name__, url_prefix="/portfolio")


class AddStockForm(FlaskForm):
    ticker = StringField('Search for a stock', validators=[
        DataRequired(message='Please enter a stock ticker or company name')
    ])
    submit = SubmitField('Add to Portfolio')


class ClearPortfolioForm(FlaskForm):
    submit = SubmitField('Clear All')


class RemoveStockForm(FlaskForm):
    ticker = StringField(validators=[DataRequired()])
    submit = SubmitField('Remove')


def find_matching_ticker(user_input):
    normalized = user_input.strip().upper()
    available_tickers = sorted(TICKER_SECTOR_MAP.keys())

    if normalized in available_tickers:
        return normalized

    for ticker, company_name in COMPANY_NAMES.items():
        company_normalized = company_name.upper()
        if normalized in company_normalized or company_normalized in normalized:
            return ticker

    close_matches = get_close_matches(normalized, available_tickers, n=1, cutoff=0.72)
    return close_matches[0] if close_matches else None


@portfolio_bp.route("/", methods=["GET", "POST"])
@login_required
def manage():
    portfolio = Portfolio.query.filter_by(user_id=current_user.id).first()
    if not portfolio:
        portfolio = Portfolio(user_id=current_user.id, name='My Portfolio')
        db.session.add(portfolio)
        db.session.commit()

    form = AddStockForm()

    if form.validate_on_submit():
        user_input = form.ticker.data.strip().upper()
        matching_ticker = find_matching_ticker(user_input)
        
        if not matching_ticker:
            flash(f"No matching stock found for '{form.ticker.data}'. Please try a different search term.", "error")
            return redirect(url_for('portfolio.manage'))
        
        tickers_list = portfolio.get_tickers_list()

        if matching_ticker not in tickers_list:
            tickers_list.append(matching_ticker)
            portfolio.set_tickers_list(tickers_list)
            db.session.commit()
            flash(f"{matching_ticker} added to your portfolio", "success")
        else:
            flash(f"{matching_ticker} is already in your portfolio", "warning")

        return redirect(url_for('portfolio.manage'))

    if request.method == "POST" and not form.validate_on_submit():
        action = request.form.get("action")
        ticker = request.form.get("ticker", "").strip().upper()

        if action == "remove":
            tickers_list = portfolio.get_tickers_list()
            if ticker in tickers_list:
                tickers_list.remove(ticker)
                portfolio.set_tickers_list(tickers_list)
                db.session.commit()
                flash(f"{ticker} removed from your portfolio", "success")
            else:
                flash(f"{ticker} is not in your portfolio", "warning")
            return redirect(url_for('portfolio.manage'))

    available_stocks = [
        {
            "ticker": ticker,
            "company_name": COMPANY_NAMES.get(ticker, ticker),
        }
        for ticker in sorted(TICKER_SECTOR_MAP.keys())
    ]

    return render_template(
        "portfolio.html",
        portfolio=portfolio.get_tickers_list(),
        form=form,
        clear_form=ClearPortfolioForm(),
        available_stocks=available_stocks,
    )


@portfolio_bp.route("/clear", methods=["POST"])
@login_required
def clear():
    clear_form = ClearPortfolioForm()
    if clear_form.validate_on_submit():
        portfolio = Portfolio.query.filter_by(user_id=current_user.id).first()
        if portfolio:
            portfolio.set_tickers_list([])
            db.session.commit()
            flash("Portfolio cleared", "success")
    return redirect(url_for("portfolio.manage"))
