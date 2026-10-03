"""
user/user_homepage.py
──────────────────────
Homepage shown to regular users after login.

NAVBAR LAYOUT (left → right)
─────────────────────────────
  [Logo + Brand]  [Home] [Category▾] [About] [Contact]  [SearchBar]  [🌙]  [Avatar▾]

Fixes & Improvements
─────────────────────
  • Article cards render in a RESPONSIVE GRID (3 cols → 2 → 1) that wraps
    properly instead of overflowing to the right.
  • Category strip pills correctly highlight the active filter after any state
    change (filter/search/rebuild).
  • Search bar clears correctly when switching categories; active filter label
    shown above content area ("Showing X results for 'NEWS'").
  • Account menu close uses add="+" binding so it never strips other listeners.
  • Category dropdown Toplevel closes reliably via FocusOut + outside-click,
    and the button chevron always resets.
  • Hero redraws correctly on every <Configure> event.
  • Footer uses place(rely=1, anchor="sw") so it never overlaps content.
  • Dark mode rebuild preserves scroll position.
  • Empty-state illustration for both no-articles and no-search-results.
  • _load_card_image gracefully falls back to a styled placeholder when PIL
    is absent or the file is missing.

user tuple:  (first_name, last_name, email, id, role, ...)
Article tuple shape from DB:
  0  id  1  headline  2  content  3  category  4  created_at
  5  first_name  6  last_name  7  media
"""

import json
import os
import tkinter as tk
from tkinter import messagebox

try:
    from theme import COLORS, FONTS
except ImportError:
    COLORS = {
        "primary_orange":       "#F5821F",
        "primary_orange_dark":  "#D97E10",
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
    "card":                 "#1F1F1F",
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

HEADER_H  = 68
ORANGE_BAR_H = 4
FOOTER_H  = 52
CARD_W    = 268
CARD_H    = 295
MIN_COLS  = 1
MAX_COLS  = 3


# ─────────────────────────────────────────────────────────────────────────────
VIDEO_EXTS = ("mp4", "mov", "avi", "mkv", "webm")
IMAGE_EXTS = ("png", "jpg", "jpeg", "gif", "webp")

def _first_media(media_raw) -> tuple[str | None, str]:
    """
    Returns (filename, kind) where kind is 'image' or 'video'.
    Replaces _first_image — now also picks up video files.
    """
    if not media_raw:
        return None, "image"

    def _extract(data):
        candidates = []
        if isinstance(data, dict):
            for fp in data.get("file_paths", []):
                candidates.append(str(fp).strip())
            if data.get("path"):
                candidates.append(str(data["path"]).strip())
        elif isinstance(data, list):
            for fp in data:
                if isinstance(fp, dict):
                    candidates.append(str(fp.get("url", "")).strip())
                else:
                    candidates.append(str(fp).strip())

        # Images preferred; fall back to video
        for fp in candidates:
            if not fp:
                continue
            ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else ""
            if ext in IMAGE_EXTS:
                return fp, "image"
        for fp in candidates:
            if not fp:
                continue
            ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else ""
            if ext in VIDEO_EXTS:
                return fp, "video"
        return None, "image"

    if isinstance(media_raw, (dict, list)):
        return _extract(media_raw)

    if isinstance(media_raw, str):
        v = media_raw.strip()
        if not v:
            return None, "image"
        try:
            import json as _j
            parsed = _j.loads(v)
            result, kind = _extract(parsed)
            if result:
                return result, kind
        except Exception:
            pass
        for fp in v.split(","):
            fp = fp.strip()
            if not fp:
                continue
            ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else ""
            if ext in IMAGE_EXTS:
                return fp, "image"
            if ext in VIDEO_EXTS:
                return fp, "video"

    return None, "image"


def _first_image(media_raw) -> str | None:
    """Legacy wrapper — keeps existing call sites working."""
    path, _ = _first_media(media_raw)
    return path


# ─────────────────────────────────────────────────────────────────────────────
class UserHomepage:

    def __init__(self, root, user=None, db_callbacks=None):
        self.root      = root
        self.user      = user
        self.callbacks = db_callbacks or {}

        self.dark_mode       = False
        self.account_visible = False
        self._cat_filter     = "All"
        self._search_query   = ""
        self._cat_menu       = None
        self._scroll_pos     = 0.0
        self._close_bind_id  = None

        self.light = COLORS.copy()
        self.dark  = DARK.copy()
        self.theme = self.light

        if self.user and len(self.user) >= 2:
            self.initials      = (str(self.user[0])[:1] + str(self.user[1])[:1]).upper()
            self.display_name  = f"{self.user[0]} {self.user[1]}".strip()
            self.display_email = self.user[2] if len(self.user) > 2 else ""
        else:
            self.initials      = "U"
            self.display_name  = "User"
            self.display_email = ""

        self.avatar_path = (
            str(self.user[5]).strip()
            if self.user and len(self.user) > 5 and self.user[5]
            else None
        )

        self._categories      = self._fetch_categories()
        self._category_names  = [
            str(c.get("name", "")).strip()
            for c in self._categories
            if str(c.get("name", "")).strip()
        ]
        self._category_color  = {
            str(c.get("name", "")).strip(): c.get("color", COLORS["primary_orange"])
            for c in self._categories
            if str(c.get("name", "")).strip()
        }
        self._all_articles    = self._fetch_articles()
        self._shown_articles  = list(self._all_articles)

        self._build_ui()
        self.root.bind("<Configure>", self._on_resize)

    # ── Data ──────────────────────────────────────────────────────────────────
    def _draw_nav_avatar(self):
        import os, io as _io, urllib.request
        T  = self.theme
        av = self._av_canvas
        av.delete("all")

        # Get avatar path from user tuple (index 5) or refresh from server
        avatar_path = (str(self.user[5]).strip()
                    if self.user and len(self.user) > 5 and self.user[5]
                    else None)

        # Try to refresh from server if we have a user_id
        user_id = self.user[3] if self.user and len(self.user) > 3 else None
        if user_id and not avatar_path:
            try:
                import json as _json
                flask_url = self.callbacks.get("flask_url", "http://127.0.0.1:5000")
                url = f"{flask_url}/mobile/profile/{user_id}"
                with urllib.request.urlopen(url, timeout=3) as resp:
                    data = _json.loads(resp.read())
                if data.get("success"):
                    avatar_path = data.get("user", {}).get("profile_image") or None
            except Exception:
                pass

        loaded_image = None

        if avatar_path:
            try:
                from PIL import Image, ImageTk, ImageDraw
                flask_url = self.callbacks.get("flask_url", "http://127.0.0.1:5000")
                src = str(avatar_path).strip().replace("\\", "/")
                filename = src.split("/")[-1]

                BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                candidates = [
                    src if os.path.isabs(src) else os.path.join(BASE_DIR, src),
                    os.path.join(BASE_DIR, "static", "uploads", "avatars", filename),
                    os.path.join(BASE_DIR, "static", "uploads", filename),
                ]
                for path in candidates:
                    path = os.path.normpath(path)
                    if os.path.exists(path):
                        try:
                            loaded_image = Image.open(path).convert("RGBA").resize((34, 34))
                            break
                        except Exception:
                            pass

                if loaded_image is None:
                    for url in [
                        f"{flask_url}/static/uploads/avatars/{filename}",
                        f"{flask_url}/static/uploads/{filename}",
                    ]:
                        try:
                            with urllib.request.urlopen(url, timeout=5) as resp:
                                loaded_image = Image.open(
                                    _io.BytesIO(resp.read())).convert("RGBA").resize((34, 34))
                            break
                        except Exception:
                            pass
            except ImportError:
                pass

        if loaded_image:
            try:
                from PIL import ImageDraw, ImageTk
                mask = Image.new("L", (34, 34), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 33, 33), fill=255)
                loaded_image.putalpha(mask)
                self._nav_avatar_photo = ImageTk.PhotoImage(loaded_image)
                av.create_image(0, 0, anchor="nw", image=self._nav_avatar_photo)
                return
            except Exception:
                pass

        # Fallback: initials
        av.create_oval(1, 1, 33, 33, fill=T["primary_orange"], outline=T["primary_orange"])
        av.create_text(17, 17, text=self.initials, fill="white", font=("Poppins", 9, "bold"))



    def _fetch_articles(self) -> list:
        cb = self.callbacks.get("fetch_homepage_articles")
        if cb:
            try:
                return cb() or []
            except Exception as e:
                print(f"[UserHomepage] fetch_articles error: {e}")
        return []

    def _fetch_categories(self) -> list:
        cb = self.callbacks.get("fetch_categories")
        if cb:
            try:
                rows = cb() or []
                active = [c for c in rows if not c.get("archived")]
                if active:
                    return active
            except Exception as e:
                print(f"[UserHomepage] fetch_categories error: {e}")
        return [
            {"name": name, "icon": "",
             "color": CAT_ACCENT.get(name, COLORS["primary_orange"]),
             "archived": False}
            for name in DEFAULT_CATEGORIES
        ]

    def _apply_filter(self):
        q   = self._search_query.lower().strip()
        cat = self._cat_filter

        self._shown_articles = [
            a for a in self._all_articles
            if (cat == "All" or str(a[3]).strip().lower() == cat.lower())
            and (not q
                 or q in str(a[1]).lower()
                 or q in str(a[5]).lower()
                 or q in str(a[6]).lower()
                 or q in str(a[2]).lower())
        ]
        self._render_content()

    # ── Build / Rebuild ───────────────────────────────────────────────────────

    def _build_ui(self):
        T = self.theme
        self.root.configure(bg=T["background"])
        self._make_navbar()
        self._make_footer()
        self._make_body()
        self.navbar.lift()
        self.footer.lift()

    def _rebuild(self):
        try:
            self._scroll_pos = self.canvas.yview()[0]
        except Exception:
            self._scroll_pos = 0.0

        self.account_visible = False
        self._cat_menu       = None
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()
        self._sync_body()
        self.root.after(60, lambda: self.canvas.yview_moveto(self._scroll_pos))

    # ─────────────────────────────────────────────────────────────────────────
    # NAVBAR
    # ─────────────────────────────────────────────────────────────────────────

    def _make_navbar(self):
        T = self.theme

        self.navbar = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        self.navbar.place(x=0, y=0, relwidth=1, height=HEADER_H)

        # ── LEFT: logo ────────────────────────────────────────────────────────
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
            font=("Hedvig Letters Serif 24pt", 15, "bold"),
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            left, text="  ·  Reader",
            bg=T["card"], fg=T["text_grey"],
            font=("Poppins", 9),
        ).pack(side="left")

        # ── RIGHT: dark-mode toggle + avatar ─────────────────────────────────
        right = tk.Frame(self.navbar, bg=T["card"])
        right.pack(side="right", fill="y", padx=(0, 22))

        tk.Button(
            right, text="🌙",
            command=self._toggle_dark,
            bg=T["card"], fg=T["text_grey"],
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"],
            font=("Poppins", 13),
            bd=0, relief="flat", cursor="hand2",
            padx=6, pady=4,
        ).pack(side="left", padx=(0, 10))

        tk.Frame(right, bg=T["border"], width=1, height=26).pack(
            side="left", padx=(0, 10), pady=20)

        av_frame = tk.Frame(right, bg=T["card"], cursor="hand2")
        av_frame.pack(side="left")

        self._av_canvas = tk.Canvas(av_frame, width=34, height=34,
                            bg=T["card"], highlightthickness=0,
                            cursor="hand2")
        self._av_canvas.pack(side="left")
        self._draw_nav_avatar()
        self._av_canvas.bind("<Button-1>",
                            lambda e: ("break", self._toggle_account_menu()))

        tk.Label(
            av_frame, text="▾",
            bg=T["card"], fg=T["text_grey"],
            font=("Poppins", 8), cursor="hand2",
        ).pack(side="left", padx=(3, 0))
        av_frame.bind("<Button-1>",
                      lambda e: ("break", self._toggle_account_menu()))

        # ── CENTER: nav links + search ────────────────────────────────────────
        # Center this group in the whole top bar instead of letting it start
        # immediately after the logo.
        center = tk.Frame(self.navbar, bg=T["card"])
        center.place(relx=0.5, rely=0.5, anchor="center")

        # Home (active underline)
        home_wrap = tk.Frame(center, bg=T["card"])
        home_wrap.pack(side="left", fill="y", padx=(0, 4))
        home_lbl = tk.Label(
            home_wrap, text="Home",
            bg=T["card"], fg=T["primary_orange"],
            font=("Poppins", 10, "bold"),
            cursor="hand2", padx=8,
        )
        home_lbl.pack(side="top", pady=(22, 0))
        tk.Frame(home_wrap, bg=T["primary_orange"], height=2).pack(
            side="top", fill="x", padx=8)
        home_lbl.bind("<Button-1>", lambda e: self._go_home())

        # Category dropdown
        self._cat_btn_var = tk.StringVar(value="Category  ▾")
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

        # About / Contact static links
        for text in ("About", "Contact"):
            lbl = tk.Label(
                center, text=text,
                bg=T["card"], fg=T["text_grey"],
                font=("Poppins", 10), cursor="hand2", padx=8,
            )
            lbl.pack(side="left", padx=4, pady=20)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=T["text_dark"]))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=T["text_grey"]))

        # Search bar
        PLACEHOLDER = "Search articles..."
        search_wrap = tk.Frame(center, bg=T["border"])
        search_wrap.pack(side="left", padx=(20, 0), pady=20)

        search_inner = tk.Frame(search_wrap, bg=T["input_bg"])
        search_inner.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(
            search_inner, text="🔍",
            bg=T["input_bg"], fg=T["text_grey"], font=("Poppins", 9),
        ).pack(side="left", padx=(6, 0))

        self._search_var = tk.StringVar()
        self._search_entry = tk.Entry(
            search_inner,
            textvariable=self._search_var,
            font=("Poppins", 9),
            bg=T["input_bg"], fg=T["text_light"],
            relief="flat", bd=0, width=20,
            insertbackground=T["primary_orange"],
        )
        self._search_entry.pack(side="left", ipady=5, padx=(2, 8))
        self._search_entry.insert(0, PLACEHOLDER)

        # Clear button (×) — hidden until there's a query
        self._clear_btn = tk.Button(
            search_inner, text="×",
            command=self._clear_search,
            bg=T["input_bg"], fg=T["text_grey"],
            activebackground=T["input_bg"],
            activeforeground=T["primary_orange"],
            font=("Poppins", 11), bd=0, relief="flat",
            cursor="hand2", padx=4,
        )

        def _focus_in(e):
            if self._search_entry.get() == PLACEHOLDER:
                self._search_entry.delete(0, "end")
                self._search_entry.config(fg=T["text_dark"])

        def _focus_out(e):
            val = self._search_entry.get().strip()
            if not val:
                self._search_entry.insert(0, PLACEHOLDER)
                self._search_entry.config(fg=T["text_light"])
                self._clear_btn.pack_forget()

        def _key_release(e):
            val = self._search_var.get()
            if val and val != PLACEHOLDER:
                self._search_query = val.strip()
                self._clear_btn.pack(side="left", padx=(0, 4))
                self._apply_filter()
            else:
                self._clear_btn.pack_forget()

        self._search_entry.bind("<FocusIn>",   _focus_in)
        self._search_entry.bind("<FocusOut>",  _focus_out)
        self._search_entry.bind("<KeyRelease>", _key_release)
        self._search_entry.bind("<Return>",
            lambda e: self._apply_filter())

        # Orange underline bar
        self.orange_bar = tk.Frame(self.root, bg=T["primary_orange"])
        self.orange_bar.place(x=0, y=HEADER_H, relwidth=1, height=ORANGE_BAR_H)

        # Account dropdown (built once, shown/hidden)
        self._account_menu = self._build_account_menu()

    def _clear_search(self):
        PLACEHOLDER = "Search articles..."
        self._search_query = ""
        self._search_var.set("")
        self._search_entry.delete(0, "end")
        self._search_entry.insert(0, PLACEHOLDER)
        self._search_entry.config(fg=self.theme["text_light"])
        self._clear_btn.pack_forget()
        self._apply_filter()

    # ── Account dropdown ──────────────────────────────────────────────────────

    def _build_account_menu(self):
        T    = self.theme
        menu = tk.Frame(
            self.root, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )

        hdr = tk.Frame(menu, bg=T["primary_orange_light"], pady=10)
        hdr.pack(fill="x")

        av_row = tk.Frame(hdr, bg=T["primary_orange_light"])
        av_row.pack(fill="x", padx=12, pady=(0, 4))

        mini_av = tk.Canvas(av_row, width=28, height=28,
                            bg=T["primary_orange_light"], highlightthickness=0)
        mini_av.pack(side="left", padx=(0, 8))
        mini_av.create_oval(1, 1, 27, 27,
                            fill=T["primary_orange"], outline=T["primary_orange"])
        mini_av.create_text(14, 14, text=self.initials,
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

        for text, red in [
            ("👤  My Profile", True),
            ("🚪  Logout",     False),
        ]:
            def make_cmd(t=text):
                if t == "👤  My Profile":
                    return lambda: self._go_to_profile()
                else:
                    return self._logout

            tk.Button(
                menu, text=text, command=make_cmd(),
                anchor="w", bg=T["card"],
                fg=T["primary_red"] if red else T["text_dark"],
                activebackground=T["primary_orange_light"],
                activeforeground=T["primary_red"] if red else T["primary_orange"],
                font=("Poppins", 9, "bold") if red else ("Poppins", 9),
                bd=0, relief="flat", padx=14, pady=9, cursor="hand2",
            ).pack(fill="x")
            tk.Frame(menu, bg=T["border"], height=1).pack(fill="x")

        return menu

    def _toggle_account_menu(self):
        self.account_visible = not self.account_visible
        if self.account_visible:
            rw = self.root.winfo_width()
            self._account_menu.place(x=rw - 222, y=HEADER_H + ORANGE_BAR_H + 2,
                                    width=210)
            self._account_menu.lift()
            self._close_bind_id = self.root.bind(
                "<Button-1>", self._close_account_on_click, add="+")
        else:
            self._close_account_menu()
            try:
                self.root.unbind("<Button-1>", self._close_bind_id)
            except Exception:
                pass

    def _close_account_menu(self):
        self.account_visible = False
        self._account_menu.place_forget()
        if self._close_bind_id:
            try:
                self.root.unbind("<Button-1>", self._close_bind_id)
            except Exception:
                pass
            self._close_bind_id = None

    def _close_account_on_click(self, event):
        """Close account menu if click is outside it and outside avatar."""
        try:
            # Walk up widget tree
            w = event.widget
            while w:
                if w is self._account_menu:
                    return
                if w is self._av_canvas:
                    return
                w = getattr(w, "master", None)
        except Exception:
            pass
        # Click was outside — close
        self.account_visible = True   # force toggle to close
        self._toggle_account_menu()

    # ── Category dropdown (Toplevel) ──────────────────────────────────────────

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
        by = self._cat_btn_widget.winfo_rooty() + self._cat_btn_widget.winfo_height()

        MENU_W = 210
        outer  = tk.Frame(menu, bg=T["card"],
                           highlightthickness=1,
                           highlightbackground=T["border"], bd=0)
        outer.pack(fill="both", expand=True)

        items = [("All categories", "All")] + [(c, c) for c in self._category_names]

        def _pick(v):
            self._cat_filter   = v
            self._search_query = ""
            self._clear_search()
            if menu.winfo_exists():
                menu.destroy()
            self._cat_menu = None
            self._cat_btn_var.set("Category  ▾")
            self._apply_filter()

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

            for widget in (row, lbl):
                widget.bind("<Enter>", lambda e, r=row, b=lbl, a=is_active: (
                    None if a else (r.config(bg="#F8F9FA"), b.config(bg="#F8F9FA"))))
                widget.bind("<Leave>", lambda e, r=row, b=lbl, a=is_active, _bg=bg: (
                    None if a else (r.config(bg=_bg), b.config(bg=_bg))))
                widget.bind("<Button-1>", lambda e, v=val: _pick(v))

            tk.Frame(outer, bg=T["border"], height=1).pack(fill="x")

        menu.update_idletasks()
        h = min(outer.winfo_reqheight(), 360)
        menu.geometry(f"{MENU_W}x{h}+{bx}+{by}")

        # Close on focus loss
        def _check_focus(e=None):
            if not menu.winfo_exists():
                return
            try:
                focused = self.root.focus_get()
                if focused and str(focused).startswith(str(menu)):
                    return
            except Exception:
                pass
            menu.after(150, lambda: (
                menu.destroy() if menu.winfo_exists() else None
            ) or self._cat_btn_var.set("Category  ▾"))

        menu.bind("<FocusOut>", _check_focus)
        menu.focus_set()

    # ── Body (scrollable) ─────────────────────────────────────────────────────

    def _make_body(self):
        T  = self.theme
        rw = max(self.root.winfo_width(),  900)
        rh = max(self.root.winfo_height(), 600)

        self.body = tk.Frame(self.root, bg=T["background"])
        self.body.place(
            x=0, y=HEADER_H + ORANGE_BAR_H,
            width=rw, height=rh - HEADER_H - ORANGE_BAR_H - FOOTER_H,
        )

        outer = tk.Frame(self.body, bg=T["background"])
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg=T["background"], highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)

        self.content = tk.Frame(self.canvas, bg=T["background"])
        self._cwin = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
            lambda e: self.canvas.itemconfig(self._cwin, width=e.width))
        self.canvas.bind("<Enter>",
            lambda e: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>",
            lambda e: self.canvas.unbind_all("<MouseWheel>"))

        self._make_hero()
        self._make_category_strip()

        self._content_area = tk.Frame(self.content, bg=T["background"])
        self._content_area.pack(fill="both", expand=True, padx=40, pady=(24, 24))

        self._render_content()

    def _on_wheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── Hero ──────────────────────────────────────────────────────────────────

    def _make_hero(self):
        T    = self.theme
        hero = tk.Canvas(self.content, height=200,
                         bg=T["navy"], highlightthickness=0)
        hero.pack(fill="x")

        def _draw(e=None):
            hero.delete("all")
            w = hero.winfo_width()
            if w < 10:
                return
            h = 200

            hero.create_rectangle(0, 0, w, h, fill=T["navy"], outline="")
            hero.create_rectangle(0, 0, int(w * 0.6), h, fill="#0A152E", outline="")

            hero.create_polygon(
                int(w * 0.40), 0, int(w * 0.50), 0,
                int(w * 0.35), h, int(w * 0.25), h,
                fill=T["primary_orange"], outline="")
            hero.create_polygon(
                int(w * 0.50), 0, int(w * 0.54), 0,
                int(w * 0.39), h, int(w * 0.35), h,
                fill=T["primary_orange_dark"], outline="")

            for row in range(4):
                for col in range(8):
                    cx_ = int(w * 0.62) + col * 26
                    cy_ = 20 + row * 44
                    hero.create_oval(cx_-2, cy_-2, cx_+2, cy_+2,
                                     fill="#1E3A6E", outline="")

            hero.create_rectangle(40, 26, 200, 48,
                                  fill=T["primary_orange"], outline="")
            hero.create_text(120, 37, text="CAMPUS PUBLICATION",
                             fill="white", font=("Poppins", 8, "bold"))
            hero.create_text(40, 80, anchor="w", text="THE GEARS",
                             fill="white", font=("Poppins", 30, "bold"))
            hero.create_text(40, 120, anchor="w",
                             text="Campus stories. Truthful news. Student creativity.",
                             fill="#94A3B8", font=("Poppins", 11))
            hero.create_text(40, 148, anchor="w",
                             text="Browse the latest articles below ↓",
                             fill=T["primary_orange"], font=("Poppins", 9, "bold"))

            lx = int(w * 0.68)
            for i, lw_ in enumerate([200, 160, 220, 130, 180, 90]):
                ly_ = 36 + i * 26
                hero.create_rectangle(lx, ly_, lx + lw_, ly_ + 7,
                                      fill="#1E3A6E", outline="")
            hero.create_text(lx + 110, h - 24, text="Est. 2025",
                             fill="#475569", font=("Poppins", 9))

        hero.bind("<Configure>", lambda e: _draw())
        hero.bind("<Map>",       lambda e: _draw())
        self.content.after(80, _draw)

    # ── Category strip ────────────────────────────────────────────────────────

    def _make_category_strip(self):
        T = self.theme
        self._strip_frame = tk.Frame(
            self.content, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1)
        self._strip_frame.pack(fill="x")
        self._render_category_strip()

    def _render_category_strip(self):
        T = self.theme
        for w in self._strip_frame.winfo_children():
            w.destroy()

        outer = tk.Frame(self._strip_frame, bg=T["card"])
        outer.pack(fill="x", padx=36, pady=8)

        tk.Label(
            outer, text="Browse:",
            bg=T["card"], fg=T["text_grey"],
            font=("Poppins", 8, "bold"),
        ).pack(side="left", padx=(0, 8))

        all_cats = [("All", "All")] + [(c, c) for c in self._category_names]

        for label, value in all_cats:
            is_active = (value == self._cat_filter)
            bg = T["primary_orange"] if is_active else T["background_alt"]
            fg = "white"              if is_active else T["text_grey"]

            btn = tk.Button(
                outer, text=label,
                command=lambda v=value: self._filter_by_cat(v),
                bg=bg, fg=fg,
                activebackground=T["primary_orange"],
                activeforeground="white",
                font=("Poppins", 8, "bold"),
                bd=0, relief="flat",
                padx=10, pady=3, cursor="hand2",
            )
            btn.pack(side="left", padx=2)
            btn.bind("<Enter>",
                lambda e, b=btn, a=is_active: b.config(
                    bg=T["primary_orange"] if a else T["border"]))
            btn.bind("<Leave>",
                lambda e, b=btn, a=is_active, _bg=bg: b.config(bg=_bg))

    # ── Content rendering ─────────────────────────────────────────────────────

    def _render_content(self):
        T = self.theme

        # Refresh pill highlights every time content renders
        self._render_category_strip()

        for w in self._content_area.winfo_children():
            w.destroy()

        # Status bar
        self._render_status_bar()

        if not self._shown_articles:
            self._render_empty_state()
            return

        grouped: dict[str, list] = {}
        for art in self._shown_articles:
            cat = str(art[3]).strip() if len(art) > 3 else "Uncategorized"
            grouped.setdefault(cat, []).append(art)

        order  = [c for c in self._category_names if c in grouped]
        order += [c for c in grouped if c not in order]

        for cat in order:
            arts    = grouped[cat]
            display = arts[:3] if self._cat_filter == "All" else arts
            self._render_section(cat, display)

    def _render_status_bar(self):
        """Show filter/search context above articles."""
        T     = self.theme
        count = len(self._shown_articles)
        q     = self._search_query.strip()
        cat   = self._cat_filter

        if cat == "All" and not q:
            return   # no label needed on default view

        bar = tk.Frame(self._content_area, bg=T["background"])
        bar.pack(fill="x", pady=(0, 12))

        # Build description
        parts = []
        if cat != "All":
            parts.append(f'category "{cat}"')
        if q:
            parts.append(f'"{q}"')

        desc = " and ".join(parts)
        text = f"{count} result{'s' if count != 1 else ''} for {desc}"

        tk.Label(bar, text=text,
                 bg=T["background"], fg=T["text_grey"],
                 font=("Poppins", 9)).pack(side="left")

        # Quick-clear link
        if cat != "All" or q:
            tk.Button(
                bar, text="× Clear filter",
                command=self._go_home,
                bg=T["background"], fg=T["primary_orange"],
                activebackground=T["background"],
                activeforeground=T["primary_orange_dark"],
                font=("Poppins", 9, "bold"),
                bd=0, relief="flat", cursor="hand2",
            ).pack(side="left", padx=(12, 0))

    def _render_empty_state(self):
        T     = self.theme
        empty = tk.Frame(self._content_area, bg=T["background"])
        empty.pack(pady=60)

        q   = self._search_query.strip()
        cat = self._cat_filter

        if q:
            icon = "🔍"
            msg = f'No articles match "{q}"'
            sub  = "Try a different keyword or clear the search."
        elif cat != "All":
            icon = "📂"
            msg = f'No articles in "{cat}" yet.'
            sub  = "Check back soon or browse another category."
        else:
            icon = "📭"
            msg  = "No articles published yet."
            sub  = "Check back soon!"

        tk.Label(empty, text=icon,
                 bg=T["background"], fg=T["text_light"],
                 font=("Poppins", 36)).pack()
        tk.Label(empty, text=msg,
                 bg=T["background"], fg=T["text_grey"],
                 font=("Poppins", 12, "bold")).pack(pady=(8, 4))
        tk.Label(empty, text=sub,
                 bg=T["background"], fg=T["text_light"],
                 font=("Poppins", 10)).pack()

        if q or cat != "All":
            tk.Button(
                empty, text="← Back to all articles",
                command=self._go_home,
                bg=T["primary_orange_light"], fg=T["primary_orange"],
                activebackground=T["primary_orange"],
                activeforeground="white",
                font=("Poppins", 9, "bold"),
                bd=0, relief="flat", padx=14, pady=7, cursor="hand2",
            ).pack(pady=(16, 0))

    def _render_section(self, category: str, articles: list):
        T   = self.theme
        acc = CAT_ACCENT.get(category, T["primary_orange"])
        sec = tk.Frame(self._content_area, bg=T["background"])
        sec.pack(fill="x", pady=(0, 36))

        # Section header
        hdr = tk.Frame(sec, bg=T["background"])
        hdr.pack(fill="x", pady=(0, 12))

        tk.Frame(hdr, bg=acc, width=4, height=22).pack(side="left", padx=(0, 10))
        tk.Label(hdr, text=category.upper(),
                 bg=T["background"], fg=T["text_dark"],
                 font=("Poppins", 12, "bold")).pack(side="left")
        tk.Label(hdr,
                 text=f"  {len(articles)} article{'s' if len(articles) != 1 else ''}",
                 bg=T["background"], fg=T["text_light"],
                 font=("Poppins", 9)).pack(side="left", padx=(4, 0))

        if self._cat_filter == "All":
            tk.Button(
                hdr, text="View all →",
                command=lambda c=category: self._filter_by_cat(c),
                bg=T["background"], fg=acc,
                activebackground=T["background"],
                activeforeground=T["primary_orange_dark"],
                font=("Poppins", 9, "bold"),
                bd=0, relief="flat", cursor="hand2",
            ).pack(side="right")

        tk.Frame(sec, bg=T["border"], height=1).pack(fill="x", pady=(0, 12))

        # ── Responsive grid ───────────────────────────────────────────────────
        # We use a Frame-based grid that reflows on width changes.
        # Cols = floor(available_width / (CARD_W + gap)), clamped 1–MAX_COLS.
        grid_wrap = tk.Frame(sec, bg=T["background"])
        grid_wrap.pack(fill="x")

        self._draw_card_grid(grid_wrap, articles)

        # Bind resize so grid reflows when window width changes
        def _on_grid_resize(e, gw=grid_wrap, arts=articles):
            self._draw_card_grid(gw, arts)
        grid_wrap.bind("<Configure>", _on_grid_resize)

    def _draw_card_grid(self, grid_wrap: tk.Frame, articles: list):
        """Destroy existing card children and re-place in responsive columns."""
        for w in grid_wrap.winfo_children():
            w.destroy()

        avail = grid_wrap.winfo_width() or 900

        # Fixed gap between cards. Do not give columns equal "weight/uniform",
        # because that stretches the grid cells and creates a very wide distance
        # between article cards on large windows.
        GAP = 28
        cols = max(MIN_COLS, min(MAX_COLS, (avail + GAP) // (CARD_W + GAP)))

        # Reset possible old column settings from previous resize calls.
        for col in range(MAX_COLS):
            grid_wrap.grid_columnconfigure(col, weight=0, uniform="", minsize=0)

        for idx, art in enumerate(articles):
            row = idx // cols
            col = idx % cols
            cell = tk.Frame(grid_wrap, bg=self.theme["background"])
            cell.grid(
                row=row,
                column=col,
                padx=(0, GAP if col < cols - 1 else 0),
                pady=(0, GAP),
                sticky="nw",
            )
            self._article_card(cell, art)

    # ── Article card ──────────────────────────────────────────────────────────

    def _article_card(self, parent, art):
        T = self.theme

        art_id   = art[0]  if len(art) > 0 else None
        headline = art[1]  if len(art) > 1 else "(No headline)"
        category = str(art[3]).strip() if len(art) > 3 else ""
        fn       = art[5]  if len(art) > 5 else ""
        ln       = art[6]  if len(art) > 6 else ""
        author   = f"{fn} {ln}".strip() or "Unknown"
        date_str = str(art[4])[:10]    if len(art) > 4 else ""
        media    = art[7]  if len(art) > 7 else None
        img_path, img_kind = _first_media(media)

        acc      = self._category_color.get(category,
                   CAT_ACCENT.get(category, T["primary_orange"]))

        card = tk.Frame(
            parent,
            bg=T["card"],
            width=CARD_W,
            highlightbackground=T["border"],
            highlightthickness=1,
            cursor="hand2",
        )
        card.pack(anchor="nw")
        card.pack_propagate(False)
        card.configure(height=CARD_H)

        # Accent top bar
        tk.Frame(card, bg=acc, height=3).pack(fill="x")

        # Image area
        img_frame = tk.Frame(card, bg="#EEEBE6", height=148, width=CARD_W)
        img_frame.pack(fill="x")
        img_frame.pack_propagate(False)

        img_cv = tk.Canvas(img_frame, bg="#EEEBE6",
                           highlightthickness=0, width=CARD_W, height=148)
        img_cv.pack(fill="both", expand=True)
        self._load_card_image(img_cv, img_path, CARD_W, 148, category, acc)

        # Text area
        body = tk.Frame(card, bg=T["card"])
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # Category pill
        pill_bg = T["primary_orange_light"]
        pill_fg = acc
        tk.Label(body, text=category.upper(),
                 bg=pill_bg, fg=pill_fg,
                 font=("Poppins", 7, "bold"), padx=7, pady=2).pack(anchor="w")

        # Headline
        short = (headline[:80] + "…") if len(headline) > 80 else headline
        tk.Label(body, text=short,
                 bg=T["card"], fg=T["text_dark"],
                 font=("Poppins", 10, "bold"),
                 wraplength=CARD_W - 28, justify="left",
                 anchor="w").pack(anchor="w", pady=(6, 0))

        # Author + date row
        meta = tk.Frame(body, bg=T["card"])
        meta.pack(anchor="w", pady=(6, 0))
        tk.Label(meta, text="✍",
                 bg=T["card"], fg=acc, font=("Poppins", 9)).pack(side="left")
        tk.Label(meta, text=f"  {author}",
                 bg=T["card"], fg=T["text_grey"],
                 font=("Poppins", 8)).pack(side="left")
        if date_str:
            tk.Label(meta, text=f"  ·  {date_str}",
                     bg=T["card"], fg=T["text_light"],
                     font=("Poppins", 8)).pack(side="left")

        read_more = tk.Label(body, text="Read more →",
                             bg=T["card"], fg=acc,
                             font=("Poppins", 8, "bold"), cursor="hand2")
        read_more.pack(anchor="w", pady=(8, 2))

        # Interaction
        def _click(e=None, aid=art_id):
            if hasattr(self.root, "show_article_detail"):
                self.root.show_article_detail(aid, self.user)

        def _enter(e):
            card.config(highlightbackground=acc, highlightthickness=2)
            read_more.config(fg=T["primary_orange_dark"])

        def _leave(e):
            card.config(highlightbackground=T["border"], highlightthickness=1)
            read_more.config(fg=acc)

        for w in [card, body, img_cv, img_frame, read_more]:
            w.bind("<Button-1>", _click)
            w.bind("<Enter>",    _enter)
            w.bind("<Leave>",    _leave)

    def _load_card_image(self, canvas, img_path, w, h, category, accent):
        """Load image/video thumbnail with PIL — local first, then Flask fallback."""
        import os, io as _io, urllib.request, subprocess, tempfile

        flask_url  = self.callbacks.get("flask_url", "http://127.0.0.1:5000")
        UPLOAD_DIR = os.getenv(
            "UPLOAD_DIR",
            r"C:\Users\Jasper\Downloads\The_Gears_Web\Web_TheGears\static\uploads"
        )
        FFMPEG = os.getenv("FFMPEG_PATH", r"C:\ffmpeg\bin\ffmpeg.exe")

        def _show(pil_img):
            try:
                from PIL import Image, ImageTk
                resample = getattr(Image, "Resampling", Image)
                pil_img  = pil_img.resize((w, h), resample.LANCZOS)
                photo    = ImageTk.PhotoImage(pil_img)
                canvas._photo = photo
                canvas.create_image(0, 0, anchor="nw", image=photo)
            except Exception as e:
                print(f"[UserHomepage] _show error: {e}")

        def _draw_placeholder():
            canvas.create_rectangle(0, 0, w, h, fill=accent, outline="")
            stripe_color = self._darken(accent)
            for i in range(-h, w + h, 32):
                canvas.create_line(i, 0, i + h, h, fill=stripe_color, width=18)
            initial = category[:1].upper() if category else "?"
            canvas.create_text(w // 2, h // 2, text=initial, fill="white",
                            font=("Poppins", 38, "bold"))
            canvas.create_text(w // 2, h // 2 + 38, text=category, fill="white",
                            font=("Poppins", 8))

        def _draw_play_icon():
            """Overlay a play button in the center of the canvas."""
            cx, cy = w // 2, h // 2
            # Tkinter doesn't support 8-digit hex (alpha). Use stipple for transparency.
            canvas.create_oval(cx - 20, cy - 20, cx + 20, cy + 20,
                            fill="black", outline="",
                            stipple="gray50")
            canvas.create_polygon(
                cx - 7, cy - 10,
                cx - 7, cy + 10,
                cx + 13, cy,
                fill="white", outline=""
            )

        if not img_path:
            _draw_placeholder()
            return

        filename = os.path.basename(str(img_path).replace("\\", "/"))
        ext      = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        # ── VIDEO: generate thumbnail via FFmpeg ──────────────────────────────────
        if ext in ("mp4", "mov", "avi", "mkv", "webm"):
            try:
                from PIL import Image

                # Resolve video file path
                video_path = None
                candidates = [
                    img_path if os.path.isabs(img_path) else None,
                    os.path.join(UPLOAD_DIR, filename),
                ]
                for c in candidates:
                    if c and os.path.exists(c):
                        video_path = c
                        break

                # Try fetching from Flask if not found locally
                if not video_path:
                    print(f"[UserHomepage] video not found locally: {filename}")
                    _draw_placeholder()
                    _draw_play_icon()
                    return

                thumb_path = os.path.join(
                    tempfile.gettempdir(), f"uh_thumb_{filename}.jpg")

                # Use cached thumbnail if available
                if not os.path.exists(thumb_path):
                    cmd = [FFMPEG, "-y", "-i", video_path,
                        "-ss", "00:00:01", "-vframes", "1",
                        "-vf", "scale=640:-1", "-q:v", "3",
                        thumb_path]
                    result = subprocess.run(cmd, capture_output=True, timeout=30)
                    if result.returncode != 0:
                        err = result.stderr.decode("utf-8", errors="replace")[-200:]
                        print(f"[UserHomepage] FFmpeg failed: {err}")

                if os.path.exists(thumb_path):
                    img = Image.open(thumb_path)
                    img.load()
                    _show(img)          # draw thumbnail
                    _draw_play_icon()   # overlay play icon on top
                    return

            except Exception as e:
                print(f"[UserHomepage] video thumb error: {e}")

            # Fallback for video — show placeholder + play icon
            _draw_placeholder()
            _draw_play_icon()
            return

        # ── IMAGE: local file then Flask server ───────────────────────────────────
        try:
            from PIL import Image

            candidates = []
            if os.path.isabs(img_path) or (len(img_path) > 1 and img_path[1] == ":"):
                candidates.append(img_path)
            candidates += [
                os.path.join(UPLOAD_DIR, filename),
                os.path.join("static", "uploads", filename),
            ]
            local_path = next((p for p in candidates if os.path.exists(p)), None)

            img = None
            if local_path:
                try:
                    img = Image.open(local_path)
                    img.load()
                except Exception:
                    img = None

            if img is None:
                for url in [
                    f"{flask_url}/static/uploads/{filename}",
                    f"{flask_url}/static/uploads/avatars/{filename}",
                ]:
                    try:
                        import io as _io
                        with urllib.request.urlopen(url, timeout=6) as resp:
                            data = resp.read()
                        img = Image.open(_io.BytesIO(data))
                        img.load()
                        break
                    except Exception:
                        continue

            if img:
                _show(img)
                return

        except Exception as e:
            print(f"[UserHomepage] image load error: {e}")

        # ── Styled placeholder ────────────────────────────────────────────────────
        _draw_placeholder()

    @staticmethod
    def _darken(hex_color: str, factor: float = 0.75) -> str:
        """Return a darkened version of a hex colour for stripe contrast."""
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            r, g, b = int(r * factor), int(g * factor), int(b * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return "#333333"

    # ── Footer ────────────────────────────────────────────────────────────────

    def _make_footer(self):
        T = self.theme
        self.footer = tk.Frame(self.root, bg=T["navy"], height=FOOTER_H)
        self.footer.place(x=0, rely=1.0, anchor="sw", relwidth=1)
        self.footer.pack_propagate(False)

        inner = tk.Frame(self.footer, bg=T["navy"])
        inner.pack(fill="x", padx=36)

        tk.Label(inner, text="© 2025 The Gears",
                 font=FONTS["small_bold"], fg=T["white"],
                 bg=T["navy"]).pack(side="left", pady=16)
        tk.Label(inner, text="WRITE WITHOUT FAVOR. EXPRESS WITHOUT FEAR.",
                 font=FONTS["small"], fg="#7F8AA8",
                 bg=T["navy"]).pack(side="right", pady=16)

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

    # ── Toggles / navigation ──────────────────────────────────────────────────

    def _toggle_dark(self):
        self.dark_mode = not self.dark_mode
        self.theme     = self.dark if self.dark_mode else self.light
        self._rebuild()

    def _filter_by_cat(self, cat: str):
        self._cat_filter   = cat
        self._search_query = ""
        self._clear_search()
        self._apply_filter()

    def _go_home(self):
        self._cat_filter     = "All"
        self._search_query   = ""
        self._shown_articles = list(self._all_articles)
        self._clear_search()
        self._render_content()

    def _go_to_profile(self):
        self._close_account_menu()
        if hasattr(self.root, "show_user_profile"):
            target_user = self.user or getattr(self.root, "current_user", None)
            if target_user:
                self.root.show_user_profile(target_user)
            else:
                print("[UserHomepage] No user to show profile for")

    def _logout(self):
        self._toggle_account_menu()
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            if hasattr(self.root, "show_landing"):
                self.root.show_landing()
            else:
                self.root.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    DUMMY = [
        (1, "Campus Paper Launches New Digital Edition",
         "Body text here.", "NEWS",     "2025-05-01", "Juan",  "Dela Cruz", None),
        (2, "Why Student Voices Still Matter in Modern Campuses",
         "Body text here.", "OPINION",  "2025-04-28", "Maria", "Santos",    None),
        (3, "A Collection of Campus Poems from This Semester",
         "Body text here.", "LITERARY", "2025-04-20", "Ana",   "Reyes",     None),
        (4, "End-of-Year Sports Recap: Highs and Lows",
         "Body text here.", "UPDATES",  "2025-04-15", "Ben",   "Cruz",      None),
        (5, "Feature: Student Art Showcase 2025",
         "Body text here.", "FEATURE",  "2025-04-10", "Cara",  "Tan",       None),
        (6, "Komiks: Campus Life Edition Vol. 3",
         "Body text here.", "KOMIKS",   "2025-04-05", "Dan",   "Lim",       None),
        (7, "Photos from the Annual Foundation Day Celebrations",
         "Body text here.", "PHOTOS",   "2025-04-01", "Eve",   "Garcia",    None),
        (8, "Breaking: Administration Announces New Curriculum",
         "Body text here.", "NEWS",     "2025-05-10", "Felix", "Ramos",     None),
        (9, "Opinion: Is Online Learning Here to Stay?",
         "Body text here.", "OPINION",  "2025-05-08", "Grace", "Villanueva",None),
    ]

    root = tk.Tk()
    root.title("The Gears — Home")
    root.geometry("1280x800")
    root.minsize(900, 600)

    root.show_article_detail = lambda aid, user=None: print(f"→ Open article {aid}")
    root.show_landing         = lambda: print("→ Go to landing")

    UserHomepage(
        root,
        user=("Maria", "Santos", "maria@gears.com", 1, "user"),
        db_callbacks={"fetch_homepage_articles": lambda: DUMMY},
    )
    root.mainloop()