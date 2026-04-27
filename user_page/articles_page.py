import tkinter as tk

try:
    from theme import COLORS, FONTS, SPACING, RADIUS
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
        "white": "#FFFFFF",
        "text_dark": "#1A1A1A",
        "text_mid": "#444444",
        "text_grey": "#717171",
        "text_light": "#9E9E9E",
        "border": "#E5E0D8",
        "border_focus": "#F19421",
        "shadow": "#DED6CF",
        "navy": "#0C1633",
        "navy_light": "#1A2A52",
        "input_bg": "#F5F3F0",
        "success": "#2E7D32",
        "error": "#B02029",
    }
    FONTS = {
        "brand": ("Helvetica", 24, "bold"),
        "hero": ("Helvetica", 22, "bold"),
        "heading": ("Helvetica", 18, "bold"),
        "section": ("Helvetica", 14, "bold"),
        "card_title": ("Helvetica", 12, "bold"),
        "body": ("Helvetica", 10),
        "body_bold": ("Helvetica", 10, "bold"),
        "small": ("Helvetica", 9),
        "small_bold": ("Helvetica", 9, "bold"),
        "button": ("Helvetica", 10, "bold"),
        "tag": ("Helvetica", 8, "bold"),
        "input": ("Helvetica", 10),
    }
    RADIUS = {"sm": 4, "md": 8, "lg": 12, "card": 10, "button": 6, "input": 6, "modal": 14}
    SPACING = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 40, "xxl": 64}

try:
    from components.auth_modal import AuthModal
except ImportError:
    AuthModal = None


DARK = {
    "background": "#121212",
    "background_alt": "#1A1A1A",
    "card": "#1F1F1F",
    "text_dark": "#E5E7EB",
    "text_mid": "#D1D5DB",
    "text_grey": "#9CA3AF",
    "text_light": "#6B7280",
    "border": "#333333",
    "navy": "#0C1633",
    "input_bg": "#2A2A2A",
    "white": "#1F1F1F",
    "shadow": "#0A0A0A",
}

SAMPLE_ARTICLES = [
    (1, "Staff Writer", "The Editorial Board", "Campus paper launches new digital desktop edition", "May 2025", "News", None),
    (2, "Ana Reyes", "Ana Reyes", "School administration announces updated academic calendar", "May 2025", "News", None),
    (3, "Mark Santos", "Mark Santos", "Basketball team clinches regional championship title", "Apr 2025", "News", None),
    (4, "The Editors", "The Editors", "Why student voices still matter in modern campus journalism", "May 2025", "Opinion", None),
    (5, "Liza Cruz", "Liza Cruz", "Rethinking how we measure academic success", "Apr 2025", "Opinion", None),
    (6, "Literary Club", "Literary Club", "A collection of poems and visual stories from young writers", "Apr 2025", "Literary", None),
    (7, "Jane Doe", "Jane Doe", "Flash fiction: The last page of a forgotten notebook", "Mar 2025", "Literary", None),
    (8, "Art Dept", "Art Dept", "Student illustrations inspired by campus life", "Apr 2025", "Arts", None),
    (9, "Photo Club", "Photo Club", "Faces of the campus: a student photography exhibit", "Mar 2025", "Photos", None),
    (10, "Feature Desk", "Feature Desk", "Inside the life of a student journalist", "May 2025", "Feature", None),
]

CATEGORIES = ["All", "News", "Updates", "Opinion", "Feature", "Literary", "Komiks", "Arts", "Photos", "Videos"]

CAT_COLORS = {
    "News": ("#E8F5E9", "#2E7D32"),
    "Updates": ("#E3F2FD", "#1565C0"),
    "Opinion": ("#FFF3E0", "#E65100"),
    "Feature": ("#E8EAF6", "#283593"),
    "Literary": ("#F3E5F5", "#6A1B9A"),
    "Komiks": ("#FCE4EC", "#880E4F"),
    "Arts": ("#FFF8E1", "#F57F17"),
    "Photos": ("#E0F2F1", "#00695C"),
    "Videos": ("#EDE7F6", "#4527A0"),
}

PLACEHOLDER_ICONS = {
    "News": "📰",
    "Updates": "📢",
    "Opinion": "✍️",
    "Feature": "🔍",
    "Literary": "📖",
    "Komiks": "🎭",
    "Arts": "🎨",
    "Photos": "📷",
    "Videos": "🎬",
}


def rr_pts(x1, y1, x2, y2, r):
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


def draw_rr(canvas, x1, y1, x2, y2, r=12, **kw):
    return canvas.create_polygon(rr_pts(x1, y1, x2, y2, r), smooth=True, splinesteps=36, **kw)


class PillButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=120, height=38,
                 bg="#FFFFFF", fg="#000000", hover_bg=None, hover_fg=None,
                 border_color=None, font=None, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=parent.cget("bg"),
            cursor="hand2",
            **kwargs
        )
        self.command = command
        self._text = text
        self.w, self.h = width, height
        self.bg_ = bg
        self.fg_ = fg
        self.hbg = hover_bg or bg
        self.hfg = hover_fg or fg
        self.bc = border_color or bg
        self.fnt = font or FONTS["button"]
        self._hov = False
        self._draw()
        self.bind("<Button-1>", lambda e: command() if command else None)
        self.bind("<Enter>", lambda e: self._set(True))
        self.bind("<Leave>", lambda e: self._set(False))

    def _set(self, hovered):
        self._hov = hovered
        self._draw()

    def _draw(self):
        self.delete("all")
        fill = self.hbg if self._hov else self.bg_
        text_fill = self.hfg if self._hov else self.fg_
        r = self.h // 2
        self.create_oval(1, 1, self.h - 1, self.h - 1, fill=fill, outline=self.bc)
        self.create_oval(self.w - self.h + 1, 1, self.w - 1, self.h - 1, fill=fill, outline=self.bc)
        self.create_rectangle(r, 1, self.w - r, self.h - 1, fill=fill, outline=self.bc)
        self.create_line(r, 1, self.w - r, 1, fill=self.bc)
        self.create_line(r, self.h - 1, self.w - r, self.h - 1, fill=self.bc)
        self.create_text(self.w // 2, self.h // 2, text=self._text, fill=text_fill, font=self.fnt)


class ArticlesPage(tk.Frame):
    def __init__(self, parent, user=None, articles=None):
        super().__init__(parent, bg=COLORS["background"])
        self.parent = parent
        self.user = user
        self.articles = articles or SAMPLE_ARTICLES
        self._dark = False
        self._current_cat = "All"
        self._search_query = ""

        self.pack(fill="both", expand=True)
        parent.bind("<Configure>", self._on_resize)
        self._width = parent.winfo_width() or 1100

        self._build_ui()

    def _c(self, key):
        if self._dark and key in DARK:
            return DARK[key]
        return COLORS.get(key, "#FFFFFF")

    def _build_ui(self):
        self._build_navbar()
        self._build_scroll_area()
        self._build_footer()

    def _build_navbar(self):
        self._nav_wrap = tk.Frame(self, bg=self._c("white"))
        self._nav_wrap.pack(fill="x")

        self._nav = tk.Frame(self._nav_wrap, bg=self._c("white"), height=72)
        self._nav.pack(fill="x")
        self._nav.pack_propagate(False)

        tk.Frame(self._nav_wrap, bg=self._c("border"), height=1).pack(fill="x")

        left = tk.Frame(self._nav, bg=self._c("white"))
        left.pack(side="left", padx=36, pady=12)

        logo_c = tk.Canvas(left, width=38, height=38, bg=self._c("white"), highlightthickness=0)
        logo_c.pack(side="left")
        logo_c.create_oval(2, 2, 36, 36, fill=COLORS["primary_orange"], outline="")
        logo_c.create_text(19, 19, text="⬡", fill="white", font=("Helvetica", 12, "bold"))

        brand = tk.Frame(left, bg=self._c("white"))
        brand.pack(side="left", padx=(8, 0))
        tk.Label(brand, text="THE GEARS", font=FONTS["brand"],
                 fg=COLORS["primary_orange"], bg=self._c("white")).pack(anchor="w")
        tk.Label(brand, text="Official Campus Publication", font=FONTS["small"],
                 fg=self._c("text_grey"), bg=self._c("white")).pack(anchor="w")

        right = tk.Frame(self._nav, bg=self._c("white"))
        right.pack(side="right", padx=36, pady=12)

        home_lbl = tk.Label(
            right, text="Home", font=FONTS["body"],
            fg=self._c("text_grey"), bg=self._c("white"), cursor="hand2"
        )
        home_lbl.pack(side="left", padx=10)
        home_lbl.bind("<Enter>", lambda e: home_lbl.config(fg=self._c("text_dark")))
        home_lbl.bind("<Leave>", lambda e: home_lbl.config(fg=self._c("text_grey")))
        home_lbl.bind("<Button-1>", lambda e: self.parent.show_landing())

        for item in ["About", "Contact"]:
            lbl = tk.Label(
                right, text=item, font=FONTS["body"],
                fg=self._c("text_grey"), bg=self._c("white"), cursor="hand2"
            )
            lbl.pack(side="left", padx=10)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=self._c("text_dark")))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=self._c("text_grey")))

        self._cat_btn = PillButton(
            right, text="Category ▾", width=118, height=36,
            bg=self._c("white"), fg=self._c("text_dark"),
            hover_bg=self._c("background_alt"), hover_fg=self._c("text_dark"),
            border_color=self._c("border"),
            command=self._show_category_menu
        )
        self._cat_btn.pack(side="left", padx=6)

        search_wrap = tk.Frame(
            right, bg=self._c("input_bg"),
            highlightbackground=self._c("border"),
            highlightthickness=1, bd=0
        )
        search_wrap.pack(side="left", padx=6)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        self._search_entry = tk.Entry(
            search_wrap,
            textvariable=self._search_var,
            font=FONTS["body"],
            bg=self._c("input_bg"),
            fg=self._c("text_grey"),
            relief="flat",
            bd=4,
            insertbackground=COLORS["primary_orange"],
            width=18
        )
        self._search_entry.insert(0, "Search articles…")
        self._search_entry.bind("<FocusIn>", self._search_focus_in)
        self._search_entry.bind("<FocusOut>", self._search_focus_out)
        self._search_entry.pack(side="left")
        tk.Label(search_wrap, text="🔍", bg=self._c("input_bg"),
                 fg=COLORS["primary_orange"]).pack(side="left", padx=(0, 6))

        tk.Frame(right, bg=self._c("border"), width=1, height=26).pack(side="left", padx=8)

        self._theme_btn = tk.Label(
            right, text="🌙", font=("Helvetica", 16),
            bg=self._c("white"), fg=COLORS["primary_orange"], cursor="hand2"
        )
        self._theme_btn.pack(side="left", padx=4)
        self._theme_btn.bind("<Button-1>", self._toggle_dark)

        if self.user:
            first = self.user[0] if len(self.user) > 0 else "U"
            last = self.user[1] if len(self.user) > 1 else "S"
            email = self.user[2] if len(self.user) > 2 else ""
            initials = (first[:1] + last[:1]).upper()

            acc_c = tk.Canvas(right, width=36, height=36, bg=self._c("white"), highlightthickness=0)
            acc_c.pack(side="left", padx=(6, 0))
            acc_c.create_oval(2, 2, 34, 34, fill=COLORS["primary_orange"], outline="")
            acc_c.create_text(18, 18, text=initials, fill="white", font=FONTS["small_bold"])
            acc_c.bind("<Button-1>", self._show_account_menu)
            acc_c.config(cursor="hand2")
            self._acc_canvas = acc_c
            self._account_email = email
        else:
            login_btn = PillButton(
                right, text="Log in", width=100, height=36,
                bg=COLORS["white"], fg=COLORS["primary_orange"],
                hover_bg=COLORS["primary_orange_light"], hover_fg=COLORS["primary_orange_dark"],
                border_color=COLORS["primary_orange"],
                command=lambda: AuthModal(self.parent, mode="login") if AuthModal else None
            )
            login_btn.pack(side="left", padx=4)

    def _show_category_menu(self):
        menu = tk.Menu(
            self, tearoff=0, bg=self._c("card"),
            fg=self._c("text_dark"),
            activebackground=COLORS["primary_orange"],
            activeforeground="white",
            font=FONTS["body"],
            relief="flat", bd=0
        )
        for cat in CATEGORIES:
            menu.add_command(label=cat, command=lambda c=cat: self._set_category(c))
        x = self._cat_btn.winfo_rootx()
        y = self._cat_btn.winfo_rooty() + self._cat_btn.winfo_height()
        menu.tk_popup(x, y)

    def _set_category(self, cat):
        self._current_cat = cat
        self._refresh_articles()

    def _show_account_menu(self, _=None):
        menu = tk.Menu(
            self, tearoff=0, bg=self._c("card"),
            fg=self._c("text_dark"),
            activebackground=COLORS["primary_orange"],
            activeforeground="white",
            font=FONTS["body"],
            relief="flat", bd=0
        )
        if self.user:
            menu.add_command(label=f"  {self.user[0]} {self.user[1]}", state="disabled")
            if len(self.user) > 2:
                menu.add_command(label=f"  {self.user[2]}", state="disabled")
        menu.add_separator()
        menu.add_command(label="  👤  Profile")
        menu.add_separator()
        menu.add_command(label="  🚪  Logout", foreground="#B91C1C", command=lambda: self.parent.show_landing())
        x = self._acc_canvas.winfo_rootx()
        y = self._acc_canvas.winfo_rooty() + self._acc_canvas.winfo_height()
        menu.tk_popup(x, y)

    def _toggle_dark(self, _=None):
        self._dark = not self._dark
        self._theme_btn.config(text="☀️" if self._dark else "🌙")
        for w in self.winfo_children():
            w.destroy()
        self._build_ui()

    def _search_focus_in(self, _):
        if self._search_entry.get() == "Search articles…":
            self._search_entry.delete(0, tk.END)
            self._search_entry.config(fg=self._c("text_dark"))

    def _search_focus_out(self, _):
        if not self._search_entry.get().strip():
            self._search_entry.insert(0, "Search articles…")
            self._search_entry.config(fg=self._c("text_grey"))

    def _on_search(self, *_):
        val = self._search_var.get()
        self._search_query = "" if val == "Search articles…" else val.lower()
        self._refresh_articles()

    def _build_scroll_area(self):
        outer = tk.Frame(self, bg=self._c("background"))
        outer.pack(fill="both", expand=True)

        self._sc = tk.Canvas(outer, bg=self._c("background"), highlightthickness=0)
        self._sc.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical", command=self._sc.yview)
        sb.pack(side="right", fill="y")
        self._sc.configure(yscrollcommand=sb.set)

        self._content = tk.Frame(self._sc, bg=self._c("background"))
        self._cid = self._sc.create_window((0, 0), window=self._content, anchor="nw")

        self._content.bind("<Configure>", lambda e: self._sc.configure(scrollregion=self._sc.bbox("all")))
        self._sc.bind("<Configure>", lambda e: self._sc.itemconfig(self._cid, width=e.width))
        self._sc.bind_all("<MouseWheel>", lambda e: self._sc.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._build_hero(self._content)
        self._build_category_pills(self._content)

        self._articles_frame = tk.Frame(self._content, bg=self._c("background"))
        self._articles_frame.pack(fill="x")

        self._refresh_articles()

    def _build_hero(self, parent):
        self._hero_outer = tk.Frame(parent, bg=self._c("background"))
        self._hero_outer.pack(fill="x")
        self._draw_hero()

    def _draw_hero(self):
        for w in self._hero_outer.winfo_children():
            w.destroy()

        cw = max(self._width, 900)
        ch = 220

        c = tk.Canvas(self._hero_outer, width=cw, height=ch, bg=self._c("background"), highlightthickness=0)
        c.pack(fill="x", expand=True)

        draw_rr(c, 0, 0, cw, ch, r=0, fill=COLORS["navy"], outline="")
        c.create_polygon(
            int(cw * 0.45), 0, int(cw * 0.55), 0,
            int(cw * 0.40), ch, int(cw * 0.30), ch,
            fill=COLORS["primary_orange"], outline=""
        )
        c.create_polygon(
            int(cw * 0.55), 0, cw, 0, cw, ch, int(cw * 0.40), ch,
            fill=COLORS["primary_red"], outline=""
        )
        c.create_oval(cw - 120, -40, cw + 40, 120, outline=COLORS["primary_orange"], width=2)

        bx = 56
        draw_rr(c, bx, 30, bx + 186, 56, r=13, fill=COLORS["primary_orange_light"], outline="")
        c.create_text(
            bx + 93, 43,
            text="✦  CAMPUS PUBLICATION  ✦",
            fill=COLORS["primary_orange"],
            font=FONTS["tag"]
        )

        c.create_text(56, 90, anchor="w", text="ALL ARTICLES", fill="white", font=FONTS["hero"])
        c.create_text(
            56, 130,
            anchor="w",
            text="Browse every story, opinion, and creative work\nfrom The Gears community.",
            fill="#CBD5E1",
            font=FONTS["body"]
        )

    def _build_category_pills(self, parent):
        self._pills_frame = tk.Frame(parent, bg=self._c("background_alt"))
        self._pills_frame.pack(fill="x")
        self._draw_pills()

    def _draw_pills(self):
        for w in self._pills_frame.winfo_children():
            w.destroy()

        inner = tk.Frame(self._pills_frame, bg=self._c("background_alt"))
        inner.pack(pady=14, padx=40, anchor="w")

        for cat in CATEGORIES:
            active = (cat == self._current_cat)
            btn = PillButton(
                inner,
                text=cat,
                width=max(60, len(cat) * 10 + 24),
                height=32,
                bg=COLORS["primary_orange"] if active else self._c("card"),
                fg="white" if active else self._c("text_grey"),
                hover_bg=COLORS["primary_orange_dark"] if active else self._c("background"),
                hover_fg="white" if active else self._c("text_dark"),
                border_color=COLORS["primary_orange"] if active else self._c("border"),
                font=FONTS["small_bold"],
                command=lambda c=cat: self._set_category(c)
            )
            btn.pack(side="left", padx=4)

    def _refresh_articles(self):
        self._draw_pills()
        for w in self._articles_frame.winfo_children():
            w.destroy()

        filtered = [
            a for a in self.articles
            if (self._current_cat == "All" or a[5] == self._current_cat)
            and (not self._search_query or self._search_query in a[3].lower() or self._search_query in a[1].lower())
        ]

        if not filtered:
            tk.Label(
                self._articles_frame,
                text="No articles found.",
                font=FONTS["body"],
                fg=self._c("text_grey"),
                bg=self._c("background")
            ).pack(pady=60)
            return

        if self._current_cat == "All":
            groups = {}
            for a in filtered:
                groups.setdefault(a[5], []).append(a)

            for cat, arts in groups.items():
                self._build_section(self._articles_frame, cat, arts, show_view_all=True)
        else:
            self._build_section(self._articles_frame, self._current_cat, filtered, show_view_all=False)

    def _build_section(self, parent, category, articles, show_view_all):
        section = tk.Frame(parent, bg=self._c("background"))
        section.pack(fill="x", padx=40, pady=(32, 0))

        header = tk.Frame(section, bg=self._c("background"))
        header.pack(fill="x", pady=(0, 16))

        left_h = tk.Frame(header, bg=self._c("background"))
        left_h.pack(side="left")

        tk.Frame(left_h, bg=COLORS["primary_orange"], width=4, height=24).pack(side="left", padx=(0, 10))
        tk.Label(left_h, text=category, font=FONTS["heading"],
                 fg=self._c("text_dark"), bg=self._c("background")).pack(side="left")

        if show_view_all:
            PillButton(
                header,
                text="View All →",
                width=104,
                height=34,
                bg=COLORS["primary_orange"],
                fg="white",
                hover_bg=COLORS["primary_orange_dark"],
                hover_fg="white",
                border_color=COLORS["primary_orange"],
                font=FONTS["button"],
                command=lambda c=category: self._set_category(c)
            ).pack(side="right")

        display = articles[:3] if show_view_all else articles
        row_frame = tk.Frame(section, bg=self._c("background"))
        row_frame.pack(fill="x", pady=(0, 8))

        cols = min(len(display), 3)
        for i in range(cols):
            row_frame.columnconfigure(i, weight=1, uniform="ac")

        for idx, art in enumerate(display):
            self._article_card(row_frame, art, idx % cols)

        tk.Frame(section, bg=self._c("border"), height=1).pack(fill="x", pady=(20, 0))

    def _article_card(self, parent, article, col):
        art_id, author, photo_credit, title, date, category, media = article

        cat_bg, cat_fg = CAT_COLORS.get(category, ("#F3F4F6", "#374151"))
        icon = PLACEHOLDER_ICONS.get(category, "📄")

        outer = tk.Frame(parent, bg=self._c("background"))
        outer.grid(row=0, column=col, padx=10, sticky="nsew", pady=4)

        card = tk.Frame(
            outer,
            bg=self._c("card"),
            highlightbackground=self._c("border"),
            highlightthickness=1,
            bd=0,
            cursor="hand2"
        )
        card.pack(fill="both", expand=True)

        img_box = tk.Canvas(card, height=148, bg="#EEEBE6", highlightthickness=0, cursor="hand2")
        img_box.pack(fill="x")

        def _draw_img(e, c=img_box, i=icon, cat=category):
            c.delete("all")
            w = c.winfo_width()
            bg_hex = CAT_COLORS.get(cat, ("#EEE", "#555"))[0]
            c.create_rectangle(0, 0, w, 148, fill=bg_hex, outline="")
            c.create_text(w // 2, 64, text=i, font=("Helvetica", 36))
            c.create_text(
                w // 2, 110,
                text=f"Photo by {photo_credit or 'Unknown'}",
                fill="#888",
                font=FONTS["small"]
            )

        img_box.bind("<Configure>", _draw_img)

        inner = tk.Frame(card, bg=self._c("card"), cursor="hand2")
        inner.pack(fill="both", expand=True, padx=18, pady=14)

        badge = tk.Label(
            inner,
            text=category.upper(),
            font=FONTS["tag"],
            fg=cat_fg,
            bg=cat_bg,
            padx=8,
            pady=3,
            cursor="hand2"
        )
        badge.pack(anchor="w")

        title_lbl = tk.Label(
            inner,
            text=title,
            font=FONTS["card_title"],
            fg=self._c("text_dark"),
            bg=self._c("card"),
            wraplength=220,
            justify="left",
            anchor="w",
            cursor="hand2"
        )
        title_lbl.pack(fill="x", pady=(8, 0))

        preview_lbl = tk.Label(
            inner,
            text="A short preview of the article so readers can quickly understand the topic.",
            font=FONTS["body"],
            fg=self._c("text_grey"),
            bg=self._c("card"),
            wraplength=220,
            justify="left",
            cursor="hand2"
        )
        preview_lbl.pack(fill="x", pady=(6, 0))

        bottom = tk.Frame(inner, bg=self._c("card"), cursor="hand2")
        bottom.pack(fill="x", pady=(12, 0))

        meta_lbl = tk.Label(
            bottom,
            text=f"By {author} • {date}",
            font=FONTS["small"],
            fg=self._c("text_light"),
            bg=self._c("card"),
            cursor="hand2"
        )
        meta_lbl.pack(side="left")

        read_lbl = tk.Label(
            bottom,
            text="Read more →",
            font=FONTS["small_bold"],
            fg=COLORS["primary_orange"],
            bg=self._c("card"),
            cursor="hand2"
        )
        read_lbl.pack(side="right")

        def on_enter(_):
            card.config(highlightbackground=COLORS["primary_orange"])

        def on_leave(_):
            card.config(highlightbackground=self._c("border"))

        def open_article(_=None):
            self.parent.show_article_detail(art_id, self.user)

        for w in [card, inner, bottom, img_box, badge, title_lbl, preview_lbl, meta_lbl, read_lbl]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", open_article)

    def _build_footer(self):
        footer = tk.Frame(self, bg=self._c("navy"), height=52)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        inner = tk.Frame(footer, bg=self._c("navy"))
        inner.pack(fill="x", padx=40)

        tk.Label(
            inner,
            text="© 2025 The Gears | All Rights Reserved",
            font=FONTS["small_bold"],
            fg="white",
            bg=self._c("navy")
        ).pack(side="left", pady=16)

        tk.Label(
            inner,
            text="WRITE WITHOUT FAVOR. EXPRESS WITHOUT FEAR.",
            font=FONTS["small"],
            fg="#7F8AA8",
            bg=self._c("navy")
        ).pack(side="right", pady=16)

    def _on_resize(self, event):
        if event.widget == self.parent:
            nw = event.width
            if abs(nw - self._width) > 20:
                self._width = nw
                if hasattr(self, "_hero_outer"):
                    self._draw_hero()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("The Gears – All Articles")
    root.geometry("1200x800")
    root.minsize(900, 600)
    root.configure(bg=COLORS["background"])

    ArticlesPage(root)
    root.mainloop()