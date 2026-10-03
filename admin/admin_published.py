"""
admin/admin_published.py
────────────────────────
Published Articles page for The Gears Admin.

Inherits the full header + sidebar + scrollable shell from AdminLayout.
Only the published articles table and view modal live here.

Article tuple index (from fetch_published):
  0  id
  1  title / article name (headline used as title fallback)
  2  category
  3  date_published
  4  author (admin_name / email)
  5  None
  6  autosaved_flag
  7  photographer
  8  headline
  9  content_text
 10  media_json_or_csv   ← file paths, comma-separated or JSON list

db_callbacks expected:
  fetch_published()   → list[tuple]
"""

from datetime import datetime
import json
import os
import subprocess
import tempfile
import tkinter as tk
from tkinter import messagebox, ttk
import ctypes

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from admin.admin_layout import AdminLayout, FONTS, COLORS


# ── VLC setup (same pattern as article_detail.py) ─────────────────────────────

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
                return True
            except Exception as e:
                print(f"[VLC] Failed to load from {_d}: {e}")
    return False

_vlc_dlls_loaded = _load_vlc_dlls()

VLC_AVAILABLE = False
if _vlc_dlls_loaded:
    try:
        import vlc as _vlc
        _test = _vlc.Instance("--no-video-title-show")
        _test.release()
        VLC_AVAILABLE = True
        print("[VLC] ✅ Loaded successfully")
    except Exception as e:
        print(f"[VLC] ❌ Import failed: {e}")
else:
    print("[VLC] ❌ libvlc.dll not found")

try:
    import cv2 as _cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


# ── Media helper ───────────────────────────────────────────────────────────────

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


# ── Embedded VLC player ────────────────────────────────────────────────────────

class _VLCPlayerFrame(tk.Frame):
    def __init__(self, parent, video_path: str, **kwargs):
        super().__init__(parent, bg="black", **kwargs)
        self._path     = video_path
        self._instance = None
        self._player   = None
        self._playing  = False
        self._build()

    def _build(self):
        if not VLC_AVAILABLE:
            tk.Label(self, text="🎬  VLC not installed\npip install python-vlc",
                    font=("Courier", 11), fg="white", bg="black",
                    justify="center").pack(expand=True)
            return

        self._canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<Map>", lambda e: self.after(50, self._draw_thumbnail))

        ctrl = tk.Frame(self, bg="#1a1a1a", height=44)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

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

        tk.Button(ctrl, text="■  Stop",
                  font=("Poppins", 10),
                  bg="#333", fg="white", relief="flat", bd=0,
                  activebackground="#555", cursor="hand2",
                  padx=12, pady=6,
                  command=self._stop).pack(side="left", padx=(0, 8), pady=6)

        tk.Label(ctrl, text="🔊", bg="#1a1a1a", fg="white",
                 font=("Poppins", 11)).pack(side="right", padx=(0, 4))
        self._vol_var = tk.IntVar(value=80)
        tk.Scale(ctrl, from_=0, to=100, orient="horizontal",
                 variable=self._vol_var, length=90,
                 bg="#1a1a1a", fg="white", troughcolor="#555",
                 highlightthickness=0, showvalue=False,
                 command=lambda v: self._set_volume(int(v))
                 ).pack(side="right", padx=(0, 12), pady=4)

        self.after(200, self._init_vlc)

    def _draw_thumbnail(self):
        """Extract frame 1s in and draw it on the canvas before play is pressed."""
        import subprocess, tempfile, os
        FFMPEG = os.getenv("FFMPEG_PATH", r"C:\ffmpeg\bin\ffmpeg.exe")
        if not PIL_AVAILABLE or not os.path.exists(FFMPEG):
            return
        try:
            bare = os.path.basename(self._path.split("?")[0])
            thumb_path = os.path.join(tempfile.gettempdir(), f"vlc_thumb_{bare}.jpg")
            if not os.path.exists(thumb_path):
                subprocess.run(
                    [FFMPEG, "-y", "-i", self._path,
                    "-ss", "00:00:01", "-vframes", "1",
                    "-vf", "scale=640:-1", "-q:v", "3", thumb_path],
                    capture_output=True, timeout=15
                )
            if not os.path.exists(thumb_path):
                return
            img = Image.open(thumb_path)
            img.load()
            w = self._canvas.winfo_width() or 640
            h = self._canvas.winfo_height() or 360
            img.thumbnail((w, h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._canvas._thumb_photo = photo   # keep reference
            self._canvas.delete("all")
            self._canvas.create_image(w // 2, h // 2, image=photo, anchor="center")
            # play icon overlay
            cx, cy, r = w // 2, h // 2, 28
            self._canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                    fill="black", outline="", stipple="gray50")
            self._canvas.create_polygon(cx-9, cy-16, cx-9, cy+16, cx+18, cy,
                                        fill="white", outline="")
        except Exception as e:
            print(f"[VLCPlayerFrame] thumbnail error: {e}")

    def _init_vlc(self):
        if not VLC_AVAILABLE:
            return
        try:
            self._instance = _vlc.Instance("--no-video-title-show")
            self._player   = self._instance.media_player_new()
            wid = self._canvas.winfo_id()
            if os.name == "nt":
                self._player.set_hwnd(wid)
            else:
                self._player.set_xwindow(wid)
            media = self._instance.media_new(self._path)
            self._player.set_media(media)
            self._player.audio_set_volume(self._vol_var.get())
        except Exception as e:
            print(f"[VLCPlayer] init error: {e}")

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

    def _set_volume(self, val):
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


# ── CV2 fallback player ────────────────────────────────────────────────────────

class _CV2PlayerFrame(tk.Frame):
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
            rgb = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            w = self._canvas.winfo_width()  or 640
            h = self._canvas.winfo_height() or 360
            pil = Image.fromarray(rgb)
            pil.thumbnail((w, h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(pil)
            self._canvas.delete("all")
            self._canvas.create_image(w // 2, h // 2, image=photo, anchor="center")
            self._photo = photo
        except Exception as e:
            print(f"[CV2Player] frame error: {e}")
        self._after_id = self.after(max(1, int(1000 / self._fps)), self._next_frame)

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


# ─────────────────────────────────────────────────────────────────────────────
class AdminPublished(AdminLayout):

    ACTIVE_NAV = "published"

    def __init__(self, root, user=None, db_callbacks=None):
        self.articles = self._load_articles(db_callbacks or {})
        super().__init__(root, user, db_callbacks)
        self._build_page()

    # ── Pre-fetch ──────────────────────────────────────────────────────────────

    def _load_articles(self, callbacks) -> list:
        if "fetch_published" in callbacks:
            try:
                return callbacks["fetch_published"]() or []
            except Exception as e:
                print(f"[AdminPublished] fetch error: {e}")
        return []

    def _reload(self):
        self.articles = self._load_articles(self.callbacks)
        self._refresh_table()

    # ── Page content ───────────────────────────────────────────────────────────

    def _build_page(self):
        self._build_panel_header()
        self._build_table_card()

    # ── Panel header ───────────────────────────────────────────────────────────

    def _build_panel_header(self):
        T    = self.theme
        wrap = tk.Frame(self.inner, bg=T["background"])
        wrap.pack(fill="x", pady=(0, 16))

        tk.Label(wrap, text="Published Articles",
                 bg=T["background"], fg=T["primary_orange"],
                 font=("Poppins", 20, "bold")).pack(anchor="w")
        tk.Label(wrap,
                 text="All articles that are live and visible to readers.\n"
                      "Click View to read the full article and media.",
                 bg=T["background"], fg=T["text_grey"],
                 font=FONTS["body"]).pack(anchor="w", pady=(4, 0))

    # ── Table card ─────────────────────────────────────────────────────────────

    def _build_table_card(self):
        T = self.theme
        self.table_card = tk.Frame(
            self.inner, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1
        )
        self.table_card.pack(fill="both", expand=True)

        card_hdr = tk.Frame(self.table_card, bg="#FAFAFA")
        card_hdr.pack(fill="x")

        lh = tk.Frame(card_hdr, bg="#FAFAFA")
        lh.pack(side="left", padx=20, pady=10)
        tk.Label(lh, text="Article List", bg="#FAFAFA",
                 fg=T["text_dark"], font=("Poppins", 13, "bold")).pack(anchor="w")
        tk.Label(lh, text="Approved and published articles.",
                 bg="#FAFAFA", fg=T["text_grey"],
                 font=("Poppins", 9)).pack(anchor="w", pady=(2, 0))

        self._badge_var = tk.StringVar(value=f"{len(self.articles)} articles")
        tk.Label(card_hdr, textvariable=self._badge_var,
                 bg="#FFF3E4", fg=T["primary_orange"],
                 font=("Poppins", 8, "bold"), padx=10, pady=4
                 ).pack(side="right", padx=18)

        ttk.Separator(self.table_card, orient="horizontal").pack(fill="x")

        cols = ("headline", "category", "date_published", "author", "status")
        self._tree = ttk.Treeview(
            self.table_card, columns=cols, show="headings", selectmode="browse"
        )

        col_config = {
            "headline":       ("Headline",       320, True),
            "category":       ("Category",       130, False),
            "date_published": ("Date Published", 160, False),
            "author":         ("Author",         160, False),
            "status":         ("Status",         110, False),
        }
        for c, (label, width, stretch) in col_config.items():
            self._tree.heading(c, text=label)
            self._tree.column(c, width=width, minwidth=60, stretch=stretch)

        style = ttk.Style()
        style.configure("Treeview",
                        font=("Poppins", 10), rowheight=32,
                        background=COLORS["card"],
                        fieldbackground=COLORS["card"],
                        foreground=COLORS["text_dark"])
        style.configure("Treeview.Heading",
                        font=("Poppins", 9, "bold"),
                        background="#FCFCFC", foreground="#999999")
        style.map("Treeview",
                  background=[("selected", COLORS["primary_orange_light"])],
                  foreground=[("selected", COLORS["text_dark"])])

        self._tree.tag_configure("even", background="#FCFCFC")
        self._tree.tag_configure("odd",  background=COLORS["card"])

        tree_sb = ttk.Scrollbar(self.table_card, orient="vertical",
                                command=self._tree.yview)
        self._tree.configure(yscrollcommand=tree_sb.set)
        tree_sb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self._actions_bar = tk.Frame(self.table_card, bg=COLORS["card"])
        self._actions_bar.pack(fill="x", padx=18, pady=8)
        self._build_actions_toolbar()

        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self._refresh_table()

    def _refresh_table(self):
        self._tree.delete(*self._tree.get_children())
        count = len(self.articles)
        self._badge_var.set(f"{count} article{'s' if count != 1 else ''}")

        if not self.articles:
            self._show_empty_notice()
            return
        self._hide_empty_notice()

        for i, art in enumerate(self.articles):
            headline = str(art[8]) if len(art) > 8 and art[8] else "(No headline)"
            category = str(art[2]) if len(art) > 2 and art[2] else "—"
            author   = str(art[4]) if len(art) > 4 and art[4] else "—"
            date_pub = art[3]      if len(art) > 3 else None

            if isinstance(date_pub, datetime):
                date_display = date_pub.strftime("%b %d, %Y")
            else:
                date_display = str(date_pub or "—")

            tag = "even" if i % 2 == 0 else "odd"
            self._tree.insert(
                "", "end", iid=str(art[0]),
                values=(headline, category, date_display, author, "● Published"),
                tags=(tag,)
            )

    

    def _build_actions_toolbar(self):
        for w in self._actions_bar.winfo_children():
            w.destroy()

        self._no_sel_label = tk.Label(
            self._actions_bar,
            text="Select a row to see available actions.",
            font=("Poppins", 9),
            bg=COLORS["card"],
            fg=COLORS["text_light"],
        )
        self._no_sel_label.pack(side="left")

        self._btn_view = tk.Button(
            self._actions_bar, text="👁  View",
            command=self._on_view,
            bg=COLORS["primary_orange_light"],
            fg=COLORS["primary_orange"],
            activebackground=COLORS["primary_orange"],
            activeforeground=COLORS["white"],
            font=("Poppins", 9, "bold"),
            bd=0, relief="flat", padx=10, pady=5, cursor="hand2",
        )
        self._btn_edit = tk.Button(
            self._actions_bar, text="✎  Edit",
            command=self._on_edit,
            bg=COLORS.get("success_bg", "#DCFCE7"),
            fg=COLORS.get("success", "#15803D"),
            activebackground=COLORS.get("success", "#15803D"),
            activeforeground=COLORS["white"],
            font=("Poppins", 9, "bold"),
            bd=0, relief="flat", padx=10, pady=5, cursor="hand2",
        )
        for btn in (self._btn_view, self._btn_edit):
            btn.pack_forget()

    def _on_row_select(self, _event=None):
        self._update_action_buttons(self._selected_article())

    def _selected_article(self):
        sel = self._tree.selection()
        if not sel:
            return None
        iid = int(sel[0])
        for a in self.articles:
            if a[0] == iid:
                return a
        return None

    def _update_action_buttons(self, article):
        self._no_sel_label.pack_forget()
        self._btn_view.pack_forget()
        self._btn_edit.pack_forget()
        if article is None:
            self._no_sel_label.pack(side="left")
            return
        self._btn_view.pack(side="left", padx=(0, 6))
        self._btn_edit.pack(side="left", padx=(0, 6))

    def _on_view(self):
        article = self._selected_article()
        if article:
            self._open_view_modal(article)

    def _on_edit(self):
        article = self._selected_article()
        if article:
            self._go_edit(article)

    def _show_empty_notice(self):
        if hasattr(self, "_empty_frame") and self._empty_frame.winfo_exists():
            return
        T = self.theme
        self._empty_frame = tk.Frame(self.table_card, bg=T["card"], pady=40)
        self._empty_frame.pack(fill="x")
        tk.Label(self._empty_frame, text="📰",
                 bg=T["card"], fg=T["text_light"], font=("Poppins", 32)).pack()
        tk.Label(self._empty_frame, text="No published articles yet.",
                 bg=T["card"], fg=T["text_grey"], font=("Poppins", 11)).pack(pady=(8, 4))
        tk.Label(self._empty_frame, text="Approved articles will appear here.",
                 bg=T["card"], fg=T["text_light"], font=("Poppins", 9)).pack()

    def _hide_empty_notice(self):
        if hasattr(self, "_empty_frame"):
            try:
                self._empty_frame.destroy()
            except Exception:
                pass

    # ── View Modal ─────────────────────────────────────────────────────────────

    def _open_view_modal(self, art):
        T = self.theme

        title        = art[1]  if len(art) > 1  else ""
        headline     = art[8]  if len(art) > 8  else ""
        content      = art[9]  if len(art) > 9  else ""
        photographer = art[7]  if len(art) > 7  else ""
        date_pub     = art[3]  if len(art) > 3  else None
        author       = art[4]  if len(art) > 4  else ""
        category     = art[2]  if len(art) > 2  else ""
        media_raw    = art[10] if len(art) > 10 else None
        media_files  = _parse_media(media_raw)

        if isinstance(date_pub, datetime):
            date_display = date_pub.strftime("%b %d, %Y  %I:%M %p")
        else:
            date_display = str(date_pub or "—")

        UPLOAD_DIR = os.getenv(
            "UPLOAD_DIR",
            r"C:\Users\Jasper\Downloads\The_Gears_Web\Web_TheGears\static\uploads"
        )
        FFMPEG    = os.getenv("FFMPEG_PATH", r"C:\ffmpeg\bin\ffmpeg.exe")
        FLASK_URL = self.callbacks.get("flask_url", "http://127.0.0.1:5000")

        # ── Window setup ──────────────────────────────────────────────────────
        win = tk.Toplevel(self.root)
        win.title("Published Article")
        win.configure(bg=T["card"])
        win.resizable(True, True)
        win.grab_set()
        win.transient(self.root)

        rw = self.root.winfo_width()  or 1280
        rh = self.root.winfo_height() or 800
        mw, mh = min(1160, rw - 40), min(800, rh - 40)
        rx = self.root.winfo_rootx() + (rw - mw) // 2
        ry = self.root.winfo_rooty() + (rh - mh) // 2
        win.geometry(f"{mw}x{mh}+{rx}+{ry}")

        # Keep reference to active video player for cleanup
        win._active_player = None

        def _cleanup_player():
            if win._active_player:
                try:
                    win._active_player.destroy()
                except Exception:
                    pass
                win._active_player = None

        win.protocol("WM_DELETE_WINDOW", lambda: (_cleanup_player(), win.destroy()))

        # ── Modal header ──────────────────────────────────────────────────────
        hdr       = tk.Frame(win, bg=T["primary_orange_light"])
        hdr.pack(fill="x")
        hdr_inner = tk.Frame(hdr, bg=T["primary_orange_light"])
        hdr_inner.pack(fill="x", padx=18, pady=12)

        icon_cv = tk.Canvas(hdr_inner, width=34, height=34,
                            bg=T["primary_orange_light"], highlightthickness=0)
        icon_cv.pack(side="left", padx=(0, 12))
        icon_cv.create_oval(1, 1, 33, 33, fill=T["white"], outline="")
        icon_cv.create_text(17, 17, text="📰", font=("Poppins", 16))

        txt_f = tk.Frame(hdr_inner, bg=T["primary_orange_light"])
        txt_f.pack(side="left", fill="x", expand=True)
        tk.Label(txt_f, text=title or headline or "(Untitled Article)",
                 bg=T["primary_orange_light"], fg=T["text_dark"],
                 font=("Poppins", 13, "bold"), anchor="w",
                 wraplength=mw - 280).pack(anchor="w")

        meta_parts = []
        if author:       meta_parts.append(f"✍  {author}")
        if date_display: meta_parts.append(f"🗓  {date_display}")
        if photographer: meta_parts.append(f"📷  {photographer}")
        if category:     meta_parts.append(f"🏷  {category}")
        tk.Label(txt_f, text="   ·   ".join(meta_parts),
                 bg=T["primary_orange_light"], fg=T["text_grey"],
                 font=FONTS["small"], anchor="w",
                 wraplength=mw - 280, justify="left").pack(anchor="w", pady=(3, 0))

        tk.Label(hdr_inner, text="● Published",
                 bg="#DCFCE7", fg=COLORS.get("success", "#15803D"),
                 font=FONTS["small_bold"], padx=8, pady=4
                 ).pack(side="left", padx=12)

        tk.Button(hdr_inner, text="✕",
                  command=lambda: (_cleanup_player(), win.destroy()),
                  bg=T["primary_orange_light"], fg=T["text_grey"],
                  activebackground=T["border"],
                  font=("Poppins", 14), bd=0, relief="flat",
                  cursor="hand2").pack(side="right")

        tk.Frame(win, bg=T["border"], height=1).pack(fill="x")

    
     
        # ── Body: two-column layout ───────────────────────────────────────────
        body_wrap = tk.Frame(win, bg=T["background_alt"])
        body_wrap.pack(fill="both", expand=True)

        body_inner = tk.Frame(body_wrap, bg=T["background_alt"])
        body_inner.pack(fill="both", expand=True, padx=14, pady=12)

        body_inner.grid_columnconfigure(0, weight=10, minsize=320)
        body_inner.grid_columnconfigure(1, weight=11, minsize=320)
        body_inner.grid_rowconfigure(0, weight=1)
# NO pack_propagate here — grid manages children, pack manages body_inner itself

        # ── LEFT: media panel ──────────────────────────────────────────────────
        media_state = {"files": media_files, "idx": 0}
        self._media_photos = {}

        left_panel = tk.Frame(body_inner, bg="#0F172A")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        def _resolve_path(fp: str):
            fp   = str(fp).strip().replace("\\", "/")
            bare = fp.split("/")[-1].split("?")[0]
            candidates = [
                os.path.join(UPLOAD_DIR, bare),
                fp if os.path.isabs(fp) else None,
                os.path.join("static", "uploads", bare),
            ]
            for c in candidates:
                if c and os.path.exists(c):
                    return c
            # Fall back to Flask URL so VLC can stream
            return f"{FLASK_URL}/static/uploads/{bare}"

        def _render_media():
            # Destroy previous player widget if any
            _cleanup_player()
            for child in left_panel.winfo_children():
                try:
                    child.destroy()
                except Exception:
                    pass
            win._active_player = None

            files = media_state["files"]
            idx   = media_state["idx"]

            if not files:
                c = tk.Canvas(left_panel, bg="#1A1A1A", highlightthickness=0)
                c.pack(fill="both", expand=True)
                c.bind("<Configure>", lambda e: (
                    c.delete("all"),
                    c.create_text(e.width // 2, e.height // 2,
                                  text="📷  No media attached.",
                                  fill="#9CA3AF", font=FONTS["body"])
                ))
                return

            fp  = files[idx]
            ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else ""

            # ── VIDEO ──────────────────────────────────────────────────────────
            if ext in ("mp4", "mov", "avi", "mkv", "webm"):
                resolved = _resolve_path(fp)

                if VLC_AVAILABLE:
                    player = _VLCPlayerFrame(left_panel, resolved)
                    player.pack(fill="both", expand=True)
                    win._active_player = player
                elif CV2_AVAILABLE and not resolved.startswith("http"):
                    player = _CV2PlayerFrame(left_panel, resolved)
                    player.pack(fill="both", expand=True)
                    win._active_player = player
                else:
                    # Fallback: thumbnail + play icon static
                    _render_video_fallback(fp, resolved)

                # Nav arrows on top of player
                if len(files) > 1:
                    _add_nav_arrows()
                return

            # ── IMAGE ──────────────────────────────────────────────────────────
            canvas = tk.Canvas(left_panel, bg="#1A1A1A", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            win._active_player = canvas

            def _draw_image(e=None):
                canvas.delete("all")
                w = canvas.winfo_width()
                h = canvas.winfo_height()
                if w < 2 or h < 2:
                    return

                if ext in ("png", "jpg", "jpeg", "gif", "webp") and PIL_AVAILABLE:
                    local = _resolve_path(fp)
                    img   = None

                    if local and not local.startswith("http") and os.path.exists(local):
                        try:
                            img = Image.open(local)
                            img.load()
                        except Exception:
                            img = None

                    if img is None:
                        import io as _io, urllib.request
                        bare = os.path.basename(fp.split("?")[0])
                        for url in [
                            f"{FLASK_URL}/static/uploads/{bare}",
                            f"{FLASK_URL}/static/uploads/avatars/{bare}",
                        ]:
                            try:
                                req = urllib.request.Request(
                                    url, headers={"User-Agent": "Mozilla/5.0"})
                                with urllib.request.urlopen(req, timeout=6) as resp:
                                    img = Image.open(_io.BytesIO(resp.read()))
                                    img.load()
                                break
                            except Exception:
                                continue

                    if img:
                        try:
                            img.thumbnail((w - 20, h - 20), Image.LANCZOS)
                            photo = ImageTk.PhotoImage(img)
                            self._media_photos[f"{idx}_img"] = photo
                            canvas.create_image(w // 2, h // 2, image=photo, anchor="center")
                        except Exception as ex:
                            canvas.create_text(w // 2, h // 2,
                                               text=f"Image error:\n{ex}",
                                               fill="#9CA3AF", font=FONTS["body"])
                        if len(files) > 1:
                            canvas.create_rectangle(w - 52, h - 28, w - 4, h - 4,
                                                    fill="#0F172A", outline="")
                            canvas.create_text(w - 28, h - 16,
                                               text=f"{idx + 1}/{len(files)}",
                                               fill="white", font=FONTS["small"])
                        return

                canvas.create_text(
                    canvas.winfo_width() // 2,
                    canvas.winfo_height() // 2,
                    text=f"📄  {os.path.basename(fp)}",
                    fill="#9CA3AF", font=FONTS["body"]
                )

            canvas.bind("<Configure>", _draw_image)

            if len(files) > 1:
                _add_nav_arrows()

        def _render_video_fallback(fp, resolved):
            canvas = tk.Canvas(left_panel, bg="#0F172A", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            win._active_player = canvas

            thumb = None
            if PIL_AVAILABLE and resolved and not resolved.startswith("http") \
                    and os.path.exists(resolved) and os.path.exists(FFMPEG):
                bare       = os.path.basename(resolved)
                thumb_path = os.path.join(tempfile.gettempdir(), f"adm_thumb_{bare}.jpg")
                if not os.path.exists(thumb_path):
                    try:
                        subprocess.run(
                            [FFMPEG, "-y", "-i", resolved,
                             "-ss", "00:00:01", "-vframes", "1",
                             "-vf", "scale=640:-1", "-q:v", "3", thumb_path],
                            capture_output=True, timeout=30
                        )
                    except Exception as e:
                        print(f"[AdminPublished] ffmpeg: {e}")
                if os.path.exists(thumb_path):
                    try:
                        img = Image.open(thumb_path)
                        img.load()
                        thumb = img
                    except Exception:
                        pass

            def _draw(e=None):
                canvas.delete("all")
                w = canvas.winfo_width()
                h = canvas.winfo_height()
                if w < 2 or h < 2:
                    return
                if thumb and PIL_AVAILABLE:
                    try:
                        display = thumb.copy()
                        display.thumbnail((w, h), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(display)
                        canvas._thumb_photo = photo
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
                    cx - 11, cy - 18, cx - 11, cy + 18, cx + 20, cy,
                    fill="white", outline="")
                hint = ("Install python-vlc for video playback"
                        if not VLC_AVAILABLE else "Video file not found")
                canvas.create_text(w // 2, h - 28, text=hint,
                                   fill="#CBD5E1", font=FONTS["small"], width=w - 60)

            canvas.bind("<Configure>", _draw)

        def _add_nav_arrows():
            files = media_state["files"]

            def _prev():
                media_state["idx"] = (media_state["idx"] - 1 + len(files)) % len(files)
                _render_media()

            def _next():
                media_state["idx"] = (media_state["idx"] + 1) % len(files)
                _render_media()

            for side, cmd, txt in (("left", _prev, "‹"), ("right", _next, "›")):
                tk.Button(left_panel, text=txt, command=cmd,
                          bg="#0F172A", fg="white",
                          font=("Poppins", 22, "bold"),
                          bd=0, relief="flat", cursor="hand2", width=2
                          ).place(
                              relx=0.0 if side == "left" else 1.0,
                              rely=0.5,
                              anchor="w" if side == "left" else "e",
                              x=6 if side == "left" else -6)

        _render_media()

        # ── RIGHT: content panel ───────────────────────────────────────────────
        right_panel = tk.Frame(body_inner, bg=T["card"])
        right_panel.grid(row=0, column=1, sticky="nsew")

        right_canvas = tk.Canvas(right_panel, bg=T["card"], highlightthickness=0)
        right_sb     = tk.Scrollbar(right_panel, orient="vertical",
                                    command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_sb.set)
        right_sb.pack(side="right", fill="y")
        right_canvas.pack(side="left", fill="both", expand=True)

        right_inner = tk.Frame(right_canvas, bg=T["card"])
        r_win = right_canvas.create_window((0, 0), window=right_inner, anchor="nw")

        right_inner.bind("<Configure>",
                         lambda e: right_canvas.configure(
                             scrollregion=right_canvas.bbox("all")))
        right_canvas.bind("<Configure>",
                          lambda e: right_canvas.itemconfig(r_win, width=e.width))
        right_canvas.bind("<Enter>",
                          lambda e: right_canvas.bind_all(
                              "<MouseWheel>",
                              lambda ev: right_canvas.yview_scroll(
                                  int(-1 * (ev.delta / 120)), "units")))
        right_canvas.bind("<Leave>",
                          lambda e: right_canvas.unbind_all("<MouseWheel>"))

        inner = tk.Frame(right_inner, bg=T["card"])
        inner.pack(fill="both", expand=True, padx=18, pady=16)

        # ── Category pill ──────────────────────────────────────────────────────
        if category:
            tk.Label(inner, text=str(category).upper(),
                     bg=T["primary_orange_light"], fg=T["primary_orange"],
                     font=FONTS["tag"], padx=8, pady=3).pack(anchor="w", pady=(0, 10))

        # ── Headline box ───────────────────────────────────────────────────────
        hl_box = tk.Frame(inner, bg="#FEF3C7",
                          highlightbackground="#FCD34D", highlightthickness=1)
        hl_box.pack(fill="x", pady=(0, 14))
        tk.Label(hl_box, text="HEADLINE",
         bg="#FEF3C7", fg="#B45309",
         font=FONTS["tag"], padx=12, pady=8).pack(anchor="w", pady=(0, 2))
        tk.Label(hl_box,
            text=str(headline) if headline else "(No headline)",
            bg="#FEF3C7", fg=T["text_dark"],
            font=("Poppins", 12, "bold"),
            padx=12, pady=4,
            wraplength=460, justify="left").pack(anchor="w", pady=(0, 12))

        # ── Author / Date / Photographer info row ──────────────────────────────
        info_row = tk.Frame(inner, bg=T["background_alt"],
                            highlightbackground=T["border"], highlightthickness=1)
        info_row.pack(fill="x", pady=(0, 14))

        # Fix: use pack instead of grid to avoid column overlap bugs
        info_data = [
            ("✍  Author",       str(author)       if author       else "—"),
            ("🗓  Published",    date_display                              ),
            ("📷  Photographer", str(photographer) if photographer else "—"),
        ]
        for i, (label, value) in enumerate(info_data):
            col_f = tk.Frame(info_row, bg=T["background_alt"])
            col_f.pack(side="left", padx=14, pady=10, fill="x", expand=True)
            tk.Label(col_f, text=label,
                     bg=T["background_alt"], fg=T["text_grey"],
                     font=FONTS["tag"]).pack(anchor="w")
            tk.Label(col_f, text=value,
                     bg=T["background_alt"], fg=T["text_dark"],
                     font=FONTS["body_bold"],
                     wraplength=150, justify="left").pack(anchor="w")
            if i < len(info_data) - 1:
                tk.Frame(info_row, bg=T["border"], width=1
                         ).pack(side="left", fill="y", pady=6)

        # ── Full article content ───────────────────────────────────────────────
        tk.Label(inner, text="FULL ARTICLE",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["tag"]).pack(anchor="w", pady=(0, 6))

        txt_wrap = tk.Frame(inner, bg=T["input_bg"],
                            highlightbackground=T["border"], highlightthickness=1)
        txt_wrap.pack(fill="both", expand=True)

        txt = tk.Text(txt_wrap, wrap="word",
                      font=FONTS["body"],
                      bg=T["input_bg"], fg=T["text_dark"],
                      relief="flat", padx=12, pady=10,
                      bd=0, highlightthickness=0)
        txt_scroll = tk.Scrollbar(txt_wrap, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=txt_scroll.set)
        txt_scroll.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", str(content) if content else "(No content available.)")
        txt.config(state="disabled")

        # ── Modal footer ───────────────────────────────────────────────────────
        tk.Frame(win, bg=T["border"], height=1).pack(fill="x")
        foot = tk.Frame(win, bg=T["card"])
        foot.pack(fill="x", padx=18, pady=(8, 12))

        tk.Button(foot, text="Edit Article",
                  command=lambda: (_cleanup_player(), win.destroy(), self._go_edit(art)),
                  bg=T["primary_orange"], fg="white",
                  activebackground=T["primary_orange_dark"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=14, pady=7, cursor="hand2").pack(side="right", padx=(6, 0))

        tk.Button(foot, text="Close",
                  command=lambda: (_cleanup_player(), win.destroy()),
                  bg=T["background_alt"], fg=T["text_mid"],
                  activebackground=T["border"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=14, pady=7, cursor="hand2").pack(side="right")

    # ── Edit navigation stub ───────────────────────────────────────────────────

    def _go_edit(self, article):
        messagebox.showinfo("Edit", f"Edit article ID {article[0]} — coming soon.")


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Admin Published Test")
    root.geometry("1200x800")

    fake_user = ("John", "Doe", "john@example.com", 1, "admin")

    def mock_fetch_published():
        return [
            (1, "Sample Article Title", "News", "2026-01-01",
             "Admin User", None, None, "Photographer Name",
             "This is a sample headline",
             "This is the full article content.\n\nYou can scroll this.", None),
            (2, "Another Article", "Sports", "2026-02-10",
             "Admin User", None, None, "Another Photographer",
             "Second headline here", "Another article content here.", None),
        ]

    AdminPublished(
        root,
        user=fake_user,
        db_callbacks={"fetch_published": mock_fetch_published},
    )
    root.mainloop()