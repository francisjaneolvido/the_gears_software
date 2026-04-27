import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "lab204",
    "database": "gears_db",
}


def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            return connection

        return None

    except Error as e:
        print(f"Database connection error: {e}")
        return None


def fetch_one(query, params=None):
    connection = get_connection()

    if not connection:
        return None

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(query, params or ())
        return cursor.fetchone()

    except Error as e:
        print(f"Fetch one error: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


def fetch_all(query, params=None):
    connection = get_connection()

    if not connection:
        return []

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(query, params or ())
        return cursor.fetchall()

    except Error as e:
        print(f"Fetch all error: {e}")
        return []

    finally:
        cursor.close()
        connection.close()


def execute_query(query, params=None):
    connection = get_connection()

    if not connection:
        return False

    cursor = connection.cursor()

    try:
        cursor.execute(query, params or ())
        connection.commit()
        return True

    except Error as e:
        print(f"Execute query error: {e}")
        connection.rollback()
        return False

    finally:
        cursor.close()
        connection.close()


def execute_insert(query, params=None):
    connection = get_connection()

    if not connection:
        return None

    cursor = connection.cursor()

    try:
        cursor.execute(query, params or ())
        connection.commit()
        return cursor.lastrowid

    except Error as e:
        print(f"Insert error: {e}")
        connection.rollback()
        return None

    finally:
        cursor.close()
        connection.close()


def execute_update(query, params=None):
    """
    Run UPDATE or DELETE query.
    Returns number of affected rows.
    """
    connection = get_connection()

    if not connection:
        return 0

    cursor = connection.cursor()

    try:
        cursor.execute(query, params or ())
        connection.commit()
        return cursor.rowcount

    except Error as e:
        print(f"Update error: {e}")
        connection.rollback()
        return 0

    finally:
        cursor.close()
        connection.close()


def test_connection():
    connection = get_connection()

    if connection:
        connection.close()
        return True

    return False