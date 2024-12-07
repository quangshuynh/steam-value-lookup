CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL UNIQUE,
    username TEXT,
    profile_url TEXT
);

CREATE TABLE game (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT,
    playtime INTEGER,
    value REAL,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

CREATE TABLE inventory_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    game_id INTEGER,
    name TEXT,
    value REAL,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (game_id) REFERENCES game (id)
);
