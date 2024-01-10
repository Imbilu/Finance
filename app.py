import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT * FROM portfolio WHERE user_id = ?", session["user_id"])
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    # get cash value float
    cash = cash[0]["cash"]
    # this will be total value of all stock holdings and cash
    sum = cash

    # add stock name, add current lookup value, add total value
    for row in rows:
        look = lookup(row["symbol"])
        row["name"] = look["name"]
        row["price"] = look["price"]
        row["total"] = row["price"] * row["shares"]

        # increment sum
        sum += row["total"]

        # convert price and total to usd format
        row["price"] = usd(row["price"])
        row["total"] = usd(row["total"])

    return render_template("index.html", rows=rows, cash=usd(cash), sum=usd(sum))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    '''Allow the user to buy shares with their available cash balance'''
    if request.method == "POST":
        symbol = (request.form.get("symbol")).upper()
        shares = request.form.get("shares")
        if not lookup(symbol):
            return apology("Invalid Symbol")

        if int(shares) < 0 or not int(shares):
            return apology("Invalid number of shares")

        user_balance = db.execute(
            "SELECT cash FROM users WHERE id=?", session["user_id"]
        )
        balance = user_balance[0]["cash"]
        price = (lookup(symbol))["price"]
        purchase_cost = int(shares) * price
        if balance < purchase_cost:
            return apology("Cannot Afford")
        else:
            db.execute("UPDATE users SET cash=?", balance - purchase_cost)

        db.execute(
            "INSERT INTO purchases (user_id, symbol, shares, action, price) VALUES(?, ?, ?, ?, ?)",
            session["user_id"],
            symbol,
            shares,
            "buy",
            price,
        )

        row = db.execute(
            "SELECT * FROM portfolio WHERE user_id = ? AND symbol = ?",
            session["user_id"],
            symbol,
        )

        if len(row) != 1:
            db.execute(
                "INSERT INTO portfolio (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
                session["user_id"],
                symbol,
                shares,
                price,
            )

        oldshares = db.execute(
            "SELECT shares FROM portfolio WHERE user_id = ? AND symbol = ?",
            session["user_id"],
            symbol,
        )
        oldshares = oldshares[0]["shares"]
        newshares = int(oldshares) + int(shares)

        db.execute(
            "UPDATE portfolio SET shares = ? WHERE user_id = ? AND symbol = ?",
            newshares,
            session["user_id"],
            symbol,
        )
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT * FROM purchases WHERE user_id = ?", session["user_id"])
    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not lookup(symbol):
            return apology("Invalid Symbol")
        result = lookup(symbol)
        return render_template("quoted.html", result=result)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    rows = db.execute("SELECT * FROM users")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password:
            return apology("Username or Password cannot be blank")
        if password != confirmation:
            return apology("Password and confirmation do not match")

        try:
            db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                username,
                generate_password_hash(password),
            )
        except ValueError:
            return apology("Username already exists")

        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        # get the user's current stocks
        portfolio = db.execute(
            "SELECT symbol FROM portfolio WHERE user_id = ?", session["user_id"]
        )

        # render sell.html form, passing in current stocks
        return render_template("sell.html", portfolio=portfolio)

    # if POST method, sell stock
    else:
        # save stock symbol, number of shares, and quote dict from form
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        quote = lookup(symbol)
        rows = db.execute(
            "SELECT * FROM portfolio WHERE user_id = ? AND symbol = ?",
            session["user_id"],
            symbol,
        )

        # return apology if symbol invalid/ not owned
        if len(rows) != 1:
            return apology("must provide valid stock symbol")

        # return apology if shares not provided. buy form only accepts positive integers
        if shares < 0 or not int(shares):
            return apology("Invalid number of shares")

        # current shares of this stock
        oldshares = rows[0]["shares"]

        # cast shares from form to int
        shares = int(shares)

        # return apology if trying to sell more shares than own
        if shares > oldshares:
            return apology("shares sold can't exceed shares owned")

        # get current value of stock price times shares
        sold = quote["price"] * shares

        # add value of sold stocks to previous cash balance
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cash = cash[0]["cash"]
        cash = cash + sold

        # update cash balance in users table
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, session["user_id"])

        # subtract sold shares from previous shares
        newshares = oldshares - shares

        # if shares remain, update portfolio table with new shares
        if shares > 0:
            db.execute(
                "UPDATE portfolio SET shares = ? WHERE user_id = ? AND symbol = ?",
                newshares,
                session["user_id"],
                symbol,
            )

        # otherwise delete stock row because no shares remain
        else:
            db.execute(
                "DELETE FROM portfolio WHERE symbol = ? AND user_id = ?",
                symbol,
                session["user_id"],
            )

        # update history table
        db.execute(
            "INSERT INTO purchases (user_id, symbol, shares, action, price) VALUES (?, ?, ?, 'sell', ?)",
            session["user_id"],
            symbol,
            shares,
            quote["price"],
        )

        # redirect to index page
        return redirect("/")


@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    if request.method == "POST":
        current_hash = db.execute(
            "SELECT hash FROM users WHERE id = ?", session["user_id"]
        )
        current_hash = current_hash[0]["hash"]
        current_p = request.form.get("current_p")
        new_p = request.form.get("new_P")
        new_p2 = request.form.get("new_P2")

        if generate_password_hash(current_p) != current_hash:
            return apology("Incorrect current password")
        elif new_p != new_p2:
            return apology("New password and confirmation do not match")
        else:
            db.execute(
                "UPDATE TABLE users SET hash = ? WHERE user_id = ?",
                generate_password_hash(new_p),
                session["user_id"],
            )

        return redirect("/")

    else:
        return render_template("change.html")
