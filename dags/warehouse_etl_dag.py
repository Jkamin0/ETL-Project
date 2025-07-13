from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor
import psycopg2
import json
import logging
from typing import List, Dict, Any

default_args = {
    'owner': 'steam-data-team',
    'depends_on_past': False,
    'start_date': datetime.now() - timedelta(days=1) + timedelta(minutes=5),  # Run 5 minutes after main ETL
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'steam_warehouse_etl',
    default_args=default_args,
    description='ETL pipeline to populate Steam games data warehouse',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['warehouse', 'steam', 'dimensional'],
)

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        host='postgres',
        database='airflow',
        user='airflow',
        password='airflow'
    )

def check_initial_load(**context):
    """Check if this is the first run (initial load) or incremental"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if fact table has any data
        cur.execute("SELECT COUNT(*) FROM fact_game_metrics")
        fact_count = cur.fetchone()[0]
        
        # Check if dimensions have data
        cur.execute("SELECT COUNT(*) FROM dim_games")
        games_count = cur.fetchone()[0]
        
        if fact_count == 0 or games_count == 0:
            logging.info("First run detected - will perform initial load")
            return 'initial_load_dimensions'
        else:
            logging.info("Incremental run - will load only new data")
            return 'incremental_load_dimensions'
            
    except Exception as e:
        logging.error(f"Error checking initial load: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()

def initial_load_dimensions(**context):
    """Initial load of all dimension tables"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        logging.info("Starting initial dimension load...")
        
        # Load dim_games from games table
        cur.execute("""
            INSERT INTO dim_games (appid, name, release_date, price_initial, price_final, 
                                 price_discount_percent, price_currency, short_description)
            SELECT DISTINCT appid, name, release_date, price_initial, price_final,
                   price_discount_percent, price_currency, short_description
            FROM games
            ON CONFLICT (appid) DO UPDATE SET
                name = EXCLUDED.name,
                release_date = EXCLUDED.release_date,
                price_initial = EXCLUDED.price_initial,
                price_final = EXCLUDED.price_final,
                price_discount_percent = EXCLUDED.price_discount_percent,
                price_currency = EXCLUDED.price_currency,
                short_description = EXCLUDED.short_description,
                updated_at = CURRENT_TIMESTAMP
        """)
        
        games_loaded = cur.rowcount
        logging.info(f"Loaded {games_loaded} games into dim_games")
        
        # Load publishers
        cur.execute("""
            WITH publishers_parsed AS (
                SELECT DISTINCT appid, 
                       TRIM(publisher_name) as publisher_name
                FROM games,
                     json_array_elements_text(COALESCE(publishers::json, '[]'::json)) as publisher_name
                WHERE publishers IS NOT NULL 
                  AND publishers != '[]'
                  AND TRIM(publisher_name) != ''
            )
            INSERT INTO dim_publishers (publisher_name)
            SELECT DISTINCT publisher_name
            FROM publishers_parsed
            ON CONFLICT (publisher_name) DO NOTHING
        """)
        
        publishers_loaded = cur.rowcount
        logging.info(f"Loaded {publishers_loaded} publishers into dim_publishers")
        
        # Load genres
        cur.execute("""
            WITH genres_parsed AS (
                SELECT DISTINCT appid,
                       TRIM(genre_name) as genre_name
                FROM games,
                     json_array_elements_text(COALESCE(genres::json, '[]'::json)) as genre_name
                WHERE genres IS NOT NULL 
                  AND genres != '[]'
                  AND TRIM(genre_name) != ''
            )
            INSERT INTO dim_genres (genre_name)
            SELECT DISTINCT genre_name
            FROM genres_parsed
            ON CONFLICT (genre_name) DO NOTHING
        """)
        
        genres_loaded = cur.rowcount
        logging.info(f"Loaded {genres_loaded} genres into dim_genres")
        
        # Load bridge tables
        _load_bridge_tables(cur)
        
        conn.commit()
        logging.info("Initial dimension load completed successfully")
        
    except Exception as e:
        logging.error(f"Error in initial dimension load: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def incremental_load_dimensions(**context):
    """Incremental load of dimension tables"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        logging.info("Starting incremental dimension load...")
        
        # Get last update time
        cur.execute("SELECT MAX(updated_at) FROM dim_games")
        last_update = cur.fetchone()[0]
        
        if last_update:
            # Load only updated games
            cur.execute("""
                INSERT INTO dim_games (appid, name, release_date, price_initial, price_final, 
                                     price_discount_percent, price_currency, short_description)
                SELECT DISTINCT appid, name, release_date, price_initial, price_final,
                       price_discount_percent, price_currency, short_description
                FROM games
                WHERE updated_at > %s
                ON CONFLICT (appid) DO UPDATE SET
                    name = EXCLUDED.name,
                    release_date = EXCLUDED.release_date,
                    price_initial = EXCLUDED.price_initial,
                    price_final = EXCLUDED.price_final,
                    price_discount_percent = EXCLUDED.price_discount_percent,
                    price_currency = EXCLUDED.price_currency,
                    short_description = EXCLUDED.short_description,
                    updated_at = CURRENT_TIMESTAMP
            """, (last_update,))
            
            games_updated = cur.rowcount
            logging.info(f"Updated {games_updated} games in dim_games")
        
        # Always try to add new publishers and genres
        cur.execute("""
            WITH publishers_parsed AS (
                SELECT DISTINCT TRIM(publisher_name) as publisher_name
                FROM games,
                     json_array_elements_text(COALESCE(publishers::json, '[]'::json)) as publisher_name
                WHERE publishers IS NOT NULL 
                  AND publishers != '[]'
                  AND TRIM(publisher_name) != ''
            )
            INSERT INTO dim_publishers (publisher_name)
            SELECT DISTINCT publisher_name
            FROM publishers_parsed
            ON CONFLICT (publisher_name) DO NOTHING
        """)
        
        cur.execute("""
            WITH genres_parsed AS (
                SELECT DISTINCT TRIM(genre_name) as genre_name
                FROM games,
                     json_array_elements_text(COALESCE(genres::json, '[]'::json)) as genre_name
                WHERE genres IS NOT NULL 
                  AND genres != '[]'
                  AND TRIM(genre_name) != ''
            )
            INSERT INTO dim_genres (genre_name)
            SELECT DISTINCT genre_name
            FROM genres_parsed
            ON CONFLICT (genre_name) DO NOTHING
        """)
        
        # Refresh bridge tables
        _load_bridge_tables(cur)
        
        conn.commit()
        logging.info("Incremental dimension load completed successfully")
        
    except Exception as e:
        logging.error(f"Error in incremental dimension load: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def _load_bridge_tables(cur):
    """Load bridge tables for many-to-many relationships"""
    
    # Clear and reload game-publisher bridge
    cur.execute("DELETE FROM bridge_game_publishers")
    cur.execute("""
        WITH publishers_parsed AS (
            SELECT g.appid, dg.game_key, TRIM(publisher_name) as publisher_name
            FROM games g
            JOIN dim_games dg ON g.appid = dg.appid,
                 json_array_elements_text(COALESCE(g.publishers::json, '[]'::json)) as publisher_name
            WHERE g.publishers IS NOT NULL 
              AND g.publishers != '[]'
              AND TRIM(publisher_name) != ''
        )
        INSERT INTO bridge_game_publishers (game_key, publisher_key)
        SELECT DISTINCT pp.game_key, dp.publisher_key
        FROM publishers_parsed pp
        JOIN dim_publishers dp ON pp.publisher_name = dp.publisher_name
    """)
    
    # Clear and reload game-genre bridge
    cur.execute("DELETE FROM bridge_game_genres")
    cur.execute("""
        WITH genres_parsed AS (
            SELECT g.appid, dg.game_key, TRIM(genre_name) as genre_name
            FROM games g
            JOIN dim_games dg ON g.appid = dg.appid,
                 json_array_elements_text(COALESCE(g.genres::json, '[]'::json)) as genre_name
            WHERE g.genres IS NOT NULL 
              AND g.genres != '[]'
              AND TRIM(genre_name) != ''
        )
        INSERT INTO bridge_game_genres (game_key, genre_key)
        SELECT DISTINCT gp.game_key, dg.genre_key
        FROM genres_parsed gp
        JOIN dim_genres dg ON gp.genre_name = dg.genre_name
    """)

def load_fact_table(**context):
    """Load fact table with game metrics"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        logging.info("Starting fact table load...")
        
        # Get last loaded date from bookmark
        cur.execute("SELECT last_loaded_date FROM etl_bookmark WHERE table_name = 'fact_game_metrics'")
        result = cur.fetchone()
        last_loaded_date = result[0] if result else datetime(1900, 1, 1).date()
        
        logging.info(f"Loading fact data from {last_loaded_date}")
        
        # Load fact data
        cur.execute("""
            INSERT INTO fact_game_metrics (game_key, date_key, ccu, score, userscore, 
                                         owners, average_playtime, median_playtime)
            SELECT 
                dg.game_key,
                TO_CHAR(sd.recorded_date, 'YYYYMMDD')::INTEGER as date_key,
                sd.ccu,
                sd.score,
                sd.userscore,
                sd.owners,
                sd.average_playtime,
                sd.median_playtime
            FROM steamspy_data sd
            JOIN dim_games dg ON sd.appid = dg.appid
            JOIN dim_date dd ON TO_CHAR(sd.recorded_date, 'YYYYMMDD')::INTEGER = dd.date_key
            WHERE sd.recorded_date > %s
            ON CONFLICT (game_key, date_key) DO UPDATE SET
                ccu = EXCLUDED.ccu,
                score = EXCLUDED.score,
                userscore = EXCLUDED.userscore,
                owners = EXCLUDED.owners,
                average_playtime = EXCLUDED.average_playtime,
                median_playtime = EXCLUDED.median_playtime
        """, (last_loaded_date,))
        
        facts_loaded = cur.rowcount
        logging.info(f"Loaded {facts_loaded} fact records")
        
        # Update bookmark with latest date
        cur.execute("SELECT MAX(recorded_date) FROM steamspy_data")
        max_date = cur.fetchone()[0]
        
        if max_date:
            cur.execute("""
                UPDATE etl_bookmark 
                SET last_loaded_date = %s, updated_at = CURRENT_TIMESTAMP
                WHERE table_name = 'fact_game_metrics'
            """, (max_date,))
            
            logging.info(f"Updated bookmark to {max_date}")
        
        conn.commit()
        logging.info("Fact table load completed successfully")
        
    except Exception as e:
        logging.error(f"Error loading fact table: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

# Define tasks
check_load_type = BranchPythonOperator(
    task_id='check_load_type',
    python_callable=check_initial_load,
    dag=dag,
)

initial_dims_task = PythonOperator(
    task_id='initial_load_dimensions',
    python_callable=initial_load_dimensions,
    dag=dag,
)

incremental_dims_task = PythonOperator(
    task_id='incremental_load_dimensions',
    python_callable=incremental_load_dimensions,
    dag=dag,
)

load_facts_task = PythonOperator(
    task_id='load_fact_table',
    python_callable=load_fact_table,
    dag=dag,
    trigger_rule='none_failed_or_skipped',
)


# Set task dependencies
check_load_type
check_load_type >> [initial_dims_task, incremental_dims_task]
[initial_dims_task, incremental_dims_task] >> load_facts_task