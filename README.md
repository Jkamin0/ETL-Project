# Independent Study Project Ideas

My project proposal is to construct a ETL pipeline that pulls from an API data source. Below I have two sources as potential data candidates but both would use the proposed ETL pipeline.

![PipelineImage](/Design/pipeline.png)

## Game Popularity Trend Pipeline

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

## Satellite Trajectories Pipeline

This ETL pipeline collects, processes, and stores satellite tracking data from **CelesTrak**. The primary data sources are:

### CelesTrak Satellite Data

- **URL:** [https://www.celestrak.com/](https://www.celestrak.com/)
- **Purpose:** Provides satellite tracking data, including real-time and historical information about satellites in orbit, TLE (two-line element) data, and orbital parameters.
- **Used for:**
  - Satellite location and trajectories
  - Tracking active satellites and space debris
  - TLE data for satellite predictions
  - Space station data (e.g., ISS position)
