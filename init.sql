-- ======================================================
-- ETL INGESTION SCHEMA
-- ======================================================

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

-- ======================================================
-- DATA WAREHOUSE SCHEMA
-- ======================================================

-- Bookmark table to track ETL progress
CREATE TABLE IF NOT EXISTS etl_bookmark (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    last_loaded_date DATE NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(table_name)
);

-- Date Dimension
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    UNIQUE(full_date)
);

-- Games Dimension (SCD Type 1)
CREATE TABLE IF NOT EXISTS dim_games (
    game_key SERIAL PRIMARY KEY,
    appid INTEGER NOT NULL,
    name VARCHAR(500) NOT NULL,
    release_date VARCHAR(50),
    price_initial INTEGER,
    price_final INTEGER,
    price_discount_percent INTEGER,
    price_currency VARCHAR(10),
    short_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(appid)
);

-- Publishers Dimension
CREATE TABLE IF NOT EXISTS dim_publishers (
    publisher_key SERIAL PRIMARY KEY,
    publisher_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(publisher_name)
);

-- Genres Dimension
CREATE TABLE IF NOT EXISTS dim_genres (
    genre_key SERIAL PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(genre_name)
);

-- Bridge table for many-to-many relationship between games and publishers
CREATE TABLE IF NOT EXISTS bridge_game_publishers (
    game_key INTEGER NOT NULL,
    publisher_key INTEGER NOT NULL,
    PRIMARY KEY (game_key, publisher_key),
    FOREIGN KEY (game_key) REFERENCES dim_games(game_key) ON DELETE CASCADE,
    FOREIGN KEY (publisher_key) REFERENCES dim_publishers(publisher_key) ON DELETE CASCADE
);

-- Bridge table for many-to-many relationship between games and genres
CREATE TABLE IF NOT EXISTS bridge_game_genres (
    game_key INTEGER NOT NULL,
    genre_key INTEGER NOT NULL,
    PRIMARY KEY (game_key, genre_key),
    FOREIGN KEY (game_key) REFERENCES dim_games(game_key) ON DELETE CASCADE,
    FOREIGN KEY (genre_key) REFERENCES dim_genres(genre_key) ON DELETE CASCADE
);

-- Fact Table: Game Metrics
CREATE TABLE IF NOT EXISTS fact_game_metrics (
    fact_key SERIAL PRIMARY KEY,
    game_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    ccu INTEGER,
    score INTEGER,
    userscore INTEGER,
    owners VARCHAR(100),
    average_playtime INTEGER,
    median_playtime INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_key) REFERENCES dim_games(game_key) ON DELETE CASCADE,
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key) ON DELETE CASCADE,
    UNIQUE(game_key, date_key)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_fact_game_date ON fact_game_metrics(game_key, date_key);
CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_game_metrics(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_ccu ON fact_game_metrics(ccu DESC);
CREATE INDEX IF NOT EXISTS idx_dim_games_appid ON dim_games(appid);
CREATE INDEX IF NOT EXISTS idx_bridge_game_pub ON bridge_game_publishers(game_key);
CREATE INDEX IF NOT EXISTS idx_bridge_game_genre ON bridge_game_genres(game_key);

-- Populate date dimension with next 5 years of dates
INSERT INTO dim_date (date_key, full_date, day_of_week, day_name, month, month_name, quarter, year, is_weekend)
SELECT 
    TO_CHAR(d, 'YYYYMMDD')::INTEGER as date_key,
    d as full_date,
    EXTRACT(DOW FROM d) as day_of_week,
    TO_CHAR(d, 'Day') as day_name,
    EXTRACT(MONTH FROM d) as month,
    TO_CHAR(d, 'Month') as month_name,
    EXTRACT(QUARTER FROM d) as quarter,
    EXTRACT(YEAR FROM d) as year,
    CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN TRUE ELSE FALSE END as is_weekend
FROM generate_series('2020-01-01'::DATE, '2030-12-31'::DATE, '1 day'::INTERVAL) d
ON CONFLICT (full_date) DO NOTHING;

-- Initialize bookmark table
INSERT INTO etl_bookmark (table_name, last_loaded_date) 
VALUES ('fact_game_metrics', '1900-01-01') 
ON CONFLICT (table_name) DO NOTHING;