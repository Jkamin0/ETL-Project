from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import psycopg2
import json
import time
import logging

default_args = {
    'owner': 'steam-data-team',
    'depends_on_past': False,
    'start_date': datetime.now() - timedelta(days=1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'steam_games_etl',
    default_args=default_args,
    description='Extract Steam games data from SteamSpy and Steam APIs',
    schedule_interval=timedelta(days=1),  # Run once per day
    catchup=False,
    tags=['steam', 'games', 'etl'],
)

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        host='postgres',
        database='airflow',
        user='airflow',
        password='airflow'
    )

def fetch_top_games(**context):
    """Fetch top 100 games from SteamSpy API"""
    logging.info("Fetching top 100 games from SteamSpy...")
    
    url = "https://steamspy.com/api.php"
    params = {
        'request': 'top100in2weeks'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        games_data = response.json()
        
        # Extract just the app IDs and basic info
        top_games = []
        for appid, game_info in games_data.items():
            if appid.isdigit():
                top_games.append({
                    'appid': int(appid),
                    'name': game_info.get('name', ''),
                    'score': game_info.get('score', 0),
                    'userscore': game_info.get('userscore', 0),
                    'owners': game_info.get('owners', ''),
                    'average_playtime': game_info.get('average_forever', 0),
                    'median_playtime': game_info.get('median_forever', 0),
                    'ccu': game_info.get('ccu', 0)
                })
        
        logging.info(f"Successfully fetched {len(top_games)} games from SteamSpy")
        
        # Store in XCom for next task
        context['task_instance'].xcom_push(key='steamspy_games', value=top_games)
        
        return len(top_games)
        
    except Exception as e:
        logging.error(f"Error fetching SteamSpy data: {str(e)}")
        raise

def enrich_with_steam_data(**context):
    """Enrich games data with Steam Store API data"""
    steamspy_games = context['task_instance'].xcom_pull(key='steamspy_games')
    
    if not steamspy_games:
        logging.error("No SteamSpy games data found")
        raise ValueError("No SteamSpy games data found")
    
    logging.info(f"Enriching {len(steamspy_games)} games with Steam Store data...")
    
    enriched_games = []
    
    for i, game in enumerate(steamspy_games):
        try:
            appid = game['appid']
            logging.info(f"Processing game {i+1}/{len(steamspy_games)}: {game['name']} (ID: {appid})")
            
            # Fetch detailed info from Steam Store API
            steam_url = f"https://store.steampowered.com/api/appdetails"
            steam_params = {
                'appids': appid,
                'filters': 'price_overview,basic,release_date,developers,publishers,categories,genres'
            }
            
            steam_response = requests.get(steam_url, params=steam_params, timeout=15)
            steam_response.raise_for_status()
            steam_data = steam_response.json()
            
            # Extract Steam data
            app_data = steam_data.get(str(appid), {})
            if app_data.get('success') and 'data' in app_data:
                steam_info = app_data['data']
                
                # Combine SteamSpy and Steam data
                enriched_game = {
                    'appid': appid,
                    'name': steam_info.get('name', game['name']),
                    'steamspy_score': game['score'],
                    'steamspy_userscore': game['userscore'],
                    'steamspy_owners': game['owners'],
                    'steamspy_average_playtime': game['average_playtime'],
                    'steamspy_median_playtime': game['median_playtime'],
                    'steamspy_ccu': game['ccu'],
                    'steamspy_ccu': game['ccu'],
                    'steam_price_initial': steam_info.get('price_overview', {}).get('initial', None),
                    'steam_price_final': steam_info.get('price_overview', {}).get('final', None),
                    'steam_price_discount_percent': steam_info.get('price_overview', {}).get('discount_percent', None),
                    'steam_price_currency': steam_info.get('price_overview', {}).get('currency', None),
                    'steam_release_date': steam_info.get('release_date', {}).get('date', None),
                    'steam_short_description': steam_info.get('short_description', None),
                    'steam_developers': json.dumps(steam_info.get('developers', [])),
                    'steam_publishers': json.dumps(steam_info.get('publishers', [])),
                    'steam_categories': json.dumps([cat.get('description') for cat in steam_info.get('categories', [])]),
                    'steam_genres': json.dumps([genre.get('description') for genre in steam_info.get('genres', [])])
                }
                
                enriched_games.append(enriched_game)
            else:
                logging.warning(f"No Steam data found for app {appid}")
                # Still add the SteamSpy data
                enriched_games.append({
                    'appid': appid,
                    'name': game['name'],
                    'steamspy_score': game['score'],
                    'steamspy_userscore': game['userscore'],
                    'steamspy_owners': game['owners'],
                    'steamspy_average_playtime': game['average_playtime'],
                    'steamspy_median_playtime': game['median_playtime'],
                    'steam_price_initial': None,
                    'steam_price_final': None,
                    'steam_price_discount_percent': None,
                    'steam_price_currency': None,
                    'steam_release_date': None,
                    'steam_short_description': None,
                    'steam_developers': None,
                    'steam_publishers': None,
                    'steam_categories': None,
                    'steam_genres': None
                })
            
            # Be nice to the APIs
            time.sleep(0.5)
            
        except Exception as e:
            logging.error(f"Error processing game {game['name']} (ID: {game['appid']}): {str(e)}")
            continue
    
    logging.info(f"Successfully enriched {len(enriched_games)} games")
    
    # Store enriched data in XCom
    context['task_instance'].xcom_push(key='enriched_games', value=enriched_games)
    
    return len(enriched_games)

def store_in_database(**context):
    """Store enriched games data in PostgreSQL (games updated, steamspy daily snapshots)"""
    enriched_games = context['task_instance'].xcom_pull(key='enriched_games')
    
    if not enriched_games:
        logging.error("No enriched games data found")
        raise ValueError("No enriched games data found")
    
    logging.info(f"Storing {len(enriched_games)} games in database...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get today's date
        today = datetime.now().date()
        
        # Prepare data for games table (Steam Store data)
        games_data = []
        steamspy_data = []
        
        for game in enriched_games:
            # Games table data (Steam Store info) - only if we have Steam data
            if any(game.get(f'steam_{key}') is not None for key in ['price_initial', 'price_final', 'short_description']):
                games_data.append({
                    'appid': game['appid'],
                    'name': game['name'],
                    'price_initial': game.get('steam_price_initial'),
                    'price_final': game.get('steam_price_final'),
                    'price_discount_percent': game.get('steam_price_discount_percent'),
                    'price_currency': game.get('steam_price_currency'),
                    'release_date': game.get('steam_release_date'),
                    'short_description': game.get('steam_short_description'),
                    'developers': game.get('steam_developers'),
                    'publishers': game.get('steam_publishers'),
                    'categories': game.get('steam_categories'),
                    'genres': game.get('steam_genres')
                })
            
            # SteamSpy daily snapshot data
            steamspy_data.append({
                'appid': game['appid'],
                'name': game['name'],
                'score': game.get('steamspy_score'),
                'userscore': game.get('steamspy_userscore'),
                'owners': game.get('steamspy_owners'),
                'average_playtime': game.get('steamspy_average_playtime'),
                'median_playtime': game.get('steamspy_median_playtime'),
                'ccu': game.get('steamspy_ccu'),
                'recorded_date': today
            })
        
        # Insert/Update games table only if we have Steam Store data
        if games_data:
            games_upsert_query = """
            INSERT INTO games (
                appid, name, price_initial, price_final, price_discount_percent,
                price_currency, release_date, short_description,
                developers, publishers, categories, genres, updated_at
            ) VALUES (
                %(appid)s, %(name)s, %(price_initial)s, %(price_final)s, %(price_discount_percent)s,
                %(price_currency)s, %(release_date)s, %(short_description)s,
                %(developers)s, %(publishers)s, %(categories)s, %(genres)s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (appid) DO UPDATE SET
                name = EXCLUDED.name,
                price_initial = EXCLUDED.price_initial,
                price_final = EXCLUDED.price_final,
                price_discount_percent = EXCLUDED.price_discount_percent,
                price_currency = EXCLUDED.price_currency,
                release_date = EXCLUDED.release_date,
                short_description = EXCLUDED.short_description,
                developers = EXCLUDED.developers,
                publishers = EXCLUDED.publishers,
                categories = EXCLUDED.categories,
                genres = EXCLUDED.genres,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            cur.executemany(games_upsert_query, games_data)
            logging.info(f"Successfully stored/updated {len(games_data)} games in games table")
        else:
            logging.info("No Steam Store data to update in games table")
        
        # Insert daily SteamSpy snapshots (always insert, never update)
        # Check if today's data already exists
        cur.execute("""
            SELECT COUNT(*) FROM steamspy_data 
            WHERE recorded_date = %s
        """, (today,))
        
        existing_count = cur.fetchone()[0]
        
        if existing_count > 0:
            logging.info(f"SteamSpy data for {today} already exists ({existing_count} records). Skipping insertion.")
        else:
            steamspy_insert_query = """
            INSERT INTO steamspy_data (
                appid, name, score, userscore, owners,
                average_playtime, median_playtime, ccu, recorded_date
            ) VALUES (
                %(appid)s, %(name)s, %(score)s, %(userscore)s, %(owners)s,
                %(average_playtime)s, %(median_playtime)s, %(ccu)s, %(recorded_date)s
            );
            """
            
            cur.executemany(steamspy_insert_query, steamspy_data)
            logging.info(f"Successfully stored {len(steamspy_data)} daily SteamSpy snapshots for {today}")
        
        conn.commit()
        logging.info(f"Successfully stored all data")
        
        return len(enriched_games)
        
    except Exception as e:
        logging.error(f"Error storing data in database: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

# Define tasks
fetch_task = PythonOperator(
    task_id='fetch_steamspy_top_games',
    python_callable=fetch_top_games,
    dag=dag,
)

enrich_task = PythonOperator(
    task_id='enrich_with_steam_data',
    python_callable=enrich_with_steam_data,
    dag=dag,
)

store_task = PythonOperator(
    task_id='store_in_database',
    python_callable=store_in_database,
    dag=dag,
)

# Set task dependencies
fetch_task >> enrich_task >> store_task