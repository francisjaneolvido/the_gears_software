import tkinter as tk
import os
import json
import threading
import urllib.request
import io as _io
import subprocess
import tempfile
from PIL import Image, ImageTk

from theme import COLORS, FONTS
from components.auth_modal import AuthModal
from services.article_service import fetch_homepage_articles, fetch_categories
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
    def __init__(self, parent, text, command=None, width=120, height=40,
                 bg="#FFFFFF", fg="#000000", hover_bg=None, hover_fg=None,
                 border_color=None, font=None, radius=20, **kwargs):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bd=0,
                         bg=parent.cget("bg"), cursor="hand2", **kwargs)
        self.command      = command
        self.text         = text
        self.width_       = width
        self.height_      = height
        self.bg_          = bg
        self.fg_          = fg
        self.hover_bg     = hover_bg or bg
        self.hover_fg     = hover_fg or fg
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
        fill      = self.hover_bg if self._hovered else self.bg_
        text_fill = self.hover_fg if self._hovered else self.fg_
        border    = self.border_color
        w, h = self.width_, self.height_
        r    = h // 2
        self.create_arc(0, 0, h, h, start=90, extent=180,
                        fill=fill, outline=border, style="chord")
        self.create_arc(w - h, 0, w, h, start=270, extent=180,
                        fill=fill, outline=border, style="chord")
        self.create_rectangle(r, 1, w - r, h - 1, fill=fill, outline=fill)
        self.create_line(r, 0,     w - r, 0,     fill=border, width=1)
        self.create_line(r, h - 1, w - r, h - 1, fill=border, width=1)
        self.create_text(w // 2, h // 2, text=self.text,
                         fill=text_fill, font=self.font_)

    def _enter(self, _): self._hovered = True;  self._draw()
    def _leave(self, _): self._hovered = False; self._draw()
    def _click(self, _):
        if self.command: self.command()


# ─────────────────────────────────────────────
#  ViewAllArticle
# ─────────────────────────────────────────────
class ViewAllArticle(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["background"])
        self.parent = parent
        self.pack(fill="both", expand=True)
        self.build_ui()

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

        left = tk.Frame(nav, bg=COLORS["white"])
        left.pack(side="left", padx=40, pady=14)

        BASE_DIR  = os.path.dirname(__file__)
        logo_path = os.path.abspath(
            os.path.join(BASE_DIR, "..", "assets", "gears_logo.png"))

        try:
            img = Image.open(logo_path).resize((36, 36))
            self.logo_image = ImageTk.PhotoImage(img)
            logo_canvas = tk.Canvas(left, width=42, height=42,
                                    bg=COLORS["white"], highlightthickness=0)
            logo_canvas.pack(side="left")
            logo_canvas.create_image(21, 21, image=self.logo_image)
        except Exception:
            tk.Label(left, text="⚙", font=("Poppins", 22, "bold"),
                     fg=COLORS["primary_orange"], bg=COLORS["white"]).pack(side="left")

        brand_wrap = tk.Frame(left, bg=COLORS["white"])
        brand_wrap.pack(side="left", padx=(10, 0))
        tk.Label(brand_wrap, text="THE GEARS", font=FONTS["brand"],
                 fg=COLORS["primary_orange"], bg=COLORS["white"]).pack(anchor="w")
        tk.Label(brand_wrap, text="Official Campus Publication",
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["white"]).pack(anchor="w")

        right = tk.Frame(nav, bg=COLORS["white"])
        right.pack(side="right", padx=40, pady=14)

        home_lbl = tk.Label(right, text="Home", font=FONTS["body"],
                            fg=COLORS["text_grey"], bg=COLORS["white"], cursor="hand2")
        home_lbl.pack(side="left", padx=12)

        stories_lbl = tk.Label(right, text="Stories", font=FONTS["body"],
                               fg=COLORS["text_dark"], bg=COLORS["white"], cursor="hand2")
        stories_lbl.pack(side="left", padx=12)

        for lbl in [home_lbl, stories_lbl]:
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=COLORS["text_dark"]))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(
                fg=COLORS["text_dark"] if l.cget("text") == "Stories" else COLORS["text_grey"]))

        home_lbl.bind("<Button-1>", lambda e: self.go_home())

        tk.Frame(right, bg=COLORS["border"], width=1, height=26).pack(side="left", padx=14)

        PillButton(right, text="Log in", width=108, height=40,
                   bg=COLORS["white"], fg=COLORS["primary_orange"],
                   hover_bg=COLORS["primary_orange_light"],
                   hover_fg=COLORS["primary_orange_dark"],
                   border_color=COLORS["primary_orange"], font=FONTS["button"],
                   command=lambda: AuthModal(self.parent, mode="login")
                   ).pack(side="left", padx=5)

        PillButton(right, text="Sign up", width=114, height=40,
                   bg=COLORS["primary_orange"], fg=COLORS["white"],
                   hover_bg=COLORS["primary_orange_dark"], hover_fg=COLORS["white"],
                   border_color=COLORS["primary_orange_dark"], font=FONTS["button"],
                   command=lambda: AuthModal(self.parent, mode="signup")
                   ).pack(side="left", padx=5)

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
        self._scroll_canvas.bind_all("<MouseWheel>",
            lambda e: self._scroll_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"))

        self.build_header(self._content)
        self.build_articles_grid(self._content)
        self.build_footer(self._content)

    # ── Page header ───────────────────────────────────────────────────────────
    def build_header(self, parent):
        wrap = tk.Frame(parent, bg=COLORS["background"])
        wrap.pack(fill="x", padx=40, pady=(36, 28))

        hero = tk.Canvas(wrap, height=220, bg=COLORS["background"],
                         highlightthickness=0)
        hero.pack(fill="x", expand=True)

        def draw_header(event=None):
            hero.delete("all")
            w = hero.winfo_width()
            h = 220
            if w < 10:
                return
            draw_rounded_rect(hero, 8, 12, w - 8, h - 2, r=28,
                              fill=COLORS["shadow"], outline="")
            draw_rounded_rect(hero, 0, 0, w - 16, h - 16, r=28,
                              fill=COLORS["navy"], outline="")
            draw_rounded_rect(hero, int(w * 0.58), 0, w - 16, h - 16, r=28,
                              fill=COLORS["primary_orange"], outline="")
            hero.create_oval(w - 130, -50, w + 40, 120,
                             outline=COLORS.get("primary_red_dark", "#8B1520"), width=24)
            hero.create_text(56, 58, anchor="w", text="ALL STORIES",
                             fill=COLORS["white"], font=FONTS["hero"])
            hero.create_text(58, 118, anchor="w",
                             text="Explore campus news, features, opinions, creative works,\nand student stories from The Gears.",
                             fill="#CBD5E1", font=FONTS["body"], justify="left")
            hero.create_text(w - 190, 92, text="📰",
                             fill=COLORS["white"], font=("Poppins", 54, "bold"))
            hero.create_text(w - 190, 145, text="The Gears Archive",
                             fill=COLORS["white"], font=("Poppins", 13, "bold"))

        hero.bind("<Configure>", draw_header)

    # ── Media resolver (same logic as LandingPage) ────────────────────────────
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

        if isinstance(parsed, dict):
            media_list = parsed.get("media", [])
            if isinstance(media_list, list):
                for item in media_list:
                    if isinstance(item, dict):
                        url   = item.get("url", "")
                        thumb = item.get("thumbnail") or url
                        itype = item.get("type", "image")
                        url   = _to_full(url)   if url   and not url.startswith("http") else url
                        thumb = _to_full(thumb) if thumb and not thumb.startswith("http") else thumb
                        if url:
                            return {"url": url, "thumbnail": thumb or url, "type": itype}
            for f in parsed.get("file_paths", []):
                url = _to_full(f)
                if url:
                    return {"url": url, "thumbnail": url, "type": _ext_type(url)}

        return None

    # ── Image/video loader (blocking — run in thread) ─────────────────────────
    def _load_media_for_card(self, media_item: dict | None):
        if not media_item:
            return None

        FLASK_URL  = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
        FFMPEG     = os.getenv("FFMPEG_PATH", r"C:\ffmpeg\bin\ffmpeg.exe")
        UPLOAD_DIR = os.getenv(
            "UPLOAD_DIR",
            r"C:\Users\Jasper\Downloads\The_Gears_Web\Web_TheGears\static\uploads")

        itype = media_item.get("type", "image")
        url   = media_item.get("url", "")
        thumb = media_item.get("thumbnail", url)

        if itype == "video":
            bare      = url.replace("\\", "/").split("/")[-1].split("?")[0]
            candidate = os.path.join(UPLOAD_DIR, bare)
            if not os.path.exists(candidate):
                print(f"[ViewAll] video not found on disk: {bare}")
                return None

            thumb_path = os.path.join(tempfile.gettempdir(), f"tk_thumb_{bare}.jpg")
            if os.path.exists(thumb_path):
                try:
                    img = Image.open(thumb_path); img.load(); return img
                except Exception:
                    pass

            try:
                cmd = [FFMPEG, "-y", "-i", candidate, "-ss", "00:00:01",
                       "-vframes", "1", "-vf", "scale=640:-1", "-q:v", "3", thumb_path]
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode == 0 and os.path.exists(thumb_path):
                    img = Image.open(thumb_path); img.load()
                    print(f"[ViewAll] ✅ Thumbnail generated: {bare}")
                    return img
                else:
                    err = result.stderr.decode("utf-8", errors="replace")[-300:]
                    print(f"[ViewAll] FFmpeg failed: {err}")
                    return None
            except Exception as e:
                print(f"[ViewAll] FFmpeg error: {e}")
                return None

        else:
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
                    headers={"User-Agent": "Mozilla/5.0 TheGears-Tkinter/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                img = Image.open(_io.BytesIO(data)); img.load()
                return img
            except Exception as e:
                print(f"[ViewAll] image fetch failed: {load_url} → {e}")
                return None

    # ── Async loader ──────────────────────────────────────────────────────────
    def _load_card_image_async(self, card_info: dict, media_item: dict):
        def _worker():
            try:
                pil_img = self._load_media_for_card(media_item)
                if pil_img:
                    self.after(0, lambda: self._update_card_image(card_info, pil_img, media_item))
            except Exception as e:
                print(f"[ViewAll] async load error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _update_card_image(self, card_info: dict, pil_img, media_item: dict):
        try:
            img_wrap = card_info.get("img_wrap")
            if not img_wrap or not img_wrap.winfo_exists():
                return

            CARD_W   = 350
            IMG_H    = 180
            is_video = media_item and media_item.get("type") == "video"

            for child in img_wrap.winfo_children():
                child.destroy()

            pil_resized     = pil_img.resize((CARD_W, IMG_H), Image.LANCZOS)
            photo           = ImageTk.PhotoImage(pil_resized)
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

            open_cb   = card_info.get("open_callback")
            hover_in  = card_info.get("hover_in")
            hover_out = card_info.get("hover_out")
            for w in [img_label]:
                if open_cb:   w.bind("<Button-1>", open_cb)
                if hover_in:  w.bind("<Enter>",    hover_in)
                if hover_out: w.bind("<Leave>",    hover_out)

        except Exception as e:
            print(f"[_update_card_image] Error: {e}")

    # ── Articles grid ─────────────────────────────────────────────────────────
    def build_articles_grid(self, parent):
        section = tk.Frame(parent, bg=COLORS["background"])
        section.pack(fill="x", padx=24, pady=(0, 48))

        header = tk.Frame(section, bg=COLORS["background"])
        header.pack(fill="x", pady=(0, 22))

        left_h = tk.Frame(header, bg=COLORS["background"])
        left_h.pack(side="left", fill="y")

        tk.Frame(left_h, bg=COLORS["primary_orange"],
                 width=4, height=26).pack(side="left", padx=(0, 10))

        title_wrap = tk.Frame(left_h, bg=COLORS["background"])
        title_wrap.pack(side="left")
        tk.Label(title_wrap, text="Browse Articles", font=FONTS["heading"],
                 fg=COLORS["text_dark"], bg=COLORS["background"]).pack(anchor="w")
        tk.Label(title_wrap, text="All stories from the campus publication",
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["background"]).pack(anchor="w", pady=(2, 0))

        articles      = fetch_homepage_articles()
        category_rows = fetch_categories()
        category_colors = {
            str(cat["name"]).upper(): cat["color"]
            for cat in category_rows
            if not cat.get("archived")
        }

        if not articles:
            empty = tk.Frame(section, bg=COLORS["card"],
                             highlightbackground=COLORS["border"],
                             highlightthickness=1)
            empty.pack(fill="x", pady=30)
            tk.Label(empty, text="No articles available yet.",
                     font=FONTS["body_bold"], fg=COLORS["text_dark"],
                     bg=COLORS["card"]).pack(pady=(24, 4))
            tk.Label(empty, text="Please check back soon for new stories.",
                     font=FONTS["body"], fg=COLORS["text_grey"],
                     bg=COLORS["card"]).pack(pady=(0, 24))
            return

        grid = tk.Frame(section, bg=COLORS["background"])
        grid.pack(fill="x", anchor="center")
        for c in range(4):
            grid.columnconfigure(c, weight=1)

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

            # Derive cat_bg (light tint) from cat_color for the tag pill
            cat_bg = COLORS.get("primary_orange_light", "#FFF3E6")

            row = idx // 4
            col = idx % 4

            card_info = self._article_card(
                grid,
                article_id,
                category,
                cat_bg,
                cat_color,
                title,
                content,
                meta,
                None,
                media_item,
                row,
                col,
            )

            if media_item and card_info:
                self._load_card_image_async(card_info, media_item)

    # ── Article card (matches landing page exactly) ───────────────────────────
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
                print(f"[ViewAll] render error: {e}")
                self._article_image_placeholder(img_wrap, category, cat_fg)
        else:
            self._article_image_placeholder(img_wrap, category, cat_fg)

        # ── Card body ─────────────────────────────────────────────────────────
        body = tk.Frame(card, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=16, pady=(12, 10))

        top = tk.Frame(body, bg=COLORS["card"])
        top.pack(fill="x")

        tk.Label(top,
                 text=str(category or "Uncategorized").upper(),
                 font=FONTS["tag"], fg=cat_fg, bg=cat_bg,
                 padx=10, pady=4).pack(side="left", anchor="w")

        if is_video:
            tk.Label(top, text="🎬", font=FONTS["tag"],
                     fg=COLORS["text_grey"], bg=COLORS["card"],
                     padx=4).pack(side="left", anchor="w")

        title_text = str(title or "(Untitled)").strip()
        if len(title_text) > 52:
            title_text = title_text[:68].rstrip() + "..."

        tk.Label(body, text=title_text,
                 font=("Poppins", 12, "bold"),
                 fg=COLORS["text_dark"], bg=COLORS["card"],
                 wraplength=CARD_W - 32, justify="left", anchor="w",
                 ).pack(fill="x", pady=(12, 0))

        preview = " ".join(str(content or "").split())
        if len(preview) > 90:
            preview = preview[:135].rstrip() + "..."
        if not preview:
            preview = "No preview available."

        tk.Label(body, text=preview,
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

        tk.Label(bottom, text=meta_text,
                 font=FONTS["small"], fg=COLORS["text_light"],
                 bg=COLORS["card"], justify="left").pack(side="left", anchor="w")

        read_more = tk.Label(bottom, text="Read more →",
                             font=FONTS["small_bold"], fg=cat_fg,
                             bg=COLORS["card"], cursor="hand2")
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

        return {
            "img_wrap":      img_wrap,
            "open_callback": open_article,
            "hover_in":      on_enter,
            "hover_out":     on_leave,
        }

    # ── Placeholder (same as landing) ─────────────────────────────────────────
    def _article_image_placeholder(self, parent, category, accent):
        canvas = tk.Canvas(parent, height=180, bg="#F3EDE7",
                           highlightthickness=0, cursor="hand2")
        canvas.pack(fill="both", expand=True)

        def draw(e=None):
            canvas.delete("all")
            w = canvas.winfo_width()  or 350
            h = canvas.winfo_height() or 180
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

    # ── Footer ────────────────────────────────────────────────────────────────
    def build_footer(self, parent):
        footer = tk.Frame(parent, bg=COLORS["navy"], height=56)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        inner = tk.Frame(footer, bg=COLORS["navy"])
        inner.pack(fill="x", padx=40)

        tk.Label(inner, text="© 2025 The Gears",
                 font=FONTS["small_bold"], fg=COLORS["white"],
                 bg=COLORS["navy"]).pack(side="left", pady=18)

        tk.Label(inner, text="WRITE WITHOUT FAVOR. EXPRESS WITHOUT FEAR.",
                 font=FONTS["small"], fg="#7F8AA8",
                 bg=COLORS["navy"]).pack(side="right", pady=18)

    # ── Navigation ────────────────────────────────────────────────────────────
    def go_home(self):
        if hasattr(self.parent, "show_landing"):
            self.parent.show_landing()
        else:
            for widget in self.parent.winfo_children():
                widget.destroy()
            from user.landing_page import LandingPage
            LandingPage(self.parent)