"""
services/user_db_service.py
───────────────────────────
SUPABASE CHANGES vs old MySQL version:
  1. cur.fetchone()[0] → _scalar() helper (psycopg2 raw cursor returns tuples,
     but RealDictCursor returns dicts — _scalar handles both).
  2. is_deleted = 0/1 → is_deleted = FALSE/TRUE (PostgreSQL boolean).
  3. fetch_user_profile: row may be dict (RealDictCursor) or tuple.
  4. fetch_user_counts: _scalar() used for COUNT(*) results.
"""

from db import get_connection, execute_update


def _scalar(row, index: int = 0):
    """Extract a scalar from a tuple or dict row safely."""
    if row is None:
        return 0
    if isinstance(row, dict):
        return list(row.values())[index]
    return row[index]


# ══════════════════════════════════════════════════════════════════════════
# Fetch functions
# ══════════════════════════════════════════════════════════════════════════

def fetch_pending_users() -> list:
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, first_name, last_name, email, is_verified
            FROM users
            WHERE status = 'pending'
              AND role = 'user'
            ORDER BY id ASC
        """)
        return cur.fetchall()
    except Exception as exc:
        print(f"[fetch_pending_users] Error: {exc}")
        return []
    finally:
        if cur:
            cur.close()
        conn.close()


def fetch_accepted_users() -> list:
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, first_name, last_name, email, is_verified
            FROM users
            WHERE status = 'approved'
              AND role = 'user'
            ORDER BY id ASC
        """)
        return cur.fetchall()
    except Exception as exc:
        print(f"[fetch_accepted_users] Error: {exc}")
        return []
    finally:
        if cur:
            cur.close()
        conn.close()


def fetch_rejected_users() -> list:
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, first_name, last_name, email, is_verified
            FROM users
            WHERE status = 'rejected'
              AND role = 'user'
            ORDER BY id ASC
        """)
        return cur.fetchall()
    except Exception as exc:
        print(f"[fetch_rejected_users] Error: {exc}")
        return []
    finally:
        if cur:
            cur.close()
        conn.close()


# ══════════════════════════════════════════════════════════════════════════
# Actions
# ══════════════════════════════════════════════════════════════════════════

def accept_user(user_id: int) -> bool:
    affected = execute_update("""
        UPDATE users
        SET status = 'approved'
        WHERE id = %s AND role = 'user'
    """, (user_id,))
    return affected > 0


def reject_user(user_id: int) -> bool:
    affected = execute_update("""
        UPDATE users
        SET status = 'rejected'
        WHERE id = %s AND role = 'user'
    """, (user_id,))
    return affected > 0


def fetch_user_profile(user_id: int) -> dict:
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, first_name, last_name, email, role, status
            FROM users
            WHERE id = %s
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            return {}
        if isinstance(row, dict):
            return {
                "id":         row["id"],
                "first_name": row.get("first_name") or "",
                "last_name":  row.get("last_name") or "",
                "email":      row.get("email") or "",
                "role":       row.get("role") or "",
                "status":     row.get("status") or "",
            }
        # tuple fallback
        return {
            "id":         row[0],
            "first_name": row[1] or "",
            "last_name":  row[2] or "",
            "email":      row[3] or "",
            "role":       row[4] or "",
            "status":     row[5] or "",
        }
    except Exception as exc:
        print(f"[fetch_user_profile] Error: {exc}")
        return {}
    finally:
        if cur:
            cur.close()
        conn.close()


# ══════════════════════════════════════════════════════════════════════════
# Counts (for dashboard)
# ══════════════════════════════════════════════════════════════════════════

def fetch_user_counts() -> dict:
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
        total = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending' AND role = 'user'")
        pending = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'approved' AND role = 'user'")
        accepted = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'rejected' AND role = 'user'")
        rejected = _scalar(cur.fetchone())

        return {
            "total":    total,
            "pending":  pending,
            "accepted": accepted,
            "rejected": rejected,
        }
    except Exception as exc:
        print(f"[fetch_user_counts] Error: {exc}")
        return {"total": 0, "pending": 0, "accepted": 0, "rejected": 0}
    finally:
        if cur:
            cur.close()
        conn.close()


# ══════════════════════════════════════════════════════════════════════════
# Callback builders
# ══════════════════════════════════════════════════════════════════════════

def build_profile_callbacks() -> dict:
    return {
        "fetch_user_profile": fetch_user_profile,
    }


def build_user_callbacks() -> dict:
    return {
        "fetch_pending_users":  fetch_pending_users,
        "fetch_accepted_users": fetch_accepted_users,
        "fetch_rejected_users": fetch_rejected_users,
        "accept_user":          accept_user,
        "reject_user":          reject_user,
    }