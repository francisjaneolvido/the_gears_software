"""
superadmin/superadmin_dashboard.py
────────────────────────────────────
Superadmin Dashboard — inherits full chrome from SuperadminLayout.

Accepts optional `stats`, `recent_articles`, and `recent_users` keyword
arguments injected by main.py from the DB.  Falls back to empty/zero values
if not provided (no crashes on first run or DB hiccups).
"""

import tkinter as tk
from tkinter import messagebox
from theme import COLORS, FONTS
from superadmin.superadmin_layout import SuperadminLayout


class SuperadminDashboard(SuperadminLayout):

    ACTIVE_NAV = "dashboard"

    def __init__(self, root, user=None,
                 stats=None, recent_articles=None, recent_users=None,
                 db_callbacks=None):
        self.root.title("The Gears — Superadmin") if hasattr(self, "root") else None

        # ── Live data — fall back to safe defaults ────────────────────────────
        self.stats = stats or {
            "Total Admins":    "—",
            "Total Users":     "—",
            "Total Articles":  "—",
            "Pending Reviews": "—",
            "Pending Users":   "—",
        }
        self.recent_articles = recent_articles or []
        self.recent_users    = recent_users    or []

        # ── Base class builds all chrome; calls _build_page() ─────────────────
        super().__init__(root, user, db_callbacks)

        root.title("The Gears — Superadmin")
        root.geometry("1280x800")
        root.minsize(1050, 680)

        self._build_page()

    # =========================================================================
    # Page hook
    # =========================================================================

    def _build_page(self):
        self._section_header()
        self._section_metrics()
        self._section_quick_actions()
        self._section_activity()

    # =========================================================================
    # Page sections
    # =========================================================================

    def _section_header(self):
        T    = self.theme
        wrap = tk.Frame(self.inner, bg=T["background"])
        wrap.pack(fill="x", pady=(0, 22))

        name = (f"{self.user[0]} {self.user[1]}"
                if self.user and len(self.user) >= 2 else "Superadmin")

        tk.Label(
            wrap, text="OVERVIEW",
            bg=T["background"], fg=T["primary_orange"],
            font=("Poppins", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            wrap,
            text=f"Welcome back, {name}. Here's your platform snapshot.",
            bg=T["background"], fg=T["text_grey"],
            font=FONTS["body"],
        ).pack(anchor="w", pady=(4, 0))

    def _section_metrics(self):
        T = self.theme
        self.cards_frame = tk.Frame(self.inner, bg=T["background"])
        self.cards_frame.pack(fill="x")

        COLS = 3
        for c in range(COLS):
            self.cards_frame.grid_columnconfigure(c, weight=1, uniform="mc")

        for i, (title, value) in enumerate(self.stats.items()):
            self._metric_card(
                self.cards_frame, title, value,
                self._card_subtitle(title), self._card_chip(title),
                row=i // COLS, col=i % COLS,
            )

    def _metric_card(self, parent, title, value, subtitle, chip, row, col):
        T     = self.theme
        outer = tk.Frame(parent, bg=T["background"], padx=7, pady=7)
        outer.grid(row=row, column=col, sticky="nsew")

        card = tk.Frame(
            outer, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
            padx=20, pady=16,
        )
        card.pack(fill="both", expand=True)

        tk.Frame(card, bg=T["primary_orange"], height=3).pack(
            fill="x", pady=(0, 12))

        top = tk.Frame(card, bg=T["card"])
        top.pack(fill="x")
        tk.Label(
            top, text=title.upper(),
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["small_bold"],
        ).pack(side="left")
        tk.Label(
            top, text=chip,
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            font=FONTS["tag"], padx=8, pady=3,
        ).pack(side="right")

        tk.Label(
            card, text=value,
            bg=T["card"], fg=T["text_dark"],
            font=("Poppins", 28, "bold"),
        ).pack(anchor="w", pady=(10, 3))
        tk.Label(
            card, text=subtitle,
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["small"], wraplength=280, justify="left",
        ).pack(anchor="w")

    def _section_quick_actions(self):
        T   = self.theme
        sec = self._section_card(
            "Quick Actions",
            "Jump straight into the most important tasks.",
        )
        grid = tk.Frame(sec, bg=T["card"])
        grid.pack(fill="x", pady=(4, 0))
        grid.grid_columnconfigure(0, weight=1, uniform="qa")
        grid.grid_columnconfigure(1, weight=1, uniform="qa")

        self._quick_card(
            grid, "📝  Review Articles",
            "Check new submissions and approve or request changes.",
            self._go_pending_articles, col=0,
        )
        self._quick_card(
            grid, "👥  Manage Users",
            "Update roles, deactivate accounts, or review new signups.",
            self._go_manage_users, col=1,
        )

    def _quick_card(self, parent, title, subtitle, command, col):
        T    = self.theme
        wrap = tk.Frame(parent, bg=T["card"], padx=7, pady=7)
        wrap.grid(row=0, column=col, sticky="nsew")

        card = tk.Frame(
            wrap, bg=T["background"],
            highlightbackground=T["border"], highlightthickness=1,
            padx=20, pady=18, cursor="hand2",
        )
        card.pack(fill="both", expand=True)

        tk.Label(
            card, text=title,
            bg=T["background"], fg=T["primary_orange"],
            font=FONTS["card_title"],
        ).pack(anchor="w")
        tk.Label(
            card, text=subtitle,
            bg=T["background"], fg=T["text_grey"],
            font=FONTS["small"], wraplength=400, justify="left",
        ).pack(anchor="w", pady=(8, 0))

        def _click(e=None): command()
        card.bind("<Button-1>", _click)
        for ch in card.winfo_children():
            ch.bind("<Button-1>", _click)

        card.bind("<Enter>",
                  lambda e: card.configure(highlightbackground=COLORS["primary_orange"]))
        card.bind("<Leave>",
                  lambda e: card.configure(highlightbackground=T["border"]))

    def _section_activity(self):
        if self.recent_articles:
            art = self._section_card(
                "Recent Articles",
                "Latest content activity across the platform.",
                link_text="View All →", link_cmd=self._go_articles,
            )
            self._activity_list(art, "A",
                [(t, f"{a}  ·  {d}") for t, a, d in self.recent_articles])

        if self.recent_users:
            usr = self._section_card(
                "Recent Users",
                "New members who recently joined The Gears.",
                link_text="View All →", link_cmd=self._go_manage_users,
            )
            self._activity_list(usr, "U",
                [(n, f"{e}  ·  Joined {d}") for n, e, d in self.recent_users])

    # ── Section card (local; different signature from _panel) ─────────────────

    def _section_card(self, title, subtitle,
                      link_text=None, link_cmd=None) -> tk.Frame:
        T   = self.theme
        sec = tk.Frame(
            self.inner, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
            padx=22, pady=18,
        )
        sec.pack(fill="x", pady=(20, 0))

        hdr = tk.Frame(sec, bg=T["card"])
        hdr.pack(fill="x", pady=(0, 12))

        lft = tk.Frame(hdr, bg=T["card"])
        lft.pack(side="left", fill="x", expand=True)
        tk.Label(
            lft, text=title.upper(),
            bg=T["card"], fg=T["primary_orange"],
            font=FONTS["section"],
        ).pack(anchor="w")
        tk.Label(
            lft, text=subtitle,
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["small"],
        ).pack(anchor="w", pady=(2, 0))

        if link_text:
            tk.Button(
                hdr, text=link_text, command=link_cmd,
                bg=T["card"], fg=T["primary_orange"],
                activebackground=T["primary_orange_light"],
                activeforeground=T["primary_orange_dark"],
                font=FONTS["button"],
                bd=0, relief="flat", cursor="hand2",
            ).pack(side="right")

        return sec

    def _activity_list(self, parent, icon_letter, items):
        T  = self.theme
        lf = tk.Frame(parent, bg=T["card"])
        lf.pack(fill="x")

        for i, (title, sub) in enumerate(items):
            row = tk.Frame(lf, bg=T["card"])
            row.pack(fill="x", pady=5)

            badge = tk.Canvas(row, width=38, height=38,
                              bg=T["card"], highlightthickness=0)
            badge.pack(side="left", padx=(0, 14))
            badge.create_oval(1, 1, 37, 37,
                              fill=T["primary_orange_light"], outline="")
            badge.create_text(19, 19, text=icon_letter,
                              fill=T["primary_orange"],
                              font=("Poppins", 9, "bold"))

            info = tk.Frame(row, bg=T["card"])
            info.pack(side="left", fill="x", expand=True)
            tk.Label(
                info, text=title,
                bg=T["card"], fg=T["text_dark"],
                font=FONTS["body_bold"], anchor="w",
            ).pack(fill="x")
            tk.Label(
                info, text=sub,
                bg=T["card"], fg=T["text_grey"],
                font=FONTS["small"], anchor="w",
            ).pack(fill="x", pady=(2, 0))

            if i < len(items) - 1:
                tk.Frame(lf, bg=T["border"], height=1).pack(
                    fill="x", pady=(4, 0))

    # =========================================================================
    # Navigation aliases  (show_* kept for backward compat with main.py)
    # =========================================================================

    def show_manage_admins(self):    self._go_manage_admins()
    def show_manage_users(self):     self._go_manage_users()
    def show_pending_articles(self): self._go_pending_articles()
    def show_categories(self):       self._go_categories()
    def show_activity_logs(self):    self._go_activity_logs()

    def show_articles(self):
        self._unbind_all()
        from utils.superadmin_navigation_helper import load_published_articles
        load_published_articles(self.root, self.user)

    def _go_articles(self):
        self.show_articles()

    # =========================================================================
    # Data helpers
    # =========================================================================

    def _card_subtitle(self, title):
        return {
            "Total Admins":    "Superadmins and content admins combined.",
            "Total Users":     "Registered readers and contributors.",
            "Total Articles":  "Published, scheduled, and draft content.",
            "Pending Reviews": "Articles waiting for admin approval.",
            "Pending Users":   "New users awaiting verification.",
        }.get(title, "")

    def _card_chip(self, title):
        return {
            "Total Admins":    "All roles",
            "Total Users":     "Platform",
            "Total Articles":  "All statuses",
            "Pending Reviews": "⚠ Attention",
            "Pending Users":   "⚠ Review",
        }.get(title, "Metric")


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    from services.admin_db_service import (
        ensure_schema, fetch_dashboard_stats,
        fetch_recent_articles, fetch_recent_users,
    )
    ensure_schema()
    root = tk.Tk()
    SuperadminDashboard(
        root,
        user=("Francis Jane", "Olvido", "admin@gears.com", 1, "superadmin", True),
        stats=fetch_dashboard_stats(),
        recent_articles=fetch_recent_articles(),
        recent_users=fetch_recent_users(),
    )
    root.mainloop()