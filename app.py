from flask import Flask, render_template, request, session, redirect, request
from flask_session import Session
import random
from temp import login_required
from werkzeug.security import check_password_hash, generate_password_hash
from password_validator import PasswordValidator
import sqlite3

# Setup flask
app =Flask(__name__)
# Setup session
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




@app.route("/")
#@login_required
def index():
    return render_template("index.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method=="POST":
        # clear any previous session
        # assign the forms field to variables
    
        # validate input
        # check if the user is in database and query hashed password and player id
        # check if the password and hashed password match
        # add user's session and redirect to homepage
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

# randomly generating room number
room_number =random.randint(1000, 9999)



if __name__ == "__main__":
    app.run(debug=True)
