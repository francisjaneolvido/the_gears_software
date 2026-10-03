"""
superadmin/superadmin_categories.py
────────────────────────────────────
Categories management page — UI matches the web version (categories.html).

Layout mirrors:
  • 4-column card grid with colour-accent top bar per card
  • Article count pill (green dot), Edit / Archive / Delete actions per card
  • Click card → Detail panel with article list and back button
  • FAB-style "＋ Add Category" button (top-right of header)
  • Add / Edit modal: name field, emoji icon picker, hex entry + colour-palette swatches
  • Archived section below active grid (dashed separator, greyed cards)
  • Dark-mode via SuperadminLayout theme

db_callbacks keys (unchanged from original)
────────────────────────────────────────────
  fetch_categories()                          → list[dict]
  fetch_articles_by_category(category_name)  → list[dict]
  add_category(name, icon, color)             → bool
  update_category(cat_id, name, icon, color)  → bool
  archive_category(cat_id)                    → bool
  unarchive_category(cat_id)                  → bool
  delete_category(cat_id)                     → bool
"""

import tkinter as tk
from tkinter import messagebox, colorchooser
from tkinter import ttk

try:
    from superadmin.superadmin_layout import SuperadminLayout
    from theme import COLORS, FONTS
except ImportError:
    from superadmin_layout import SuperadminLayout
    COLORS = {
        "primary_orange":       "#F5821F",
        "primary_orange_dark":  "#D97E10",
        "primary_orange_light": "#FFE1CC",
        "primary_red":          "#B02029",
        "background":           "#F8F6F3",
        "background_alt":       "#F0EDE8",
        "card":                 "#FFFFFF",
        "white":                "#FFFFFF",
        "text_dark":            "#333333",
        "text_mid":             "#555555",
        "text_grey":            "#777777",
        "text_light":           "#9E9E9E",
        "border":               "#E5E0D8",
        "navy":                 "#0C1633",
        "success":              "#15803D",
        "input_bg":             "#F5F3F0",
        "shadow":               "#E8DDD5",
        "tab_active":           "#F5821F",
        "tab_inactive_fg":      "#777777",
    }
    FONTS = {
        "heading":    ("Poppins", 15, "bold"),
        "section":    ("Poppins", 13, "bold"),
        "body":       ("Poppins", 10),
        "body_bold":  ("Poppins", 10, "bold"),
        "small":      ("Poppins", 9),
        "small_bold": ("Poppins", 9, "bold"),
        "button":     ("Poppins", 9, "bold"),
        "tag":        ("Poppins", 8, "bold"),
        "input":      ("Poppins", 10),
        "modal_title":("Poppins", 13, "bold"),
    }

COLS = 4

COLOR_PALETTE = [
    "#fb923c", "#f97316", "#fbbf24", "#f59e0b",
    "#3b82f6", "#2563eb", "#0ea5e9", "#22c55e",
    "#16a34a", "#a855f7", "#6366f1", "#ec4899",
    "#14b8a6", "#ef4444", "#92400e",
]

ICON_OPTIONS = [
    "📰","📢","💬","⭐","📚","✏️","📷","🎨",
    "🏆","🎭","🔬","🌐","🏅","📊","🎵","🎬",
]

DEMO_CATEGORIES = [
    {"id": 1, "name": "NEWS",     "icon": "📰", "color": "#fb923c", "archived": False, "article_count": 0},
    {"id": 2, "name": "UPDATES",  "icon": "📢", "color": "#3b82f6", "archived": False, "article_count": 0},
    {"id": 3, "name": "OPINION",  "icon": "💬", "color": "#a855f7", "archived": False, "article_count": 0},
    {"id": 4, "name": "FEATURE",  "icon": "⭐", "color": "#22c55e", "archived": False, "article_count": 0},
    {"id": 5, "name": "KOMIKS",   "icon": "📚", "color": "#f97373", "archived": False, "article_count": 0},
    {"id": 6, "name": "LITERARY", "icon": "✏️", "color": "#92400e", "archived": False, "article_count": 0},
    {"id": 7, "name": "PHOTOS",   "icon": "📷", "color": "#14b8a6", "archived": False, "article_count": 0},
]

MATERIAL_TO_EMOJI = {
    "article":       "📰",
    "update":        "🔄",
    "mode_comment":  "💬",
    "star":          "⭐",
    "menu_book":     "📚",
    "edit_note":     "✏️",
    "photo_library": "📷",
    "palette":       "🎨",
    "videocam":      "🎬",
    "category":      "📁",
    "folder":        "📁",
    "image":         "🖼️",
}

class SuperadminCategories(SuperadminLayout):
    """
    Superadmin – Categories page.

    Visual design mirrors categories.html (web):
      • Card grid with coloured top-bar accent
      • Detail panel with article list
      • Add/Edit modal with emoji picker + colour palette
      • Archive / unarchive / delete flows
    """

    ACTIVE_NAV = "categories"

    def __init__(self, root, user=None, db_callbacks=None):
        self._categories: list = []
        self._detail_cat       = None
        self._view             = "grid"
        super().__init__(root, user, db_callbacks)
        self._build_page()

    # ══════════════════════════════════════════════════════════════════════
    #  Page bootstrap
    # ══════════════════════════════════════════════════════════════════════

    def _build_page(self):
        self._view       = "grid"
        self._detail_cat = None
        self._build_page_header()
        self._scroll_body = tk.Frame(self.inner, bg=self.theme["background"])
        self._scroll_body.pack(fill="both", expand=True)
        self._load_categories()

    # ── Page header ───────────────────────────────────────────────────────

    def _build_page_header(self):
        T = self.theme
        wrap = tk.Frame(self.inner, bg=T["background"])
        wrap.pack(fill="x", pady=(0, 16))

        left = tk.Frame(wrap, bg=T["background"])
        left.pack(side="left", fill="x", expand=True)

        tk.Label(
            left, text="Categories",
            bg=T["background"], fg=T["primary_orange"],
            font=("Poppins", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Organize and manage the content sections used across The Gears.",
            bg=T["background"], fg=T["text_grey"],
            font=FONTS["body"],
        ).pack(anchor="w", pady=(2, 0))

        tk.Button(
            wrap, text="＋  Add Category",
            command=self._open_add_modal,
            bg=T["primary_orange"], fg=T["white"],
            activebackground=T["primary_orange_dark"],
            activeforeground=T["white"],
            font=("Poppins", 10, "bold"),
            bd=0, relief="flat", padx=16, pady=9, cursor="hand2",
        ).pack(side="right", padx=(12, 0))

    # ══════════════════════════════════════════════════════════════════════
    #  Data
    # ══════════════════════════════════════════════════════════════════════

    def _load_categories(self):
        cb = self.callbacks.get("fetch_categories")
        if cb:
            try:
                self._categories = cb() or []
            except Exception as e:
                print(f"[Categories] fetch error: {e}")
                self._categories = list(DEMO_CATEGORIES)
        else:
            self._categories = [dict(c) for c in DEMO_CATEGORIES]
        self._render_grid()

    def _fetch_articles(self, category_name):
        cb = self.callbacks.get("fetch_articles_by_category")
        if cb:
            try:
                return cb(category_name) or []
            except Exception as e:
                print(f"[Categories] fetch_articles error: {e}")
        return []

    # ══════════════════════════════════════════════════════════════════════
    #  Grid view
    # ══════════════════════════════════════════════════════════════════════

    def _render_grid(self):
        T = self.theme
        for w in self._scroll_body.winfo_children():
            w.destroy()

        active   = [c for c in self._categories if not c.get("archived")]
        archived = [c for c in self._categories if     c.get("archived")]

        # ── outer shell card ──────────────────────────────────────────────
        shell = tk.Frame(
            self._scroll_body, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        shell.pack(fill="both", expand=True, padx=2, pady=2)

        # shell top bar: label + count pill
        top_row = tk.Frame(shell, bg=T["card"])
        top_row.pack(fill="x", padx=18, pady=(14, 0))

        self._count_lbl = tk.Label(
            top_row,
            text=f"{len(active)} active categor{'y' if len(active)==1 else 'ies'}",
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            font=FONTS["tag"], padx=10, pady=4,
        )
        self._count_lbl.pack(side="right")

        # ── active grid ───────────────────────────────────────────────────
        active_grid = tk.Frame(shell, bg=T["card"])
        active_grid.pack(fill="x", padx=16, pady=(8, 6))

        if not active:
            tk.Label(
                active_grid,
                text="No active categories yet. Use '+ Add Category' to create one.",
                bg=T["card"], fg=T["text_grey"],
                font=FONTS["body"], pady=24,
            ).pack()
        else:
            for col in range(COLS):
                active_grid.columnconfigure(col, weight=1, uniform="ag")
            for idx, cat in enumerate(active):
                self._category_card(active_grid, cat, idx // COLS, idx % COLS)

        # ── archived section ──────────────────────────────────────────────
        # ── archived section ──────────────────────────────────────────────
        sep = tk.Frame(shell, bg=T["border"], height=1)
        sep.pack(fill="x", padx=16, pady=(4, 0))

        arch_hdr = tk.Frame(shell, bg=T["card"])
        arch_hdr.pack(fill="x", padx=18, pady=(10, 2))
        tk.Label(arch_hdr, text="ARCHIVED CATEGORIES",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["tag"]).pack(anchor="w")
        tk.Label(arch_hdr,
                 text="Kept for reference and history. Hidden from active workflows.",
                 bg=T["card"], fg=T["text_light"],
                 font=FONTS["small"]).pack(anchor="w", pady=(2, 0))

        arch_grid = tk.Frame(shell, bg=T["card"])
        arch_grid.pack(fill="x", padx=16, pady=(4, 12))

        if archived:
            for col in range(COLS):
                arch_grid.columnconfigure(col, weight=1, uniform="rg")
            for idx, cat in enumerate(archived):
                self._category_card(arch_grid, cat, idx // COLS, idx % COLS, archived=True)
        else:
            tk.Label(
                arch_hdr,
                text="No archived categories.",
                bg=T["card"], fg=T["text_light"],
                font=FONTS["small"],
            ).pack(anchor="w", pady=(4, 0))

    def _category_card(self, parent, cat, row, col, archived=False):
        T      = self.theme
        color  = cat.get("color", T["primary_orange"])
        icon   = cat.get("icon", "📁")
        name   = cat.get("name", "")
        count  = cat.get("article_count", 0)

        # outer padding cell
        outer = tk.Frame(parent, bg=T["card"], padx=5, pady=5)
        outer.grid(row=row, column=col, sticky="nsew")

        border_c = color if not archived else T["border"]
        cframe = tk.Frame(
            outer, bg=T["card"],
            highlightbackground=border_c, highlightthickness=1,
            cursor="hand2",
        )
        cframe.pack(fill="both", expand=True)

        # coloured top accent bar (like the web's gradient top border)
        bar_color = color if not archived else T["border"]
        tk.Frame(cframe, bg=bar_color, height=4).pack(fill="x")

        inner = tk.Frame(cframe, bg=T["card"])
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        # icon + name row
        top = tk.Frame(inner, bg=T["card"])
        top.pack(fill="x")

        icon_circle = tk.Canvas(top, width=32, height=32,
                                bg=T["card"], highlightthickness=0)
        icon_circle.pack(side="left", padx=(0, 8))
        # Circular background for icon, using the category colour at low alpha
        icon_circle.create_oval(1, 1, 31, 31,
                                fill="#f9fafb", outline=color, width=1)
        icon_circle.create_text(16, 16, text=icon, font=("Poppins", 14))

        name_lbl = tk.Label(
            top, text=name,
            bg=T["card"],
            fg=T["text_dark"] if not archived else T["text_grey"],
            font=FONTS["body_bold"], anchor="w",
        )
        name_lbl.pack(side="left", fill="x", expand=True)

        # count pill + action row
        bottom = tk.Frame(inner, bg=T["card"])
        bottom.pack(fill="x", pady=(10, 0))

        # pill
        pill_bg = T["primary_orange_light"] if not archived else T["background_alt"]
        pill_fg = T["primary_orange"]        if not archived else T["text_grey"]
        dot_col = "#10b981"                   if not archived else "#9ca3af"

        pill = tk.Frame(bottom, bg=pill_bg)
        pill.pack(side="left")
        dot = tk.Canvas(pill, width=8, height=8,
                        bg=pill_bg, highlightthickness=0)
        dot.pack(side="left", padx=(6, 2), pady=5)
        dot.create_oval(1, 1, 7, 7, fill=dot_col, outline="")
        tk.Label(pill,
                 text=f"{count} item{'s' if count != 1 else ''}",
                 bg=pill_bg, fg=pill_fg,
                 font=FONTS["tag"], padx=4, pady=4).pack(side="left")

        # action buttons (right side)
        acts = tk.Frame(inner, bg=T["card"])
        acts.pack(fill="x", pady=(8, 0))

        tk.Button(acts, text="Edit",
                  command=lambda c=cat: self._open_edit_modal(c),
                  bg=T["background_alt"], fg=T["text_mid"],
                  activebackground=T["primary_orange_light"],
                  activeforeground=T["primary_orange"],
                  font=FONTS["small_bold"], bd=0, relief="flat",
                  padx=7, pady=3, cursor="hand2").pack(side="left", padx=(0, 4))

        arch_lbl = "Unarchive" if archived else "Archive"
        tk.Button(acts, text=arch_lbl,
                  command=lambda c=cat: (
                      self._do_unarchive(c) if c.get("archived") else self._do_archive(c)
                  ),
                  bg=T["background_alt"], fg=T["text_mid"],
                  activebackground=T["primary_orange_light"],
                  activeforeground=T["primary_orange"],
                  font=FONTS["small_bold"], bd=0, relief="flat",
                  padx=7, pady=3, cursor="hand2").pack(side="left", padx=(0, 4))

        tk.Button(acts, text="Open  ›",
                  command=lambda c=cat: self._open_detail(c),
                  bg=T["primary_orange_light"], fg=T["primary_orange"],
                  activebackground=T["primary_orange"],
                  activeforeground=T["white"],
                  font=FONTS["small_bold"], bd=0, relief="flat",
                  padx=7, pady=3, cursor="hand2").pack(side="right")

        # hover highlight + whole-card click
        def _click(e=None, c=cat):
            self._open_detail(c)

        def _enter(e, f=cframe, bc=border_c):
            f.configure(highlightbackground=bc, highlightthickness=2)

        def _leave(e, f=cframe, bc=border_c):
            f.configure(highlightbackground=bc, highlightthickness=1)

        for w in [cframe, inner, top, name_lbl, icon_circle]:
            w.bind("<Button-1>", _click)
            w.bind("<Enter>",    _enter)
            w.bind("<Leave>",    _leave)

    # ══════════════════════════════════════════════════════════════════════
    #  Detail view  (mirrors web detail-screen)
    # ══════════════════════════════════════════════════════════════════════

    def _open_detail(self, cat):
        T = self.theme
        self._detail_cat = cat
        for w in self._scroll_body.winfo_children():
            w.destroy()

        color = cat.get("color", T["primary_orange"])
        name  = cat.get("name", "")
       

        # ── back button row ───────────────────────────────────────────────
        nav = tk.Frame(self._scroll_body, bg=T["background"])
        nav.pack(fill="x", pady=(0, 10))

        tk.Button(
            nav, text="←  Back to categories",
            command=self._go_back,
            bg=T["background_alt"], fg=T["text_mid"],
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"],
            font=FONTS["button"], bd=0, relief="flat",
            padx=12, pady=6, cursor="hand2",
        ).pack(side="left")

        # article count chip (right)
        self._detail_count_lbl = tk.Label(
            nav,
            text="Loading…",
            bg=T["background_alt"], fg=T["text_grey"],
            font=FONTS["small"], padx=10, pady=6,
        )
        self._detail_count_lbl.pack(side="right")

        # ── detail card ───────────────────────────────────────────────────
        card = tk.Frame(
            self._scroll_body, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        card.pack(fill="both", expand=True)

        tk.Frame(card, bg=color, height=4).pack(fill="x")

        inner = tk.Frame(card, bg=T["card"])
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        # category title row
        title_row = tk.Frame(inner, bg=T["card"])
        title_row.pack(fill="x", pady=(0, 4))

        icon_raw  = cat.get("icon", "📁")
        icon_type = cat.get("icon_type", "emoji")
        if icon_type == "material":
            display_icon = MATERIAL_TO_EMOJI.get(icon_raw, "📁")
        elif icon_type == "link":
            display_icon = "🖼️"
        else:
            display_icon = icon_raw
        tk.Label(
            title_row,
            text=f"{display_icon}  {name}",
            bg=T["card"], fg=color,
            font=("Poppins", 18, "bold"),
        ).pack(side="left")

        tk.Label(
            inner,
            text="Compilation of articles in this category.",
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["body"],
        ).pack(anchor="w", pady=(0, 12))

        tk.Frame(inner, bg=T["border"], height=1).pack(fill="x", pady=(0, 12))

        # article list box
        list_bg = T["input_bg"]
        list_box = tk.Frame(
            inner, bg=list_bg,
            highlightbackground=T["border"], highlightthickness=1,
        )
        list_box.pack(fill="both", expand=True)

        list_hdr = tk.Frame(list_box, bg=list_bg)
        list_hdr.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(list_hdr, text="Latest articles in this category",
                 bg=list_bg, fg=T["text_grey"],
                 font=FONTS["small_bold"]).pack(side="left")

        view_all_btn = tk.Button(
            list_hdr, text="View all  ›",
            command=lambda: None,
            bg=list_bg, fg=T["primary_orange"],
            activebackground=list_bg,
            activeforeground=T["primary_orange_dark"],
            font=FONTS["small"], bd=0, relief="flat", cursor="hand2",
        )
        view_all_btn.pack(side="right")

        # scrollable article list
        canvas = tk.Canvas(list_box, bg=list_bg,
                           highlightthickness=0, height=300)
        canvas.pack(side="left", fill="both", expand=True)
        vsb = ttk.Scrollbar(list_box, orient="vertical", command=canvas.yview)
        vsb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=vsb.set)

        art_frame = tk.Frame(canvas, bg=list_bg)
        win_id = canvas.create_window((0, 0), window=art_frame, anchor="nw")

        art_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win_id, width=e.width),
        )

        # load + display articles
        articles = self._fetch_articles(name)
        count    = len(articles)
        self._detail_count_lbl.configure(
            text=f"{count} article{'s' if count != 1 else ''}")

        if not articles:
            tk.Label(
                art_frame,
                text="No published articles in this category yet.\n"
                     "Approve published articles and they will be compiled automatically.",
                bg=list_bg, fg=T["text_grey"],
                font=FONTS["body"], pady=24, justify="center",
            ).pack()
        else:
            for i, art in enumerate(articles[:10]):
                self._article_row(art_frame, art, i, list_bg)

    def _article_row(self, parent, art, idx, list_bg):
        T      = self.theme
        row_bg = T["card"] if idx % 2 == 0 else list_bg

        row = tk.Frame(
            parent, bg=row_bg,
            highlightbackground=T["border"], highlightthickness=1,
            cursor="hand2",
        )
        row.pack(fill="x", padx=8, pady=(0, 4))

        # coloured initial badge
        badge = tk.Canvas(row, width=50, height=50,
                          bg=row_bg, highlightthickness=0)
        badge.pack(side="left", padx=(10, 10), pady=8)
        badge.create_oval(3, 3, 47, 47,
                          fill="#f97316", outline="")
        initial = (art.get("category") or art.get("headline") or "S")[0].upper()
        badge.create_text(25, 25, text=initial,
                          fill="white", font=("Poppins", 15, "bold"))

        meta = tk.Frame(row, bg=row_bg)
        meta.pack(side="left", fill="x", expand=True, pady=8)

        tk.Label(
            meta,
            text=art.get("headline") or art.get("title") or "Untitled article",
            bg=row_bg, fg=T["text_dark"],
            font=FONTS["body_bold"], anchor="w",
        ).pack(anchor="w")

        author = art.get("author") or art.get("submitted_by") or "The Gears"
        date   = art.get("date") or art.get("created_at") or ""
        sub    = f"{author}  ·  {date}" if date else author
        tk.Label(meta, text=sub,
                 bg=row_bg, fg=T["text_grey"],
                 font=FONTS["small"], anchor="w").pack(anchor="w", pady=(2, 0))

        # hover tint
        def _enter(e, f=row, b=row_bg):
            f.configure(bg="#f3f4f6")
        def _leave(e, f=row, b=row_bg):
            f.configure(bg=b)

        row.bind("<Enter>", _enter)
        row.bind("<Leave>", _leave)

    def _go_back(self):
        self._detail_cat = None
        self._render_grid()

    # ══════════════════════════════════════════════════════════════════════
    #  Add / Edit modal  (mirrors web modal-backdrop-custom)
    # ══════════════════════════════════════════════════════════════════════

    def _open_add_modal(self):
        self._category_modal(mode="add")

    def _open_edit_modal(self, cat):
        self._category_modal(mode="edit", cat=cat)

    def _category_modal(self, mode="add", cat=None):
        T   = self.theme
        win = tk.Toplevel(self.root)
        win.title("Add New Category" if mode == "add" else "Edit Category")
        win.configure(bg=T["card"])
        win.resizable(False, False)
        win.grab_set()
        win.transient(self.root)

        win.update_idletasks()
        px = self.root.winfo_rootx() + self.root.winfo_width()  // 2 - 230
        py = self.root.winfo_rooty() + self.root.winfo_height() // 2 - 270
        win.geometry(f"460x560+{px}+{py}")

        # orange top accent bar
        tk.Frame(win, bg=T["primary_orange"], height=4).pack(fill="x")

        body = tk.Frame(win, bg=T["card"])
        body.pack(fill="both", expand=True, padx=22, pady=18)

        # ── header row ────────────────────────────────────────────────────
        hrow = tk.Frame(body, bg=T["card"])
        hrow.pack(fill="x", pady=(0, 4))

        title_txt = "Add New Category" if mode == "add" else "Edit Category"
        tk.Label(hrow, text=title_txt,
                 bg=T["card"], fg=T["text_dark"],
                 font=FONTS["modal_title"]).pack(side="left")
        tk.Button(hrow, text="✕", command=win.destroy,
                  bg=T["card"], fg=T["text_grey"],
                  font=("Poppins", 11), bd=0, relief="flat",
                  cursor="hand2").pack(side="right")

        tk.Label(body,
                 text="Organize and manage content sections.",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small"]).pack(anchor="w", pady=(0, 12))

        tk.Frame(body, bg=T["border"], height=1).pack(fill="x", pady=(0, 14))

        # ── name field ────────────────────────────────────────────────────
        tk.Label(body, text="Category name",
                 bg=T["card"], fg=T["text_dark"],
                 font=FONTS["small_bold"], anchor="w").pack(fill="x", pady=(0, 4))
        name_var = tk.StringVar(value=cat.get("name", "") if cat else "")
        name_entry = tk.Entry(
            body, textvariable=name_var, font=FONTS["input"],
            bg=T["input_bg"], fg=T["text_dark"], relief="flat",
            insertbackground=T["primary_orange"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        name_entry.pack(fill="x", ipady=7, pady=(0, 14))

        # ── icon picker ───────────────────────────────────────────────────
        tk.Label(body, text="Category icon",
                 bg=T["card"], fg=T["text_dark"],
                 font=FONTS["small_bold"], anchor="w").pack(fill="x", pady=(0, 4))

        icon_var = tk.StringVar(value=cat.get("icon", "📰") if cat else "📰")

        icon_row = tk.Frame(body, bg=T["card"])
        icon_row.pack(fill="x", pady=(0, 14))

        # large preview of selected icon
        icon_preview = tk.Label(icon_row, text=icon_var.get(),
                                bg=T["input_bg"], font=("Poppins", 22),
                                width=3, pady=4,
                                highlightbackground=T["border"],
                                highlightthickness=1)
        icon_preview.pack(side="left", padx=(0, 10))

        icon_grid = tk.Frame(icon_row, bg=T["card"])
        icon_grid.pack(side="left")

        def _pick_icon(em, v=icon_var, lbl=icon_preview):
            v.set(em)
            lbl.configure(text=em)

        for i, em in enumerate(ICON_OPTIONS):
            btn = tk.Button(
                icon_grid, text=em, font=("Poppins", 12),
                command=lambda e=em: _pick_icon(e),
                bd=0, relief="flat", bg=T["card"], cursor="hand2",
                padx=3, pady=2,
            )
            btn.grid(row=i // 8, column=i % 8, padx=1, pady=1)

            def _btn_enter(e, b=btn, T=T):
                b.configure(bg=T["primary_orange_light"])
            def _btn_leave(e, b=btn, T=T):
                b.configure(bg=T["card"])
            btn.bind("<Enter>", _btn_enter)
            btn.bind("<Leave>", _btn_leave)

        # ── colour section ────────────────────────────────────────────────
        tk.Label(body, text="Color",
                 bg=T["card"], fg=T["text_dark"],
                 font=FONTS["small_bold"], anchor="w").pack(fill="x", pady=(0, 4))

        color_var = tk.StringVar(
            value=cat.get("color", COLOR_PALETTE[0]) if cat else COLOR_PALETTE[0])

        # hex input row
        hex_row = tk.Frame(body, bg=T["card"])
        hex_row.pack(fill="x", pady=(0, 6))

        tk.Label(hex_row, text="Hex:",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small"]).pack(side="left", padx=(0, 4))

        hex_var = tk.StringVar(value=color_var.get())
        hex_entry = tk.Entry(
            hex_row, textvariable=hex_var,
            font=FONTS["small"], width=10,
            bg=T["input_bg"], fg=T["text_dark"], relief="flat",
            highlightbackground=T["border"], highlightthickness=1,
        )
        hex_entry.pack(side="left", ipady=5, padx=(0, 8))

        # colour preview circle
        preview = tk.Canvas(hex_row, width=26, height=26,
                            bg=T["card"], highlightthickness=0)
        preview.pack(side="left", padx=(0, 8))
        preview_oval = preview.create_oval(2, 2, 24, 24,
                                           fill=color_var.get(), outline="")

        tk.Button(hex_row, text="🎨 Pick",
                  command=lambda: _open_chooser(),
                  bg=T["primary_orange_light"], fg=T["primary_orange"],
                  activebackground=T["primary_orange"],
                  activeforeground=T["white"],
                  font=FONTS["small"], bd=0, relief="flat",
                  padx=8, pady=4, cursor="hand2").pack(side="left")

        def _sync_color(val):
            color_var.set(val)
            hex_var.set(val)
            preview.itemconfig(preview_oval, fill=val)

        def _hex_changed(*_):
            val = hex_var.get().strip()
            if val.startswith("#") and len(val) in (4, 7):
                try:
                    preview.winfo_rgb(val)
                    _sync_color(val)
                except Exception:
                    pass

        hex_var.trace_add("write", _hex_changed)

        def _open_chooser():
            _, hx = colorchooser.askcolor(
                color=color_var.get(), parent=win, title="Pick a colour")
            if hx:
                _sync_color(hx)

        # palette caption
        tk.Label(body,
                 text="Tap a colour from the palette below or type your own hex code.",
                 bg=T["card"], fg=T["text_light"],
                 font=FONTS["small"]).pack(anchor="w", pady=(0, 4))

        # colour palette swatches (mirrors web .color-grid)
        swatch_frame = tk.Frame(body, bg=T["card"])
        swatch_frame.pack(fill="x", pady=(0, 16))

        self._swatch_canvases = {}

        for i, c in enumerate(COLOR_PALETTE):
            sw = tk.Canvas(swatch_frame, width=24, height=24,
                           bg=T["card"], highlightthickness=0, cursor="hand2")
            sw.pack(side="left", padx=3, pady=2)
            ov = sw.create_oval(2, 2, 22, 22, fill=c, outline="")
            self._swatch_canvases[c] = (sw, ov)

            def _pick_swatch(col=c, sv=_sync_color):
                sv(col)
                # show check mark on selected swatch
                for hx, (s, o) in self._swatch_canvases.items():
                    s.delete("check")
                    if hx == col:
                        s.create_text(12, 12, text="✓", fill="white",
                                      font=("Poppins", 9, "bold"), tags="check")

            sw.bind("<Button-1>", lambda e, f=_pick_swatch: f())

            def _sw_enter(e, s=sw, col=c):
                s.configure(highlightbackground=col, highlightthickness=1)
            def _sw_leave(e, s=sw):
                s.configure(highlightthickness=0)
            sw.bind("<Enter>", _sw_enter)
            sw.bind("<Leave>", _sw_leave)

        # ── footer buttons ────────────────────────────────────────────────
        tk.Frame(body, bg=T["border"], height=1).pack(fill="x", pady=(0, 12))

        btn_row = tk.Frame(body, bg=T["card"])
        btn_row.pack(fill="x")

        # Delete button only in edit mode (far left, like web #modalDeleteBtn)
        if mode == "edit" and cat:
            tk.Button(
                btn_row, text="🗑  Delete",
                command=lambda: self._confirm_delete(cat, win),
                bg="#fff0f0", fg=T["primary_red"],
                activebackground=T["primary_red"],
                activeforeground=T["white"],
                font=FONTS["button"], bd=0, relief="flat",
                padx=10, pady=7, cursor="hand2",
            ).pack(side="left")

        tk.Button(btn_row, text="Cancel", command=win.destroy,
                  bg=T["background_alt"], fg=T["text_grey"],
                  activebackground=T["border"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=12, pady=7, cursor="hand2").pack(side="right", padx=(6, 0))

        save_lbl = "Save Changes" if mode == "edit" else "Add"
        tk.Button(
            btn_row, text=save_lbl,
            command=lambda: self._save_category(
                mode, cat, name_var, icon_var, color_var, win),
            bg=T["primary_orange"], fg=T["white"],
            activebackground=T["primary_orange_dark"],
            activeforeground=T["white"],
            font=FONTS["button"], bd=0, relief="flat",
            padx=16, pady=7, cursor="hand2",
        ).pack(side="right")

        name_entry.focus_set()
        win.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Return>",  lambda e: self._save_category(
            mode, cat, name_var, icon_var, color_var, win))

    # ══════════════════════════════════════════════════════════════════════
    #  CRUD
    # ══════════════════════════════════════════════════════════════════════

    def _save_category(self, mode, cat, name_var, icon_var, color_var, win):
        name  = name_var.get().strip().upper()
        icon  = icon_var.get().strip()
        color = color_var.get().strip()

        if not name:
            messagebox.showwarning("Validation",
                                   "Category name is required.", parent=win)
            return

        if mode == "add":
            cb = self.callbacks.get("add_category")
            ok = cb(name, icon, color) if cb else None
            if ok is None:
                new_id = max((c["id"] for c in self._categories), default=0) + 1
                self._categories.append({
                    "id": new_id, "name": name, "icon": icon,
                    "color": color, "archived": False, "article_count": 0,
                })
                ok = True
            if ok:
                win.destroy()
                self._load_categories()
                self._show_toast(f"Category '{name}' added successfully!")
            else:
                messagebox.showerror(
                    "Error",
                    "Failed to add category. It may already exist.",
                    parent=win,
                )
        else:
            cb = self.callbacks.get("update_category")
            ok = cb(cat["id"], name, icon, color) if cb else None
            if ok is None:
                for c in self._categories:
                    if c["id"] == cat["id"]:
                        c.update({"name": name, "icon": icon, "color": color})
                ok = True
            if ok:
                win.destroy()
                self._load_categories()
                self._show_toast(f"Category '{name}' updated successfully!")
            else:
                messagebox.showerror("Error",
                                     "Failed to update category.", parent=win)

    def _do_archive(self, cat):
        print(f"[DEBUG] Archiving cat: {cat}")
        if not messagebox.askyesno(
            "Archive Category",
            f"Archive '{cat['name']}'?\n\n"
            "It will be hidden from active workflows.",
        ):
            return
        cb = self.callbacks.get("archive_category")
        if cb:
            try:
                cb(cat["id"])
            except Exception as e:
                print(f"[archive_category] Error: {e}")
                messagebox.showerror("Error", "Failed to archive category.")
                return
        else:
            for c in self._categories:
                if c["id"] == cat["id"]:
                    c["archived"] = True
        self._load_categories()
        self._show_toast(f"Category '{cat['name']}' archived.")

    def _do_unarchive(self, cat):
        if not messagebox.askyesno(
            "Unarchive Category",
            f"Restore '{cat['name']}'?\n\n"
            "It will become active again.",
        ):
            return
        cb = self.callbacks.get("unarchive_category")
        if cb:
            try:
                cb(cat["id"])
            except Exception as e:
                print(f"[unarchive_category] Error: {e}")
                messagebox.showerror("Error", "Failed to unarchive category.")
                return
        else:
            for c in self._categories:
                if c["id"] == cat["id"]:
                    c["archived"] = False
        self._load_categories()
        self._show_toast(f"Category '{cat['name']}' restored.")


    def _confirm_delete(self, cat, parent_win=None):
        parent_arg = parent_win or self.root
        if not messagebox.askyesno(
            "Delete Category",
            f"Permanently delete '{cat['name']}'?\n\n"
            "This action cannot be undone.",
            parent=parent_arg,
        ):
            return
        cb = self.callbacks.get("delete_category")
        ok = cb(cat["id"]) if cb else None
        if ok is None:
            self._categories = [c for c in self._categories
                                 if c["id"] != cat["id"]]
            ok = True
        if ok:
            if parent_win:
                parent_win.destroy()
            self._load_categories()
            self._show_toast(f"Category '{cat['name']}' deleted.")
        else:
            messagebox.showerror(
                "Error",
                "Failed to delete category. It may still have articles.",
                parent=parent_arg,
            )

    # ══════════════════════════════════════════════════════════════════════
    #  Toast notification  (mimics web showNotification)
    # ══════════════════════════════════════════════════════════════════════

    def _show_toast(self, message: str, success: bool = True):
        """Slide-in notification at bottom-right, auto-dismiss after 3 s."""
        T = self.theme
        bg = "#22c55e" if success else "#ef4444"

        toast = tk.Label(
            self.root,
            text=f"  ✓  {message}  " if success else f"  ✗  {message}  ",
            bg=bg, fg="#ffffff",
            font=FONTS["body_bold"],
            pady=10, padx=4,
            relief="flat",
        )
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        self.root.after(3000, toast.destroy)


# ── standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("The Gears — Categories")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    SuperadminCategories(
        root,
        user=("Francis Jane", "Olvido", "sa@gears.com", 1, "superadmin"),
        db_callbacks={},
    )
    root.mainloop()