from db import fetch_one, execute_insert, execute_update
import bcrypt


def register_user(first_name, last_name, middle_name, username, email, password):
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    result = fetch_one("SELECT COUNT(*) AS total FROM users")
    is_first_user = (result["total"] == 0) if result else True

    role = "superadmin" if is_first_user else "user"

    query = """
    INSERT INTO users (
        first_name,
        middle_name,
        last_name,
        username,
        email,
        password,
        role,
        status,
        is_verified
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, 'approved', FALSE)
    """

    return execute_insert(query, (
        first_name,
        middle_name,
        last_name,
        username,
        email,
        hashed_pw.decode("utf-8"),
        role
    ))


def login_user(email, password):
    query = """
    SELECT * FROM users
    WHERE email = %s
    LIMIT 1
    """

    user = fetch_one(query, (email,))

    if not user:
        return None

    stored_hash = user["password"]

    if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
        return user

    return None


def mark_user_verified(user_id):
    query = """
    UPDATE users
    SET is_verified = TRUE
    WHERE id = %s
    """
    execute_update(query, (user_id,))
    return True


def is_user_verified(user_id):
    query = """
    SELECT is_verified
    FROM users
    WHERE id = %s
    LIMIT 1
    """
    user = fetch_one(query, (user_id,))

    if not user:
        return False

    return bool(user["is_verified"])