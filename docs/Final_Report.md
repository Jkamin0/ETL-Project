# Steam Games ETL Pipeline: Independent Readings Final Report

**Author:** Jacob Smith  
**Course:** IS-6950 Independent Readings  
**Date:** August 4, 2025  
**GitHub Repository:** https://github.com/Jkamin0/ETL-Project

---

## Abstract / Executive Summary

I built a complete ETL pipeline for Steam game data that extracts gaming data from multiple APIs, transforms data into a dimensional model, and loads data into a PostgreSQL data warehouse.

The system includes two Apache Airflow DAGs running in Docker containers, a PostgreSQL database with raw and warehouse schemas, and Metabase visualization tools. The pipeline collects daily data on the top 100 most-played Steam games, enriches data with metadata, and stores data in a star schema for analysis.

Key accomplishments:

- API integration with rate limiting and error handling
- Dimensional data model with fact and dimension tables
- Automated incremental loading with change detection
- Containerized deployment using Docker Compose
- Business intelligence through Metabase

The system proved its reliability by completing over 30 scheduled executions.

---

## Introduction

Steam serves millions of users across thousands of games daily. I built a scalable ETL pipeline to capture and analyze Steam gaming data.

### Project Scope and Objectives

I designed and implemented a complete data engineering solution with these goals in mind:

1. **Extract** real-time gaming data from external APIs
2. **Transform** raw JSON data into a structured dimensional model
3. **Load** processed data into a data warehouse for analytics
4. **Orchestrate** the pipeline with scheduling and monitoring
5. **Visualize** the data through interactive dashboards

The project evolved through multiple phases. I started with basic API integration and built a sophisticated data warehouse with business intelligence tools.

---

## ETL Pipeline Architecture and Implementation

### System Architecture Overview

The pipeline follows modern data engineering practices, and the implementation includes distinct layers for raw data ingestion, transformation, and analytical storage.

**Core Components:**

- **Orchestration Layer:** Apache Airflow with two coordinated DAGs
- **Data Sources:** SteamSpy API and Steam Web API
- **Storage Layer:** PostgreSQL with separate schemas for raw and warehouse data
- **Containerization:** Docker Compose for reproducible deployments
- **Visualization:** Metabase for business intelligence and dashboards

### Data Ingestion Pipeline (steam_games_dag.py)

The primary ETL DAG implements a three-stage process:

**Stage 1: Data Extraction**

```python
def fetch_top_games(**context):
    """Fetch top 100 games from SteamSpy API"""
    url = "https://steamspy.com/api.php"
    params = {'request': 'top100in2weeks'}
```

I query the SteamSpy API to retrieve the top 100 most-played games in the last two weeks. This provides a focused dataset of relevant games and balances data volume with analytical value.

**Stage 2: Data Enrichment**
For each game from Stage 1, I query the official Steam Web API to gather metadata:

- Game descriptions and metadata
- Pricing information and discounts
- Developer and publisher information
- Genre and category classifications
- Release dates and other temporal data

**Stage 3: Data Persistence**
I store the enriched data in PostgreSQL tables optimized for raw data preservation and analytical queries. The system implements upsert logic to handle duplicate records and maintain data integrity.

### Data Warehouse Pipeline (warehouse_etl_dag.py)

The warehouse ETL DAG transforms raw ingestion data into a dimensional model for analytical workloads:

**Dimensional Model Design:**

- **dim_games:** Game master data with overwriting updates
- **dim_publishers:** Publisher dimension with bridge table for many-to-many relationships
- **dim_genres:** Genre classifications with bridge table support
- **dim_date:** Standard date dimension for temporal analysis
- **fact_game_metrics:** Daily game performance metrics

**Incremental Loading Strategy:**
I implemented incremental loading using bookmarking:

```python
def check_initial_load(**context):
    """Check if this is the first run (initial load) or incremental"""
    cur.execute("SELECT COUNT(*) FROM fact_game_metrics")
    fact_count = cur.fetchone()[0]

    if fact_count == 0:
        return 'create_warehouse_schema'
    else:
        return 'incremental_load_dimensions'
```

This approach processes only new or changed data after the initial load.

### Database Schema Evolution

I implemented a dual-schema approach:

**Raw Ingestion Schema:**

```sql
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    appid INTEGER UNIQUE NOT NULL,
    name VARCHAR(500),
    -- Raw JSON storage fields
    developers TEXT,
    publishers TEXT,
    categories TEXT,
    genres TEXT
);
```

**Dimensional Warehouse Schema:**

```sql
CREATE TABLE fact_game_metrics (
    game_key INTEGER REFERENCES dim_games(game_key),
    date_key INTEGER REFERENCES dim_date(date_key),
    ccu INTEGER,
    score INTEGER,
    owners_estimate INTEGER,
    -- Additional metrics
);
```

The dimensional model better supports analytical queries. I maintained referential integrity and query performance through proper indexing strategies as well.

---

## Technical Implementation and Development Evolution

### Project Development Timeline

I evolved the project through six major commits:

**Phase 1: Foundation (Initial Commit - June 2025)**

- Repository initialization with .gitignore
- Basic project structure establishment

**Phase 2: Design and Planning (README and PlantUML - March 2025)**

- Architectural design documentation
- PlantUML pipeline diagrams
- Initial project documentation

**Phase 3: Core ETL Implementation (API Integration - June 2025)**

- Steam API integration with rate limiting
- PostgreSQL database schema design
- Docker containerization setup
- Airflow DAG implementation (314 lines of core ETL logic)
- Basic raw data storage functionality

**Phase 4: Data Warehouse Development (July 2025)**

- Dimensional model design and implementation
- Warehouse ETL DAG creation (367 lines of transformation logic)
- Incremental loading strategy implementation
- Advanced SQL schema with 128 additional lines

**Phase 5: API Optimization (July 2025)**

- Migration from third-party to official Valve API endpoints
- Improved data accuracy and reliability
- Enhanced error handling and retry logic

**Phase 6: Business Intelligence Integration (August 2025)**

- Metabase integration for visualization
- Docker Compose enhancements for BI stack
- Dashboard and reporting tools

### Key Technical Decisions

**API Strategy Evolution:**
I initially used third-party APIs but evolved to use official Valve endpoints for better data accuracy and reliability. This change required refactoring the enrichment logic but resulted in more authoritative data.

**Containerization Approach:**
I chose Docker Compose for orchestration to ensure environment consistency and simplified deployment. The final configuration includes:

- PostgreSQL database service
- Airflow web server and scheduler
- Metabase business intelligence platform
- Shared network configuration for inter-service communication

**Data Modeling Philosophy:**
The dimensional model follows Kimball methodology with proper fact and dimension table design. Bridge tables handle many-to-many relationships (games-to-genres, games-to-publishers), enabling flexible analytical queries without data duplication.

---

## Data Processing and Quality Assurance

### Data Quality Implementation

I implemented multiple data quality checks:

**Schema Validation:**

```python
required_fields = ['appid', 'name', 'ccu']
for field in required_fields:
    if field not in game_data:
        logging.warning(f"Missing required field {field} for game {appid}")
        continue
```

**Duplicate Prevention:**
I use composite unique constraints and upsert logic to prevent data duplication while allowing for legitimate updates.

**Error Handling and Retry Logic:**
API calls implement exponential backoff and retry strategies to handle temporary service outages and rate limiting.

### Performance Optimization

**Database Indexing Strategy:**

```sql
CREATE INDEX idx_steamspy_appid_date ON steamspy_data(appid, recorded_date);
CREATE INDEX idx_steamspy_ccu ON steamspy_data(ccu DESC);
```

I used indexing to support both operational queries (by game and date) and analytical queries (top games by concurrent users).

**Query Optimization:**
The dimensional model enables efficient analytical queries:

```sql
-- Average CCU by day of week for top games
SELECT dg.name, dd.day_of_week, AVG(fgm.ccu) as avg_ccu
FROM fact_game_metrics fgm
JOIN dim_games dg ON fgm.game_key = dg.game_key
JOIN dim_date dd ON fgm.date_key = dd.date_key
WHERE dd.full_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dg.name, dd.day_of_week;
```

---

## Production Deployment and Monitoring

### Containerized Deployment

The final system deploys through Docker Compose with the following services:

```yaml
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: airflow
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow

  airflow-webserver:
    build: .
    depends_on:
      - postgres
    ports:
      - "8080:8080"

  metabase:
    image: metabase/metabase:latest
    depends_on:
      - postgres
    ports:
      - "3000:3000"
```

This configuration ensures consistent environments across development and production deployments.

### Operational Excellence

**Monitoring and Logging:**
The system generates comprehensive logs through Airflow's built-in logging system, with over 30+ successful pipeline executions documented in the logs directory. Each task execution creates detailed logs for troubleshooting and performance analysis.

**Scheduling and Reliability:**
Both DAGs run on daily schedules with proper dependency management. The warehouse ETL DAG waits for the ingestion DAG to complete before processing new data, ensuring data consistency.

**Backup and Recovery:**
PostgreSQL data persists through Docker volumes, ensuring data durability across container restarts and system maintenance. Full database backups can be created using either Postgres or cloning the Docker volume.

---

## Major Learnings

### Technical Skills Development

**Modern Data Engineering Practices:**
This project provided hands-on experience with industry-standard tools and patterns. Working with Apache Airflow taught me the importance of independent operations, proper task dependencies, and proper error handling in production data pipelines.

**Dimensional Modeling Expertise:**
Implementing a star schema from scratch reinforced theoretical knowledge of dimensional modeling. The challenge of handling many-to-many relationships through bridge tables and maintaining referential integrity in a dynamic data environment was particularly challenging.

**API Integration and Rate Limiting:**
Working with external APIs taught valuable lessons about resilience engineering. Implementing proper retry logic, handling rate limits, and gracefully degrading service quality during API outages are critical skills for production systems.

### Data Architecture Understanding

**Schema Evolution Management:**
The project demonstrated the importance of planning for schema changes. The evolution from a simple raw data storage to a sophisticated dimensional model required careful migration strategies and backward compatibility considerations.

**Performance vs. Flexibility Trade-offs:**
Balancing query performance through proper indexing while maintaining schema flexibility for future requirements required careful consideration of access patterns and growth projections.

### Learning Process Insights

**Iterative Development Value:**
The commit history shows how the project benefited from incremental development. Each phase built upon previous work while allowing for course corrections based on lessons learned.

**Documentation Importance:**
Maintaining comprehensive README documentation and architectural diagrams proved invaluable for project continuity and knowledge transfer.

---

## Experiences

### What Went Well

**Architectural Planning:**
The initial PlantUML diagrams and architectural planning provided a solid foundation for guiding development throughout the project. The upfront investment in design paid dividends during implementation.

**Docker Containerization:**
Containerizing the entire stack early in the project eliminated environment-related issues and made deployment reproducible. The ability to spin up the entire system with `docker-compose up` significantly accelerated development cycles.

**Incremental Development Approach:**
Breaking the project into logical phases (API integration → data warehouse → visualization) allowed for steady progress and reduced complexity at each stage.

### Challenges and Solutions

**API Rate Limiting and Reliability:**
The Steam APIs imposed strict rate limits and occasionally experienced outages. This challenge led to implementing robust retry logic and graceful degradation strategies:

```python
def enrich_with_steam_data(**context):
    for appid in appids:
        try:
            # API call with timeout and retry logic
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 429:  # Rate limited
                time.sleep(60)  # Back off and retry
                continue
        except requests.exceptions.RequestException as e:
            logging.error(f"API error for {appid}: {e}")
            continue
```

**Data Quality and Consistency:**
Raw API data contained inconsistencies, missing fields, and formatting variations. Implementing comprehensive data validation and cleaning logic was more complex than initially anticipated but crucial for data warehouse integrity.

**Performance Optimization:**
Initial query performance was poor due to missing indexes and suboptimal table design. Learning to identify bottlenecks through query analysis and implementing appropriate indexing strategies was a valuable skill development experience.

### Adaptations and Course Corrections

**API Strategy Pivot:**
The decision to switch from third-party APIs to official Valve endpoints mid-project required significant refactoring but resulted in better data quality and reliability. This taught the importance of evaluating data source quality early in project planning.

**Schema Design Evolution:**
The initial single-table approach evolved into a sophisticated dimensional model as the project progressed. This evolution demonstrated the value of flexible design patterns to accommodate changing requirements in a real work environment.

**Visualization Integration:**
The late addition of Metabase wasn't part of the original design (planed to use Grafana) but is essential for demonstrating the pipeline's value. This taught the importance of considering end-user needs throughout the development process.

---

## Conclusion

I successfully delivered a production-ready ETL pipeline demonstrating the usage of modern data engineering principles and practices. The system extracts, transforms, and loads Steam gaming data while maintaining high standards for reliability and maintainability.

The project's evolution from a simple API integration to a full data warehouse with business intelligence capabilities reflects a full implementation of the data engineering lifecycle. Key achievements include implementing robust API integration with error handling, designing and implementing a dimensional data model following industry best practices, building automated incremental loading with change detection, containerizing the entire solution for reproducible deployments, and integrating business intelligence capabilities for end-user value.

Beyond technical accomplishments, this project provided valuable learning experiences in architectural planning and iterative development The challenges encountered provided opportunities to develop problem-solving skills essential for professional data engineering work.

The final system represents a solid foundation for gaming industry analytics, supporting various analytical use cases from trend analysis to market research. The modular architecture and comprehensive documentation ensure the system allows future extensions and maintenance.

I successfully achieved the objectives while delivering a practical, working system for deployment in a production environment. The experience gained in modern data engineering tools, practices, troubleshooting, and challenges provides a great foundation for more work in the field professionally.

## Appendix

### Repository Information

- **GitHub URL:** https://github.com/Jkamin0/ETL-Project
- **Primary Branch:** main
- **Docker Setup:** `docker-compose up -d`
- **Airflow UI:** http://localhost:8080 (admin/admin)
- **Metabase UI:** http://localhost:3000
- **Database:** PostgreSQL (localhost:5432, airflow/airflow/airflow)

### Key Files and Line Counts

- `dags/steam_games_dag.py`: 314 lines (Main ETL pipeline)
- `dags/warehouse_etl_dag.py`: 367 lines (Data warehouse processing)
- `init.sql`: 168 lines (Database schema definitions)
- `docker-compose.yml`: Complete containerized deployment configuration
- `Design/pipeline.puml`: PlantUML architectural diagrams

### Execution Statistics

- Total pipeline executions: 30+ successful runs
- Daily schedule: Automated execution at configurable intervals
- Average execution time: 1-5 minutes per full pipeline run
- Data volume: Top 100 games with comprehensive metadata daily

### Technical Stack Summary

- **Orchestration:** Apache Airflow 2.x
- **Database:** PostgreSQL 13
- **Containerization:** Docker & Docker Compose
- **APIs:** Steam Web API, SteamSpy API
- **Languages:** Python 3.x, SQL
- **Visualization:** Metabase
- **Architecture:** Medallion/Lakehouse pattern with dimensional modeling
