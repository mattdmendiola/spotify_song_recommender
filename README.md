# Spotify Song Recommender

A Python data pipeline that ingests Spotify playlists via the Spotify Web API and stores normalized data in PostgreSQL for analytics. Includes a lightweight Streamlit front end for interactive querying and exploration.

## What It Does

* Discovers playlists from search queries
* Fetches and deduplicates track metadata
* Writes playlists, tracks, and relationships to PostgreSQL
* Handles API rate limits and retries automatically
* Exposes ingested data via a Streamlit UI

## Tech Stack

* Python
* PostgreSQL
* Spotify Web API
* Streamlit
* spotipy
* psycopg2
* python-dotenv

## Database Schema
playlist_info_table
*   playlist_id
*   playlist_name
*   snapshot_id
*   total_tracks
  
song_info_table
*   song_id
*   song_name
*   artist_name
*   song_popularity

playlist_song_connections
*   playlist_id
*   song_id

playlist_query_status
*   query
*   status

This design allows tracks to exist independently of playlists and supports many-to-many relationships.

## Setup
```
git clone https://github.com/yourusername/spotify-playlist-ingestion.git
cd spotify-playlist-ingestion
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file
```
SPOTIPY_CLIENT_ID=...
SPOTIPY_CLIENT_SECRET=...
DATABASE_URL_DEV=...
DATABASE_URL_PROD=...
APP_ENV=dev
```

## Run 
### Crawler
```python crawler.py ```

### Streamlit Front-End
``` streamlit run app.py ```
