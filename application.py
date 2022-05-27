import os
import redis
from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import errorPage, login_required, usd

# Configure application
application = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# Ensure templates are auto-reloaded
application.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@application.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
application.jinja_env.filters["usd"] = usd

# Configure Redis for storing the session data locally on the server-side
application.secret_key = 'BAD_SECRET_KEY'
application.config['SESSION_TYPE'] = 'redis'
application.config['SESSION_PERMANENT'] = False
application.config['SESSION_USE_SIGNER'] = True
application.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
# Create and initialize the Flask-Session object AFTER `app` has been configured
server_session = Session(application)

# Configure Flask to use local SQLite3 database with SQLAlchemy
application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'house_data.db')
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(application)

# Configure marshmallow
ma = Marshmallow(application)

# Create classes/models
class mytable(db.Model):
    house_id = db.Column(db.Integer, primary_key=True)
    actual_price = db.Column(db.Float)
    proj_price = db.Column(db.Float)
    actual_crypto = db.Column(db.Integer)
    proj_crypto = db.Column(db.Integer)
    bedrooms = db.Column(db.Integer)
    bathrooms = db.Column(db.Integer)
    acres = db.Column(db.Float)
    floors = db.Column(db.Integer)
    waterfront = db.Column(db.Integer)
    view = db.Column(db.Integer)
    grade = db.Column(db.Integer)
    sqft_above = db.Column(db.Integer)
    yr_built = db.Column(db.Integer)

    def __init__(self, actual_price, proj_price, actual_crypto, proj_crypto, bedrooms, bathrooms, acres, floors, waterfront, view, grade, sqft_above, yr_built):
        self.actual_price = actual_price
        self.proj_price = proj_price
        self.actual_crypto = actual_crypto
        self.proj_crypto = proj_crypto
        self.bedrooms = bedrooms
        self.bathrooms = bathrooms
        self.acres = acres
        self.floors = floors
        self.waterfront = waterfront
        self.view = view
        self.grade = grade
        self.sqft_above = sqft_above
        self.yr_built = yr_built


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(length=50))
    hash = db.Column(db.String(length=200))
    cash = db.Column(db.Integer)
    # Create initializer/constructor
    def __init__(self, username, hash, cash):
        self.username = username
        self.hash = hash
        self.cash = cash
class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)

    # Create initializer/constructor
    def __init__(self, house_id, user_id):
        self.house_id = house_id
        self.user_id = user_id


class Bought(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer)
    house_id = db.Column(db.Integer)
    time = db.Column(db.String(length=100))
    price_bought = db.Column(db.Float)
    crypto_bought = db.Column(db.Integer)
    # Create initializer/constructor
    def __init__(self, buyer_id, time, house_id, price_bought, crypto_bought):
        self.buyer_id = buyer_id
        self.house_id = house_id
        self.time = time
        self.price_bought = price_bought
        self.crypto_bought = crypto_bought

class Sold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer)
    house_id = db.Column(db.Integer)
    time = db.Column(db.String(length=100))
    price_sold = db.Column(db.Float)
    crypto_sold = db.Column(db.Integer)
    # Create initializer/constructor
    def __init__(self, seller_id, time, house_id, price_sold, crypto_sold):
        self.seller_id = seller_id
        self.house_id = house_id
        self.time = time
        self.price_bought = price_sold
        self.crypto_bought = crypto_sold

# Create
# mas (only include data you want to show)
class UsersSchema(ma.Schema):
    class Meta:
        fields = ('username', 'cash')
class PortfolioSchema(ma.Schema):
    class Meta:
        field = ('house_id')
class BoughtSchema(ma.Schema):
    class Meta:
        fields = ('time', 'house_id', 'price_bought', 'crypto_bought')
class SoldSchema(ma.Schema):
    class Meta:
        fields = ('time', 'house_id', 'price_sold', 'crypto_sold')
        
# Initialize Schemas
users_schema = UsersSchema
portfolio_schema = PortfolioSchema(many=True)
bought_schema = BoughtSchema(many=True)
sold_schema = SoldSchema(many=True)

# Make sure API key is set
os.environ.get("API_KEY")

if not os.environ.get("API_KEY"):
   raise RuntimeError("API_KEY not set")

@application.route("/")
def landing():
    return render_template("landing.html")

@application.route("/home")
@login_required
def index():
    # Obtain user id
    user = session["user_id"]
    print("user: ", user)

    # Obtain available cash
    availableCash = (Users.query.filter_by(id = user).first()).cash
    print("availableCash: ", availableCash)

    # Obtain at least one house id that the user possesses
    houseList = Portfolio.query.filter_by(user_id = user).all()
    print("houseList: ", houseList)

    # If user has no properties return minimum information
    if houseList == []:
        return render_template("index.html", availableCash = usd(availableCash), grandTotal = usd(availableCash),  total = [], price = [], houseList = [], houseListLength = 0)
    # If user owns properties return the remaining information
    else:
        # Calculate symbol list length for iteration in index.html
        houseListLength = len(houseList)
        print("houseListLength: ", houseListLength)

        # Create empty arrays to store values
        houses = []
        price = []
        totalCost = 0

        # Calculate value of each holding of property in portfolio
        for i in range(len(houseList)):
            houseIndex = houseList[i].house_id
            print("houseIndex:", houseIndex)
            houses.append(houseIndex)

            # Obtain price of property using iex API
            priceIndex = mytable.query.filter_by(house_id = houseIndex).first().proj_price
            print("priceIndex:", priceIndex)
            price.append(priceIndex)

            # calculate total price of properties
            totalCost = totalCost + price[i]
            print("totalCost:", totalCost)

        print("houses:", houses)
        print("price:", price)

        # Calculate grand total value of all assets
        grandTotal = totalCost + availableCash

        # Render page with information
        return render_template("index.html", houses = houses, houseListLength = houseListLength, price = price, availableCash = usd(availableCash), grandTotal = usd(grandTotal))


@application.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
        houseID = request.form.get("houseID")

        # User error handling: stop empty symbol and shares fields, stop invalid symbols, and negative share numbers
        if not houseID:
            return errorPage(blockTitle="No Data", errorMessage = "Please enter a valid house ID", imageSource = "no-data.svg")

        # if property already bought, prevent user from buying
        if Portfolio.query.filter_by(house_id = houseID).first():
            return errorPage(blockTitle="Forbidden", errorMessage="Property has already been purchased",
                             imageSource="animated-403.svg")

        # Obtain user id
        user = session["user_id"]
        print("user:", user)

        # Obtain available cash
        availableCash = (Users.query.filter_by(id = user).first()).cash
        print("available:", availableCash)

        # Get current price of property
        price = mytable.query.filter_by(house_id = houseID).first().proj_price
        print("price:", price)

        # User error handling: stop user if seeking to buy beyond cash balance
        if availableCash < price:
             return errorPage(blockTitle="Forbidden", errorMessage = "Insufficient funds to complete transaction", imageSource="animated-403.svg")

        # Continue with transaction and calculate remaining cash
        remainingCash = availableCash - price

        # Obtain year, month, day, hour, minute, second
        now = datetime.now()
        time = now.strftime("%d/%m/%Y %H:%M:%S")

        # Update cash field in Users Table and create entry into Bought Table
        updatedCash = Users.query.filter_by(id = user).first()
        updatedCash.cash = remainingCash
        db.session.commit()
        #"UPDATE users SET cash = :remaining WHERE id = :id", remaining = remaining, id = user)

        # Log transaction history
        logPurchase = Bought(user, time, houseID, price, 0)
        db.session.add(logPurchase)
        db.session.commit()
        #("INSERT INTO bought (buyer_id, time, symbol, shares_bought, price_bought) VALUES (:buyer_id, :time, :symbol, :shares_bought, :price_bought)", time = datetime.datetime.now(), symbol = symbol, shares_bought = shares, price_bought = price, buyer_id = user)

        # If buyer never bought this property before
        portfolio = Portfolio.query.filter(Portfolio.user_id == user, Portfolio.house_id == houseID).first()
        print("portfolio", portfolio)

        # Add to portfolio
        db.session.add(Portfolio(houseID, user))
        db.session.commit()

        return render_template("bought.html", houseID = houseID, price = usd(price))


@application.route("/history")
@login_required
def history():
    # Obtain user id
    user = session["user_id"]

    # Obtain purchase history
    bought_list = Bought.query.filter_by(buyer_id = user).all()
    print("bought_list:", bought_list)
    #("SELECT time, symbol, shares_bought, price_bought FROM bought WHERE buyer_id = :id", id = user)

    # If user didn't sell propertys, only query bought table, if didn't buy anything, return empty
    if bought_list == []:
        # Will return empty list if user didn't buy anything
        return render_template("history.html", bought_list_length = 0, bought_list = [], sold_list_length = 0, sold_list = [])

    # Else query sold table
    else:
        # Obtain sell history
        sold_list = Sold.query.filter_by(seller_id = user).all()
        print("sold_list:", sold_list)
        #("SELECT time, symbol, shares_sold, price_sold FROM sold WHERE seller_id = :id", id = user)

        # Calculate length of bought_list and sold_list
        bought_list_length = len(bought_list)
        sold_list_length = len(sold_list)

        return render_template("history.html", bought_list = bought_list, sold_list = sold_list, bought_list_length = bought_list_length, sold_list_length = sold_list_length)


@application.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return errorPage(blockTitle="No Data", errorMessage = "Must provide username", imageSource = "no-data.svg")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return errorPage(blockTitle="No Data", errorMessage = "Must provide password", imageSource = "no-data.svg")

        # Query database for username
        rows = Users.query.filter_by(username=request.form.get("username")).first()
        #("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Ensure user exists
        try:
            rows.username

        # NoneType is returned and therefore username does't exist in database
        except AttributeError:
             return errorPage(blockTitle="No Data", errorMessage = "User doesn't exist", imageSource = "no-data.svg")

        # Finish logging user in
        else:
            # Ensure username and password is correct
            if rows.username != request.form.get("username") or not check_password_hash(rows.hash, request.form.get("password")):
                return errorPage(blockTitle = "Unauthorized", errorMessage = "invalid username and/or password", imageSource="animated-401.svg")

            # Remember which user has logged in
            session["user_id"] = rows.id

            # Redirect user to home page
            return redirect("/home")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@application.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@application.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    else:
        houseID = request.form.get("houseID")
        data = mytable.query.filter_by(house_id = houseID).first()
        print("data:", data)

        # User error handling: stop empty symbol and shares fields, stop invalid symbols, and negative share numbers
        if not houseID:
            return errorPage(blockTitle="Bad Request", errorMessage="Please enter a valid house ID",
                             imageSource="bad-request.svg")

        return render_template("quoted.html", data = data)


@application.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        # Obtain username inputted
        username = request.form.get("username")

        # User error handling: stop empty username and password fields, stop usernames already taken, stop non-matching passwords
        if not username:
            return errorPage(blockTitle="No Data", errorMessage = "Please enter a username", imageSource = "no-data.svg")

        existing = Users.query.filter_by(username=username)
        print("EXISTING USER: ", existing)
        #("SELECT * FROM users WHERE username = :username", username=username)
        if existing == username:
            print("EXISTING USER ALREADY!: ", existing)
            return errorPage(blockTitle="Forbidden", errorMessage = "Username already taken", imageSource="animated-403.svg")
        password = request.form.get("password")
        if not password:
            return errorPage(blockTitle="No Data", errorMessage = "Please enter a password", imageSource = "no-data.svg")
        confirmation = request.form.get("confirmation")
        if password != confirmation:
            return errorPage(blockTitle = "Unauthorized", errorMessage = "Passwords do not match", imageSource="animated-401.svg")
        hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        # All users automatically recieve $10,000,000 to start with
        cash = 10000000

        # Add and commit the data into database
        db.session.add(Users(username, hashed, cash))
        db.session.commit()
        #("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=hashed)

        # Automatically sign in after creating account
        rows = Users.query.filter_by(username=request.form.get("username")).first()
        session["user_id"] = rows.id

        # Redirect user to home page
        return redirect("/home")


@application.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # Obtain user id
    user = session["user_id"]

    if request.method == "GET":
        # Obtain properties that the user possesses
        houseList = Portfolio.query.filter_by(user_id = user).all()
        #("SELECT symbol FROM portfolio WHERE user_id = :id", id = user)

        # If user never bought anything, return empty values
        if houseList == []:
            return render_template("sell.html", houseList = houseList, houseListLength = 0)
        # Else display property symbols in drop-down menu

        else:
            houseListLength = len(houseList)
            # Render sell page with list of properties the user owns
            return render_template("sell.html", houseList = houseList, houseListLength = houseListLength)
    else:
        # Obtain property ID from user
        houseID = request.form.get("houseID")

        # If user doesn't own property, render error
        if houseID == '':
            return errorPage(blockTitle="Forbidden", errorMessage = "Must own property before selling", imageSource="animated-403.svg")


        # Obtain available cash
        availableCash = (Users.query.filter_by(id = user).first()).cash
        #("SELECT cash FROM users WHERE id = :id", id = user)

        # Obtain current price of property
        price = mytable.query.filter_by(house_id = houseID).first().proj_price
        print("price:", price)

        # Calculate new amount of available cash
        total = availableCash + price

        # Update cash field in Users Table
        update_cash = Users.query.filter_by(id = user).first()
        update_cash.cash = total
        db.session.commit()
        #("UPDATE users SET cash = :total WHERE id = :id", total = total, id = user)

        # Obtain year, month, day, hour, minute, second
        now = datetime.now()
        time = now.strftime("%d/%m/%Y %H:%M:%S")

        # Log transaction history
        log_sale = Sold(user, time, houseID, price, 0)
        db.session.add(log_sale)
        db.session.commit()
        #("INSERT INTO sold (seller_id, time, symbol, shares_sold, price_sold) VALUES (:seller_id, :time, :symbol, :shares_sold, :price_sold)", time = datetime.datetime.now(), symbol = symbol, shares_sold = shares, price_sold = price, seller_id = user)

        # remove from portfolio
        Portfolio.query.filter_by(house_id = houseID).delete()
        db.session.commit()

        # Render success page with infomation about transaction
        return render_template("sold.html", houseID = houseID)


# def errorhandler(e):
#     """Handle error"""
#     if not isinstance(e, HTTPException):
#         e = InternalServerError()
#     return apology(e.name, e.code)


# Listen for errors
# for code in default_exceptions:
#     application.errorhandler(code)(errorhandler)

@application.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

# Run Server
# Run the following in the command line: python application.py
if __name__ == '__main__':
    application.run(host='0.0.0.0')