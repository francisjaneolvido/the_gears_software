"""
db.py  —  Supabase / PostgreSQL drop-in replacement
=====================================================
Exact same public API as the old MySQL version:
    get_connection()
    fetch_one(query, params)
    fetch_all(query, params)
    execute_query(query, params)
    execute_insert(query, params)
    execute_update(query, params)
    test_connection()

Changes vs old MySQL db.py
---------------------------
1. Uses psycopg2 instead of mysql.connector
2. Placeholder syntax:  ? → %s  (auto-converted inside each function)
3. fetch_one / fetch_all return dicts  (via RealDictCursor, same as dictionary=True)
4. execute_insert appends RETURNING id to get lastrowid
5. get_connection() returns a plain psycopg2 connection
   (services that call get_connection() directly will work as-is)

Setup
-----
pip install psycopg2-binary python-dotenv

Add to your .env file (or fill SUPABASE_DB_URL directly):
    SUPABASE_DB_URL=postgresql://postgres.<project>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

The URL is found in:
    Supabase Dashboard → Project Settings → Database →
    Connection string → Session mode (port 5432)
"""

import os
import re

import psycopg2
import psycopg2.extras          # RealDictCursor  (gives dict rows like dictionary=True)
from dotenv import load_dotenv

load_dotenv()

# ── Connection string ──────────────────────────────────────────────────────
# Priority: environment variable → hard-coded fallback (fill in for local dev)
SUPABASE_DB_URL: str = os.getenv(
    "SUPABASE_DB_URL",
    ""   # ← paste your Supabase connection string here if you don't use .env
)


# ── Internal helper: convert MySQL ? placeholders → psycopg2 %s ───────────
def _pg(query: str) -> str:
    """Replace bare ? with %s so MySQL-style queries work in PostgreSQL."""
    # Only replace ? that are not already inside %s / %(name)s patterns
    return query.replace("?", "%s")


# ── Internal helper: MySQL date format → PostgreSQL ───────────────────────
def _translate(query: str) -> str:
    """
    Light SQL dialect translation layer.

    Converts the small subset of MySQL-isms used in admin_db_service.py
    and article_service.py to valid PostgreSQL syntax.

    Conversions
    -----------
    DATE_FORMAT(col, fmt)   → TO_CHAR(col, fmt)   (format tokens also mapped)
    NOW()                   → NOW()                (same — no change needed)
    %% (escaped percent)    → %%                   (kept — psycopg2 needs it)
    CONCAT(a, b, ...)       → CONCAT(a, b, ...)    (same — no change needed)
    BOOLEAN literals        → same (PostgreSQL understands TRUE/FALSE)
    information_schema      → same (PostgreSQL has it too)
    DATABASE()              → current_database()
    """
    # DATE_FORMAT → TO_CHAR  (MySQL date format codes → PostgreSQL equivalents)
    def _replace_date_format(m):
        col = m.group(1).strip()
        fmt = m.group(2).strip().strip("'\"")
        # Map MySQL format tokens → PostgreSQL
        fmt = fmt.replace("%Y", "YYYY")
        fmt = fmt.replace("%m", "MM")
        fmt = fmt.replace("%d", "DD")
        fmt = fmt.replace("%H", "HH24")
        fmt = fmt.replace("%i", "MI")
        fmt = fmt.replace("%s", "SS")
        fmt = fmt.replace("%b", "Mon")
        fmt = fmt.replace("%p", "AM")
        fmt = fmt.replace("%h", "HH12")
        # Keep double-percent escapes that psycopg2 needs
        fmt = fmt.replace("%%Y", "YYYY")
        fmt = fmt.replace("%%m", "MM")
        fmt = fmt.replace("%%d", "DD")
        fmt = fmt.replace("%%H", "HH24")
        fmt = fmt.replace("%%i", "MI")
        fmt = fmt.replace("%%s", "SS")
        fmt = fmt.replace("%%b", "Mon")
        fmt = fmt.replace("%%p", "AM")
        fmt = fmt.replace("%%h", "HH12")
        return f"TO_CHAR({col}, '{fmt}')"

    query = re.sub(
        r"DATE_FORMAT\s*\(\s*([^,]+),\s*'([^']+)'\s*\)",
        _replace_date_format,
        query,
        flags=re.IGNORECASE,
    )

    # DATABASE() → current_database()
    query = re.sub(r"\bDATABASE\s*\(\s*\)", "current_database()", query, flags=re.IGNORECASE)

    # ? → %s
    query = _pg(query)

    return query


# ── Connection factory ─────────────────────────────────────────────────────
def get_connection():
    """
    Return a live psycopg2 connection to Supabase.
    Returns None on failure (same contract as old MySQL version).

    Services that call get_connection() directly (e.g. admin_db_service.py)
    must use %s placeholders and call _translate() themselves — OR just use
    fetch_one / fetch_all / execute_* helpers which handle translation.
    """
    if not SUPABASE_DB_URL:
        print(
            "[db] ERROR: SUPABASE_DB_URL is not set.\n"
            "  Add it to your .env file or set it at the top of db.py."
        )
        return None

    try:
        conn = psycopg2.connect(
            SUPABASE_DB_URL,
            connect_timeout=15,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        conn.autocommit = False
        return conn
    except psycopg2.OperationalError as e:
        print(f"[db] Connection error: {e}")
        return None


# ── Public helpers ─────────────────────────────────────────────────────────

def fetch_one(query: str, params=None):
    """
    Execute a SELECT and return the first row as a dict, or None.
    Equivalent to cursor(dictionary=True).fetchone() in the MySQL version.
    """
    conn = get_connection()
    if not conn:
        return None

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(_translate(query), params or ())
            row = cur.fetchone()
            # RealDictRow → plain dict so callers can use row["key"]
            return dict(row) if row else None
    except Exception as e:
        print(f"[db] fetch_one error: {e}\nQuery: {query}")
        return None
    finally:
        conn.close()


def fetch_all(query: str, params=None):
    """
    Execute a SELECT and return all rows as a list of dicts.
    Equivalent to cursor(dictionary=True).fetchall() in the MySQL version.
    """
    conn = get_connection()
    if not conn:
        return []

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(_translate(query), params or ())
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"[db] fetch_all error: {e}\nQuery: {query}")
        return []
    finally:
        conn.close()


def execute_query(query: str, params=None) -> bool:
    """
    Run a non-SELECT statement (DELETE, UPDATE, etc.).
    Returns True on success, False on error.
    """
    conn = get_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            cur.execute(_translate(query), params or ())
        conn.commit()
        return True
    except Exception as e:
        print(f"[db] execute_query error: {e}\nQuery: {query}")
        conn.rollback()
        return False
    finally:
        conn.close()


def execute_insert(query: str, params=None):
    """
    Run an INSERT and return the new row's id (int), or None on failure.

    PostgreSQL does not expose cursor.lastrowid like MySQL does.
    We append  RETURNING id  to the query automatically when it is missing.
    """
    conn = get_connection()
    if not conn:
        return None

    translated = _translate(query)

    # Append RETURNING id if not already present
    if "returning" not in translated.lower():
        translated = translated.rstrip().rstrip(";") + " RETURNING id"

    try:
        with conn.cursor() as cur:
            cur.execute(translated, params or ())
            row = cur.fetchone()
            new_id = row[0] if row else None
        conn.commit()
        return new_id
    except Exception as e:
        print(f"[db] execute_insert error: {e}\nQuery: {query}")
        conn.rollback()
        return None
    finally:
        conn.close()


def execute_update(query: str, params=None) -> int:
    """
    Run an UPDATE or DELETE.
    Returns the number of affected rows (0 on error).
    """
    conn = get_connection()
    if not conn:
        return 0

    try:
        with conn.cursor() as cur:
            cur.execute(_translate(query), params or ())
            affected = cur.rowcount
        conn.commit()
        return affected
    except Exception as e:
        print(f"[db] execute_update error: {e}\nQuery: {query}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def test_connection() -> bool:
    """Return True if a connection to Supabase can be established."""
    conn = get_connection()
    if conn:
        conn.close()
        return True
    return False