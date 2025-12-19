import psycopg2
from psycopg2.extras import RealDictCursor

from config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD

def get_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        port="5432",
        user=DB_USER,
        password=DB_PASSWORD
    )

    return conn

def execute_write(query, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            try:
                result = cur.fetchone()
                return result[0] if result else None
            except (psycopg2.ProgrammingError, TypeError):
                return None
    finally:
        conn.close()

def execute_read(query, params=None):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()
