from db import fetch_one, fetch_all, execute_insert


def get_article_by_id(article_id):
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


def get_comments_by_article(article_id):
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
    query = """
    INSERT INTO comments (article_id, user_id, comment)
    VALUES (%s, %s, %s)
    """
    return execute_insert(query, (article_id, user_id, comment_text))