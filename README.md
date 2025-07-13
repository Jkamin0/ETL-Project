# Steam Games ETL Pipeline

An Airflow-based ETL pipeline that fetches Steam game data and stores it in a PostgreSQL data warehouse, all running in Docker containers.

## What it does

1. **Fetches top 100 games** from the SteamSpy API (most played in the last 2 weeks)
2. **Enriches each game** with detailed metadata from the Steam Store API
3. **Stores data** in a PostgreSQL data warehouse with a star schema including:
   - Dimension tables for games, publishers, genres, and dates
   - Bridge tables to model many-to-many relationships (e.g., games to genres and publishers)
   - A fact table capturing daily game performance metrics
4. **Supports incremental loads** using a bookmarking system to track the latest data processed and avoid duplicates
5. **Pipeline orchestration** split into two coordinated Airflow DAGs:
   - Raw data ingestion DAG
   - Warehouse processing DAG that normalizes JSON and loads dimensional & fact tables

## Quick Start

1. **Clone/download all files**
2. **Make setup script executable**: `chmod +x setup.sh`
3. **Run setup**: `./setup.sh`
4. **Wait 2-3 minutes** for initialization, including table creation and initial loads
5. **Open Airflow UI**: [http://localhost:8080](http://localhost:8080) (admin/admin)

## Usage

- **Start pipeline**: Enable the `steam_games_etl` DAG in the Airflow UI
- **Manual run**: Click the "Trigger DAG" button
- **Schedule**: Runs once per day automatically
- **Monitor**: Check task and DAG status in Airflow UI

## Database Access

Connect to PostgreSQL:

- **Host**: localhost:5432
- **Database**: airflow
- **Username**: airflow
- **Password**: airflow

## Trending Analysis Examples

```sql
-- See how a specific game's CCU changed over the last month
SELECT dg.name, fgm.ccu, dd.full_date
FROM fact_game_metrics fgm
JOIN dim_games dg ON fgm.game_key = dg.game_key
JOIN dim_date dd ON fgm.date_key = dd.date_key
WHERE dg.appid = 1089350
  AND dd.full_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY dd.full_date;

-- Average CCU by day of week for top games
SELECT
    dg.name,
    dd.day_of_week,
    AVG(fgm.ccu) as avg_ccu
FROM fact_game_metrics fgm
JOIN dim_games dg ON fgm.game_key = dg.game_key
JOIN dim_date dd ON fgm.date_key = dd.date_key
WHERE dd.full_date >= CURRENT_DATE - INTERVAL '30 days'
  AND dg.appid IN (
      SELECT dg2.appid
      FROM fact_game_metrics fgm2
      JOIN dim_games dg2 ON fgm2.game_key = dg2.game_key
      JOIN dim_date dd2 ON fgm2.date_key = dd2.date_key
      WHERE dd2.full_date = CURRENT_DATE
      ORDER BY fgm2.ccu DESC LIMIT 10
  )
GROUP BY dg.name, dd.day_of_week
ORDER BY dg.name, dd.day_of_week;
```
