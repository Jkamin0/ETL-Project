# Game Popularity Trend Pipeline

![PipelineImage](https://raw.githubusercontent.com/Jkamin0/ETL-Project/refs/heads/main/Design/pipeline.png)

## Project Overview

This ETL pipeline collects and processes data related to video game popularity on Steam. The primary data sources are:

### Steam Web API

- **URL:** [https://partner.steamgames.com/doc/webapi](https://partner.steamgames.com/doc/webapi)
- **Purpose:** Provides real-time and historical data on concurrent player counts, game details, and app information.
- **Used for:**
  - Game names and app IDs
  - Current and peak player counts
  - Game metadata (e.g. genre, release date)

### SteamSpy

- **SteamSpy:** [https://steamspy.com/api.php](https://steamspy.com/api.php)
- **Purpose:** Aggregates game popularity stats including average player counts, peak counts, and more.
- **Used for:**
  - Historical trends
  - Regional popularity
  - Additional metadata

## Goals

1. Data Integration and Analysis

- Consolidate game popularity data from Steam Web API and SteamSpy into a centralized PostgreSQL database
- Comprehensive analysis of player count trends across different time periods and game categories

2. Pipeline Reliability

- Robust data collection with error handling for API limitations and outages
- A modular architecture that can easily incorporate additional data sources or metrics in the future

3. Accessible Visualization

- Intuitive Grafana dashboards that present key metrics and trends
- Support data-driven decision making with customizable reports

## Milestones:

I plan to use the default milestone dates provided in canvas. As the project progresses and matures, I may make slight changes along the way. I hope to have the following done for each milestone:

### Milestone 1: Data Collection & Storage Foundation

- Implement API connectors for Steam Web API and SteamSpy
- Create raw data storage layer with proper schema design
- Build initial ETL pipeline with scheduled Airflow DAGs for daily data collection

Deliverable: Functional pipeline consistently collecting and storing raw game data

### Milestone 2: Data Transformation & Analysis

- Develop transformation scripts using pandas to clean and structure the data
- Create dimension and fact tables in PostgreSQL for analytical queries
- Implement historical trend calculations and popularity metrics
- Build aggregation logic for different time periods (daily, weekly, monthly)

Deliverable: Complete transformation layer with cleaned, structured data ready for analysis

### Milestone 3: Visualization & Insights Platform

- Set up Grafana dashboard with real-time game popularity metrics
- Create custom visualizations for trend analysis and comparisons
- Implement automated reports for rising/declining games
- Build genre, category, and regional analysis features

Deliverable: Fully functional end-to-end system with interactive dashboards for game popularity insights
