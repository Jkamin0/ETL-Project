# Steam Games ETL Pipeline

A Airflow-based ETL pipeline that fetches Steam game data and stores it in PostgreSQL, all running in Docker containers.

## What it does

1. **Fetches top 100 games** from SteamSpy API (most played in last 2 weeks)
2. **Enriches each game** with detailed data from Steam Store API
3. **Stores everything** in a PostgreSQL database

## Quick Start

1. **Clone/download all files**
2. **Make setup script executable**: `chmod +x setup.sh`
3. **Run setup**: `./setup.sh`
4. **Wait 2-3 minutes** for initialization
5. **Open Airflow UI**: http://localhost:8080 (admin/admin)

## Usage

- **Start pipeline**: Enable the `steam_games_etl` DAG in Airflow UI
- **Manual run**: Click "Trigger DAG" button
- **Schedule**: Runs once per day automatically
- **Monitor**: Check task status in Airflow UI

## Database Access

Connect to PostgreSQL:

- **Host**: localhost:5432
- **Database**: airflow
- **Username**: airflow
- **Password**: airflow

## Trending Analysis Examples

```sql
-- See how a specific game's CCU changed over the last month
SELECT name, ccu, recorded_date
FROM steamspy_data
WHERE appid = 1089350
  AND recorded_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY recorded_date;

-- Average CCU by day of week for top games
SELECT
    name,
    EXTRACT(DOW FROM recorded_date) as day_of_week,
    AVG(ccu) as avg_ccu
FROM steamspy_data
WHERE recorded_date >= CURRENT_DATE - INTERVAL '30 days'
  AND appid IN (
      SELECT appid FROM steamspy_data
      WHERE recorded_date = CURRENT_DATE
      ORDER BY ccu DESC LIMIT 10
  )
GROUP BY name, appid, EXTRACT(DOW FROM recorded_date)
ORDER BY name, day_of_week;
```
