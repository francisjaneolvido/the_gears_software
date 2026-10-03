"""
superadmin/superadmin_layout.py
────────────────────────────────
Reusable Superadmin Layout for The Gears.

Provides a consistent header + sidebar shell that any superadmin page can
inherit.  Mirrors admin/admin_layout.py in structure and API.

Usage:
    class MyPage(SuperadminLayout):
        def __init__(self, root, user=None, db_callbacks=None):
            super().__init__(root, user, db_callbacks)
            self._build_page()   # ← build your page content inside self.inner

The subclass gets:
    self.inner      – tk.Frame inside the scrollable content area (pack into this)
    self.canvas     – the scrollable Canvas (for yview manipulation)
    self.theme      – current colour dict (light or dark)
    self.root       – the Tk root
    self.user       – user tuple
    self.callbacks  – db_callbacks dict

Set the class attribute ACTIVE_NAV on the subclass to highlight the correct
sidebar entry.  Valid values:
    "dashboard"  "manage_admins"  "manage_users"
    "pending_articles"  "categories"  "activity_logs"

Navigation helpers call self._unbind_all() automatically before navigating away.
"""

import tkinter as tk
from tkinter import messagebox

try:
    from theme import COLORS, FONTS
except ImportError:
    COLORS = {
        "primary_orange":       "#F19421",
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
        "input_bg":             "#F5F3F0",
        "navy":                 "#0C1633",
        "tab_active":           "#F19421",
        "tab_inactive_fg":      "#777777",
    }
    FONTS = {
        "heading":     ("Poppins", 20, "bold"),
        "section":     ("Poppins", 16, "bold"),
        "card_title":  ("Poppins", 13, "bold"),
        "body":        ("Poppins", 11),
        "body_bold":   ("Poppins", 11, "bold"),
        "small":       ("Poppins", 9),
        "small_bold":  ("Poppins", 9, "bold"),
        "button":      ("Poppins", 10, "bold"),
        "tag":         ("Poppins", 8, "bold"),
        "input":       ("Poppins", 11),
        "modal_title": ("Poppins", 18, "bold"),
        "table_head":  ("Poppins", 9, "bold"),
        "table_body":  ("Poppins", 10),
    }


# ─────────────────────────────────────────────────────────────────────────────
class SuperadminLayout:
    """
    Base layout class providing the header, orange bar, sidebar, scrollable
    content area, and user dropdown menu for superadmin pages.
    """

    HEADER_H   = 64
    BAR_H      = 3
    TOP_OFFSET = HEADER_H + BAR_H
    SIDEBAR_W  = 256

    ACTIVE_NAV = "dashboard"

    def __init__(self, root, user=None, db_callbacks=None):
        self.root      = root
        self.user      = user
        self.callbacks = db_callbacks or {}

        self.sidebar_visible    = False
        self.content_expanded   = False
        self.user_menu_visible  = False
        self.dark_mode          = False
        self._scroll_pos        = 0.0

        self._bind_configure = None
        self._bind_click     = None

        # ── Themes ────────────────────────────────────────────────────────────
        self.light = COLORS.copy()
        self.dark  = {
            **COLORS,
            "background":           "#111111",
            "background_alt":       "#181818",
            "card":                 "#1C1C1C",
            "text_dark":            "#F0F0F0",
            "text_mid":             "#D0D0D0",
            "text_grey":            "#A0A0A0",
            "text_light":           "#606060",
            "border":               "#2A1F14",
            "input_bg":             "#232323",
            "primary_orange_light": "#2E1A08",
            "white":                "#FFFFFF",
        }
        self.theme = self.light

        # ── User info ─────────────────────────────────────────────────────────
        self.initials = (
            (self.user[0][:1] + self.user[1][:1]).upper()
            if self.user and len(self.user) >= 2 else "SA"
        )
        self.display_name = (
            f"{self.user[0]} {self.user[1]}"
            if self.user and len(self.user) >= 2 else "Superadmin"
        )
        self.user_id = self.user[3] if self.user and len(self.user) > 3 else None
        self._profile = self._fetch_profile()

        self._build_chrome()

        self._bind_configure = self.root.bind("<Configure>", self._on_root_resize)
        self._bind_click     = self.root.bind(
            "<Button-1>", self._maybe_close_user_menu, add="+"
        )

    # =========================================================================
    # Public helpers
    # =========================================================================

    def _rebuild_chrome(self):
        try:
            self._scroll_pos = self.canvas.yview()[0]
        except Exception:
            self._scroll_pos = 0.0

        self._unbind_all()
        self.sidebar_visible   = False
        self.content_expanded  = False
        self.user_menu_visible = False

        for w in self.root.winfo_children():
            w.destroy()

        self._build_chrome()
        self._build_page()

        self._bind_configure = self.root.bind("<Configure>", self._on_root_resize)
        self._bind_click     = self.root.bind(
            "<Button-1>", self._maybe_close_user_menu, add="+"
        )
        self._sync_geometry()
        self.root.after(60, lambda: self.canvas.yview_moveto(self._scroll_pos))

    def _build_page(self):
        """Override in subclasses to populate self.inner."""
        pass

    # =========================================================================
    # Chrome construction
    # =========================================================================

    def _build_chrome(self):
        self.root.configure(bg=self.theme["background"])
        self._make_header()
        self._make_orange_bar()
        self._make_sidebar()
        self._make_main_shell()
        self._make_user_menu()
        self.header.lift()
        self.orange_bar.lift()

    # ── Header ────────────────────────────────────────────────────────────────

    def _make_header(self):
        T = self.theme
        self.header = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        self.header.place(x=0, y=0, relwidth=1, height=self.HEADER_H)

        # Left ─────────────────────────────────────────────────────────────────
        left = tk.Frame(self.header, bg=T["card"])
        left.pack(side="left", fill="y", padx=(16, 0))

        # Hamburger
        ham = tk.Button(
            left, text="☰", command=self.toggle_sidebar,
            bg=T["card"], fg=T["text_grey"],
            activebackground=T["background_alt"],
            activeforeground=T["primary_orange"],
            font=("Poppins", 17),
            bd=0, relief="flat", cursor="hand2",
            padx=8, pady=4,
        )
        ham.pack(side="left", padx=(0, 12))

        # Separator
        tk.Frame(left, bg=T["border"], width=1).pack(
            side="left", fill="y", pady=14, padx=(0, 16))

        # Logo
        import os
        from PIL import Image, ImageTk

        logo_c = tk.Canvas(left, width=32, height=32,
                           bg=T["card"], highlightthickness=0)
        logo_c.pack(side="left", padx=(0, 10))
        try:
            _logo_path = os.path.join("assets", "gears_logo.png")
            _logo_img  = Image.open(_logo_path).convert("RGBA").resize(
                (32, 32), Image.LANCZOS)
            self._logo_photo = ImageTk.PhotoImage(_logo_img)
            logo_c.create_image(0, 0, anchor="nw", image=self._logo_photo)
        except Exception:
            logo_c.configure(bg=T["primary_orange"])
            logo_c.create_text(16, 16, text="TG", fill="white",
                               font=("Poppins", 9, "bold"))

        # Wordmark
        brand = tk.Frame(left, bg=T["card"])
        brand.pack(side="left")
        tk.Label(
            brand, text="The Gears",
            bg=T["card"], fg=T["primary_orange"],
            font=("Hedvig Letters Serif 24pt", 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand, text="Superadmin Panel",
            bg=T["card"], fg=T["text_light"],
            font=("Poppins", 8),
        ).pack(anchor="w")

        # Right ────────────────────────────────────────────────────────────────
        right = tk.Frame(self.header, bg=T["card"])
        right.pack(side="right", fill="y", padx=(0, 20))

        # Role badge — always SUPERADMIN
        tk.Label(
            right, text="SUPERADMIN",
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            font=("Poppins", 7, "bold"), padx=10, pady=4,
        ).pack(side="left", padx=(0, 16))

        # Separator
        tk.Frame(right, bg=T["border"], width=1).pack(
            side="left", fill="y", pady=14, padx=(0, 16))

        # Avatar button
        self._avatar_canvas = tk.Canvas(
            right, width=34, height=34,
            bg=T["card"], highlightthickness=0, cursor="hand2",
        )
        self._avatar_canvas.pack(side="left")
        self._draw_header_avatar()
        self._avatar_canvas.bind(
            "<Button-1>", lambda e: ("break", self.toggle_user_menu())
        )

        # Caret
        self._caret_lbl = tk.Label(
            right, text="▾",
            bg=T["card"], fg=T["text_light"],
            font=("Poppins", 8), cursor="hand2",
        )
        self._caret_lbl.pack(side="left", padx=(4, 0))
        self._caret_lbl.bind("<Button-1>", lambda e: self.toggle_user_menu())

    def _draw_header_avatar(self):
        T = self.theme
        self._avatar_canvas.delete("all")

        import os
        try:
            from PIL import Image, ImageTk, ImageDraw
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            src = self._profile.get("profile_image")
            if src:
                src  = src.replace("\\", "/")
                full = src if os.path.isabs(src) else os.path.join(project_root, src)
                full = os.path.normpath(full)
                if os.path.exists(full):
                    img  = Image.open(full).convert("RGBA").resize((34, 34))
                    mask = Image.new("L", (34, 34), 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, 33, 33), fill=255)
                    img.putalpha(mask)
                    self._header_avatar_photo = ImageTk.PhotoImage(img)
                    self._avatar_canvas.create_image(
                        0, 0, anchor="nw", image=self._header_avatar_photo)
                    return
        except Exception as e:
            print(f"[SuperadminLayout._draw_header_avatar] {e}")

        # Fallback initials circle
        self._avatar_canvas.create_oval(
            1, 1, 33, 33, fill=T["primary_orange"], outline="")
        self._avatar_canvas.create_text(
            17, 17, text=self.initials, fill="white",
            font=("Poppins", 9, "bold"))

    # ── Orange accent bar ─────────────────────────────────────────────────────

    def _make_orange_bar(self):
        self.orange_bar = tk.Frame(self.root, bg=self.theme["primary_orange"])
        self.orange_bar.place(x=0, y=self.HEADER_H, relwidth=1, height=self.BAR_H)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _make_sidebar(self):
        T  = self.theme
        rh = self.root.winfo_height() or 800

        self.sidebar = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        self.sidebar.place(
            x=-self.SIDEBAR_W, y=self.TOP_OFFSET,
            width=self.SIDEBAR_W, height=rh - self.TOP_OFFSET,
        )

        # ── Profile mini card ─────────────────────────────────────────────────
        profile_card = tk.Frame(self.sidebar, bg=T["primary_orange_light"])
        profile_card.pack(fill="x")

        pc_inner = tk.Frame(profile_card, bg=T["primary_orange_light"])
        pc_inner.pack(fill="x", padx=16, pady=14)

        av_c = tk.Canvas(pc_inner, width=36, height=36,
                         bg=T["primary_orange_light"], highlightthickness=0)
        av_c.pack(side="left", padx=(0, 10))
        self._sidebar_avatar_canvas = av_c
        self._draw_sidebar_avatar()

        info_col = tk.Frame(pc_inner, bg=T["primary_orange_light"])
        info_col.pack(side="left", fill="x", expand=True)

        name = self.display_name
        if len(name) > 18:
            name = name[:16] + "…"
        tk.Label(
            info_col, text=name,
            bg=T["primary_orange_light"], fg=T["text_dark"],
            font=("Poppins", 9, "bold"), anchor="w",
        ).pack(fill="x")
        tk.Label(
            info_col, text="Super Admin",
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            font=("Poppins", 8), anchor="w",
        ).pack(fill="x")

        # Divider
        tk.Frame(self.sidebar, bg=T["border"], height=1).pack(fill="x")

        # ── MAIN section ──────────────────────────────────────────────────────
        self._section_label("MAIN")

        self._nav_item(
            "🏠", "Dashboard", self._go_dashboard,
            active=(self.ACTIVE_NAV == "dashboard"),
        )

        # ── USERS section ─────────────────────────────────────────────────────
        self._section_label("USERS")

        self._nav_item(
            "👤", "Manage Admins", self._go_manage_admins,
            active=(self.ACTIVE_NAV == "manage_admins"),
        )
        self._nav_item(
            "👥", "Manage Users", self._go_manage_users,
            active=(self.ACTIVE_NAV == "manage_users"),
        )

        # ── CONTENT section ───────────────────────────────────────────────────
        self._section_label("CONTENT")

        self.content_btn = self._nav_item(
            "📂", "Content", self._toggle_content,
            active=(self.ACTIVE_NAV in (
                "pending_articles", "categories", "activity_logs"
            )),
            has_chevron=True,
        )

        # Content submenu
        self.content_frame = tk.Frame(self.sidebar, bg=T["background"])
        sub_items = [
            ("Pending Articles", self._go_pending_articles, "pending_articles"),
            ("Categories",       self._go_categories,       "categories"),
            ("Activity Logs",    self._go_activity_logs,    "activity_logs"),
        ]
        for text, cmd, key in sub_items:
            self._subnav_item(text, cmd, active=(self.ACTIVE_NAV == key))

        # Auto-expand if a content sub-page is active
        if self.ACTIVE_NAV in ("pending_articles", "categories", "activity_logs"):
            self.content_expanded = True
            self.content_frame.pack(fill="x", after=self.content_btn)
            if hasattr(self, "_content_chevron"):
                self._content_chevron.config(text="▴")

        # ── Spacer ────────────────────────────────────────────────────────────
        tk.Frame(self.sidebar, bg=T["card"]).pack(fill="both", expand=True)

        # ── Bottom strip ──────────────────────────────────────────────────────
        bottom = tk.Frame(self.sidebar, bg=T["background_alt"])
        bottom.pack(fill="x", side="bottom")
        tk.Frame(bottom, bg=T["border"], height=1).pack(fill="x")
        tk.Label(
            bottom,
            text="The Gears  •  Superadmin v1.0",
            bg=T["background_alt"], fg=T["text_light"],
            font=("Poppins", 7),
            pady=8,
        ).pack()

    def _section_label(self, text: str):
        T = self.theme
        row = tk.Frame(self.sidebar, bg=T["card"])
        row.pack(fill="x", padx=16, pady=(14, 2))
        tk.Label(
            row, text=text,
            bg=T["card"], fg=T["text_light"],
            font=("Poppins", 7, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Frame(row, bg=T["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(6, 0), pady=1,
        )

    def _nav_item(self, icon: str, label: str, cmd,
                  active=False, has_chevron=False):
        T = self.theme

        outer = tk.Frame(self.sidebar, bg=T["card"], cursor="hand2")
        outer.pack(fill="x", padx=8, pady=1)

        accent = tk.Frame(outer, width=3,
                          bg=T["primary_orange"] if active else T["card"])
        accent.pack(side="left", fill="y")

        inner = tk.Frame(
            outer,
            bg=T["primary_orange_light"] if active else T["card"],
            padx=12, pady=10,
        )
        inner.pack(side="left", fill="both", expand=True)

        icon_lbl = tk.Label(
            inner, text=icon,
            bg=T["primary_orange_light"] if active else T["card"],
            fg=T["primary_orange"] if active else T["text_grey"],
            font=("Poppins", 11),
        )
        icon_lbl.pack(side="left", padx=(0, 8))

        text_lbl = tk.Label(
            inner, text=label,
            bg=T["primary_orange_light"] if active else T["card"],
            fg=T["primary_orange"] if active else T["text_dark"],
            font=("Poppins", 10, "bold") if active else ("Poppins", 10),
            anchor="w",
        )
        text_lbl.pack(side="left", fill="x", expand=True)

        if has_chevron:
            self._content_chevron = tk.Label(
                inner, text="▾",
                bg=T["primary_orange_light"] if active else T["card"],
                fg=T["text_light"],
                font=("Poppins", 8),
            )
            self._content_chevron.pack(side="right")

        bg_normal = T["primary_orange_light"] if active else T["card"]
        bg_hover  = T["primary_orange_light"]

        def _on_enter(e):
            if not active:
                inner.config(bg=bg_hover)
                for w in inner.winfo_children():
                    try:
                        w.config(bg=bg_hover)
                    except Exception:
                        pass

        def _on_leave(e):
            if not active:
                inner.config(bg=bg_normal)
                for w in inner.winfo_children():
                    try:
                        w.config(bg=bg_normal)
                    except Exception:
                        pass

        for widget in [outer, inner, icon_lbl, text_lbl]:
            widget.bind("<Button-1>", lambda e, c=cmd: c())
            widget.bind("<Enter>",    _on_enter)
            widget.bind("<Leave>",    _on_leave)

        if has_chevron:
            self._content_chevron.bind("<Button-1>", lambda e: cmd())
            self._content_chevron.bind("<Enter>", _on_enter)
            self._content_chevron.bind("<Leave>", _on_leave)

        return outer

    def _subnav_item(self, text: str, cmd, active=False):
        T  = self.theme
        bg = T["primary_orange_light"] if active else T["background"]

        row = tk.Frame(self.content_frame, bg=bg, cursor="hand2")
        row.pack(fill="x")

        tk.Frame(row, bg=T["primary_orange"] if active else T["border"],
                 width=2).pack(side="left", fill="y", padx=(28, 0))

        dot = tk.Label(
            row, text="•",
            bg=bg,
            fg=T["primary_orange"] if active else T["text_light"],
            font=("Poppins", 8),
        )
        dot.pack(side="left", padx=(8, 6), pady=8)

        lbl = tk.Label(
            row, text=text,
            bg=bg,
            fg=T["primary_orange"] if active else T["text_grey"],
            font=("Poppins", 9, "bold") if active else ("Poppins", 9),
            anchor="w",
        )
        lbl.pack(side="left", fill="x", expand=True, pady=8)

        bg_hover = T["primary_orange_light"]

        def _enter(e):
            if not active:
                row.config(bg=bg_hover)
                dot.config(bg=bg_hover)
                lbl.config(bg=bg_hover)

        def _leave(e):
            if not active:
                row.config(bg=bg)
                dot.config(bg=bg)
                lbl.config(bg=bg)

        for w in [row, dot, lbl]:
            w.bind("<Button-1>", lambda e, c=cmd: c())
            w.bind("<Enter>",    _enter)
            w.bind("<Leave>",    _leave)

    def _toggle_content(self):
        self.content_expanded = not self.content_expanded
        if self.content_expanded:
            self.content_frame.pack(fill="x", after=self.content_btn)
            if hasattr(self, "_content_chevron"):
                self._content_chevron.config(text="▴")
        else:
            self.content_frame.pack_forget()
            if hasattr(self, "_content_chevron"):
                self._content_chevron.config(text="▾")

    def _draw_sidebar_avatar(self):
        T = self.theme
        c = self._sidebar_avatar_canvas
        c.delete("all")

        import os
        try:
            from PIL import Image, ImageTk, ImageDraw
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            src = self._profile.get("profile_image")
            if src:
                src  = src.replace("\\", "/")
                full = src if os.path.isabs(src) else os.path.join(project_root, src)
                full = os.path.normpath(full)
                if os.path.exists(full):
                    img  = Image.open(full).convert("RGBA").resize((36, 36))
                    mask = Image.new("L", (36, 36), 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, 35, 35), fill=255)
                    img.putalpha(mask)
                    self._sidebar_avatar_photo = ImageTk.PhotoImage(img)
                    c.create_image(0, 0, anchor="nw",
                                   image=self._sidebar_avatar_photo)
                    return
        except Exception:
            pass

        c.create_oval(1, 1, 35, 35, fill=T["primary_orange"], outline="")
        c.create_text(18, 18, text=self.initials,
                      fill="white", font=("Poppins", 10, "bold"))

    # ── User menu (dropdown from avatar) ─────────────────────────────────────

    def _make_user_menu(self):
        T = self.theme
        self.user_menu = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )

        # Header strip
        info = tk.Frame(self.user_menu, bg=T["primary_orange_light"], pady=14)
        info.pack(fill="x")

        av_row = tk.Frame(info, bg=T["primary_orange_light"])
        av_row.pack(fill="x", padx=14, pady=(0, 4))

        av = tk.Canvas(av_row, width=40, height=40,
                       bg=T["primary_orange_light"], highlightthickness=0)
        av.pack(side="left", padx=(0, 10))
        self._avatar_menu_canvas = av
        self._draw_user_menu_avatar()

        name_col = tk.Frame(av_row, bg=T["primary_orange_light"])
        name_col.pack(side="left", fill="x", expand=True)
        tk.Label(
            name_col, text=self.display_name,
            bg=T["primary_orange_light"], fg=T["text_dark"],
            font=("Poppins", 10, "bold"), anchor="w",
        ).pack(fill="x")
        email = self.user[2] if self.user and len(self.user) > 2 else ""
        tk.Label(
            name_col, text=email,
            bg=T["primary_orange_light"], fg=T["text_grey"],
            font=("Poppins", 8), anchor="w",
        ).pack(fill="x")

        tk.Frame(self.user_menu, bg=T["border"], height=1).pack(fill="x")

        moon = "🌙  Light Mode" if self.dark_mode else "🌙  Dark Mode"
        items = [
            ("👤  My Profile",  self._go_profile,      False),
            (moon,               self.toggle_dark_mode, False),
        ]
        for lbl, cmd, red in items:
            self._menu_item(lbl, cmd, red=red)

        tk.Frame(self.user_menu, bg=T["border"], height=1).pack(
            fill="x", padx=12, pady=2)

        self._menu_item("🚪  Logout", self._logout, red=True)

    def _menu_item(self, text: str, cmd, red=False):
        T  = self.theme
        fg = T["primary_red"] if red else T["text_dark"]
        bg = T["card"]

        row = tk.Frame(self.user_menu, bg=bg, cursor="hand2")
        row.pack(fill="x")

        lbl = tk.Label(
            row, text=text,
            bg=bg, fg=fg,
            font=("Poppins", 9, "bold") if red else ("Poppins", 9),
            anchor="w", padx=16, pady=10,
        )
        lbl.pack(fill="x")

        hover_bg = "#FFF4F4" if red else T["background_alt"]

        def _enter(e):
            row.config(bg=hover_bg)
            lbl.config(bg=hover_bg)

        def _leave(e):
            row.config(bg=bg)
            lbl.config(bg=bg)

        row.bind("<Button-1>", lambda e: cmd())
        lbl.bind("<Button-1>", lambda e: cmd())
        row.bind("<Enter>", _enter)
        row.bind("<Leave>", _leave)
        lbl.bind("<Enter>", _enter)
        lbl.bind("<Leave>", _leave)

    def _draw_user_menu_avatar(self):
        T = self.theme
        c = self._avatar_menu_canvas
        c.delete("all")

        import os
        try:
            from PIL import Image, ImageTk, ImageDraw
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            src = self._profile.get("profile_image")
            if src:
                src  = src.replace("\\", "/")
                full = src if os.path.isabs(src) else os.path.join(project_root, src)
                full = os.path.normpath(full)
                if os.path.exists(full):
                    img  = Image.open(full).convert("RGBA").resize((40, 40))
                    mask = Image.new("L", (40, 40), 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, 39, 39), fill=255)
                    img.putalpha(mask)
                    self._user_menu_avatar_photo = ImageTk.PhotoImage(img)
                    c.create_image(0, 0, anchor="nw",
                                   image=self._user_menu_avatar_photo)
                    return
        except Exception as e:
            print(f"[SuperadminLayout._draw_user_menu_avatar] {e}")

        c.create_oval(1, 1, 39, 39, fill=T["primary_orange"], outline="")
        c.create_text(20, 20, text=self.initials,
                      fill="white", font=("Poppins", 11, "bold"))

    def _maybe_close_user_menu(self, event):
        if not self.user_menu_visible:
            return
        try:
            mx, my = self.user_menu.winfo_rootx(), self.user_menu.winfo_rooty()
            mw, mh = self.user_menu.winfo_width(), self.user_menu.winfo_height()
            rx, ry = event.x_root, event.y_root
            if not (mx <= rx <= mx + mw and my <= ry <= my + mh):
                ax, ay = (self._avatar_canvas.winfo_rootx(),
                          self._avatar_canvas.winfo_rooty())
                aw, ah = (self._avatar_canvas.winfo_width(),
                          self._avatar_canvas.winfo_height())
                if not (ax <= rx <= ax + aw and ay <= ry <= ay + ah):
                    self.user_menu_visible = True
                    self.toggle_user_menu()
        except Exception:
            pass

    # ── Scrollable main shell ─────────────────────────────────────────────────

    def _make_main_shell(self):
        T  = self.theme
        rw = max(self.root.winfo_width(),  900)
        rh = max(self.root.winfo_height(), 600)

        self.main = tk.Frame(self.root, bg=T["background"])
        self.main.place(
            x=0, y=self.TOP_OFFSET,
            width=rw, height=rh - self.TOP_OFFSET,
        )

        outer = tk.Frame(self.main, bg=T["background"])
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg=T["background"], highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)

        self.content_frame_main = tk.Frame(self.canvas, bg=T["background"])
        self._cwin = self.canvas.create_window(
            (0, 0), window=self.content_frame_main, anchor="nw")

        self.content_frame_main.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._cwin, width=e.width),
        )
        self.canvas.bind(
            "<Enter>",
            lambda e: self.canvas.bind_all("<MouseWheel>", self._on_wheel),
        )
        self.canvas.bind(
            "<Leave>",
            lambda e: self.canvas.unbind_all("<MouseWheel>"),
        )

        self.inner = tk.Frame(self.content_frame_main, bg=T["background"])
        self.inner.pack(fill="both", expand=True, padx=36, pady=(28, 44))

    def _on_wheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _sync_geometry(self):
        try:
            if not (self.sidebar.winfo_exists() and self.main.winfo_exists()):
                return
            rw = self.root.winfo_width()
            rh = self.root.winfo_height()
            if rw < 100 or rh < 100:
                return
            bh = rh - self.TOP_OFFSET
            sx = 0 if self.sidebar_visible else -self.SIDEBAR_W
            self.sidebar.place_configure(
                x=sx, y=self.TOP_OFFSET, width=self.SIDEBAR_W, height=bh)
            mx = self.SIDEBAR_W if self.sidebar_visible else 0
            self.main.place_configure(
                x=mx, y=self.TOP_OFFSET, width=rw - mx, height=bh)
            self.header.lift()
            self.orange_bar.lift()
            if self.sidebar_visible:
                self.sidebar.lift()
            if self.user_menu_visible:
                self.user_menu.lift()
        except Exception:
            pass

    def _on_root_resize(self, event=None):
        if event and event.widget is not self.root:
            return
        self._sync_geometry()
        if self.user_menu_visible:
            try:
                rw = self.root.winfo_width()
                self.user_menu.place_configure(
                    x=rw - 248, y=self.TOP_OFFSET, width=240)
            except Exception:
                pass

    # ── Toggles ───────────────────────────────────────────────────────────────

    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        self._sync_geometry()

    def toggle_user_menu(self):
        self.user_menu_visible = not self.user_menu_visible
        if self.user_menu_visible:
            rw = self.root.winfo_width()
            self.user_menu.place(x=rw - 248, y=self.TOP_OFFSET, width=240)
            self.user_menu.lift()
        else:
            self.user_menu.place_forget()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.theme     = self.dark if self.dark_mode else self.light
        self._rebuild_chrome()

    # ── Binding cleanup ───────────────────────────────────────────────────────

    def _unbind_all(self):
        try:
            if self._bind_configure:
                self.root.unbind("<Configure>", self._bind_configure)
        except Exception:
            pass
        try:
            if self._bind_click:
                self.root.unbind("<Button-1>", self._bind_click)
        except Exception:
            pass
        self._bind_configure = None
        self._bind_click     = None

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _fetch_profile(self) -> dict:
        cb = self.callbacks.get("fetch_profile")
        if cb and self.user_id:
            try:
                result = cb(self.user_id)
                if result:
                    return result
            except Exception as exc:
                print(f"[SuperadminLayout] fetch_profile error: {exc}")
        return {
            "name":               self.display_name,
            "email":              self.user[2] if self.user and len(self.user) > 2 else "",
            "profile_image": None,
        }

    # ── Reusable panel helper ─────────────────────────────────────────────────

    def _panel(self, title: str) -> tk.Frame:
        T   = self.theme
        sec = tk.Frame(
            self.inner, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
            padx=22, pady=18,
        )
        sec.pack(fill="x", pady=(0, 16))
        tk.Label(
            sec, text=title.upper(),
            bg=T["card"], fg=T["primary_orange"],
            font=FONTS["section"],
        ).pack(anchor="w", pady=(0, 10))
        tk.Frame(sec, bg=T["border"], height=1).pack(fill="x", pady=(0, 12))
        return sec

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_dashboard(self):
        self._unbind_all()
        from utils.superadmin_navigation_helper import load_superadmin_dashboard
        load_superadmin_dashboard(self.root, self.user)

    def _go_manage_admins(self):
        self._unbind_all()
        from utils.superadmin_navigation_helper import load_manage_admins
        load_manage_admins(self.root, self.user)

    def _go_manage_users(self):
        self._unbind_all()
        from utils.superadmin_navigation_helper import load_manage_users
        load_manage_users(self.root, self.user)

    def _go_pending_articles(self):
        self._unbind_all()
        from utils.superadmin_navigation_helper import load_pending_articles
        load_pending_articles(self.root, self.user)

    def _go_categories(self):
        self._unbind_all()
        from utils.superadmin_navigation_helper import load_categories
        load_categories(self.root, self.user)

    def _go_activity_logs(self):
        self._unbind_all()
        from utils.superadmin_navigation_helper import load_activity_logs
        load_activity_logs(self.root, self.user)

    def _go_profile(self):
        self._unbind_all()
        from utils.superadmin_navigation_helper import load_superadmin_profile
        load_superadmin_profile(self.root, self.user)

    def _logout(self):
        self._unbind_all()
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            if hasattr(self.root, "show_landing"):
                self.root.show_landing()
            else:
                self.root.destroy()


# ── Standalone demo ────────────────────────────────────────────────────────────
if __name__ == "__main__":

    class DemoPage(SuperadminLayout):
        ACTIVE_NAV = "dashboard"

        def __init__(self, root, user=None, db_callbacks=None):
            super().__init__(root, user, db_callbacks)
            self._build_page()

        def _build_page(self):
            T = self.theme
            tk.Label(
                self.inner,
                text="Hi, this is a superadmin demo page 👋",
                bg=T["background"], fg=T["primary_orange"],
                font=("Poppins", 22, "bold"),
            ).pack(anchor="w")
            tk.Label(
                self.inner,
                text="Inherit SuperadminLayout and override _build_page() to build any superadmin page.",
                bg=T["background"], fg=T["text_grey"],
                font=FONTS["body"],
            ).pack(anchor="w", pady=(4, 20))

            sec = self._panel("Sample Panel")
            tk.Label(
                sec,
                text="Use self._panel('Title') for consistent card sections.",
                bg=T["card"], fg=T["text_mid"],
                font=FONTS["body"],
            ).pack(anchor="w")

    root = tk.Tk()
    root.title("The Gears — Superadmin Layout Demo")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    DemoPage(
        root,
        user=("Francis Jane", "Olvido", "admin@gears.com", 1, "superadmin"),
    )
    root.mainloop()