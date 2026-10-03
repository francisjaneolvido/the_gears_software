"""
admin/admin_revision_modal.py
─────────────────────────────
Standalone revision-edit modal for AdminNeedsRevision.

Extracted from admin_needs_revision._open_revision_modal() so it can be
imported and reused independently.

Usage
─────
    from admin.admin_revision_modal import open_revision_modal

    open_revision_modal(
        root          = self.root,
        art           = art_tuple,
        theme         = self.theme,
        callbacks     = self.callbacks,
        on_saved      = self._refresh,          # called after save_revision_edit
        on_submitted  = self._refresh,          # called after submit_revision
    )

Article tuple format (12 fields):
  0  id
  1  author_name
  2  category
  3  headline
  4  content_text
  5  media_json
  6  file_paths_csv
  7  date_str
  8  headline          (compat dup)
  9  content_text      (compat dup)
  10 author_name       (compat dup)
  11 feedback          (superadmin revision notes)

db_callbacks keys used here:
  save_revision_edit(article_id, headline, body)  → bool
  submit_revision(article_id)                     → bool
"""

import os
import json
import tkinter as tk
from tkinter import messagebox

try:
    from theme import COLORS, FONTS
except ImportError:
    COLORS = {
        "primary_orange":       "#F19421",
        "primary_orange_dark":  "#D97E10",
        "primary_orange_light": "#FFF1DF",
        "primary_red":          "#B02029",
        "background":           "#F8F6F3",
        "background_alt":       "#F0EDE8",
        "card":                 "#FFFFFF",
        "white":                "#FFFFFF",
        "text_dark":            "#1A1A1A",
        "text_mid":             "#444444",
        "text_grey":            "#717171",
        "text_light":           "#9E9E9E",
        "border":               "#E5E0D8",
        "input_bg":             "#F5F3F0",
        "success":              "#2E7D32",
        "error":                "#B02029",
        "navy":                 "#0C1633",
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


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

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


def _parse_inline_comments(notes_text: str) -> tuple:
    """
    Parse superadmin revision notes → (general_notes: str, inline_comments: list).

    inline_comments items: {"text": str, "comment": str}

    Supports the format written by superadmin_review_modal.py:
      GENERAL NOTES:
      <text>

      INLINE COMMENTS:
      1. Text: "some quoted text"
         Comment: the comment text
    """
    if not notes_text:
        return "", []

    import re
    lines           = notes_text.replace("\r", "").split("\n")
    inline_comments = []
    general_lines   = []
    current         = None
    in_general      = False
    in_inline       = False

    for raw in lines:
        t = raw.strip()
        if not t:
            continue

        if t.upper().startswith("GENERAL NOTES:"):
            in_general, in_inline = True, False
            rest = raw.split(":", 1)[1].strip() if ":" in raw else ""
            if rest:
                general_lines.append(rest)
            continue

        if t.upper().startswith("INLINE COMMENTS:"):
            in_general, in_inline = False, True
            continue

        if in_inline:
            m = re.match(r'^\d+\.\s*Text:\s*"(.*)"$', t, re.IGNORECASE)
            if m:
                if current:
                    inline_comments.append(current)
                current = {"text": m.group(1), "comment": ""}
                continue

            m = re.match(r'^Comment:\s*(.*)$', t, re.IGNORECASE)
            if m and current is not None:
                current["comment"] += (" " if current["comment"] else "") + m.group(1)
                continue

            if current and current["comment"]:
                current["comment"] += " " + t
            continue

        if in_general:
            general_lines.append(t)

    if current:
        inline_comments.append(current)

    return "\n".join(general_lines).strip(), inline_comments


def _rounded_rect_pts(x1, y1, x2, y2, r):
    r = max(1, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    return [
        x1 + r, y1,   x2 - r, y1,
        x2, y1,        x2, y1 + r,
        x2, y2 - r,   x2, y2,
        x2 - r, y2,   x1 + r, y2,
        x1, y2,        x1, y2 - r,
        x1, y1 + r,   x1, y1,
    ]


def _draw_pill_on(canvas, x1, y1, x2, y2, fill, outline=None):
    r = (y2 - y1) // 2
    pts = _rounded_rect_pts(x1, y1, x2, y2, r)
    return canvas.create_polygon(pts, smooth=True, splinesteps=36,
                                 fill=fill, outline=outline or fill)


class _PillBtn(tk.Frame):
    def __init__(
        self,
        parent,
        text,
        command,
        bg,
        fg,
        hover_bg=None,
        hover_fg=None,
        height=42,
        font=None,
        **kwargs
    ):
        super().__init__(
            parent,
            bg=bg,
            height=height,
            highlightthickness=1,
            highlightbackground=bg,
            cursor="hand2",
            **kwargs
        )

        self.pack_propagate(False)

        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg or bg
        self._hover_fg = hover_fg or fg
        self._command = command

        self.label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=fg,
            font=font or FONTS["button"],
            relief="flat",
            bd=0,
            cursor="hand2"
        )

        self.label.pack(expand=True, fill="both")

        for w in (self, self.label):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", self._on_click)

    def _on_enter(self, e):
        self.configure(bg=self._hover_bg)
        self.label.configure(
            bg=self._hover_bg,
            fg=self._hover_fg
        )

    def _on_leave(self, e):
        self.configure(bg=self._bg)
        self.label.configure(
            bg=self._bg,
            fg=self._fg
        )

    def _on_click(self, e):
        if self._command:
            self._command()

    def set_style(self, bg=None, hover_bg=None, text=None):
        if bg:
            self._bg = bg

        if hover_bg:
            self._hover_bg = hover_bg

        if text:
            self.label.configure(text=text)

        self.configure(
            bg=self._bg,
            highlightbackground=self._bg
        )

        self.label.configure(bg=self._bg)


def _sec_title(parent, text, bg, border_color):
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", padx=16, pady=(18, 6))
    tk.Label(row, text=text.upper(), bg=bg, fg="#999999",
             font=FONTS["tag"]).pack(side="left")
    tk.Frame(row, bg=border_color, height=1).pack(
        side="left", fill="x", expand=True, padx=(8, 0), pady=4)


# ─────────────────────────────────────────────────────────────────────────────
#  Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def open_revision_modal(root, art, theme=None, callbacks=None,
                        on_saved=None, on_submitted=None):
    """
    Open the revision-edit modal for a single needs-revision article.

    Parameters
    ----------
    root         : tk.Tk | tk.Toplevel
    art          : tuple  — 12-field article tuple
    theme        : dict   — COLORS dict; falls back to module COLORS
    callbacks    : dict   — {"save_revision_edit": fn, "submit_revision": fn}
    on_saved     : callable | None  — called after a successful save
    on_submitted : callable | None  — called after a successful submit
    """
    T         = theme or COLORS
    callbacks = callbacks or {}

    # ── Unpack ────────────────────────────────────────────────────────────────
    def _col(idx, fallback=""):
        try:
            return art[idx] if art[idx] is not None else fallback
        except IndexError:
            return fallback

    art_id          = _col(0)
    headline        = _col(8, _col(3, "(Untitled)"))
    category        = _col(2)
    date_str        = _col(7)
    content         = _col(9, _col(4, ""))
    feedback        = _col(11)
    media           = _parse_media(_col(6, _col(5, "")))
    general_notes, inline_comments = _parse_inline_comments(feedback)

    # ── Window ────────────────────────────────────────────────────────────────
    win = tk.Toplevel(root)
    win.title(f"Revision — {headline}")
    win.configure(bg=T["card"])
    win.grab_set()
    win.transient(root)
    win.geometry("1200x750")
    win.minsize(900, 600)
    win.attributes("-alpha", 0.0)

    def _fade(step=0, steps=10):
        try:
            win.attributes("-alpha", step / steps)
            if step < steps:
                win.after(18, lambda: _fade(step + 1, steps))
        except tk.TclError:
            pass

    win.after(30, _fade)

    # ── Header ────────────────────────────────────────────────────────────────
    tk.Frame(win, bg=T["primary_orange"], height=4).pack(fill="x")

    hdr = tk.Frame(win, bg=T["card"],
                   highlightbackground=T["border"], highlightthickness=1)
    hdr.pack(fill="x")

    hdr_inner = tk.Frame(hdr, bg=T["card"])
    hdr_inner.pack(fill="x", padx=20, pady=(10, 12))

    # Close
    close_c = tk.Canvas(hdr_inner, width=32, height=32,
                        bg=T["card"], highlightthickness=0, cursor="hand2")
    close_c.pack(side="right", padx=(8, 0))
    close_c.create_oval(1, 1, 31, 31,
                        fill=T["background_alt"], outline=T["border"])
    close_c.create_text(16, 16, text="✕",
                        fill=T["text_grey"], font=("Poppins", 11, "bold"))
    close_c.bind("<Button-1>", lambda e: win.destroy())
    close_c.bind("<Enter>",
                 lambda e: close_c.itemconfig(2, fill=T["text_dark"]))
    close_c.bind("<Leave>",
                 lambda e: close_c.itemconfig(2, fill=T["text_grey"]))

    # Status pill
    tk.Label(hdr_inner, text="🛠  NEEDS REVISION",
             bg="#FFF3CD", fg="#856404",
             font=FONTS["tag"], padx=10, pady=4
             ).pack(side="right", padx=(0, 12))

    title_block = tk.Frame(hdr_inner, bg=T["card"])
    title_block.pack(side="left", fill="x", expand=True)

    tk.Label(title_block, text=headline,
             bg=T["card"], fg=T["primary_orange"],
             font=("Poppins", 14, "bold"), anchor="w").pack(anchor="w")

    meta = [p for p in [category, date_str] if p]
    tk.Label(title_block, text="  ·  ".join(meta) if meta else "—",
             bg=T["card"], fg=T["text_grey"],
             font=FONTS["small"], anchor="w").pack(anchor="w", pady=(2, 0))

    tk.Frame(win, bg=T["border"], height=1).pack(fill="x")

    # ── Two-pane body ─────────────────────────────────────────────────────────
    RIGHT_BG = "#FFF8F0"

    paned = tk.PanedWindow(win, orient="horizontal",
                           bg=T["border"],
                           sashwidth=4, sashrelief="flat", sashpad=0)
    paned.pack(fill="both", expand=True)

    # ═════════════════════════════════════════════════════════════════════════
    # LEFT PANE — media + editable article
    # ═════════════════════════════════════════════════════════════════════════
    left_pane = tk.Frame(paned, bg=T["card"])
    paned.add(left_pane, minsize=500, stretch="always")

    art_canvas = tk.Canvas(left_pane, bg=T["card"], highlightthickness=0)
    art_vsb    = tk.Scrollbar(left_pane, orient="vertical",
                              command=art_canvas.yview)
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
            lambda ev: art_canvas.yview_scroll(
                int(-1 * (ev.delta / 120)), "units")))
    art_canvas.bind("<Leave>",
        lambda e: art_canvas.unbind_all("<MouseWheel>"))

    body_frame = tk.Frame(art_inner, bg=T["card"])
    body_frame.pack(fill="both", expand=True, padx=22, pady=18)

    # ── Media viewer ──────────────────────────────────────────────────────────
    media_state = {"files": media, "idx": 0}

    if media:
        media_wrap = tk.Frame(body_frame, bg="#111111", height=240)
        media_wrap.pack(fill="x", pady=(0, 16))
        media_wrap.pack_propagate(False)

        mc = tk.Canvas(media_wrap, bg="#1A1A1A", highlightthickness=0)
        mc.pack(fill="both", expand=True)

        def _render_media(c=mc, ms=media_state):
            c.delete("all")
            w  = c.winfo_width()  or 600
            h  = c.winfo_height() or 220
            fp = ms["files"][ms["idx"]]
            ext      = fp.rsplit(".", 1)[-1].lower() if "." in fp else ""
            filename = os.path.basename(fp)
 
            flask_url = (callbacks or {}).get("flask_url", "http://127.0.0.1:5000")
 
            # ── Resolve: local first, then Flask ──────────────────────────
            candidates = [
                fp if os.path.isabs(fp) else None,
                os.path.join("static", "uploads", "avatars", filename),
                os.path.join("static", "uploads", filename),
            ]
            local_path = next(
                (p for p in candidates if p and os.path.exists(p)), None
            )
 
            if ext in ("png", "jpg", "jpeg", "gif", "webp"):
                try:
                    import urllib.request, io
                    from PIL import Image, ImageTk
 
                    img = None
 
                    if local_path:
                        try:
                            img = Image.open(local_path)
                        except Exception as e:
                            print(f"[RevisionModal] local open error: {e}")
 
                    if img is None:
                        for url in [
                            f"{flask_url}/static/uploads/avatars/{filename}",
                            f"{flask_url}/static/uploads/{filename}",
                        ]:
                            try:
                                with urllib.request.urlopen(url, timeout=8) as resp:
                                    img = Image.open(io.BytesIO(resp.read()))
                                print(f"[RevisionModal] ✅ Fetched: {url}")
                                break
                            except Exception:
                                pass
 
                    if img:
                        img.thumbnail((w, h))
                        ph = ImageTk.PhotoImage(img)
                        c._ph = ph
                        c.create_image(w // 2, h // 2, image=ph, anchor="center")
                        if len(ms["files"]) > 1:
                            c.create_text(w - 8, h - 8,
                                          text=f"{ms['idx']+1}/{len(ms['files'])}",
                                          fill="white", font=FONTS["small"],
                                          anchor="se")
                        return
                except Exception as exc:
                    print(f"[RevisionModal] image preview error: {exc}")
 
            # Fallback — non-image or failed load
            c.create_rectangle(0, 0, w, h, fill="#2A2A2A", outline="")
            c.create_text(w // 2, h // 2 - 12, text="📄",
                          fill="#666666", font=("Poppins", 28))
            c.create_text(w // 2, h // 2 + 18, text=filename,
                          fill="#666666", font=FONTS["small"])

        if len(media) > 1:
            def _prev(ms=media_state):
                ms["idx"] = (ms["idx"] - 1 + len(ms["files"])) % len(ms["files"])
                _render_media()
            def _nxt(ms=media_state):
                ms["idx"] = (ms["idx"] + 1) % len(ms["files"])
                _render_media()
            tk.Button(media_wrap, text="‹", command=_prev,
                      bg="#111111", fg="white",
                      activebackground="#333333",
                      font=("Poppins", 18, "bold"),
                      bd=0, relief="flat", cursor="hand2", width=2
                      ).place(relx=0, rely=0.5, anchor="w", x=8)
            tk.Button(media_wrap, text="›", command=_nxt,
                      bg="#111111", fg="white",
                      activebackground="#333333",
                      font=("Poppins", 18, "bold"),
                      bd=0, relief="flat", cursor="hand2", width=2
                      ).place(relx=1, rely=0.5, anchor="e", x=-8)
    else:
        ph_frame = tk.Frame(body_frame, bg="#1A1A1A", height=80)
        ph_frame.pack(fill="x", pady=(0, 16))
        ph_frame.pack_propagate(False)
        tk.Label(ph_frame, text="No media attached",
                 bg="#1A1A1A", fg="#666666",
                 font=FONTS["small"]).pack(expand=True)

    # ── Headline field ────────────────────────────────────────────────────────
    tk.Label(body_frame, text="HEADLINE",
             bg=T["card"], fg=T["text_light"],
             font=FONTS["tag"]).pack(anchor="w", pady=(0, 4))

    headline_frame = tk.Frame(body_frame, bg="#FFE89F",
                              highlightbackground="#F3B079",
                              highlightthickness=1)
    headline_frame.pack(fill="x", pady=(0, 14))

    headline_var   = tk.StringVar(value=headline)
    headline_entry = tk.Entry(
        headline_frame,
        textvariable=headline_var,
        font=("Poppins", 12, "bold"),
        bg="#FFE89F", fg=T["text_dark"],
        relief="flat", bd=0,
        insertbackground=T["primary_orange"],
        state="disabled",
        disabledbackground="#FFE89F",
        disabledforeground=T["text_dark"],
    )
    headline_entry.pack(fill="x", padx=12, pady=10)

    # ── Article body ──────────────────────────────────────────────────────────
    tk.Label(body_frame, text="ARTICLE BODY",
             bg=T["card"], fg=T["text_light"],
             font=FONTS["tag"]).pack(anchor="w", pady=(0, 4))

    body_txt_frame = tk.Frame(body_frame, bg=T["input_bg"],
                              highlightbackground=T["border"],
                              highlightthickness=1)
    body_txt_frame.pack(fill="both", expand=True)

    body_txt = tk.Text(
        body_txt_frame, wrap="word",
        font=("Poppins", 10),
        bg=T["input_bg"], fg=T["text_dark"],
        relief="flat", bd=0, highlightthickness=0,
        padx=12, pady=12,
        cursor="xterm",
        selectbackground="#FFE69A",
        selectforeground=T["text_dark"],
        spacing1=2, spacing3=2,
        state="disabled",
    )
    body_txt.pack(fill="both", expand=True)
    body_txt.configure(state="normal")
    body_txt.insert("1.0", content or "(No content.)")

    # Highlight inline-commented phrases in yellow
    body_txt.tag_configure("highlight",
                            background="#FFE69A",
                            foreground=T["text_dark"])
    for ic in inline_comments:
        phrase = ic.get("text", "").strip()
        if phrase:
            start = "1.0"
            while True:
                pos = body_txt.search(phrase, start, stopindex="end",
                                      nocase=True)
                if not pos:
                    break
                end = f"{pos}+{len(phrase)}c"
                body_txt.tag_add("highlight", pos, end)
                start = end

    body_txt.configure(state="disabled")

    # ═════════════════════════════════════════════════════════════════════════
    # RIGHT PANE — feedback + edit controls
    # ═════════════════════════════════════════════════════════════════════════
    right_pane = tk.Frame(paned, bg=RIGHT_BG)
    paned.add(right_pane, minsize=330, stretch="never")

    # ── Pinned footer (packed FIRST) ──────────────────────────────────────────
    # ── Fixed footer ──────────────────────────────────────────────────────────
    footer = tk.Frame(
        right_pane,
        bg=T["card"],
        highlightbackground=T["border"],
        highlightthickness=1,
    )

    footer.pack(side="bottom", fill="x")

    tk.Frame(footer, bg=T["primary_orange"], height=2).pack(fill="x")

    footer_inner = tk.Frame(footer, bg=T["card"])
    footer_inner.pack(fill="x", padx=16, pady=14)
    
    tk.Label(footer_inner, text="TAKE ACTION",
             bg=T["card"], fg=T["text_light"],
             font=FONTS["tag"]).pack(anchor="w", pady=(0, 10))

    # Edit state
    edit_state = {"editing": False}

    def _toggle_edit():
        if not edit_state["editing"]:
            # Enter edit mode
            edit_state["editing"] = True
            headline_entry.configure(
                state="normal",
                bg="#FFFDE7",
                highlightbackground=T["primary_orange"],
                highlightthickness=1)
            headline_frame.configure(
                bg="#FFFDE7", highlightbackground=T["primary_orange"])
            body_txt.configure(
                state="normal",
                bg="#FFFFFF",
                highlightbackground=T["primary_orange"],
                highlightthickness=1)
            body_txt_frame.configure(
                bg="#FFFFFF", highlightbackground=T["primary_orange"])
            edit_btn.set_style(
                bg=T["success"],
                hover_bg="#1B5E20",
                text="💾  Save Changes"
            )
        else:
            # Save changes
            new_headline = headline_var.get().strip()
            new_body     = body_txt.get("1.0", "end-1c").strip()

            cb = callbacks.get("save_revision_edit")
            if cb:
                ok = cb(art_id, new_headline, new_body)
                if not ok:
                    messagebox.showerror("Error",
                        "Failed to save changes.", parent=win)
                    return
            else:
                messagebox.showinfo(
                    "Stub",
                    f"save_revision_edit callback not wired.\n"
                    f"Headline: {new_headline}", parent=win)

            edit_state["editing"] = False
            headline_entry.configure(
                state="disabled", bg="#FFE89F", highlightthickness=0)
            headline_frame.configure(
                bg="#FFE89F", highlightbackground="#F3B079")
            body_txt.configure(
                state="disabled", bg=T["input_bg"],
                highlightbackground=T["border"], highlightthickness=1)
            body_txt_frame.configure(
                bg=T["input_bg"], highlightbackground=T["border"])
            edit_btn.set_style(
    bg="#1976D2",
    hover_bg="#0D47A1",
    text="✏️  Start Editing"
)

            if on_saved:
                on_saved()
            messagebox.showinfo("Saved",
                "Changes saved. You can now submit for review.", parent=win)

    def _submit_from_modal():
        if edit_state["editing"]:
            messagebox.showwarning(
                "Unsaved Changes",
                "Please save your changes before submitting.", parent=win)
            return
        if not messagebox.askyesno(
                "Submit for Review",
                "Submit this revised article back to Superadmin for review?",
                parent=win):
            return
        cb = callbacks.get("submit_revision")
        if cb:
            ok = cb(art_id)
            if ok:
                messagebox.showinfo(
                    "Submitted",
                    "Article submitted for Superadmin review! ✔", parent=win)
                win.destroy()
                if on_submitted:
                    on_submitted()
            else:
                messagebox.showerror("Error",
                    "Failed to submit article.", parent=win)
        else:
            messagebox.showinfo("Stub",
                "submit_revision callback not wired.", parent=win)
            win.destroy()

    edit_btn = _PillBtn(
        footer_inner,
        text="✏️  Start Editing",
        command=_toggle_edit,
        bg="#1976D2", fg=T["white"],
        hover_bg="#0D47A1", hover_fg=T["white"],
        height=40, font=FONTS["button"],
    )
    edit_btn.pack(fill="x", pady=(0, 8))

    submit_btn = _PillBtn(
        footer_inner,
        text="📤  Submit for Review",
        command=_submit_from_modal,
        bg="#22C55E", fg=T["white"],
        hover_bg="#16A34A", hover_fg=T["white"],
        height=40, font=FONTS["button"],
    )
    submit_btn.pack(fill="x")

   

    # ── Scrollable right content ───────────────────────────────────────────────
    scroll_outer = tk.Frame(right_pane, bg=RIGHT_BG)
    scroll_outer.pack(side="top", fill="both", expand=True, pady=(0, 0))

    right_vsb    = tk.Scrollbar(scroll_outer, orient="vertical")
    right_vsb.pack(side="right", fill="y")

    right_canvas = tk.Canvas(scroll_outer, bg=RIGHT_BG,
                             highlightthickness=0,
                             yscrollcommand=right_vsb.set)
    right_canvas.pack(side="left", fill="both", expand=True)
    right_vsb.config(command=right_canvas.yview)

    act_body    = tk.Frame(right_canvas, bg=RIGHT_BG)
    act_body_id = right_canvas.create_window((0, 0), window=act_body, anchor="nw")

    act_body.bind("<Configure>",
        lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
    right_canvas.bind("<Configure>",
        lambda e: right_canvas.itemconfig(act_body_id, width=e.width)
                  if right_canvas.winfo_width() > 1 else None)
    right_canvas.bind("<Enter>",
        lambda e: right_canvas.bind_all("<MouseWheel>",
            lambda ev: right_canvas.yview_scroll(
                int(-1 * (ev.delta / 120)), "units")))
    right_canvas.bind("<Leave>",
        lambda e: right_canvas.unbind_all("<MouseWheel>"))

    def _force_width():
        right_canvas.update_idletasks()
        w = right_canvas.winfo_width()
        if w > 1:
            right_canvas.itemconfig(act_body_id, width=w)
        right_canvas.configure(scrollregion=right_canvas.bbox("all"))

    right_canvas.after(10, _force_width)

    # ── General feedback ──────────────────────────────────────────────────────
    _sec_title(act_body, "Superadmin Feedback", RIGHT_BG, T["border"])

    if general_notes:
        notes_card = tk.Frame(act_body, bg="#FFF3CD",
                              highlightbackground="#FFC107",
                              highlightthickness=1)
        notes_card.pack(fill="x", padx=16, pady=(0, 10))

        inner_nc = tk.Frame(notes_card, bg="#FFF3CD")
        inner_nc.pack(fill="x", padx=10, pady=8)

        tk.Label(inner_nc, text="GENERAL NOTES",
                 bg="#FFF3CD", fg="#856404",
                 font=FONTS["tag"]).pack(anchor="w")
        tk.Label(inner_nc, text=general_notes,
                 bg="#FFF3CD", fg=T["text_dark"],
                 font=FONTS["small"],
                 wraplength=270, justify="left").pack(anchor="w", pady=(4, 0))
    else:
        tk.Label(act_body, text="No general notes provided.",
                 bg=RIGHT_BG, fg=T["text_light"],
                 font=FONTS["small"]).pack(anchor="w", padx=16, pady=(0, 8))

    # ── Inline comments ───────────────────────────────────────────────────────
    if inline_comments:
        _sec_title(act_body, "Inline Comments", RIGHT_BG, T["border"])

        tk.Label(
            act_body,
            text="Phrases highlighted in yellow in the article have\n"
                 "an inline comment from Superadmin.",
            bg=RIGHT_BG, fg=T["text_grey"],
            font=FONTS["small"], justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 8))

        for ic in inline_comments:
            phrase  = ic.get("text",    "").strip()
            comment = ic.get("comment", "").strip()
            if not phrase:
                continue

            item = tk.Frame(act_body, bg=T["white"],
                            highlightbackground=T["border"],
                            highlightthickness=1)
            item.pack(fill="x", padx=16, pady=(0, 8))

            # Orange left accent
            tk.Frame(item, bg=T["primary_orange"], width=3).pack(
                side="left", fill="y")

            ic_inner = tk.Frame(item, bg=T["white"])
            ic_inner.pack(side="left", fill="both", expand=True,
                          padx=10, pady=8)

            short = phrase[:60] + ("…" if len(phrase) > 60 else "")
            tk.Label(ic_inner, text=f'❝ {short}',
                     bg=T["white"], fg=T["text_grey"],
                     font=FONTS["small"],
                     wraplength=240, justify="left").pack(anchor="w")

            tk.Frame(ic_inner, bg=T["border"], height=1).pack(
                fill="x", pady=(4, 4))

            tk.Label(ic_inner, text=f'💬  {comment}',
                     bg=T["white"], fg=T["text_dark"],
                     font=FONTS["small"],
                     wraplength=240, justify="left").pack(anchor="w")

            def _jump(p=phrase):
                pos = body_txt.search(p, "1.0", stopindex="end", nocase=True)
                if pos:
                    body_txt.see(pos)

            jump_c = tk.Canvas(ic_inner, height=26, bd=0,
                               highlightthickness=0, bg=T["white"])
            jump_c.pack(fill="x", pady=(4, 0))

            def _draw_jump(e=None, c=jump_c, p=phrase):
                c.delete("all")
                w = c.winfo_width() or 220
                _draw_pill_on(c, 0, 1, w, 25,
                              fill=T["background_alt"],
                              outline=T["border"])
                c.create_text(w // 2, 13, text="→ Jump to text",
                              fill=T["text_grey"], font=FONTS["small"])

            def _jump_hover(v, c=jump_c, p=phrase):
                c.delete("all")
                w = c.winfo_width() or 220
                fill = T["primary_orange_light"] if v else T["background_alt"]
                fg   = T["primary_orange"]       if v else T["text_grey"]
                _draw_pill_on(c, 0, 1, w, 25,
                              fill=fill, outline=T["border"])
                c.create_text(w // 2, 13, text="→ Jump to text",
                              fill=fg, font=FONTS["small"])

            jump_c.bind("<Configure>", _draw_jump)
            jump_c.bind("<Button-1>",  lambda e, p=phrase: _jump(p))
            jump_c.bind("<Enter>",     lambda e, c=jump_c: _jump_hover(True,  c))
            jump_c.bind("<Leave>",     lambda e, c=jump_c: _jump_hover(False, c))

    # ── Tip section ───────────────────────────────────────────────────────────
    _sec_title(act_body, "Tip", RIGHT_BG, T["border"])

    tip_frame = tk.Frame(act_body, bg=T["primary_orange_light"],
                         highlightbackground=T["primary_orange"],
                         highlightthickness=1)
    tip_frame.pack(fill="x", padx=16, pady=(0, 16))

    tk.Label(
        tip_frame,
        text="💡  Click 'Start Editing' to unlock the headline and article "
             "body for editing. Yellow highlights mark phrases flagged by "
             "Superadmin. Use 'Jump to text' to locate them, make your "
             "corrections, then save and submit.",
        bg=T["primary_orange_light"], fg=T["primary_orange"],
        font=FONTS["small"],
        wraplength=270, justify="left"
    ).pack(padx=10, pady=10)

    win.bind("<Escape>", lambda e: win.destroy())


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    SAMPLE = (
        1, "Maria Santos", "News",
        "Campus Paper Launches New Edition",
        "The Gears officially launched its new digital desktop edition this semester. "
        "The platform was developed by the IT department in collaboration with the "
        "editorial board of The Gears publication.",
        "",   # media_json
        "",   # file_paths_csv
        "2025-05-01 10:22",
        "Campus Paper Launches New Edition",
        "The Gears officially launched its new digital desktop edition this semester. "
        "The platform was developed by the IT department in collaboration with the "
        "editorial board of The Gears publication.",
        "Maria Santos",
        "GENERAL NOTES:\nPlease expand the introduction and clarify the timeline.\n\n"
        "INLINE COMMENTS:\n"
        '1. Text: "IT department"\n'
        "   Comment: Spell out the full department name on first use.\n"
        '2. Text: "editorial board"\n'
        "   Comment: Consider naming specific members for credibility.",
    )

    root = tk.Tk()
    root.title("Revision Modal — standalone test")
    root.geometry("1280x800")
    root.minsize(1050, 680)
    root.configure(bg="#F8F6F3")

    tk.Button(
        root,
        text="Open Revision Modal",
        command=lambda: open_revision_modal(
            root=root,
            art=SAMPLE,
            callbacks={
                "save_revision_edit": lambda aid, h, b: (
                    print(f"[stub] save({aid})\n  {h}\n  {b[:60]}") or True),
                "submit_revision":    lambda aid: (
                    print(f"[stub] submit({aid})") or True),
            },
            on_saved=lambda: print("on_saved called"),
            on_submitted=lambda: print("on_submitted called"),
        ),
        font=("Poppins", 12, "bold"),
        bg="#F19421", fg="white",
        bd=0, relief="flat", padx=24, pady=12, cursor="hand2",
    ).place(relx=0.5, rely=0.5, anchor="center")

    root.mainloop()