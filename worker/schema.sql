CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hwid TEXT UNIQUE NOT NULL,
  ip TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  authorized INTEGER DEFAULT 0,
  location TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_users_hwid ON users(hwid);
CREATE INDEX IF NOT EXISTS idx_users_authorized ON users(authorized);
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen);
