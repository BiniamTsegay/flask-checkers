
"""This is backup"""

# a variable to track if the player has another capture allowed
track_capture= 0

# a variable to figure out whose turn is and player 1 starts the game
prevous_turn= None
 # handling movement  
@socketio.on("move") 
def handle_move(data):
    global track_capture
    global determine_turn
    global prevous_turn
    
    
    
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
    
    if prevous_turn == moved_by and track_capture ==0:
        print("here")
        return   

    # if the prevous player does not have a leftover to capture the player can not make a move
    if prevous_turn == moved_by and data["movement_path"]["try_capture"] == False:
        return
    # check if the move is forward
    player_1_possible_move=[origin_id + 7, origin_id + 9, origin_id + 14, origin_id + 18]
    player_2_possible_move =[origin_id - 7, origin_id - 9, origin_id - 14, origin_id - 18]
    
    if moved_by==player_1:
        if target_id not in player_1_possible_move and origin_piece =="♟":
            return
        
    elif moved_by==player_2:
        if target_id not in player_2_possible_move and origin_piece =="♟":
            return
        
    # if the players joined are not  2 players can not move their pieces
    if members_joined() != 2:
        return

    # check if the target cell is empty
    if target_piece!= "":
        return
    
    
    
    # check if the movement was just single move or a jump trying to capture
    if data["movement_path"]["try_capture"] == True:
        jumping_path = data.get("movement_path")
        # check who the player is and if the movement is forward
        if moved_by == player_1 and(target_id != origin_id + 14 and target_id != origin_id + 18) and origin_piece == "♟":
            return

        if moved_by == player_2 and (target_id != origin_id - 14 and target_id != origin_id - 18) and origin_piece == "♟":
            return
        # king only jump +-14 or +-18
        if origin_piece !="♟": 
            valid_jumps_for_king=[origin_id + 14, origin_id -14, origin_id + 18, origin_id -18]
            if target_id not in valid_jumps_for_king:
                return
            

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
                    return
                # if king is the one trying to capture
                elif origin_piece != "♟" and (possible_moves[move][0] =="" or possible_moves[move][1]== session.get("color")):
                    return
        

        # dynamically figure out the captured item
        captured_piece = (target_id - origin_id)//2
        validated_result["captured"] =origin_id + captured_piece
    # check if the piece will be crowned
    crowning_locations = [2,4,6,8,57,59,61,63]
    if target_id in crowning_locations:
        validated_result["crown"] = True

    
    validated_result["valid_move"]=True
    emit("handled_move", validated_result, broadcast= True)
    # to track the players turn and if the player has any leftover captures
    if data["movement_path"]["try_capture"] == True:
        track_capture=target_id
    else:
        track_capture = 0
    # saving prevous players id so that they can not make anauthorized move
    prevous_turn = request.sid
        # since there was no capture no need to track leftover pieces
    

    print(data)
    
    return
