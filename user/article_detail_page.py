import json
import tkinter as tk
from tkinter import messagebox
import os
import threading
import urllib.request
import io as _io
from PIL import Image, ImageTk

from theme import COLORS, FONTS
from services.auth_services import is_user_accepted

try:
    from services.article_service import (
        get_article_by_id,
        get_comments_by_article,
        add_comment,
    )
except ImportError:
    def get_article_by_id(article_id):
        return {
            "id": article_id,
            "headline": "Sample Article Headline",
            "content": ("This is a sample article body. " * 30),
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


import ctypes

_VLC_DIRS = [
    r"C:\Program Files\VideoLAN\VLC",
    r"C:\Program Files (x86)\VideoLAN\VLC",
]

def _load_vlc_dlls():
    for _d in _VLC_DIRS:
        dll_path = os.path.join(_d, "libvlc.dll")
        if os.path.exists(dll_path):
            try:
                os.environ["PATH"] = _d + ";" + os.environ.get("PATH", "")
                os.add_dll_directory(_d)
                ctypes.CDLL(dll_path)
                print(f"[VLC] Loaded libvlc.dll from: {_d}")
                return True
            except Exception as e:
                print(f"[VLC] Failed to load from {_d}: {e}")
    return False

_vlc_dlls_loaded = _load_vlc_dlls()

VLC_AVAILABLE = False
if _vlc_dlls_loaded:
    try:
        import vlc as _vlc
        _test_instance = _vlc.Instance("--no-video-title-show")
        _test_instance.release()
        VLC_AVAILABLE = True
        print("[VLC] ✅ Loaded successfully")
    except Exception as _vlc_err:
        print(f"[VLC] ❌ Import failed: {_vlc_err}")
else:
    print("[VLC] ❌ libvlc.dll not found in standard VLC directories")

try:
    import cv2 as _cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


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
    "NEWS":     ("#E8F5E9", "#2E7D32"),
    "UPDATES":  ("#E3F2FD", "#1565C0"),
    "OPINION":  ("#FFF3E0", "#E65100"),
    "FEATURE":  ("#E8EAF6", "#283593"),
    "LITERARY": ("#F3E5F5", "#6A1B9A"),
    "KOMIKS":   ("#FCE4EC", "#880E4F"),
    "PHOTOS":   ("#E0F2F1", "#00695C"),
    "VIDEOS":   ("#EDE7F6", "#4527A0"),
}

# ── Logo path ─────────────────────────────────────────────────────────────────
_LOGO_PATH = r"C:\Users\Jasper\Downloads\The_Gears_Software\assets\gears_logo.png"


def _load_logo(size: int = 36):
    """Return an ImageTk.PhotoImage of the logo, or None on failure."""
    try:
        img = Image.open(_LOGO_PATH).resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"[Logo] Could not load gears_logo.png: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════════
#  VLC Video Player Widget
# ═════════════════════════════════════════════════════════════════════════════
class VLCPlayerFrame(tk.Frame):
    def __init__(self, parent, video_path: str, **kwargs):
        super().__init__(parent, bg="black", **kwargs)
        self._video_path = video_path
        self._instance   = None
        self._player     = None
        self._playing    = False
        self._controls   = None
        self._build()

    def _build(self):
        if not VLC_AVAILABLE:
            tk.Label(
                self, text="🎬  VLC not installed\npip install python-vlc",
                font=("Courier", 12), fg="white", bg="black",
                justify="center",
            ).pack(expand=True)
            return

        self._canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        ctrl = tk.Frame(self, bg="#1a1a1a", height=44)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)
        self._controls = ctrl

        self._play_btn = tk.Button(
            ctrl, text="▶  Play",
            font=("Poppins", 10, "bold"),
            bg=COLORS.get("primary_orange", "#f5821f"),
            fg="white", relief="flat", bd=0,
            activebackground="#c9680c", activeforeground="white",
            cursor="hand2", padx=14, pady=6,
            command=self._toggle_play,
        )
        self._play_btn.pack(side="left", padx=8, pady=6)

        self._stop_btn = tk.Button(
            ctrl, text="■  Stop",
            font=("Poppins", 10),
            bg="#333", fg="white", relief="flat", bd=0,
            activebackground="#555", activeforeground="white",
            cursor="hand2", padx=12, pady=6,
            command=self._stop,
        )
        self._stop_btn.pack(side="left", padx=(0, 8), pady=6)

        tk.Label(ctrl, text="🔊", bg="#1a1a1a", fg="white",
                 font=("Poppins", 11)).pack(side="right", padx=(0, 4))
        self._vol_var = tk.IntVar(value=80)
        vol_slider = tk.Scale(
            ctrl, from_=0, to=100, orient="horizontal",
            variable=self._vol_var, length=90,
            bg="#1a1a1a", fg="white", troughcolor="#555",
            highlightthickness=0, showvalue=False,
            command=lambda v: self._set_volume(int(v)),
        )
        vol_slider.pack(side="right", padx=(0, 12), pady=4)
        self.after(200, self._init_vlc)

    def _init_vlc(self):
        if not VLC_AVAILABLE:
            return
        try:
            self._instance = _vlc.Instance("--no-video-title-show", "--audio-desync=0")
            self._player   = self._instance.media_player_new()
            wid = self._canvas.winfo_id()
            if os.name == "nt":
                self._player.set_hwnd(wid)
            else:
                self._player.set_xwindow(wid)
            media = self._instance.media_new(self._video_path)
            self._player.set_media(media)
            self._player.audio_set_mute(False)
            self._player.audio_set_volume(self._vol_var.get())
        except Exception as e:
            print(f"[VLCPlayerFrame] init error: {e}")

    def _toggle_play(self):
        if not self._player:
            return
        if self._playing:
            self._player.pause()
            self._play_btn.config(text="▶  Play")
            self._playing = False
        else:
            self._player.audio_set_mute(False)
            self._player.audio_set_volume(self._vol_var.get())
            self._player.play()
            self._play_btn.config(text="⏸  Pause")
            self._playing = True

    def _stop(self):
        if not self._player:
            return
        self._player.stop()
        self._play_btn.config(text="▶  Play")
        self._playing = False

    def _set_volume(self, val: int):
        if self._player:
            self._player.audio_set_volume(val)

    def destroy(self):
        try:
            if self._player:
                self._player.stop()
                self._player.release()
            if self._instance:
                self._instance.release()
        except Exception:
            pass
        super().destroy()


# ═════════════════════════════════════════════════════════════════════════════
#  CV2 Fallback Video Player
# ═════════════════════════════════════════════════════════════════════════════
class CV2PlayerFrame(tk.Frame):
    def __init__(self, parent, video_path: str, **kwargs):
        super().__init__(parent, bg="black", **kwargs)
        self._path     = video_path
        self._cap      = None
        self._playing  = False
        self._photo    = None
        self._fps      = 25
        self._after_id = None

        self._canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        ctrl = tk.Frame(self, bg="#1a1a1a", height=44)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

        self._play_btn = tk.Button(
            ctrl, text="▶  Play",
            font=("Poppins", 10, "bold"),
            bg=COLORS.get("primary_orange", "#f5821f"),
            fg="white", relief="flat", bd=0,
            cursor="hand2", padx=14, pady=6,
            command=self._toggle_play,
        )
        self._play_btn.pack(side="left", padx=8, pady=6)
        tk.Label(ctrl, text="(No audio — install python-vlc for full playback)",
                 font=("Poppins", 9), fg="#aaa", bg="#1a1a1a").pack(side="left", padx=8)

    def _open(self):
        if not CV2_AVAILABLE:
            return False
        try:
            self._cap = _cv2.VideoCapture(self._path)
            if not self._cap.isOpened():
                return False
            self._fps = self._cap.get(_cv2.CAP_PROP_FPS) or 25
            return True
        except Exception as e:
            print(f"[CV2Player] open error: {e}")
            return False

    def _toggle_play(self):
        if self._playing:
            self._playing = False
            self._play_btn.config(text="▶  Play")
            if self._after_id:
                self.after_cancel(self._after_id)
        else:
            if not self._cap and not self._open():
                tk.Label(self._canvas, text="Cannot open video",
                         fg="white", bg="black").place(relx=.5, rely=.5, anchor="center")
                return
            self._playing = True
            self._play_btn.config(text="⏸  Pause")
            self._next_frame()

    def _next_frame(self):
        if not self._playing or not self._cap:
            return
        ok, frame = self._cap.read()
        if not ok:
            self._cap.set(_cv2.CAP_PROP_POS_FRAMES, 0)
            self._playing = False
            self._play_btn.config(text="▶  Play")
            return
        try:
            frame_rgb = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            w = self._canvas.winfo_width()  or 640
            h = self._canvas.winfo_height() or 360
            pil   = Image.fromarray(frame_rgb)
            pil.thumbnail((w, h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(pil)
            self._canvas.delete("all")
            self._canvas.create_image(w // 2, h // 2, image=photo, anchor="center")
            self._photo = photo
        except Exception as e:
            print(f"[CV2Player] frame error: {e}")
        delay = max(1, int(1000 / self._fps))
        self._after_id = self.after(delay, self._next_frame)

    def destroy(self):
        self._playing = False
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
        super().destroy()


# ═════════════════════════════════════════════════════════════════════════════
#  ArticleDetailPage
# ═════════════════════════════════════════════════════════════════════════════
class ArticleDetailPage(tk.Frame):
    def __init__(self, parent, article_id, user=None, from_landing=False):
        super().__init__(parent, bg=COLORS["background"])
        self.parent       = parent
        self.article_id   = article_id
        self.user         = user
        self.from_landing = from_landing

        self.article             = None
        self.comments            = []
        self.media_list          = []
        self.current_media_index = 0
        self._thumb_cache        = {}
        self._active_player      = None

        self._article_expanded = False
        self.PREVIEW_LIMIT     = 300

        # Pre-load logo once for this page instance
        self._logo_photo = _load_logo(36)

        self.pack(fill="both", expand=True)
        self._load_data()
        self._build_ui()

    # ── Data ──────────────────────────────────────────────────────────────────
    def _load_data(self):
        raw_article = get_article_by_id(self.article_id)

        if raw_article:
            if isinstance(raw_article, dict):
                self.article = {
                    "id":         raw_article.get("id"),
                    "headline":   raw_article.get("headline"),
                    "content":    raw_article.get("content"),
                    "category":   raw_article.get("category"),
                    "created_at": raw_article.get("created_at"),
                    "first_name": raw_article.get("first_name"),
                    "last_name":  raw_article.get("last_name"),
                    "media":      raw_article.get("media"),
                }
            else:
                self.article = {
                    "id":         raw_article[0],
                    "headline":   raw_article[1],
                    "content":    raw_article[2],
                    "category":   raw_article[3],
                    "created_at": raw_article[4],
                    "first_name": raw_article[5],
                    "last_name":  raw_article[6],
                    "media":      raw_article[7],
                }
        else:
            self.article = None

        raw_comments = get_comments_by_article(self.article_id)
        self.comments = []
        for c in raw_comments:
            if isinstance(c, dict):
                self.comments.append({
                    "id":         c.get("id"),
                    "comment":    c.get("comment"),
                    "created_at": c.get("created_at"),
                    "first_name": c.get("first_name"),
                    "last_name":  c.get("last_name"),
                })
            else:
                self.comments.append({
                    "id":         c[0],
                    "comment":    c[1],
                    "created_at": c[2],
                    "first_name": c[3],
                    "last_name":  c[4],
                })

        self.media_list = []
        if not self.article:
            return

        raw = self.article.get("media")
        if raw:
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw

                image_exts = ("jpg", "jpeg", "png", "gif", "webp", "bmp")
                video_exts = ("mp4", "mov", "avi", "mkv", "webm")

                def add_file(path):
                    if not path:
                        return
                    path = str(path).strip()
                    if not path:
                        return
                    clean = path.split("?")[0]
                    ext   = clean.rsplit(".", 1)[-1].lower() if "." in clean else ""
                    if ext in image_exts:
                        self.media_list.append({"type": "image", "path": path})
                    elif ext in video_exts:
                        self.media_list.append({"type": "video", "path": path})
                    else:
                        pl = path.lower()
                        if any(v in pl for v in (".mp4", ".mov", ".webm", ".avi", ".mkv")):
                            self.media_list.append({"type": "video", "path": path})
                        elif any(i in pl for i in (".jpg", ".jpeg", ".png", ".gif", ".webp")):
                            self.media_list.append({"type": "image", "path": path})

                if isinstance(data, dict):
                    add_file(data.get("path"))
                    media_items = data.get("media", [])
                    if isinstance(media_items, list):
                        for item in media_items:
                            if isinstance(item, dict):
                                url   = item.get("url", "")
                                itype = item.get("type", "image")
                                if url:
                                    self.media_list.append({"type": itype, "path": url})
                            elif isinstance(item, str):
                                add_file(item)
                    for fp in data.get("file_paths", []):
                        add_file(fp)
                    for fp in data.get("paths", []):
                        add_file(fp)

                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            url   = item.get("url") or item.get("path") or ""
                            itype = item.get("type", "image")
                            if url:
                                self.media_list.append({"type": itype, "path": url})
                        else:
                            add_file(item)

                elif isinstance(data, str):
                    for fp in data.split(","):
                        add_file(fp)

            except Exception as e:
                print("[ArticleDetailPage] media parse error:", e)
                try:
                    for fp in str(raw).split(","):
                        fp = fp.strip()
                        if fp:
                            ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else ""
                            if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
                                self.media_list.append({"type": "image", "path": fp})
                            elif ext in ("mp4", "mov", "avi", "mkv", "webm"):
                                self.media_list.append({"type": "video", "path": fp})
                except Exception:
                    self.media_list = []

        seen, clean_media = set(), []
        for item in self.media_list:
            p = item.get("path")
            if p and p not in seen:
                seen.add(p)
                clean_media.append(item)
        self.media_list = clean_media

        print("[ARTICLE RAW MEDIA]", raw)
        print("[ARTICLE MEDIA LIST]", self.media_list)

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

        left = tk.Frame(body, bg=COLORS["background"])
        left.pack(side="left", fill="both", expand=True, padx=(16, 8), pady=16)

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

        # ── LEFT: logo image + brand text ─────────────────────────────────────
        left = tk.Frame(nav, bg=COLORS["white"])
        left.pack(side="left", padx=32, pady=10)

        if self._logo_photo:
            logo_c = tk.Canvas(left, width=40, height=40,
                               bg=COLORS["white"], highlightthickness=0)
            logo_c.pack(side="left")
            logo_c.create_image(20, 20, image=self._logo_photo, anchor="center")
        else:
            # Fallback: orange circle with TG initials
            logo_c = tk.Canvas(left, width=40, height=40,
                               bg=COLORS["white"], highlightthickness=0)
            logo_c.pack(side="left")
            logo_c.create_oval(2, 2, 38, 38, fill=COLORS["primary_orange"], outline="")
            logo_c.create_text(20, 20, text="TG",
                               fill="white", font=("Poppins", 12, "bold"))

        brand = tk.Frame(left, bg=COLORS["white"])
        brand.pack(side="left", padx=(10, 0))

        # "THE GEARS" in Hedvig font
        tk.Label(brand, text="THE GEARS",
                 font=("Hedvig Letters Serif", 15, "bold"),
                 fg=COLORS["primary_orange"],
                 bg=COLORS["white"]).pack(anchor="w")
        tk.Label(brand, text="Official Campus Publication",
                 font=FONTS["small"],
                 fg=COLORS["text_grey"],
                 bg=COLORS["white"]).pack(anchor="w")

        # ── RIGHT: back button + category badge + user avatar ─────────────────
        right = tk.Frame(nav, bg=COLORS["white"])
        right.pack(side="right", padx=32, pady=10)

        back = tk.Canvas(right, width=90, height=34,
                         bg=COLORS["white"], highlightthickness=0, cursor="hand2")
        back.pack(side="left", padx=(0, 14))
        back.create_oval(1, 1, 33, 33, fill=COLORS["primary_orange"], outline="")
        back.create_oval(57, 1, 89, 33, fill=COLORS["primary_orange"], outline="")
        back.create_rectangle(17, 1, 73, 33, fill=COLORS["primary_orange"], outline="")
        back.create_line(17, 1,  73, 1,  fill=COLORS["primary_orange"])
        back.create_line(17, 33, 73, 33, fill=COLORS["primary_orange"])
        back.create_text(45, 17, text="← Back", fill="white", font=FONTS["button"])
        back.bind("<Button-1>", lambda e: self._go_back())

        if self.article:
            cat     = self.article.get("category", "")
            cat_key = str(cat).strip().upper()
            cat_bg, cat_fg = CAT_COLORS.get(cat_key, ("#F3F4F6", "#374151"))
            tk.Label(right, text=cat.upper(), font=FONTS["tag"],
                     fg=cat_fg, bg=cat_bg, padx=10, pady=5).pack(side="left", padx=6)

        if self.user:
            first = self.user[0][:1] if len(self.user) > 0 else "U"
            last  = self.user[1][:1] if len(self.user) > 1 else "S"
            acc_c = tk.Canvas(right, width=34, height=34,
                              bg=COLORS["white"], highlightthickness=0)
            acc_c.pack(side="left", padx=(10, 0))
            acc_c.create_oval(2, 2, 32, 32, fill=COLORS["primary_orange"], outline="")
            acc_c.create_text(17, 17, text=(first + last).upper(),
                              fill="white", font=FONTS["small_bold"])

    # ── Media panel ───────────────────────────────────────────────────────────
    def _build_media_panel(self, parent):
        self._media_counter_var = tk.StringVar()
        self._update_media_counter()

        counter_bar = tk.Frame(parent, bg=COLORS["background"])
        counter_bar.pack(fill="x", pady=(0, 6))
        tk.Label(counter_bar, textvariable=self._media_counter_var,
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["background"]).pack(side="right")

        self._media_outer = tk.Frame(parent, bg=COLORS["navy"])
        self._media_outer.pack(fill="both", expand=True)

        if len(self.media_list) > 1:
            self._prev_btn_cfg = dict(
                text="‹", font=("Poppins", 24, "bold"),
                bg=COLORS["primary_red"], fg=COLORS["white"],
                activebackground=COLORS.get("primary_red_dark", "#8B1520"),
                activeforeground=COLORS["white"],
                relief="flat", bd=0, cursor="hand2", width=2,
                command=self._prev_media,
            )
            self._next_btn_cfg = dict(
                text="›", font=("Poppins", 24, "bold"),
                bg=COLORS["primary_red"], fg=COLORS["white"],
                activebackground=COLORS.get("primary_red_dark", "#8B1520"),
                activeforeground=COLORS["white"],
                relief="flat", bd=0, cursor="hand2", width=2,
                command=self._next_media,
            )

        self._render_current_media()

    # ── Render current media ──────────────────────────────────────────────────
    def _render_current_media(self):
        if self._active_player:
            try:
                self._active_player.destroy()
            except Exception:
                pass
            self._active_player = None

        for child in self._media_outer.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

        if not self.media_list:
            self._show_no_media()
            return

        if self.current_media_index >= len(self.media_list):
            self.current_media_index = 0

        item  = self.media_list[self.current_media_index]
        mtype = item.get("type", "image")
        path  = item.get("path") or item.get("url", "")

        if mtype == "video":
            self._render_video(path)
        else:
            self._render_image_canvas(path)

        if len(self.media_list) > 1:
            self._add_nav_buttons()

    # ── No-media fallback: logo + "THE GEARS" ─────────────────────────────────
    def _show_no_media(self):
        c = tk.Canvas(self._media_outer, bg=COLORS["navy"], highlightthickness=0)
        c.pack(fill="both", expand=True)

        # Keep a reference so GC doesn't collect it
        self._no_media_logo_ref = None

        def _draw(e=None):
            c.delete("all")
            w = e.width  if e else c.winfo_width()
            h = e.height if e else c.winfo_height()
            if w < 10 or h < 10:
                return

            draw_rounded_rect(c, 10, 10, w - 10, h - 10,
                              r=18, fill=COLORS["navy"], outline="")

            # Decorative diagonal slash (orange accent)
            c.create_polygon(
                0,       h * 0.55,
                w * 0.18, 0,
                w * 0.28, 0,
                w * 0.10, h * 0.55,
                fill=COLORS["primary_orange"], outline=""
            )

            cx, cy = w // 2, h // 2

            # Logo image (centred, 72×72)
            try:
                logo_img = Image.open(_LOGO_PATH).resize((72, 72), Image.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                c._logo_photo_ref = logo_photo          # prevent GC on canvas
                self._no_media_logo_ref = logo_photo
                c.create_image(cx, cy - 36, image=logo_photo, anchor="center")
            except Exception:
                # Fallback: orange circle with TG
                r2 = 36
                c.create_oval(cx - r2, cy - r2 - 36,
                              cx + r2, cy + r2 - 36,
                              fill=COLORS["primary_orange"], outline="")
                c.create_text(cx, cy - 36,
                              text="TG", fill="white",
                              font=("Poppins", 22, "bold"))

            # "THE GEARS" in Hedvig
            c.create_text(cx, cy + 18,
                          text="THE GEARS",
                          fill=COLORS["white"],
                          font=("Hedvig Letters Serif", 22, "bold"))

            # Tagline
            c.create_text(cx, cy + 50,
                          text="No media attached",
                          fill="#7F8AA8",
                          font=FONTS["small"])

        c.bind("<Configure>", _draw)

    # ── Image canvas ──────────────────────────────────────────────────────────
    def _render_image_canvas(self, path: str):
        canvas = tk.Canvas(self._media_outer, bg=COLORS["navy"],
                           highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self._active_player = canvas

        def _draw(e=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 2 or h < 2:
                return
            draw_rounded_rect(canvas, 10, 10, w - 10, h - 10,
                              r=18, fill=COLORS["navy"], outline="")

            img = self._fetch_image(path)
            if img:
                try:
                    display = img.copy()
                    display.thumbnail((w - 40, h - 40), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(display)
                    canvas._photo = photo
                    canvas.create_image(w // 2, h // 2, image=photo, anchor="center")
                except Exception as ex:
                    canvas.create_text(w // 2, h // 2,
                                       text=f"Image render error:\n{ex}",
                                       fill="white", font=FONTS["body"], width=w - 80)
            else:
                fname = path.replace("\\", "/").split("/")[-1]
                canvas.create_text(w // 2, h // 2,
                                   text=f"Image not found:\n{fname}",
                                   fill="white", font=FONTS["body"], width=w - 80)

        canvas.bind("<Configure>", _draw)
        threading.Thread(target=lambda: self.after(50, _draw), daemon=True).start()

    # ── Video ─────────────────────────────────────────────────────────────────
    def _render_video(self, path: str):
        local_path = self._resolve_video_path(path)

        if local_path and VLC_AVAILABLE:
            player = VLCPlayerFrame(self._media_outer, local_path)
            player.pack(fill="both", expand=True)
            self._active_player = player
            return

        if local_path and CV2_AVAILABLE:
            if not local_path.startswith("http"):
                player = CV2PlayerFrame(self._media_outer, local_path)
                player.pack(fill="both", expand=True)
                self._active_player = player
                return

        self._render_video_thumbnail_fallback(path, None)

    def _render_video_thumbnail_fallback(self, original_path: str, local_path):
        canvas = tk.Canvas(self._media_outer, bg=COLORS["navy"],
                           highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self._active_player = canvas

        thumb = self._fetch_thumbnail(local_path) if local_path else None

        def _draw(e=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 2 or h < 2:
                return
            draw_rounded_rect(canvas, 10, 10, w - 10, h - 10,
                              r=18, fill=COLORS["navy"], outline="")

            if thumb:
                try:
                    display = thumb.copy()
                    display.thumbnail((w - 40, h - 40), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(display)
                    canvas._photo = photo
                    canvas.create_image(w // 2, h // 2, image=photo, anchor="center")
                except Exception:
                    pass
            else:
                canvas.create_text(w // 2, h // 2 - 40,
                                   text="🎬", font=("Helvetica", 48))

            cx, cy, r = w // 2, h // 2, 32
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                               fill="black", outline="", stipple="gray50")
            canvas.create_polygon(
                cx - 11, cy - 18,
                cx - 11, cy + 18,
                cx + 20, cy,
                fill="white", outline="",
            )

            hint = ("Install python-vlc for video playback"
                    if not VLC_AVAILABLE else
                    "Video file not found on disk")
            canvas.create_text(w // 2, h - 32,
                               text=hint, fill="#CBD5E1",
                               font=FONTS["small"], width=w - 60)

        canvas.bind("<Configure>", _draw)

    def _add_nav_buttons(self):
        children = self._media_outer.winfo_children()
        if not children:
            return
        target = children[0]

        prev  = tk.Button(target if isinstance(target, tk.Canvas) else self._media_outer,
                          **self._prev_btn_cfg)
        next_ = tk.Button(target if isinstance(target, tk.Canvas) else self._media_outer,
                          **self._next_btn_cfg)

        if isinstance(target, tk.Canvas):
            prev.place(relx=0.02, rely=0.5, anchor="w")
            next_.place(relx=0.98, rely=0.5, anchor="e")
        else:
            prev.place(in_=self._media_outer, relx=0.01, rely=0.45, anchor="w")
            next_.place(in_=self._media_outer, relx=0.99, rely=0.45, anchor="e")

    def _update_media_counter(self):
        total = len(self.media_list)
        if total > 1:
            self._media_counter_var.set(f"{self.current_media_index + 1} / {total}")
        else:
            self._media_counter_var.set("")

    def _prev_media(self):
        if not self.media_list:
            return
        self.current_media_index = (self.current_media_index - 1) % len(self.media_list)
        self._update_media_counter()
        self._render_current_media()

    def _next_media(self):
        if not self.media_list:
            return
        self.current_media_index = (self.current_media_index + 1) % len(self.media_list)
        self._update_media_counter()
        self._render_current_media()

    # ── Path/URL helpers ──────────────────────────────────────────────────────
    def _resolve_video_path(self, path: str) -> str | None:
        UPLOAD_DIR = os.getenv(
            "UPLOAD_DIR",
            r"C:\Users\Jasper\Downloads\The_Gears_Web\Web_TheGears\static\uploads",
        )
        FLASK_URL = os.getenv("FLASK_URL", "http://127.0.0.1:5000")

        if path.startswith("http://") or path.startswith("https://"):
            return path
        if os.path.isabs(path) and os.path.exists(path):
            return path

        bare = path.replace("\\", "/").split("/")[-1].split("?")[0]
        for subdir in ["", "avatars"]:
            candidate = os.path.join(UPLOAD_DIR, subdir, bare) if subdir else os.path.join(UPLOAD_DIR, bare)
            if os.path.exists(candidate):
                return candidate

        flask_url = f"{FLASK_URL}/static/uploads/{bare}"
        print(f"[ArticleDetail] video not on disk, streaming from Flask: {flask_url}")
        return flask_url

    def _fetch_thumbnail(self, path: str):
        if not path or not os.path.exists(path):
            return None
        if path in self._thumb_cache:
            return self._thumb_cache[path]

        import subprocess, tempfile

        FFMPEG = os.getenv("FFMPEG_PATH", r"C:\ffmpeg\bin\ffmpeg.exe")
        bare   = os.path.basename(path)
        thumb_path = os.path.join(tempfile.gettempdir(), f"tk_thumb_{bare}.jpg")

        if os.path.exists(thumb_path):
            try:
                img = Image.open(thumb_path)
                img.load()
                self._thumb_cache[path] = img
                return img
            except Exception:
                pass

        try:
            result = subprocess.run(
                [FFMPEG, "-y", "-i", path,
                 "-ss", "00:00:01", "-vframes", "1",
                 "-vf", "scale=640:-1", "-q:v", "3", thumb_path],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0 and os.path.exists(thumb_path):
                img = Image.open(thumb_path)
                img.load()
                self._thumb_cache[path] = img
                return img
            err = result.stderr.decode("utf-8", errors="replace")[-300:]
            print(f"[ArticleDetail] FFmpeg failed: {err}")
        except Exception as e:
            print(f"[ArticleDetail] FFmpeg error: {e}")

        self._thumb_cache[path] = None
        return None

    def _fetch_image(self, path: str):
        if path in self._thumb_cache:
            return self._thumb_cache[path]

        FLASK_URL = os.getenv("FLASK_URL", "http://127.0.0.1:5000")
        img = None

        if path.startswith("http://") or path.startswith("https://"):
            try:
                req = urllib.request.Request(path, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    img = Image.open(_io.BytesIO(resp.read()))
                img.load()
            except Exception as e:
                print(f"[ArticleDetail] remote image failed: {e}")

        elif os.path.isabs(path) and os.path.exists(path):
            try:
                img = Image.open(path)
            except Exception as e:
                print(f"[ArticleDetail] local image failed: {e}")

        if img is None:
            filename = path.replace("\\", "/").split("/")[-1]
            try:
                url = f"{FLASK_URL}/static/uploads/{filename}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    img = Image.open(_io.BytesIO(resp.read()))
                img.load()
                print(f"[ArticleDetail] ✅ Loaded from Flask: {filename}")
            except Exception as e:
                print(f"[ArticleDetail] Flask fetch failed: {e}")

        self._thumb_cache[path] = img
        return img

    # ── Right panel ───────────────────────────────────────────────────────────
    def _build_right_panel(self, parent):
        header = tk.Frame(parent, bg=COLORS["background_alt"])
        header.pack(fill="x")

        # Logo in right panel header
        rp_logo = _load_logo(36)
        if rp_logo:
            self._rp_logo_photo = rp_logo      # keep reference
            rp_logo_c = tk.Canvas(header, width=40, height=40,
                                  bg=COLORS["background_alt"], highlightthickness=0)
            rp_logo_c.pack(side="left", padx=12, pady=10)
            rp_logo_c.create_image(20, 20, image=rp_logo, anchor="center")
        else:
            av = tk.Canvas(header, width=40, height=40,
                           bg=COLORS["background_alt"], highlightthickness=0)
            av.pack(side="left", padx=12, pady=10)
            av.create_oval(2, 2, 38, 38, fill=COLORS["primary_orange"], outline="")
            av.create_text(20, 20, text="TG", fill=COLORS["white"],
                           font=("Poppins", 12, "bold"))

        tk.Label(header, text="The Gears Publications",
                 font=FONTS["body_bold"], fg=COLORS["text_dark"],
                 bg=COLORS["background_alt"]).pack(side="left", padx=(0, 12))

        outer = tk.Frame(parent, bg=COLORS["card"])
        outer.pack(fill="both", expand=True)

        body_canvas = tk.Canvas(outer, bg=COLORS["card"], highlightthickness=0)
        body_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(outer, orient="vertical",
                                 command=body_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        body_canvas.configure(yscrollcommand=scrollbar.set)

        inner  = tk.Frame(body_canvas, bg=COLORS["card"])
        win_id = body_canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>",
                   lambda e: body_canvas.configure(
                       scrollregion=body_canvas.bbox("all")))
        body_canvas.bind("<Configure>",
                         lambda e: body_canvas.itemconfig(win_id, width=e.width))

        def _wheel(e):
            body_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        body_canvas.bind("<Enter>",
                         lambda e: body_canvas.bind_all("<MouseWheel>", _wheel))
        body_canvas.bind("<Leave>",
                         lambda e: body_canvas.unbind_all("<MouseWheel>"))

        self._build_article_section(inner)
        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill="x", padx=16, pady=(0, 8))
        self._build_comments_section(inner)
        self._build_comment_form(inner)

    # ── Article text ──────────────────────────────────────────────────────────
    def _build_article_section(self, parent):
        wrap = tk.Frame(parent, bg=COLORS["card"])
        wrap.pack(fill="x", padx=16, pady=(14, 10))

        author = (f"{self.article.get('first_name','')} "
                  f"{self.article.get('last_name','')}").strip()
        cat    = self.article.get("category", "")
        date   = str(self.article.get("created_at", ""))

        cat_key        = str(cat).strip().upper()
        cat_bg, cat_fg = CAT_COLORS.get(cat_key, ("#F3F4F6", "#374151"))
        tk.Label(wrap, text=cat.upper(), font=FONTS["tag"],
                 fg=cat_fg, bg=cat_bg, padx=8, pady=3).pack(anchor="w", pady=(0, 8))

        tk.Label(wrap, text=self.article.get("headline", ""),
                 font=FONTS["card_title"], fg=COLORS["text_dark"],
                 bg=COLORS["card"], wraplength=370, justify="left").pack(anchor="w")

        tk.Label(wrap, text=f"By {author}  ·  {date}",
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["card"]).pack(anchor="w", pady=(4, 12))

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
            self._text_lbl.config(
                text=self._full_text[:self.PREVIEW_LIMIT].rstrip() + "…")
            self._toggle_lbl.config(text="See more ▼")

    def _toggle_text(self):
        self._article_expanded = not self._article_expanded
        self._render_text()

    # ── Comments ──────────────────────────────────────────────────────────────
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
            name = (f"{c.get('first_name','')} {c.get('last_name','')}").strip()
            text = c.get("comment", "")
            date = str(c.get("created_at", ""))

            item = tk.Frame(self._comments_frame,
                            bg=COLORS["background_alt"],
                            highlightbackground=COLORS["border"],
                            highlightthickness=1)
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

        user_id     = self.user[3] if self.user and len(self.user) > 3 else None
        can_comment = bool(user_id and is_user_accepted(user_id))
        self.can_comment = can_comment

        tk.Frame(form, bg=COLORS["border"], height=1).pack(fill="x", pady=(0, 10))

        if self.user:
            name = (f"{self.user[0]} {self.user[1]}"
                    if len(self.user) > 1 else self.user[0])
            tk.Label(form, text=f"Commenting as  {name}",
                     font=FONTS["small"], fg=COLORS["text_grey"],
                     bg=COLORS["card"]).pack(anchor="w", pady=(0, 4))

        self._comment_text = tk.Text(
            form, height=4, font=FONTS["body"],
            bg=COLORS["input_bg"], fg=COLORS["text_dark"],
            relief="solid", bd=1, wrap="word",
            highlightcolor=COLORS["border_focus"],
            insertbackground=COLORS["primary_orange"],
        )
        self._comment_text.pack(fill="x", pady=(0, 8))

        if not can_comment:
            self._comment_text.config(state="disabled")
            tk.Label(form,
                     text=("Your account is view-only. Please wait for an admin or "
                           "superadmin to accept your account before commenting."),
                     font=FONTS["small"], fg=COLORS["text_grey"],
                     bg=COLORS["card"], wraplength=360, justify="left",
                     ).pack(anchor="w", pady=(0, 8))

        btn_row = tk.Frame(form, bg=COLORS["card"])
        btn_row.pack(fill="x")

        if not self.user:
            tk.Label(btn_row, text="Log in to post a comment.",
                     font=FONTS["small"], fg=COLORS["text_grey"],
                     bg=COLORS["card"]).pack(side="left")

        if can_comment:
            post_c = tk.Canvas(btn_row, width=130, height=34,
                               bg=COLORS["card"], highlightthickness=0, cursor="hand2")
            post_c.pack(side="right")
            self._post_canvas  = post_c
            self._post_hovered = False
            self._draw_post_btn()
            post_c.bind("<Enter>",    lambda e: self._post_hover(True))
            post_c.bind("<Leave>",    lambda e: self._post_hover(False))
            post_c.bind("<Button-1>", lambda e: self._submit_comment())
        else:
            tk.Label(btn_row, text="View only",
                     font=FONTS["small_bold"], fg=COLORS["text_light"],
                     bg=COLORS["card"]).pack(side="right")

    def _draw_post_btn(self):
        self._post_canvas.delete("all")
        bg  = (COLORS["primary_orange_dark"] if self._post_hovered
               else COLORS["primary_orange"])
        w, h, r = 130, 34, 17
        self._post_canvas.create_oval(1, 1, h - 1, h - 1, fill=bg, outline=bg)
        self._post_canvas.create_oval(w - h + 1, 1, w - 1, h - 1, fill=bg, outline=bg)
        self._post_canvas.create_rectangle(r, 1, w - r, h - 1, fill=bg, outline=bg)
        self._post_canvas.create_line(r, 1,     w - r, 1,     fill=bg)
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
        if not getattr(self, "can_comment", False):
            messagebox.showwarning(
                "Comment Access Required",
                "Your account must be accepted before you can comment.", parent=self)
            return

        text = self._comment_text.get("1.0", "end").strip()
        if not text:
            messagebox.showerror("Empty Comment",
                                 "Please write something before posting.", parent=self)
            return

        user_id = self.user[3] if len(self.user) > 3 else None
        if not user_id:
            messagebox.showerror("Error",
                                 "User ID not found. Please log in again.", parent=self)
            return

        ok = add_comment(self.article_id, user_id, text)
        if not ok:
            messagebox.showerror("Error",
                                 "Failed to post comment. Please try again.", parent=self)
            return

        self._comment_text.delete("1.0", "end")
        self.comments = get_comments_by_article(self.article_id)
        self._render_comments()

    # ── Navigation ────────────────────────────────────────────────────────────
    def _go_back(self):
        if self._active_player and hasattr(self._active_player, "destroy"):
            try:
                self._active_player.destroy()
            except Exception:
                pass
            self._active_player = None

        if self.from_landing or not self.user:
            if hasattr(self.parent, "show_landing"):
                self.parent.show_landing()
            else:
                self.destroy()
            return

        if hasattr(self.parent, "show_articles"):
            self.parent.show_articles(self.user)
        else:
            self.destroy()


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Article Detail – Test")
    root.geometry("1200x800")
    root.minsize(900, 600)
    root.show_articles = lambda user: print("→ Back to articles, user:", user)
    ArticleDetailPage(root, article_id=1,
                      user=("Juan", "Dela Cruz", "juan@example.com", 1))
    root.mainloop()