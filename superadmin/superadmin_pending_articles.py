"""
superadmin/superadmin_pending_articles.py
──────────────────────────────────────────
Pending Articles review page for The Gears Superadmin.

Inherits the full header + sidebar + scrollable shell from SuperadminLayout.
This module only builds the page-specific content inside self.inner.
"""

import json
import tkinter as tk

from superadmin.superadmin_layout import SuperadminLayout
from superadmin.superadmin_review_modal import open_review_modal

try:
    from theme import COLORS, FONTS
except ImportError:
    COLORS = {
        "primary_orange":       "#F5821F",
        "primary_orange_dark":  "#D97E10",
        "primary_orange_light": "#FFE1CC",
        "primary_red":          "#B02029",
        "background":           "#F8F6F3",
        "background_alt":       "#FFF6F4",
        "card":                 "#FFFFFF",
        "white":                "#FFFFFF",
        "text_dark":            "#333333",
        "text_mid":             "#555555",
        "text_grey":            "#777777",
        "text_light":           "#9E9E9E",
        "border":               "#F0C2A0",
        "navy":                 "#0C1633",
        "success":              "#15803D",
        "success_bg":           "#DCFCE7",
        "input_bg":             "#F5F3F0",
        "shadow":               "#E8DDD5",
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
    }


# ── Media helper ──────────────────────────────────────────────────────────────
def _parse_media(raw) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(f).strip() for f in raw if str(f).strip()]
    s = str(raw).strip()
    if not s:
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(f).strip() for f in parsed if str(f).strip()]
        if isinstance(parsed, dict):
            return [str(f).strip() for f in parsed.get("file_paths", []) if str(f).strip()]
    except Exception:
        pass
    return [f.strip() for f in s.split(",") if f.strip()]


# ─────────────────────────────────────────────────────────────────────────────
class PendingArticles(SuperadminLayout):
    """Pending Articles review page, built on top of SuperadminLayout."""

    ACTIVE_NAV = "pending_articles"

    # ── Init ──────────────────────────────────────────────────────────────────
    def __init__(self, root, user=None, db_callbacks=None):
        # Data must be ready before _build_page() is called by the parent.
        self._all_articles   = []
        self._shown_articles = []
        self._search_var     = None
        self._category_var   = None

        super().__init__(root, user, db_callbacks)

        # Fetch data then populate the page.
        self._reload_data()
        self._build_page()

    # ── Data ──────────────────────────────────────────────────────────────────
    def _fetch(self) -> list:
        if "fetch_pending" in self.callbacks:
            try:
                return self.callbacks["fetch_pending"]() or []
            except Exception as e:
                print(f"[PendingArticles] fetch_pending error: {e}")
        return []

    def _reload_data(self):
        self._all_articles   = self._fetch()
        self._shown_articles = list(self._all_articles)

    def _reload(self):
        """Called after a modal closes to refresh the list."""
        self._reload_data()
        self._apply_filter()
        self.count_lbl.configure(text=f"{len(self._shown_articles)} pending")

    # ── Page build ────────────────────────────────────────────────────────────
    def _build_page(self):
        """Populate self.inner with the Pending Articles UI."""
        # Clear any previous content (e.g. after dark-mode rebuild).
        for w in self.inner.winfo_children():
            w.destroy()

        self._build_page_header()
        self._build_articles_card()

    # ── Page header ───────────────────────────────────────────────────────────
    def _build_page_header(self):
        T = self.theme
        wrap = tk.Frame(self.inner, bg=T["background"])
        wrap.pack(fill="x", pady=(0, 16))

        tk.Label(
            wrap, text="PENDING ARTICLES",
            bg=T["background"], fg=T["primary_orange"],
            font=("Poppins", 22, "bold"),
        ).pack(anchor="w")

        tk.Label(
            wrap,
            text="Review admin-submitted articles. Approve to publish or send revision notes.",
            bg=T["background"], fg=T["text_grey"],
            font=FONTS["body"],
        ).pack(anchor="w", pady=(4, 0))

    # ── Articles card ─────────────────────────────────────────────────────────
    def _build_articles_card(self):
        T = self.theme

        self.articles_card = tk.Frame(
            self.inner, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
        )
        self.articles_card.pack(fill="x")

        # Card header row
        card_hdr = tk.Frame(self.articles_card, bg=T["background_alt"], pady=12)
        card_hdr.pack(fill="x")

        left_h = tk.Frame(card_hdr, bg=T["background_alt"])
        left_h.pack(side="left", padx=20)

        title_row = tk.Frame(left_h, bg=T["background_alt"])
        title_row.pack(anchor="w")

        tk.Label(
            title_row, text="Articles Awaiting Review",
            bg=T["background_alt"], fg=T["text_dark"],
            font=FONTS["body_bold"],
        ).pack(side="left")

        self.count_lbl = tk.Label(
            title_row,
            text=f"{len(self._shown_articles)} pending",
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            font=FONTS["tag"], padx=8, pady=2,
        )
        self.count_lbl.pack(side="left", padx=(8, 0))

        tk.Label(
            left_h,
            text="Click any card to open the full-screen review workspace.",
            bg=T["background_alt"], fg=T["text_grey"],
            font=FONTS["small"],
        ).pack(anchor="w", pady=(4, 0))

        # Filter controls
        filter_frame = tk.Frame(card_hdr, bg=T["background_alt"])
        filter_frame.pack(side="right", padx=20)

        self._search_var   = tk.StringVar()
        self._category_var = tk.StringVar(value="")

        se = tk.Entry(
            filter_frame, textvariable=self._search_var,
            font=FONTS["small"], bg=T["input_bg"], fg=T["text_dark"],
            relief="flat", bd=0,
            highlightbackground=T["border"], highlightthickness=1,
        )
        se.pack(side="left", ipady=6, padx=(0, 8), ipadx=6)
        se.insert(0, "Search headline / author…")
        se.configure(fg=T["text_light"])

        def _fi(e):
            if se.get() == "Search headline / author…":
                se.delete(0, "end")
                se.configure(fg=T["text_dark"])

        def _fo(e):
            if not se.get().strip():
                se.insert(0, "Search headline / author…")
                se.configure(fg=T["text_light"])

        se.bind("<FocusIn>",  _fi)
        se.bind("<FocusOut>", _fo)
        self._search_var.trace_add("write", lambda *_: self._apply_filter())

        cats = sorted({
            a[2] for a in self._all_articles if len(a) > 2 and a[2]
        })
        cat_options = ["All categories"] + cats
        cat_menu = tk.OptionMenu(
            filter_frame, self._category_var, *cat_options,
            command=lambda _: self._apply_filter(),
        )
        cat_menu.configure(
            font=FONTS["small"], bg=T["input_bg"], fg=T["text_dark"],
            relief="flat", highlightthickness=0, bd=0,
            activebackground=T["primary_orange_light"],
            activeforeground=T["primary_orange"],
        )
        cat_menu["menu"].configure(font=FONTS["small"])
        cat_menu.pack(side="left")

        tk.Frame(self.articles_card, bg=T["border"], height=1).pack(fill="x")

        self.list_frame = tk.Frame(self.articles_card, bg=T["card"])
        self.list_frame.pack(fill="x", padx=16, pady=12)
        self._render_article_cards()

    # ── Filter & render ───────────────────────────────────────────────────────
    def _apply_filter(self):
        q = self._search_var.get().lower().strip() if self._search_var else ""
        if q == "search headline / author…":
            q = ""
        cat = self._category_var.get() if self._category_var else ""
        if cat == "All categories":
            cat = ""

        self._shown_articles = [
            a for a in self._all_articles
            if (
                not q
                or q in str(a[3]  if len(a) > 3  else "").lower()
                or q in str(a[1]  if len(a) > 1  else "").lower()
                or q in str(a[10] if len(a) > 10 else "").lower()
            )
            and (not cat or str(a[2] if len(a) > 2 else "") == cat)
        ]
        self._render_article_cards()
        if hasattr(self, "count_lbl"):
            self.count_lbl.configure(text=f"{len(self._shown_articles)} pending")

    def _render_article_cards(self):
        T = self.theme
        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self._shown_articles:
            tk.Label(
                self.list_frame,
                text="🎉  No pending articles.\n"
                     "Once admins submit new articles, they'll appear here.",
                bg=T["card"], fg=T["text_grey"],
                font=FONTS["body"], pady=28, justify="center",
            ).pack()
            return

        for art in self._shown_articles:
            self._article_card(art)

    # ── Single article card ───────────────────────────────────────────────────
    def _article_card(self, art):
        T = self.theme

        title       = art[3]  if len(art) > 3  else "(No title)"
        content     = art[4]  if len(art) > 4  else ""
        category    = art[2]  if len(art) > 2  else ""
        date_str    = art[7]  if len(art) > 7  else ""
        author      = art[10] if len(art) > 10 else (art[1] if len(art) > 1 else "Unknown")
        media_items = art[11] if len(art) > 11 else []
        media_count = len(media_items)

        card = tk.Frame(
            self.list_frame, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
            cursor="hand2",
        )
        card.pack(fill="x", pady=(0, 8))

        accent = tk.Frame(card, bg=T["primary_orange"], width=4)
        accent.pack(side="left", fill="y", padx=(0, 12))

        body = tk.Frame(card, bg=T["card"])
        body.pack(side="left", fill="both", expand=True, pady=10, padx=(0, 14))

        # ── Top row: author · category · status badge ──────────────────────────
        top = tk.Frame(body, bg=T["card"])
        top.pack(fill="x")

        tk.Label(
            top, text=f"👤 {author}",
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["small_bold"],
        ).pack(side="left", padx=(0, 8))

        if category:
            tk.Label(
                top, text=category.upper(),
                bg=T["primary_orange_light"], fg=T["primary_orange"],
                font=FONTS["tag"], padx=8, pady=2,
            ).pack(side="left", padx=(0, 8))

        tk.Label(
            top, text="● PENDING",
            bg="#FFF3CD", fg="#856404",
            font=FONTS["tag"], padx=8, pady=2,
        ).pack(side="right")

        # ── Headline ───────────────────────────────────────────────────────────
        tk.Label(
            body, text=title or "(Untitled)",
            bg=T["card"], fg=T["text_dark"],
            font=FONTS["card_title"], anchor="w",
        ).pack(fill="x", pady=(4, 0))

        # ── Meta row: date · media count ──────────────────────────────────────
        meta = tk.Frame(body, bg=T["card"])
        meta.pack(fill="x", pady=(2, 0))

        if date_str:
            tk.Label(
                meta, text=f"📅 {date_str}",
                bg=T["card"], fg=T["text_grey"],
                font=FONTS["small"],
            ).pack(side="left", padx=(0, 12))

        if media_count:
            # figure out how many are videos vs images
            vid_count = sum(1 for m in media_items if m.get("type") == "video")
            img_count = media_count - vid_count

            parts = []
            if img_count:
                parts.append(f"🖼 {img_count} image{'s' if img_count > 1 else ''}")
            if vid_count:
                parts.append(f"🎬 {vid_count} video{'s' if vid_count > 1 else ''}")

            tk.Label(
                meta, text="  ·  ".join(parts),
                bg=T["card"], fg=T["text_grey"],
                font=FONTS["small"],
            ).pack(side="left")
        else:
            tk.Label(
                meta, text="No media attached",
                bg=T["card"], fg=T["text_light"],
                font=FONTS["small"],
            ).pack(side="left")

        # ── Content snippet ────────────────────────────────────────────────────
        snippet = (content or "")[:160]
        if len(content or "") > 160:
            snippet += "…"
        if snippet:
            prev = tk.Frame(body, bg=T["card"])
            prev.pack(fill="x", pady=(4, 0))
            tk.Label(
                prev, text="Preview: ",
                bg=T["card"], fg=T["text_light"],
                font=FONTS["tag"],
            ).pack(side="left")
            tk.Label(
                prev, text=snippet,
                bg=T["card"], fg=T["text_grey"],
                font=FONTS["small"], wraplength=700,
                justify="left", anchor="w",
            ).pack(side="left", fill="x")

        # ── Hover / click bindings ─────────────────────────────────────────────
        def _enter(e, c=card):
            c.configure(highlightbackground=T["primary_orange"])

        def _leave(e, c=card):
            c.configure(highlightbackground=T["border"])

        def _click(e=None, a=art):
            self._open_review_modal(a)

        for w in [card, body, top, accent, meta]:
            w.bind("<Enter>",    _enter)
            w.bind("<Leave>",    _leave)
            w.bind("<Button-1>", _click)

    # ── Review modal ──────────────────────────────────────────────────────────
    def _open_review_modal(self, art):
        open_review_modal(
            root      = self.root,
            art       = art,       # art[11] now contains resolved media_items
            theme     = self.theme,
            callbacks = self.callbacks,
            on_close  = self._reload,
        )


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.title("The Gears — Pending Articles")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    dummy = [
        (
            1, "Francis Jane Olvido", "Updates", "dasdsadsadasda",
            "sdsadsadsdsadsadsadsadsadasdsadsdasada",
            "Updates", "", "2026-05-01 13:47:49",
            "dasdsadsadasda", "sdsadsadsdsadsadsadsadsadasdsadsdasada",
            "francisjaneolvido",
        ),
        (
            2, "Maria Santos", "Opinion", "Why Student Voices Still Matter",
            "In an era dominated by social media, the role of campus journalism "
            "remains crucial. Student voices bring authenticity and perspective "
            "that no algorithm can replicate.",
            "Opinion", "", "2025-04-28",
            "Why Student Voices Still Matter",
            "In an era dominated by social media…",
            "Maria Santos",
        ),
    ]

    PendingArticles(
        root,
        user=("Francis Jane", "Olvido", "superadmin@gears.com", 1, "superadmin", True),
        db_callbacks={"fetch_pending": lambda: dummy},
    )
    root.mainloop()