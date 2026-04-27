import json
import tkinter as tk
from tkinter import messagebox

from theme import COLORS, FONTS

try:
    from services.article_service import (
        get_article_by_id,
        get_comments_by_article,
        add_comment,
    )
except ImportError:
    # ── Fallback stubs so the file runs standalone ────────────────────────────
    def get_article_by_id(article_id):
        return {
            "id": article_id,
            "headline": "Sample Article Headline",
            "content": (
                "This is a sample article body. " * 30
            ),
            "category": "News",
            "first_name": "Juan",
            "last_name": "Dela Cruz",
            "created_at": "May 2025",
            "media": None,
        }

    def get_comments_by_article(article_id):
        return [
            {
                "first_name": "Ana",
                "last_name": "Reyes",
                "comment": "Great article! Really enjoyed reading this.",
                "created_at": "May 1, 2025",
            },
        ]

    def add_comment(article_id, user_id, text):
        return True


# ── Helpers ───────────────────────────────────────────────────────────────────
def draw_rounded_rect(canvas, x1, y1, x2, y2, r=12, **kwargs):
    points = [
        x1 + r, y1,   x2 - r, y1,
        x2,     y1,   x2,     y1 + r,
        x2,     y2 - r, x2,   y2,
        x2 - r, y2,   x1 + r, y2,
        x1,     y2,   x1,     y2 - r,
        x1,     y1 + r, x1,   y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=36, **kwargs)


CAT_COLORS = {
    "News":     ("#E8F5E9", "#2E7D32"),
    "Updates":  ("#E3F2FD", "#1565C0"),
    "Opinion":  ("#FFF3E0", "#E65100"),
    "Feature":  ("#E8EAF6", "#283593"),
    "Literary": ("#F3E5F5", "#6A1B9A"),
    "Komiks":   ("#FCE4EC", "#880E4F"),
    "Arts":     ("#FFF8E1", "#F57F17"),
    "Photos":   ("#E0F2F1", "#00695C"),
    "Videos":   ("#EDE7F6", "#4527A0"),
}


# ═════════════════════════════════════════════════════════════════════════════
#  ArticleDetailPage
# ═════════════════════════════════════════════════════════════════════════════
class ArticleDetailPage(tk.Frame):
    """
    Full-screen article detail view.

    Layout
    ------
    ┌─────────────────────────────────────────────────┐
    │  Navbar  (logo · back · category badge)         │
    ├──────────────────────────┬──────────────────────┤
    │  Media panel  (left)     │  Article + comments  │
    │                          │  (right, fixed 420px)│
    └──────────────────────────┴──────────────────────┘

    user tuple: (first_name, last_name, email, user_id)
                 index 0       1         2      3
    """

    def __init__(self, parent, article_id, user=None):
        super().__init__(parent, bg=COLORS["background"])
        self.parent   = parent
        self.article_id = article_id
        self.user     = user

        self.article  = None
        self.comments = []
        self.media_list = []
        self.current_media_index = 0

        self._article_expanded = False
        self.PREVIEW_LIMIT = 300

        self.pack(fill="both", expand=True)
        self._load_data()
        self._build_ui()

    # ── Data ──────────────────────────────────────────────────────────────────
    def _load_data(self):
        self.article  = get_article_by_id(self.article_id)
        self.comments = get_comments_by_article(self.article_id)

        if not self.article:
            return

        raw = self.article.get("media")
        if raw:
            try:
                self.media_list = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                self.media_list = []

    # ── Top-level layout ──────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_navbar()

        if not self.article:
            tk.Label(self, text="Article not found.",
                     font=FONTS["heading"], fg=COLORS["error"],
                     bg=COLORS["background"]).pack(pady=60)
            return

        body = tk.Frame(self, bg=COLORS["background"])
        body.pack(fill="both", expand=True)

        # Left: media
        left = tk.Frame(body, bg=COLORS["background"])
        left.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=16)

        # Right: article text + comments  (fixed 420 px wide)
        right = tk.Frame(body, bg=COLORS["card"],
                         highlightbackground=COLORS["border"],
                         highlightthickness=1, width=420)
        right.pack(side="right", fill="y", padx=(0, 16), pady=16)
        right.pack_propagate(False)

        self._build_media_panel(left)
        self._build_right_panel(right)

    # ── Navbar ────────────────────────────────────────────────────────────────
    def _build_navbar(self):
        nav_wrap = tk.Frame(self, bg=COLORS["white"])
        nav_wrap.pack(fill="x")

        nav = tk.Frame(nav_wrap, bg=COLORS["white"], height=66)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        tk.Frame(nav_wrap, bg=COLORS["border"], height=1).pack(fill="x")

        # Logo
        left = tk.Frame(nav, bg=COLORS["white"])
        left.pack(side="left", padx=32, pady=10)

        logo_c = tk.Canvas(left, width=36, height=36, bg=COLORS["white"], highlightthickness=0)
        logo_c.pack(side="left")
        logo_c.create_oval(2, 2, 34, 34, fill=COLORS["primary_orange"], outline="")
        logo_c.create_text(18, 18, text="⬡", fill="white", font=("Helvetica", 11, "bold"))

        brand = tk.Frame(left, bg=COLORS["white"])
        brand.pack(side="left", padx=(8, 0))
        tk.Label(brand, text="THE GEARS", font=FONTS["brand"],
                 fg=COLORS["primary_orange"], bg=COLORS["white"]).pack(anchor="w")
        tk.Label(brand, text="Official Campus Publication", font=FONTS["small"],
                 fg=COLORS["text_grey"], bg=COLORS["white"]).pack(anchor="w")

        # Right controls
        right = tk.Frame(nav, bg=COLORS["white"])
        right.pack(side="right", padx=32, pady=10)

        # Back button
        back = tk.Canvas(right, width=90, height=34, bg=COLORS["white"],
                         highlightthickness=0, cursor="hand2")
        back.pack(side="left", padx=(0, 14))
        back.create_oval(1, 1, 33, 33, fill=COLORS["primary_orange"], outline="")
        back.create_oval(57, 1, 89, 33, fill=COLORS["primary_orange"], outline="")
        back.create_rectangle(17, 1, 73, 33, fill=COLORS["primary_orange"], outline="")
        back.create_line(17, 1, 73, 1, fill=COLORS["primary_orange"])
        back.create_line(17, 33, 73, 33, fill=COLORS["primary_orange"])
        back.create_text(45, 17, text="← Back", fill="white", font=FONTS["button"])
        back.bind("<Button-1>", lambda e: self._go_back())

        # Category badge (if article loaded)
        if self.article:
            cat = self.article.get("category", "")
            cat_bg, cat_fg = CAT_COLORS.get(cat, ("#F3F4F6", "#374151"))
            tk.Label(right, text=cat.upper(), font=FONTS["tag"],
                     fg=cat_fg, bg=cat_bg, padx=10, pady=5).pack(side="left", padx=6)

        # User initials
        if self.user:
            first = self.user[0][:1] if len(self.user) > 0 else "U"
            last  = self.user[1][:1] if len(self.user) > 1 else "S"
            acc_c = tk.Canvas(right, width=34, height=34, bg=COLORS["white"], highlightthickness=0)
            acc_c.pack(side="left", padx=(10, 0))
            acc_c.create_oval(2, 2, 32, 32, fill=COLORS["primary_orange"], outline="")
            acc_c.create_text(17, 17, text=(first + last).upper(),
                              fill="white", font=FONTS["small_bold"])

    # ── Media panel (left) ────────────────────────────────────────────────────
    def _build_media_panel(self, parent):
        # Counter label
        self._media_counter_var = tk.StringVar()
        self._update_media_counter()

        counter_bar = tk.Frame(parent, bg=COLORS["background"])
        counter_bar.pack(fill="x", pady=(0, 6))
        tk.Label(counter_bar, textvariable=self._media_counter_var,
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["background"]).pack(side="right")

        # Canvas
        self.media_canvas = tk.Canvas(parent, bg=COLORS["navy"], highlightthickness=0)
        self.media_canvas.pack(fill="both", expand=True)
        self.media_canvas.bind("<Configure>", lambda e: self._draw_media())

        # Prev / Next  (only if multiple media)
        if len(self.media_list) > 1:
            nav_bar = tk.Frame(parent, bg=COLORS["background"])
            nav_bar.pack(fill="x", pady=(8, 0))

            tk.Button(nav_bar, text="◀  Prev", font=FONTS["button"],
                      bg=COLORS["primary_red"], fg=COLORS["white"],
                      activebackground=COLORS["primary_red_dark"],
                      relief="flat", bd=0, cursor="hand2",
                      command=self._prev_media).pack(side="left")

            tk.Button(nav_bar, text="Next  ▶", font=FONTS["button"],
                      bg=COLORS["primary_red"], fg=COLORS["white"],
                      activebackground=COLORS["primary_red_dark"],
                      relief="flat", bd=0, cursor="hand2",
                      command=self._next_media).pack(side="right")

    def _update_media_counter(self):
        total = len(self.media_list)
        if total > 1:
            self._media_counter_var.set(f"{self.current_media_index + 1} / {total}")
        else:
            self._media_counter_var.set("")

    def _draw_media(self, _=None):
        self.media_canvas.delete("all")
        w = self.media_canvas.winfo_width()
        h = self.media_canvas.winfo_height()
        if w < 2 or h < 2:
            return

        draw_rounded_rect(self.media_canvas, 10, 10, w - 10, h - 10,
                          r=18, fill=COLORS["navy"], outline="")

        if self.media_list:
            item  = self.media_list[self.current_media_index]
            mtype = item.get("type", "image")
            fname = item.get("url", "media file")
            icon  = "🎬" if mtype == "video" else "🖼️"
            label = "Video" if mtype == "video" else "Image"
        else:
            icon, label, fname = "📷", "No Media", "No image or video attached"

        self.media_canvas.create_text(w // 2, h // 2 - 36,
                                      text=icon, font=("Helvetica", 48))
        self.media_canvas.create_text(w // 2, h // 2 + 14,
                                      text=label, fill=COLORS["white"],
                                      font=FONTS["heading"])
        self.media_canvas.create_text(w // 2, h // 2 + 42,
                                      text=fname, fill="#CBD5E1",
                                      font=FONTS["body"], width=w - 80)

    def _prev_media(self):
        if not self.media_list:
            return
        self.current_media_index = (self.current_media_index - 1) % len(self.media_list)
        self._update_media_counter()
        self._draw_media()

    def _next_media(self):
        if not self.media_list:
            return
        self.current_media_index = (self.current_media_index + 1) % len(self.media_list)
        self._update_media_counter()
        self._draw_media()

    # ── Right panel ───────────────────────────────────────────────────────────
    def _build_right_panel(self, parent):
        # ── Header strip ──
        header = tk.Frame(parent, bg=COLORS["background_alt"])
        header.pack(fill="x")

        av = tk.Canvas(header, width=40, height=40,
                       bg=COLORS["background_alt"], highlightthickness=0)
        av.pack(side="left", padx=12, pady=10)
        av.create_oval(2, 2, 38, 38, fill=COLORS["primary_orange"], outline="")
        av.create_text(20, 20, text="⬡", fill=COLORS["white"], font=FONTS["small_bold"])

        tk.Label(header, text="The Gears Publications",
                 font=FONTS["body_bold"], fg=COLORS["text_dark"],
                 bg=COLORS["background_alt"]).pack(side="left", padx=(0, 12))

        # ── Scrollable body ──
        outer = tk.Frame(parent, bg=COLORS["card"])
        outer.pack(fill="both", expand=True)

        body_canvas = tk.Canvas(outer, bg=COLORS["card"], highlightthickness=0)
        body_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(outer, orient="vertical", command=body_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        body_canvas.configure(yscrollcommand=scrollbar.set)

        inner = tk.Frame(body_canvas, bg=COLORS["card"])
        win_id = body_canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>",
                   lambda e: body_canvas.configure(scrollregion=body_canvas.bbox("all")))
        body_canvas.bind("<Configure>",
                         lambda e: body_canvas.itemconfig(win_id, width=e.width))

        def _wheel(e):
            body_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        body_canvas.bind("<Enter>",  lambda e: body_canvas.bind_all("<MouseWheel>", _wheel))
        body_canvas.bind("<Leave>",  lambda e: body_canvas.unbind_all("<MouseWheel>"))

        self._build_article_section(inner)
        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill="x", padx=16, pady=(0, 8))
        self._build_comments_section(inner)
        self._build_comment_form(inner)

    # ── Article text section ──────────────────────────────────────────────────
    def _build_article_section(self, parent):
        wrap = tk.Frame(parent, bg=COLORS["card"])
        wrap.pack(fill="x", padx=16, pady=(14, 10))

        author = f"{self.article.get('first_name','')} {self.article.get('last_name','')}".strip()
        cat    = self.article.get("category", "")
        date   = str(self.article.get("created_at", ""))

        # Category + headline
        cat_bg, cat_fg = CAT_COLORS.get(cat, ("#F3F4F6", "#374151"))
        tk.Label(wrap, text=cat.upper(), font=FONTS["tag"],
                 fg=cat_fg, bg=cat_bg, padx=8, pady=3).pack(anchor="w", pady=(0, 8))

        tk.Label(wrap, text=self.article.get("headline", ""),
                 font=FONTS["card_title"], fg=COLORS["text_dark"],
                 bg=COLORS["card"], wraplength=370, justify="left").pack(anchor="w")

        tk.Label(wrap, text=f"By {author}  ·  {date}",
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["card"]).pack(anchor="w", pady=(4, 12))

        # Article body with "See more / See less"
        self._full_text = self.article.get("content") or ""

        self._text_lbl = tk.Label(wrap, text="", font=FONTS["body"],
                                   fg=COLORS["text_mid"], bg=COLORS["card"],
                                   wraplength=370, justify="left")
        self._text_lbl.pack(anchor="w")

        self._toggle_lbl = tk.Label(wrap, text="", font=FONTS["small_bold"],
                                     fg=COLORS["primary_orange"], bg=COLORS["card"],
                                     cursor="hand2")
        self._toggle_lbl.pack(anchor="w", pady=(4, 0))
        self._toggle_lbl.bind("<Button-1>", lambda e: self._toggle_text())

        self._render_text()

    def _render_text(self):
        if len(self._full_text) <= self.PREVIEW_LIMIT:
            self._text_lbl.config(text=self._full_text)
            self._toggle_lbl.config(text="")
            return
        if self._article_expanded:
            self._text_lbl.config(text=self._full_text)
            self._toggle_lbl.config(text="See less ▲")
        else:
            self._text_lbl.config(text=self._full_text[:self.PREVIEW_LIMIT].rstrip() + "…")
            self._toggle_lbl.config(text="See more ▼")

    def _toggle_text(self):
        self._article_expanded = not self._article_expanded
        self._render_text()

    # ── Comments list ─────────────────────────────────────────────────────────
    def _build_comments_section(self, parent):
        tk.Label(parent, text="Comments",
                 font=FONTS["body_bold"], fg=COLORS["text_dark"],
                 bg=COLORS["card"]).pack(anchor="w", padx=16, pady=(0, 6))

        self._comments_frame = tk.Frame(parent, bg=COLORS["card"])
        self._comments_frame.pack(fill="x", padx=12, pady=(0, 4))

        self._render_comments()

    def _render_comments(self):
        for w in self._comments_frame.winfo_children():
            w.destroy()

        if not self.comments:
            tk.Label(self._comments_frame,
                     text="No comments yet. Be the first to share your thoughts!",
                     font=FONTS["body"], fg=COLORS["text_grey"],
                     bg=COLORS["card"], wraplength=360, justify="left").pack(
                         anchor="w", pady=8, padx=4)
            return

        for c in self.comments:
            name = f"{c.get('first_name','')} {c.get('last_name','')}".strip()
            text = c.get("comment", "")
            date = str(c.get("created_at", ""))

            item = tk.Frame(self._comments_frame, bg=COLORS["background_alt"],
                            highlightbackground=COLORS["border"], highlightthickness=1)
            item.pack(fill="x", pady=4, padx=2)

            tk.Label(item, text=f"{name}  ·  {date}",
                     font=FONTS["small_bold"], fg=COLORS["text_dark"],
                     bg=COLORS["background_alt"]).pack(anchor="w", padx=10, pady=(8, 2))

            tk.Label(item, text=text, font=FONTS["body"],
                     fg=COLORS["text_mid"], bg=COLORS["background_alt"],
                     wraplength=360, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

    # ── Comment form ──────────────────────────────────────────────────────────
    def _build_comment_form(self, parent):
        form = tk.Frame(parent, bg=COLORS["card"])
        form.pack(fill="x", padx=16, pady=(8, 16))

        tk.Frame(form, bg=COLORS["border"], height=1).pack(fill="x", pady=(0, 10))

        if self.user:
            name = f"{self.user[0]} {self.user[1]}" if len(self.user) > 1 else self.user[0]
            tk.Label(form, text=f"Commenting as  {name}",
                     font=FONTS["small"], fg=COLORS["text_grey"],
                     bg=COLORS["card"]).pack(anchor="w", pady=(0, 4))

        self._comment_text = tk.Text(
            form, height=4, font=FONTS["body"],
            bg=COLORS["input_bg"], fg=COLORS["text_dark"],
            relief="solid", bd=1, wrap="word",
            highlightcolor=COLORS["border_focus"],
            insertbackground=COLORS["primary_orange"]
        )
        self._comment_text.pack(fill="x", pady=(0, 8))

        btn_row = tk.Frame(form, bg=COLORS["card"])
        btn_row.pack(fill="x")

        if not self.user:
            tk.Label(btn_row, text="Log in to post a comment.",
                     font=FONTS["small"], fg=COLORS["text_grey"],
                     bg=COLORS["card"]).pack(side="left")

        post_c = tk.Canvas(btn_row, width=130, height=34,
                           bg=COLORS["card"], highlightthickness=0, cursor="hand2")
        post_c.pack(side="right")
        self._post_canvas = post_c
        self._post_hovered = False
        self._draw_post_btn()

        post_c.bind("<Enter>",    lambda e: self._post_hover(True))
        post_c.bind("<Leave>",    lambda e: self._post_hover(False))
        post_c.bind("<Button-1>", lambda e: self._submit_comment())

    def _draw_post_btn(self):
        self._post_canvas.delete("all")
        bg = COLORS["primary_orange_dark"] if self._post_hovered else COLORS["primary_orange"]
        r = 17
        w, h = 130, 34
        self._post_canvas.create_oval(1, 1, h - 1, h - 1, fill=bg, outline=bg)
        self._post_canvas.create_oval(w - h + 1, 1, w - 1, h - 1, fill=bg, outline=bg)
        self._post_canvas.create_rectangle(r, 1, w - r, h - 1, fill=bg, outline=bg)
        self._post_canvas.create_line(r, 1, w - r, 1, fill=bg)
        self._post_canvas.create_line(r, h - 1, w - r, h - 1, fill=bg)
        self._post_canvas.create_text(w // 2, h // 2, text="Post Comment",
                                       fill="white", font=FONTS["button"])

    def _post_hover(self, state):
        self._post_hovered = state
        self._draw_post_btn()

    def _submit_comment(self):
        if not self.user:
            messagebox.showerror("Login Required",
                                 "You must be logged in to post a comment.", parent=self)
            return

        text = self._comment_text.get("1.0", "end").strip()
        if not text:
            messagebox.showerror("Empty Comment",
                                 "Please write something before posting.", parent=self)
            return

        # user tuple: (first_name, last_name, email, user_id)
        user_id = self.user[3] if len(self.user) > 3 else None
        if not user_id:
            messagebox.showerror("Error", "User ID not found. Please log in again.",
                                 parent=self)
            return

        ok = add_comment(self.article_id, user_id, text)
        if not ok:
            messagebox.showerror("Error", "Failed to post comment. Please try again.",
                                 parent=self)
            return

        self._comment_text.delete("1.0", "end")
        self.comments = get_comments_by_article(self.article_id)
        self._render_comments()

    # ── Navigation ────────────────────────────────────────────────────────────
    def _go_back(self):
        if hasattr(self.parent, "show_articles"):
            self.parent.show_articles(self.user)
        else:
            # Fallback: just destroy self
            self.destroy()


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    root.title("Article Detail – Test")
    root.geometry("1200x800")
    root.minsize(900, 600)

    root.show_articles = lambda user: print("→ Back to articles, user:", user)

    ArticleDetailPage(root, article_id=1, user=("Juan", "Dela Cruz", "juan@example.com", 1))
    root.mainloop()