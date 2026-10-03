# utils/admin_navigation_helper.py


def _clear(root):
    """
    Unbind root-level events that pages attach, then destroy all widgets.

    Why this matters
    ────────────────
    Pages like AdminDashboard bind "<Configure>" and "<Button-1>" directly
    to `root`.  Those bindings survive widget destruction, so after navigation
    the OLD page's handler keeps firing and fights with the NEW page's geometry.
    We unbind the known tags before clearing widgets.
    """
    for seq in ("<Configure>", "<Button-1>", "<MouseWheel>"):
        try:
            root.unbind(seq)
        except Exception:
            pass

    for w in root.winfo_children():
        try:
            w.destroy()
        except Exception:
            pass


def _load_page(root, page_class, user, **kwargs):
    """Reusable page loader."""
    _clear(root)
    page_class(root, user=user, **kwargs)


# =====================================================
# DASHBOARD
# =====================================================
def load_admin_dashboard(root, user):
    from admin.admin_dashboard import AdminDashboard
    from services.admin_db_service import build_dashboard_callbacks

    _load_page(
        root,
        AdminDashboard,
        user,
        db_callbacks=build_dashboard_callbacks()
    )


# =====================================================
# DRAFTS
# =====================================================
def load_admin_drafts(root, user):
    from admin.admin_drafts import AdminDrafts
    from services.admin_db_service import build_admin_callbacks

    _load_page(
        root,
        AdminDrafts,
        user,
        db_callbacks=build_admin_callbacks(user[3])
    )


# =====================================================
# UNDER REVIEW
# =====================================================
def load_admin_under_review(root, user):
    from admin.admin_under_review import AdminUnderReview
    from services.admin_db_service import build_admin_callbacks

    _load_page(
        root,
        AdminUnderReview,
        user,
        db_callbacks=build_admin_callbacks(user[3])
    )


# =====================================================
# NEEDS REVISION
# =====================================================
def load_admin_needs_revision(root, user):
    from admin.admin_needs_revision import AdminNeedsRevision
    from services.admin_db_service import build_admin_callbacks

    _load_page(
        root,
        AdminNeedsRevision,
        user,
        db_callbacks=build_admin_callbacks(user[3])
    )


# =====================================================
# PUBLISHED
# =====================================================
def load_admin_published(root, user):
    from admin.admin_published import AdminPublished
    from services.admin_db_service import build_admin_callbacks

    _load_page(
        root,
        AdminPublished,
        user,
        db_callbacks=build_admin_callbacks(user[3])
    )


# =====================================================
# CREATE ARTICLE
# =====================================================
def load_admin_publish(root, user):
    from admin.admin_create_article import AdminPublish
    from services.admin_db_service import build_admin_callbacks

    _load_page(
        root,
        AdminPublish,
        user,
        db_callbacks=build_admin_callbacks(user[3])
    )


# =====================================================
# MANAGE USERS
# =====================================================
# =====================================================
# MANAGE USERS
# =====================================================
def load_admin_manage_users(root, user):
    from admin.admin_manage_user import AdminManageUsers
    from services.users_db_services import build_user_callbacks
    from services.admin_db_service import build_admin_callbacks

    callbacks = {
        **build_admin_callbacks(user[3]),  # ← includes fetch_profile
        **build_user_callbacks(),          # ← includes fetch_pending_users, etc.
    }

    _load_page(
        root,
        AdminManageUsers,
        user,
        db_callbacks=callbacks
    )

# =====================================================
# PROFILE
# =====================================================
def load_admin_profile(root, user=None):
    from admin.admin_profile import AdminProfile
    from services.auth_services import update_profile, change_password
    from db import fetch_one

    _clear(root)

    def fetch_profile(uid):
        return fetch_one(
            "SELECT CONCAT(first_name, ' ', last_name) AS name, "
            "email, profile_image FROM users WHERE id = %s",
            (uid,)
        ) or {}

    def delete_account(uid):
        from db import execute_update
        try:
            execute_update(
                "UPDATE users SET status = 'deleted' WHERE id = %s", (uid,))
            return True
        except Exception as e:
            print(f"[delete_account] {e}")
            return False

    db_callbacks = {
        "fetch_profile":   fetch_profile,
        "update_profile":  update_profile,
        "change_password": change_password,
        "delete_account":  delete_account,
    }

    AdminProfile(root, user=user, db_callbacks=db_callbacks)