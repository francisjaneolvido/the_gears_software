"""
superadmin/superadmin_review_modal.py
──────────────────────────────────────────
Standalone Review Modal for The Gears Superadmin — Pending Articles.

FIXES:
  1. _render_media now falls back to Flask static URL when local path missing.
  2. _send_revision passes inline_comments list to request_revision callback,
     so highlighted_texts are saved to the DB alongside the feedback text.
  3. request_revision callback signature updated: fn(art_id, notes, inline=[])
"""

import os
import json
import tkinter as tk
from tkinter import messagebox

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
        "heading":    ("Poppins", 20, "bold"),
        "section":    ("Poppins", 16, "bold"),
        "card_title": ("Poppins", 13, "bold"),
        "body":       ("Poppins", 11),
        "body_bold":  ("Poppins", 11, "bold"),
        "small":      ("Poppins", 9),
        "small_bold": ("Poppins", 9, "bold"),
        "button":     ("Poppins", 10, "bold"),
        "tag":        ("Poppins", 8, "bold"),
        "input":      ("Poppins", 11),
        "modal_title":("Poppins", 18, "bold"),
    }

RIGHT_BG = "#FFF4E8"

PLACEHOLDER_COMMENT = "Write a comment for the selected text…"
PLACEHOLDER_NOTES   = "Write overall revision notes (optional)…"


# ── Module-level helpers ───────────────────────────────────────────────────────

def _parse_media(raw) -> list:
    """Normalise the media field into a flat list of file-path strings."""
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
            files = []
            if parsed.get("path"):
                files.append(str(parsed["path"]).strip())
            fps = parsed.get("file_paths", [])
            if isinstance(fps, list):
                files.extend(str(f).strip() for f in fps if str(f).strip())
            return files
    except Exception:
        pass

    return [f.strip() for f in s.split(",") if f.strip()]


def _clean_date(date_str) -> str:
    if not date_str:
        return ""
    if "%" in str(date_str):
        return ""
    return str(date_str)


def _pill_button(parent, text, bg, fg, command,
                 font=None, height=44, padx=16, pady=8,
                 hover_bg=None, hover_fg=None):
    hover_bg = hover_bg or bg
    hover_fg = hover_fg or fg
    _font    = font or ("Poppins", 11, "bold")

    frame = tk.Frame(parent, bg=parent["bg"])
    frame.pack(fill="x", padx=padx, pady=pady)

    btn = tk.Label(frame, text=text, bg=bg, fg=fg,
                   font=_font, cursor="hand2", height=1)
    btn.pack(fill="x", ipady=height // 3)

    btn.bind("<Button-1>", lambda e: command())
    btn.bind("<Enter>",    lambda e: btn.config(bg=hover_bg, fg=hover_fg))
    btn.bind("<Leave>",    lambda e: btn.config(bg=bg,       fg=fg))

    return btn


def _section_title(parent, text, bg):
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", padx=14, pady=(16, 4))
    tk.Label(row, text=text.upper(), bg=bg,
             fg=COLORS["text_grey"], font=FONTS["tag"]).pack(side="left")
    tk.Frame(row, bg=COLORS["border"], height=1).pack(
        side="left", fill="x", expand=True, padx=(8, 0), pady=5)


# ── Image loading helper ───────────────────────────────────────────────────────

def _load_image_from_url(url: str, max_w: int, max_h: int):
    """Load image from a full URL (Flask or Supabase) or local path."""
    try:
        from PIL import Image, ImageTk
        import urllib.request, io

        if url.startswith("http://") or url.startswith("https://"):
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data))
        else:
            # local path fallback
            filename = os.path.basename(url.replace("\\", "/"))
            candidates = [
                url,
                os.path.join("uploads", filename),
                os.path.join("static", "uploads", filename),
                os.path.join("static", "uploads", "avatars", filename),
            ]
            img = None
            for path in candidates:
                if os.path.exists(path):
                    img = Image.open(path)
                    break
            if not img:
                return None

        img.thumbnail((max_w, max_h))
        return ImageTk.PhotoImage(img)

    except Exception as e:
        print(f"[review_modal] image load failed: {e}")
        return None


# ── Main entry point ───────────────────────────────────────────────────────────

def open_review_modal(root, art, theme=None, callbacks=None, on_close=None):
    """
    Open the full-screen review modal for a single pending article.

    Parameters
    ----------
    root      : tk.Tk | tk.Toplevel
    art       : tuple  — article row from the database
    theme     : dict | None  — COLORS-style dict; falls back to module COLORS
    callbacks : dict | None  — {
                    "approve_article":  fn(art_id) -> bool,
                    "request_revision": fn(art_id, notes, inline_comments=[]) -> bool,
                    "flask_url":        str  (optional, for image fallback)
                }
    on_close  : callable | None  — called after a successful action (reload hook)

    FIXES applied:
      • _render_media falls back to Flask static URL when local path is missing.
      • _send_revision passes inline_comments list to request_revision so
        highlighted_texts are saved to the DB alongside the feedback text.
    """
    T         = theme or COLORS
    callbacks = callbacks or {}

    # Flask base URL for image fallback (e.g. "http://127.0.0.1:5000")
    flask_url = callbacks.get("flask_url", os.getenv("FLASK_URL", "http://127.0.0.1:5000"))

    # ── Unpack article fields ─────────────────────────────────────────────────
    art_id   = art[0]  if len(art) >  0 else None
    title    = art[3]  if len(art) >  3 else "(No title)"
    content  = art[4]  if len(art) >  4 else ""
    category = art[2]  if len(art) >  2 else ""
    date_str = _clean_date(art[7] if len(art) > 7 else "")
    author   = art[10] if len(art) > 10 else (art[1] if len(art) > 1 else "Unknown")
    # Use resolved media_items from index 11 if available,
# fall back to parsing raw media from index 6
    raw_media_items = art[11] if len(art) > 11 else []
    if raw_media_items:
        media = raw_media_items   # list of {"url","thumbnail","type"}
    else:
        # legacy fallback — build basic dicts from file_paths_csv
        raw_paths = _parse_media(art[6] if len(art) > 6 else None)
        media = [{"url": p, "thumbnail": p, "type": "video"
                if p.rsplit(".", 1)[-1].lower() in ("mp4","mov","avi","webm","mkv")
                else "image"} for p in raw_paths]

    # ── Modal window ──────────────────────────────────────────────────────────
    modal = tk.Toplevel(root)
    modal.transient(root)
    modal.grab_set()
    modal.geometry("1100x650+100+50")
    modal.configure(bg=T["card"],
                    highlightbackground=T["border"], highlightthickness=1)

    def _close_modal():
        try:
            modal.grab_release()
        except Exception:
            pass
        try:
            modal.destroy()
        except Exception:
            pass

    # ── Modal header ──────────────────────────────────────────────────────────
    hdr = tk.Frame(modal, bg=T["card"],
                   highlightbackground=T["border"], highlightthickness=1)
    hdr.pack(side="top", fill="x")

    hdr_inner = tk.Frame(hdr, bg=T["card"])
    hdr_inner.pack(fill="x", padx=18, pady=10)

    tk.Button(hdr_inner, text="✕", command=_close_modal,
              bg=T["card"], fg=T["primary_orange"],
              activebackground=T["primary_orange_light"],
              font=("Poppins", 18), bd=0, relief="flat",
              cursor="hand2").pack(side="right")

    title_block = tk.Frame(hdr_inner, bg=T["card"])
    title_block.pack(side="left", fill="x", expand=True)

    tk.Label(title_block, text=title or "(No title)",
             bg=T["card"], fg=T["primary_orange"],
             font=("Poppins", 16, "bold"), anchor="w").pack(anchor="w")

    meta_parts = [f"Submitted by {author}"]
    if category: meta_parts.append(category)
    if date_str: meta_parts.append(date_str)
    tk.Label(title_block, text=" · ".join(meta_parts),
             bg=T["card"], fg=T["text_grey"],
             font=FONTS["small"], anchor="w").pack(anchor="w")

    tk.Frame(modal, bg=T["border"], height=1).pack(side="top", fill="x")

    # ── Two-pane body ─────────────────────────────────────────────────────────
    paned = tk.PanedWindow(modal, orient="horizontal",
                           bg=T["background_alt"],
                           sashwidth=6, sashrelief="flat", sashpad=2)
    paned.pack(side="top", fill="both", expand=True)

    # ════════════════════════════════════════════════════════════════════════
    # LEFT PANE — article viewer
    # ════════════════════════════════════════════════════════════════════════
    art_pane = tk.Frame(paned, bg=T["card"])
    paned.add(art_pane, minsize=480, stretch="always")

    art_canvas = tk.Canvas(art_pane, bg=T["card"], highlightthickness=0)
    art_vsb    = tk.Scrollbar(art_pane, orient="vertical", command=art_canvas.yview)
    art_canvas.configure(yscrollcommand=art_vsb.set)
    art_vsb.pack(side="right", fill="y")
    art_canvas.pack(side="left", fill="both", expand=True)

    art_inner = tk.Frame(art_canvas, bg=T["card"])
    art_win   = art_canvas.create_window((0, 0), window=art_inner, anchor="nw")

    art_inner.bind("<Configure>",
        lambda e: art_canvas.configure(scrollregion=art_canvas.bbox("all")))
    art_canvas.bind("<Configure>",
        lambda e: art_canvas.itemconfig(art_win, width=e.width))
    art_canvas.bind("<Enter>",
        lambda e: art_canvas.bind_all("<MouseWheel>",
            lambda ev: art_canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
    art_canvas.bind("<Leave>",
        lambda e: art_canvas.unbind_all("<MouseWheel>"))

    art_body_frame = tk.Frame(art_inner, bg=T["card"])
    art_body_frame.pack(fill="both", expand=True, padx=20, pady=16)

    # ── Media viewer ──────────────────────────────────────────────────────────
    media_state = {"files": media, "idx": 0}

    if media:
        media_wrap = tk.Frame(art_body_frame, bg="#E8E8E8", height=260)
        media_wrap.pack(fill="x", pady=(0, 12))
        media_wrap.pack_propagate(False)

        media_cv = tk.Canvas(media_wrap, bg="#1a1a1a", highlightthickness=0)
        media_cv.pack(fill="both", expand=True)

        # Status label shown while loading
        status_lbl = tk.Label(media_wrap, text="", bg="#1a1a1a", fg="#aaaaaa",
                            font=FONTS["small"])

        def _render_media(c=media_cv, ms=media_state):
            c.delete("all")
            w = c.winfo_width() or 600
            h = c.winfo_height() or 240
            files = ms["files"]
            if not files:
                return

            item  = files[ms["idx"]]
            url   = item.get("url", "")   if isinstance(item, dict) else str(item)
            thumb = item.get("thumbnail", url) if isinstance(item, dict) else url
            itype = item.get("type", "image")  if isinstance(item, dict) else "image"
            ext   = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""

            # Remove old "Open Video" buttons
            for child in media_wrap.winfo_children():
                if isinstance(child, tk.Button):
                    child.destroy()

            def _counter():
                if len(files) > 1:
                    c.create_text(w - 8, h - 8,
                                text=f"{ms['idx']+1}/{len(files)}",
                                fill="white", font=FONTS["small"], anchor="se")

            # ── IMAGE ──────────────────────────────────────────────────────────
            if itype == "image" or ext in ("png","jpg","jpeg","gif","webp"):
                photo = _load_image_from_url(url, w, h)
                if photo:
                    c._photo = photo
                    c.create_image(w // 2, h // 2, image=photo, anchor="center")
                    _counter()
                else:
                    c.create_rectangle(0, 0, w, h, fill="#2a2a2a", outline="")
                    c.create_text(w // 2, h // 2, text="⚠ Could not load image",
                                fill="#888888", font=("Poppins", 12))
                    _counter()
                return

            # ── VIDEO ──────────────────────────────────────────────────────────
            if itype == "video" or ext in ("mp4","mov","avi","webm","mkv"):
                
                # 1. Kung may thumbnail URL na ibang-iba sa video URL, subukan muna
                thumb_photo = None
                
                # 2. Try Flask thumbnail endpoint
                if not thumb_photo and flask_url and url:
                    fname = url.split("/")[-1].split("?")[0]
                    thumb_endpoint = f"{flask_url}/api/thumbnail/{fname}"
                    if thumb_endpoint != url:  # avoid loop
                        thumb_photo = _load_image_from_url(thumb_endpoint, w, h)
                
                # 3. Try local FFmpeg generation
                if not thumb_photo:
                    thumb_photo = _generate_local_thumbnail(url, w, h)
                
                # 4. Try existing thumb URL from media dict
                if not thumb_photo and thumb and thumb != url:
                    thumb_photo = _load_image_from_url(thumb, w, h)
                
                if thumb_photo:
                    c._photo = thumb_photo
                    c.create_image(w // 2, h // 2, image=thumb_photo, anchor="center")
                    # Darkened overlay for play button
                    c.create_rectangle(w//2 - 36, h//2 - 36, w//2 + 36, h//2 + 36,
                                    fill="#000000", stipple="gray50", outline="")
                    # Play button circle
                    cx, cy = w // 2, h // 2
                    c.create_oval(cx-28, cy-28, cx+28, cy+28,
                                fill="#000000", outline="white", width=2)
                    c.create_polygon(cx-10, cy-16, cx-10, cy+16, cx+18, cy,
                                fill="white", outline="")
                else:
                    # Fallback dark placeholder
                    c.create_rectangle(0, 0, w, h, fill="#111111", outline="")
                    cx, cy = w // 2, h // 2
                    c.create_oval(cx-32, cy-32, cx+32, cy+32,
                                fill="#333333", outline="#f5821f", width=2)
                    c.create_polygon(cx-12, cy-18, cx-12, cy+18, cx+20, cy,
                                fill="#f5821f", outline="")
                    fname = url.split("/")[-1].split("?")[0][:35]
                    c.create_text(w//2, cy + 50, text=f"🎬 {fname}",
                                fill="#aaaaaa", font=FONTS["small"])
                
                # Filename bar at bottom
                fname_full = url.split("/")[-1].split("?")[0][:40]
                c.create_rectangle(0, h-26, w, h, fill="#000000", outline="")
                c.create_text(w//2, h-13, text=f"🎬 {fname_full}",
                            fill="#dddddd", font=FONTS["small"], anchor="center")
                
                # Open in browser button
                def _open_video(u=url):
                    import webbrowser
                    webbrowser.open(u)
                
                open_btn = tk.Button(
                    media_wrap, text="▶  Open Video",
                    command=_open_video,
                    bg="#f5821f", fg="white",
                    font=FONTS["small_bold"],
                    bd=0, relief="flat", cursor="hand2",
                    padx=10, pady=4,
                )
                open_btn.place(relx=0.5, rely=0.85, anchor="center")
                
                _counter()
                return

            # ── Unknown type ────────────────────────────────────────────────────
            c.create_rectangle(0, 0, w, h, fill="#2a2a2a", outline="")
            c.create_text(w//2, h//2, text=f"📎 {url.split('/')[-1][:50]}",
                        fill="#888888", font=("Poppins", 12))
            _counter()
        media_cv.bind("<Configure>", lambda e: _render_media())

        if len(media) > 1:
            def _prev(ms=media_state):
                # remove old open_video buttons if any
                for w in media_wrap.winfo_children():
                    if isinstance(w, tk.Button) and "Open Video" in (w.cget("text") or ""):
                        w.destroy()
                ms["idx"] = (ms["idx"] - 1 + len(ms["files"])) % len(ms["files"])
                _render_media()

            def _nxt(ms=media_state):
                for w in media_wrap.winfo_children():
                    if isinstance(w, tk.Button) and "Open Video" in (w.cget("text") or ""):
                        w.destroy()
                ms["idx"] = (ms["idx"] + 1) % len(ms["files"])
                _render_media()

            tk.Button(media_wrap, text="‹", command=_prev,
                    bg="#0F172A", fg="white", font=("Poppins", 18, "bold"),
                    bd=0, relief="flat", cursor="hand2", width=2
                    ).place(relx=0, rely=0.5, anchor="w", x=6)
            tk.Button(media_wrap, text="›", command=_nxt,
                    bg="#0F172A", fg="white", font=("Poppins", 18, "bold"),
                    bd=0, relief="flat", cursor="hand2", width=2
                    ).place(relx=1, rely=0.5, anchor="e", x=-6)

    if category:
        tk.Label(art_body_frame, text=f"Category: {category}",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small"]).pack(anchor="w", pady=(0, 6))

    tk.Label(art_body_frame, text="ARTICLE BODY",
             bg=T["card"], fg=T["text_grey"],
             font=FONTS["tag"]).pack(anchor="w", pady=(0, 4))

    selection_state = {"text": "", "start": None, "end": None}

    body_txt = tk.Text(
        art_body_frame, wrap="word", font=("Poppins", 11),
        bg=T["input_bg"], fg=T["text_dark"],
        relief="flat", bd=0, highlightthickness=0,
        padx=10, pady=10, cursor="xterm",
        selectbackground="#FFE69A", selectforeground=T["text_dark"],
    )
    body_txt.pack(fill="both", expand=True)
    body_txt.insert("1.0", content or "(No content.)")
    body_txt.tag_configure("highlight",
                           background="#FFE69A", foreground=T["text_dark"])
    body_txt.bind("<Key>", lambda e: "break")   # read-only

    # ════════════════════════════════════════════════════════════════════════
    # RIGHT PANE — actions / comments
    # ════════════════════════════════════════════════════════════════════════
    act_pane = tk.Frame(paned, bg=RIGHT_BG)
    paned.add(act_pane, minsize=340, stretch="always")

    btn_area = tk.Frame(act_pane, bg=RIGHT_BG,
                        highlightbackground=T["border"], highlightthickness=1)
    btn_area.pack(side="bottom", fill="x")

    btn_inner = tk.Frame(btn_area, bg=RIGHT_BG)
    btn_inner.pack(fill="x", padx=16, pady=12)

    scroll_outer = tk.Frame(act_pane, bg=RIGHT_BG)
    scroll_outer.pack(side="top", fill="both", expand=True)

    right_vsb = tk.Scrollbar(scroll_outer, orient="vertical")
    right_vsb.pack(side="right", fill="y")

    right_canvas = tk.Canvas(scroll_outer, bg=RIGHT_BG,
                             highlightthickness=0,
                             yscrollcommand=right_vsb.set)
    right_canvas.pack(side="left", fill="both", expand=True)
    right_vsb.config(command=right_canvas.yview)

    act_body    = tk.Frame(right_canvas, bg=RIGHT_BG)
    act_body_id = right_canvas.create_window((0, 0), window=act_body, anchor="nw")

    def _sync_region(e=None):
        right_canvas.configure(scrollregion=right_canvas.bbox("all"))

    def _sync_width(e=None):
        w = right_canvas.winfo_width()
        if w > 1:
            right_canvas.itemconfig(act_body_id, width=w)

    act_body.bind("<Configure>", _sync_region)
    right_canvas.bind("<Configure>", _sync_width)

    right_canvas.bind("<Enter>",
        lambda e: right_canvas.bind_all("<MouseWheel>",
            lambda ev: right_canvas.yview_scroll(int(-1 * (ev.delta / 120)), "units")))
    right_canvas.bind("<Leave>",
        lambda e: right_canvas.unbind_all("<MouseWheel>"))

    def _force_width():
        right_canvas.update_idletasks()
        w = right_canvas.winfo_width()
        if w > 1:
            right_canvas.itemconfig(act_body_id, width=w)
        right_canvas.configure(scrollregion=right_canvas.bbox("all"))

    right_canvas.after(10, _force_width)

    # ── Inline comment list ───────────────────────────────────────────────────
    inline_comments: list = []   # list of {"text": str, "note": str}

    # ── Right-pane sections ───────────────────────────────────────────────────
    _section_title(act_body, "New Comment", RIGHT_BG)

    sel_card = tk.Frame(act_body, bg=T["white"],
                        highlightbackground=T["border"], highlightthickness=1)
    sel_card.pack(fill="x", pady=(4, 0), padx=14)

    sel_lbl = tk.Label(sel_card,
                       text="Select text in the article to comment on.",
                       bg=T["white"], fg=T["text_light"],
                       font=FONTS["small"], padx=8, pady=6,
                       wraplength=260, justify="left")
    sel_lbl.pack(anchor="w")

    comment_txt = tk.Text(act_body, wrap="word", height=4,
                          font=FONTS["small"],
                          bg=T["white"], fg=T["text_light"],
                          relief="flat", bd=0,
                          highlightbackground=T["border"], highlightthickness=1,
                          padx=12, pady=12)
    comment_txt.pack(fill="x", pady=(6, 0), padx=14)
    comment_txt.insert("1.0", PLACEHOLDER_COMMENT)

    def _comment_focus_in(e):
        if comment_txt.get("1.0", "end-1c") == PLACEHOLDER_COMMENT:
            comment_txt.delete("1.0", "end")
            comment_txt.configure(fg=T["text_dark"])

    def _comment_focus_out(e):
        if not comment_txt.get("1.0", "end-1c").strip():
            comment_txt.insert("1.0", PLACEHOLDER_COMMENT)
            comment_txt.configure(fg=T["text_light"])

    comment_txt.bind("<FocusIn>",  _comment_focus_in)
    comment_txt.bind("<FocusOut>", _comment_focus_out)

    # ── Text selection handler ────────────────────────────────────────────────
    def _store_selection(e=None) -> str:
        try:
            start = body_txt.index(tk.SEL_FIRST)
            end   = body_txt.index(tk.SEL_LAST)
            sel   = body_txt.get(start, end).strip()
            if sel:
                selection_state["text"]  = sel
                selection_state["start"] = start
                selection_state["end"]   = end
                short = sel[:80] + ("…" if len(sel) > 80 else "")
                sel_lbl.configure(text=f'"{short}"', fg=T["text_dark"])
                return sel
        except tk.TclError:
            pass
        return selection_state.get("text", "")

    body_txt.bind("<ButtonRelease-1>", _store_selection)
    body_txt.bind("<B1-Motion>",       _store_selection)
    body_txt.bind("<<Selection>>",     _store_selection)
    body_txt.bind("<FocusOut>",        _store_selection)

    # Section: Comment Thread
    _section_title(act_body, "Comment Thread", RIGHT_BG)
    comment_list_frame = tk.Frame(act_body, bg=RIGHT_BG)
    comment_list_frame.pack(fill="x", padx=14, pady=(4, 0))

    def _render_comments():
        for w in comment_list_frame.winfo_children():
            w.destroy()

        tk.Button(comment_list_frame,
                  text="🔍  Jump to first highlight",
                  command=_jump_to_first_highlight,
                  bg=T["white"], fg=T["text_grey"],
                  activebackground=T["primary_orange_light"],
                  activeforeground=T["primary_orange"],
                  font=FONTS["small"], bd=1, relief="solid",
                  highlightbackground=T["border"],
                  padx=10, pady=6, cursor="hand2"
                  ).pack(fill="x", pady=(0, 6))

        if not inline_comments:
            _sync_region()
            return

        box = tk.Frame(comment_list_frame, bg=T["white"],
                       highlightbackground=T["border"], highlightthickness=1)
        box.pack(fill="x", pady=(0, 6))

        tk.Label(box, text="INLINE COMMENTS",
                 bg=T["white"], fg=T["text_grey"],
                 font=FONTS["tag"], padx=8, pady=6).pack(anchor="w")

        for c in inline_comments:
            item = tk.Frame(box, bg="#FFFBF0",
                            highlightbackground="#F0C2A0", highlightthickness=1)
            item.pack(fill="x", padx=6, pady=3)

            short_q = c["text"][:60] + ("…" if len(c["text"]) > 60 else "")
            tk.Label(item, text=f'"{short_q}"',
                     bg="#FFFBF0", fg=T["text_dark"],
                     font=FONTS["small_bold"],
                     padx=8, pady=4, wraplength=240, justify="left"
                     ).pack(anchor="w")
            tk.Label(item, text=f'💬 {c["note"]}',
                     bg="#FFFBF0", fg=T["text_grey"],
                     font=FONTS["small"],
                     padx=8, pady=4, wraplength=240, justify="left"
                     ).pack(anchor="w")

        _sync_region()

    def _jump_to_first_highlight():
        ranges = body_txt.tag_ranges("highlight")
        if ranges:
            body_txt.see(ranges[0])
        else:
            messagebox.showinfo(
                "No Highlights",
                "No inline comments yet. Select text and add a comment first.",
                parent=modal,
            )

    def _add_comment():
        current_sel = _store_selection()
        sel  = (current_sel or selection_state.get("text", "")).strip()
        note = comment_txt.get("1.0", "end-1c").strip()

        if not note or note == PLACEHOLDER_COMMENT:
            messagebox.showwarning("Empty Comment",
                "Please write a comment first.", parent=modal)
            return

        if not sel:
            messagebox.showwarning(
                "No Selection",
                "Please select some text in the article body first.\n\n"
                "Step 1: Highlight text on the left article body.\n"
                "Step 2: Type your comment.\n"
                "Step 3: Click Add Comment.",
                parent=modal,
            )
            return

        tag_name = f"highlight_{len(inline_comments) + 1}"
        body_txt.tag_configure(tag_name,
                               background="#FFE69A", foreground=T["text_dark"])

        start = selection_state.get("start")
        end   = selection_state.get("end")

        try:
            if start and end:
                body_txt.tag_add(tag_name,    start, end)
                body_txt.tag_add("highlight", start, end)
                body_txt.see(start)
            else:
                raise tk.TclError("no saved indices")
        except tk.TclError:
            idx = body_txt.search(sel, "1.0", stopindex="end")
            if idx:
                end_idx = f"{idx}+{len(sel)}c"
                body_txt.tag_add(tag_name,    idx, end_idx)
                body_txt.tag_add("highlight", idx, end_idx)
                body_txt.see(idx)

        inline_comments.append({"text": sel, "note": note})
        _render_comments()

        right_canvas.update_idletasks()
        right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        right_canvas.yview_moveto(0.35)

        comment_txt.delete("1.0", "end")
        comment_txt.insert("1.0", PLACEHOLDER_COMMENT)
        comment_txt.configure(fg=T["text_light"])

        try:
            body_txt.tag_remove(tk.SEL, "1.0", "end")
        except Exception:
            pass
        sel_lbl.configure(
            text="Select text in the article body to comment on.",
            fg=T["text_light"],
        )
        selection_state.update({"text": "", "start": None, "end": None})

    tk.Button(act_body, text="💬  Add Comment",
              command=_add_comment,
              bg="#FFC107", fg="#7A5000",
              activebackground="#E6AC00", activeforeground="#7A5000",
              font=FONTS["button"], bd=0, relief="flat",
              padx=12, pady=8, cursor="hand2"
              ).pack(fill="x", pady=(10, 0), padx=14)

    # Section: General Notes
    _section_title(act_body, "General Notes", RIGHT_BG)

    notes_txt = tk.Text(act_body, wrap="word", height=5,
                        font=FONTS["small"],
                        bg=T["white"], fg=T["text_light"],
                        relief="flat", bd=0,
                        highlightbackground=T["border"], highlightthickness=1,
                        padx=12, pady=12)
    notes_txt.pack(fill="x", pady=(6, 14), padx=14)
    notes_txt.insert("1.0", PLACEHOLDER_NOTES)

    def _notes_focus_in(e):
        if notes_txt.get("1.0", "end-1c") == PLACEHOLDER_NOTES:
            notes_txt.delete("1.0", "end")
            notes_txt.configure(fg=T["text_dark"])

    def _notes_focus_out(e):
        if not notes_txt.get("1.0", "end-1c").strip():
            notes_txt.insert("1.0", PLACEHOLDER_NOTES)
            notes_txt.configure(fg=T["text_light"])

    notes_txt.bind("<FocusIn>",  _notes_focus_in)
    notes_txt.bind("<FocusOut>", _notes_focus_out)

    # ── Revision / approve helpers ────────────────────────────────────────────
    def _build_revision_notes() -> str:
        """Build the human-readable notes string (used as the feedback/revision_notes text)."""
        general = notes_txt.get("1.0", "end-1c").strip()
        if general == PLACEHOLDER_NOTES:
            general = ""
        parts = []
        if general:
            parts.append(f"GENERAL NOTES:\n{general}")
        if inline_comments:
            lines = "INLINE COMMENTS:\n"
            for i, c in enumerate(inline_comments, 1):
                lines += f'{i}. Text: "{c["text"]}"\n   Comment: {c["note"]}\n'
            parts.append(lines.strip())
        return "\n\n".join(parts)

    def _send_revision():
        notes = _build_revision_notes()
        if not notes:
            if not messagebox.askyesno(
                "No Notes",
                "You haven't written any revision notes.\n"
                "Send revision request anyway?",
                parent=modal,
            ):
                return
        if not messagebox.askyesno(
            "Send Revision Request",
            "Send these revision notes back to the author?",
            parent=modal,
        ):
            return

        cb = callbacks.get("request_revision")
        if cb:
            # FIX: pass inline_comments so the DB saves highlighted_texts too.
            # The callback should accept (art_id, notes, inline_comments=[]).
            # admin_db_service.request_revision is updated to match.
            try:
                result = cb(art_id, notes, inline_comments)
            except TypeError:
                # Graceful fallback if old 2-arg signature is wired
                result = cb(art_id, notes)

            if result:
                messagebox.showinfo("Sent",
                    "Revision request sent successfully.", parent=modal)
                _close_modal()
                if on_close:
                    on_close()
            else:
                messagebox.showerror("Error",
                    "Failed to send revision request.", parent=modal)
        else:
            messagebox.showinfo("Sent (stub)",
                "request_revision callback not wired.", parent=modal)
            _close_modal()

    def _approve():
        if not messagebox.askyesno(
            "Approve & Publish",
            "Approve and publish this article?",
            parent=modal,
        ):
            return
        cb = callbacks.get("approve_article")
        if cb:
            if cb(art_id):
                messagebox.showinfo("Published",
                    "Article approved and published!", parent=modal)
                _close_modal()
                if on_close:
                    on_close()
            else:
                messagebox.showerror("Error",
                    "Failed to approve article.", parent=modal)
        else:
            messagebox.showinfo("Approved (stub)",
                "approve_article callback not wired.", parent=modal)
            _close_modal()

    # ── Bottom action buttons ─────────────────────────────────────────────────
    _pill_button(btn_inner,
                 text="✏️  Send Revision Request",
                 bg="#FFF3CD", fg="#856404",
                 hover_bg="#FFE69C", hover_fg="#664D03",
                 command=_send_revision,
                 font=FONTS["button"], height=44, padx=16, pady=8)

    _pill_button(btn_inner,
                 text="✔  Approve & Publish",
                 bg="#28A745", fg="white",
                 hover_bg="#3AC55B", hover_fg="white",
                 command=_approve,
                 font=FONTS["button"], height=44, padx=16, pady=8)

    _render_comments()
def _generate_local_thumbnail(video_url: str, max_w: int, max_h: int):
    """
    Generate a thumbnail locally using FFmpeg.
    Works for both local file paths and HTTP URLs.
    Returns ImageTk.PhotoImage or None.
    """
    import subprocess, tempfile, io
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return None

    ffmpeg = os.getenv("FFMPEG_PATH", "ffmpeg")
    
    # Determine source: local file or URL
    if video_url.startswith("http://") or video_url.startswith("https://"):
        # Try to find local copy first
        fname = video_url.split("/")[-1].split("?")[0]
        local_candidates = [
            os.path.join("static", "uploads", fname),
            os.path.join("uploads", fname),
            fname,
        ]
        video_source = None
        for path in local_candidates:
            if os.path.exists(path):
                video_source = path
                break
        if not video_source:
            video_source = video_url  # FFmpeg can read HTTP directly
    else:
        video_source = video_url

    # Output thumbnail to temp file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        thumb_path = tmp.name

    try:
        cmd = [
            ffmpeg, "-y",
            "-i", video_source,
            "-ss", "00:00:01",
            "-vframes", "1",
            "-vf", f"scale={max_w}:-1",
            "-q:v", "3",
            thumb_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        
        if result.returncode == 0 and os.path.exists(thumb_path):
            img = Image.open(thumb_path)
            img.thumbnail((max_w, max_h))
            return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"[_generate_local_thumbnail] FFmpeg error: {e}")
    finally:
        try:
            os.unlink(thumb_path)
        except Exception:
            pass

    return None

# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Review Modal — standalone test")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    dummy_art = (
        1, "Francis Jane Olvido", "Updates",
        "Sample Article Title for Review",
        "This is the body of the article. Select any text here and add an inline comment.\n\n"
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus volutpat "
        "libero a turpis facilisis, vel facilisis metus gravida. Integer at diam vel "
        "mi faucibus consequat.",
        "Updates", "", "2026-05-01 13:47:49",
        "Sample Article Title for Review",
        "This is the body of the article.",
        "Francis Jane Olvido",
    )

    def mock_revision(art_id, notes, inline=[]):
        print(f"request_revision({art_id})")
        print(f"  notes: {notes}")
        print(f"  inline ({len(inline)}): {inline}")
        return True

    tk.Button(
        root,
        text="Open Review Modal",
        command=lambda: open_review_modal(
            root=root,
            art=dummy_art,
            callbacks={
                "request_revision": mock_revision,
                "flask_url": "http://127.0.0.1:5000",
            },
            on_close=lambda: print("Modal closed — reload triggered"),
        ),
        font=("Poppins", 12, "bold"),
        bg="#F5821F", fg="white",
        padx=20, pady=10,
    ).place(relx=0.5, rely=0.5, anchor="center")

    root.mainloop()