-- Create games table
CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    appid INTEGER UNIQUE NOT NULL,
    name VARCHAR(500),
    price_initial INTEGER,
    price_final INTEGER,
    price_discount_percent INTEGER,
    price_currency VARCHAR(10),
    release_date VARCHAR(50),
    short_description TEXT,
    developers TEXT,
    publishers TEXT,
    categories TEXT,
    genres TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create steamspy_data table
CREATE TABLE IF NOT EXISTS steamspy_data (
    id SERIAL PRIMARY KEY,
    appid INTEGER NOT NULL,
    name VARCHAR(500),
    score INTEGER,
    userscore INTEGER,
    owners VARCHAR(100),
    average_playtime INTEGER,
    median_playtime INTEGER,
    ccu INTEGER,
    recorded_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (appid) REFERENCES games(appid) ON DELETE CASCADE,
    UNIQUE(appid, recorded_date)  -- One record per game per day
);

-- Create indexes for queries
CREATE INDEX IF NOT EXISTS idx_steamspy_appid_date ON steamspy_data(appid, recorded_date);
CREATE INDEX IF NOT EXISTS idx_steamspy_date ON steamspy_data(recorded_date);
CREATE INDEX IF NOT EXISTS idx_steamspy_ccu ON steamspy_data(ccu DESC);