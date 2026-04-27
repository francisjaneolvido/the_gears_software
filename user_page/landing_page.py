import tkinter as tk
from theme import COLORS, FONTS, SPACING, RADIUS
from components.auth_modal import AuthModal


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def rounded_rect_points(x1, y1, x2, y2, r):
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


def draw_rounded_rect(canvas, x1, y1, x2, y2, r=12, **kwargs):
    return canvas.create_polygon(
        rounded_rect_points(x1, y1, x2, y2, r),
        smooth=True,
        splinesteps=36,
        **kwargs
    )


class PillButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command=None,
        width=120,
        height=40,
        bg="#FFFFFF",
        fg="#000000",
        hover_bg=None,
        hover_fg=None,
        border_color=None,
        font=None,
        radius=20,
        **kwargs
    ):
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
        self.text = text
        self.width_ = width
        self.height_ = height
        self.bg_ = bg
        self.fg_ = fg
        self.hover_bg = hover_bg or bg
        self.hover_fg = hover_fg or fg
        self.border_color = border_color or bg
        self.font_ = font or FONTS["button"]
        self.radius = min(radius, height // 2)

        self._hovered = False
        self._draw()

        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)

    def _draw(self):
        self.delete("all")
        fill = self.hover_bg if self._hovered else self.bg_
        fg = self.hover_fg if self._hovered else self.fg_

        # pill base
        self.create_oval(
            1, 1, self.height_ - 1, self.height_ - 1,
            fill=fill, outline=self.border_color
        )
        self.create_oval(
            self.width_ - self.height_ + 1, 1, self.width_ - 1, self.height_ - 1,
            fill=fill, outline=self.border_color
        )
        self.create_rectangle(
            self.height_ // 2, 1,
            self.width_ - self.height_ // 2, self.height_ - 1,
            fill=fill, outline=self.border_color
        )

        # border cleanup lines
        self.create_line(self.height_ // 2, 1, self.width_ - self.height_ // 2, 1, fill=self.border_color)
        self.create_line(self.height_ // 2, self.height_ - 1, self.width_ - self.height_ // 2, self.height_ - 1, fill=self.border_color)

        self.create_text(
            self.width_ // 2,
            self.height_ // 2,
            text=self.text,
            fill=fg,
            font=self.font_
        )

    def _enter(self, _):
        self._hovered = True
        self._draw()

    def _leave(self, _):
        self._hovered = False
        self._draw()

    def _click(self, _):
        if self.command:
            self.command()


class RoundedCard(tk.Canvas):
    def __init__(self, parent, width=260, height=200, radius=16, bg="#FFFFFF", border="#E5E0D8", **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=parent.cget("bg"),
            **kwargs
        )
        self.width_ = width
        self.height_ = height
        self.radius = radius
        self.card_bg = bg
        self.border = border
        self.shadow_color = COLORS["shadow"]
        self._draw()

    def _draw(self):
        self.delete("all")
        # soft shadow
        draw_rounded_rect(
            self,
            6, 8, self.width_ - 2, self.height_ - 2,
            r=self.radius,
            fill=self.shadow_color,
            outline=""
        )
        # card
        draw_rounded_rect(
            self,
            2, 2, self.width_ - 6, self.height_ - 8,
            r=self.radius,
            fill=self.card_bg,
            outline=self.border
        )


# ─────────────────────────────────────────────
#  Landing Page
# ─────────────────────────────────────────────
class LandingPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["background"])
        self.parent = parent
        self.pack(fill="both", expand=True)

        self._width = parent.winfo_width() or 1100
        parent.bind("<Configure>", self._on_resize)

        self.build_ui()

    def _on_resize(self, event):
        if event.widget == self.parent:
            new_w = event.width
            if abs(new_w - self._width) > 20:
                self._width = new_w
                self._refresh_hero()

    # ── Top-level layout ──────────────────────
    def build_ui(self):
        self.build_navbar()
        self.build_scrollable_content()
        self.build_footer()

    # ── Navbar ────────────────────────────────
    def build_navbar(self):
        nav_wrap = tk.Frame(self, bg=COLORS["white"])
        nav_wrap.pack(fill="x")

        nav = tk.Frame(nav_wrap, bg=COLORS["white"], height=76)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        border = tk.Frame(nav_wrap, bg=COLORS["border"], height=1)
        border.pack(fill="x")

        left = tk.Frame(nav, bg=COLORS["white"])
        left.pack(side="left", padx=40, pady=14)

        # Logo
        logo_canvas = tk.Canvas(
            left,
            width=42,
            height=42,
            bg=COLORS["white"],
            highlightthickness=0
        )
        logo_canvas.pack(side="left")
        logo_canvas.create_oval(
            2, 2, 40, 40,
            fill=COLORS["primary_orange"],
            outline=COLORS["primary_orange"]
        )
        logo_canvas.create_text(
            21, 21,
            text="⬡",
            fill=COLORS["white"],
            font=("Poppins", 14, "bold")
        )

        brand_wrap = tk.Frame(left, bg=COLORS["white"])
        brand_wrap.pack(side="left", padx=(10, 0))

        tk.Label(
            brand_wrap,
            text="THE GEARS",
            font=FONTS["brand"],
            fg=COLORS["primary_orange"],
            bg=COLORS["white"]
        ).pack(anchor="w")

        tk.Label(
            brand_wrap,
            text="Official Campus Publication",
            font=FONTS["small"],
            fg=COLORS["text_grey"],
            bg=COLORS["white"]
        ).pack(anchor="w")

        right = tk.Frame(nav, bg=COLORS["white"])
        right.pack(side="right", padx=40, pady=14)

        for item in ["Home", "About", "Stories"]:
            lbl = tk.Label(
                right,
                text=item,
                font=FONTS["body"],
                fg=COLORS["text_grey"],
                bg=COLORS["white"],
                cursor="hand2"
            )
            lbl.pack(side="left", padx=12)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=COLORS["text_dark"]))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=COLORS["text_grey"]))

        tk.Frame(right, bg=COLORS["border"], width=1, height=26).pack(side="left", padx=14)

        login_btn = PillButton(
            right,
            text="Log in",
            width=108,
            height=40,
            bg=COLORS["white"],
            fg=COLORS["primary_orange"],
            hover_bg=COLORS["primary_orange_light"],
            hover_fg=COLORS["primary_orange_dark"],
            border_color=COLORS["primary_orange"],
            font=FONTS["button"],
            command=lambda: AuthModal(self.parent, mode="login")
        )
        login_btn.pack(side="left", padx=5)

        signup_btn = PillButton(
            right,
            text="Sign up",
            width=114,
            height=40,
            bg=COLORS["primary_red"],
            fg=COLORS["white"],
            hover_bg=COLORS["primary_red_dark"],
            hover_fg=COLORS["white"],
            border_color=COLORS["primary_red"],
            font=FONTS["button"],
            command=lambda: AuthModal(self.parent, mode="signup")
        )
        signup_btn.pack(side="left", padx=5)

    # ── Scrollable wrapper ────────────────────
    def build_scrollable_content(self):
        outer = tk.Frame(self, bg=COLORS["background"])
        outer.pack(fill="both", expand=True)

        self._scroll_canvas = tk.Canvas(
            outer,
            bg=COLORS["background"],
            highlightthickness=0
        )
        self._scroll_canvas.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical", command=self._scroll_canvas.yview)
        sb.pack(side="right", fill="y")
        self._scroll_canvas.configure(yscrollcommand=sb.set)

        self._content = tk.Frame(self._scroll_canvas, bg=COLORS["background"])
        self._content_id = self._scroll_canvas.create_window(
            (0, 0),
            window=self._content,
            anchor="nw"
        )

        self._content.bind("<Configure>", self._on_content_configure)
        self._scroll_canvas.bind("<Configure>", self._on_canvas_configure)

        self._scroll_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        )

        self._build_sections()

    def _on_content_configure(self, _):
        self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._scroll_canvas.itemconfig(self._content_id, width=e.width)

    def _build_sections(self):
        self.build_hero(self._content)
        self.build_intro(self._content)
        self.build_feature_cards(self._content)
        self.build_articles(self._content)
        self.build_cta(self._content)

    # ── Hero ──────────────────────────────────
    def build_hero(self, parent):
        self._hero_wrap = tk.Frame(parent, bg=COLORS["background"])
        self._hero_wrap.pack(fill="x", pady=(36, 32), padx=40)
        self._draw_hero()

    def _draw_hero(self):
        for w in self._hero_wrap.winfo_children():
            w.destroy()

        cw = max(self._hero_wrap.winfo_width(), 900)
        ch = 350

        hero = tk.Canvas(
            self._hero_wrap,
            width=cw,
            height=ch,
            bg=COLORS["background"],
            highlightthickness=0
        )
        hero.pack(fill="x", expand=True)

        # shadow
        draw_rounded_rect(hero, 8, 12, cw - 8, ch - 2, r=28, fill=COLORS["shadow"], outline="")

        # main panel
        draw_rounded_rect(hero, 0, 0, cw - 16, ch - 16, r=28, fill=COLORS["navy"], outline="")

        # right panel
        draw_rounded_rect(hero, int(cw * 0.58), 0, cw - 16, ch - 16, r=28, fill="#C4B8AE", outline="")

        # accent slash
        hero.create_polygon(
            int(cw * 0.52), 0,
            int(cw * 0.61), 0,
            int(cw * 0.47), ch - 16,
            int(cw * 0.39), ch - 16,
            fill=COLORS["primary_orange"],
            outline=""
        )

        hero.create_oval(
            int(cw * 0.82), -30,
            int(cw * 1.02), 120,
            outline=COLORS["primary_orange"],
            width=2
        )

        hero.create_oval(
            int(cw * 0.88), 70,
            int(cw * 0.98), 160,
            outline=COLORS["navy_light"],
            width=1
        )

        # badge
        badge_x, badge_y = 56, 46
        draw_rounded_rect(
            hero, badge_x, badge_y, badge_x + 188, badge_y + 28,
            r=14,
            fill=COLORS["primary_orange_light"],
            outline=""
        )
        hero.create_text(
            badge_x + 94, badge_y + 14,
            text="✦  CAMPUS PUBLICATION  ✦",
            fill=COLORS["primary_orange"],
            font=FONTS["tag"]
        )

        # headline
        hero.create_text(
            56, 105,
            anchor="w",
            text="THE GEARS",
            fill=COLORS["white"],
            font=FONTS["hero"]
        )

        hero.create_text(
            56, 154,
            anchor="w",
            text="Campus stories. Truthful news.\nStudent creativity.",
            fill=COLORS["white"],
            font=("Poppins", 16, "bold")
        )

        hero.create_text(
            56, 226,
            anchor="w",
            text="A modern desktop publication experience designed for readers,\ncontributors, and the entire student community.",
            fill="#CBD5E1",
            font=FONTS["body"]
        )

        self._draw_canvas_pill_button(
            hero, 56, 272, 160, 42,
            "Explore Stories",
            fill=COLORS["primary_orange"],
            text_fill=COLORS["white"]
        )

        hero.create_text(
            int(cw * 0.79), ch // 2 - 4,
            text="📰\nFeatured Story",
            fill="#6B625B",
            font=("Poppins", 14, "bold"),
            justify="center"
        )

    def _refresh_hero(self):
        if hasattr(self, "_hero_wrap"):
            self._draw_hero()

    # ── Intro strip ───────────────────────────
    def build_intro(self, parent):
        intro = tk.Frame(parent, bg=COLORS["background_alt"])
        intro.pack(fill="x")

        inner = tk.Frame(intro, bg=COLORS["background_alt"])
        inner.pack(pady=38, padx=60)

        tk.Label(
            inner,
            text="WHAT IS THE GEARS?",
            font=FONTS["section"],
            fg=COLORS["primary_orange"],
            bg=COLORS["background_alt"]
        ).pack()

        tk.Frame(inner, bg=COLORS["primary_orange"], width=56, height=3).pack(pady=(8, 14))

        tk.Label(
            inner,
            text=(
                "The Gears is the official campus publication dedicated to delivering truthful news,\n"
                "compelling stories, and creative works produced by students — for students."
            ),
            font=FONTS["body"],
            fg=COLORS["text_grey"],
            bg=COLORS["background_alt"],
            justify="center"
        ).pack()

    # ── Feature cards ─────────────────────────
    def build_feature_cards(self, parent):
        section = tk.Frame(parent, bg=COLORS["background"])
        section.pack(fill="x", padx=40, pady=40)

        cards_data = [
            ("📰", "Campus News", "Latest updates on school events, issues, and official announcements."),
            ("✍️", "Opinion & Editorial", "Insightful perspectives and thoughtful commentary from the student community."),
            ("🎨", "Creative Works", "Literary pieces, illustrations, comics, photography, and more."),
        ]

        cards_row = tk.Frame(section, bg=COLORS["background"])
        cards_row.pack(fill="x")
        cards_row.columnconfigure((0, 1, 2), weight=1, uniform="col")

        for col, (icon, title, desc) in enumerate(cards_data):
            self._feature_card(cards_row, icon, title, desc, col)

    def _feature_card(self, parent, icon, title, desc, col):
        outer = tk.Frame(parent, bg=COLORS["background"])
        outer.grid(row=0, column=col, padx=12, sticky="nsew")

        card = tk.Frame(
            outer,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0
        )
        card.pack(fill="both", expand=True, ipadx=2, ipady=2)

        tk.Frame(card, bg=COLORS["primary_orange"], height=4).pack(fill="x")

        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(fill="both", expand=True, padx=24, pady=22)

        bubble_canvas = tk.Canvas(
            inner,
            width=48,
            height=48,
            bg=COLORS["card"],
            highlightthickness=0
        )
        bubble_canvas.pack(anchor="w", pady=(0, 14))
        bubble_canvas.create_oval(2, 2, 46, 46, fill=COLORS["primary_orange_light"], outline="")
        bubble_canvas.create_text(24, 24, text=icon, font=("Poppins", 18))

        tk.Label(
            inner,
            text=title,
            font=FONTS["card_title"],
            fg=COLORS["text_dark"],
            bg=COLORS["card"],
            anchor="w"
        ).pack(fill="x")

        tk.Label(
            inner,
            text=desc,
            font=FONTS["body"],
            fg=COLORS["text_grey"],
            bg=COLORS["card"],
            wraplength=220,
            justify="left",
            anchor="w"
        ).pack(fill="x", pady=(8, 0))

        def on_enter(_):
            card.config(highlightbackground=COLORS["primary_orange"])

        def on_leave(_):
            card.config(highlightbackground=COLORS["border"])

        for widget in [card, inner, bubble_canvas]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    # ── Articles ──────────────────────────────
    def build_articles(self, parent):
        section = tk.Frame(parent, bg=COLORS["background"])
        section.pack(fill="x", padx=40, pady=(0, 48))

        header = tk.Frame(section, bg=COLORS["background"])
        header.pack(fill="x", pady=(0, 22))

        left_h = tk.Frame(header, bg=COLORS["background"])
        left_h.pack(side="left", fill="y")

        tk.Frame(left_h, bg=COLORS["primary_orange"], width=4, height=26).pack(side="left", padx=(0, 10))

        tk.Label(
            left_h,
            text="Latest Articles",
            font=FONTS["heading"],
            fg=COLORS["text_dark"],
            bg=COLORS["background"]
        ).pack(side="left")

        view_all = PillButton(
            header,
            text="View All",
            width=110,
            height=38,
            bg=COLORS["primary_orange"],
            fg=COLORS["white"],
            hover_bg=COLORS["primary_orange_dark"],
            hover_fg=COLORS["white"],
            border_color=COLORS["primary_orange"],
            font=FONTS["button"]
        )
        view_all.pack(side="right")

        row = tk.Frame(section, bg=COLORS["background"])
        row.pack(fill="x")
        row.columnconfigure((0, 1, 2), weight=1, uniform="art")

        articles = [
            ("Campus News", "#E8F5E9", "#2E7D32", "Campus paper launches new digital desktop edition", "By Staff Writer • May 2025"),
            ("Opinion", "#FFF3E0", "#E65100", "Why student voices still matter in modern campus journalism", "By The Editors • May 2025"),
            ("Creative", "#F3E5F5", "#6A1B9A", "A collection of poems and visual stories from young writers", "By Literary Club • April 2025"),
        ]

        for col, (cat, cat_bg, cat_fg, title, meta) in enumerate(articles):
            self._article_card(row, cat, cat_bg, cat_fg, title, meta, col)

    def _article_card(self, parent, category, cat_bg, cat_fg, title, meta, col):
        outer = tk.Frame(parent, bg=COLORS["background"])
        outer.grid(row=0, column=col, padx=12, sticky="nsew")

        card = tk.Frame(
            outer,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0
        )
        card.pack(fill="both", expand=True)

        img_box = tk.Canvas(card, height=150, bg="#EEEBE6", highlightthickness=0)
        img_box.pack(fill="x")

        def _draw_img(e, c=img_box):
            c.delete("all")
            w = c.winfo_width()
            draw_rounded_rect(c, 0, 0, w, 150, r=18, fill="#EEEBE6", outline="")
            c.create_text(
                w // 2, 75,
                text="📷  Article Image",
                fill="#AAAAAA",
                font=FONTS["body"]
            )

        img_box.bind("<Configure>", _draw_img)

        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        badge = tk.Label(
            inner,
            text=category.upper(),
            font=FONTS["tag"],
            fg=cat_fg,
            bg=cat_bg,
            padx=10,
            pady=4
        )
        badge.pack(anchor="w")

        tk.Label(
            inner,
            text=title,
            font=FONTS["card_title"],
            fg=COLORS["text_dark"],
            bg=COLORS["card"],
            wraplength=220,
            justify="left",
            anchor="w"
        ).pack(fill="x", pady=(10, 0))

        tk.Label(
            inner,
            text="A short preview of the article goes here so readers can quickly understand the topic before clicking.",
            font=FONTS["body"],
            fg=COLORS["text_grey"],
            bg=COLORS["card"],
            wraplength=220,
            justify="left"
        ).pack(fill="x", pady=(8, 0))

        bottom = tk.Frame(inner, bg=COLORS["card"])
        bottom.pack(fill="x", pady=(16, 0))

        tk.Label(
            bottom,
            text=meta,
            font=FONTS["small"],
            fg=COLORS["text_light"],
            bg=COLORS["card"]
        ).pack(side="left")

        read = tk.Label(
            bottom,
            text="Read more →",
            font=FONTS["small_bold"],
            fg=COLORS["primary_orange"],
            bg=COLORS["card"],
            cursor="hand2"
        )
        read.pack(side="right")

        def on_enter(_):
            card.config(highlightbackground=COLORS["primary_orange"])

        def on_leave(_):
            card.config(highlightbackground=COLORS["border"])

        for w in [card, inner, bottom]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    # ── CTA banner ────────────────────────────
    def build_cta(self, parent):
        cta_outer = tk.Frame(parent, bg=COLORS["background"])
        cta_outer.pack(fill="x", padx=40, pady=(0, 48))

        cta = tk.Canvas(
            cta_outer,
            height=182,
            bg=COLORS["background"],
            highlightthickness=0
        )
        cta.pack(fill="x", expand=True)

        def _draw_cta(e, c=cta):
            c.delete("all")
            w = c.winfo_width()
            h = 182

            draw_rounded_rect(c, 8, 10, w - 8, h - 2, r=26, fill=COLORS["shadow"], outline="")
            draw_rounded_rect(c, 0, 0, w - 16, h - 16, r=26, fill=COLORS["primary_orange"], outline="")
            draw_rounded_rect(c, int(w * 0.52), 0, w - 16, h - 16, r=26, fill=COLORS["primary_red"], outline="")

            c.create_oval(
                w - 90, -35,
                w + 50, 105,
                outline=COLORS["primary_red_dark"],
                width=34
            )

            c.create_text(
                w // 2, 58,
                text="STAY CONNECTED WITH THE GEARS",
                fill=COLORS["white"],
                font=FONTS["section"]
            )
            c.create_text(
                w // 2, 98,
                text="Read the latest stories, features, and updates that keep you informed\nand inspired as part of our campus community.",
                fill="#FFE8C8",
                font=FONTS["body"],
                justify="center"
            )

            bx = w // 2 - 74
            self._draw_canvas_pill_button(
                c, bx, 128, 148, 40,
                "Explore Stories",
                fill=COLORS["white"],
                text_fill=COLORS["text_dark"]
            )

        cta.bind("<Configure>", _draw_cta)

    # ── Footer ────────────────────────────────
    def build_footer(self):
        footer = tk.Frame(self, bg=COLORS["navy"], height=56)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        inner = tk.Frame(footer, bg=COLORS["navy"])
        inner.pack(fill="x", padx=40)

        tk.Label(
            inner,
            text="© 2025 The Gears",
            font=FONTS["small_bold"],
            fg=COLORS["white"],
            bg=COLORS["navy"]
        ).pack(side="left", pady=18)

        tk.Label(
            inner,
            text="WRITE WITHOUT FAVOR. EXPRESS WITHOUT FEAR.",
            font=FONTS["small"],
            fg="#7F8AA8",
            bg=COLORS["navy"]
        ).pack(side="right", pady=18)

    # ── Utility ───────────────────────────────
    def _draw_canvas_pill_button(self, canvas, x, y, w, h, text, fill, text_fill):
        canvas.create_oval(x, y, x + h, y + h, fill=fill, outline=fill)
        canvas.create_oval(x + w - h, y, x + w, y + h, fill=fill, outline=fill)
        canvas.create_rectangle(x + h // 2, y, x + w - h // 2, y + h, fill=fill, outline=fill)
        canvas.create_text(
            x + w // 2,
            y + h // 2,
            text=text,
            fill=text_fill,
            font=FONTS["button"]
        )