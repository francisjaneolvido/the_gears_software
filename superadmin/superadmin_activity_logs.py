"""
superadmin/superadmin_activity_logs.py
───────────────────────────────────────
Activity Logs page for The Gears Superadmin.

Inherits the full header + sidebar + scrollable shell from SuperadminLayout,
so this module only contains page-specific content.

db_callbacks keys
─────────────────
  fetch_admin_logs()   → list[dict]
  fetch_reader_logs()  → list[dict]
  fetch_profile(user_id) → dict (optional, for avatar)
"""

import csv
import os
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

try:
    from superadmin.superadmin_layout import SuperadminLayout
    from theme import COLORS, FONTS
except ImportError:
    from superadmin_layout import SuperadminLayout
    COLORS = {
        "primary_orange":       "#F5821F",
        "primary_orange_dark":  "#D97E10",
        "primary_orange_light": "#FFF1DF",
        "primary_red":          "#B02029",
        "background":           "#F8F6F3",
        "background_alt":       "#F0EDE8",
        "card":                 "#FFFFFF",
        "white":                "#FFFFFF",
        "text_dark":            "#1A1A1A",
        "text_mid":             "#444444",
        "text_grey":            "#717171",
        "text_light":           "#9E9E9E",
        "border":               "#E5E0D8",
        "navy":                 "#0C1633",
        "success":              "#15803D",
        "input_bg":             "#F5F3F0",
        "tab_active":           "#F5821F",
        "tab_inactive_fg":      "#777777",
    }
    FONTS = {
        "heading":    ("Poppins", 20, "bold"),
        "section":    ("Poppins", 16, "bold"),
        "card_title": ("Poppins", 13, "bold"),
        "body":       ("Poppins", 11),
        "body_bold":  ("Poppins", 11, "bold"),
        "small":      ("Poppins", 9),
        "small_bold": ("Poppins", 9, "bold"),
        "button":     ("Poppins", 10, "bold"),
        "tag":        ("Poppins", 8, "bold"),
        "input":      ("Poppins", 11),
        "modal_title":("Poppins", 18, "bold"),
    }

PAGE_SIZE = 10

SRCH_PH = "Search username, action, category…"
DATE_PH = "YYYY-MM-DD"

ACTION_COLORS = {
    "Saved as Draft":    ("#6B7280", "#E5E7EB"),
    "Submitted":         ("#166534", "#DCFCE7"),
    "Edited an Article": ("#1E40AF", "#DBEAFE"),
    "Accepted a User":   ("#166534", "#DCFCE7"),
    "Rejected a User":   ("#991B1B", "#FEE2E2"),
    "Deleted a Comment": ("#991B1B", "#FEE2E2"),
    "Commented":         ("#5B21B6", "#EDE9FE"),
    "Viewed":            ("#6B7280", "#E5E7EB"),
    "Logged In":         ("#1E40AF", "#DBEAFE"),
    "Registered":        ("#166534", "#DCFCE7"),
}

ADMIN_ACTIONS  = [
    "Saved as Draft", "Submitted", "Edited an Article",
    "Accepted a User", "Rejected a User",
    "Deleted a Comment", "Commented", "Logged In",
]
READER_ACTIONS = ["Viewed", "Commented", "Logged In", "Registered"]


# ══════════════════════════════════════════════════════════════════════════════
class ActivityLogs(SuperadminLayout):
    """
    Superadmin page: Activity Logs.

    Inherits chrome from SuperadminLayout; only builds page-specific
    content inside self.inner.
    """

    ACTIVE_NAV = "activity_logs"

    def __init__(self, root, user=None, db_callbacks=None):
        # Data state — initialised before super().__init__ calls _build_page
        self._admin_data:  list = []
        self._reader_data: list = []
        self._filtered_admin:  list = []
        self._filtered_reader: list = []
        self._role_tab = "all"
        self._sort = {
            "admin":  {"key": None, "asc": True},
            "reader": {"key": None, "asc": True},
        }
        self._shown = {"admin": PAGE_SIZE, "reader": PAGE_SIZE}

        super().__init__(root, user, db_callbacks)
        self._build_page()

    # ══════════════════════════════════════════════════════════════════════
    #  Page construction  (populates self.inner)
    # ══════════════════════════════════════════════════════════════════════

    def _build_page(self):
        """Called by __init__ and again by _rebuild_chrome on theme toggle."""
        # Reset filter/sort/pagination state on rebuild
        self._role_tab = "all"
        self._sort     = {
            "admin":  {"key": None, "asc": True},
            "reader": {"key": None, "asc": True},
        }
        self._shown = {"admin": PAGE_SIZE, "reader": PAGE_SIZE}

        self._build_page_header()
        self._build_filter_bar()
        self._build_admin_section()
        self._build_reader_section()
        self._load_data()

    # ── Page header ───────────────────────────────────────────────────────────

    def _build_page_header(self):
        T    = self.theme
        wrap = tk.Frame(self.inner, bg=T["background"])
        wrap.pack(fill="x", pady=(0, 16))

        tk.Label(wrap, text="ACTIVITY LOGS",
                 bg=T["background"], fg=T["primary_orange"],
                 font=("Poppins", 22, "bold")).pack(anchor="w")
        tk.Label(wrap,
                 text="System-wide actions by admins and readers. "
                      "Use filters to drill down.",
                 bg=T["background"], fg=T["text_grey"],
                 font=FONTS["body"]).pack(anchor="w", pady=(4, 0))

    # ── Filter bar ────────────────────────────────────────────────────────────

    def _build_filter_bar(self):
        T    = self.theme
        card = tk.Frame(self.inner, bg=T["card"],
                        highlightbackground=T["border"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 14))

        tk.Frame(card, bg=T["primary_orange"], height=3).pack(fill="x")

        bar = tk.Frame(card, bg=T["card"])
        bar.pack(fill="x", padx=18, pady=14)

        # Role tabs
        tab_row = tk.Frame(bar, bg=T["card"])
        tab_row.pack(fill="x", pady=(0, 12))

        self._tab_btns: dict[str, tk.Button] = {}
        for key, label in [("all",    "All Roles"),
                            ("admin",  "Admin Only"),
                            ("reader", "Readers Only")]:
            btn = tk.Button(tab_row, text=label,
                            font=FONTS["button"],
                            relief="flat", bd=0, cursor="hand2",
                            padx=14, pady=6,
                            command=lambda k=key: self._on_role_tab(k))
            btn.pack(side="left", padx=(0, 6))
            self._tab_btns[key] = btn
        self._refresh_tab_styles()

        # Filter controls row
        fr = tk.Frame(bar, bg=T["card"])
        fr.pack(fill="x")

        tk.Label(fr, text="Action:", bg=T["card"], fg=T["text_grey"],
                 font=FONTS["tag"]).pack(side="left", padx=(0, 4))

        self._action_var = tk.StringVar(value="All Actions")
        all_actions = (["All Actions"] + ADMIN_ACTIONS
                       + [a for a in READER_ACTIONS if a not in ADMIN_ACTIONS])
        self._action_om = tk.OptionMenu(
            fr, self._action_var, *all_actions,
            command=lambda _: self._on_filter_change())
        self._action_om.configure(
            font=FONTS["small"], bg=T["input_bg"],
            fg=T["text_dark"], relief="flat",
            highlightthickness=0, bd=0,
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"])
        self._action_om["menu"].configure(font=FONTS["small"])
        self._action_om.pack(side="left", padx=(0, 16))

        tk.Label(fr, text="From:", bg=T["card"], fg=T["text_grey"],
                 font=FONTS["tag"]).pack(side="left", padx=(0, 4))
        self._date_from = tk.Entry(
            fr, width=11, font=FONTS["small"],
            bg=T["input_bg"], fg=T["text_light"],
            relief="flat", bd=0,
            highlightbackground=T["border"], highlightthickness=1)
        self._date_from.pack(side="left", ipady=5, padx=(0, 8))
        self._date_from.insert(0, DATE_PH)
        self._add_placeholder(self._date_from, DATE_PH)

        tk.Label(fr, text="To:", bg=T["card"], fg=T["text_grey"],
                 font=FONTS["tag"]).pack(side="left", padx=(0, 4))
        self._date_to = tk.Entry(
            fr, width=11, font=FONTS["small"],
            bg=T["input_bg"], fg=T["text_light"],
            relief="flat", bd=0,
            highlightbackground=T["border"], highlightthickness=1)
        self._date_to.pack(side="left", ipady=5, padx=(0, 16))
        self._date_to.insert(0, DATE_PH)
        self._add_placeholder(self._date_to, DATE_PH)

        tk.Label(fr, text="Search:", bg=T["card"], fg=T["text_grey"],
                 font=FONTS["tag"]).pack(side="left", padx=(0, 4))
        self._search_var = tk.StringVar()
        se = tk.Entry(fr, textvariable=self._search_var,
                      font=FONTS["small"], bg=T["input_bg"],
                      fg=T["text_dark"], relief="flat", bd=0,
                      highlightbackground=T["border"], highlightthickness=1)
        se.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 16))
        self._search_entry = se
        se.insert(0, SRCH_PH)
        se.configure(fg=T["text_light"])
        self._add_placeholder(se, SRCH_PH)
        self._search_var.trace_add("write", lambda *_: self._on_filter_change())

        bf = tk.Frame(fr, bg=T["card"])
        bf.pack(side="left")

        self._flat_btn(bf, "↺  Reset", self._reset_filters,
                       T["background_alt"], T["text_grey"],
                       T["primary_orange_light"], T["primary_orange"]
                       ).pack(side="left", padx=(0, 6))
        self._flat_btn(bf, "⬇  Export CSV", self._export_csv,
                       T["primary_orange_light"], T["primary_orange"],
                       T["primary_orange"], T["white"]
                       ).pack(side="left")

    def _add_placeholder(self, entry, placeholder):
        T = self.theme

        def _fi(e):
            if entry.get().strip() == placeholder:
                entry.delete(0, "end")
                entry.configure(fg=T["text_dark"])
            self._on_filter_change()

        def _fo(e):
            if not entry.get().strip():
                entry.insert(0, placeholder)
                entry.configure(fg=T["text_light"])
            self._on_filter_change()

        entry.bind("<FocusIn>",  _fi)
        entry.bind("<FocusOut>", _fo)
        entry.bind("<Return>",   lambda e: self._on_filter_change())

    @staticmethod
    def _flat_btn(parent, text, command, bg, fg, hover_bg, hover_fg,
                  padx=12, pady=6):
        btn = tk.Button(parent, text=text, command=command,
                        bg=bg, fg=fg,
                        activebackground=hover_bg, activeforeground=hover_fg,
                        font=FONTS["button"], bd=0, relief="flat",
                        cursor="hand2", padx=padx, pady=pady)
        btn.bind("<Enter>", lambda _: btn.config(bg=hover_bg, fg=hover_fg))
        btn.bind("<Leave>", lambda _: btn.config(bg=bg,       fg=fg))
        return btn

    # ── Admin section ─────────────────────────────────────────────────────────

    def _build_admin_section(self):
        T = self.theme
        self._admin_section = tk.Frame(
            self.inner, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1)
        self._admin_section.pack(fill="x", pady=(0, 14))

        tk.Frame(self._admin_section, bg=T["primary_orange"],
                 height=3).pack(fill="x")

        hdr = tk.Frame(self._admin_section, bg=T["card"])
        hdr.pack(fill="x", padx=18, pady=(14, 6))

        left_h = tk.Frame(hdr, bg=T["card"])
        left_h.pack(side="left")
        tk.Label(left_h, text="ADMIN ACTIVITY",
                 bg=T["card"], fg=T["primary_orange"],
                 font=FONTS["section"]).pack(anchor="w")
        tk.Label(left_h, text="Actions taken by admin accounts.",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small"]).pack(anchor="w")

        self._admin_totals = tk.Label(
            hdr, text="", bg=T["card"], fg=T["text_grey"],
            font=FONTS["small"])
        self._admin_totals.pack(side="right")

        self._admin_tree = self._make_tree(
            self._admin_section,
            cols=("date", "user", "role", "action", "description"),
            headings=("Date & Time", "User", "Role", "Action", "Description / Article"),
            widths=(145, 160, 75, 155, 0),
            table="admin",
        )

        self._admin_more = self._flat_btn(
            self._admin_section, "Show more ↓",
            lambda: self._load_more("admin"),
            T["primary_orange"], T["white"],
            T["primary_orange_dark"], T["white"])
        self._admin_more.pack(pady=(6, 14))

    # ── Reader section ────────────────────────────────────────────────────────

    def _build_reader_section(self):
        T = self.theme
        self._reader_section = tk.Frame(
            self.inner, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1)
        self._reader_section.pack(fill="x")

        tk.Frame(self._reader_section, bg=T["primary_orange"],
                 height=3).pack(fill="x")

        hdr = tk.Frame(self._reader_section, bg=T["card"])
        hdr.pack(fill="x", padx=18, pady=(14, 6))

        left_h = tk.Frame(hdr, bg=T["card"])
        left_h.pack(side="left")
        tk.Label(left_h, text="READER ACTIVITY",
                 bg=T["card"], fg=T["primary_orange"],
                 font=FONTS["section"]).pack(anchor="w")
        tk.Label(left_h, text="Engagement from reader accounts.",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small"]).pack(anchor="w")

        self._reader_totals = tk.Label(
            hdr, text="", bg=T["card"], fg=T["text_grey"],
            font=FONTS["small"])
        self._reader_totals.pack(side="right")

        self._reader_tree = self._make_tree(
            self._reader_section,
            cols=("date", "user", "role", "action", "content"),
            headings=("Date & Time", "User", "Role", "Action", "Content / Article"),
            widths=(145, 160, 75, 120, 0),
            table="reader",
        )

        self._reader_more = self._flat_btn(
            self._reader_section, "Show more ↓",
            lambda: self._load_more("reader"),
            T["primary_orange"], T["white"],
            T["primary_orange_dark"], T["white"])
        self._reader_more.pack(pady=(6, 14))

    # ── Treeview factory ──────────────────────────────────────────────────────

    def _make_tree(self, parent, cols, headings, widths, table):
        T     = self.theme
        frame = tk.Frame(parent, bg=T["card"])
        frame.pack(fill="x", padx=18, pady=(0, 4))

        sn = f"{table}.AL.Treeview"
        style = ttk.Style()
        style.configure(sn,
                        font=FONTS["small"], rowheight=32,
                        background=T["card"], fieldbackground=T["card"],
                        foreground=T["text_dark"])
        style.configure(f"{sn}.Heading",
                        font=FONTS["small_bold"],
                        background="#FFEDD5", foreground=T["text_mid"],
                        relief="flat")
        style.map(sn,
                  background=[("selected", T["primary_orange_light"])],
                  foreground=[("selected", T["text_dark"])])

        vsb  = ttk.Scrollbar(frame, orient="vertical")
        tree = ttk.Treeview(frame, columns=cols, show="headings",
                            selectmode="browse", style=sn,
                            yscrollcommand=vsb.set, height=8)
        vsb.configure(command=tree.yview)

        for col, heading, width in zip(cols, headings, widths):
            stretch = (width == 0)
            tree.heading(col, text=heading,
                         command=lambda c=col, t=table: self._on_sort(t, c))
            tree.column(col,
                        width=width if width else 200,
                        minwidth=60, stretch=stretch)

        tree.tag_configure("even", background="#FFF9F3")
        tree.tag_configure("odd",  background=T["card"])
        tree.tag_configure("empty", foreground=T["text_light"])

        vsb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        tree.bind("<Double-1>", lambda e, t=table: self._on_row_click(t))
        tree.bind("<Return>",   lambda e, t=table: self._on_row_click(t))

        return tree

    # ══════════════════════════════════════════════════════════════════════
    #  Data
    # ══════════════════════════════════════════════════════════════════════

    def _load_data(self):
        cb_a = self.callbacks.get("fetch_admin_logs")
        cb_r = self.callbacks.get("fetch_reader_logs")

        try:
            self._admin_data = cb_a() if cb_a else []
        except Exception as e:
            print(f"[ActivityLogs] fetch_admin_logs error: {e}")
            self._admin_data = []

        try:
            self._reader_data = cb_r() if cb_r else []
        except Exception as e:
            print(f"[ActivityLogs] fetch_reader_logs error: {e}")
            self._reader_data = []

        self._apply_filters()

    # ══════════════════════════════════════════════════════════════════════
    #  Filter logic
    # ══════════════════════════════════════════════════════════════════════

    def _on_role_tab(self, key):
        self._role_tab = key
        self._shown    = {"admin": PAGE_SIZE, "reader": PAGE_SIZE}
        self._refresh_tab_styles()
        self._update_action_options()
        self._apply_filters()

    def _refresh_tab_styles(self):
        T = self.theme
        for key, btn in self._tab_btns.items():
            if key == self._role_tab:
                btn.config(bg=T["primary_orange"], fg=T["white"])
            else:
                btn.config(bg=T["background_alt"], fg=T["text_grey"])

    def _update_action_options(self):
        role = self._role_tab
        if role == "admin":
            options = ["All Actions"] + ADMIN_ACTIONS
        elif role == "reader":
            options = ["All Actions"] + READER_ACTIONS
        else:
            options = (["All Actions"] + ADMIN_ACTIONS
                       + [a for a in READER_ACTIONS if a not in ADMIN_ACTIONS])

        menu = self._action_om["menu"]
        menu.delete(0, "end")
        for opt in options:
            menu.add_command(label=opt,
                             command=lambda v=opt: (
                                 self._action_var.set(v),
                                 self._on_filter_change()))
        if self._action_var.get() not in options:
            self._action_var.set("All Actions")

    def _on_filter_change(self):
        self._shown = {"admin": PAGE_SIZE, "reader": PAGE_SIZE}
        self._apply_filters()

    def _get_filters(self):
        raw_search = self._search_var.get().strip()
        search = "" if raw_search.lower() == SRCH_PH.lower() else raw_search.lower()

        action = self._action_var.get()
        if action == "All Actions":
            action = ""

        start = self._date_from.get().strip()
        if start == DATE_PH:
            start = ""

        end = self._date_to.get().strip()
        if end == DATE_PH:
            end = ""

        return search, action, start, end

    def _filter_rows(self, data: list, action_key: str) -> list:
        search, action, start, end = self._get_filters()
        result = []
        for r in data:
            if search:
                blob = " ".join(str(v).lower() for v in r.values())
                if search not in blob:
                    continue
            if action and r.get(action_key, "") != action:
                continue
            date_only = str(r.get("date", ""))[:10]
            if start and date_only < start:
                continue
            if end and date_only > end:
                continue
            result.append(r)
        return result

    def _apply_filters(self):
        role = self._role_tab

        # Admin table
        if role in ("all", "admin"):
            self._filtered_admin = self._sort_data(
                self._filter_rows(self._admin_data, "action"), "admin")
            total_a = len(self._filtered_admin)
            shown_a = min(self._shown["admin"], total_a)

            self._populate_tree(self._admin_tree, self._filtered_admin,
                                "admin", self._shown["admin"])
            self._admin_totals.config(
                text=(f"Showing {shown_a} of {total_a} "
                      f"(total: {len(self._admin_data)})")
                if self._admin_data else "No admin logs.")

            if total_a > self._shown["admin"]:
                self._admin_more.pack(pady=(6, 14))
            else:
                self._admin_more.pack_forget()

            self._admin_section.pack(fill="x", pady=(0, 14))
        else:
            self._admin_section.pack_forget()

        # Reader table
        if role in ("all", "reader"):
            self._filtered_reader = self._sort_data(
                self._filter_rows(self._reader_data, "action"), "reader")
            total_r = len(self._filtered_reader)
            shown_r = min(self._shown["reader"], total_r)

            self._populate_tree(self._reader_tree, self._filtered_reader,
                                "reader", self._shown["reader"])
            self._reader_totals.config(
                text=(f"Showing {shown_r} of {total_r} "
                      f"(total: {len(self._reader_data)})")
                if self._reader_data else "No reader logs.")

            if total_r > self._shown["reader"]:
                self._reader_more.pack(pady=(6, 14))
            else:
                self._reader_more.pack_forget()

            self._reader_section.pack(fill="x")
        else:
            self._reader_section.pack_forget()

    def _populate_tree(self, tree: ttk.Treeview, data: list,
                       kind: str, limit: int):
        tree.delete(*tree.get_children())
        subset = data[:limit]

        if not subset:
            tree.insert("", "end",
                        values=("—", "—", "—",
                                "No matching activity found", ""),
                        tags=("empty",))
            return

        for i, r in enumerate(subset):
            if kind == "admin":
                detail = (r.get("description") or r.get("headline")
                          or r.get("category") or "")
                vals = (
                    r.get("date",      ""),
                    r.get("user_name", ""),
                    r.get("role",      ""),
                    r.get("action",    ""),
                    (detail[:90] + "…") if len(detail) > 90 else detail,
                )
            else:
                content = (r.get("content") or r.get("headline")
                           or r.get("category") or "")
                vals = (
                    r.get("date",      ""),
                    r.get("user_name", ""),
                    r.get("role",      ""),
                    r.get("action",    ""),
                    (content[:90] + "…") if len(content) > 90 else content,
                )
            tag = "even" if i % 2 == 0 else "odd"
            tree.insert("", "end", values=vals, tags=(tag,))

    # ══════════════════════════════════════════════════════════════════════
    #  Sort
    # ══════════════════════════════════════════════════════════════════════

    def _on_sort(self, table, col):
        state = self._sort[table]
        if state["key"] == col:
            state["asc"] = not state["asc"]
        else:
            state["key"] = col
            state["asc"] = True
        self._apply_filters()

        tree = self._admin_tree if table == "admin" else self._reader_tree
        key_map = {
            "date": "Date & Time", "user": "User", "role": "Role",
            "action": "Action", "description": "Description / Article",
            "content": "Content / Article",
        }
        for c in tree["columns"]:
            base  = key_map.get(c, c.title())
            arrow = ("  ▲" if state["asc"] else "  ▼") if c == col else ""
            tree.heading(c, text=base + arrow)

    def _sort_data(self, data: list, table: str) -> list:
        state = self._sort[table]
        if not state["key"]:
            return data
        col_to_key = {
            "date": "date", "user": "user_name", "role": "role",
            "action": "action", "description": "description", "content": "content",
        }
        dk  = col_to_key.get(state["key"], state["key"])
        rev = not state["asc"]
        return sorted(data,
                      key=lambda r: str(r.get(dk) or "").lower(),
                      reverse=rev)

    # ══════════════════════════════════════════════════════════════════════
    #  Pagination
    # ══════════════════════════════════════════════════════════════════════

    def _load_more(self, table: str):
        self._shown[table] += PAGE_SIZE
        self._apply_filters()

    # ══════════════════════════════════════════════════════════════════════
    #  Row click → detail modal
    # ══════════════════════════════════════════════════════════════════════

    def _on_row_click(self, table: str):
        tree = self._admin_tree if table == "admin" else self._reader_tree
        sel  = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0], "values")
        if not vals or vals[0] == "—":
            return
        date, user, role, action = vals[0], vals[1], vals[2], vals[3]
        preview = vals[4] if len(vals) > 4 else ""
        self._show_detail_modal(action, preview, date, user, role)

    def _show_detail_modal(self, action, preview, date, user, role):
        T = self.theme

        win = tk.Toplevel(self.root)
        win.title("Activity Log Detail")
        win.configure(bg=T["background"])
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        W, H = 480, 310
        win.update_idletasks()
        rx = self.root.winfo_rootx() + self.root.winfo_width()  // 2 - W // 2
        ry = self.root.winfo_rooty() + self.root.winfo_height() // 2 - H // 2
        win.geometry(f"{W}x{H}+{rx}+{ry}")
        win.bind("<Escape>", lambda e: win.destroy())

        card = tk.Frame(win, bg=T["card"],
                        highlightbackground=T["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=14, pady=14)

        ac_fg, ac_bg = ACTION_COLORS.get(action, (T["text_grey"], T["background_alt"]))
        tk.Frame(card, bg=ac_bg, height=4).pack(fill="x")

        title_row = tk.Frame(card, bg=T["card"])
        title_row.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(title_row, text="Log Detail",
                 font=FONTS["modal_title"],
                 bg=T["card"], fg=T["primary_orange"],
                 anchor="w").pack(side="left")
        tk.Button(title_row, text="✕", command=win.destroy,
                  bg=T["card"], fg=T["text_grey"],
                  activebackground=T["background_alt"],
                  font=("Poppins", 14), bd=0, relief="flat",
                  cursor="hand2").pack(side="right")

        tk.Frame(card, bg=T["border"], height=1).pack(
            fill="x", padx=16, pady=(0, 10))

        df = tk.Frame(card, bg=T["card"])
        df.pack(fill="x", padx=16)

        for label, value in [
            ("Action",      action),
            ("Preview",     preview or "(no additional details)"),
            ("Date & Time", date),
            ("Username",    user),
            ("Role",        role),
        ]:
            row = tk.Frame(df, bg=T["card"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{label}:",
                     bg=T["card"], fg=T["text_grey"],
                     font=FONTS["small_bold"],
                     width=12, anchor="w").pack(side="left")
            if label == "Action":
                tk.Label(row, text=f" {value} ",
                         bg=ac_bg, fg=ac_fg,
                         font=FONTS["small_bold"],
                         padx=4, pady=2).pack(side="left")
            else:
                tk.Label(row, text=value,
                         bg=T["card"], fg=T["text_dark"],
                         font=FONTS["small"],
                         wraplength=300, justify="left",
                         anchor="w").pack(side="left")

        tk.Button(card, text="Close", command=win.destroy,
                  bg=T["primary_orange"], fg=T["white"],
                  activebackground=T["primary_orange_dark"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=20, pady=8, cursor="hand2"
                  ).pack(side="right", padx=16, pady=(10, 14))

    # ══════════════════════════════════════════════════════════════════════
    #  Reset & Export
    # ══════════════════════════════════════════════════════════════════════

    def _reset_filters(self):
        self._role_tab = "all"
        self._shown    = {"admin": PAGE_SIZE, "reader": PAGE_SIZE}
        self._sort     = {
            "admin":  {"key": None, "asc": True},
            "reader": {"key": None, "asc": True},
        }
        self._action_var.set("All Actions")
        self._refresh_tab_styles()
        self._update_action_options()

        T = self.theme
        for entry, ph in [(self._date_from, DATE_PH),
                          (self._date_to,   DATE_PH)]:
            entry.delete(0, "end")
            entry.insert(0, ph)
            entry.configure(fg=T["text_light"])

        self._search_var.set("")
        self._search_entry.delete(0, "end")
        self._search_entry.insert(0, SRCH_PH)
        self._search_entry.configure(fg=T["text_light"])

        self._apply_filters()

    def _export_csv(self):
        export_dir = filedialog.askdirectory(
            title="Select folder to save CSV files", parent=self.root)
        if not export_dir:
            return

        exports = [
            ("admin",  self._filtered_admin,  "admin_logs.csv"),
            ("reader", self._filtered_reader, "reader_logs.csv"),
        ]
        saved = []
        for _, data, filename in exports:
            if not data:
                continue
            path = os.path.join(export_dir, filename)
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                saved.append(filename)
            except Exception as exc:
                messagebox.showerror("Export Error",
                    f"Failed to write {filename}:\n{exc}", parent=self.root)
                return

        if saved:
            messagebox.showinfo("Exported",
                f"Saved to {export_dir}:\n" + "\n".join(saved),
                parent=self.root)
        else:
            messagebox.showinfo("Nothing to export",
                "No filtered data to export.", parent=self.root)


# ══════════════════════════════════════════════════════════════════════════════
# Standalone smoke-test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import random
    import datetime as dt

    ADMIN_ACTS  = ["Saved as Draft", "Submitted", "Edited an Article",
                   "Accepted a User", "Rejected a User",
                   "Deleted a Comment", "Commented", "Logged In"]
    READER_ACTS = ["Viewed", "Commented", "Logged In", "Registered"]
    CATS        = ["Campus News", "Opinion", "Sports", "Technology", "Arts"]
    ADMINS      = ["Juan Dela Cruz", "Maria Santos", "Rico Cruz"]
    READERS     = ["Ana Reyes", "Ben Torres", "Cara Lim", "David Yu"]
    HEADLINES   = ["Campus Paper Launches New Edition",
                   "Why Student Voices Still Matter",
                   "IT Dept Opens New Lab",
                   "Editorial Board Expands Coverage"]

    def _rdate():
        base = dt.date(2025, 1, 1)
        return (base + dt.timedelta(days=random.randint(0, 150))
                ).strftime("%Y-%m-%d %H:%M")

    def _gen_admin(n=30):
        return [{"date": _rdate(), "user_name": random.choice(ADMINS),
                 "role": "admin", "action": random.choice(ADMIN_ACTS),
                 "description": random.choice(["Fixed grammar", "Updated image", ""]),
                 "category": random.choice(CATS),
                 "headline": random.choice(HEADLINES)}
                for _ in range(n)]

    def _gen_reader(n=25):
        return [{"date": _rdate(), "user_name": random.choice(READERS),
                 "role": "user", "action": random.choice(READER_ACTS),
                 "content": random.choice(["Great article!", "Interesting.", ""]),
                 "category": random.choice(CATS),
                 "headline": random.choice(HEADLINES)}
                for _ in range(n)]

    root = tk.Tk()
    root.title("The Gears — Activity Logs")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    ActivityLogs(
        root,
        user=("Francis", "Olvido", "superadmin@gears.com", 1, "superadmin"),
        db_callbacks={
            "fetch_admin_logs":  _gen_admin,
            "fetch_reader_logs": _gen_reader,
        },
    )
    root.mainloop()