# services/article_service.py
# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE CHANGES vs old MySQL version:
#   1. ensure_activity_logs_schema / ensure_categories_schema →
#      removed MySQL-specific syntax (AUTO_INCREMENT, INDEX inside CREATE TABLE)
#      Tables already exist in Supabase so these are now no-ops / safe checks.
#   2. DATE_FORMAT() → TO_CHAR()
#   3. is_deleted = 0 → is_deleted = FALSE
#   4. fetch_all / fetch_one return dicts — row["key"] access used throughout.
#   5. fetch_articles_by_category: rows are dicts so keyed access used.
#   6. fetch_categories: rows may be tuples (raw cursor) or dicts — handled.
#   7. Removed MySQL INDEX syntax from CREATE TABLE statements.
# ─────────────────────────────────────────────────────────────────────────────

from db import fetch_one, fetch_all, execute_insert, execute_update, get_connection


# ═════════════════════════════════════════════════════════════════════════════
# SCHEMA HELPERS  (safe no-ops if tables already exist in Supabase)
# ═════════════════════════════════════════════════════════════════════════════

def ensure_activity_logs_schema():
    """
    Create activity_logs table if it doesn't exist.
    Uses PostgreSQL syntax (SERIAL, no inline INDEX).
    Safe to call every startup.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id          BIGSERIAL PRIMARY KEY,
                user_id     BIGINT       NOT NULL,
                article_id  BIGINT       DEFAULT NULL,
                action      VARCHAR(120) NOT NULL,
                description TEXT         DEFAULT NULL,
                created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()
    except Exception as exc:
        print(f"[ensure_activity_logs_schema] Error: {exc}")
    finally:
        cur.close()
        conn.close()


def ensure_categories_schema():
    """
    Create categories table if it doesn't exist.
    Uses PostgreSQL syntax (SERIAL, no inline INDEX).
    Safe to call every startup.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id         BIGSERIAL    PRIMARY KEY,
                name       VARCHAR(100) NOT NULL UNIQUE,
                icon       VARCHAR(10)  NOT NULL DEFAULT '📁',
                color      VARCHAR(20)  NOT NULL DEFAULT '#fb923c',
                archived   BOOLEAN      NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()
    except Exception as exc:
        print(f"[ensure_categories_schema] Error: {exc}")
    finally:
        cur.close()
        conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# ARTICLE DETAILS
# ═════════════════════════════════════════════════════════════════════════════

def get_article_by_id(article_id):
    """
    Fetch a single article by ID.
    Returns dict or None (fetch_one uses RealDictCursor).
    """
    query = """
    SELECT
        a.id,
        a.headline,
        a.content,
        a.category,
        a.created_at,
        u.first_name,
        u.last_name,
        a.media
    FROM articles a
    JOIN users u ON a.author_id = u.id
    WHERE a.id = %s AND a.is_deleted = FALSE
    LIMIT 1
    """
    return fetch_one(query, (article_id,))


def fetch_homepage_articles() -> list:
    """
    Fetch all approved, non-deleted articles for the user homepage.
    Returns list of dicts.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                a.id,
                a.headline,
                a.content,
                a.category,
                a.created_at,
                u.first_name,
                u.last_name,
                a.media
            FROM articles a
            JOIN users u ON u.id = a.author_id
            WHERE a.status     = 'approved'
              AND a.is_deleted = FALSE
            ORDER BY a.created_at DESC
        """)
        return cur.fetchall()
    except Exception as exc:
        print(f"[fetch_homepage_articles] Error: {exc}")
        return []
    finally:
        cur.close()
        conn.close()


def fetch_articles_by_category(category_name: str) -> list:
    """
    Return approved articles for a given category name.
    Returns list of dicts: {id, headline, author, date}
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                a.id,
                a.headline,
                CONCAT(u.first_name, ' ', u.last_name) AS author,
                TO_CHAR(a.created_at, 'Mon DD, YYYY')  AS date
            FROM articles a
            JOIN users u ON u.id = a.author_id
            WHERE a.category   = %s
              AND a.status     = 'approved'
              AND a.is_deleted = FALSE
            ORDER BY a.created_at DESC
            LIMIT 20
        """, (category_name,))
        rows = cur.fetchall()
        result = []
        for r in rows:
            if isinstance(r, dict):
                result.append({
                    "id":       r["id"],
                    "headline": r["headline"],
                    "author":   r["author"],
                    "date":     r["date"],
                })
            else:
                result.append({
                    "id": r[0], "headline": r[1],
                    "author": r[2], "date": r[3],
                })
        return result
    except Exception as exc:
        print(f"[fetch_articles_by_category] Error: {exc}")
        return []
    finally:
        cur.close()
        conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# COMMENTS
# ═════════════════════════════════════════════════════════════════════════════

def get_comments_by_article(article_id):
    """
    Fetch all comments for an article, oldest first.
    Returns list of dicts: {id, comment, created_at, first_name, last_name}
    """
    query = """
    SELECT
        c.id,
        c.comment,
        c.created_at,
        u.first_name,
        u.last_name
    FROM comments c
    JOIN users u ON c.user_id = u.id
    WHERE c.article_id = %s
    ORDER BY c.created_at ASC
    """
    return fetch_all(query, (article_id,))


def add_comment(article_id, user_id, comment_text):
    """
    Insert a new comment on an article.
    Returns the new comment's id (int) or None on failure.
    """
    query = """
    INSERT INTO comments (article_id, user_id, comment)
    VALUES (%s, %s, %s)
    """
    return execute_insert(query, (article_id, user_id, comment_text))


def delete_comment(comment_id: int) -> bool:
    """Hard-delete a comment by id. Returns True on success."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        print(f"[delete_comment] Error: {exc}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# ACTIVITY LOGS
# ═════════════════════════════════════════════════════════════════════════════

def insert_activity_log(
    user_id,
    action,
    description="",
    article_id=None,
):
    """
    Insert a single activity log entry.
    Returns the new log row's id (int) or None on failure.
    """
    query = """
    INSERT INTO activity_logs
        (user_id, article_id, action, description)
    VALUES (%s, %s, %s, %s)
    """
    return execute_insert(query, (user_id, article_id, action, description))


def fetch_admin_activity_logs() -> list:
    query = """
    SELECT
        al.created_at                          AS created_at,
        CONCAT(u.first_name, ' ', u.last_name) AS user_name,
        u.role                                 AS role,
        al.action                              AS action,
        al.description                         AS description,
        COALESCE(a.category, '')               AS category,
        COALESCE(a.headline, '')               AS headline
    FROM activity_logs al
    JOIN users u ON al.user_id = u.id
    LEFT JOIN articles a ON al.article_id = a.id
    WHERE LOWER(u.role) IN ('admin', 'superadmin')
    ORDER BY al.created_at DESC
    """
    rows = fetch_all(query)
    return [
        {
            "date":        r["created_at"].strftime("%Y-%m-%d %H:%M")
                           if r.get("created_at") else "",
            "user_name":   r.get("user_name") or "",
            "role":        r.get("role") or "",
            "action":      r.get("action") or "",
            "description": r.get("description") or "",
            "category":    r.get("category") or "",
            "headline":    r.get("headline") or "",
        }
        for r in rows
    ]


def fetch_reader_activity_logs() -> list:
    query = """
    SELECT
        al.created_at                          AS created_at,
        CONCAT(u.first_name, ' ', u.last_name) AS user_name,
        u.role                                 AS role,
        al.action                              AS action,
        al.description                         AS description,
        COALESCE(a.category, '')               AS category,
        COALESCE(a.headline, '')               AS headline
    FROM activity_logs al
    JOIN users u ON al.user_id = u.id
    LEFT JOIN articles a ON al.article_id = a.id
    WHERE LOWER(u.role) = 'user'
    ORDER BY al.created_at DESC
    """
    rows = fetch_all(query)
    return [
        {
            "date":     r["created_at"].strftime("%Y-%m-%d %H:%M")
                        if r.get("created_at") else "",
            "user_name": r.get("user_name") or "",
            "role":      r.get("role") or "",
            "action":    r.get("action") or "",
            "content":   r.get("description") or "",
            "category":  r.get("category") or "",
            "headline":  r.get("headline") or "",
        }
        for r in rows
    ]


def build_activity_log_callbacks() -> dict:
    return {
        "fetch_admin_logs":  fetch_admin_activity_logs,
        "fetch_reader_logs": fetch_reader_activity_logs,
    }


# ═════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ═════════════════════════════════════════════════════════════════════════════

def fetch_categories() -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                c.id,
                c.name,
                c.icon,
                COALESCE(c.icon_type, 'emoji')             AS icon_type,
                c.icon_svg_url,
                c.color,
                (c.archived OR COALESCE(c.is_archived, 0) = 1) AS archived,
                COUNT(a.id)                                AS article_count
            FROM categories c
            LEFT JOIN articles a
                ON  a.category   = c.name
                AND a.is_deleted = FALSE
                AND a.status     IN ('approved', 'published')
            GROUP BY c.id, c.name, c.icon, c.icon_type,
                     c.icon_svg_url, c.color, c.archived, c.is_archived
            ORDER BY (c.archived OR COALESCE(c.is_archived,0)=1) ASC, c.name ASC
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            if isinstance(r, dict):
                result.append({
                    "id":            r["id"],
                    "name":          r["name"],
                    "icon":          r["icon"],
                    "icon_type":     r["icon_type"],
                    "icon_svg_url":  r["icon_svg_url"],
                    "color":         r["color"],
                    "archived":      bool(r["archived"]),
                    "article_count": int(r["article_count"]),
                })
            else:
                result.append({
                    "id":            r[0],
                    "name":          r[1],
                    "icon":          r[2],
                    "icon_type":     r[3],
                    "icon_svg_url":  r[4],
                    "color":         r[5],
                    "archived":      bool(r[6]),
                    "article_count": int(r[7]),
                })
        return result
    except Exception as exc:
        print(f"[fetch_categories] Error: {exc}")
        return []
    finally:
        cur.close()
        conn.close()


def fetch_active_categories() -> list:
    """Return only active/non-archived categories."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, icon, color
            FROM categories
            WHERE archived = FALSE
            ORDER BY name ASC
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            if isinstance(r, dict):
                result.append({
                    "id":    r["id"],
                    "name":  r["name"],
                    "icon":  r["icon"],
                    "color": r["color"],
                })
            else:
                result.append({
                    "id": r[0], "name": r[1],
                    "icon": r[2], "color": r[3],
                })
        return result
    except Exception as exc:
        print(f"[fetch_active_categories] Error: {exc}")
        return []
    finally:
        cur.close()
        conn.close()

_TKINTER_DEFAULTS = [
    ("NEWS",     "📰", "#fb923c"),
    ("UPDATES",  "📢", "#3b82f6"),
    ("OPINION",  "💬", "#a855f7"),
    ("FEATURE",  "⭐", "#22c55e"),
    ("KOMIKS",   "📚", "#f97373"),
    ("LITERARY", "✏️", "#92400e"),
    ("ARTS",     "🎨", "#ec4899"),
    ("PHOTOS",   "📷", "#14b8a6"),
    ("VIDEOS",   "🎬", "#6366f1"),
]

def seed_default_categories() -> None:
    """Insert default categories if missing. Safe to call every startup."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        for name, icon, color in _TKINTER_DEFAULTS:
            cur.execute(
                "SELECT 1 FROM categories WHERE UPPER(name) = %s", (name,)
            )
            if cur.fetchone():
                continue
            cur.execute("""
                INSERT INTO categories
                    (name, icon, icon_type, color, archived, is_archived)
                VALUES (%s, %s, 'emoji', %s, FALSE, 0)
            """, (name, icon, color))
        conn.commit()
    except Exception as exc:
        print(f"[seed_default_categories] Error: {exc}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def add_category(name: str, icon: str, color: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO categories (name, icon, icon_type, color, archived, is_archived)
            VALUES (%s, %s, 'emoji', %s, FALSE, 0)
        """, (name.strip().upper(), icon.strip(), color.strip()))
        conn.commit()
        return True
    except Exception as exc:
        print(f"[add_category] Error: {exc}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()



def update_category(cat_id: int, name: str, icon: str, color: str) -> bool:
    affected = execute_update("""
        UPDATE categories
        SET name  = %s,
            icon  = %s,
            color = %s
        WHERE id = %s
    """, (name.strip().upper(), icon.strip(), color.strip(), cat_id))
    return affected > 0


def archive_category(cat_id: int) -> bool:
    affected = execute_update(
        "UPDATE categories SET archived = TRUE, is_archived = 1 WHERE id = %s",
        (cat_id,)
    )
    return affected > 0


def unarchive_category(cat_id: int) -> bool:
    affected = execute_update(
        "UPDATE categories SET archived = FALSE, is_archived = 0 WHERE id = %s",
        (cat_id,)
    )
    return affected > 0


def delete_category(cat_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM categories WHERE id = %s", (cat_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        print(f"[delete_category] Error: {exc}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def build_category_callbacks() -> dict:
    return {
        "fetch_categories":           fetch_categories,
        "fetch_articles_by_category": fetch_articles_by_category,
        "add_category":               add_category,
        "update_category":            update_category,
        "archive_category":           archive_category,
        "unarchive_category":         unarchive_category,
        "delete_category":            delete_category,
        "fetch_homepage_articles":    fetch_homepage_articles,
        "fetch_active_categories":    fetch_active_categories,
    }


def build_homepage_callbacks() -> dict:
    return {
        "fetch_homepage_articles": fetch_homepage_articles,
    }


def build_article_detail_callbacks(user_id: int) -> dict:
    return {
        "get_article":    get_article_by_id,
        "get_comments":   get_comments_by_article,
        "add_comment":    lambda aid, text: add_comment(aid, user_id, text),
        "delete_comment": delete_comment,
        "log_view":       lambda aid: insert_activity_log(
                              user_id, "Viewed", article_id=aid),
        "log_comment":    lambda aid, excerpt="": insert_activity_log(
                              user_id, "Commented", description=excerpt,
                              article_id=aid),
    }