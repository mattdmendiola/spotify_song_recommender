import db_calls as dbc
import spotify_calls as spc
import os
import psycopg2
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

auth = SpotifyClientCredentials(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
)
sp = spotipy.Spotify(auth_manager=auth)

env = os.getenv("APP_ENV", "dev").lower()
DB_URL = os.getenv("DATABASE_URL_PROD") if env == "prod" else os.getenv("DATABASE_URL_DEV")

def main():
    with psycopg2.connect(DB_URL) as conn:
        run_crawler(conn)

def run_crawler(conn):
    caller = spc.SpotifyCaller(min_interval_s=1.0, max_retries=8)
    
    while (query := dbc.get_next_query(conn)[0]):
        print(query)
        try:
            playlist_table = []
            song_table = []
            connection_table = []
            song_set = set()

            playlists = dbc.filter_new_or_changed_playlists(conn, spc.gather_playlists(caller, sp, query))

            for playlist_id, playlist_name, snap_id, total_tracks in playlists:    
                songs =  spc.get_all_tracks_from_playlist(caller, sp, playlist_id)
                
                spc.add_songs(songs, playlist_id, connection_table, song_table, song_set)
                
                playlist_table.append((playlist_id, playlist_name, snap_id, total_tracks))
                
                if len(connection_table) > 20000:
                    dbc.insert_edges(conn, connection_table)
                    connection_table = []
                    
                    dbc.insert_songs(conn, song_table)
                    song_table = []
                    
                    dbc.insert_playlists(conn, playlist_table)
                    playlist_table = []       
                    
                    conn.commit()   
                    
            if len(connection_table) > 0:
                dbc.insert_edges(conn, connection_table)                
                dbc.insert_songs(conn, song_table)                
                dbc.insert_playlists(conn, playlist_table)
                
            dbc.mark_query_complete(conn, query)
            conn.commit()
            print('Success')
        
        except Exception as e:
            conn.rollback()
            dbc.mark_query_failed(conn, query, str(e))
            conn.commit()
            print('Error')

                
        
if __name__ == "__main__":
    main()


