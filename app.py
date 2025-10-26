from flask import Flask, render_template, request, session, redirect, request
from flask_session import Session
import random
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from password_validator import PasswordValidator
import sqlite3
import os
from dotenv import load_dotenv
import secrets



# Setup flask
app =Flask(__name__)

#red variables in .env file
load_dotenv()

# assign secret key
secret = os.getenv("secret_key")
app.secret_key = secret

# Setup session config
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["TEMPLATES_AUTO_RELOAD"] = True
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# For password validation
schema = PasswordValidator()
schema\
.min(8)\
.max(100)\
.has().uppercase()\
.has().lowercase()\
.has().digits()\
.has().no().spaces()\

# define login_required to require login for some views or routes

def login_required(f):
    """Adopted from Login required Decorator at this url
    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/"""

    @wraps(f)
    def decorated_inner_function(*args, **kwargs):
        # if player is not logged in redirect to login page
        if session.get("player_id") is None:
            return redirect("/login")
        return f(*args,*kwargs)
    return decorated_inner_function


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method=="POST":
        # clear any previous session
        session.clear()
        # assign the forms field to variables
        username = request.form.get("username")
        password = request.form.get("password")
        # validate input
        if not username:
            return render_template("apology.html", reason="Please enter your username")
        elif not password:
            return render_template("apology.html", reason ="Please enter your password")
        # check if the user is in database and query hashed password and player id
        datab = sqlite3.connect("biniam.db")
        db=datab.cursor()
        # This return tuple
        rows = db.execute("SELECT * FROM players WHERE user_name = ?", (username,))
        rows = rows.fetchone()
        
        # if user is not in database redirect to register page
        if rows is None:
            return redirect("/register")

        # check if the password and hashed password match
        elif not check_password_hash(rows[2],password):
            return render_template("apology.html", reason="Password and username did not match")
        # add user's session and redirect to homepage
        session["player_id"] =rows[0]
        datab.commit()
        datab.close()
        return redirect("/")

    return render_template("login.html")
  
@app.route("/register", methods=["POST","GET"])
def register():
    if request.method =="POST":
        # TODO:
        # assign the forms fields to variables
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # hashing password
        generate_hashed_password = generate_password_hash(password)
        # connect to database
        datab = sqlite3.connect("biniam.db")
        db = datab.cursor()
        # check if username is already in database
        rows = db.execute("SELECT user_name from players WHERE user_name =?", (username,))

        
        # check if username is filled
        if not username:
            return render_template("apology.html", reason="Please Enter a Username")
        
        # check if the password is validated password
        elif schema.validate(password) == False:
            return render_template("apology.html", reason="Please Enter a valid password")
         # check if the password matches
        elif password != confirmation:
            return render_template("apology.html", reason="Password did not match")
        # Check if the usernamme is available
        elif len(rows.fetchall())!=0:
            return render_template("apology.html", reason="Username is already taken")
        
        # register player in to database
        else:
            try:
                db.execute("INSERT INTO players(user_name, hash_password) VALUES (?,?)", (username, generate_hashed_password))
                datab.commit()
                datab.close()
                return redirect("/login")
            except Exception:
                return render_template("apology.html", reason="Something went wrong. We could not register you. Try again.")


        
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    """Log user out"""
    session.clear()
    return redirect("/login")

# randomly generating room number
room_number =random.randint(1000, 9999)



if __name__ == "__main__":
    app.run(debug=True)
