import tkinter as tk
from tkinter import messagebox
from dotenv import load_dotenv

from theme import COLORS
from user.landing_page import LandingPage
from user.user_homepage import UserHomepage
from user.article_detail_page import ArticleDetailPage
from user.view_all_article import ViewAllArticle
import os
# ── FIX: ensure_schema removed (Supabase schema already exists)
from services.admin_db_service import build_admin_callbacks
from services.article_service import (
    ensure_categories_schema,
    ensure_activity_logs_schema,
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

print(f"[DEBUG] TKINTER_API_TOKEN = '{os.getenv('TKINTER_API_TOKEN')}'")
print(f"[DEBUG] FLASK_URL = '{os.getenv('FLASK_URL')}'")

# ─────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────

def clear_root(root):
    for widget in root.winfo_children():
        widget.destroy()


# ─────────────────────────────────────────────────────────────
# USER / READER PAGES
# ─────────────────────────────────────────────────────────────

def show_landing(root):
    root.current_user = None
    clear_root(root)
    LandingPage(root)


def show_articles(root, user=None):
    from services.article_service import (
        fetch_homepage_articles,
        fetch_categories,
    )
 
    clear_root(root)
 
    UserHomepage(
        root,
        user=user,
        db_callbacks={
            "fetch_homepage_articles": fetch_homepage_articles,
            "fetch_categories":        fetch_categories,
            "flask_url":               os.getenv("FLASK_URL", "http://127.0.0.1:5000"),
        }
    )
 

def show_view_all_article(root):
    clear_root(root)
    ViewAllArticle(root)


def show_article_detail(root, article_id, user=None, from_landing=False):
    clear_root(root)
    ArticleDetailPage(
        root,
        article_id=article_id,
        user=user,
        from_landing=from_landing
    )


# ─────────────────────────────────────────────────────────────
# SUPERADMIN PAGES
# ─────────────────────────────────────────────────────────────

def show_superadmin(root, user=None):
    from superadmin.superadmin_dashboard import SuperadminDashboard
    from services.admin_db_service import (
        fetch_dashboard_stats,
        fetch_recent_articles,
        fetch_recent_users,
    )

    clear_root(root)

    if user:
        root.current_user = user

    SuperadminDashboard(
        root,
        user=root.current_user,
        stats=fetch_dashboard_stats(),
        recent_articles=fetch_recent_articles(),
        recent_users=fetch_recent_users(),
    )


def show_manage_admins(root, user=None):
    from superadmin.superadmin_manage_admins import ManageAdmins
    from services.admin_db_service import build_callbacks

    clear_root(root)
    ManageAdmins(root, user=root.current_user, db_callbacks=build_callbacks())


def show_manage_users(root, user=None):
    from superadmin.superadmin_manage_users import ManageUsers
    from services.users_db_services import build_user_callbacks

    clear_root(root)
    ManageUsers(root, user=root.current_user, db_callbacks=build_user_callbacks())


def show_pending_articles(root, user=None):
    from superadmin.superadmin_pending_articles import PendingArticles
    from services.admin_db_service import build_admin_callbacks

    clear_root(root)
    PendingArticles(
        root,
        user=root.current_user,
        db_callbacks=build_admin_callbacks(root.current_user[3]),
    )


def show_categories(root, user=None):
    from superadmin.superadmin_categories import SuperadminCategories
    from services.article_service import build_category_callbacks

    clear_root(root)
    SuperadminCategories(
        root,
        user=root.current_user,
        db_callbacks=build_category_callbacks(),
    )


def show_activity_logs(root, user=None):
    from superadmin.superadmin_activity_logs import ActivityLogs
    from services.article_service import build_activity_log_callbacks

    clear_root(root)
    ActivityLogs(
        root,
        user=root.current_user,
        db_callbacks=build_activity_log_callbacks(),
    )


# ─────────────────────────────────────────────────────────────
# ADMIN PAGES
# ─────────────────────────────────────────────────────────────

def _admin_user_id(root):
    """Safely extract the DB user id from root.current_user (index 3)."""
    user = root.current_user
    return user[3] if user and len(user) > 3 else None


def show_admin(root, user=None):
    from admin.admin_dashboard import AdminDashboard
    from services.admin_db_service import build_dashboard_callbacks

    clear_root(root)

    if user:
        root.current_user = user

    AdminDashboard(
        root,
        user=root.current_user,
        db_callbacks=build_dashboard_callbacks()
    )


def show_admin_drafts(root, user=None):
    from admin.admin_drafts import AdminDrafts
    import os

    clear_root(root)
    user_id   = _admin_user_id(root)
    callbacks = build_admin_callbacks(user_id)
    callbacks["flask_url"] = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
    callbacks["api_token"] = os.getenv("TKINTER_API_TOKEN", "supersecret123")
    AdminDrafts(root, user=root.current_user, db_callbacks=callbacks)


def show_admin_publish(root, user=None):
    from admin.admin_create_article import AdminPublish
    import os

    clear_root(root)
    user_id   = _admin_user_id(root)
    callbacks = build_admin_callbacks(user_id)
    callbacks["flask_url"] = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
    callbacks["api_token"] = os.getenv("TKINTER_API_TOKEN", "supersecret123")
    AdminPublish(root, user=root.current_user, db_callbacks=callbacks)


def show_admin_under_review(root, user=None):
    from admin.admin_under_review import AdminUnderReview
 
    clear_root(root)
    user_id   = _admin_user_id(root)
    callbacks = build_admin_callbacks(user_id)
    callbacks["flask_url"] = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
    AdminUnderReview(root, user=root.current_user, db_callbacks=callbacks)


def show_admin_needs_revision(root, user=None):
    from admin.admin_needs_revision import AdminNeedsRevision
 
    clear_root(root)
    user_id   = _admin_user_id(root)
    callbacks = build_admin_callbacks(user_id)
    callbacks["flask_url"] = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
    AdminNeedsRevision(root, user=root.current_user, db_callbacks=callbacks)


def show_admin_published(root, user=None):
    from admin.admin_published import AdminPublished
 
    clear_root(root)
    user_id   = _admin_user_id(root)
    callbacks = build_admin_callbacks(user_id)
    callbacks["flask_url"] = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
    AdminPublished(root, user=root.current_user, db_callbacks=callbacks)


def show_admin_manage_users(root, user=None):
    from admin.admin_manage_user import AdminManageUsers
    from services.users_db_services import build_user_callbacks

    clear_root(root)
    AdminManageUsers(
        root,
        user=root.current_user,
        db_callbacks=build_user_callbacks(),
    )


def show_admin_profile(root, user=None):
    from admin.admin_profile import AdminProfile
    from services.auth_services import update_profile, change_password

    clear_root(root)

    def delete_account(user_id):
        from db import execute_update
        try:
            execute_update(
                "UPDATE users SET status = 'deleted' WHERE id = %s",
                (user_id,)
            )
            return True
        except Exception as e:
            print(f"[delete_account] {e}")
            return False

    db_callbacks = {
        "fetch_profile": lambda uid: (
            __import__('db', fromlist=['fetch_one']).fetch_one(
                "SELECT CONCAT(first_name, ' ', last_name) AS name, "
                "email, profile_image FROM users WHERE id = %s",
                (uid,)
            ) or {}
        ),
        "update_profile":  update_profile,
        "change_password": change_password,
        "delete_account":  delete_account,
    }

    AdminProfile(root, user=root.current_user, db_callbacks=db_callbacks)


# ─────────────────────────────────────────────────────────────
# NAVIGATION SETUP
# ─────────────────────────────────────────────────────────────

def setup_navigation(root):
    root.current_user = None

    # ── User / reader ─────────────────────────────────────────
    root.show_user_homepage = lambda user=None, **kw: show_articles(
        root, user or root.current_user
    )
    root.show_landing = lambda: show_landing(root)

    root.show_articles = lambda user=None: show_articles(root, user)

    root.show_view_all_article = lambda: show_view_all_article(root)

    root.show_article_detail = lambda article_id, user=None, from_landing=False: (
        show_article_detail(root, article_id, user, from_landing)
    )

    root.show_user_profile = lambda user=None: show_user_profile(
        root, user or root.current_user
    )

    # ── Superadmin ────────────────────────────────────────────
    root.show_superadmin = lambda user=None: show_superadmin(
        root, user or root.current_user
    )

    root.show_manage_admins = lambda user=None: show_manage_admins(
        root, user or root.current_user
    )

    root.show_manage_users = lambda user=None: show_manage_users(
        root, user or root.current_user
    )

    root.show_pending_articles = lambda user=None: show_pending_articles(
        root, user or root.current_user
    )

    root.show_categories = lambda user=None: show_categories(
        root, user or root.current_user
    )

    root.show_activity_logs = lambda user=None: show_activity_logs(
        root, user or root.current_user
    )

    # ── Admin ─────────────────────────────────────────────────
    root.show_admin = lambda user=None: show_admin(
        root, user or root.current_user
    )

    root.show_admin_drafts = lambda user=None: show_admin_drafts(
        root, user or root.current_user
    )

    root.show_admin_publish = lambda user=None: show_admin_publish(
        root, user or root.current_user
    )

    root.show_admin_under_review = lambda user=None: show_admin_under_review(
        root, user or root.current_user
    )

    root.show_admin_needs_revision = lambda user=None: show_admin_needs_revision(
        root, user or root.current_user
    )

    root.show_admin_manage_users = lambda user=None: show_admin_manage_users(
        root, user or root.current_user
    )

    root.show_admin_profile = lambda user=None: show_admin_profile(
        root, user or root.current_user
    )

    # aliases
    root.show_under_review    = root.show_admin_under_review
    root.show_needs_revision  = root.show_admin_needs_revision

    root.show_admin_published = lambda user=None: show_admin_published(
        root, user or root.current_user
    )


def show_user_profile(root, user=None):
    from user.user_profile import UserProfilePage
    from services.auth_services import update_profile, change_password

    # I-update ang current_user kung may naipasa
    if user:
        root.current_user = user

    clear_root(root)

    def delete_account(user_id):
        from db import execute_update
        try:
            execute_update(
                "UPDATE users SET status = 'deleted' WHERE id = %s",
                (user_id,)
            )
            return True
        except Exception as e:
            print(f"[delete_account] {e}")
            return False

    db_callbacks = {
        "update_profile":  lambda uid, name, email, avatar=None:
            update_profile(uid, name, "", email, avatar),
        "change_password": change_password,
        "delete_account":  delete_account,
    }

    UserProfilePage(
        root,
        user=root.current_user,  # palaging galing sa root
        db_callbacks=db_callbacks
    )

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    # ── FIX: ensure_schema() removed — Supabase schema already exists.
    # Only run the safe PostgreSQL-compatible helpers.
    try:
        ensure_categories_schema()
    except Exception as exc:
        print(f"[main] categories schema warning: {exc}")

    try:
        ensure_activity_logs_schema()
    except Exception as exc:
        print(f"[main] activity logs schema warning: {exc}")

    root = tk.Tk()
    root.title("The Gears")
    root.geometry("1280x800")
    root.minsize(900, 600)
    root.configure(bg=COLORS["background"])

    setup_navigation(root)

    from services.article_service import seed_default_categories
    seed_default_categories() 

    show_landing(root) 

    root.mainloop()


if __name__ == "__main__":
    main()