
from psycopg2.extras import execute_values

def bulk_insert(
    conn,
    table: str,
    columns: list[str],
    rows: list[tuple],
    conflict_cols: list[str] | None = None,
    page_size: int = 5000,
):
    """
    Bulk insert rows (list of tuples) into Postgres using execute_values.
    Assumes tuple order matches `columns`.
    """
    if not rows:
        return

    cols_sql = ", ".join(f'"{c}"' for c in columns)
    table_sql = f'"{table}"'
    insert_sql = f'INSERT INTO {table_sql} ({cols_sql}) VALUES %s'

    if conflict_cols:
        conflict_sql = ", ".join(f'"{c}"' for c in conflict_cols)
        insert_sql += f' ON CONFLICT ({conflict_sql}) DO NOTHING'

    with conn.cursor() as cur:
        execute_values(cur, insert_sql, rows, page_size=page_size)


def insert_edges(conn, edge_rows):
    bulk_insert(
        conn,
        table="playlist_song_connection",
        columns=["playlist_id", "song_id"],
        rows=edge_rows,
        conflict_cols=["playlist_id", "song_id"],
        page_size=5000,
    )

def insert_songs(conn, song_rows):
    bulk_insert(
        conn,
        table="song_info_table",
        columns=["song_id", "song_name", "artist", "song_popularity"],
        rows=song_rows,
        conflict_cols=["song_id"],
        page_size=2000,
    )


def insert_playlists(conn, song_rows):
    bulk_insert(
        conn,
        table="playlist_info_table",
        columns=["playlist_id", "playlist_name", "snapshot_id", "total_tracks"],
        rows=song_rows,
        conflict_cols=["playlist_id"],
        page_size=2000,
    )


def get_next_query(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT query
            FROM playlist_query_status
            WHERE status = 0
            ORDER BY index
            LIMIT 1
        """)
        rows = cur.fetchall()
    return list(sum(rows, ()))



def mark_query_complete(conn, query):
    with conn.cursor() as cur:
         cur.execute(
            """
            UPDATE playlist_query_status
            SET status = 1
            WHERE query = %s
            """,
            (query,)
        )
    
def mark_query_failed(conn, query, error_msg):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE playlist_query_status
            SET status = -1,
                last_error = %s
            WHERE query = %s
            """,
            (error_msg, query)
        )


def filter_new_or_changed_playlists(conn, playlists):
    """
    playlists: list[str] -> [playlist_id, ...]
    Returns: list[str] of playlists to crawl (new or changed)
    """
    if not playlists:
        return []

    sql = """
        WITH candidates(playlist_id, playlist_name, snapshot_id, total_tracks) AS (
            VALUES %s
        )
        SELECT c.playlist_id, c.playlist_name, c.snapshot_id, c.total_tracks
        FROM candidates c
        LEFT JOIN "playlist_info_table" p
          ON p."playlist_id" = c.playlist_id
        WHERE p."playlist_id" IS NULL
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, playlists, page_size=1000)
        return cur.fetchall()




    