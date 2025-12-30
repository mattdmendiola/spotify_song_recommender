import time
import random
from spotipy.exceptions import SpotifyException

class SpotifyCaller:
    """
    Centralized wrapper for ALL Spotify API calls.
    - Enforces a minimum time gap between calls (rate limiting)
    - Handles 429 Retry-After
    - Retries transient 5xx with exponential backoff
    """
    def __init__(self, min_interval_s: float = 1.0, max_retries: int = 8):
        self.min_interval_s = min_interval_s
        self.max_retries = max_retries
        self._last_call_ts = 0.0

    def _pace(self):
        now = time.time()
        wait = self.min_interval_s - (now - self._last_call_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_call_ts = time.time()

    def call(self, fn, *args, **kwargs):
        attempt = 0
        while True:
            self._pace()
            try:
                return fn(*args, **kwargs)

            except SpotifyException as e:
                status = getattr(e, "http_status", None)

                # 429: rate limited — respect Retry-After if present
                if status == 429:
                    retry_after = None
                    headers = getattr(e, "headers", None) or {}
                    ra = headers.get("Retry-After") or headers.get("retry-after")
                    if ra is not None:
                        try:
                            retry_after = int(ra)
                        except ValueError:
                            retry_after = None

                    # Fallback if header missing
                    if retry_after is None:
                        retry_after = min(2 ** attempt, 60)

                    # Add small jitter so you don't hammer exactly on the boundary
                    time.sleep(retry_after + random.uniform(0, 0.25))
                    attempt += 1
                    if attempt > self.max_retries:
                        raise
                    continue

                # 5xx: transient server errors
                if status is not None and 500 <= status < 600:
                    backoff = min(2 ** attempt, 60) + random.uniform(0, 0.25)
                    time.sleep(backoff)
                    attempt += 1
                    if attempt > self.max_retries:
                        raise
                    continue

                # Other 4xx are usually permanent (bad request, forbidden, etc.)
                raise


def gather_playlists(caller, sp, query):
    valid_playlists = []
    playlist_set = set()
    for offset in range(0, 1000, 50):
        results = caller.call(sp.search, q=query, type="playlist", limit=50, offset=offset)
        for p in results["playlists"]["items"]:
            if p is not None and p["tracks"]["total"] in range(20, 301) and p["id"] not in playlist_set:
                valid_playlists.append((p["id"], p['name'], p['snapshot_id'], p["tracks"]["total"]))
                playlist_set.add(p['id'])
                
    return valid_playlists


def get_all_tracks_from_playlist(caller, sp, playlist_id):
    tracks = []
    # Initial request
    results = caller.call(sp.playlist_tracks, playlist_id=playlist_id)
    tracks.extend(results['items'])

    # Loop to handle pagination
    while results['next']:
        
        results = caller.call(sp.next, results)
        tracks.extend(results['items'])
        
    return tracks


def add_songs(curr_playlist_songs, playlist_id, ps_table, s_table, s_set):
    for item in curr_playlist_songs:
        track = item['track']
        if track and track['id'] and track['name'] and track['artists'][0]['name'] and track['popularity'] in range(0, 101): 
            ps_table.append((
                playlist_id,
                track['id']
            ))
            if track['id'] not in s_set:
                s_set.add(track['id'])
                s_table.append((
                    track['id'],
                    track['name'],
                    track['artists'][0]['name'],
                    track['popularity']
                ))
                
