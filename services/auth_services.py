"""
services/auth_service.py
────────────────────────
SUPABASE CHANGES:
  - login_user now handles BOTH hash formats:
      * bcrypt  ($2b$...) — used by Tkinter app
      * werkzeug (pbkdf2:...) — used by Flask web app
    This is needed because existing users registered via the web
    have werkzeug hashes, not bcrypt.
"""

from db import fetch_one, execute_insert, execute_update
from services.article_service import insert_activity_log

import bcrypt


# ─────────────────────────────────────────────────────────────────────────────
# Internal: verify password against any hash format
# ─────────────────────────────────────────────────────────────────────────────

def _check_password(plain: str, stored_hash: str) -> bool:
    """
    Try bcrypt first, then werkzeug pbkdf2/scrypt.
    Returns True if password matches.
    """
    if not stored_hash:
        return False

    # ── bcrypt (Tkinter-registered users) ────────────────────────────────
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        try:
            hash_bytes = stored_hash.encode("utf-8") if isinstance(stored_hash, str) else stored_hash
            return bcrypt.checkpw(plain.encode("utf-8"), hash_bytes)
        except Exception as e:
            print(f"[_check_password] bcrypt error: {e}")
            return False

    # ── werkzeug (Flask web-registered users) ────────────────────────────
    if stored_hash.startswith("pbkdf2:") or stored_hash.startswith("scrypt:"):
        try:
            from werkzeug.security import check_password_hash
            return check_password_hash(stored_hash, plain)
        except Exception as e:
            print(f"[_check_password] werkzeug error: {e}")
            return False

    # ── Unknown format — try both ─────────────────────────────────────────
    try:
        hash_bytes = stored_hash.encode("utf-8") if isinstance(stored_hash, str) else stored_hash
        if bcrypt.checkpw(plain.encode("utf-8"), hash_bytes):
            return True
    except Exception:
        pass

    try:
        from werkzeug.security import check_password_hash
        return check_password_hash(stored_hash, plain)
    except Exception:
        pass

    return False


# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_user(first_name, last_name, middle_name, username, email, password):
    first_name  = first_name.strip()
    last_name   = last_name.strip()
    middle_name = middle_name.strip() if middle_name else None
    username    = username.strip()
    email       = email.strip().lower()

    result = fetch_one("SELECT COUNT(*) AS total FROM users WHERE email = %s", (email,))
    if result and result["total"] > 0:
        raise ValueError("Email is already registered.")

    result = fetch_one("SELECT COUNT(*) AS total FROM users WHERE username = %s", (username,))
    if result and result["total"] > 0:
        raise ValueError("Username is already taken.")

    from werkzeug.security import generate_password_hash
    hashed_pw = generate_password_hash(password)

    result        = fetch_one("SELECT COUNT(*) AS total FROM users")
    is_first_user = (result["total"] == 0) if result else True

    role   = "superadmin" if is_first_user else "user"
    status = "approved"   if is_first_user else "pending"
    is_eic = True         if is_first_user else False

    new_user_id = execute_insert("""
        INSERT INTO users (
            first_name, middle_name, last_name,
            username, email, password,
            role, status, is_verified, is_eic
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s)
    """, (
        first_name, middle_name, last_name,
        username, email, hashed_pw,
        role, status, is_eic,
    ))

    insert_activity_log(
        user_id=new_user_id,
        action="Registered",
        description=f"{first_name} {last_name} created an account",
    )
    return new_user_id


# ─────────────────────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────────────────────

def login_user(email, password):
    query = """
        SELECT id, first_name, last_name, email, password,
               role, must_change_password, is_eic, is_editorial
        FROM users
        WHERE email = %s
        LIMIT 1
    """
    user = fetch_one(query, (email.strip().lower(),))

    if not user:
        return None

    stored_hash = user.get("password") or ""

    if _check_password(password, stored_hash):
        insert_activity_log(
            user_id=user["id"],
            action="Logged In",
            description=f"{user['email']} logged in",
        )
        if user.get("must_change_password"):
            user["force_change"] = True
        return user

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Verification helpers
# ─────────────────────────────────────────────────────────────────────────────

def mark_user_verified(user_id):
    execute_update("UPDATE users SET is_verified = TRUE WHERE id = %s", (user_id,))
    return True


def is_user_verified(user_id):
    user = fetch_one("SELECT is_verified FROM users WHERE id = %s LIMIT 1", (user_id,))
    return bool(user and user.get("is_verified"))


def is_user_accepted(user_id):
    user = fetch_one("SELECT status FROM users WHERE id = %s LIMIT 1", (user_id,))
    return bool(user and user.get("status") == "approved")


# ─────────────────────────────────────────────────────────────────────────────
# Profile update
# ─────────────────────────────────────────────────────────────────────────────

def update_profile(user_id, name: str, last_name_or_empty: str,
                   email: str, avatar_path=None):
    """
    Update a user's profile info.
    Returns (bool, str).
    """
    if user_id is None:
        return False, "Invalid user session."

    name               = (name or "").strip()
    last_name_or_empty = (last_name_or_empty or "").strip()

    if last_name_or_empty:
        first_name = name
        last_name  = last_name_or_empty
    else:
        parts      = name.split(" ", 1)
        first_name = parts[0]
        last_name  = parts[1].strip() if len(parts) > 1 else ""

    email = (email or "").strip().lower()

    if not first_name:
        return False, "Full name cannot be empty."
    if not email or "@" not in email:
        return False, "Please enter a valid email address."

    current = fetch_one(
        "SELECT first_name, last_name, email FROM users WHERE id = %s",
        (user_id,),
    )
    if not current:
        return False, "User not found."

    if email != (current.get("email") or "").strip().lower():
        taken = fetch_one(
            "SELECT id FROM users WHERE email = %s AND id != %s",
            (email, user_id),
        )
        if taken:
            return False, "Email is already in use by another account."

    name_changed   = (first_name != current.get("first_name") or
                      last_name  != current.get("last_name"))
    email_changed  = email != (current.get("email") or "").strip().lower()
    avatar_changed = avatar_path is not None

    if not name_changed and not email_changed and not avatar_changed:
        return False, "No changes detected."

    execute_update(
        """
        UPDATE users
        SET first_name    = %s,
            last_name     = %s,
            email         = %s,
            profile_image = COALESCE(%s, profile_image)
        WHERE id = %s
        """,
        (first_name, last_name, email, avatar_path, user_id),
    )

    insert_activity_log(
        user_id,
        "Updated Profile",
        f"{first_name} {last_name} updated their profile info",
    )
    return True, "Profile updated successfully."


# ─────────────────────────────────────────────────────────────────────────────
# Password change
# ─────────────────────────────────────────────────────────────────────────────

def change_password(user_id, current_password: str, new_password: str):
    """
    Secure password change. Handles both bcrypt and werkzeug hashes.
    Returns (bool, str).
    """
    if user_id is None:
        return False, "Invalid user session."

    if not current_password or not new_password:
        return False, "Both current and new passwords are required."

    if len(new_password) < 8:
        return False, "New password must be at least 8 characters."

    if current_password == new_password:
        return False, "New password must be different from the current password."

    user = fetch_one(
        "SELECT password FROM users WHERE id = %s LIMIT 1",
        (user_id,),
    )
    if not user:
        return False, "User not found."

    stored_hash = user.get("password") or ""

    if not _check_password(current_password, stored_hash):
        return False, "Current password is incorrect."

    # Always re-hash with bcrypt going forward
    from werkzeug.security import generate_password_hash
    new_hash = generate_password_hash(new_password)

    execute_update(
        "UPDATE users SET password = %s WHERE id = %s",
        (new_hash, user_id),
    )

    insert_activity_log(user_id, "Changed Password", "User updated their password")
    return True, "Password changed successfully."