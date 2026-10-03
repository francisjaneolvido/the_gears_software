# utils/superadmin_navigation_helper.py

def _clear(root):
    """Clear all widgets from root frame."""
    for w in root.winfo_children():
        w.destroy()


def _load_page(root, page_class, user, **kwargs):
    """Reusable page loader."""
    _clear(root)
    page_class(root, user=user, **kwargs)


# =====================================================
# DASHBOARD
# =====================================================
def load_superadmin_dashboard(root, user):
    from superadmin.superadmin_dashboard import SuperadminDashboard
    from services.admin_db_service import (
        fetch_dashboard_stats,
        fetch_recent_articles,
        fetch_recent_users,
    )

    _load_page(
        root,
        SuperadminDashboard,
        user,
        stats=fetch_dashboard_stats(),
        recent_articles=fetch_recent_articles(),
        recent_users=fetch_recent_users(),
    )


# =====================================================
# MANAGE ADMINS
# =====================================================
def load_manage_admins(root, user):
    from superadmin.superadmin_manage_admins import ManageAdmins
    from services.admin_db_service import build_callbacks

    _load_page(
        root,
        ManageAdmins,
        user,
        db_callbacks=build_callbacks()
    )


# =====================================================
# MANAGE USERS
# =====================================================
def load_manage_users(root, user):
    from superadmin.superadmin_manage_users import ManageUsers
    from services.users_db_services import build_user_callbacks

    _load_page(
        root,
        ManageUsers,
        user,
        db_callbacks=build_user_callbacks()
    )


# =====================================================
# PENDING ARTICLES
# =====================================================
def load_pending_articles(root, user):
    from superadmin.superadmin_pending_articles import PendingArticles
    from services.admin_db_service import build_pending_callbacks

    _load_page(
        root,
        PendingArticles,
        user,
        db_callbacks=build_pending_callbacks()
    )


# =====================================================
# ACTIVITY LOGS
# =====================================================

def load_activity_logs(root, user):
    from superadmin.superadmin_activity_logs import ActivityLogs
    from services.article_service import build_activity_log_callbacks

    _load_page(
        root,
        ActivityLogs,
        user,
        db_callbacks=build_activity_log_callbacks()
    )

# =====================================================
# CATEGORIES
# =====================================================
def load_categories(root, user):
    from superadmin.superadmin_categories import SuperadminCategories
    from services.article_service import build_category_callbacks

    _load_page(
        root,
        SuperadminCategories,
        user,
        db_callbacks=build_category_callbacks()
    )

# =====================================================
# REVIEW MODAL
# =====================================================
def load_review_modal(root, user):
    from superadmin.superadmin_review_modal import ReviewModal

    _load_page(
        root,
        ReviewModal,
        user
    )