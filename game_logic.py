from datetime import datetime
from flask import session
import sqlite3
import os
from globals import track_captured_pieces, rooms_in_use, board, manage_players_in_room

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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "biniam.db")
    datab = sqlite3.connect(db_path)
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
    