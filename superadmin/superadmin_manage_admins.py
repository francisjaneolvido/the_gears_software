import tkinter as tk
from tkinter import messagebox, simpledialog
import sys
import os

# ---------------------------------------------------------------------------
# Minimal theme fallback so the file runs standalone without the full project
# ---------------------------------------------------------------------------
try:
    from theme import COLORS, FONTS
except ImportError:
    COLORS = {
        "primary_orange": "#F19421",
        "primary_orange_dark": "#D97E10",
        "primary_orange_light": "#FFF1DF",
        "primary_red": "#B02029",
        "primary_red_dark": "#8E1A21",
        "background": "#F8F6F3",
        "background_alt": "#F0EDE8",
        "card": "#FFFFFF",
        "card_hover": "#FAFAF9",
        "white": "#FFFFFF",
        "text_dark": "#1A1A1A",
        "text_mid": "#444444",
        "text_grey": "#717171",
        "text_light": "#9E9E9E",
        "border": "#E5E0D8",
        "border_focus": "#F19421",
        "shadow": "#DED6CF",
        "success": "#2E7D32",
        "error": "#B02029",
        "input_bg": "#F5F3F0",
        "navy": "#0C1633",
    }
    FONTS = {
        "brand":       ("Hedvig Letters Serif 24pt", 24, "bold"),
        "heading":     ("Poppins", 20, "bold"),
        "section":     ("Poppins", 16, "bold"),
        "card_title":  ("Poppins", 13, "bold"),
        "body":        ("Poppins", 11),
        "body_bold":   ("Poppins", 11, "bold"),
        "small":       ("Poppins", 9),
        "small_bold":  ("Poppins", 9, "bold"),
        "button":      ("Poppins", 10, "bold"),
        "tag":         ("Poppins", 8, "bold"),
        "label":       ("Poppins", 10),
        "input":       ("Poppins", 11),
        "modal_title": ("Poppins", 18, "bold"),
        "link":        ("Poppins", 10, "underline"),
    }

# ---------------------------------------------------------------------------
# Colour constants for non-theme action buttons
# ---------------------------------------------------------------------------
GREEN       = "#2E7D32"
GREEN_DARK  = "#1B5E20"
RED_DISABLE = "#D32F2F"
RED_DARK    = "#B71C1C"
BLUE        = "#1976D2"
BLUE_DARK   = "#0D47A1"
BROWN       = "#6D4C41"
BROWN_DARK  = "#4E342E"


# ============================================================================
#  ManageAdmins — full page
# ============================================================================

class ManageAdmins:
    """
    Manage Admins page for The Gears Superadmin dashboard.

    Parameters
    ----------
    root : tk.Tk | tk.Frame
        The top-level window (must expose `.show_superadmin`, `.show_landing`,
        etc. if navigation is wired up in main.py).
    user : tuple, optional
        (first_name, last_name, email, id, role)
    db_callbacks : dict, optional
        Hook real database operations in.  Keys accepted:
            "fetch_admins"  → callable() → list[dict]
            "create_admin"  → callable(firstname, middlename, lastname, email) → str (generated pw)
            "update_admin"  → callable(admin_id, username, email)
            "disable_admin" → callable(admin_id)
            "enable_admin"  → callable(admin_id)
            "promote_admin" → callable(admin_id)
            "demote_admin"  → callable(admin_id)
        If None, demo data is used.
    """

    HEADER_H   = 68
    BAR_H      = 5
    TOP_OFFSET = HEADER_H + BAR_H
    SIDEBAR_W  = 248

    # Demo admin rows: (id, username, email, firstname, middlename, lastname, is_active, is_editorial)
    DEMO_ADMINS = [
        (1, "maria.santos",  "maria@gears.com",   "Maria",   "A.",       "Santos",    1, 0),
        (2, "john.reyes",    "john@gears.com",     "John",    "",         "Reyes",     1, 1),
        (3, "alyssa.cruz",   "alyssa@gears.com",   "Alyssa",  "B.",       "Cruz",      1, 0),
        (4, "paulo.garcia",  "paulo@gears.com",    "Paulo",   "",         "Garcia",    0, 0),
        (5, "nina.torres",   "nina@gears.com",     "Nina",    "C.",       "Torres",    1, 1),
        (6, "rex.mendoza",   "rex@gears.com",      "Rex",     "",         "Mendoza",   0, 0),
    ]

    def __init__(self, root, user=None, db_callbacks=None):
        self.root         = root
        self.user         = user
        self.callbacks    = db_callbacks or {}

        # State
        self.sidebar_visible            = False
        self.content_management_visible = False
        self.user_menu_visible          = False
        self.dark_mode                  = False

        # Themes
        self.light = COLORS.copy()
        self.dark  = {
            **COLORS,
            "background":           "#141414",
            "background_alt":       "#1A1A1A",
            "card":                 "#1E1E1E",
            "card_hover":           "#252525",
            "text_dark":            "#F0F0F0",
            "text_mid":             "#D0D0D0",
            "text_grey":            "#A0A0A0",
            "text_light":           "#787878",
            "border":               "#2E2219",
            "shadow":               "#000000",
            "input_bg":             "#252525",
            "primary_orange_light": "#3A2210",
            "white":                "#FFFFFF",
        }
        self.theme = self.light

        # Active filter tab: "active" | "disabled" | "editorial"
        self.active_filter = "active"

        # Load admin data
        self.admins = self._fetch_admins()

        # User initials for avatar
        self.initials = (
            (self.user[0][:1] + self.user[1][:1]).upper()
            if self.user and len(self.user) >= 2 else "SA"
        )

        self._build_ui()
        self.root.bind("<Configure>", self._on_root_resize)

    # ── Data ─────────────────────────────────────────────────────────────────

    def _fetch_admins(self):
        if "fetch_admins" in self.callbacks:
            return self.callbacks["fetch_admins"]()
        return list(self.DEMO_ADMINS)

    def _counts(self):
        active    = sum(1 for a in self.admins if a[6] == 1 and a[7] == 0)
        disabled  = sum(1 for a in self.admins if a[6] == 0)
        editorial = sum(1 for a in self.admins if a[7] == 1 and a[6] == 1)
        return active, disabled, editorial

    def _filtered_admins(self):
        if self.active_filter == "active":
            return [a for a in self.admins if a[6] == 1 and a[7] == 0]
        if self.active_filter == "disabled":
            return [a for a in self.admins if a[6] == 0]
        if self.active_filter == "editorial":
            return [a for a in self.admins if a[6] == 1 and a[7] == 1]
        return self.admins

    # ── Build / Rebuild ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.configure(bg=self.theme["background"])
        self._make_header()
        self._make_orange_bar()
        self._make_sidebar()
        self._make_main()
        self._make_user_menu()
        self.header.lift()
        self.orange_bar.lift()

    def _rebuild(self):
        self.sidebar_visible            = False
        self.content_management_visible = False
        self.user_menu_visible          = False
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()
        self._sync_geometry()

    # ── Header ────────────────────────────────────────────────────────────────

    def _make_header(self):
        T = self.theme
        self.header = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        self.header.place(x=0, y=0, relwidth=1, height=self.HEADER_H)

        left = tk.Frame(self.header, bg=T["card"])
        left.pack(side="left", fill="y", padx=(18, 0))

        tk.Button(
            left, text="☰", command=self.toggle_sidebar,
            bg=T["card"], fg=T["primary_orange"],
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"],
            font=("Poppins", 20, "bold"),
            bd=0, relief="flat", cursor="hand2",
        ).pack(side="left", padx=(0, 16))

        logo_c = tk.Canvas(left, width=36, height=36,
                           bg=T["primary_orange"], highlightthickness=0)
        logo_c.pack(side="left", padx=(0, 14))
        logo_c.create_text(18, 18, text="TG", fill="white",
                           font=("Poppins", 11, "bold"))

        tk.Label(
            left, text="The Gears",
            bg=T["card"], fg=T["primary_orange"],
            font=("Hedvig Letters Serif 24pt", 17, "bold"),
        ).pack(side="left")

        tk.Label(
            left, text="  ·  Superadmin",
            bg=T["card"], fg=T["text_grey"],
            font=("Poppins", 11),
        ).pack(side="left")

        right = tk.Frame(self.header, bg=T["card"])
        right.pack(side="right", fill="y", padx=(0, 22))

        tk.Label(
            right, text="SUPERADMIN",
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            font=FONTS["tag"], padx=12, pady=5,
        ).pack(side="left", padx=(0, 14))

        av = tk.Canvas(right, width=36, height=36,
                       bg=T["card"], highlightthickness=0, cursor="hand2")
        av.pack(side="left")
        av.create_oval(1, 1, 35, 35,
                       fill=T["primary_orange"], outline=T["primary_orange"])
        av.create_text(18, 18, text=self.initials,
                       fill="white", font=("Poppins", 10, "bold"))
        av.bind("<Button-1>", lambda e: self.toggle_user_menu())

    # ── Orange bar ────────────────────────────────────────────────────────────

    def _make_orange_bar(self):
        self.orange_bar = tk.Frame(self.root, bg=self.theme["primary_orange"])
        self.orange_bar.place(x=0, y=self.HEADER_H, relwidth=1, height=self.BAR_H)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _make_sidebar(self):
        T   = self.theme
        rh  = self.root.winfo_height() or 800

        self.sidebar = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        self.sidebar.place(
            x=-self.SIDEBAR_W, y=self.TOP_OFFSET,
            width=self.SIDEBAR_W, height=rh - self.TOP_OFFSET,
        )

        strip = tk.Frame(self.sidebar, bg=T["primary_orange_light"], height=50)
        strip.pack(fill="x")
        strip.pack_propagate(False)
        tk.Label(strip, text="NAVIGATION",
                 bg=T["primary_orange_light"], fg=T["primary_orange"],
                 font=FONTS["tag"], padx=22).pack(side="left", fill="y")

        self._nav("🏠  Dashboard",    self._go_dashboard)
        self._nav("👤  Manage Admins", self._go_manage_admins, active=True)
        self._nav("👥  Manage Users",  self._go_manage_users)

        self.content_btn = self._nav("📂  Content  ▾", self.toggle_content_management)

        self.dropdown_frame = tk.Frame(self.sidebar, bg=T["background_alt"])
        self._subnav("   📄  Pending Articles", self._go_pending_articles)
        self._subnav("   🏷️  Categories",        self._go_categories)
        self._subnav("   📋  Activity Logs",     self._go_activity_logs)

        tk.Frame(self.sidebar, bg=T["card"]).pack(fill="both", expand=True)
        tk.Frame(self.sidebar, bg=T["border"], height=1).pack(fill="x", padx=14, pady=(0, 2))

        tk.Button(
            self.sidebar, text="🚪  Logout", command=self._logout,
            anchor="w", bg=T["card"], fg=T["primary_red"],
            activebackground="#FFF0F0", activeforeground=T["primary_red"],
            font=FONTS["body_bold"],
            bd=0, relief="flat", padx=22, pady=14, cursor="hand2",
        ).pack(fill="x")

    def _nav(self, text, command, active=False):
        T  = self.theme
        bg = T["primary_orange_light"] if active else T["card"]
        fg = T["primary_orange"]       if active else T["text_dark"]
        btn = tk.Button(
            self.sidebar, text=text, command=command,
            anchor="w", bg=bg, fg=fg,
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"],
            font=FONTS["button"] if active else FONTS["body"],
            bd=0, relief="flat", padx=22, pady=13, cursor="hand2",
        )
        btn.pack(fill="x", padx=8, pady=1)
        return btn

    def _subnav(self, text, command):
        T = self.theme
        tk.Button(
            self.dropdown_frame, text=text, command=command,
            anchor="w", bg=T["background_alt"], fg=T["text_grey"],
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"],
            font=FONTS["body"],
            bd=0, relief="flat", padx=28, pady=11, cursor="hand2",
        ).pack(fill="x", padx=8)

    # ── Main scrollable area ──────────────────────────────────────────────────

    def _make_main(self):
        T  = self.theme
        rw = self.root.winfo_width()  or 1280
        rh = self.root.winfo_height() or 800

        self.main = tk.Frame(self.root, bg=T["background"])
        self.main.place(x=0, y=self.TOP_OFFSET, width=rw, height=rh - self.TOP_OFFSET)

        outer = tk.Frame(self.main, bg=T["background"])
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg=T["background"], highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)

        self.content = tk.Frame(self.canvas, bg=T["background"])
        self._cwin   = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfig(self._cwin, width=e.width))
        self.canvas.bind("<Enter>",
            lambda e: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>",
            lambda e: self.canvas.unbind_all("<MouseWheel>"))

        self.inner = tk.Frame(self.content, bg=T["background"])
        self.inner.pack(fill="both", expand=True, padx=36, pady=(30, 44))

        self._section_page_header()
        self._section_status_tabs()
        self._section_table_card()

    def _on_wheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── User menu ─────────────────────────────────────────────────────────────

    def _make_user_menu(self):
        T = self.theme
        self.user_menu = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )

        if self.user:
            name  = f"{self.user[0]} {self.user[1]}" if len(self.user) >= 2 else self.user[0]
            email = self.user[2] if len(self.user) > 2 else ""
            info  = tk.Frame(self.user_menu, bg=T["primary_orange_light"], pady=10)
            info.pack(fill="x")
            tk.Label(info, text=name,
                     bg=T["primary_orange_light"], fg=T["text_dark"],
                     font=FONTS["small_bold"], anchor="w", padx=14).pack(fill="x")
            tk.Label(info, text=email,
                     bg=T["primary_orange_light"], fg=T["text_grey"],
                     font=FONTS["small"], anchor="w", padx=14).pack(fill="x")

        tk.Frame(self.user_menu, bg=T["border"], height=1).pack(fill="x", padx=8, pady=2)

        for label, cmd, red in [
            ("🌙  Toggle Dark Mode", self.toggle_dark_mode, False),
            ("🚪  Logout",           self._logout,           True),
        ]:
            tk.Button(
                self.user_menu, text=label, command=cmd,
                anchor="w", bg=T["card"],
                fg=T["primary_red"] if red else T["text_dark"],
                activebackground=T["primary_orange_light"],
                activeforeground=T["primary_red"] if red else T["primary_orange"],
                font=FONTS["body_bold"] if red else FONTS["body"],
                bd=0, relief="flat", padx=14, pady=10, cursor="hand2",
            ).pack(fill="x")

    # ── Page header ───────────────────────────────────────────────────────────

    def _section_page_header(self):
        T    = self.theme
        wrap = tk.Frame(self.inner, bg=T["background"])
        wrap.pack(fill="x", pady=(0, 18))

        left = tk.Frame(wrap, bg=T["background"])
        left.pack(side="left", fill="y")

        tk.Label(left, text="MANAGE ADMIN ACCOUNTS",
                 bg=T["background"], fg=T["primary_orange"],
                 font=("Poppins", 22, "bold")).pack(anchor="w")
        tk.Label(left, text="Create, edit, and manage admin accounts for The Gears.",
                 bg=T["background"], fg=T["text_grey"],
                 font=FONTS["body"]).pack(anchor="w", pady=(4, 0))

        tk.Button(
            wrap, text="＋  Add New Admin",
            command=self._open_create_modal,
            bg=T["primary_orange"], fg=T["white"],
            activebackground=T["primary_orange_dark"],
            activeforeground=T["white"],
            font=FONTS["button"],
            bd=0, relief="flat", padx=18, pady=10, cursor="hand2",
        ).pack(side="right", anchor="center")

    # ── Status tabs ───────────────────────────────────────────────────────────

    def _section_status_tabs(self):
        T = self.theme
        active_c, disabled_c, editorial_c = self._counts()

        self.tabs_frame = tk.Frame(self.inner, bg=T["background"])
        self.tabs_frame.pack(fill="x", pady=(0, 16))

        self.tab_btns = {}
        for key, label, count in [
            ("active",    "Active",          active_c),
            ("disabled",  "Disabled",        disabled_c),
            ("editorial", "Editorial Board", editorial_c),
        ]:
            self.tab_btns[key] = self._tab_button(
                self.tabs_frame, key, label, count
            )

        self._refresh_tab_styles()

    def _tab_button(self, parent, key, label, count):
        T      = self.theme
        is_act = (key == self.active_filter)
        bg     = T["primary_orange"] if is_act else T["card"]
        fg     = T["white"]          if is_act else T["text_grey"]

        frame = tk.Frame(parent,
                         bg=bg,
                         highlightbackground=T["border"],
                         highlightthickness=1)
        frame.pack(side="left", padx=(0, 8))

        inner = tk.Frame(frame, bg=bg)
        inner.pack(padx=14, pady=7)

        lbl = tk.Label(inner, text=label, bg=bg, fg=fg, font=FONTS["button"])
        lbl.pack(side="left")

        badge_bg = "#FFFFFF33" if is_act else T["primary_orange_light"]
        badge_fg = T["white"]  if is_act else T["primary_orange"]
        cnt_lbl  = tk.Label(inner, text=str(count),
                            bg=badge_bg, fg=badge_fg,
                            font=FONTS["tag"], padx=6, pady=2)
        cnt_lbl.pack(side="left", padx=(8, 0))

        def _click(k=key):
            self.active_filter = k
            self._refresh_tab_styles()
            self._refresh_table()

        for widget in (frame, inner, lbl, cnt_lbl):
            widget.bind("<Button-1>", lambda e, k=key: _click(k))
            widget.configure(cursor="hand2")

        return frame

    def _refresh_tab_styles(self):
        T = self.theme
        active_c, disabled_c, editorial_c = self._counts()
        counts = {"active": active_c, "disabled": disabled_c, "editorial": editorial_c}

        for key, frame in self.tab_btns.items():
            is_act = (key == self.active_filter)
            bg     = T["primary_orange"] if is_act else T["card"]
            fg     = T["white"]          if is_act else T["text_grey"]
            badge_bg = T["primary_orange_light"] if not is_act else T["primary_orange"]
            badge_fg = T["primary_orange"]       if not is_act else T["white"]

            frame.configure(bg=bg, highlightbackground=T["border"])
            for child in frame.winfo_children():
                child.configure(bg=bg)
                for grandchild in child.winfo_children():
                    grandchild.configure(bg=bg, fg=fg)

    # ── Table card ────────────────────────────────────────────────────────────

    def _section_table_card(self):
        T = self.theme
        active_c, disabled_c, editorial_c = self._counts()
        total = active_c + disabled_c + editorial_c

        self.table_card_frame = tk.Frame(
            self.inner, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        self.table_card_frame.pack(fill="x")

        # Card header
        card_hdr = tk.Frame(self.table_card_frame, bg=T["background_alt"], pady=12)
        card_hdr.pack(fill="x")

        left_hdr = tk.Frame(card_hdr, bg=T["background_alt"])
        left_hdr.pack(side="left", padx=22)

        tk.Label(left_hdr, text="Admin List",
                 bg=T["background_alt"], fg=T["text_dark"],
                 font=FONTS["body_bold"]).pack(anchor="w")
        tk.Label(left_hdr, text="All users with admin privileges in the system.",
                 bg=T["background_alt"], fg=T["text_grey"],
                 font=FONTS["small"]).pack(anchor="w", pady=(2, 0))

        tk.Label(card_hdr,
                 text=f"{total} admins",
                 bg=T["primary_orange_light"], fg=T["primary_orange"],
                 font=FONTS["tag"], padx=10, pady=4,
                 ).pack(side="right", padx=22, anchor="center")

        # Separator
        tk.Frame(self.table_card_frame, bg=T["border"], height=1).pack(fill="x")

        # Table container (will be rebuilt on filter change)
        self.table_container = tk.Frame(self.table_card_frame, bg=T["card"])
        self.table_container.pack(fill="x")
        self._build_table()

    def _build_table(self):
        T       = self.theme
        for w in self.table_container.winfo_children():
            w.destroy()

        admins = self._filtered_admins()

        # Column headers
        hdr_frame = tk.Frame(self.table_container, bg=T["background_alt"])
        hdr_frame.pack(fill="x")

        COL_WEIGHTS = [3, 2, 3, 1, 3]
        COL_LABELS  = ["Full Name", "Username", "Email", "Status", "Actions"]
        for c in range(5):
            hdr_frame.grid_columnconfigure(c, weight=COL_WEIGHTS[c], uniform="tc")

        for c, lbl in enumerate(COL_LABELS):
            tk.Label(
                hdr_frame, text=lbl.upper(),
                bg=T["background_alt"], fg=T["text_grey"],
                font=FONTS["tag"], anchor="w",
                padx=16, pady=10,
            ).grid(row=0, column=c, sticky="ew")

        tk.Frame(self.table_container, bg=T["border"], height=1).pack(fill="x")

        if not admins:
            tk.Label(
                self.table_container,
                text="No admins in this category.",
                bg=T["card"], fg=T["text_grey"],
                font=FONTS["body"], pady=28,
            ).pack()
            return

        for i, admin in enumerate(admins):
            row_bg = T["background_alt"] if i % 2 == 1 else T["card"]
            self._table_row(self.table_container, admin, row_bg, COL_WEIGHTS, i < len(admins) - 1)

    def _table_row(self, parent, admin, row_bg, col_weights, add_sep):
        T   = self.theme
        aid, username, email, fn, mn, ln, is_active, is_editorial = admin
        full_name = f"{fn} {mn} {ln}".replace("  ", " ").strip()

        row = tk.Frame(parent, bg=row_bg)
        row.pack(fill="x")
        for c in range(5):
            row.grid_columnconfigure(c, weight=col_weights[c], uniform="tc")

        status_text  = "Active"   if is_active else "Disabled"
        status_color = T["success"] if is_active else T["primary_red"]

        cells = [full_name, username, email]
        for c, txt in enumerate(cells):
            tk.Label(row, text=txt, bg=row_bg, fg=T["text_dark"],
                     font=FONTS["body"], anchor="w", padx=16, pady=12,
                     ).grid(row=0, column=c, sticky="ew")

        # Status badge
        status_wrap = tk.Frame(row, bg=row_bg)
        status_wrap.grid(row=0, column=3, sticky="ew", padx=8, pady=8)
        tk.Label(
            status_wrap, text=status_text,
            bg=T["primary_orange_light"] if is_active else "#FDE8E8",
            fg=status_color,
            font=FONTS["small_bold"], padx=8, pady=4,
        ).pack(anchor="w")

        # Actions
        act_frame = tk.Frame(row, bg=row_bg)
        act_frame.grid(row=0, column=4, sticky="ew", padx=8, pady=8)

        if is_active:
            self._action_btn(act_frame, "✏ Edit", GREEN, GREEN_DARK,
                             lambda a=admin: self._open_edit_modal(a))
            self._action_btn(act_frame, "✕ Disable", RED_DISABLE, RED_DARK,
                             lambda a=admin: self._confirm_disable(a))
            if is_editorial:
                self._action_btn(act_frame, "▼ Demote", BROWN, BROWN_DARK,
                                 lambda a=admin: self._confirm_demote(a))
            else:
                self._action_btn(act_frame, "▲ Promote", BLUE, BLUE_DARK,
                                 lambda a=admin: self._confirm_promote(a))
        else:
            self._action_btn(act_frame, "✓ Enable", GREEN, GREEN_DARK,
                             lambda a=admin: self._confirm_enable(a))

        if add_sep:
            tk.Frame(parent, bg=T["border"], height=1).pack(fill="x")

    def _action_btn(self, parent, text, bg, active_bg, command):
        T = self.theme
        tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=T["white"],
            activebackground=active_bg, activeforeground=T["white"],
            font=FONTS["tag"], padx=10, pady=5,
            bd=0, relief="flat", cursor="hand2",
        ).pack(side="left", padx=(0, 6))

    def _refresh_table(self):
        self._build_table()

    # ── Modals ────────────────────────────────────────────────────────────────

    def _modal_window(self, title_text):
        """Create and return a centred Toplevel modal."""
        T    = self.theme
        win  = tk.Toplevel(self.root)
        win.title(title_text)
        win.configure(bg=T["card"])
        win.resizable(False, False)
        win.grab_set()
        win.transient(self.root)

        # Centre on parent
        win.update_idletasks()
        rw = self.root.winfo_x() + self.root.winfo_width()  // 2
        rh = self.root.winfo_y() + self.root.winfo_height() // 2
        win.geometry(f"+{rw - 200}+{rh - 160}")
        return win

    def _modal_title(self, win, text):
        T = self.theme
        tk.Label(win, text=text,
                 bg=T["card"], fg=T["primary_orange"],
                 font=FONTS["modal_title"]).pack(anchor="w", padx=24, pady=(22, 4))

    def _modal_subtitle(self, win, text):
        T = self.theme
        tk.Label(win, text=text, wraplength=340,
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["body"], justify="left").pack(anchor="w", padx=24, pady=(0, 12))

    def _modal_sep(self, win):
        tk.Frame(win, bg=self.theme["border"], height=1).pack(fill="x", padx=24, pady=4)

    def _modal_input(self, win, placeholder, show=""):
        T   = self.theme
        var = tk.StringVar()
        ent = tk.Entry(win, textvariable=var, show=show,
                       font=FONTS["input"],
                       bg=T["input_bg"], fg=T["text_dark"],
                       insertbackground=T["text_dark"],
                       highlightbackground=T["border"],
                       highlightthickness=1, bd=0,
                       relief="flat")
        ent.pack(fill="x", padx=24, pady=(0, 8), ipady=8)

        def _on_focus_in(e):
            ent.configure(highlightbackground=T["primary_orange"])
        def _on_focus_out(e):
            ent.configure(highlightbackground=T["border"])
        ent.bind("<FocusIn>",  _on_focus_in)
        ent.bind("<FocusOut>", _on_focus_out)

        # Placeholder behaviour
        ent.insert(0, placeholder)
        ent.configure(fg=T["text_light"])
        def _clear(e):
            if ent.get() == placeholder:
                ent.delete(0, "end")
                ent.configure(fg=T["text_dark"])
        def _restore(e):
            if not ent.get():
                ent.insert(0, placeholder)
                ent.configure(fg=T["text_light"])
        ent.bind("<FocusIn>",  _clear)
        ent.bind("<FocusOut>", _restore)
        return ent, var

    def _modal_label(self, win, text):
        T = self.theme
        tk.Label(win, text=text,
                 bg=T["card"], fg=T["text_mid"],
                 font=FONTS["small_bold"]).pack(anchor="w", padx=24, pady=(6, 2))

    def _modal_actions(self, win, cancel_text, confirm_text, confirm_cmd,
                       confirm_bg=None, confirm_fg=None):
        T   = self.theme
        cbg = confirm_bg or T["primary_orange"]
        cfg = confirm_fg or T["white"]
        cab = T["primary_orange_dark"]

        act = tk.Frame(win, bg=T["card"])
        act.pack(fill="x", padx=24, pady=(12, 22))

        tk.Button(act, text=cancel_text,
                  command=win.destroy,
                  bg=T["background_alt"], fg=T["text_mid"],
                  activebackground=T["border"], activeforeground=T["text_dark"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=18, pady=9, cursor="hand2").pack(side="left")

        tk.Button(act, text=confirm_text,
                  command=confirm_cmd,
                  bg=cbg, fg=cfg,
                  activebackground=cab, activeforeground=cfg,
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=18, pady=9, cursor="hand2").pack(side="right")

    # ── Create Admin Modal ────────────────────────────────────────────────────

    def _open_create_modal(self):
        win = self._modal_window("Add New Admin")
        win.geometry("420x480")

        self._modal_title(win, "Add New Admin")
        self._modal_subtitle(win, "Fill in the details to create a new admin account.")
        self._modal_sep(win)

        self._modal_label(win, "First Name *")
        fn_ent, fn_var = self._modal_input(win, "e.g. Maria")

        self._modal_label(win, "Middle Name")
        mn_ent, mn_var = self._modal_input(win, "e.g. A. (optional)")

        self._modal_label(win, "Last Name *")
        ln_ent, ln_var = self._modal_input(win, "e.g. Santos")

        self._modal_label(win, "Email Address *")
        em_ent, em_var = self._modal_input(win, "e.g. maria@gears.com")

        placeholders = {fn_ent: "e.g. Maria", mn_ent: "e.g. A. (optional)",
                        ln_ent: "e.g. Santos", em_ent: "e.g. maria@gears.com"}

        def _get(ent, ph):
            v = ent.get()
            return "" if v == ph else v

        def _confirm():
            fn = _get(fn_ent, placeholders[fn_ent])
            mn = _get(mn_ent, placeholders[mn_ent])
            ln = _get(ln_ent, placeholders[ln_ent])
            em = _get(em_ent, placeholders[em_ent])
            if not fn or not ln or not em:
                messagebox.showerror("Validation", "First name, last name, and email are required.",
                                     parent=win)
                return
            win.destroy()
            self._confirm_create(fn, mn, ln, em)

        self._modal_actions(win, "Cancel", "✓  Create Admin", _confirm)

    def _confirm_create(self, fn, mn, ln, email):
        win = self._modal_window("Confirm Create Admin")
        win.geometry("400x200")
        self._modal_title(win, "Confirm Action")
        self._modal_subtitle(win,
            f"Are you sure you want to create an admin account for\n{fn} {ln}?")

        def _do():
            if "create_admin" in self.callbacks:
                pw = self.callbacks["create_admin"](fn, mn, ln, email)
            else:
                pw = "demo_password_123"
                # Add to local demo list
                new_id = max(a[0] for a in self.admins) + 1 if self.admins else 1
                uname  = f"{fn.lower()}.{ln.lower()}"
                self.admins.append((new_id, uname, email, fn, mn, ln, 1, 0))
            win.destroy()
            self._show_generated_password(pw)
            self._rebuild_table_section()

        self._modal_actions(win, "Cancel", "✓  Yes, Create", _do)

    def _show_generated_password(self, pw):
        T   = self.theme
        win = self._modal_window("Admin Created")
        win.geometry("400x200")

        self._modal_title(win, "✓  Admin Created")
        self._modal_subtitle(win, "The admin account has been created successfully.")

        info = tk.Frame(win, bg="#FFF8E6",
                        highlightbackground="#FFECB3", highlightthickness=1)
        info.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(info, text="Generated Password:",
                 bg="#FFF8E6", fg="#8A6D3B",
                 font=FONTS["small_bold"], padx=12, pady=(8, 2)).pack(anchor="w")
        tk.Label(info, text=pw,
                 bg="#FFF8E6", fg=T["text_dark"],
                 font=("Courier", 12, "bold"), padx=12, pady=(2, 8)).pack(anchor="w")

        tk.Button(win, text="Close", command=win.destroy,
                  bg=T["primary_orange"], fg=T["white"],
                  activebackground=T["primary_orange_dark"],
                  activeforeground=T["white"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=18, pady=9, cursor="hand2").pack(pady=8)

    # ── Edit Admin Modal ──────────────────────────────────────────────────────

    def _open_edit_modal(self, admin):
        aid, username, email = admin[0], admin[1], admin[2]
        win = self._modal_window("Edit Admin")
        win.geometry("420x320")

        self._modal_title(win, "Edit Admin")
        self._modal_subtitle(win, "Update the admin's username and email address.")
        self._modal_sep(win)

        self._modal_label(win, "Username")
        un_ent, un_var = self._modal_input(win, "Username")
        un_ent.delete(0, "end"); un_ent.insert(0, username)
        un_ent.configure(fg=self.theme["text_dark"])

        self._modal_label(win, "Email Address")
        em_ent, em_var = self._modal_input(win, "Email")
        em_ent.delete(0, "end"); em_ent.insert(0, email)
        em_ent.configure(fg=self.theme["text_dark"])

        def _confirm():
            new_un = un_ent.get().strip()
            new_em = em_ent.get().strip()
            if not new_un or not new_em:
                messagebox.showerror("Validation", "Username and email are required.", parent=win)
                return
            if "update_admin" in self.callbacks:
                self.callbacks["update_admin"](aid, new_un, new_em)
            else:
                # Update demo list
                for i, a in enumerate(self.admins):
                    if a[0] == aid:
                        self.admins[i] = (a[0], new_un, new_em, a[3], a[4], a[5], a[6], a[7])
                        break
            win.destroy()
            self._rebuild_table_section()

        self._modal_actions(win, "Cancel", "✓  Update Admin", _confirm)

    # ── Disable / Enable ──────────────────────────────────────────────────────

    def _confirm_disable(self, admin):
        aid, username = admin[0], admin[1]
        win = self._modal_window("Disable Admin")
        win.geometry("400x200")
        self._modal_title(win, "Disable Admin")
        self._modal_subtitle(win, f'Are you sure you want to disable admin "{username}"?\nThis will revoke their access.')

        def _do():
            if "disable_admin" in self.callbacks:
                self.callbacks["disable_admin"](aid)
            else:
                for i, a in enumerate(self.admins):
                    if a[0] == aid:
                        self.admins[i] = (*a[:6], 0, a[7])
                        break
            win.destroy()
            self._rebuild_table_section()

        self._modal_actions(win, "Cancel", "✕  Yes, Disable", _do,
                            confirm_bg=self.theme["primary_red"])

    def _confirm_enable(self, admin):
        aid, username = admin[0], admin[1]
        win = self._modal_window("Enable Admin")
        win.geometry("400x200")
        self._modal_title(win, "Enable Admin")
        self._modal_subtitle(win, f'Are you sure you want to re-enable admin "{username}"?')

        def _do():
            if "enable_admin" in self.callbacks:
                self.callbacks["enable_admin"](aid)
            else:
                for i, a in enumerate(self.admins):
                    if a[0] == aid:
                        self.admins[i] = (*a[:6], 1, a[7])
                        break
            win.destroy()
            self._rebuild_table_section()

        self._modal_actions(win, "Cancel", "✓  Yes, Enable", _do)

    # ── Promote / Demote ──────────────────────────────────────────────────────

    def _confirm_promote(self, admin):
        aid, username = admin[0], admin[1]
        win = self._modal_window("Promote Admin")
        win.geometry("400x200")
        self._modal_title(win, "Promote Admin")
        self._modal_subtitle(win,
            f'Promote "{username}" to Editorial Board Member?')

        def _do():
            if "promote_admin" in self.callbacks:
                self.callbacks["promote_admin"](aid)
            else:
                for i, a in enumerate(self.admins):
                    if a[0] == aid:
                        self.admins[i] = (*a[:7], 1)
                        break
            win.destroy()
            self._rebuild_table_section()

        self._modal_actions(win, "Cancel", "▲  Yes, Promote", _do,
                            confirm_bg=BLUE)

    def _confirm_demote(self, admin):
        aid, username = admin[0], admin[1]
        win = self._modal_window("Demote Admin")
        win.geometry("400x200")
        self._modal_title(win, "Demote Admin")
        self._modal_subtitle(win,
            f'Remove "{username}" from the Editorial Board?')

        def _do():
            if "demote_admin" in self.callbacks:
                self.callbacks["demote_admin"](aid)
            else:
                for i, a in enumerate(self.admins):
                    if a[0] == aid:
                        self.admins[i] = (*a[:7], 0)
                        break
            win.destroy()
            self._rebuild_table_section()

        self._modal_actions(win, "Cancel", "▼  Yes, Demote", _do,
                            confirm_bg=BROWN)

    # ── Table refresh helper ──────────────────────────────────────────────────

    def _rebuild_table_section(self):
        """Refresh the tab counts and table without a full rebuild."""
        # Refresh tab counts
        active_c, disabled_c, editorial_c = self._counts()
        counts = {"active": active_c, "disabled": disabled_c, "editorial": editorial_c}
        # Destroy and recreate tabs + table
        self.tabs_frame.destroy()
        self.table_card_frame.destroy()
        self._section_status_tabs()
        self._section_table_card()

    # ── Geometry / Toggles ────────────────────────────────────────────────────

    def _sync_geometry(self):
        rw     = self.root.winfo_width()
        rh     = self.root.winfo_height()
        body_h = rh - self.TOP_OFFSET

        sx = 0 if self.sidebar_visible else -self.SIDEBAR_W
        self.sidebar.place_configure(x=sx, y=self.TOP_OFFSET,
                                     width=self.SIDEBAR_W, height=body_h)
        mx = self.SIDEBAR_W if self.sidebar_visible else 0
        self.main.place_configure(x=mx, y=self.TOP_OFFSET,
                                  width=rw - mx, height=body_h)

    def _on_root_resize(self, event=None):
        if event and event.widget is not self.root:
            return
        self._sync_geometry()

    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        if self.sidebar_visible:
            self.sidebar.lift()
        self._sync_geometry()

    def toggle_content_management(self):
        self.content_management_visible = not self.content_management_visible
        if self.content_management_visible:
            self.dropdown_frame.pack(fill="x", pady=(0, 4))
            self.content_btn.configure(text="📂  Content  ▴")
        else:
            self.dropdown_frame.pack_forget()
            self.content_btn.configure(text="📂  Content  ▾")

    def toggle_user_menu(self):
        self.user_menu_visible = not self.user_menu_visible
        if self.user_menu_visible:
            rw = self.root.winfo_width()
            self.user_menu.place(x=rw - 240, y=self.TOP_OFFSET, width=228)
            self.user_menu.lift()
        else:
            self.user_menu.place_forget()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.theme     = self.dark if self.dark_mode else self.light
        self._rebuild()

    # ── Navigation stubs ──────────────────────────────────────────────────────

    def _go_dashboard(self):
        if hasattr(self.root, "show_superadmin"):
            self.root.show_superadmin(user=self.user)

    def _go_manage_admins(self):
        pass  # already here

    def _go_manage_users(self):
        if hasattr(self.root, "show_manage_users"):
            self.root.show_manage_users(user=self.user)
        else:
            messagebox.showinfo("Manage Users", "Navigating to Manage Users.")

    def _go_pending_articles(self):
        messagebox.showinfo("Pending Articles", "Navigating to Pending Articles.")

    def _go_categories(self):
        messagebox.showinfo("Categories", "Navigating to Categories.")

    def _go_activity_logs(self):
        messagebox.showinfo("Activity Logs", "Navigating to Activity Logs.")

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            if hasattr(self.root, "show_landing"):
                self.root.show_landing()
            else:
                self.root.destroy()


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    root.title("The Gears — Manage Admins")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    ManageAdmins(
        root,
        user=("Francis Jane", "Olvido", "admin@gears.com", 1, "superadmin"),
    )
    root.mainloop()