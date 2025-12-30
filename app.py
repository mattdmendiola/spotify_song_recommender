import streamlit as st
from streamlit_searchbox import st_searchbox
import db_calls as dbc
import os
import re
import psycopg2
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from functools import partial

load_dotenv()

auth = SpotifyClientCredentials(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
)
sp = spotipy.Spotify(auth_manager=auth)

env = os.getenv("APP_ENV", "dev").lower()
DB_URL = os.getenv("DATABASE_URL_PROD") if env == "prod" else os.getenv("DATABASE_URL_DEV")


if 'song' not in st.session_state:
    st.session_state['song'] = None
    
if 'song_id' not in st.session_state:
    st.session_state['song_id'] = None

def search_song(searchterm: str, conn) -> list:
    # search wikipedia for the searchterm
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT song_id, song_name, artist
            FROM song_info_table
            WHERE song_name like '%{searchterm}%'
            ORDER BY song_popularity DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
              
    return [f'{(song)} by {(artist)} ({song_id})' for song_id, song, artist in rows]

def get_recommendation(conn, song_id):
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT b.song_name, b.artist, b.song_popularity
            FROM (
            SELECT song_id,  COUNT(song_id) as num
            FROM PLAYLIST_SONG_CONNECTION 
            WHERE playlist_id IN (
                SELECT playlist_id 
                FROM PLAYLIST_SONG_CONNECTION 
                WHERE song_id = '{song_id}'
                )
                AND song_id <> '{song_id}'
            GROUP BY song_id 
            ) AS a
            JOIN SONG_INFO_TABLE AS B
            ON a.song_id = b.song_id
            ORDER BY num DESC
        """)
        rows = cur.fetchall()
        return [f'{(song)} by {(artist)}' for song, artist, popularity in rows]
    
def main():
    with psycopg2.connect(DB_URL) as conn:
        run_app(conn)
        
        
def run_app(conn):
    st.title('Spotify Recommender Tool')

    search_fn = partial(search_song, conn=conn)
    
    
    st.session_state['song'] = st_searchbox(search_fn, key="song_search")
        
    if st.session_state['song']:
        st.session_state['song_id'] = re.findall(r"\(([^\)]+)\)", st.session_state['song'])[0]

    if st.session_state['song_id']:
        recs = get_recommendation(conn, st.session_state['song_id'])
        st.write(recs[:10])
    
        
if __name__ == "__main__":
    main()
