"""
admin/admin_dashboard.py
─────────────────────────
Admin Dashboard for The Gears.

Inherits the full header + sidebar + scrollable shell from AdminLayout.
Only dashboard-specific content lives here (stats, charts, contributors, etc.)
"""

import tkinter as tk
from tkinter import messagebox

from admin.admin_layout import AdminLayout, FONTS


# ─────────────────────────────────────────────────────────────────────────────
class AdminDashboard(AdminLayout):

    ACTIVE_NAV = "dashboard"

    # Chart constants (dashboard-specific)
    CHART_H = 180
    BAR_GAP = 10
    PAD_L   = 48
    PAD_R   = 16
    PAD_T   = 14
    PAD_B   = 28

    def __init__(self, root, user=None, db_callbacks=None):
        # Fetch dashboard data BEFORE super().__init__() builds the UI,
        # because _build_page() (called inside super) needs them.
        self._pre_fetch(db_callbacks or {})
        super().__init__(root, user, db_callbacks)
        self._build_page()

    # ── Pre-fetch (before super().__init__) ───────────────────────────────────

    def _pre_fetch(self, callbacks: dict):
        """Fetch all dashboard data before the layout is constructed."""
        self.stats        = self._load_stats(callbacks)
        self.contributors = self._load_contributors(callbacks)
        self.trends       = self._load_trends(callbacks)

    def _load_stats(self, callbacks) -> dict:
        defaults = {
            "total_users": 0, "total_articles": 0,
            "pending_items": 0, "total_comments": 0,
            "active_users": 0, "approved_users": 0, "pending_users": 0,
        }
        if "fetch_admin_stats" in callbacks:
            try:
                defaults.update(callbacks["fetch_admin_stats"]())
            except Exception as exc:
                print(f"[AdminDashboard] fetch_admin_stats error: {exc}")
        return defaults

    def _load_contributors(self, callbacks) -> list:
        if "fetch_top_contributors" in callbacks:
            try:
                return callbacks["fetch_top_contributors"](5)
            except Exception as exc:
                print(f"[AdminDashboard] fetch_top_contributors error: {exc}")
        return []

    def _load_trends(self, callbacks) -> list:
        if "fetch_activity_trends" in callbacks:
            try:
                return callbacks["fetch_activity_trends"](8)
            except Exception as exc:
                print(f"[AdminDashboard] fetch_activity_trends error: {exc}")
        return []

    # ── Page content (called by AdminLayout after chrome is ready) ────────────

    def _build_page(self):
        """Fill self.inner with dashboard-specific sections."""
        self._section_welcome()
        self._section_stats()
        self._section_platform()
        self._section_trends()
        self._section_contributors()
        self._section_quick_actions()

    # ── Sections ──────────────────────────────────────────────────────────────

    def _section_welcome(self):
        T    = self.theme
        wrap = tk.Frame(self.inner, bg=T["background"])
        wrap.pack(fill="x", pady=(0, 20))

        first = self.user[0] if self.user else "Admin"
        tk.Label(wrap, text=f"Hi, {first} 👋",
                 bg=T["background"], fg=T["primary_orange"],
                 font=("Poppins", 22, "bold")).pack(anchor="w")
        tk.Label(wrap,
                 text="Quick overview of your content performance and tools.",
                 bg=T["background"], fg=T["text_grey"],
                 font=FONTS["body"]).pack(anchor="w", pady=(4, 0))

    def _section_stats(self):
        T    = self.theme
        wrap = tk.Frame(self.inner, bg=T["background"])
        wrap.pack(fill="x", pady=(0, 6))

        CARDS = [
            ("Total Users",    self.stats["total_users"],    "All registered accounts"),
            ("Total Articles", self.stats["total_articles"], "All posts ever created"),
            ("Pending Items",  self.stats["pending_items"],  "Awaiting approval"),
            ("Total Comments", self.stats["total_comments"], "Reader feedback"),
        ]
        for c in range(4):
            wrap.grid_columnconfigure(c, weight=1, uniform="sc")
        for i, (title, value, sub) in enumerate(CARDS):
            self._stat_card(wrap, title, value, sub, row=0, col=i)

    def _stat_card(self, parent, title, value, subtitle, row, col):
        T     = self.theme
        outer = tk.Frame(parent, bg=T["background"], padx=7, pady=7)
        outer.grid(row=row, column=col, sticky="nsew")

        card = tk.Frame(outer, bg=T["card"],
                        highlightbackground=T["border"], highlightthickness=1,
                        padx=18, pady=16)
        card.pack(fill="both", expand=True)

        tk.Frame(card, bg=T["primary_orange"], height=3).pack(fill="x", pady=(0, 10))
        tk.Label(card, text=title.upper(),
                 bg=T["card"], fg=T["primary_orange"],
                 font=FONTS["tag"]).pack(anchor="w")

        display = str(value) if value not in (None, "", "—") else "0"
        tk.Label(card, text=display,
                 bg=T["card"], fg=T["text_dark"],
                 font=("Poppins", 26, "bold")).pack(anchor="w", pady=(6, 2))
        tk.Label(card, text=subtitle,
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small"]).pack(anchor="w")

    def _section_platform(self):
        T   = self.theme
        sec = self._panel("Platform Overview")
        sec.pack(fill="x", pady=(0, 20))

        grid = tk.Frame(sec, bg=T["card"])
        grid.pack(fill="x", pady=(4, 0))
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1, uniform="pc")

        try:
            total = int(self.stats.get("total_users", 0) or 0)
        except (ValueError, TypeError):
            total = 0

        CARDS = [
            ("Active Users",   self.stats["active_users"],   "✅", "#27AE60"),
            ("Approved Users", self.stats["approved_users"], "✔",  self.theme["primary_orange"]),
            ("Pending Users",  self.stats["pending_users"],  "⏳", "#E67E22"),
        ]

        for i, (title, value, icon, accent) in enumerate(CARDS):
            outer = tk.Frame(grid, bg=T["card"], padx=6, pady=6)
            outer.grid(row=0, column=i, sticky="nsew")

            inner = tk.Frame(outer, bg=T["background_alt"],
                             highlightbackground=T["border"], highlightthickness=1,
                             padx=16, pady=14)
            inner.pack(fill="both", expand=True)

            top_row = tk.Frame(inner, bg=T["background_alt"])
            top_row.pack(fill="x")
            tk.Label(top_row, text=icon,
                     bg=T["background_alt"], fg=accent,
                     font=("Poppins", 14)).pack(side="left", padx=(0, 6))
            tk.Label(top_row, text=title.upper(),
                     bg=T["background_alt"], fg=T["text_grey"],
                     font=FONTS["tag"]).pack(side="left")

            display = str(value) if value not in (None, "", "—") else "0"
            tk.Label(inner, text=display,
                     bg=T["background_alt"], fg=T["text_dark"],
                     font=("Poppins", 26, "bold")).pack(anchor="w", pady=(8, 4))

            bar_bg = tk.Frame(inner, bg=T["border"], height=5)
            bar_bg.pack(fill="x")
            bar_bg.pack_propagate(False)

            try:
                v   = int(value) if str(value).lstrip("-").isdigit() else 0
                pct = min(v / total, 1.0) if total > 0 else 0
            except Exception:
                pct = 0

            def _draw_bar(event, _bg=bar_bg, _p=pct, _clr=accent):
                w = event.width
                if w > 4 and _p > 0:
                    fill_w = max(int(w * _p), 5)
                    tk.Frame(_bg, bg=_clr, height=5,
                             width=fill_w).place(x=0, y=0, height=5, width=fill_w)
            bar_bg.bind("<Configure>", _draw_bar)

            pct_text = f"{int(pct * 100)}% of all users" if total > 0 else "No user data"
            tk.Label(inner, text=pct_text,
                     bg=T["background_alt"], fg=T["text_light"],
                     font=FONTS["small"]).pack(anchor="w", pady=(4, 0))

    def _section_trends(self):
        T    = self.theme
        sec  = self._panel("Activity Trends")
        data = self.trends

        if not data:
            empty = tk.Frame(sec, bg=T["card"])
            empty.pack(fill="x", pady=(0, 8))
            tk.Label(empty, text="📈", bg=T["card"], fg=T["border"],
                     font=("Poppins", 36)).pack(pady=(12, 4))
            tk.Label(empty, text="No activity data yet.",
                     bg=T["card"], fg=T["text_grey"],
                     font=FONTS["body_bold"]).pack()
            tk.Label(empty,
                     text="Stats will appear once articles are submitted.",
                     bg=T["card"], fg=T["text_light"],
                     font=FONTS["small"]).pack(pady=(2, 12))
            return

        chart_frame = tk.Frame(sec, bg=T["card"])
        chart_frame.pack(fill="x", pady=(0, 4))

        cv = tk.Canvas(chart_frame, bg=T["card"],
                       height=self.CHART_H, highlightthickness=0)
        cv.pack(fill="x")

        def _draw(event=None):
            cv.delete("all")
            cw = cv.winfo_width()
            if cw < 20:
                return
            max_val  = max(v for _, v in data) or 1
            n        = len(data)
            usable_w = cw - self.PAD_L - self.PAD_R
            bar_w    = max(6, (usable_w - self.BAR_GAP * (n - 1)) // n)
            chart_h  = self.CHART_H - self.PAD_T - self.PAD_B
            baseline = self.PAD_T + chart_h

            for k in range(1, 5):
                y  = self.PAD_T + chart_h - int(chart_h * k / 4)
                lv = round(max_val * k / 4)
                cv.create_line(self.PAD_L, y, cw - self.PAD_R, y,
                               fill=T["border"], dash=(3, 5))
                cv.create_text(self.PAD_L - 6, y, text=str(lv),
                               anchor="e", fill=T["text_grey"],
                               font=("Poppins", 7))

            cv.create_line(self.PAD_L, baseline,
                           cw - self.PAD_R, baseline, fill=T["border"])

            for i, (label, val) in enumerate(data):
                x0    = self.PAD_L + i * (bar_w + self.BAR_GAP)
                x1    = x0 + bar_w
                h     = max(int(chart_h * val / max_val), 1)
                y0    = baseline - h
                mid_x = (x0 + x1) // 2

                cap_h = min(4, h)
                cv.create_rectangle(x0, y0, x1, baseline,
                                    fill=T["primary_orange_light"], outline="")
                cv.create_rectangle(x0, y0, x1, y0 + cap_h,
                                    fill=T["primary_orange"], outline="")
                cv.create_rectangle(x0, y0 + cap_h, x1, baseline,
                                    fill=T["primary_orange"], outline="")

                if h > 16:
                    cv.create_text(mid_x, y0 + 8, text=str(val),
                                   fill=T["white"], font=("Poppins", 7, "bold"))
                elif val > 0:
                    cv.create_text(mid_x, y0 - 8, text=str(val),
                                   fill=T["text_grey"], font=("Poppins", 7))

                cv.create_text(mid_x, baseline + 6, text=label,
                               anchor="n", fill=T["text_grey"],
                               font=("Poppins", 7))

        cv.bind("<Configure>", lambda e: _draw(e))
        cv.bind("<Map>",       lambda e: _draw(e))
        sec.after(80, _draw)

        leg = tk.Frame(sec, bg=T["card"])
        leg.pack(anchor="w", pady=(6, 0))
        dot = tk.Canvas(leg, width=10, height=10,
                        bg=T["card"], highlightthickness=0)
        dot.pack(side="left", padx=(0, 4))
        dot.create_oval(1, 1, 9, 9, fill=T["primary_orange"], outline="")
        tk.Label(leg, text="Articles submitted per week",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small"]).pack(side="left")

    def _section_contributors(self):
        T   = self.theme
        sec = self._panel("Top Contributors")

        if not self.contributors:
            tk.Label(sec, text="No contributor data available yet.",
                     bg=T["card"], fg=T["text_light"],
                     font=FONTS["small"]).pack(anchor="w")
            return

        max_count = max(c for _, c in self.contributors) or 1
        MEDAL     = ["🥇", "🥈", "🥉"]

        for i, (name, count) in enumerate(self.contributors):
            row = tk.Frame(sec, bg=T["card"])
            row.pack(fill="x", pady=(4, 0))

            badge = MEDAL[i] if i < 3 else f"#{i+1}"
            tk.Label(row, text=badge, bg=T["card"], fg=T["text_dark"],
                     font=("Poppins", 14)).pack(side="left", padx=(0, 12))

            info = tk.Frame(row, bg=T["card"])
            info.pack(side="left", fill="x", expand=True)

            name_row = tk.Frame(info, bg=T["card"])
            name_row.pack(fill="x")
            tk.Label(name_row, text=name, bg=T["card"], fg=T["text_dark"],
                     font=FONTS["body_bold"]).pack(side="left")
            tk.Label(name_row,
                     text=f"  —  {count} article{'s' if count != 1 else ''}",
                     bg=T["card"], fg=T["text_grey"],
                     font=FONTS["body"]).pack(side="left")

            bar_bg = tk.Frame(info, bg=T["border"], height=4)
            bar_bg.pack(fill="x", pady=(4, 0))
            bar_bg.pack_propagate(False)

            pct = count / max_count

            def _draw_bar(event, _bg=bar_bg, _p=pct):
                w = event.width
                if w > 4:
                    fill_w = max(int(w * _p), 4)
                    tk.Frame(_bg, bg=T["primary_orange"],
                             height=4, width=fill_w).place(
                                 x=0, y=0, height=4, width=fill_w)
            bar_bg.bind("<Configure>", _draw_bar)

            if i < len(self.contributors) - 1:
                tk.Frame(sec, bg=T["border"], height=1).pack(fill="x", pady=(6, 0))

    def _section_quick_actions(self):
        T   = self.theme
        sec = self._panel("Quick Actions")

        ACTIONS = [
            ("✏️  New Article",    self._go_add_article),
            ("📂  View Drafts",    self._go_drafts),
            ("📤  Under Review",   self._go_under_review),
            ("🛠  Needs Revision", self._go_needs_revision),
            ("📚  Published",      self._go_published),
            ("👥  Manage Users",   self._go_manage_users),
            ("💬  Comments",       self._go_comments),
        ]

        btn_frame = tk.Frame(sec, bg=T["card"])
        btn_frame.pack(fill="x", pady=(4, 0))

        for idx, (label, cmd) in enumerate(ACTIONS):
            col = idx % 4
            row = idx // 4
            btn_frame.grid_columnconfigure(col, weight=1, uniform="qa")
            btn = tk.Button(btn_frame, text=label, command=cmd,
                            bg=T["primary_orange_light"], fg=T["primary_orange"],
                            activebackground=T["primary_orange"],
                            activeforeground=T["white"],
                            font=("Poppins", 9, "bold"),
                            bd=0, relief="flat", padx=12, pady=10, cursor="hand2")
            btn.grid(row=row, column=col, padx=(0, 8), pady=4, sticky="ew")

    # ── Comments stub ─────────────────────────────────────────────────────────

    def _go_comments(self):
        messagebox.showinfo("Comments", "Comments module coming soon.")


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("The Gears — Admin Dashboard")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    SAMPLE_TRENDS = [
        ("Apr 14", 3), ("Apr 21", 7), ("Apr 28", 5),
        ("May 05", 9), ("May 12", 4), ("May 19", 11),
        ("May 26", 6), ("Jun 02", 8),
    ]

    AdminDashboard(
        root,
        user=("Maria", "Santos", "maria@gears.com", 1, "admin"),
        db_callbacks={
            "fetch_admin_stats": lambda: {
                "total_users": 142, "total_articles": 38,
                "pending_items": 5,  "total_comments": 217,
                "active_users": 130, "approved_users": 130, "pending_users": 12,
            },
            "fetch_top_contributors": lambda limit: [
                ("Maria Santos", 14), ("Juan dela Cruz", 9),
                ("Ana Reyes", 7), ("Ben Aquino", 4), ("Carla Gomez", 2),
            ][:limit],
            "fetch_activity_trends": lambda weeks: SAMPLE_TRENDS[-weeks:],
        },
    )
    root.mainloop()