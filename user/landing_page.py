import tkinter as tk

from matplotlib.pyplot import grid
from theme import COLORS, FONTS, SPACING, RADIUS
from components.auth_modal import AuthModal
from services.article_service import fetch_homepage_articles, fetch_categories
from user.view_all_article import ViewAllArticle
import os
import threading
from PIL import Image, ImageTk
import urllib.request
import urllib.parse
import io as _io
import os
from PIL import Image
import json
from dotenv import load_dotenv
load_dotenv()



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


# ─────────────────────────────────────────────
#  PillButton
# ─────────────────────────────────────────────
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
        self.command      = command
        self.text         = text
        self.width_       = width
        self.height_      = height
        self.bg_          = bg
        self.fg_          = fg
        self.hover_bg     = hover_bg     or bg
        self.hover_fg     = hover_fg     or fg
        self.border_color = border_color or bg
        self.font_        = font or FONTS["button"]
        self.radius       = min(radius, height // 2)
        self._hovered     = False
        self._draw()

        self.bind("<Button-1>", self._click)
        self.bind("<Enter>",    self._enter)
        self.bind("<Leave>",    self._leave)

    def _draw(self):
        self.delete("all")
        fill      = self.hover_bg    if self._hovered else self.bg_
        text_fill = self.hover_fg    if self._hovered else self.fg_
        border    = self.border_color

        w, h = self.width_, self.height_
        r    = h // 2

        self.create_arc(0, 0, h, h,         start=90,  extent=180,
                        fill=fill, outline=border, style="chord")
        self.create_arc(w - h, 0, w, h,     start=270, extent=180,
                        fill=fill, outline=border, style="chord")
        self.create_rectangle(r, 1, w - r, h - 1,
                              fill=fill, outline=fill)
        self.create_line(r, 0,     w - r, 0,     fill=border, width=1)
        self.create_line(r, h - 1, w - r, h - 1, fill=border, width=1)

        self.create_text(w // 2, h // 2,
                         text=self.text,
                         fill=text_fill,
                         font=self.font_)

    def _enter(self, _):
        self._hovered = True
        self._draw()

    def _leave(self, _):
        self._hovered = False
        self._draw()

    def _click(self, _):
        if self.command:
            self.command()


# ─────────────────────────────────────────────
#  RoundedCard
# ─────────────────────────────────────────────
class RoundedCard(tk.Canvas):
    def __init__(self, parent, width=260, height=200,
                 radius=16, bg="#FFFFFF", border="#E5E0D8", **kwargs):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bd=0,
                         bg=parent.cget("bg"), **kwargs)
        self.width_  = width
        self.height_ = height
        self.radius  = radius
        self.card_bg = bg
        self.border  = border
        self._draw()

    def _draw(self):
        self.delete("all")
        draw_rounded_rect(self, 6, 8, self.width_ - 2, self.height_ - 2,
                          r=self.radius, fill=COLORS["shadow"], outline="")
        draw_rounded_rect(self, 2, 2, self.width_ - 6, self.height_ - 8,
                          r=self.radius, fill=self.card_bg, outline=self.border)


# ─────────────────────────────────────────────
#  Landing Page
# ─────────────────────────────────────────────
class LandingPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["background"])
        self.parent = parent
        self.pack(fill="both", expand=True)

        self._width       = parent.winfo_width() or 1100
        self._hero_canvas = None

        parent.bind("<Configure>", self._on_resize)
        self.build_ui()

    def _on_resize(self, event):
        if event.widget == self.parent:
            new_w = event.width
            if abs(new_w - self._width) > 4:
                self._width = new_w
                if self._hero_canvas:
                    self.parent.after_idle(self._redraw_hero)

    # ── Top-level layout ──────────────────────────────────────────────────────
    def build_ui(self):
        self.build_navbar()
        self.build_scrollable_content()

    # ── Navbar ────────────────────────────────────────────────────────────────
    def build_navbar(self):
        nav_wrap = tk.Frame(self, bg=COLORS["white"])
        nav_wrap.pack(fill="x")

        nav = tk.Frame(nav_wrap, bg=COLORS["white"], height=76)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        tk.Frame(nav_wrap, bg=COLORS["border"], height=1).pack(fill="x")

        # LEFT — logo + brand
        left = tk.Frame(nav, bg=COLORS["white"])
        left.pack(side="left", padx=40, pady=14)

        BASE_DIR  = os.path.dirname(__file__)
        logo_path = os.path.abspath(
            os.path.join(BASE_DIR, "..", "assets", "gears_logo.png")
        )
        img = Image.open(logo_path).resize((36, 36))
        self.logo_image = ImageTk.PhotoImage(img)

        logo_canvas = tk.Canvas(left, width=42, height=42,
                                bg=COLORS["white"], highlightthickness=0)
        logo_canvas.pack(side="left")
        logo_canvas.create_image(21, 21, image=self.logo_image)

        brand_wrap = tk.Frame(left, bg=COLORS["white"])
        brand_wrap.pack(side="left", padx=(10, 0))

        tk.Label(brand_wrap, text="THE GEARS",
                 font=FONTS["brand"], fg=COLORS["primary_orange"],
                 bg=COLORS["white"]).pack(anchor="w")
        tk.Label(brand_wrap, text="Official Campus Publication",
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["white"]).pack(anchor="w")

        # RIGHT — nav links + buttons
        right = tk.Frame(nav, bg=COLORS["white"])
        right.pack(side="right", padx=40, pady=14)

        for item in ["Home", "About", "Stories"]:
            lbl = tk.Label(right, text=item, font=FONTS["body"],
                           fg=COLORS["text_grey"], bg=COLORS["white"],
                           cursor="hand2")
            lbl.pack(side="left", padx=12)
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=COLORS["text_dark"]))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=COLORS["text_grey"]))
            if item == "About":
                lbl.bind("<Button-1>", lambda e: self.scroll_to_footer())

        tk.Frame(right, bg=COLORS["border"], width=1, height=26).pack(side="left", padx=14)

        login_btn = PillButton(
            right, text="Log in", width=108, height=40,
            bg=COLORS["white"], fg=COLORS["primary_orange"],
            hover_bg=COLORS["primary_orange_light"],
            hover_fg=COLORS["primary_orange_dark"],
            border_color=COLORS["primary_orange"],
            font=FONTS["button"],
            command=lambda: AuthModal(self.parent, mode="login")
        )
        login_btn.pack(side="left", padx=5)

        signup_btn = PillButton(
            right, text="Sign up", width=114, height=40,
            bg=COLORS["primary_orange"], fg=COLORS["white"],
            hover_bg=COLORS["primary_orange_dark"],
            hover_fg=COLORS["white"],
            border_color=COLORS["primary_orange_dark"],
            font=FONTS["button"],
            command=lambda: AuthModal(self.parent, mode="signup")
        )
        signup_btn.pack(side="left", padx=5)

    # ── Scrollable wrapper ────────────────────────────────────────────────────
    def build_scrollable_content(self):
        outer = tk.Frame(self, bg=COLORS["background"])
        outer.pack(fill="both", expand=True)

        self._scroll_canvas = tk.Canvas(outer, bg=COLORS["background"],
                                        highlightthickness=0)
        self._scroll_canvas.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical",
                          command=self._scroll_canvas.yview)
        sb.pack(side="right", fill="y")
        self._scroll_canvas.configure(yscrollcommand=sb.set)

        self._content    = tk.Frame(self._scroll_canvas, bg=COLORS["background"])
        self._content_id = self._scroll_canvas.create_window(
            (0, 0), window=self._content, anchor="nw")

        self._content.bind("<Configure>",
            lambda e: self._scroll_canvas.configure(
                scrollregion=self._scroll_canvas.bbox("all")))
        self._scroll_canvas.bind("<Configure>",
            lambda e: self._scroll_canvas.itemconfig(
                self._content_id, width=e.width))
        self._scroll_canvas.bind_all("<MouseWheel>", self._safe_scroll)

        self._build_sections()

    def _build_sections(self):
        self.build_hero(self._content)
        self.build_intro(self._content)
        self.build_articles(self._content)
        self.build_cta(self._content)
        self.build_footer(self._content)

    # ── Hero ──────────────────────────────────────────────────────────────────
    def build_hero(self, parent):
        self._hero_wrap = tk.Frame(parent, bg=COLORS["background"])
        self._hero_wrap.pack(fill="x", pady=(36, 32), padx=40)

        self._hero_canvas = tk.Canvas(
            self._hero_wrap,
            height=340,
            bg=COLORS["background"],
            highlightthickness=0
        )
        self._hero_canvas.pack(fill="x", expand=True)
        self._hero_canvas.bind("<Configure>", lambda e: self._redraw_hero())

    def _redraw_hero(self):
        c  = self._hero_canvas
        cw = c.winfo_width()
        ch = c.winfo_height()
        if cw < 10:
            return

        c.delete("all")

        # Drop shadow
        draw_rounded_rect(c, 8, 12, cw - 8, ch - 2,
                          r=28, fill=COLORS["shadow"], outline="")
        # Navy main panel
        draw_rounded_rect(c, 0, 0, cw - 16, ch - 16,
                          r=28, fill=COLORS["navy"], outline="")
        # Right image panel
        rp_x = int(cw * 0.58)
        draw_rounded_rect(c, rp_x, 0, cw - 16, ch - 16,
                          r=28, fill="#C4B8AE", outline="")
        # Orange diagonal slash
        c.create_polygon(
            int(cw * 0.52), 0,
            int(cw * 0.61), 0,
            int(cw * 0.47), ch - 16,
            int(cw * 0.39), ch - 16,
            fill=COLORS["primary_orange"], outline=""
        )
        # Decorative circles
        c.create_oval(int(cw * 0.82), -30, int(cw * 1.02), 120,
                      outline=COLORS["primary_orange"], width=2)
        c.create_oval(int(cw * 0.88), 70, int(cw * 0.98), 160,
                      outline="#2A3A5C", width=1)

        lx = 56

        # Badge pill
        bx, by = lx, 38
        bw, bh = 196, 28
        draw_rounded_rect(c, bx, by, bx + bw, by + bh,
                          r=14, fill=COLORS["primary_orange_light"], outline="")
        c.create_text(bx + bw // 2, by + bh // 2,
                      text="✦  CAMPUS PUBLICATION  ✦",
                      fill=COLORS["primary_orange"], font=FONTS["tag"])

        c.create_text(lx, 94, anchor="w",
                      text="THE GEARS",
                      fill=COLORS["white"], font=FONTS["hero"])
        c.create_text(lx, 146, anchor="w",
                      text="Campus stories. Truthful news.\nStudent creativity.",
                      fill=COLORS["white"],
                      font=("Poppins", 16, "bold"))
        c.create_text(lx, 216, anchor="w",
                      text="A modern desktop publication experience designed for\nreaders, contributors, and the entire student community.",
                      fill="#CBD5E1", font=FONTS["body"])

        self._draw_canvas_pill_button(
            c, lx, 258, 164, 44,
            "Explore Stories",
            fill=COLORS["primary_orange"],
            text_fill=COLORS["white"]
        )

        # Right panel — newspaper card
        # ── Featured Story Dynamic Card ─────────────────────────
        rpanel_cx = rp_x + (cw - 16 - rp_x) // 2
        rpanel_cy = (ch - 16) // 2

        card_w, card_h = 220, 180
        card_x = rpanel_cx - card_w // 2
        card_y = rpanel_cy - card_h // 2 - 10

        latest_title = "No articles yet"
        featured_img = None

        try:
            latest_articles = fetch_homepage_articles()

            if latest_articles:
                latest_article = latest_articles[0]

                latest_title = latest_article[1] or "Untitled"

                if len(latest_title) > 55:
                    latest_title = latest_title[:55] + "..."

                raw_media = latest_article[7]
                media_item = self._resolve_first_media(raw_media)

                if media_item:
                    pil_img = self._load_media_for_card(media_item)

                    if pil_img:
                        pil_img = pil_img.resize((card_w, card_h), Image.LANCZOS)
                        featured_img = ImageTk.PhotoImage(pil_img)

        except Exception as e:
            print("[Featured Hero Error]", e)

        # card shadow
        draw_rounded_rect(
            c,
            card_x + 5,
            card_y + 6,
            card_x + card_w + 5,
            card_y + card_h + 6,
            r=16,
            fill=COLORS["shadow"],
            outline=""
        )

        # image or fallback
        if featured_img:
            c.create_image(
                card_x,
                card_y,
                image=featured_img,
                anchor="nw"
            )

            # IMPORTANT: prevent garbage collection
            self._featured_img_ref = featured_img

        else:
            draw_rounded_rect(
                c,
                card_x,
                card_y,
                card_x + card_w,
                card_y + card_h,
                r=16,
                fill="#F5F0EA",
                outline="#D6CFC7"
            )

            c.create_text(
                rpanel_cx,
                rpanel_cy - 10,
                text="THE GEARS",
                fill=COLORS["primary_orange"],
                font=("Poppins", 18, "bold")
            )

        # dark overlay
        c.create_rectangle(
            card_x,
            card_y + card_h - 55,
            card_x + card_w,
            card_y + card_h,
            fill="#000000",
            outline=""
        )

        # featured label
        c.create_text(
            card_x + 12,
            card_y + card_h - 38,
            text="FEATURED STORY",
            anchor="w",
            fill=COLORS["primary_orange"],
            font=("Poppins", 9, "bold")
        )

        # title
        c.create_text(
            card_x + 12,
            card_y + card_h - 18,
            text=latest_title,
            anchor="w",
            fill="white",
            width=card_w - 24,
            font=("Poppins", 10, "bold")
        )

    def _safe_scroll(self, event):
        try:
            self._scroll_canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    # ── Intro ─────────────────────────────────────────────────────────────────
    def build_intro(self, parent):
        intro = tk.Frame(parent, bg=COLORS["background_alt"])
        intro.pack(fill="x")

        inner = tk.Frame(intro, bg=COLORS["background_alt"])
        inner.pack(pady=38, padx=60)

        tk.Label(inner, text="WHAT IS THE GEARS?",
                 font=FONTS["section"],
                 fg=COLORS["primary_orange"],
                 bg=COLORS["background_alt"]).pack()

        tk.Frame(inner, bg=COLORS["primary_orange"],
                 width=56, height=3).pack(pady=(8, 14))

        tk.Label(inner,
                 text=("The Gears is the official campus publication dedicated to "
                       "delivering truthful news,\ncompelling stories, and creative "
                       "works produced by students — for students."),
                 font=FONTS["body"],
                 fg=COLORS["text_grey"],
                 bg=COLORS["background_alt"],
                 justify="center").pack()

    # ── Feature cards ─────────────────────────────────────────────────────────
    def build_feature_cards(self, parent):
        section = tk.Frame(parent, bg=COLORS["background"])
        section.pack(fill="x", padx=40, pady=40)

        cards_data = [
            ("📰", "Campus News",
             "Latest updates on school events, issues, and official announcements."),
            ("✍️", "Opinion & Editorial",
             "Insightful perspectives and thoughtful commentary from the student community."),
            ("🎨", "Creative Works",
             "Literary pieces, illustrations, comics, photography, and more."),
        ]

        cards_row = tk.Frame(section, bg=COLORS["background"])
        cards_row.pack(fill="x")
        cards_row.columnconfigure((0, 1, 2), weight=1, uniform="col")

        for col, (icon, title, desc) in enumerate(cards_data):
            self._feature_card(cards_row, icon, title, desc, col)

    def _feature_card(self, parent, icon, title, desc, col):
        outer = tk.Frame(parent, bg=COLORS["background"])
        outer.grid(row=0, column=col, padx=12, sticky="nsew")

        card = tk.Frame(outer, bg=COLORS["card"],
                        highlightbackground=COLORS["border"],
                        highlightthickness=1, bd=0)
        card.pack(fill="both", expand=True, ipadx=2, ipady=2)

        tk.Frame(card, bg=COLORS["primary_orange"], height=4).pack(fill="x")

        inner = tk.Frame(card, bg=COLORS["card"])
        inner.pack(fill="both", expand=True, padx=24, pady=22)

        bubble = tk.Canvas(inner, width=48, height=48,
                           bg=COLORS["card"], highlightthickness=0)
        bubble.pack(anchor="w", pady=(0, 14))
        bubble.create_oval(2, 2, 46, 46,
                           fill=COLORS["primary_orange_light"], outline="")
        bubble.create_text(24, 24, text=icon, font=("Poppins", 18))

        tk.Label(inner, text=title, font=FONTS["card_title"],
                 fg=COLORS["text_dark"], bg=COLORS["card"],
                 anchor="w").pack(fill="x")

        tk.Label(inner, text=desc, font=FONTS["body"],
                 fg=COLORS["text_grey"], bg=COLORS["card"],
                 wraplength=220, justify="left", anchor="w"
                 ).pack(fill="x", pady=(8, 0))

        def on_enter(_): card.config(highlightbackground=COLORS["primary_orange"])
        def on_leave(_): card.config(highlightbackground=COLORS["border"])

        for w in [card, inner, bubble]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    def view_all_articles(self):
        for widget in self.parent.winfo_children():
            widget.destroy()
        ViewAllArticle(self.parent)

    # ── Media resolver ────────────────────────────────────────────────────────
    def _resolve_first_media(self, raw_media) -> dict | None:
        VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        FLASK_URL  = os.getenv("FLASK_URL", "http://127.0.0.1:5000")

        def _ext_type(u):
            ext = os.path.splitext(u.split("?")[0])[1].lower()
            return "video" if ext in VIDEO_EXTS else "image"

        def _to_full(f):
            f = str(f).strip()
            if not f:
                return None
            if f.startswith("http://") or f.startswith("https://"):
                return f
            # strip local Windows/Unix paths down to filename
            if len(f) > 2 and f[1] == ":":
                f = f.replace("\\", "/").split("/")[-1]
            elif "\\" in f or (f.startswith("/") and len(f) > 1):
                f = f.replace("\\", "/").split("/")[-1]
            return f"{FLASK_URL}/static/uploads/{f}"

        if not raw_media:
            return None

        parsed = raw_media
        if isinstance(raw_media, str):
            try:
                parsed = json.loads(raw_media)
            except Exception:
                url = _to_full(raw_media)
                return {"url": url, "thumbnail": url, "type": _ext_type(url)} if url else None

        # Mobile format: list of dicts
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    url   = item.get("url", "")
                    thumb = item.get("thumbnail") or url
                    itype = item.get("type", "image")
                    if url and not url.startswith("http"):
                        url   = f"https://vkllnewjkagdmqdclywg.supabase.co/storage/v1/object/public/article_media/{url}"
                        thumb = url
                    if url:
                        return {"url": url, "thumbnail": thumb, "type": itype}
                elif isinstance(item, str) and item.strip():
                    url = _to_full(item)
                    if url:
                        return {"url": url, "thumbnail": url, "type": _ext_type(url)}
            return None

        # Tkinter/Web dict format
        if isinstance(parsed, dict):
            # New unified format with "media" key (list of dicts)
            media_list = parsed.get("media", [])
            if isinstance(media_list, list):
                for item in media_list:
                    if isinstance(item, dict):
                        url   = item.get("url", "")
                        thumb = item.get("thumbnail") or url
                        itype = item.get("type", "image")
                        url   = _to_full(url)   if url   and not url.startswith("http")   else url
                        thumb = _to_full(thumb) if thumb and not thumb.startswith("http") else thumb
                        if url:
                            return {"url": url, "thumbnail": thumb or url, "type": itype}

            # Legacy file_paths list
            for f in parsed.get("file_paths", []):
                url = _to_full(f)
                if url:
                    return {"url": url, "thumbnail": url, "type": _ext_type(url)}

        return None

    # ── Image loading (blocking — call from thread) ───────────────────────────
    def _load_media_for_card(self, media_item: dict | None):
        if not media_item:
            return None

        import urllib.request
        import urllib.parse
        import io as _io
        import subprocess
        import tempfile

        itype     = media_item.get("type", "image")
        url       = media_item.get("url", "")
        thumb     = media_item.get("thumbnail", url)
        FLASK_URL = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
        FFMPEG    = os.getenv("FFMPEG_PATH", r"C:\ffmpeg\bin\ffmpeg.exe")
        UPLOAD_DIR = os.getenv(
            "UPLOAD_DIR",
            r"C:\Users\Jasper\Downloads\The_Gears_Web\Web_TheGears\static\uploads"
        )

        if itype == "video":
            # ── Step 1: resolve the actual video file path on disk ────────────────
            video_path = None

            # Strip to bare filename
            bare = url.replace("\\", "/").split("/")[-1].split("?")[0]

            # Check uploads folder directly
            candidate = os.path.join(UPLOAD_DIR, bare)
            print(f"[DEBUG] UPLOAD_DIR = {UPLOAD_DIR}")
            print(f"[DEBUG] bare filename = {bare}")
            print(f"[DEBUG] candidate path = {candidate}")
            print(f"[DEBUG] exists = {os.path.exists(candidate)}")
            if os.path.exists(candidate):
                video_path = candidate

            if not video_path:
                print(f"[LandingPage] video not found on disk: {bare}")
                return None

            # ── Step 2: run FFmpeg locally to generate thumbnail ──────────────────
            thumb_path = os.path.join(
                tempfile.gettempdir(),
                f"tk_thumb_{bare}.jpg"
            )

            # Return cached thumbnail if already generated this session
            if os.path.exists(thumb_path):
                try:
                    img = Image.open(thumb_path)
                    img.load()
                    return img
                except Exception:
                    pass  # regenerate below

            try:
                cmd = [
                    FFMPEG, "-y",
                    "-i", video_path,
                    "-ss", "00:00:01",
                    "-vframes", "1",
                    "-vf", "scale=640:-1",
                    "-q:v", "3",
                    thumb_path,
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode == 0 and os.path.exists(thumb_path):
                    img = Image.open(thumb_path)
                    img.load()
                    print(f"[LandingPage] ✅ Thumbnail generated: {bare}")
                    return img
                else:
                    err = result.stderr.decode("utf-8", errors="replace")[-300:]
                    print(f"[LandingPage] FFmpeg failed: {err}")
                    return None
            except Exception as e:
                print(f"[LandingPage] FFmpeg error: {e}")
                return None

        else:
            # ── Image ─────────────────────────────────────────────────────────────
            load_url = url or thumb
            if not load_url:
                return None

            if not load_url.startswith("http"):
                try:
                    return Image.open(load_url)
                except Exception:
                    return None

            try:
                req = urllib.request.Request(
                    load_url,
                    headers={"User-Agent": "Mozilla/5.0 TheGears-Tkinter/1.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                img = Image.open(_io.BytesIO(data))
                img.load()
                return img
            except Exception as e:
                print(f"[LandingPage] image fetch failed: {load_url} → {e}")
                return None

    # ── Async image loading ───────────────────────────────────────────────────
    def _load_card_image_async(self, card_info: dict, media_item: dict):
        """Spawn background thread to load image, update UI on main thread when done."""
        def _worker():
            try:
                pil_img = self._load_media_for_card(media_item)
                if pil_img:
                    self.after(0, lambda: self._update_card_image(
                        card_info, pil_img, media_item))
            except Exception as e:
                print(f"[LandingPage] async load error: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _update_card_image(self, card_info: dict, pil_img, media_item: dict):
        """Called on main thread after async image load completes."""
        try:
            img_wrap = card_info.get("img_wrap")
            if not img_wrap or not img_wrap.winfo_exists():
                return

            CARD_W   = 360
            IMG_H    = 190
            is_video = media_item and media_item.get("type") == "video"

            # Clear existing placeholder children
            for child in img_wrap.winfo_children():
                child.destroy()

            pil_resized     = pil_img.resize((CARD_W, IMG_H), Image.LANCZOS)
            photo           = ImageTk.PhotoImage(pil_resized)
            img_label       = tk.Label(img_wrap, image=photo, bd=0,
                                       bg="#EEEBE6", cursor="hand2")
            img_label.image = photo  # prevent GC
            img_label.pack(fill="both", expand=True)

            # Video play icon badge
            if is_video:
                badge_cv = tk.Canvas(img_wrap, width=56, height=56,
                                     bg=COLORS["navy"], highlightthickness=0)
                badge_cv.create_polygon(18, 12, 18, 44, 46, 28,
                                        fill="white", outline="")
                badge_cv.place(relx=0.5, rely=0.5, anchor="center")

            # Re-bind events to the new label
            open_cb   = card_info.get("open_callback")
            hover_in  = card_info.get("hover_in")
            hover_out = card_info.get("hover_out")

            for w in [img_label]:
                if open_cb:   w.bind("<Button-1>", open_cb)
                if hover_in:  w.bind("<Enter>",    hover_in)
                if hover_out: w.bind("<Leave>",    hover_out)

        except Exception as e:
            print(f"[_update_card_image] Error: {e}")

    # ── Articles section ──────────────────────────────────────────────────────
    def build_articles(self, parent):
        section = tk.Frame(parent, bg=COLORS["background"])
        section.pack(fill="x", padx=24, pady=(0, 36))

        header = tk.Frame(section, bg=COLORS["background"])
        header.pack(fill="x", pady=(0, 14))

        left_h = tk.Frame(header, bg=COLORS["background"])
        left_h.pack(side="left", fill="y")

        tk.Frame(left_h, bg=COLORS["primary_orange"],
                 width=4, height=26).pack(side="left", padx=(0, 10))

        title_wrap = tk.Frame(left_h, bg=COLORS["background"])
        title_wrap.pack(side="left")

        tk.Label(title_wrap, text="Latest Articles",
                 font=FONTS["heading"], fg=COLORS["text_dark"],
                 bg=COLORS["background"]).pack(anchor="w")
        tk.Label(title_wrap, text="Fresh stories from the campus publication",
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["background"]).pack(anchor="w", pady=(2, 0))

        PillButton(
            header,
            text="View All",
            width=110, height=38,
            bg=COLORS["primary_orange"], fg=COLORS["white"],
            hover_bg=COLORS["primary_orange_dark"], hover_fg=COLORS["white"],
            border_color=COLORS["primary_orange"],
            font=FONTS["button"],
            command=self.view_all_articles
        ).pack(side="right")

        grid = tk.Frame(section, bg=COLORS["background"])
        grid.pack(fill="x", anchor="center")
        for c in range(4):
            grid.columnconfigure(c, weight=1)

        articles      = fetch_homepage_articles()[:8]
        category_rows = fetch_categories()
        category_colors = {
            str(cat["name"]).upper(): cat["color"]
            for cat in category_rows
            if not cat.get("archived")
        }

        if not articles:
            empty = tk.Frame(grid, bg=COLORS["card"],
                             highlightbackground=COLORS["border"],
                             highlightthickness=1)
            empty.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(6, 0))
            tk.Label(empty, text="No articles published yet.",
                     font=FONTS["body_bold"], fg=COLORS["text_dark"],
                     bg=COLORS["card"]).pack(pady=(24, 4))
            tk.Label(empty, text="Please check back soon for new stories.",
                     font=FONTS["body"], fg=COLORS["text_grey"],
                     bg=COLORS["card"]).pack(pady=(0, 24))
            return

        for idx, art in enumerate(articles):
            article_id = art[0]
            title      = art[1] or "(Untitled)"
            content    = art[2] or ""
            category   = art[3] or "Uncategorized"
            created_at = str(art[4] or "")
            author     = f"{art[5]} {art[6]}".strip() or "Unknown"

            date_text = created_at
            try:
                if " " in created_at:
                    date_text = created_at.split(" ")[0]
            except Exception:
                pass

            meta       = f"By {author}" + (f" · {date_text}" if date_text else "")
            raw_media  = art[7]
            media_item = self._resolve_first_media(raw_media)
            cat_color  = category_colors.get(str(category).upper(), COLORS["primary_orange"])

            row = idx // 4
            col = idx % 4

            # Create card with placeholder first
            card_info = self._article_card(
                grid,
                article_id,
                category,
                "#FFF3E6",
                cat_color,
                title,
                content,
                meta,
                None,        # no image yet
                media_item,
                row,
                col,
            )

            # Load image in background thread
            if media_item and card_info:
                self._load_card_image_async(card_info, media_item)

    # ── Article card ──────────────────────────────────────────────────────────
    def _article_card(self, parent, article_id, category, cat_bg, cat_fg,
                      title, content, meta, loaded_image, media_item,
                      row, col) -> dict:
        CARD_W = 350
        CARD_H = 390
        IMG_H  = 180

        outer = tk.Frame(parent, bg=COLORS["background"])
        outer.grid(row=row, column=col, padx=8, pady=(0, 16), sticky="n")

        shadow = tk.Frame(outer, bg=COLORS["shadow"])
        shadow.pack(padx=(3, 0), pady=(5, 0))

        card = tk.Frame(
            shadow, bg=COLORS["card"],
            width=CARD_W, height=CARD_H,
            highlightbackground=COLORS["border"],
            highlightthickness=1, bd=0, cursor="hand2",
        )
        card.pack(padx=(0, 3), pady=(0, 5))
        card.pack_propagate(False)

        tk.Frame(card, bg=cat_fg, height=4).pack(fill="x")

        img_wrap = tk.Frame(card, bg="#EEEBE6", height=IMG_H)
        img_wrap.pack(fill="x")
        img_wrap.pack_propagate(False)

        is_video = media_item and media_item.get("type") == "video"

        # Render image if already available, otherwise show placeholder
        if loaded_image:
            try:
                pil_img         = loaded_image.resize((CARD_W, IMG_H), Image.LANCZOS)
                photo           = ImageTk.PhotoImage(pil_img)
                img_label       = tk.Label(img_wrap, image=photo, bd=0,
                                           bg="#EEEBE6", cursor="hand2")
                img_label.image = photo
                img_label.pack(fill="both", expand=True)

                if is_video:
                    badge_cv = tk.Canvas(img_wrap, width=56, height=56,
                                         bg=COLORS["navy"], highlightthickness=0)
                    badge_cv.create_polygon(18, 12, 18, 44, 46, 28,
                                            fill="white", outline="")
                    badge_cv.place(relx=0.5, rely=0.5, anchor="center")
            except Exception as e:
                print(f"[LandingPage] render error: {e}")
                self._article_image_placeholder(img_wrap, category, cat_fg)
        else:
            self._article_image_placeholder(img_wrap, category, cat_fg)

        # ── Card body ─────────────────────────────────────────────────────────
        body = tk.Frame(card, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=16, pady=(12, 10))

        top = tk.Frame(body, bg=COLORS["card"])
        top.pack(fill="x")

        tk.Label(
            top,
            text=str(category or "Uncategorized").upper(),
            font=FONTS["tag"], fg=cat_fg, bg=cat_bg,
            padx=10, pady=4,
        ).pack(side="left", anchor="w")

        if is_video:
            tk.Label(
                top, text="🎬",
                font=FONTS["tag"], fg=COLORS["text_grey"],
                bg=COLORS["card"], padx=4,
            ).pack(side="left", anchor="w")

        title_text = str(title or "(Untitled)").strip()
        if len(title_text) > 52:
            title_text = title_text[:68].rstrip() + "..."

        tk.Label(
            body, text=title_text,
            font=("Poppins", 12, "bold"),
            fg=COLORS["text_dark"], bg=COLORS["card"],
            wraplength=CARD_W - 32, justify="left", anchor="w",
        ).pack(fill="x", pady=(12, 0))

        preview = " ".join(str(content or "").split())
        if len(preview) > 90:
            preview = preview[:135].rstrip() + "..."
        if not preview:
            preview = "No preview available."

        tk.Label(
            body, text=preview,
            font=FONTS["body"], fg=COLORS["text_grey"], bg=COLORS["card"],
            wraplength=CARD_W - 32, justify="left", anchor="nw",
        ).pack(fill="x", pady=(10, 0))

        tk.Frame(body, bg=COLORS["card"]).pack(fill="both", expand=True)
        tk.Frame(body, bg=COLORS["border"], height=1).pack(fill="x", pady=(10, 10))

        bottom = tk.Frame(body, bg=COLORS["card"])
        bottom.pack(fill="x")

        meta_text = str(meta or "").strip()
        if len(meta_text) > 34:
            meta_text = meta_text[:34].rstrip() + "..."

        tk.Label(
            bottom, text=meta_text,
            font=FONTS["small"], fg=COLORS["text_light"],
            bg=COLORS["card"], justify="left",
        ).pack(side="left", anchor="w")

        read_more = tk.Label(
            bottom, text="Read more →",
            font=FONTS["small_bold"], fg=cat_fg,
            bg=COLORS["card"], cursor="hand2",
        )
        read_more.pack(side="right", anchor="e")

        def open_article(event=None):
            if hasattr(self.parent, "show_article_detail"):
                self.parent.show_article_detail(article_id, None, from_landing=True)

        def on_enter(_):
            card.config(highlightbackground=cat_fg, highlightthickness=2)
            read_more.config(fg=COLORS["primary_orange_dark"])

        def on_leave(_):
            card.config(highlightbackground=COLORS["border"], highlightthickness=1)
            read_more.config(fg=cat_fg)

        for w in [card, body, img_wrap, read_more, bottom, top]:
            w.bind("<Button-1>", open_article)
            w.bind("<Enter>",    on_enter)
            w.bind("<Leave>",    on_leave)

        for child in img_wrap.winfo_children():
            child.bind("<Button-1>", open_article)
            child.bind("<Enter>",    on_enter)
            child.bind("<Leave>",    on_leave)

        # Return dict so async loader can update the image later
        return {
            "img_wrap":       img_wrap,
            "open_callback":  open_article,
            "hover_in":       on_enter,
            "hover_out":      on_leave,
        }

    def _article_image_placeholder(self, parent, category, accent):
        canvas = tk.Canvas(parent, height=190, bg="#F3EDE7",
                           highlightthickness=0, cursor="hand2")
        canvas.pack(fill="both", expand=True)

        def draw(e=None):
            canvas.delete("all")
            w = canvas.winfo_width()  or 360
            h = canvas.winfo_height() or 190

            canvas.create_rectangle(0, 0, w, h, fill="#F3EDE7", outline="")
            canvas.create_polygon(0, h, w * 0.45, 0, w * 0.72, 0, w * 0.25, h,
                                  fill=accent, outline="")
            canvas.create_oval(w - 84, -38, w + 36, 82,
                               outline=accent, width=3)
            canvas.create_text(w // 2, h // 2 - 10,
                               text="THE GEARS",
                               fill=COLORS["primary_orange"],
                               font=("Poppins", 20, "bold"))
            canvas.create_text(w // 2, h // 2 + 24,
                               text=str(category or "ARTICLE").upper(),
                               fill=COLORS["text_grey"],
                               font=FONTS["small_bold"])

        canvas.bind("<Configure>", draw)
        canvas.after_idle(draw)

    # ── CTA banner ────────────────────────────────────────────────────────────
    def build_cta(self, parent):
        cta_outer = tk.Frame(parent, bg=COLORS["background"])
        cta_outer.pack(fill="x", padx=40, pady=(0, 48))

        cta = tk.Canvas(cta_outer, height=182,
                        bg=COLORS["background"], highlightthickness=0)
        cta.pack(fill="x", expand=True)

        def _draw_cta(e, c=cta):
            c.delete("all")
            w = c.winfo_width()
            h = 182

            draw_rounded_rect(c, 8, 10, w - 8, h - 2,
                              r=26, fill=COLORS["shadow"], outline="")
            draw_rounded_rect(c, 0, 0, w - 16, h - 16,
                              r=26, fill=COLORS["primary_orange"], outline="")
            draw_rounded_rect(c, int(w * 0.52), 0, w - 16, h - 16,
                              r=26, fill=COLORS["primary_red"], outline="")

            # Fallback for primary_red_dark key
            red_dark = COLORS.get("primary_red_dark", "#8B1520")
            c.create_oval(w - 90, -35, w + 50, 105,
                          outline=red_dark, width=34)

            c.create_text(w // 2, 58,
                          text="STAY CONNECTED WITH THE GEARS",
                          fill=COLORS["white"], font=FONTS["section"])
            c.create_text(w // 2, 98,
                          text="Read the latest stories, features, and updates that keep you informed\nand inspired as part of our campus community.",
                          fill="#FFE8C8", font=FONTS["body"], justify="center")

            bx = w // 2 - 74
            self._draw_canvas_pill_button(
                c, bx, 128, 148, 40,
                "Explore Stories",
                fill=COLORS["white"],
                text_fill=COLORS["text_dark"]
            )

        cta.bind("<Configure>", _draw_cta)

    # ── Footer ────────────────────────────────────────────────────────────────
    def build_footer(self, parent):
        footer = tk.Frame(parent, bg=COLORS["navy"], height=56)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        self.footer = footer

        inner = tk.Frame(footer, bg=COLORS["navy"])
        inner.pack(fill="x", padx=40)

        tk.Label(inner, text="© 2025 The Gears",
                 font=FONTS["small_bold"], fg=COLORS["white"],
                 bg=COLORS["navy"]).pack(side="left", pady=18)

        tk.Label(inner, text="WRITE WITHOUT FAVOR. EXPRESS WITHOUT FEAR.",
                 font=FONTS["small"], fg="#7F8AA8",
                 bg=COLORS["navy"]).pack(side="right", pady=18)

    def scroll_to_footer(self):
        self.update_idletasks()
        footer_y      = self.footer.winfo_y()
        scroll_region = self._scroll_canvas.bbox("all")
        if scroll_region:
            total_height  = scroll_region[3]
            canvas_height = self._scroll_canvas.winfo_height()
            target        = footer_y / max(total_height - canvas_height, 1)
            self.smooth_scroll_to(target)

    def smooth_scroll_to(self, target, steps=20):
        current = self._scroll_canvas.yview()[0]
        target  = max(0, min(1, target))

        def animate(step=0):
            if step >= steps:
                self._scroll_canvas.yview_moveto(target)
                return
            new_pos = current + (target - current) * (step / steps)
            self._scroll_canvas.yview_moveto(new_pos)
            self.after(10, lambda: animate(step + 1))

        animate()

    # ── Canvas pill button helper ─────────────────────────────────────────────
    def _draw_canvas_pill_button(self, canvas, x, y, w, h, text, fill, text_fill):
        r = h // 2
        canvas.create_arc(x, y, x + h, y + h,
                          start=90, extent=180,
                          fill=fill, outline=fill, style="chord")
        canvas.create_arc(x + w - h, y, x + w, y + h,
                          start=270, extent=180,
                          fill=fill, outline=fill, style="chord")
        canvas.create_rectangle(x + r, y, x + w - r, y + h,
                                 fill=fill, outline=fill)
        canvas.create_text(x + w // 2, y + h // 2,
                           text=text, fill=text_fill, font=FONTS["button"])