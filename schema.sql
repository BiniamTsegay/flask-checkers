CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL UNIQUE,
    hash_password TEXT NOT NULL, 
    score INTEGER DEFAULT 0
);