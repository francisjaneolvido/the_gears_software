"""
user/user_profile.py
─────────────────────
Profile page for regular users.

db_callbacks keys recognised:
  "update_profile"   → fn(user_id, name, email, avatar_path) → (bool, str)
  "change_password"  → fn(user_id, current_pw, new_pw)       → (bool, str)
  "delete_account"   → fn(user_id)                           → bool
  "fetch_categories" → fn()                                  → list[dict]

user tuple: (first_name, last_name, email, id, role, profile_image?, ...)
"""

import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from services.auth_services import update_profile, change_password

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Theme ─────────────────────────────────────────────────────────────────────
try:
    from theme import COLORS, FONTS
except ImportError:
    COLORS = {
        "primary_orange":       "#F5821F",
        "primary_orange_dark":  "#D97010",
        "primary_orange_light": "#FFF1DF",
        "background":           "#F9FAFB",
        "background_alt":       "#F3F4F6",
        "card":                 "#FFFFFF",
        "white":                "#FFFFFF",
        "text_dark":            "#1F2937",
        "text_mid":             "#374151",
        "text_grey":            "#6B7280",
        "text_light":           "#9CA3AF",
        "border":               "#E5E7EB",
        "navy":                 "#0C1633",
        "input_bg":             "#F9FAFB",
        "primary_red":          "#B91C1C",
        "shadow":               "#E8DDD5",
    }
    FONTS = {
        "body":       ("Poppins", 10),
        "body_bold":  ("Poppins", 10, "bold"),
        "small":      ("Poppins", 9),
        "small_bold": ("Poppins", 9, "bold"),
        "button":     ("Poppins", 9, "bold"),
        "tag":        ("Poppins", 8, "bold"),
        "heading":    ("Poppins", 14, "bold"),
        "section":    ("Poppins", 12, "bold"),
        "card_title": ("Poppins", 11, "bold"),
        "input":      ("Poppins", 10),
    }

DARK = {
    **COLORS,
    "background":           "#121212",
    "background_alt":       "#1E1E1E",
    "card":                 "#1E1E1E",
    "text_dark":            "#F0F0F0",
    "text_mid":             "#D1D5DB",
    "text_grey":            "#9CA3AF",
    "text_light":           "#6B7280",
    "border":               "#2D2D2D",
    "input_bg":             "#2A2A2A",
    "primary_orange_light": "#3A2210",
    "shadow":               "#0A0A0A",
    "white":                "#FFFFFF",
    "navy":                 "#080F22",
}

DANGER      = "#B91C1C"
DANGER_SOFT = "#FEF2F2"

HEADER_H     = 68
ORANGE_BAR_H = 4
FOOTER_H     = 52

DEFAULT_CATEGORIES = [
    "NEWS", "UPDATES", "OPINION", "FEATURE",
    "KOMIKS", "LITERARY", "PHOTOS", "VIDEOS",
]

CAT_ACCENT = {
    "NEWS":     "#FB923C",
    "UPDATES":  "#3B82F6",
    "OPINION":  "#A855F7",
    "FEATURE":  "#22C55E",
    "LITERARY": "#BE185D",
    "KOMIKS":   "#EF4444",
    "PHOTOS":   "#14B8A6",
    "VIDEOS":   "#6366F1",
}


# ─────────────────────────────────────────────────────────────────────────────
class UserProfilePage:

    def __init__(self, root, user=None, db_callbacks=None):
        self.root = root
        self.user = user or ()

        # Unified callbacks dict with sensible defaults
        self.callbacks = {
            "update_profile": lambda user_id, name, email, avatar_path=None:
                update_profile(user_id, name, "", email, avatar_path),
            "change_password": lambda user_id, cur_pw, new_pw:
                change_password(user_id, cur_pw, new_pw),
        }
        if db_callbacks:
            self.callbacks.update(db_callbacks)

        self.dark_mode       = False
        self.account_visible = False
        self._cat_menu       = None
        self._cat_filter     = "All"
        self._close_bind_id  = None

        self.light = COLORS.copy()
        self.dark  = DARK.copy()
        self.theme = self.light

        # ── User info ──────────────────────────────────────────────────────
        fn = str(self.user[0]) if len(self.user) > 0 else "User"
        ln = str(self.user[1]) if len(self.user) > 1 else ""
        self.initials      = (fn[:1] + ln[:1]).upper() or "U"
        self.display_name  = f"{fn} {ln}".strip()
        self.display_email = str(self.user[2]) if len(self.user) > 2 else ""
        self.user_id       = self.user[3] if len(self.user) > 3 else None
        self.avatar_path   = (str(self.user[5])
                              if len(self.user) > 5 and self.user[5] else None)
        self._refresh_avatar_from_server()

        # Mutable state
        self._pending_avatar = None
        self._avatar_photo   = None
        self._nav_avatar_photo = None

        # Categories
        self._categories     = self._fetch_categories()
        self._category_names = [
            str(c.get("name", "")).strip()
            for c in self._categories
            if str(c.get("name", "")).strip()
        ]

        # Dirty-tracking baselines
        self._initial_name  = self.display_name
        self._initial_email = self.display_email
        self._dirty         = False

        self._build_ui()
        self.root.bind("<Configure>", self._on_resize)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _refresh_avatar_from_server(self):
        """Fetch the latest profile_image from Flask so web-side changes show up."""
        if not self.user_id:
            return
        try:
            import urllib.request, json as _json
            from dotenv import load_dotenv
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
            FLASK_URL = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
            url = f"{FLASK_URL}/mobile/profile/{self.user_id}"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = _json.loads(resp.read())
            if data.get("success") and data.get("user", {}).get("profile_image"):
                server_pic = data["user"]["profile_image"]
                if server_pic and server_pic != self.avatar_path:
                    self.avatar_path = server_pic
        except Exception as e:
            print(f"[UserProfile] refresh avatar skipped: {e}")

    def _fetch_categories(self) -> list:
        cb = self.callbacks.get("fetch_categories")
        if cb:
            try:
                rows   = cb() or []
                active = [c for c in rows if not c.get("archived")]
                if active:
                    return active
            except Exception as e:
                print(f"[UserProfilePage] fetch_categories: {e}")
        return [
            {"name": n, "icon": "",
             "color": CAT_ACCENT.get(n, COLORS["primary_orange"]),
             "archived": False}
            for n in DEFAULT_CATEGORIES
        ]

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        T = self.theme
        self.root.configure(bg=T["background"])
        self._make_navbar()
        self._make_footer()
        self._make_body()
        self.navbar.lift()
        self.footer.lift()

    def _rebuild(self):
        self.account_visible = False
        self._cat_menu       = None
        self._close_bind_id  = None
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()

    # ── Navbar ────────────────────────────────────────────────────────────────

    def _make_navbar(self):
        T = self.theme

        self.navbar = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        self.navbar.place(x=0, y=0, relwidth=1, height=HEADER_H)

        # ── Left: Logo ─────────────────────────────────────────────────────
        left = tk.Frame(self.navbar, bg=T["card"])
        left.pack(side="left", fill="y", padx=(20, 0))

        logo = tk.Canvas(left, width=34, height=34,
                         bg=T["card"], highlightthickness=0)
        logo.pack(side="left", anchor="center")
        logo.create_oval(1, 1, 33, 33,
                         fill=T["primary_orange"], outline=T["primary_orange"])
        logo.create_text(17, 17, text="TG", fill="white",
                         font=("Poppins", 9, "bold"))

        tk.Label(
            left, text="The Gears",
            bg=T["card"], fg=T["primary_orange"],
            font=("Poppins", 15, "bold"),
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            left, text="  ·  Profile",
            bg=T["card"], fg=T["text_grey"],
            font=("Poppins", 9),
        ).pack(side="left")

        # ── Right: Dark-mode toggle + avatar ───────────────────────────────
        right = tk.Frame(self.navbar, bg=T["card"])
        right.pack(side="right", fill="y", padx=(0, 22))

        self._dark_btn = tk.Button(
            right,
            text="🌙" if not self.dark_mode else "☀️",
            command=self._toggle_dark,
            bg=T["card"], fg=T["text_grey"],
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"],
            font=("Poppins", 13),
            bd=0, relief="flat", cursor="hand2",
            padx=6, pady=4,
        )
        self._dark_btn.pack(side="left", padx=(0, 10))

        tk.Frame(right, bg=T["border"], width=1, height=26).pack(
            side="left", padx=(0, 10), pady=20)

        av_frame = tk.Frame(right, bg=T["card"], cursor="hand2")
        av_frame.pack(side="left")

        # Single canvas for the nav avatar (fixed duplicate bug)
        self._av_canvas = tk.Canvas(
            av_frame, width=34, height=34,
            bg=T["card"], highlightthickness=0, cursor="hand2",
        )
        self._av_canvas.pack(side="left")
        self._draw_nav_avatar()
        self._av_canvas.bind("<Button-1>", lambda e: self._toggle_account_menu())
        av_frame.bind("<Button-1>",        lambda e: self._toggle_account_menu())

        self._chevron_lbl = tk.Label(
            av_frame, text="▾",
            bg=T["card"], fg=T["text_grey"],
            font=("Poppins", 8), cursor="hand2",
        )
        self._chevron_lbl.pack(side="left", padx=(3, 0))
        self._chevron_lbl.bind("<Button-1>", lambda e: self._toggle_account_menu())

        # ── Center: Nav links + search ─────────────────────────────────────
        center = tk.Frame(self.navbar, bg=T["card"])
        center.place(relx=0.5, rely=0.5, anchor="center")

        home_lbl = tk.Label(
            center, text="Home",
            bg=T["card"], fg=T["text_grey"],
            font=("Poppins", 10), cursor="hand2", padx=8,
        )
        home_lbl.pack(side="left", pady=20, padx=4)
        home_lbl.bind("<Button-1>", lambda e: self._go_home())
        home_lbl.bind("<Enter>", lambda e: home_lbl.config(fg=T["text_dark"]))
        home_lbl.bind("<Leave>", lambda e: home_lbl.config(fg=T["text_grey"]))

        self._cat_btn_var    = tk.StringVar(value="Category  ▾")
        self._cat_btn_widget = tk.Button(
            center,
            textvariable=self._cat_btn_var,
            command=self._toggle_cat_menu,
            bg=T["card"], fg=T["text_grey"],
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"],
            font=("Poppins", 10),
            bd=0, relief="flat", cursor="hand2",
            padx=8, pady=4,
        )
        self._cat_btn_widget.pack(side="left", padx=4, pady=20)

        for text in ("About", "Contact"):
            lbl = tk.Label(
                center, text=text,
                bg=T["card"], fg=T["text_grey"],
                font=("Poppins", 10), cursor="hand2", padx=8,
            )
            lbl.pack(side="left", padx=4, pady=20)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=T["text_dark"]))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=T["text_grey"]))

        PLACEHOLDER  = "Search articles..."
        search_wrap  = tk.Frame(center, bg=T["border"])
        search_wrap.pack(side="left", padx=(20, 0), pady=20)
        search_inner = tk.Frame(search_wrap, bg=T["input_bg"])
        search_inner.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(
            search_inner, text="🔍",
            bg=T["input_bg"], fg=T["text_grey"],
            font=("Poppins", 9),
        ).pack(side="left", padx=(6, 0))

        self._search_var   = tk.StringVar()
        self._search_entry = tk.Entry(
            search_inner, textvariable=self._search_var,
            font=("Poppins", 9), bg=T["input_bg"], fg=T["text_light"],
            relief="flat", bd=0, width=18,
            insertbackground=T["primary_orange"],
        )
        self._search_entry.pack(side="left", ipady=5, padx=(2, 8))
        self._search_entry.insert(0, PLACEHOLDER)

        def _focus_in(e):
            if self._search_entry.get() == PLACEHOLDER:
                self._search_entry.delete(0, "end")
                self._search_entry.config(fg=T["text_dark"])

        def _focus_out(e):
            if not self._search_entry.get().strip():
                self._search_entry.insert(0, PLACEHOLDER)
                self._search_entry.config(fg=T["text_light"])

        self._search_entry.bind("<FocusIn>",  _focus_in)
        self._search_entry.bind("<FocusOut>", _focus_out)
        self._search_entry.bind(
            "<Return>",
            lambda e: self._go_home_search(self._search_var.get()),
        )

        # Orange accent bar below navbar
        self.orange_bar = tk.Frame(self.root, bg=T["primary_orange"])
        self.orange_bar.place(x=0, y=HEADER_H, relwidth=1, height=ORANGE_BAR_H)

        # Build but don't show account dropdown yet
        self._account_menu = self._build_account_menu()

    # ── Account dropdown ──────────────────────────────────────────────────────

    def _build_account_menu(self):
        T    = self.theme
        menu = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )

        # Header strip
        hdr = tk.Frame(menu, bg=T["primary_orange_light"], pady=10)
        hdr.pack(fill="x")

        av_row = tk.Frame(hdr, bg=T["primary_orange_light"])
        av_row.pack(fill="x", padx=12, pady=(0, 4))

        mini_av = tk.Canvas(av_row, width=30, height=30,
                            bg=T["primary_orange_light"], highlightthickness=0)
        mini_av.pack(side="left", padx=(0, 8))
        mini_av.create_oval(1, 1, 29, 29,
                            fill=T["primary_orange"], outline=T["primary_orange"])
        mini_av.create_text(15, 15, text=self.initials,
                            fill="white", font=("Poppins", 8, "bold"))

        col = tk.Frame(av_row, bg=T["primary_orange_light"])
        col.pack(side="left")
        tk.Label(col, text=self.display_name,
                 bg=T["primary_orange_light"], fg=T["text_dark"],
                 font=("Poppins", 9, "bold"), anchor="w").pack(anchor="w")
        tk.Label(col, text=self.display_email,
                 bg=T["primary_orange_light"], fg=T["text_grey"],
                 font=("Poppins", 8), anchor="w").pack(anchor="w")

        tk.Frame(menu, bg=T["border"], height=1).pack(fill="x")

        items = [
            ("👤  My Profile", True,  self._go_to_profile),
            ("🚪  Logout",     False, self._logout),
        ]
        for text, is_orange, cmd in items:
            fg     = T["primary_red"] if is_orange else T["text_dark"]
            fg_act = T["primary_red"] if is_orange else T["primary_orange"]
            tk.Button(
                menu, text=text, command=cmd,
                anchor="w", bg=T["card"], fg=fg,
                activebackground=T["primary_orange_light"],
                activeforeground=fg_act,
                font=("Poppins", 9, "bold") if is_orange else ("Poppins", 9),
                bd=0, relief="flat", padx=14, pady=9, cursor="hand2",
            ).pack(fill="x")
            tk.Frame(menu, bg=T["border"], height=1).pack(fill="x")

        return menu

    def _go_to_profile(self):
        """Navigate to the user profile page."""
        self._close_account_menu()
        if hasattr(self.root, "show_user_profile"):
            self.root.show_user_profile(self.user)
        # If already on profile page, just close the menu

    def _toggle_account_menu(self):
        self.account_visible = not self.account_visible
        if self.account_visible:
            rw = self.root.winfo_width()
            self._account_menu.place(
                x=rw - 222, y=HEADER_H + ORANGE_BAR_H + 2, width=210,
            )
            self._account_menu.lift()
            self._close_bind_id = self.root.bind(
                "<Button-1>", self._close_account_on_click, add="+",
            )
        else:
            self._close_account_menu()

    def _close_account_menu(self):
        """Hide the account menu and clean up the click-away binding."""
        self.account_visible = False
        self._account_menu.place_forget()
        if self._close_bind_id:
            try:
                self.root.unbind("<Button-1>", self._close_bind_id)
            except Exception:
                pass
            self._close_bind_id = None

    def _close_account_on_click(self, event):
        """Dismiss account menu when clicking outside it."""
        w = event.widget
        while w:
            if w is self._account_menu or w is self._av_canvas:
                return
            w = getattr(w, "master", None)
        self._close_account_menu()

    # ── Category dropdown ─────────────────────────────────────────────────────

    def _toggle_cat_menu(self):
        T = self.theme
        if self._cat_menu and self._cat_menu.winfo_exists():
            self._cat_menu.destroy()
            self._cat_menu = None
            self._cat_btn_var.set("Category  ▾")
            return

        self._cat_btn_var.set("Category  ▴")
        menu = tk.Toplevel(self.root)
        menu.overrideredirect(True)
        menu.configure(bg=T["card"])
        menu.attributes("-topmost", True)
        self._cat_menu = menu

        self.root.update_idletasks()
        bx = self._cat_btn_widget.winfo_rootx()
        by = (self._cat_btn_widget.winfo_rooty()
              + self._cat_btn_widget.winfo_height())

        MENU_W = 210
        outer  = tk.Frame(menu, bg=T["card"],
                          highlightthickness=1,
                          highlightbackground=T["border"], bd=0)
        outer.pack(fill="both", expand=True)

        items = [("All categories", "All")] + [
            (c, c) for c in self._category_names
        ]

        def _pick(v):
            if menu.winfo_exists():
                menu.destroy()
            self._cat_menu = None
            self._cat_btn_var.set("Category  ▾")
            self._go_home_with_cat(v)

        for label, val in items:
            is_active = (val == self._cat_filter)
            bg = T["primary_orange_light"] if is_active else T["card"]
            fg = T["primary_orange"]       if is_active else T["text_dark"]

            row = tk.Frame(outer, bg=bg, cursor="hand2")
            row.pack(fill="x")

            if is_active:
                tk.Frame(row, bg=T["primary_orange"], width=3).pack(
                    side="left", fill="y")

            lbl = tk.Label(
                row, text=label, bg=bg, fg=fg,
                anchor="w", padx=14, pady=9,
                font=("Poppins", 9, "bold") if is_active else ("Poppins", 9),
            )
            lbl.pack(fill="x", side="left", expand=True)

            hover_bg = T["background_alt"]
            for widget in (row, lbl):
                widget.bind("<Enter>",
                    lambda e, r=row, b=lbl, a=is_active, h=hover_bg: (
                        None if a else (r.config(bg=h), b.config(bg=h))))
                widget.bind("<Leave>",
                    lambda e, r=row, b=lbl, a=is_active, _bg=bg: (
                        None if a else (r.config(bg=_bg), b.config(bg=_bg))))
                widget.bind("<Button-1>", lambda e, v=val: _pick(v))

            tk.Frame(outer, bg=T["border"], height=1).pack(fill="x")

        menu.update_idletasks()
        h = min(outer.winfo_reqheight(), 360)
        menu.geometry(f"{MENU_W}x{h}+{bx}+{by}")

        # Dismiss on click outside via root binding (more reliable than FocusOut)
        def _dismiss_cat(e=None):
            if self._cat_menu and self._cat_menu.winfo_exists():
                self._cat_menu.destroy()
                self._cat_menu = None
                self._cat_btn_var.set("Category  ▾")

        # Bind click-away on root; remove after dismiss
        _bind_id = [None]

        def _cat_click_away(e):
            w = e.widget
            while w:
                if w is menu:
                    return
                w = getattr(w, "master", None)
            _dismiss_cat()
            try:
                self.root.unbind("<Button-1>", _bind_id[0])
            except Exception:
                pass

        _bind_id[0] = self.root.bind("<Button-1>", _cat_click_away, add="+")

    # ── Body ──────────────────────────────────────────────────────────────────

    def _make_body(self):
        T  = self.theme
        rw = max(self.root.winfo_width(),  900)
        rh = max(self.root.winfo_height(), 600)

        self.body = tk.Frame(self.root, bg=T["background"])
        self.body.place(
            x=0, y=HEADER_H + ORANGE_BAR_H,
            width=rw,
            height=rh - HEADER_H - ORANGE_BAR_H - FOOTER_H,
        )

        outer = tk.Frame(self.body, bg=T["background"])
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg=T["background"], highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)

        self.content = tk.Frame(self.canvas, bg=T["background"])
        self._cwin   = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw")

        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
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

        self._make_profile_content()

    def _on_wheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── Profile content ───────────────────────────────────────────────────────

    def _make_profile_content(self):
        T = self.theme

        wrap = tk.Frame(self.content, bg=T["background"])
        wrap.pack(fill="both", expand=True, padx=48, pady=36)

        # Page heading
        heading_row = tk.Frame(wrap, bg=T["background"])
        heading_row.pack(anchor="w", fill="x", pady=(0, 4))

        tk.Frame(heading_row, bg=T["primary_orange"], width=4, height=32).pack(
            side="left", anchor="w", padx=(0, 12))
        hdr_col = tk.Frame(heading_row, bg=T["background"])
        hdr_col.pack(side="left")
        tk.Label(hdr_col, text="Your Profile",
                 bg=T["background"], fg=T["text_dark"],
                 font=("Poppins", 20, "bold")).pack(anchor="w")

        tk.Label(wrap,
                 text="Manage your personal information, security settings, and account preferences.",
                 bg=T["background"], fg=T["text_grey"],
                 font=("Poppins", 9)).pack(anchor="w", pady=(0, 24))

        # Thin separator
        tk.Frame(wrap, bg=T["border"], height=1).pack(fill="x", pady=(0, 28))

        grid = tk.Frame(wrap, bg=T["background"])
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=0, minsize=300)
        grid.columnconfigure(1, weight=1)

        left_col  = tk.Frame(grid, bg=T["background"])
        left_col.grid(row=0, column=0, sticky="nw", padx=(0, 24))
        right_col = tk.Frame(grid, bg=T["background"])
        right_col.grid(row=0, column=1, sticky="nsew")

        self._section_label(left_col,  "Profile Photo")
        self._make_avatar_card(left_col)

        self._section_label(right_col, "Account & Security")
        self._make_account_info_card(right_col)
        self._make_password_card(right_col)
        self._make_save_card(right_col)
        self._make_danger_card(right_col)

    def _section_label(self, parent, text):
        T = self.theme
        row = tk.Frame(parent, bg=T["background"])
        row.pack(anchor="w", fill="x", pady=(0, 8))
        tk.Label(row, text=text.upper(),
                bg=T["background"], fg=T["text_light"],
                font=("Poppins", 8, "bold")).pack(side="left")
        tk.Frame(row, bg=T["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(10, 0))

    def _card(self, parent, title, subtitle, danger=False):
        T  = self.theme
        if danger:
            bg = "#2A1010" if self.dark_mode else DANGER_SOFT
        else:
            bg = T["card"]

        # Outer shadow effect via a slightly-offset frame
        shadow = tk.Frame(parent, bg=T["shadow"] if not self.dark_mode else "#000000")
        shadow.pack(fill="x", pady=(0, 18), padx=(0, 0))

        card = tk.Frame(
            shadow, bg=bg,
            highlightbackground=T["border"], highlightthickness=1,
        )
        card.pack(fill="x", padx=0, pady=0)

        inner = tk.Frame(card, bg=bg)
        inner.pack(fill="both", expand=True, padx=22, pady=20)

        # Title row with accent line
        title_row = tk.Frame(inner, bg=bg)
        title_row.pack(anchor="w", fill="x", pady=(0, 2))

        title_fg = DANGER if danger else T["primary_orange"]
        tk.Label(title_row, text=title, bg=bg,
                 fg=title_fg, font=("Poppins", 12, "bold")).pack(
            side="left", anchor="w")

        tk.Label(inner, text=subtitle, bg=bg,
                 fg=T["text_grey"], font=("Poppins", 8)).pack(
            anchor="w", pady=(0, 14))

        return inner, bg

    # ── Avatar card ───────────────────────────────────────────────────────────

    def _make_avatar_card(self, parent):
        T = self.theme
        inner, bg = self._card(
            parent, "Profile Photo",
            "Your photo and initials appear on your articles.",
        )

        center = tk.Frame(inner, bg=bg)
        center.pack(fill="x")

        # Avatar circle with a styled ring
        av_wrap = tk.Frame(center, bg=T["primary_orange"], padx=2, pady=2)
        av_wrap.pack(pady=(4, 0))
        self._av_big = tk.Canvas(
            av_wrap, width=96, height=96,
            bg=bg, highlightthickness=0, cursor="hand2",
        )
        self._av_big.pack()
        self._av_big.bind("<Button-1>", self._open_avatar_modal)
        self._draw_big_avatar()

        tk.Label(
            center,
            text="Click to preview · Recommended 400×400px, JPG/PNG up to 2 MB",
            bg=bg, fg=T["text_light"],
            font=("Poppins", 8), wraplength=240, justify="center",
        ).pack(pady=(8, 4))

        self._file_name_var = tk.StringVar(value="No file selected")
        tk.Label(center, textvariable=self._file_name_var,
                 bg=bg, fg=T["text_grey"],
                 font=("Poppins", 8)).pack(pady=(0, 4))

        btn_row = tk.Frame(center, bg=bg)
        btn_row.pack(pady=8)

        choose_btn = tk.Button(
            btn_row, text="📁  Choose Photo",
            command=self._choose_photo,
            bg=T["primary_orange"], fg="white",
            activebackground=T["primary_orange_dark"], activeforeground="white",
            font=("Poppins", 9, "bold"), bd=0, relief="flat",
            padx=14, pady=7, cursor="hand2",
        )
        choose_btn.pack(side="left", padx=(0, 8))

        reset_btn = tk.Button(
            btn_row, text="↺  Reset",
            command=self._reset_photo,
            bg=T["background_alt"], fg=T["text_grey"],
            activebackground=T["border"],
            font=("Poppins", 9), bd=0, relief="flat",
            padx=10, pady=6, cursor="hand2",
        )
        reset_btn.pack(side="left")

    # ── Avatar drawing helpers ────────────────────────────────────────────────

    def _resolve_image(self, src, size):
        """Try to load an image from local paths then Flask. Returns PIL Image or None."""
        import io as _io, urllib.request
        try:
            from PIL import Image
        except ImportError:
            return None

        if not src:
            return None

        src = str(src).strip().replace("\\", "/")
        filename = src.split("/")[-1]

        try:
            from dotenv import load_dotenv
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
        except Exception:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        FLASK_URL = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
        project_root = BASE_DIR

        candidates = [
            src if os.path.isabs(src) else os.path.join(project_root, src),
            os.path.join(project_root, "static", "uploads", "avatars", filename),
            os.path.join(project_root, "static", "uploads", filename),
            os.path.join(project_root, "uploads", "avatars", filename),
            os.path.join(project_root, "uploads", filename),
        ]
        for path in candidates:
            path = os.path.normpath(path)
            if os.path.exists(path):
                try:
                    return Image.open(path).convert("RGBA").resize((size, size))
                except Exception as e:
                    print(f"[Avatar] local error {path}: {e}")

        for url in [
            f"{FLASK_URL}/static/uploads/avatars/{filename}",
            f"{FLASK_URL}/static/uploads/{filename}",
        ]:
            try:
                with urllib.request.urlopen(url, timeout=8) as resp:
                    img = Image.open(_io.BytesIO(resp.read())).convert("RGBA").resize((size, size))
                print(f"[Avatar] ✅ Fetched: {url}")
                return img
            except Exception:
                pass

        return None

    def _apply_circle_mask(self, img):
        """Apply a circular mask to a PIL image."""
        from PIL import Image, ImageDraw
        size = img.size[0]
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        img.putalpha(mask)
        return img

    def _draw_nav_avatar(self):
        T  = self.theme
        av = self._av_canvas
        av.delete("all")

        src   = self._pending_avatar or self.avatar_path
        image = self._resolve_image(src, 34)

        if image:
            try:
                from PIL import ImageTk
                image = self._apply_circle_mask(image)
                self._nav_avatar_photo = ImageTk.PhotoImage(image)
                av.create_image(0, 0, anchor="nw", image=self._nav_avatar_photo)
                return
            except Exception as e:
                print(f"[NavAvatar] render error: {e}")

        av.create_oval(1, 1, 33, 33,
                       fill=T["primary_orange"], outline=T["primary_orange"])
        av.create_text(17, 17, text=self.initials,
                       fill="white", font=("Poppins", 9, "bold"))

    def _draw_big_avatar(self):
        T  = self.theme
        av = self._av_big
        av.delete("all")

        image = None
        for src in (self._pending_avatar, self.avatar_path):
            image = self._resolve_image(src, 96)
            if image:
                break

        if image:
            try:
                from PIL import ImageTk
                image = self._apply_circle_mask(image)
                self._avatar_photo = ImageTk.PhotoImage(image)
                av.create_image(0, 0, anchor="nw", image=self._avatar_photo)
                return
            except Exception as e:
                print(f"[BigAvatar] render error: {e}")

        av.create_oval(1, 1, 95, 95,
                       fill=T["primary_orange"], outline=T["primary_orange"])
        av.create_text(48, 48, text=self.initials,
                       fill="white", font=("Poppins", 28, "bold"))

    def _open_avatar_modal(self, e=None):
        src = self._pending_avatar or self.avatar_path
        if not src:
            return

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = src if os.path.isabs(src) else os.path.join(project_root, src)

        if not os.path.exists(full_path):
            print(f"[Avatar Modal] File not found: {full_path}")
            return

        try:
            from PIL import Image, ImageTk
        except ImportError:
            messagebox.showinfo("Avatar", f"Image path:\n{full_path}")
            return

        T     = self.theme
        modal = tk.Toplevel(self.root)
        modal.title("Profile Photo Preview")
        modal.configure(bg="#0A0A0A")
        modal.attributes("-topmost", True)
        modal.grab_set()
        modal.resizable(False, False)

        try:
            img   = Image.open(full_path)
            img.thumbnail((520, 520))
            photo = ImageTk.PhotoImage(img)
            lbl   = tk.Label(modal, image=photo, bg="#0A0A0A")
            lbl._photo = photo
            lbl.pack(padx=24, pady=(24, 12))
        except Exception as ex:
            tk.Label(modal, text=str(ex), fg="white", bg="#0A0A0A").pack(
                padx=20, pady=20)

        tk.Button(
            modal, text="✕  Close",
            command=modal.destroy,
            bg=T["primary_orange"], fg="white",
            font=("Poppins", 9, "bold"),
            bd=0, relief="flat", padx=16, pady=7,
            cursor="hand2",
        ).pack(pady=(0, 20))

    def _choose_photo(self):
        path = filedialog.askopenfilename(
            title="Select Profile Photo",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._pending_avatar = path
            short = os.path.basename(path)
            self._file_name_var.set(
                short if len(short) <= 30 else "…" + short[-27:])
            self._draw_big_avatar()
            self._mark_dirty()

    def _reset_photo(self):
        self._pending_avatar = None
        self._file_name_var.set("No file selected")
        self._draw_big_avatar()
        self._check_dirty()

    # ── Account info card ─────────────────────────────────────────────────────

    def _make_account_info_card(self, parent):
        T = self.theme
        inner, bg = self._card(
            parent, "Account Information",
            "Keep your profile information up to date.",
        )

        # Name
        tk.Label(inner, text="Full Name", bg=bg, fg=T["text_grey"],
                 font=("Poppins", 9, "bold")).pack(anchor="w", pady=(4, 2))
        self._name_var   = tk.StringVar(value=self.display_name)
        self._name_entry = self._entry(inner, bg, self._name_var)
        self._name_var.trace_add("write", lambda *_: self._check_dirty())

        # Email
        tk.Label(inner, text="Email Address", bg=bg, fg=T["text_grey"],
                 font=("Poppins", 9, "bold")).pack(anchor="w", pady=(10, 2))
        self._email_var   = tk.StringVar(value=self.display_email)
        self._email_entry = self._entry(inner, bg, self._email_var)
        self._email_var.trace_add("write", lambda *_: self._check_dirty())

        tk.Label(
            inner,
            text="Account-related notifications will be sent to this address.",
            bg=bg, fg=T["text_light"], font=("Poppins", 8),
        ).pack(anchor="w", pady=(2, 4))

    # ── Password card ─────────────────────────────────────────────────────────

    def _make_password_card(self, parent):
        T = self.theme
        inner, bg = self._card(
            parent, "Change Password",
            "Use a strong, unique password to keep your account secure.",
        )

        # Current password
        tk.Label(inner, text="Current Password", bg=bg, fg=T["text_grey"],
                 font=("Poppins", 9, "bold")).pack(anchor="w", pady=(4, 2))
        self._cur_pw_var = tk.StringVar()
        row_cur = tk.Frame(inner, bg=bg)
        row_cur.pack(fill="x")
        self._cur_pw_entry = self._entry(row_cur, bg, self._cur_pw_var,
                                         show="•", expand=True)
        self._cur_pw_var.trace_add("write", lambda *_: self._check_dirty())
        self._pw_toggle_btn(row_cur, self._cur_pw_entry, bg)

        tk.Label(
            inner, text="Required only when changing your password.",
            bg=bg, fg=T["text_light"], font=("Poppins", 8),
        ).pack(anchor="w", pady=(2, 10))

        # New / confirm row
        pw_row = tk.Frame(inner, bg=bg)
        pw_row.pack(fill="x")
        pw_row.columnconfigure(0, weight=1)
        pw_row.columnconfigure(1, weight=1)

        left_pw = tk.Frame(pw_row, bg=bg)
        left_pw.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        tk.Label(left_pw, text="New Password", bg=bg, fg=T["text_grey"],
                 font=("Poppins", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self._new_pw_var = tk.StringVar()
        row_new = tk.Frame(left_pw, bg=bg)
        row_new.pack(fill="x")
        self._new_pw_entry = self._entry(row_new, bg, self._new_pw_var,
                                          show="•", expand=True)
        self._pw_toggle_btn(row_new, self._new_pw_entry, bg)

        # Strength bar
        bar_bg = tk.Frame(left_pw, bg=T["border"], height=4)
        bar_bg.pack(fill="x", pady=(5, 0))
        self._strength_bar = tk.Frame(bar_bg, bg=T["border"], height=4)
        self._strength_bar.place(x=0, y=0, relheight=1, relwidth=0)
        self._strength_lbl = tk.Label(left_pw, text="",
                                       bg=bg, fg=T["text_grey"],
                                       font=("Poppins", 8))
        self._strength_lbl.pack(anchor="w", pady=(3, 0))

        self._new_pw_var.trace_add(
            "write",
            lambda *_: (self._update_strength(), self._check_dirty()),
        )

        right_pw = tk.Frame(pw_row, bg=bg)
        right_pw.grid(row=0, column=1, sticky="ew")

        tk.Label(right_pw, text="Confirm New Password", bg=bg, fg=T["text_grey"],
                 font=("Poppins", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self._conf_pw_var = tk.StringVar()
        row_conf = tk.Frame(right_pw, bg=bg)
        row_conf.pack(fill="x")
        self._conf_pw_entry = self._entry(row_conf, bg, self._conf_pw_var,
                                           show="•", expand=True)
        self._pw_toggle_btn(row_conf, self._conf_pw_entry, bg)

        self._match_lbl = tk.Label(right_pw, text="",
                                    bg=bg, fg=T["text_grey"],
                                    font=("Poppins", 8))
        self._match_lbl.pack(anchor="w", pady=(5, 0))

        self._conf_pw_var.trace_add(
            "write",
            lambda *_: (self._update_match(), self._check_dirty()),
        )

        tk.Label(
            inner,
            text="Minimum 8 characters — mix letters and numbers for a stronger password.",
            bg=bg, fg=T["text_light"], font=("Poppins", 8),
        ).pack(anchor="w", pady=(12, 0))

    def _update_strength(self):
        val = self._new_pw_var.get()
        if not val:
            self._strength_lbl.config(text="")
            self._strength_bar.place_configure(relwidth=0)
            return
        if len(val) < 6:
            text, color, w = "Strength: Weak",   "#E63946", 0.33
        elif len(val) < 10:
            text, color, w = "Strength: Fair",   "#F6A609", 0.66
        else:
            text, color, w = "Strength: Strong", "#1B873F", 1.0
        self._strength_lbl.config(text=text, fg=color)
        self._strength_bar.config(bg=color)
        self._strength_bar.place_configure(relwidth=w)

    def _update_match(self):
        new_  = self._new_pw_var.get()
        conf_ = self._conf_pw_var.get()
        if not new_ and not conf_:
            self._match_lbl.config(text="")
        elif new_ and conf_ and new_ == conf_:
            self._match_lbl.config(text="✔ Passwords match", fg="#1B873F")
        elif conf_:
            self._match_lbl.config(text="✗ Passwords do not match", fg="#E63946")
        else:
            self._match_lbl.config(text="")

    # ── Save card ─────────────────────────────────────────────────────────────

    def _make_save_card(self, parent):
        T = self.theme
        inner, bg = self._card(parent, "Save Changes",
                               "Review your updates before applying them.")

        btn_row = tk.Frame(inner, bg=bg)
        btn_row.pack(anchor="w", pady=(4, 0))

        self._save_btn = tk.Button(
            btn_row, text="💾  Save Changes",
            command=self._save_profile,
            bg=T["primary_orange"], fg="white",
            activebackground=T["primary_orange_dark"],
            activeforeground="white",
            font=("Poppins", 10, "bold"),
            bd=0, relief="flat", padx=18, pady=9,
            cursor="hand2", state="disabled",
            disabledforeground="#FFDAB0",
        )
        self._save_btn.pack(side="left", padx=(0, 10))

        tk.Button(
            btn_row, text="↺  Reset",
            command=self._reset_form,
            bg=T["background_alt"], fg=T["text_grey"],
            activebackground=T["border"],
            font=("Poppins", 9), bd=0, relief="flat",
            padx=12, pady=8, cursor="hand2",
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row, text="Cancel",
            command=self._go_home,
            bg=T["background_alt"], fg=T["text_grey"],
            activebackground=T["border"],
            font=("Poppins", 9), bd=0, relief="flat",
            padx=12, pady=8, cursor="hand2",
        ).pack(side="left")

    # ── Danger card ───────────────────────────────────────────────────────────

    def _make_danger_card(self, parent):
        inner, bg = self._card(
            parent, "Danger Zone",
            "Deleting your account is permanent and cannot be undone.",
            danger=True,
        )

        row = tk.Frame(inner, bg=bg)
        row.pack(fill="x")

        tk.Label(
            row,
            text="Once deleted, all your data — articles, comments, and settings — "
                 "will be permanently removed.",
            bg=bg, fg=DANGER, font=("Poppins", 8),
            wraplength=460, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)

        tk.Button(
            row, text="🗑  Delete Account",
            command=self._delete_account,
            bg=DANGER, fg="white",
            activebackground="#9B1C1C", activeforeground="white",
            font=("Poppins", 9, "bold"),
            bd=0, relief="flat", padx=14, pady=8, cursor="hand2",
        ).pack(side="right", anchor="e", padx=(12, 0))

    # ── Form helpers ──────────────────────────────────────────────────────────

    def _entry(self, parent, bg, textvariable=None, show=None, expand=False):
        T = self.theme
        wrap = tk.Frame(parent, bg=T["border"], padx=1, pady=1)
        if expand:
            wrap.pack(side="left", fill="x", expand=True, pady=(0, 2))
        else:
            wrap.pack(fill="x", pady=(0, 2))

        e = tk.Entry(
            wrap, textvariable=textvariable,
            font=("Poppins", 10), bg=T["input_bg"],
            fg=T["text_dark"], relief="flat", bd=0,
            insertbackground=T["primary_orange"],
            **({"show": show} if show else {}),
        )
        e.pack(fill="x", ipady=7, padx=8)

        # Focus highlight
        def _focus_in(e_):
            wrap.config(bg=T["primary_orange"])

        def _focus_out(e_):
            wrap.config(bg=T["border"])

        e.bind("<FocusIn>",  _focus_in)
        e.bind("<FocusOut>", _focus_out)
        return e

    def _pw_toggle_btn(self, parent, entry, bg):
        T       = self.theme
        showing = [False]

        def toggle():
            showing[0] = not showing[0]
            entry.config(show="" if showing[0] else "•")
            btn.config(text="Hide" if showing[0] else "Show")

        btn = tk.Button(
            parent, text="Show", command=toggle,
            bg=bg, fg=T["text_grey"],
            activebackground=bg, activeforeground=T["primary_orange"],
            font=("Poppins", 8), bd=0, relief="flat",
            padx=6, pady=4, cursor="hand2",
        )
        btn.pack(side="left", padx=(6, 0))
        return btn

    # ── Dirty tracking ────────────────────────────────────────────────────────

    def _mark_dirty(self):
        self._dirty = True
        if hasattr(self, "_save_btn"):
            self._save_btn.config(state="normal")

    def _check_dirty(self):
        name_changed   = (hasattr(self, "_name_var")
                          and self._name_var.get() != self._initial_name)
        email_changed  = (hasattr(self, "_email_var")
                          and self._email_var.get() != self._initial_email)
        pw_changed     = (hasattr(self, "_new_pw_var")
                          and bool(self._new_pw_var.get()))
        avatar_changed = self._pending_avatar is not None

        self._dirty = name_changed or email_changed or pw_changed or avatar_changed
        if hasattr(self, "_save_btn"):
            self._save_btn.config(
                state="normal" if self._dirty else "disabled")

    def _reset_form(self):
        self._pending_avatar = None
        if hasattr(self, "_file_name_var"):
            self._file_name_var.set("No file selected")
        self._draw_big_avatar()

        if hasattr(self, "_name_var"):
            self._name_var.set(self.display_name)
        if hasattr(self, "_email_var"):
            self._email_var.set(self.display_email)
        for attr in ("_cur_pw_var", "_new_pw_var", "_conf_pw_var"):
            if hasattr(self, attr):
                getattr(self, attr).set("")
        if hasattr(self, "_strength_lbl"):
            self._strength_lbl.config(text="")
            self._strength_bar.place_configure(relwidth=0)
        if hasattr(self, "_match_lbl"):
            self._match_lbl.config(text="")

        self._dirty = False
        if hasattr(self, "_save_btn"):
            self._save_btn.config(state="disabled")

        self._draw_nav_avatar()

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save_profile(self):
        from services.api_client import APIClient

        name    = self._name_var.get().strip()
        email   = self._email_var.get().strip()
        cur_pw  = self._cur_pw_var.get()
        new_pw  = self._new_pw_var.get()
        conf_pw = self._conf_pw_var.get()

        # ── Front-end validation ────────────────────────────────────────────
        if not name:
            messagebox.showerror("Validation", "Full Name cannot be empty.")
            return
        if not email or "@" not in email:
            messagebox.showerror(
                "Validation", "Please enter a valid email address.")
            return

        changing_password = bool(new_pw or cur_pw)
        if changing_password:
            if not cur_pw:
                messagebox.showerror(
                    "Validation",
                    "Please enter your current password to change it.")
                return
            if len(new_pw) < 8:
                messagebox.showerror(
                    "Validation",
                    "New password must be at least 8 characters.")
                return
            if new_pw != conf_pw:
                messagebox.showerror(
                    "Validation", "New passwords do not match.")
                return
            if cur_pw == new_pw:
                messagebox.showerror(
                    "Validation",
                    "New password must differ from your current password.")
                return

        # ── Upload avatar to Flask ──────────────────────────────────────────
        saved_avatar = self.avatar_path

        if self._pending_avatar and os.path.exists(self._pending_avatar):
            api             = APIClient()
            remote_filename = api.upload_avatar(self._pending_avatar)

            if not remote_filename:
                messagebox.showerror(
                    "Upload Error",
                    "Could not upload the profile photo to the server.\n"
                    "Make sure Flask is running and try again.",
                )
                return

            # Local copy so Tkinter can render without a network round-trip
            project_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
            local_dir = os.path.join(
                project_root, "static", "uploads", "avatars")
            os.makedirs(local_dir, exist_ok=True)
            try:
                shutil.copy2(
                    self._pending_avatar,
                    os.path.join(local_dir, remote_filename),
                )
            except Exception as e:
                print(f"[UserProfile._save_profile] local copy warning: {e}")

            saved_avatar = f"avatars/{remote_filename}"
            print(f"[UserProfile] ✅ Avatar stored as: {saved_avatar}")

        # ── Update profile (name / email / avatar) ─────────────────────────
        profile_cb = self.callbacks.get("update_profile")
        if profile_cb:
            try:
                ok, msg = profile_cb(self.user_id, name, email, saved_avatar)
            except Exception as ex:
                ok, msg = False, str(ex)

            if not ok and msg != "No changes detected.":
                messagebox.showerror("Error", msg or "Failed to update profile.")
                return

        # ── Change password ────────────────────────────────────────────────
        if changing_password:
            pw_cb = self.callbacks.get("change_password")
            if pw_cb:
                try:
                    ok_pw, msg_pw = pw_cb(self.user_id, cur_pw, new_pw)
                except Exception as ex:
                    ok_pw, msg_pw = False, str(ex)

                if not ok_pw:
                    messagebox.showerror(
                        "Error", msg_pw or "Failed to update password.")
                    return

        # ── Update local state ─────────────────────────────────────────────
        self.display_name    = name
        self.display_email   = email
        self.avatar_path     = saved_avatar
        self._initial_name   = name
        self._initial_email  = email
        self._pending_avatar = None
        if hasattr(self, "_file_name_var"):
            self._file_name_var.set("No file selected")

        for attr in ("_cur_pw_var", "_new_pw_var", "_conf_pw_var"):
            if hasattr(self, attr):
                getattr(self, attr).set("")
        if hasattr(self, "_strength_lbl"):
            self._strength_lbl.config(text="")
            self._strength_bar.place_configure(relwidth=0)
        if hasattr(self, "_match_lbl"):
            self._match_lbl.config(text="")

        self._dirty = False
        self._save_btn.config(state="disabled")
        self._draw_nav_avatar()
        self._draw_big_avatar()

        msg = ("Profile and password updated successfully!"
               if changing_password else "Profile updated successfully!")
        messagebox.showinfo("Success", msg)

    # ── Delete account ────────────────────────────────────────────────────────

    def _delete_account(self):
        if not messagebox.askyesno(
            "Delete Account",
            "Are you sure you want to permanently delete your account?\n\n"
            "All your articles, comments, and data will be removed.\n"
            "This action CANNOT be undone.",
            icon="warning",
        ):
            return

        cb = self.callbacks.get("delete_account")
        if cb:
            try:
                ok = cb(self.user_id)
            except Exception as ex:
                messagebox.showerror("Error", str(ex))
                return
            if ok:
                messagebox.showinfo(
                    "Account Deleted",
                    "Your account has been permanently deleted.",
                )
                self._logout(confirm=False)
            else:
                messagebox.showerror("Error", "Account deletion failed.")
        else:
            messagebox.showinfo("Demo", "Delete account (no backend connected).")
            self._logout(confirm=False)

    # ── Footer ────────────────────────────────────────────────────────────────

    def _make_footer(self):
        T = self.theme
        self.footer = tk.Frame(self.root, bg=T["navy"], height=FOOTER_H)
        self.footer.place(x=0, rely=1.0, anchor="sw", relwidth=1)
        self.footer.pack_propagate(False)

        inner = tk.Frame(self.footer, bg=T["navy"])
        inner.pack(fill="x", padx=36)

        tk.Label(
            inner, text="© 2025 The Gears",
            font=FONTS["small_bold"], fg=T["white"],
            bg=T["navy"],
        ).pack(side="left", pady=16)

        tk.Label(
            inner, text="WRITE WITHOUT FAVOR. EXPRESS WITHOUT FEAR.",
            font=FONTS["small"], fg="#7F8AA8",
            bg=T["navy"],
        ).pack(side="right", pady=16)

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _sync_body(self):
        rw = max(self.root.winfo_width(),  900)
        rh = max(self.root.winfo_height(), 600)
        self.body.place_configure(
            x=0, y=HEADER_H + ORANGE_BAR_H,
            width=rw,
            height=rh - HEADER_H - ORANGE_BAR_H - FOOTER_H,
        )

    def _on_resize(self, event=None):
        if event and event.widget is not self.root:
            return
        self._sync_body()
        if self.account_visible:
            rw = self.root.winfo_width()
            self._account_menu.place_configure(
                x=rw - 222, y=HEADER_H + ORANGE_BAR_H + 2)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _toggle_dark(self):
        self.dark_mode = not self.dark_mode
        self.theme     = self.dark if self.dark_mode else self.light
        self._rebuild()

    def _go_home(self):
        if hasattr(self.root, "show_user_homepage"):
            self.root.show_user_homepage(self.user)
        elif hasattr(self.root, "show_homepage"):
            self.root.show_homepage(self.user)

    def _go_home_with_cat(self, cat):
        if hasattr(self.root, "show_user_homepage"):
            self.root.show_user_homepage(self.user, category=cat)
        else:
            self._go_home()

    def _go_home_search(self, query):
        if hasattr(self.root, "show_user_homepage"):
            self.root.show_user_homepage(self.user, search=query)
        else:
            self._go_home()

    def _logout(self, confirm=True):
        if self.account_visible:
            self._close_account_menu()
        if confirm and not messagebox.askyesno(
                "Logout", "Are you sure you want to logout?"):
            return
        if hasattr(self.root, "show_landing"):
            self.root.show_landing()
        else:
            self.root.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("The Gears — Profile")
    root.geometry("1280x800")
    root.minsize(900, 600)

    root.show_user_homepage = lambda user, **kw: print(f"→ Go home {kw}")
    root.show_landing        = lambda: print("→ Landing")
    root.show_user_profile   = lambda user: print(f"→ Profile {user}")

    DUMMY_USER = ("Maria", "Santos", "maria@gears.com", 1, "user")

    def _fake_update(uid, name, email, avatar=None):
        print(f"[update_profile] uid={uid} name={name} email={email} avatar={avatar}")
        return True, "Profile saved!"

    def _fake_pw(uid, cur_pw, new_pw):
        print(f"[change_password] uid={uid}")
        if cur_pw != "password123":
            return False, "Wrong current password (hint: 'password123')"
        return True, "Password changed!"

    def _fake_delete(uid):
        print(f"[delete_account] uid={uid}")
        return True

    UserProfilePage(
        root,
        user=DUMMY_USER,
        db_callbacks={
            "update_profile":  _fake_update,
            "change_password": _fake_pw,
            "delete_account":  _fake_delete,
        },
    )
    root.mainloop()