"""
admin/admin_drafts.py
─────────────────────
Drafts page for The Gears Admin.

CHANGES (video support):
  • _thumb_cell() calls get_local_thumbnail() for videos so real frames
    are shown instead of a plain 🎬 emoji. Thumbnail generation runs in
    a background thread so the UI never freezes.
  • _collect() preserves the dict format returned by upload_helper so
    video thumbnail/type info is not lost when saving.
"""

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

from admin.upload_helper import (
    upload_files_to_flask,
    get_local_thumbnail,
    VIDEO_EXTENSIONS,
    IMAGE_EXTENSIONS,
)

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from admin.admin_layout import AdminLayout, FONTS


DEFAULT_CATEGORIES = [
    "NEWS", "UPDATES", "OPINION", "FEATURE",
    "KOMIKS", "LITERARY", "PHOTOS", "VIDEOS",
]

COLUMNS = [
    ("title",        "Title",        300, True),
    ("category",     "Category",     110, False),
    ("last_updated", "Last Updated", 150, False),
    ("status",       "Status",        90, False),
    ("admin",        "Admin",        160, False),
]


class AdminDrafts(AdminLayout):

    ACTIVE_NAV = "drafts"

    def __init__(self, root, user=None, db_callbacks=None):
        self.drafts = []
        super().__init__(root, user, db_callbacks)
        self._build_page()
        self._refresh_drafts()

    def _build_page(self):
        self.drafts = []
        self._build_panel()

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _fetch_drafts(self) -> list:
        cb = self.callbacks.get("fetch_drafts")
        if cb:
            try:
                return cb() or []
            except Exception as exc:
                print(f"[AdminDrafts] fetch_drafts error: {exc}")
        return []

    def _refresh_drafts(self):
        self.drafts = self._fetch_drafts()
        self._repopulate_table()

    def _load_category_names(self) -> list:
        cb = self.callbacks.get("fetch_active_categories")
        if cb:
            try:
                rows  = cb() or []
                names = []
                for row in rows:
                    name = (row.get("name", "") if isinstance(row, dict)
                            else str(row)).strip()
                    if name:
                        names.append(name)
                return names or DEFAULT_CATEGORIES
            except Exception as exc:
                print(f"[AdminDrafts] fetch_active_categories error: {exc}")
        return DEFAULT_CATEGORIES

    # ── Panel + table ─────────────────────────────────────────────────────────

    def _build_panel(self):
        T = self.theme

        hrow = tk.Frame(self.inner, bg=T["background"])
        hrow.pack(fill="x", pady=(0, 8))

        left_hdr = tk.Frame(hrow, bg=T["background"])
        left_hdr.pack(side="left")
        tk.Label(left_hdr, text="DRAFT ARTICLES",
                 bg=T["background"], fg=T["primary_orange"],
                 font=FONTS["heading"]).pack(anchor="w")
        tk.Label(left_hdr,
                 text="Articles saved as drafts or autosaved by admins.",
                 bg=T["background"], fg=T["text_grey"],
                 font=FONTS["body"]).pack(anchor="w", pady=(2, 0))

        tk.Button(hrow, text="🔄  Refresh", command=self._refresh_drafts,
                  bg=T["primary_orange"], fg=T["white"],
                  activebackground=T["primary_orange_dark"],
                  activeforeground=T["white"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=14, pady=7, cursor="hand2").pack(side="right", pady=4)

        card = tk.Frame(self.inner, bg=T["card"],
                        highlightthickness=1,
                        highlightbackground=T["border"])
        card.pack(fill="both", expand=True)
        self._table_card = card

        card_hdr = tk.Frame(card, bg=T["background_alt"])
        card_hdr.pack(fill="x")

        left_card = tk.Frame(card_hdr, bg=T["background_alt"])
        left_card.pack(side="left", padx=18, pady=10)
        tk.Label(left_card, text="Draft List",
                 font=FONTS["section"],
                 bg=T["background_alt"], fg=T["text_dark"]).pack(anchor="w")
        tk.Label(left_card,
                 text="All articles currently saved as drafts in the system.",
                 font=FONTS["small"],
                 bg=T["background_alt"], fg=T["text_grey"]).pack(anchor="w")

        self._count_var = tk.StringVar(value="0 draft(s)")
        tk.Label(card_hdr, textvariable=self._count_var,
                 font=FONTS["tag"],
                 bg=T["primary_orange_light"], fg=T["primary_orange"],
                 relief="flat", padx=10, pady=4).pack(side="right", padx=18, pady=10)

        ttk.Separator(card, orient="horizontal").pack(fill="x")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Drafts.Treeview",
                        font=FONTS["body"], rowheight=32,
                        background=T["card"], fieldbackground=T["card"],
                        foreground=T["text_dark"], borderwidth=0)
        style.configure("Drafts.Treeview.Heading",
                        font=FONTS["small_bold"],
                        background=T["background_alt"],
                        foreground=T["text_grey"], relief="flat")
        style.map("Drafts.Treeview",
                  background=[("selected", T["primary_orange_light"])],
                  foreground=[("selected", T["text_dark"])])

        cols = [c[0] for c in COLUMNS]
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 style="Drafts.Treeview", selectmode="browse")
        for cid, label, width, stretch in COLUMNS:
            self.tree.heading(cid, text=label)
            self.tree.column(cid, width=width, minwidth=60,
                             stretch=stretch, anchor="w")

        vsb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tree.tag_configure("odd",       background=T["card"])
        self.tree.tag_configure("even",      background=T.get("row_alt", "#FCFCFC"))
        self.tree.tag_configure("autosaved", background="#FFF8EE")

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.bind("<Double-1>",          self._continue_selected)

        self._actions_bar = tk.Frame(card, bg=T["background_alt"])
        self._actions_bar.pack(fill="x", padx=18, pady=8)
        self._build_actions_toolbar()

    def _repopulate_table(self):
        self.tree.delete(*self.tree.get_children())

        if hasattr(self, "_count_var"):
            self._count_var.set(f"{len(self.drafts)} draft(s)")

        if not self.drafts:
            self.tree.insert("", "end",
                             values=("No drafts yet. ✏️ Create one via Add Article.",
                                     "", "", "", ""),
                             tags=("odd",))
            return

        for i, d in enumerate(self.drafts):
            try:
                article_id   = d[0]
                author_name  = d[1]
                category     = d[2]
                last_updated = d[3] or "—"
                autosaved    = d[6]
                headline     = d[8] or "(Untitled)"
                status = "Autosaved" if autosaved == 1 else "Draft"
                tag    = "autosaved" if autosaved == 1 else (
                    "even" if i % 2 == 0 else "odd")
                self.tree.insert("", "end", iid=str(article_id),
                                 values=(headline, category, last_updated,
                                         status, author_name),
                                 tags=(tag,))
            except Exception as exc:
                print(f"[AdminDrafts] row render error: {exc}", d)

    # ── Actions toolbar ───────────────────────────────────────────────────────

    def _build_actions_toolbar(self):
        T = self.theme
        for w in self._actions_bar.winfo_children():
            w.destroy()

        self._no_sel_label = tk.Label(
            self._actions_bar,
            text="Select a row to see available actions.",
            font=FONTS["small"], bg=T["background_alt"], fg=T["text_light"])
        self._no_sel_label.pack(side="left")

        self._btn_continue = tk.Button(
            self._actions_bar, text="▶  Continue Draft",
            command=self._continue_selected,
            bg=T["primary_orange"], fg=T["white"],
            activebackground=T["primary_orange_dark"],
            activeforeground=T["white"],
            font=FONTS["button"], bd=0, relief="flat",
            padx=14, pady=6, cursor="hand2")

        self._btn_delete = tk.Button(
            self._actions_bar, text="🗑  Delete Draft",
            command=self._delete_selected,
            bg=T["card"], fg=T["primary_red"],
            activebackground="#FFF0F0",
            activeforeground=T["primary_red"],
            font=FONTS["button"], bd=1,
            highlightbackground=T["primary_red"],
            relief="solid", padx=14, pady=6, cursor="hand2")

        self._btn_continue.pack_forget()
        self._btn_delete.pack_forget()

    def _on_row_select(self, _event=None):
        sel = self.tree.selection()
        self._no_sel_label.pack_forget()
        self._btn_continue.pack_forget()
        self._btn_delete.pack_forget()
        if sel:
            self._btn_continue.pack(side="left", padx=(0, 8))
            self._btn_delete.pack(side="left")
        else:
            self._no_sel_label.pack(side="left")

    # ── Table interactions ────────────────────────────────────────────────────

    def _get_selected_draft(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select a draft first.")
            return None, None
        iid = sel[0]
        for d in self.drafts:
            if str(d[0]) == iid:
                return iid, d
        return iid, None

    def _continue_selected(self, _event=None):
        iid, draft = self._get_selected_draft()
        if draft is not None:
            self._open_modal(iid, draft)

    def _delete_selected(self):
        iid, draft = self._get_selected_draft()
        if draft is None:
            return
        title = draft[8] if len(draft) > 8 and draft[8] else draft[1] or "(Untitled)"
        if not messagebox.askyesno(
            "Delete Draft",
            f'Are you sure you want to delete:\n\n"{title}"?\n\nThis cannot be undone.',
            icon="warning"):
            return
        cb = self.callbacks.get("delete_draft")
        if cb:
            try:
                ok = cb(draft[0])
            except Exception as exc:
                messagebox.showerror("Error", f"Could not delete draft:\n{exc}")
                return
            if ok:
                self.drafts = [d for d in self.drafts if d[0] != draft[0]]
                self._repopulate_table()
                messagebox.showinfo("Deleted", f'"{title}" has been deleted.')
            else:
                messagebox.showerror("Error",
                    "Could not delete draft. It may have already been deleted.")
        else:
            messagebox.showerror("Config Error",
                "delete_draft callback is not wired up.")

    # ── Media helper ──────────────────────────────────────────────────────────

    def _extract_media_paths(self, draft) -> list:
        """
        Returns a list of file path strings (url field only) for display.
        Handles both old string format and new dict format.
        """
        possible = []
        if len(draft) > 10:
            possible.append(draft[10])
        if len(draft) > 5:
            possible.append(draft[5])
        if len(draft) > 6 and isinstance(draft[6], str):
            possible.append(draft[6])

        paths = []
        for media in possible:
            if not media:
                continue
            try:
                if isinstance(media, list):
                    for item in media:
                        if isinstance(item, dict):
                            paths.append(item.get("url", ""))
                        elif isinstance(item, str):
                            paths.extend(str(p).strip() for p in [item] if str(p).strip())
                    continue
                if isinstance(media, dict):
                    # New format: {"author":..., "file_paths":[...], "media":[...]}
                    full = media.get("media", [])
                    if full:
                        for item in full:
                            if isinstance(item, dict):
                                paths.append(item.get("url", ""))
                            elif isinstance(item, str):
                                paths.append(item)
                    else:
                        paths.extend(media.get("file_paths", []) or
                                     media.get("paths", []))
                    continue
                if isinstance(media, str):
                    s = media.strip()
                    if not s:
                        continue
                    try:
                        parsed = json.loads(s)
                        if isinstance(parsed, dict):
                            full = parsed.get("media", [])
                            if full:
                                for item in full:
                                    if isinstance(item, dict):
                                        paths.append(item.get("url", ""))
                                    elif isinstance(item, str):
                                        paths.append(item)
                            else:
                                paths.extend(parsed.get("file_paths", []) or
                                             parsed.get("paths", []))
                        elif isinstance(parsed, list):
                            for item in parsed:
                                if isinstance(item, dict):
                                    paths.append(item.get("url", ""))
                                elif isinstance(item, str):
                                    paths.append(item.strip())
                        continue
                    except Exception:
                        pass
                    if "," in s:
                        paths.extend(p.strip() for p in s.split(",") if p.strip())
                    else:
                        paths.append(s)
            except Exception as exc:
                print(f"[AdminDrafts] media parse error: {exc}")

        clean = []
        for p in paths:
            if p and p not in clean:
                clean.append(p)
        return clean

    def _get_thumbnail_url(self, draft, url: str) -> str:
        """
        Given a file url from the draft's media list, find its thumbnail.
        Falls back to url itself if not found.
        """
        possible = []
        if len(draft) > 10:
            possible.append(draft[10])

        for media in possible:
            if not media:
                continue
            try:
                parsed = media if isinstance(media, (dict, list)) \
                         else json.loads(media)
                if isinstance(parsed, dict):
                    items = parsed.get("media", [])
                elif isinstance(parsed, list):
                    items = parsed
                else:
                    items = []
                for item in items:
                    if isinstance(item, dict) and item.get("url") == url:
                        return item.get("thumbnail", url)
            except Exception:
                pass
        return url

    # ── Thumbnail cell ────────────────────────────────────────────────────────

    def _thumb_cell(self, parent, path, on_remove, draft=None,
                    thumb_refs: list = None):
        """
        Build a single media thumbnail cell.

        Images  → load directly with PIL (unchanged).
        Videos  → load thumbnail URL from media dict if available,
                  otherwise generate via get_local_thumbnail() in a thread.
        """
        T = self.theme
        cell = tk.Frame(parent, bg=T["background_alt"],
                        highlightbackground=T["border"], highlightthickness=1)
        cell.pack(side="left", padx=(0, 8), pady=4)

        ext      = os.path.splitext(path)[1].lower()
        is_video = ext in VIDEO_EXTENSIONS
        is_image = ext in IMAGE_EXTENSIONS

        flask_url = self.callbacks.get("flask_url", "http://127.0.0.1:5000")

        img_label = tk.Label(cell, bg=T["background_alt"])
        img_label.pack()

        def _try_load_url(load_path):
            """Load image from local path or http URL. Returns PIL Image or None."""
            try:
                if load_path.startswith("http"):
                    import urllib.request, io as _io
                    with urllib.request.urlopen(load_path, timeout=8) as resp:
                        return Image.open(_io.BytesIO(resp.read()))
                elif os.path.exists(load_path):
                    return Image.open(load_path)
            except Exception as e:
                print(f"[AdminDrafts] thumb load error: {e}")
            return None

        def _apply_image(img):
            """Resize and apply PIL image to img_label (call from main thread)."""
            try:
                img.thumbnail((100, 78), Image.LANCZOS)
                ph = ImageTk.PhotoImage(img)
                if thumb_refs is not None:
                    thumb_refs.append(ph)
                img_label.config(image=ph, width=100, height=78)
            except Exception as e:
                print(f"[AdminDrafts] apply image error: {e}")

        if is_image and PIL_AVAILABLE:
            # ── Image: try local then Flask URL ───────────────────────────────
            local_path = path if os.path.exists(path) else None
            flask_path = f"{flask_url}/static/uploads/{os.path.basename(path)}"

            img = None
            if local_path:
                img = _try_load_url(local_path)
            if img is None:
                img = _try_load_url(flask_path)

            if img:
                _apply_image(img)
            else:
                img_label.config(text="🖼", font=("Poppins", 26),
                                 fg=T["text_grey"], width=7, height=3)

        elif is_video and PIL_AVAILABLE:
            # ── Video: show spinner, load thumbnail in background ─────────────
            img_label.config(text="⏳", font=("Poppins", 26),
                             fg=T["text_grey"], width=7, height=3)

            # First try: thumbnail URL from media dict
            thumb_url = self._get_thumbnail_url(draft, path) if draft else path

            def _gen_video_thumb(path=path, thumb_url=thumb_url):
                img = None

                # Try thumbnail URL first (server-side thumb already generated)
                if thumb_url and thumb_url != path:
                    if not thumb_url.startswith("http"):
                        # bare filename — build full URL
                        full_thumb = f"{flask_url}/static/uploads/{thumb_url}"
                    else:
                        full_thumb = thumb_url
                    img = _try_load_url(full_thumb)

                # Fall back: generate locally via FFmpeg
                if img is None and os.path.exists(path):
                    local_thumb = get_local_thumbnail(path)
                    if local_thumb:
                        img = _try_load_url(local_thumb)

                if img:
                    self.root.after(0, lambda i=img: _apply_image(i))
                else:
                    self.root.after(0, lambda: img_label.config(
                        text="🎬", font=("Poppins", 26),
                        fg=T["text_grey"], width=7, height=3))

            threading.Thread(target=_gen_video_thumb, daemon=True).start()

        else:
            icon = "🎬" if is_video else "🖼"
            img_label.config(text=icon, font=("Poppins", 26),
                             fg=T["text_grey"], width=7, height=3)

        tk.Label(cell, text=os.path.basename(path),
                 bg=T["background_alt"], fg=T["text_grey"],
                 font=FONTS["small"], wraplength=100,
                 justify="center").pack(padx=4, pady=(2, 2))
        tk.Button(cell, text="Remove", command=on_remove,
                  bg=T["primary_red"], fg="white",
                  activebackground="#8F1A20", activeforeground="white",
                  font=("Poppins", 8, "bold"),
                  bd=0, relief="flat", padx=6, pady=3,
                  cursor="hand2").pack(fill="x")
        return cell

    # ── Continue Draft Modal ──────────────────────────────────────────────────

    def _open_modal(self, iid, draft):
        def col(idx, fallback=""):
            try:
                return draft[idx] if draft[idx] is not None else fallback
            except IndexError:
                return fallback

        T = self.theme

        modal = tk.Toplevel(self.root)
        modal.title("Continue Draft")
        modal.geometry("680x640")
        modal.minsize(560, 560)
        modal.configure(bg=T["background"])
        modal.grab_set()
        modal.transient(self.root)

        tk.Frame(modal, bg=T["primary_orange"], height=6).pack(fill="x")
        title_bar = tk.Frame(modal, bg=T["card"],
                             highlightbackground=T["border"], highlightthickness=1)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="Continue Draft",
                 bg=T["card"], fg=T["primary_orange"],
                 font=FONTS["modal_title"], padx=22, pady=14).pack(side="left")
        tk.Button(title_bar, text="✕", command=modal.destroy,
                  bg=T["card"], fg=T["text_grey"],
                  activebackground=T["border"],
                  activeforeground=T["primary_red"],
                  font=("Poppins", 14, "bold"),
                  bd=0, relief="flat", padx=18, pady=12,
                  cursor="hand2").pack(side="right")

        body_outer = tk.Frame(modal, bg=T["background"])
        body_outer.pack(fill="both", expand=True)
        m_canvas = tk.Canvas(body_outer, bg=T["background"], highlightthickness=0)
        m_canvas.pack(side="left", fill="both", expand=True)
        m_sb = tk.Scrollbar(body_outer, orient="vertical", command=m_canvas.yview)
        m_sb.pack(side="right", fill="y")
        m_canvas.configure(yscrollcommand=m_sb.set)
        body = tk.Frame(m_canvas, bg=T["background"])
        bwin = m_canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>",
            lambda e: m_canvas.configure(scrollregion=m_canvas.bbox("all")))
        m_canvas.bind("<Configure>",
            lambda e: m_canvas.itemconfig(bwin, width=e.width))
        m_canvas.bind("<Enter>",
            lambda e: m_canvas.bind_all(
                "<MouseWheel>",
                lambda ev: m_canvas.yview_scroll(
                    int(-1 * (ev.delta / 120)), "units")))
        m_canvas.bind("<Leave>", lambda e: m_canvas.unbind_all("<MouseWheel>"))

        form = tk.Frame(body, bg=T["card"],
                        highlightbackground=T["border"], highlightthickness=1)
        form.pack(fill="both", expand=True, padx=20, pady=16)
        inner = tk.Frame(form, bg=T["card"])
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        def lbl(text):
            tk.Label(inner, text=text, bg=T["card"], fg=T["text_dark"],
                     font=FONTS["body_bold"], anchor="w").pack(
                     fill="x", pady=(0, 4))

        def entry(var):
            e = tk.Entry(inner, textvariable=var, font=FONTS["input"],
                         bg=T["input_bg"], fg=T["text_dark"],
                         insertbackground=T["primary_orange"],
                         relief="flat",
                         highlightbackground=T["border"],
                         highlightthickness=1)
            e.pack(fill="x", pady=(0, 10), ipady=7)
            return e

        lbl("Author")
        author_var = tk.StringVar(value=col(1))
        entry(author_var)

        lbl("Photographer")
        photo_var = tk.StringVar(value=col(7))
        entry(photo_var)

        lbl("Headline")
        headline_var = tk.StringVar(value=col(8))
        entry(headline_var)

        lbl("Content")
        content_box = tk.Text(inner, height=6, wrap="word", font=FONTS["input"],
                              bg=T["input_bg"], fg=T["text_dark"],
                              insertbackground=T["primary_orange"],
                              relief="flat",
                              highlightbackground=T["border"],
                              highlightthickness=1,
                              padx=10, pady=8)
        content_box.pack(fill="x", pady=(0, 10))
        content_box.insert("1.0", col(9))

        lbl("Category")
        category_values  = self._load_category_names()
        current_category = col(2)
        cat_var = tk.StringVar(
            value=current_category if current_category in category_values else "")
        ttk.Combobox(inner, textvariable=cat_var,
                     values=category_values,
                     state="readonly",
                     font=FONTS["input"]).pack(fill="x", pady=(0, 10))

        # ── Media ─────────────────────────────────────────────────────────────
        tk.Frame(inner, bg=T["border"], height=1).pack(fill="x", pady=(4, 10))
        tk.Label(inner,
                 text="Note: Existing files are kept. Newly uploaded files will be added.",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small"], wraplength=480, justify="left").pack(
                 fill="x", pady=(0, 8))

        # existing_files stores url strings for display
        existing_files     = self._extract_media_paths(draft)
        existing_thumb_refs = []

        lbl("Existing Media")
        existing_media_frame = tk.Frame(inner, bg=T["card"])
        existing_media_frame.pack(fill="x", pady=(0, 10))

        def render_existing_media():
            for w in existing_media_frame.winfo_children():
                w.destroy()
            existing_thumb_refs.clear()
            if not existing_files:
                tk.Label(existing_media_frame,
                         text="No existing media found in the draft data.",
                         bg=T["card"], fg=T["text_grey"],
                         font=FONTS["small"], anchor="w").pack(fill="x")
                return
            for i, path in enumerate(existing_files):
                def _remove(idx=i):
                    if 0 <= idx < len(existing_files):
                        existing_files.pop(idx)
                    render_existing_media()
                # pass draft so _thumb_cell can look up the thumbnail URL
                self._thumb_cell(existing_media_frame, path, _remove,
                                 draft=draft,
                                 thumb_refs=existing_thumb_refs)

        render_existing_media()

        lbl("Upload Additional Files (Images or Videos)")
        extra_files      = []
        extra_thumb_refs = []

        extra_media_frame = tk.Frame(inner, bg=T["card"])
        extra_media_frame.pack(fill="x", pady=(4, 12))

        def render_extra_media():
            for w in extra_media_frame.winfo_children():
                w.destroy()
            extra_thumb_refs.clear()
            if not extra_files:
                tk.Label(extra_media_frame,
                         text="No additional files selected.",
                         bg=T["card"], fg=T["text_grey"],
                         font=FONTS["small"], anchor="w").pack(fill="x")
                return
            for i, path in enumerate(extra_files):
                def _remove(idx=i):
                    if 0 <= idx < len(extra_files):
                        extra_files.pop(idx)
                    render_extra_media()
                self._thumb_cell(extra_media_frame, path, _remove,
                                 thumb_refs=extra_thumb_refs)

        def choose_extra():
            paths = filedialog.askopenfilenames(
                parent=modal,
                title="Select Additional Files",
                filetypes=[("Media files",
                            "*.png *.jpg *.jpeg *.gif *.bmp *.webp "
                            "*.mp4 *.mov *.avi *.mkv"),
                           ("All files", "*.*")])
            for p in paths:
                if p not in extra_files and p not in existing_files:
                    extra_files.append(p)
            render_extra_media()

        tk.Button(inner, text="📎  Choose Files", command=choose_extra,
                  bg=T["primary_orange_light"], fg=T["primary_orange"],
                  activebackground=T["primary_orange"],
                  activeforeground=T["white"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(anchor="w")

        render_extra_media()

        # ── Action buttons ────────────────────────────────────────────────────
        tk.Frame(inner, bg=T["border"], height=1).pack(fill="x", pady=(4, 12))
        btn_row = tk.Frame(inner, bg=T["card"])
        btn_row.pack(fill="x")

        def _collect():
            flask_url = self.callbacks.get("flask_url", "http://127.0.0.1:5000")
            api_token = self.callbacks.get("api_token", "")

            # existing_files: url strings already on server — wrap as image
            # dicts so save_draft() stores them with proper format
            existing_as_dicts = []
            for url in existing_files:
                ext = os.path.splitext(url)[1].lower()
                thumb = self._get_thumbnail_url(draft, url)
                existing_as_dicts.append({
                    "url":       url,
                    "thumbnail": thumb,
                    "type":      "video" if ext in VIDEO_EXTENSIONS else "image",
                })

            # extra_files: local paths — upload now, returns dicts
            uploaded_extra = upload_files_to_flask(
                extra_files, flask_url, api_token)

            cat = cat_var.get()
            return {
                "draft_id":     draft[0],
                "author":       author_var.get().strip(),
                "photographer": photo_var.get().strip(),
                "headline":     headline_var.get().strip(),
                "content_text": content_box.get("1.0", "end-1c").strip(),
                "category":     cat if cat in category_values else "Uncategorized",
                "file_paths":   existing_as_dicts + uploaded_extra,
                "author_id":    self.user[3] if self.user and len(self.user) > 3
                                else None,
            }

        def save_draft_action():
            data = _collect()
            cb   = self.callbacks.get("save_draft")
            try:
                if cb:
                    cb(data)
                messagebox.showinfo("Saved", "Draft saved successfully.",
                                    parent=modal)
                modal.destroy()
                self._refresh_drafts()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not save draft:\n{exc}",
                                     parent=modal)

        def submit_action():
            data   = _collect()
            errors = []
            if not data["author"]:       errors.append("• Author is required.")
            if not data["headline"]:     errors.append("• Headline is required.")
            if not data["content_text"]: errors.append("• Content cannot be empty.")
            if errors:
                messagebox.showwarning("Validation", "\n".join(errors),
                                       parent=modal)
                return
            if not messagebox.askyesno(
                "Submit for Review",
                "Submit this draft for review?\n\nThe admin team will be notified.",
                parent=modal):
                return
            cb = self.callbacks.get("submit_for_review")
            try:
                if cb:
                    cb(data)
                messagebox.showinfo("Submitted",
                                    "Draft submitted for review! ✔",
                                    parent=modal)
                modal.destroy()
                self._refresh_drafts()
            except Exception as exc:
                messagebox.showerror("Error", f"Submission failed:\n{exc}",
                                     parent=modal)

        tk.Button(btn_row, text="Save Draft", command=save_draft_action,
                  bg=T["card"], fg=T["primary_orange"],
                  activebackground=T["primary_orange_light"],
                  activeforeground=T["primary_orange"],
                  font=FONTS["button"], bd=1,
                  highlightbackground=T["primary_orange"],
                  relief="solid", padx=18, pady=9,
                  cursor="hand2").pack(side="left", padx=(0, 10))

        tk.Button(btn_row, text="Submit for Review", command=submit_action,
                  bg=T["primary_orange"], fg=T["white"],
                  activebackground=T["primary_orange_dark"],
                  activeforeground=T["white"],
                  font=FONTS["button"], bd=0, relief="flat",
                  padx=18, pady=9, cursor="hand2").pack(side="left")


# =============================================================================
# Standalone demo
# =============================================================================

if __name__ == "__main__":
    import tkinter as tk

    SAMPLE_DRAFTS = [
        (1, "Maria Santos",   "News",    "2025-05-01 10:22", "maria@gears.com",
         None, 0, "Juan Cruz",  "Breaking: Gears Wins Award",  "Full article content here…"),
        (2, "Juan Dela Cruz", "Opinion", "2025-04-30 14:08", "juan@gears.com",
         None, 1, "",           "Opinion: The Road Ahead",     "We must consider the facts…"),
        (3, "Ana Reyes",      "Feature", "2025-04-28 09:15", "ana@gears.com",
         None, 0, "Luis Tan",  "(Untitled)",                   ""),
    ]

    root = tk.Tk()
    root.title("The Gears — Drafts")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    AdminDrafts(
        root,
        user=("Maria", "Santos", "maria@gears.com", 1, "admin"),
        db_callbacks={
            "fetch_drafts": lambda: SAMPLE_DRAFTS,
        },
    )
    root.mainloop()