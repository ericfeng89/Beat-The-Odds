import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def errorPage(blockTitle, errorMessage, imageSource):
    return render_template("error.html", title = (blockTitle), info = (errorMessage), file = (imageSource))


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

"""
def lookup(id):
    Look up quote for symbol.


    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    try:
        response = mytable.query.filter_by(house_id = id).all()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "house_id": quote["house_id"],
            "price": float(quote["latestPrice"]),
            "crypto": quote["la"]
        }
    except (KeyError, TypeError, ValueError):
        return None
"""

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def checkInt(str):
    try:
        int(str)
        return True
    except ValueError:
        return False


#Given wager, odds, and whether it's a free bet, returns the potential payout
def payout(wager, odds, decimal=True, free=False):
    if not decimal:
        odds = americanToDecimal(odds)

    payout = wager * odds

    if free:
        payout -= wager

    return payout


def americanToDecimal(odds):
    if odds > 0:
        return odds/100 + 1
    else:
        return 100/(-odds) + 1