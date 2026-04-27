import tkinter as tk
from tkinter import messagebox
from dotenv import load_dotenv

from theme import COLORS
from user_page.landing_page import LandingPage
from user_page.articles_page import ArticlesPage
from user_page.article_detail_page import ArticleDetailPage


load_dotenv()


def clear_root(root):
    for widget in root.winfo_children():
        widget.destroy()


def show_landing(root):
    clear_root(root)
    LandingPage(root)


def show_articles(root, user=None):
    clear_root(root)
    ArticlesPage(root, user=user)


def show_article_detail(root, article_id, user=None):
    clear_root(root)
    ArticleDetailPage(root, article_id=article_id, user=user)


def show_superadmin(root, user=None):
    from superadmin.superadmin_dashboard import SuperadminDashboard
    clear_root(root)
    SuperadminDashboard(root, user=user)


def show_manage_admins(root, user=None):
    from superadmin.superadmin_manage_admins import ManageAdmins
    clear_root(root)
    ManageAdmins(root, user=user)


def show_admin(root, user=None):
    messagebox.showinfo(
        "Admin Dashboard",
        "Admin dashboard is not available yet.",
        parent=root,
    )


def setup_navigation(root):
    root.show_landing = lambda: show_landing(root)

    root.show_articles = lambda user=None: show_articles(root, user)

    root.show_article_detail = (
        lambda article_id, user=None: show_article_detail(root, article_id, user)
    )

    root.show_superadmin = lambda user=None: show_superadmin(root, user)

    root.show_manage_admins = lambda user=None: show_manage_admins(root, user)

    root.show_admin = lambda user=None: show_admin(root, user)


def main():
    root = tk.Tk()

    root.title("The Gears")
    root.geometry("1280x800")
    root.minsize(900, 600)
    root.configure(bg=COLORS["background"])

    setup_navigation(root)
    show_landing(root)

    root.mainloop()


if __name__ == "__main__":
    main()