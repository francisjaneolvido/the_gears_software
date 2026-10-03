"""
services/admin_db_service.py
────────────────────────────
All database operations for the Admin pages.

SUPABASE CHANGES vs old MySQL version:
  1. 'rejected'      → 'needs_revision'  (status value aligned with web)
  2. media column    → JSONB in Supabase, so json.loads() not needed when
                       psycopg2 already returns a dict/list; _parse_media()
                       handles both cases safely.
  3. ensure_schema() → removed MySQL-specific ALTER TABLE / DATABASE() calls;
                       Supabase schema is already correct.
  4. cur.lastrowid   → not available in psycopg2; use execute_insert() from
                       db.py which appends RETURNING id automatically.
  5. cur.fetchone()  → psycopg2 with RealDictCursor returns dicts, but when
                       get_connection() is used directly the raw cursor returns
                       tuples — _scalar() helper extracts index [0] safely.
  6. DATE_FORMAT()   → handled by db._translate() automatically.
  7. DATABASE()      → handled by db._translate() automatically.
  8. GROUP BY name   → PostgreSQL requires all non-aggregate SELECTs in GROUP BY;
                       fixed in fetch_top_contributors.
  9. WEEKDAY() /
     DATE_SUB()      → replaced with PostgreSQL equivalents in
                       fetch_activity_trends.
"""

import json
from datetime import datetime

from services.article_service import (
    fetch_active_categories,
    insert_activity_log,
)
from db import fetch_one, execute_insert, execute_update, get_connection
import os

PROFILE_IMAGE_DIR = os.path.join("static", "uploads", "profiles")

FLASK_BASE_URL        = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
SUPABASE_STORAGE_BASE = "https://vkllnewjkagdmqdclywg.supabase.co/storage/v1/object/public"

def resolve_media_items(media_val) -> list:
    """
    Convert any media format into a list of dicts:
      {"url": "...", "thumbnail": "...", "type": "image"|"video"}

    Handles:
      - Tkinter JSONB dict: {"file_paths": ["photo.jpg"], ...}
      - Mobile list:        [{"url": "https://...", "type": "image"}]
      - Legacy flat list:   ["photo.jpg"]
      - JSON string of any of the above
    """
    VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    def _clean(f):
        f = str(f).strip()
        if len(f) > 2 and f[1] == ":":          # Windows full path
            f = f.replace("\\", "/").split("/")[-1]
        elif f.startswith("/") or "\\" in f:
            f = f.replace("\\", "/").split("/")[-1]
        return f

    def _to_full_url(filename):
        if filename.startswith("http"):
            return filename
        # Check if it's a Supabase storage path
        if filename.startswith("article_media/"):
            return f"{SUPABASE_STORAGE_BASE}/{filename}"
        return f"{FLASK_BASE_URL}/static/uploads/{filename}"

    def _ext_type(filename):
        ext = os.path.splitext(filename)[1].lower()
        return "video" if ext in VIDEO_EXTS else "image"

    # --- parse raw value ---
    if media_val is None:
        return []

    parsed = media_val
    if isinstance(media_val, str):
        v = media_val.strip()
        if not v:
            return []
        try:
            parsed = json.loads(v)
        except Exception:
            return []

    # Format 1: Tkinter dict {"author":..., "file_paths":[...]}
    if isinstance(parsed, dict):
        items  = []
        # new unified format also has "media" key (list of dicts)
        if "media" in parsed and isinstance(parsed["media"], list):
            for item in parsed["media"]:
                if isinstance(item, dict):
                    url   = _to_full_url(_clean(item.get("url", "")))
                    thumb = _to_full_url(_clean(item.get("thumbnail", item.get("url", ""))))
                    items.append({"url": url, "thumbnail": thumb,
                                  "type": item.get("type", "image")})
        # legacy file_paths list
        for f in parsed.get("file_paths", []):
            fn    = _clean(f)
            if not fn:
                continue
            url   = _to_full_url(fn)
            itype = _ext_type(fn)
            items.append({"url": url, "thumbnail": url, "type": itype})
        return items

    # Format 2: list (mobile format)
    if isinstance(parsed, list):
        items = []
        for item in parsed:
            if isinstance(item, dict):
                url   = item.get("url", "")
                thumb = item.get("thumbnail", url)
                itype = item.get("type", "image")
                if url and not url.startswith("http"):
                    url   = f"{SUPABASE_STORAGE_BASE}/article_media/{url}"
                    thumb = url
                if url:
                    items.append({"url": url, "thumbnail": thumb, "type": itype})
            elif isinstance(item, str) and item.strip():
                fn    = _clean(item)
                url   = _to_full_url(fn)
                itype = _ext_type(fn)
                items.append({"url": url, "thumbnail": url, "type": itype})
        return items

    return []

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

# GAMITIN NA LANG WERKZEUG PARA SAME SA WEB:
def _hash_password(plain: str) -> str:
    from werkzeug.security import generate_password_hash
    return generate_password_hash(plain)


def _scalar(row, index: int = 0):
    """
    Safely extract a scalar from a tuple or dict row.
    Raw psycopg2 cursors return tuples; RealDictCursor returns dicts.
    """
    if row is None:
        return None
    if isinstance(row, dict):
        return list(row.values())[index]
    return row[index]


def _parse_media(media_val):
    """
    Supabase media column is JSONB — psycopg2 returns it already as a
    Python dict/list. The old MySQL code stored it as a JSON string so
    json.loads() was needed. This helper handles both safely.
    """
    if media_val is None:
        return None, ""

    # Already a dict (psycopg2 JSONB) — convert back to string for compat
    if isinstance(media_val, (dict, list)):
        return media_val, json.dumps(media_val)

    # String — parse it
    if isinstance(media_val, str) and media_val.strip():
        try:
            parsed = json.loads(media_val)
            return parsed, media_val
        except Exception:
            pass

    return None, ""


def _extract_file_paths_csv(media_val) -> str:
    parsed, _ = _parse_media(media_val)
    if not parsed:
        return ""
    if isinstance(parsed, dict):
        fps = parsed.get("file_paths", [])
    elif isinstance(parsed, list):
        fps = parsed
    else:
        return ""
    if isinstance(fps, list):
        return ",".join(str(f) for f in fps if f)
    return ""


def _media_json_str(media_val) -> str:
    """Return media as a JSON string (for tuple field [5])."""
    _, s = _parse_media(media_val)
    return s


def _row_to_admin_tuple(row) -> tuple:
    """
    Works with both tuple rows (raw cursor) and dict rows (RealDictCursor).
    """
    if isinstance(row, dict):
        db_id      = row["id"]
        username   = row.get("username") or ""
        email      = row.get("email") or ""
        first_name = row.get("first_name") or ""
        middle_name= row.get("middle_name") or ""
        last_name  = row.get("last_name") or ""
        status     = row.get("status") or ""
        is_editorial = row.get("is_editorial") or False
        role       = row.get("role") or ""
        is_eic     = row.get("is_eic") or False
    else:
        (db_id, username, email, first_name, middle_name, last_name,
         status, is_editorial, role, is_eic) = row

    is_active = 1 if status == "approved" else 0
    return (
        db_id,
        username   or "",
        email      or "",
        first_name or "",
        middle_name or "",
        last_name  or "",
        is_active,
        int(bool(is_editorial)),
        role,
        int(bool(is_eic)),
    )


def _row_to_article_tuple(row) -> tuple:
    if isinstance(row, dict):
        art_id      = row["id"]
        author_name = row.get("author_name") or ""
        category    = row.get("category") or ""
        headline    = row.get("headline") or ""
        content     = row.get("content") or ""
        media_val   = row.get("media")
        date_str    = row.get("date_str") or ""
    else:
        art_id, author_name, category, headline, content, media_val, date_str = row

    media_json_str = _media_json_str(media_val)
    file_paths_csv = _extract_file_paths_csv(media_val)
    media_items    = resolve_media_items(media_val)   # ← NEW: resolved list of dicts

    return (
        art_id,
        author_name or "",   # 1
        category    or "",   # 2
        headline    or "",   # 3
        content     or "",   # 4
        media_json_str,      # 5  raw JSON (legacy)
        file_paths_csv,      # 6  csv (legacy)
        date_str    or "",   # 7
        headline    or "",   # 8  dup
        content     or "",   # 9  dup
        author_name or "",   # 10 dup
        media_items,         # 11 ← NEW: list of {"url","thumbnail","type"}
    )

# ─────────────────────────────────────────────────────────────────────────────
# Admin fetch helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_admins() -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, email,
                   first_name, middle_name, last_name,
                   status, is_editorial, role, is_eic
            FROM users
            WHERE role IN ('admin', 'superadmin')
            ORDER BY role DESC, last_name, first_name
        """)
        return [_row_to_admin_tuple(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def fetch_users() -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, email, first_name, last_name
            FROM users
            WHERE role = 'user' AND status = 'approved'
            ORDER BY last_name, first_name
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            if isinstance(r, dict):
                result.append((r["id"], r.get("username") or "", r.get("email"), r.get("first_name"), r.get("last_name")))
            else:
                result.append((r[0], r[1] or "", r[2], r[3], r[4]))
        return result
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Pending articles  (superadmin review queue)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_pending() -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                a.id,
                CONCAT(u.first_name, ' ', u.last_name) AS author_name,
                a.category,
                a.headline,
                a.content,
                a.media,
                TO_CHAR(a.updated_at, 'YYYY-MM-DD HH24:MI') AS date_str
            FROM   articles a
            JOIN   users    u ON u.id = a.author_id
            WHERE  a.status     = 'pending'
              AND  a.is_deleted = FALSE
            ORDER  BY a.updated_at ASC
        """)
        return [_row_to_article_tuple(r) for r in cur.fetchall()]
    except Exception as exc:
        print(f"[fetch_pending] Error: {exc}")
        return []
    finally:
        cur.close()
        conn.close()


def approve_article(article_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE articles
            SET    status     = 'approved',
                   feedback   = NULL,
                   updated_at = NOW()
            WHERE  id = %s
              AND  status = 'pending'
              AND  is_deleted = FALSE
        """, (article_id,))
        success = cur.rowcount > 0
        conn.commit()

        if success:
            insert_activity_log(
                user_id=1,
                action="Approved Article",
                description=f"Approved article #{article_id}",
                article_id=article_id,
            )
        return success
    except Exception as exc:
        print(f"[approve_article] Error: {exc}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def request_revision(article_id: int, notes: str, inline_comments: list = None) -> bool:
    """
    Send a revision request back to the article author.
 
    FIX: accepts optional inline_comments list and saves it to the
    highlighted_texts JSONB column so:
      • The Tkinter Needs Revision page (index 11 = feedback) gets the
        human-readable notes string.
      • The Flask web page (highlighted_texts) gets the structured list
        for rendering individual highlights.
 
    Parameters
    ----------
    article_id      : int
    notes           : str   — human-readable combined notes (general + inline summary)
    inline_comments : list  — [{"text": "...", "note": "..."}, ...]  (may be empty)
    """
    if inline_comments is None:
        inline_comments = []
 
    # Ensure it's a plain list of dicts (safe to serialise)
    safe_inline = []
    for item in inline_comments:
        if isinstance(item, dict):
            safe_inline.append({
                "text": str(item.get("text", "")),
                "note": str(item.get("note", "")),
            })
 
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE articles
            SET    status            = 'needs_revision',
                   revision_notes   = %s,
                   feedback         = %s,
                   highlighted_texts = %s::jsonb,
                   feedback_given_at = NOW(),
                   updated_at       = NOW()
            WHERE  id = %s
              AND  status = 'pending'
              AND  is_deleted = FALSE
        """, (
            notes or "",
            notes or "",
            json.dumps(safe_inline),
            article_id,
        ))
        success = cur.rowcount > 0
        conn.commit()
 
        if success:
            insert_activity_log(
                user_id=1,
                action="Requested Revision",
                description=(notes or "")[:200],
                article_id=article_id,
            )
        return success
    except Exception as exc:
        print(f"[request_revision] Error: {exc}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def fetch_published(author_id: int = None) -> list:
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()

        sql = """
            SELECT
                a.id,
                CONCAT(u.first_name, ' ', u.last_name) AS author_name,
                a.category,
                a.updated_at                            AS date_published,
                u.email                                 AS admin_email,
                NULL,
                0                                       AS autosaved,
                a.media,
                a.headline,
                a.content,
                a.media                                 AS media2
            FROM articles a
            JOIN users u ON u.id = a.author_id
            WHERE a.status = 'approved'
              AND a.is_deleted = FALSE
        """

        if author_id:
            cur.execute(sql + " AND a.author_id = %s ORDER BY a.updated_at DESC", (author_id,))
        else:
            cur.execute(sql + " ORDER BY a.updated_at DESC")

        rows = cur.fetchall()
        result = []

        for row in rows:
            if isinstance(row, dict):
                art_id       = row["id"]
                author_name  = row.get("author_name") or ""
                category     = row.get("category") or ""
                date_pub     = row.get("date_published")
                admin_email  = row.get("admin_email") or ""
                autosaved    = 0
                media_val    = row.get("media")
                headline     = row.get("headline") or ""
                content      = row.get("content") or ""
            else:
                (art_id, author_name, category, date_pub,
                 admin_email, _, autosaved, media_val,
                 headline, content, _) = row

            photographer = ""
            parsed, media_json_str = _parse_media(media_val)
            if isinstance(parsed, dict):
                photographer = parsed.get("photographer", "")
                if parsed.get("author"):
                    author_name = parsed["author"]

            result.append((
                art_id,
                headline    or "(Untitled)",
                category    or "",
                date_pub,
                author_name or admin_email or "",
                None,
                autosaved,
                photographer,
                headline    or "(Untitled)",
                content     or "",
                media_json_str,
            ))

        return result

    except Exception as exc:
        print(f"[fetch_published] Error: {exc}")
        return []
    finally:
        if cur:
            cur.close()
        conn.close()


def fetch_under_review(author_id: int) -> list:
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                a.id,
                CONCAT(u.first_name, ' ', u.last_name) AS author_name,
                a.category,
                TO_CHAR(a.updated_at, 'YYYY-MM-DD HH24:MI') AS date_submitted,
                u.email                                      AS admin_email,
                NULL,
                0                                            AS autosaved,
                a.media,
                a.headline,
                a.content,
                a.media                                      AS media2
            FROM articles a
            JOIN users u ON u.id = a.author_id
            WHERE a.status     = 'pending'
              AND a.is_deleted = FALSE
              AND a.author_id  = %s
            ORDER BY a.updated_at DESC
        """, (author_id,))

        rows = cur.fetchall()
        result = []

        for row in rows:
            if isinstance(row, dict):
                art_id      = row["id"]
                author_name = row.get("author_name") or ""
                category    = row.get("category") or ""
                date_sub    = row.get("date_submitted") or ""
                admin_email = row.get("admin_email") or ""
                autosaved   = 0
                media_val   = row.get("media")
                headline    = row.get("headline") or ""
                content     = row.get("content") or ""
            else:
                (art_id, author_name, category, date_sub,
                 admin_email, _, autosaved, media_val,
                 headline, content, _) = row

            photographer = ""
            parsed, media_json_str = _parse_media(media_val)
            if isinstance(parsed, dict):
                photographer = parsed.get("photographer", "")
                if parsed.get("author"):
                    author_name = parsed["author"]

            result.append((
                art_id,
                author_name or "",
                category    or "",
                date_sub    or "",
                admin_email or "",
                None,
                autosaved,
                photographer,
                headline    or "(Untitled)",
                content     or "",
                media_json_str,
            ))

        return result

    except Exception as exc:
        print(f"[fetch_under_review] Error: {exc}")
        return []
    finally:
        if cur:
            cur.close()
        conn.close()


def withdraw_submission(article_id: int, author_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE articles
            SET    status     = 'draft',
                   updated_at = NOW()
            WHERE  id        = %s
              AND  author_id = %s
              AND  status    = 'pending'
              AND  is_deleted = FALSE
        """, (article_id, author_id))
        success = cur.rowcount > 0
        conn.commit()

        if success:
            insert_activity_log(
                user_id=author_id,
                action="Withdrawn Submission",
                article_id=article_id,
            )
        return success
    except Exception as exc:
        print(f"[withdraw_submission] Error: {exc}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Draft operations
# ─────────────────────────────────────────────────────────────────────────────

def save_draft(data: dict) -> dict | None:
    """
    Insert or update a draft article.
 
    file_paths may now contain:
      - dicts:  {"url": "vid.mp4", "thumbnail": "vid_thumb.jpg", "type": "video"}
      - dicts:  {"url": "img.jpg", "thumbnail": "img.jpg",       "type": "image"}
      - strings: "bare_filename.jpg"  (legacy / already-uploaded pass-through)
 
    The media column stores a unified list so every backend can read it:
      [
        {"url": "img.jpg",  "thumbnail": "img.jpg",       "type": "image"},
        {"url": "vid.mp4",  "thumbnail": "vid_thumb.jpg", "type": "video"},
      ]
 
    For backward compat with the web's normalize_media() the old dict format
    {"author":..., "file_paths":[...]} is also kept inside the payload so
    existing web routes that read file_paths still work.
    """
    print("🚨 FINAL DATA RECEIVED:", data)
    conn = get_connection()
    try:
        cur = conn.cursor()
 
        headline     = (data.get("headline") or "").strip() or "(Untitled)"
        content_text = (data.get("content_text") or "").strip()
        category     = (data.get("category") or "").strip() or "Uncategorized"
        author_id    = data.get("author_id")
        author_name  = data.get("author", "")
        photographer = data.get("photographer", "")
 
        # ── Normalise file_paths into a unified media list ────────────────────
        raw_files = data.get("file_paths", [])
        media_list = []       # list of dicts — stored in DB
        file_paths = []       # list of url strings — for legacy file_paths key
 
        for item in raw_files:
            if isinstance(item, dict):
                # Already a proper media dict from upload_helper
                media_list.append({
                    "url":       item.get("url", ""),
                    "thumbnail": item.get("thumbnail", item.get("url", "")),
                    "type":      item.get("type", "image"),
                })
                file_paths.append(item.get("url", ""))
            elif isinstance(item, str) and item.strip():
                # Legacy bare filename — treat as image
                fname = item.strip()
                media_list.append({
                    "url":       fname,
                    "thumbnail": fname,
                    "type":      "image",
                })
                file_paths.append(fname)
 
        # Store as unified list — web's resolve_media_url() handles this format
        # Also include legacy keys so older web routes still work
        media_payload = json.dumps({
            "author":       author_name,
            "photographer": photographer,
            "file_paths":   file_paths,   # legacy flat list for web compat
            "media":        media_list,   # full structured list with thumbnails
        })
 
        draft_id = data.get("draft_id")
 
        if draft_id:
            cur.execute("""
                UPDATE articles
                SET headline   = %s,
                    content    = %s,
                    category   = %s,
                    media      = %s::jsonb,
                    status     = 'draft',
                    updated_at = NOW()
                WHERE id = %s
                  AND is_deleted = FALSE
            """, (headline, content_text, category, media_payload, draft_id))
            conn.commit()
 
            insert_activity_log(
                user_id=author_id,
                action="Updated Draft",
                description=headline,
                article_id=draft_id,
            )
            return {"id": draft_id}
 
        else:
            if not author_id:
                print("[save_draft] ERROR: author_id is required for new drafts")
                return None
 
            new_id = execute_insert("""
                INSERT INTO articles
                    (headline, content, category, author_id,
                     media, status, is_deleted)
                VALUES (%s, %s, %s, %s, %s::jsonb, 'draft', FALSE)
            """, (headline, content_text, category, author_id, media_payload))
 
            return {"id": new_id} if new_id else None
 
    except Exception as exc:
        conn.rollback()
        print(f"[save_draft] Error: {exc}")
        return None
    finally:
        cur.close()
        conn.close()


def fetch_drafts(author_id: int = None) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()

        sql = """
            SELECT a.id,
                   CONCAT(u.first_name, ' ', u.last_name)           AS author_name,
                   a.category,
                   TO_CHAR(a.updated_at, 'Mon DD, YYYY  HH12:MI AM') AS last_updated,
                   u.email                                            AS admin_email,
                   NULL,
                   0                                                  AS autosaved,
                   a.media,
                   a.headline,
                   a.content
            FROM   articles a
            JOIN   users    u ON u.id = a.author_id
            WHERE  a.status     = 'draft'
              AND  a.is_deleted = FALSE
        """
        if author_id:
            cur.execute(sql + " AND a.author_id = %s ORDER BY a.updated_at DESC", (author_id,))
        else:
            cur.execute(sql + " ORDER BY a.updated_at DESC")

        rows = cur.fetchall()
        result = []

        for row in rows:
            if isinstance(row, dict):
                art_id       = row["id"]
                author_name  = row.get("author_name") or ""
                category     = row.get("category") or ""
                last_updated = row.get("last_updated") or ""
                admin_email  = row.get("admin_email") or ""
                autosaved    = 0
                media_val    = row.get("media")
                headline     = row.get("headline") or ""
                content      = row.get("content") or ""
            else:
                (art_id, author_name, category, last_updated,
                 admin_email, _, autosaved, media_val,
                 headline, content) = row

            photographer = ""
            parsed, media_json_str = _parse_media(media_val)
            if isinstance(parsed, dict):
                photographer = parsed.get("photographer", "")
                if parsed.get("author"):
                    author_name = parsed["author"]

            result.append((
                art_id,
                author_name  or "",
                category     or "",
                last_updated or "",
                admin_email  or "",
                None,
                autosaved,
                photographer,
                headline or "(Untitled)",
                content  or "",
                media_json_str,
            ))

        return result

    except Exception as exc:
        print(f"[fetch_drafts] Error: {exc}")
        return []
    finally:
        cur.close()
        conn.close()


def fetch_needs_revision(author_id: int) -> list:
    """
    Fetch articles that need revision for a specific author.
 
    Tuple layout (12 fields):
      0  id
      1  author_name
      2  category
      3  headline
      4  content
      5  media_json_str
      6  file_paths_csv
      7  date_str
      8  headline          (compat dup)
      9  content           (compat dup)
      10 author_name       (compat dup)
      11 feedback          ← full revision notes shown in modal
 
    No change to this function — listed here so you can confirm the
    field at index 11 is `a.feedback` which is now populated correctly
    by the fixed request_revision above.
    """
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                a.id,
                CONCAT(u.first_name, ' ', u.last_name)            AS author_name,
                a.category,
                a.headline,
                a.content,
                a.media,
                TO_CHAR(a.updated_at, 'Mon DD, YYYY  HH12:MI AM') AS date_str,
                a.feedback
            FROM articles a
            JOIN users u ON u.id = a.author_id
            WHERE a.status     = 'needs_revision'
              AND a.is_deleted = FALSE
              AND a.author_id  = %s
            ORDER BY a.updated_at DESC
        """, (author_id,))
 
        rows = cur.fetchall()
        result = []
 
        for row in rows:
            if isinstance(row, dict):
                art_id      = row["id"]
                author_name = row.get("author_name") or ""
                category    = row.get("category") or ""
                headline    = row.get("headline") or ""
                content     = row.get("content") or ""
                media_val   = row.get("media")
                date_str    = row.get("date_str") or ""
                feedback    = row.get("feedback") or ""
            else:
                (art_id, author_name, category, headline,
                 content, media_val, date_str, feedback) = row
 
            # Reuse the helpers from the existing file
            from services.admin_db_service import _parse_media, _extract_file_paths_csv
            parsed, media_json_str = _parse_media(media_val)
            file_paths_csv = _extract_file_paths_csv(media_val)
 
            result.append((
                art_id,
                author_name    or "",  # 1
                category       or "",  # 2
                headline       or "",  # 3
                content        or "",  # 4
                media_json_str,        # 5
                file_paths_csv,        # 6
                date_str       or "",  # 7
                headline       or "",  # 8  compat dup
                content        or "",  # 9  compat dup
                author_name    or "",  # 10 compat dup
                feedback       or "",  # 11 ← feedback/revision_notes text
            ))
 
        return result
 
    except Exception as exc:
        print(f"[fetch_needs_revision] Error: {exc}")
        return []
    finally:
        if cur:
            cur.close()
        conn.close()


def save_revision_edit(article_id: int, headline: str, body: str, author_id: int) -> bool:
    """
    FIX: status = 'needs_revision'  (was 'rejected' in MySQL version)
    """
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE articles
            SET headline   = %s,
                content    = %s,
                updated_at = NOW()
            WHERE id        = %s
              AND author_id = %s
              AND status    = 'needs_revision'
              AND is_deleted = FALSE
        """, (headline.strip(), body.strip(), article_id, author_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        print(f"[save_revision_edit] Error: {exc}")
        conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        conn.close()


def delete_draft(article_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE articles
            SET    is_deleted = TRUE,
                   updated_at = NOW()
            WHERE  id = %s AND status = 'draft'
        """, (article_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        print(f"[delete_draft] Error: {exc}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


def publish_article(data: dict) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()

        media_payload = json.dumps({
            "author":       data.get("author", ""),
            "photographer": data.get("photographer", ""),
            "file_paths":   data.get("file_paths", []),
        })
        author_id = data.get("author_id")
        draft_id  = data.get("draft_id")

        if draft_id:
            cur.execute("""
                UPDATE articles
                SET headline   = %s,
                    content    = %s,
                    category   = %s,
                    media      = %s::jsonb,
                    status     = 'approved',
                    updated_at = NOW()
                WHERE id = %s AND is_deleted = FALSE
            """, (
                (data.get("headline") or "").strip(),
                (data.get("content_text") or "").strip(),
                data.get("category", "Uncategorized"),
                media_payload,
                draft_id,
            ))
        else:
            if not author_id:
                print("[publish_article] ERROR: author_id required")
                return False
            execute_insert("""
                INSERT INTO articles
                    (headline, content, category, author_id,
                     media, status, is_deleted)
                VALUES (%s, %s, %s, %s, %s::jsonb, 'approved', FALSE)
            """, (
                (data.get("headline") or "").strip(),
                (data.get("content_text") or "").strip(),
                data.get("category", "Uncategorized"),
                author_id,
                media_payload,
            ))

        conn.commit()

        insert_activity_log(
            user_id=author_id,
            action="Published Article",
            description=data.get("headline", ""),
        )
        return True
    except Exception as exc:
        print(f"[publish_article] Error: {exc}")
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Admin CRUD
# ─────────────────────────────────────────────────────────────────────────────

def create_admin(first_name, middle_name, last_name, email, password):
    conn = get_connection()
    try:
        cur = conn.cursor()
        base = f"{first_name.lower().strip()}.{last_name.lower().strip()}"
        base = "".join(c if c.isalnum() or c == "." else "" for c in base)
        username = base
        suffix = 1
        while True:
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if not cur.fetchone():
                break
            username = f"{base}{suffix}"
            suffix += 1

        hashed = _hash_password(password)

        # FIX: use execute_insert for RETURNING id
        new_id = execute_insert("""
            INSERT INTO users
              (first_name, middle_name, last_name, username,
               email, password, role, status,
               is_verified, is_eic, is_editorial, must_change_password)
            VALUES (%s, %s, %s, %s, %s, %s,
                    'admin', 'approved',
                    TRUE, FALSE, FALSE, TRUE)
        """, (first_name, middle_name or None, last_name, username, email, hashed))
        return new_id
    except Exception as exc:
        print(f"[create_admin] Error: {exc}")
        return None
    finally:
        cur.close()
        conn.close()


def update_admin(user_id, username, email) -> bool:
    affected = execute_update("""
        UPDATE users SET username = %s, email = %s
        WHERE id = %s AND role IN ('admin', 'superadmin')
    """, (username, email, user_id))
    return affected > 0


def disable_admin(user_id) -> bool:
    affected = execute_update("""
        UPDATE users SET status = 'rejected'
        WHERE id = %s AND role IN ('admin', 'superadmin')
    """, (user_id,))
    return affected > 0


def enable_admin(user_id) -> bool:
    affected = execute_update("""
        UPDATE users SET status = 'approved'
        WHERE id = %s AND role IN ('admin', 'superadmin')
    """, (user_id,))
    return affected > 0


def promote_eb(user_id) -> bool:
    affected = execute_update("""
        UPDATE users
        SET    is_editorial = TRUE,
               role         = 'superadmin'
        WHERE  id   = %s
          AND  role = 'admin'
    """, (user_id,))
    return affected > 0


def demote_eb(user_id) -> bool:
    row = fetch_one("SELECT is_eic FROM users WHERE id = %s", (user_id,))
    if not row or row.get("is_eic"):
        return False
    affected = execute_update("""
        UPDATE users
        SET    is_editorial = FALSE,
               role         = 'admin'
        WHERE  id     = %s
          AND  is_eic = FALSE
    """, (user_id,))
    return affected > 0


def promote_to_superadmin(user_id) -> bool:
    affected = execute_update("""
        UPDATE users SET role = 'superadmin'
        WHERE id = %s AND role = 'admin'
    """, (user_id,))
    return affected > 0


def demote_to_admin(user_id) -> bool:
    row = fetch_one("SELECT is_eic FROM users WHERE id = %s", (user_id,))
    if not row or row.get("is_eic"):
        return False
    affected = execute_update("""
        UPDATE users SET role = 'admin'
        WHERE id = %s AND role = 'superadmin' AND is_eic = FALSE
    """, (user_id,))
    return affected > 0


def promote_user_to_admin(user_id, password) -> bool:
    hashed = _hash_password(password)
    affected = execute_update("""
        UPDATE users
        SET role = 'admin',
            status = 'approved',
            is_verified = TRUE,
            password = %s,
            must_change_password = TRUE
        WHERE id = %s AND role = 'user'
    """, (hashed, user_id))
    return affected > 0


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard stats
# ─────────────────────────────────────────────────────────────────────────────

def fetch_dashboard_stats() -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin','superadmin')")
        total_admins = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
        total_users = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM articles WHERE status = 'approved' AND is_deleted = FALSE")
        total_articles = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM articles WHERE status = 'pending' AND is_deleted = FALSE")
        pending_reviews = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
        pending_users = _scalar(cur.fetchone())

        return {
            "Total Admins":    str(total_admins),
            "Total Users":     f"{total_users:,}",
            "Total Articles":  str(total_articles),
            "Pending Reviews": str(pending_reviews),
            "Pending Users":   str(pending_users),
        }
    finally:
        cur.close()
        conn.close()


def fetch_recent_articles(limit: int = 3) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.headline,
                   CONCAT(u.first_name, ' ', u.last_name),
                   TO_CHAR(a.created_at, 'Mon DD, YYYY')
            FROM articles a
            JOIN users u ON u.id = a.author_id
            WHERE a.is_deleted = FALSE
            ORDER BY a.created_at DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def fetch_recent_users(limit: int = 3) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT CONCAT(first_name, ' ', last_name),
                   email,
                   TO_CHAR(created_at, 'Mon DD, YYYY')
            FROM users
            WHERE role = 'user'
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def submit_revision(article_id: int, author_id: int) -> bool:
    """
    FIX: status check 'needs_revision'  (was 'rejected' in MySQL version)
    """
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE articles
            SET status     = 'pending',
                feedback   = NULL,
                updated_at = NOW()
            WHERE id        = %s
              AND author_id = %s
              AND status    = 'needs_revision'
              AND is_deleted = FALSE
        """, (article_id, author_id))
        success = cur.rowcount > 0
        conn.commit()

        if success:
            insert_activity_log(
                user_id=author_id,
                action="Submitted Revision",
                article_id=article_id,
            )
        return success
    except Exception as exc:
        print(f"[submit_revision] Error: {exc}")
        conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        conn.close()


def fetch_admin_stats() -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users WHERE is_deleted = FALSE OR is_deleted IS NULL")
        total_users = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM articles WHERE status = 'approved' AND is_deleted = FALSE")
        total_articles = _scalar(cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM articles WHERE status = 'pending' AND is_deleted = FALSE")
        pending_items = _scalar(cur.fetchone())

        try:
            cur.execute("SELECT COUNT(*) FROM comments")
            total_comments = _scalar(cur.fetchone())
        except Exception:
            total_comments = 0

        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'approved'")
        active_users = _scalar(cur.fetchone())

        approved_users = active_users

        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
        pending_users = _scalar(cur.fetchone())

        return {
            "total_users":    total_users,
            "total_articles": total_articles,
            "pending_items":  pending_items,
            "total_comments": total_comments,
            "active_users":   active_users,
            "approved_users": approved_users,
            "pending_users":  pending_users,
        }
    except Exception as exc:
        print(f"[fetch_admin_stats] Error: {exc}")
        return {
            "total_users": "—", "total_articles": "—",
            "pending_items": "—", "total_comments": "—",
            "active_users": "—", "approved_users": "—",
            "pending_users": "—",
        }
    finally:
        cur.close()
        conn.close()


def fetch_top_contributors(limit: int = 5) -> list:
    """
    FIX: GROUP BY must include all non-aggregate columns in PostgreSQL.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT CONCAT(u.first_name, ' ', u.last_name) AS name,
                   COUNT(a.id) AS article_count
            FROM   articles a
            JOIN   users    u ON u.id = a.author_id
            WHERE  a.is_deleted = FALSE
              AND  a.status     = 'approved'
            GROUP  BY a.author_id, u.first_name, u.last_name
            ORDER  BY article_count DESC
            LIMIT  %s
        """, (limit,))
        rows = cur.fetchall()
        result = []
        for r in rows:
            if isinstance(r, dict):
                result.append((r["name"], r["article_count"]))
            else:
                result.append((r[0], r[1]))
        return result
    except Exception as exc:
        print(f"[fetch_top_contributors] Error: {exc}")
        return []
    finally:
        cur.close()
        conn.close()


def fetch_activity_trends(weeks: int = 8) -> list:
    """
    FIX: DATE_SUB / WEEKDAY → PostgreSQL equivalents.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                TO_CHAR(
                    date_trunc('week', a.created_at),
                    'Mon DD'
                ) AS week_start,
                COUNT(*) AS cnt
            FROM articles a
            WHERE a.is_deleted = FALSE
              AND a.status     = 'approved'
              AND a.created_at >= NOW() - (%s || ' weeks')::interval
            GROUP BY date_trunc('week', a.created_at)
            ORDER BY date_trunc('week', a.created_at) ASC
        """, (weeks,))
        rows = cur.fetchall()
        result = []
        for r in rows:
            if isinstance(r, dict):
                result.append((r["week_start"], r["cnt"]))
            else:
                result.append((r[0], r[1]))
        return result
    except Exception as exc:
        print(f"[fetch_activity_trends] Error: {exc}")
        return []
    finally:
        cur.close()
        conn.close()


def fetch_profile(user_id: int) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT first_name, last_name, email, profile_image
            FROM   users
            WHERE  id = %s
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            first = row.get("first_name") or ""
            last  = row.get("last_name") or ""
            email = row.get("email") or ""
            pic   = row.get("profile_image")
        else:
            first, last, email, pic = row
        return {
            "name":          f"{first} {last}".strip(),
            "email":         email or "",
            "profile_image": pic or None,
        }
    except Exception as exc:
        print(f"[fetch_profile] Error: {exc}")
        return None
    finally:
        cur.close()
        conn.close()


def delete_account(user_id: int) -> bool:
    """
    FIX: removed MySQL DATABASE() check — Supabase already has is_deleted column.
    """
    affected = execute_update("""
        UPDATE users
        SET    status     = 'deleted',
               is_deleted = TRUE,
               updated_at = NOW()
        WHERE  id = %s
    """, (user_id,))
    success = affected > 0
    if success:
        try:
            insert_activity_log(user_id=user_id, action="Deleted Account")
        except Exception:
            pass
    return success


def submit_for_review(data: dict) -> bool:
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()

        draft_id  = data.get("draft_id")
        author_id = data.get("author_id")

        headline     = (data.get("headline") or "").strip()
        content_text = (data.get("content_text") or "").strip()
        category     = (data.get("category") or "").strip() or "Uncategorized"

        media_payload = json.dumps({
            "author":       data.get("author", ""),
            "photographer": data.get("photographer", ""),
            "file_paths":   data.get("file_paths", []),
        })

        if draft_id:
            cur.execute("""
                UPDATE articles
                SET headline   = %s,
                    content    = %s,
                    category   = %s,
                    media      = %s::jsonb,
                    status     = 'pending',
                    updated_at = NOW()
                WHERE id = %s
                  AND is_deleted = FALSE
            """, (headline, content_text, category, media_payload, draft_id))
        else:
            if not author_id:
                print("[submit_for_review] ERROR: author_id is required")
                return False
            cur.execute("""
                INSERT INTO articles
                    (headline, content, category, author_id,
                     media, status, is_deleted)
                VALUES (%s, %s, %s, %s, %s::jsonb, 'pending', FALSE)
            """, (headline, content_text, category, author_id, media_payload))

        success = cur.rowcount > 0
        conn.commit()

        if success and author_id:
            insert_activity_log(
                user_id=author_id,
                action="Submitted",
                description=headline,
            )
        return success

    except Exception as exc:
        print(f"[submit_for_review] Error: {exc}")
        conn.rollback()
        return False
    finally:
        if cur:
            cur.close()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Callback builders
# ─────────────────────────────────────────────────────────────────────────────

def build_callbacks() -> dict:
    return {
        "fetch_admins":           fetch_admins,
        "fetch_users":            fetch_users,
        "create_admin":           create_admin,
        "update_admin":           update_admin,
        "disable_admin":          disable_admin,
        "enable_admin":           enable_admin,
        "promote_eb":             promote_eb,
        "demote_eb":              demote_eb,
        "promote_to_superadmin":  promote_to_superadmin,
        "demote_to_admin":        demote_to_admin,
        "promote_user_to_admin":  promote_user_to_admin,
        "fetch_profile":          fetch_profile,
    }


def build_pending_callbacks() -> dict:
    return {
        "fetch_pending":    fetch_pending,
        "approve_article":  approve_article,
        "request_revision": request_revision,
        "fetch_profile":    fetch_profile,
    }


def build_admin_callbacks(author_id: int) -> dict:
    from services.api_client import APIClient
    api = APIClient()   # reads FLASK_API_URL and TKINTER_API_TOKEN from env

    return {
        "fetch_profile":           lambda user_id=None: fetch_profile(author_id),
        "delete_account":          delete_account,
        "fetch_active_categories": api.fetch_categories,

        # Drafts — now go through API
        "fetch_drafts":            lambda: api.fetch_drafts(author_id),
        "save_draft":              lambda data: api.save_draft({**data, "author_id": author_id}),
        "delete_draft":            api.delete_draft,
        "submit_for_review":       lambda data: api.submit_for_review({**data, "author_id": author_id}),

        # These still use direct DB until you add more API routes
        "publish_article":         lambda data: publish_article({**data, "author_id": author_id}),
        "fetch_under_review":      lambda: fetch_under_review(author_id),
        "withdraw_submission":     lambda art_id: withdraw_submission(art_id, author_id),
        "fetch_needs_revision":    lambda: fetch_needs_revision(author_id),
        "save_revision_edit":      lambda art_id, headline, body: save_revision_edit(art_id, headline, body, author_id),
        "submit_revision":         lambda art_id: submit_revision(art_id, author_id),
        "fetch_published":         lambda: fetch_published(author_id),
        "fetch_pending":           fetch_pending,

        "flask_url":               os.getenv("FLASK_URL",         "http://127.0.0.1:5000"),
        "api_token":               os.getenv("TKINTER_API_TOKEN", "supersecret123"),
    }


def build_dashboard_callbacks() -> dict:
    return {
        "fetch_admin_stats":      fetch_admin_stats,
        "fetch_top_contributors": fetch_top_contributors,
        "fetch_activity_trends":  fetch_activity_trends,
        "fetch_profile":          lambda uid: fetch_one(
            "SELECT CONCAT(first_name, ' ', last_name) AS name, "
            "email, profile_image FROM users WHERE id = %s",
            (uid,)
        ) or {},
    }

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