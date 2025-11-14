# imports
from flask import Flask, render_template, request, session, redirect, request, flash
from flask_session import Session
import random
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from password_validator import PasswordValidator
import sqlite3
import os
from dotenv import load_dotenv
import secrets
from flask_socketio import SocketIO, join_room, leave_room, emit,send
from datetime import datetime
import copy

# global variables

# To track all rooms in use
rooms_in_use=[]

# Manage players in a room 
manage_players_in_room = {}

# for tracking captured pieces by a player in a room
track_captured_pieces = {}


# To track 8x8 board data
columns = 8
rows = 8
board = {}


# populate the board with data
for row in range(rows):
    for column in range(columns):
        if (row + column) % 2 !=0:
            id = row * 8 + column + 1
            # at the start of the game player 1 places his 12 pieces in the first 24 cells
            if id <= 24:
                board[id] = ["♟", "black"]
            # at the start of the game player 2 places his 12 pieces in the last 24 cells
            elif id >=41:
                board[id] =["♟", "green"]
            else:
                board[id]=["",""]

# Setup flask
app =Flask(__name__)

#read variables in .env file
load_dotenv()

# assign secret key
secret = os.getenv("secret_key")
app.secret_key = secret

# set flask-socketio
socketio = SocketIO(app)

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

@app.route("/room", methods=["POST", "GET"])
@login_required
def room():
    if request.method=="POST":

        start_game=request.form.get("start")
        join_into_room = request.form.get("join_room")
        # if user start a game
        if start_game =="":
            # randomly generating room number
            while True:
                room_number =random.randint(1000, 9999)
                if room_number not in rooms_in_use:
                    break
            message= f"Send {room_number} to let your buddy join."
            flash(message)
            rooms_in_use.append(room_number)
            # store room in session
            session["room"] = room_number
            # the one that start the game controls black
            session["color"] ="black"
            return render_template("room.html", place=session["color"], rotate="180deg")
        # try to change into int
        try:
            join_into_room =int(join_into_room)
        except Exception:
            return render_template("apology.html", reason = "The room is invalid")
        
        # if user is joining using room_code
        if not join_into_room:
            return render_template("apology.html", reason ="Please Enter a room number")
        # check if the room exist
        if join_into_room not in rooms_in_use:
            return render_template("apology.html", reason="Try again! Room does not exist")
        # limit to only two users per room
        
        #store the room in session
        session["room"] = join_into_room
        # the one that joins controls the green
        session["color"]="green"
        # to track if the user has joined
        rooms_in_use.append(join_into_room)
        
        return render_template("room.html", place=session["color"], rotate="0deg")

    return render_template("join.html")

@app.route("/leaderboard")
@login_required
def leaderboard():
    """Show the players with the highest 100 scores"""
    datab = sqlite3.connect("biniam.db")
    db = datab.cursor()
    rows =db.execute("SELECT user_name, score FROM players ORDER BY score DESC LIMIT 100").fetchall()
    datab.commit()
    datab.close()
    return render_template("leaderboard.html", rows=rows)


# establish connection between users and add them to a room
@socketio.on("connect")
def connect():
    # limit connection to only two users
    
    if members_joined() > 2:
        return 

    room=session.get("room")
    if not room:
        return
    join_room(room)
    # to manage players in the joined room
    if room not in manage_players_in_room:
        manage_players_in_room[room]={}
    
    # to track the captured pieces by a player
    if room not in track_captured_pieces:
        track_captured_pieces[room] ={}
    # assign black pieces to player 1 and green to player 2
    if session.get("color")=="black":
        manage_players_in_room[room]["player_1"] = request.sid
        track_captured_pieces[room]["player_1"]=[]
        

    elif session.get("color")=="green":
        manage_players_in_room[room]["player_2"]= request.sid
        track_captured_pieces[room]["player_2"]=[]
    # track captured id so a player can continue from where he stoped if he has leftover piece
    manage_players_in_room[room]["track_capture"]=0
    manage_players_in_room[room]["prevous_turn"] = None
    manage_players_in_room[room]["board"] = copy.deepcopy(board)
    #give few seconds chance to capture any leftover pieces
    manage_players_in_room[room]["time"]= None
    manage_players_in_room[room]["winner"]= None

  
@socketio.on("disconnect")
def disconnect():
    """emit game over """
    room = session.get("room")
    if manage_players_in_room[room]["winner"] == None:
        if request.sid == manage_players_in_room[room]["player_1"]:
            emit("gameover", {"winner":"player_2"}, broadcast=True)
            manage_players_in_room[room]["winner"] = "player_2"
        else:
            emit("gameover", {"winner":"player_1"}, broadcast=True)
            manage_players_in_room[room]["winner"] = "player_1"
    

# handle quit
@socketio.on("quit")
def quit(data):
    # determine who is the quiter
    room = session.get("room")
    if data == manage_players_in_room[room]["player_1"]:
        emit("gameover", {"winner":"player_2"}, broadcast=True)
        manage_players_in_room[room]["winner"] = "player_2"
    else:
        emit("gameover", {"winner":"player_1"}, broadcast=True)
        manage_players_in_room[room]["winner"] = "player_1"


 # handling movement  

@socketio.on("move") 
def handle_move(data):
    global manage_players_in_room
    
    room=session.get("room")
    player_1 = manage_players_in_room[room]["player_1"]
    player_2 = manage_players_in_room[room]["player_2"]
    origin_piece = data.get("origin_piece")
    moved_by =data.get("moved_by")
    origin_piece_color = data.get("origin_piece_color")
    target_piece = data.get("target_piece")
    origin_id = data.get("origin_id")
    target_id = data.get("target_id")
    validated_result = {"captured":None, "valid_move":False, "crown":False, 
                        "origin_piece":origin_piece, "origin_color": origin_piece_color,
                        "origin_id":origin_id, "target_id":target_id
                        }

    # check if the players are moving their piece
    if moved_by == request.sid and origin_piece_color == session.get("color"):
        pass
    else:
        return
    #check if the origin is not empty cell
    if origin_piece == "":
        return
    
    # manage turns
    if manage_turns(room, moved_by, origin_id, data) == False:
        print("349")
        return
    # check if the move is forward
    if check_move_forward(origin_id, moved_by, player_1, target_id, player_2, origin_piece) == False:
        return
        
    # if the players joined are not  2 players can not move their pieces
    if members_joined() != 2:
        return

    # check if the target cell is empty
    if target_piece!= "":
        return
    
    # if the jump was invalid 
    if handle_invalid_jump(data, moved_by, target_id, origin_id, origin_piece, player_1, player_2) == False:
        return
    # manage capture
    validated_result["captured"] = manage_captures(room,data,moved_by, player_1, target_id, origin_id)
    # if player did not capture check if he had a capture, players are forced to capture 
    if data["movement_path"]["try_capture"] == False:
        if force_capture(room, player_1, player_2, moved_by):
            return
        
    # check if the piece will be crowned
    crowning_locations = [2,4,6,8,57,59,61,63]
    if target_id in crowning_locations:
        validated_result["crown"] = True

    
    validated_result["valid_move"]=True
    emit("handled_move", validated_result, broadcast= True)
    # finalizing move
    current_player=request.sid
    finalize_player_move(room,data,origin_id, target_id, origin_piece, origin_piece_color, current_player)
    
    # check if the game is over
    if detect_winner() == "player_1":
        emit("gameover", {"winner":"player_1"}, broadcast=True)
        manage_players_in_room[room]["winner"] = "player_1"
        return
    elif detect_winner() =="player_2":
        emit("gameover", {"winner":"player_2"}, broadcast=True)
        manage_players_in_room[room]["winner"] = "player_2"
        return
 
    return

@socketio.on("after_game")
def handle_aftergame(data):
    room= session.get("room")
    add_score(data)
    leave_room(room)
    # delete anything associated with the room
    if room in manage_players_in_room:
        del manage_players_in_room[room]
    if room in track_captured_pieces:
        del track_captured_pieces[room]
    while room in rooms_in_use:
        rooms_in_use.remove(room)
    
    

def add_score(player):
    """add 10 points to the winner"""
    # if winner is player 1 he is black
    if player == "player_1":
        if session.get("color") == "black":
            player_id = session.get("player_id")
        else:
            return
    else:
        if session.get("color") =="green":
            player_id = session.get("player_id")
        else:
            return
        

    score_gain = 10
    datab = sqlite3.connect("biniam.db")
    db = datab.cursor()
    db.execute("SELECT score FROM players WHERE id= ?", (player_id, ))
    score = db.fetchone()[0]
    db.execute("UPDATE players SET score = ? WHERE id = ?",(score + score_gain, player_id) )

    datab.commit()
    datab.close()


    


def handle_invalid_jump(data, moved_by,target_id, origin_id, origin_piece, player_1, player_2):

    """returns false if jump was invalid"""


    if data["movement_path"]["try_capture"] == True:
        jumping_path = data.get("movement_path")
        # check who the player is and if the movement is forward
        if moved_by == player_1 and(target_id != origin_id + 14 and target_id != origin_id + 18) and origin_piece == "♟":
            return False

        if moved_by == player_2 and (target_id != origin_id - 14 and target_id != origin_id - 18) and origin_piece == "♟":
            return False
        # king only jump +-14 or +-18
        if origin_piece !="♟": 
            valid_jumps_for_king=[origin_id + 14, origin_id -14, origin_id + 18, origin_id -18]
            if target_id not in valid_jumps_for_king:
                return False
            

        # possible moves for jumping
        possible_moves ={origin_id + 18:[jumping_path["o+x+1"][2],jumping_path["o+x+1"][1],player_1], 
                  origin_id + 14:[jumping_path["o+x-1"][2], jumping_path["o+x-1"][1],player_1], 
                  origin_id - 18:[jumping_path["o-x-1"][2], jumping_path["o-x-1"][1], player_2], 
                  origin_id - 14:[jumping_path["o-x+1"][2], jumping_path["o-x+1"][1], player_2 ]
                  }
        # check if there is valid piece to be captured
        
        for move in possible_moves:
            if target_id ==move:
                if origin_piece =="♟" and (possible_moves[move][0] != "♟" or possible_moves[move][1]== session.get("color")) and moved_by==possible_moves[move][2]:
                    return False
                # if king is the one trying to capture
                elif origin_piece != "♟" and (possible_moves[move][0] =="" or possible_moves[move][1]== session.get("color")):
                    return False
    
    return True
        



def members_joined():
    """This tracks the number of users in a room"""
    return rooms_in_use.count(session["room"])

def check_move_forward(origin_id, moved_by, player_1, target_id, player_2, origin_piece):

    player_1_possible_move=[origin_id + 7, origin_id + 9, origin_id + 14, origin_id + 18]
    player_2_possible_move =[origin_id - 7, origin_id - 9, origin_id - 14, origin_id - 18]
    
    if moved_by==player_1:
        if target_id not in player_1_possible_move and origin_piece =="♟":
            return False
        
    elif moved_by==player_2:
        if target_id not in player_2_possible_move and origin_piece =="♟":
            return False

def manage_captures(room,data,moved_by, player_1, target_id, origin_id):

    # once there is capture add it it to the players captured list
    # Using None to save memory space because type is not neccessary. The only thing that matter is count
    if data["movement_path"]["try_capture"] == True:
        if moved_by==player_1:
            track_captured_pieces[room]["player_1"].append(None)
        else:
            track_captured_pieces[room]["player_2"].append(None)
        # dynamically figure out the captured item
        return origin_id + (target_id - origin_id)//2
    else:
        return None
        
        

def manage_turns(room, moved_by, origin_id, data):

     # manage turns
    if manage_players_in_room[room]["prevous_turn"] == moved_by and manage_players_in_room[room]["track_capture"] ==0:
        return False
    
    # let the current player wait few sec incase the prevous player has to capture leftover piece
    if moved_by != manage_players_in_room[room]["prevous_turn"]  and manage_players_in_room[room]["track_capture"] != 0:
        if (datetime.now() - manage_players_in_room[room]["time"]).total_seconds() < 4:
            return False
    # if the prevous player after making capture is not making the next capture from where he stoped it is invalid
    if moved_by == manage_players_in_room[room]["prevous_turn"] and origin_id != manage_players_in_room[room]["track_capture"]:
        return False
    # if the prevous player does not have a leftover to capture the player can not make a move
    if manage_players_in_room[room]["prevous_turn"] == moved_by and data["movement_path"]["try_capture"] == False:
        return False

def detect_winner():
    """Figure out who the winner is depending on the captures, if all pieces are captured which are 12 
    We have a winner"""
    #TODO: there are some stuff do be done yet not complete yet
    room= session.get("room")
    if len(track_captured_pieces[room]["player_1"]) == 12:
        return "player_1"
    elif len(track_captured_pieces[room]["player_2"]) == 12:
        return "player_2"

def finalize_player_move(room,data,origin_id, target_id, origin_piece, origin_piece_color, current_player):
    global manage_players_in_room

    if data["movement_path"]["try_capture"] == True:
        manage_players_in_room[room]["track_capture"]=target_id
        # if the above code excuted it means there was valid capture
        # the board needs to be update
        captured_id = origin_id + ((target_id - origin_id)//2)
        manage_players_in_room[room]["board"][captured_id][0]=""
        manage_players_in_room[room]["board"][captured_id][1]=""

    else:
        # since there was no capture no need to track leftover pieces
        manage_players_in_room[room]["track_capture"] = 0
    # saving prevous player id once the player make the move so that they can not make anauthorized move
    manage_players_in_room[room]["prevous_turn"] = current_player
    # to store the time a valid move was done. It will be used when a player capture a piece and may have a leftover
    # so the next player waits few seconds before making his move
    manage_players_in_room[room]["time"] = datetime.now()
    manage_players_in_room[room]["board"][origin_id][0] =""
    manage_players_in_room[room]["board"][origin_id][1] =""
    manage_players_in_room[room]["board"][target_id][0] = origin_piece
    manage_players_in_room[room]["board"][target_id][1] = origin_piece_color
    

def force_capture(room, player_1, player_2, moved_by):
    """To force capture if there is a capture""" 
    global manage_players_in_room
    board_state = manage_players_in_room[room]["board"]
    print(manage_players_in_room[room])
    print(board_state)
    print(board)
    
    for cell in manage_players_in_room[room]["board"]:
        
        piece = manage_players_in_room[room]["board"][cell][0]
        color = manage_players_in_room[room]["board"][cell][1]

        originplus14_piece = board_state.get(cell + 14, [None])[0]
        originplus18_piece = board_state.get(cell + 18, [None])[0]
        originminus14_piece = board_state.get(cell - 14, [None])[0]
        originminus18_piece = board_state.get(cell - 18, [None])[0]
        originplus7_piece = board_state.get(cell + 7, [None])[0]
        originplus7_color = board_state.get(cell + 7, [None, None])[1]
        originplus9_piece = board_state.get(cell + 9, [None])[0]
        originplus9_color = board_state.get(cell + 9, [None, None])[1]
        originminus7_piece = board_state.get(cell - 7, [None])[0]
        originminus7_color = board_state.get(cell - 7, [None, None])[1]
        originminus9_piece = board_state.get(cell -9, [None])[0]
        originminus9_color = board_state.get(cell -9, [None, None])[1]
        print(piece, color, cell)
    
        if moved_by == player_1 and piece =="♟" and color=="black":
            # check if there is a piece that needs to be captured return true
            # in order to capture the destination must be empty the middle piece must be "♟" and the color must be different
            if originplus14_piece=="" and originplus7_piece== "♟" and color != originplus7_color:
                print("492")
                print("+14=", originplus14_piece, "+7=", originplus7_piece, "+7color=", originplus7_color)
                return True
                
            
            if originplus18_piece=="" and originplus9_piece== "♟" and color != originplus9_color:
                print("497")
                print("+18=", originplus18_piece, "+9=", originplus9_piece, "+9color=", originplus9_color)
                return True
        
        if moved_by==player_2 and piece=="♟" and color=="green":

            if originminus14_piece=="" and originminus7_piece== "♟" and color != originminus7_color:
                print("503")
                print("-14=", originminus14_piece, "-7=", originminus7_piece, "-7color=", originminus7_color)
                return True
            
            if originminus18_piece=="" and originminus9_piece== "♟" and color != originminus9_color:
                print("509")
                print("-18=", originminus18_piece, "-9=", originminus9_piece, "-9color=", originminus9_color)
                return True
        
        # for kings
        if ((moved_by == player_1 and color=="black") or (moved_by== player_2 and color=="green")) and piece=="♚":

            if originplus14_piece =="" and (originplus7_piece != "" and originplus7_piece !="♟") and color != originplus7_color:
                return True
            
            if originplus18_piece=="" and (originplus9_piece != "" and originplus9_piece != "♟") and color != originplus9_color:
                return True
            
            if originminus18_piece=="" and (originminus9_piece != "" and originminus9_piece != "♟") and color != originminus9_color:
                return True
            
            if originminus14_piece=="" and (originminus7_piece != "" and originminus7_piece != "♟") and color != originminus7_color:
                return True
    



   

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)

