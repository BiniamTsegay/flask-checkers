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
