CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    salt TEXT,
    hash_password TEXT NOT NULL
);