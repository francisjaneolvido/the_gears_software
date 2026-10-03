"""
admin/admin_create_article.py
──────────────────────────────
Publish New Article — web-inspired UI matching publish.html.

CHANGES (video support):
  • _render_files() now calls get_local_thumbnail() from upload_helper
    so videos show a real extracted frame instead of a plain 🎬 emoji.
  • Thumbnail generation runs in a background thread so the UI never freezes
    on large video files.
  • Everything else is unchanged.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
from admin.upload_helper import upload_files_to_flask, get_local_thumbnail, VIDEO_EXTENSIONS

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from admin.admin_layout import AdminLayout, FONTS

DEFAULT_CATEGORIES = [
    "NEWS", "UPDATES", "OPINION", "FEATURE",
    "KOMIKS", "LITERARY", "ARTS", "PHOTOS", "VIDEOS",
]

AUTOSAVE_DELAY_MS = 3000

LIGHT = {
    "bg":           "#fff6f4",
    "card":         "#ffffff",
    "border":       "#f0c2a0",
    "accent":       "#f5821f",
    "accent_soft":  "#ffe1cc",
    "text_dark":    "#333333",
    "text_grey":    "#777777",
    "white":        "#ffffff",
    "input_bg":     "#fff6f4",
    "success":      "#22c55e",
    "error":        "#ef4444",
}

DARK = {
    "bg":           "#151515",
    "card":         "#1f1f1f",
    "border":       "#3c2c1f",
    "accent":       "#f5821f",
    "accent_soft":  "#3a2a1f",
    "text_dark":    "#f5f5f5",
    "text_grey":    "#b0b0b0",
    "white":        "#ffffff",
    "input_bg":     "#2a2a2a",
    "success":      "#4ade80",
    "error":        "#f87171",
}


class AdminPublish(AdminLayout):

    ACTIVE_NAV = "add_article"

    def __init__(self, root, user=None, db_callbacks=None):
        self.draft_id       = None
        self.selected_files = []   # list of local paths OR server filenames
        self._thumb_refs    = []   # keep PhotoImage refs alive
        self._autosave_job  = None
        self._autosave_lock = threading.Lock()
        self._submitted     = False

        super().__init__(root, user, db_callbacks)

        self._focus_bind = self.root.bind("<FocusOut>", self._on_focus_out)
        self._build_page()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _unbind_all(self):
        super()._unbind_all()
        try:
            if hasattr(self, "_focus_bind") and self._focus_bind:
                self.root.unbind("<FocusOut>", self._focus_bind)
        except Exception:
            pass
        self._focus_bind = None

    @property
    def T(self):
        return DARK if self.dark_mode else LIGHT

    def _build_page(self):
        self._build_publish_form()

    # ── Dark-mode toggle ──────────────────────────────────────────────────────

    def toggle_dark_mode(self):
        try:
            data  = self._collect_form_data()
            files = list(self.selected_files)
            has_data = True
        except Exception:
            has_data = False

        self.dark_mode = not self.dark_mode
        self.theme     = self.dark if self.dark_mode else self.light
        self._rebuild_chrome()

        if has_data:
            self.author_var.set(data["author"])
            self.photographer_var.set(data["photographer"])
            self.headline_var.set(data["headline"])
            self.content_text.insert("1.0", data["content_text"])
            if data["category"]:
                self.category_var.set(data["category"])
                self.category_combo.set(data["category"])
            self.selected_files = files
            self._render_files()

    # ── Category loader ───────────────────────────────────────────────────────

    def _load_category_names(self):
        cb = self.callbacks.get("fetch_active_categories")
        if cb:
            try:
                rows  = cb() or []
                names = [
                    (row.get("name", "") if isinstance(row, dict) else str(row)).strip()
                    for row in rows
                ]
                names = [n for n in names if n]
                return names or DEFAULT_CATEGORIES
            except Exception as exc:
                print(f"[AdminPublish] fetch_active_categories error: {exc}")
        return DEFAULT_CATEGORIES

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _card(self, parent, title, subtitle, icon="✏"):
        T = self.T
        wrap = tk.Frame(parent, bg=T["card"],
                        highlightbackground=T["border"], highlightthickness=1)
        wrap.pack(fill="x", pady=(0, 16))
        tk.Frame(wrap, bg=T["accent"], height=4).pack(fill="x")
        hdr = tk.Frame(wrap, bg=T["card"])
        hdr.pack(fill="x", padx=20, pady=(14, 10))
        icon_box = tk.Frame(hdr, bg=T["accent_soft"], width=34, height=34)
        icon_box.pack_propagate(False)
        icon_box.pack(side="left")
        tk.Label(icon_box, text=icon, bg=T["accent_soft"],
                 fg=T["accent"], font=("Poppins", 14)).pack(expand=True)
        txt_col = tk.Frame(hdr, bg=T["card"])
        txt_col.pack(side="left", padx=(10, 0))
        tk.Label(txt_col, text=title.upper(),
                 bg=T["card"], fg=T["accent"],
                 font=("Poppins", 11, "bold")).pack(anchor="w")
        tk.Label(txt_col, text=subtitle,
                 bg=T["card"], fg=T["text_grey"],
                 font=("Poppins", 9)).pack(anchor="w")
        tk.Frame(wrap, bg=T["border"], height=1).pack(fill="x")
        body = tk.Frame(wrap, bg=T["card"])
        body.pack(fill="x", padx=20, pady=(16, 20))
        return body

    def _label(self, parent, text, required=False):
        T = self.T
        row = tk.Frame(parent, bg=T["card"])
        row.pack(fill="x", pady=(0, 4))
        tk.Label(row, text=text.upper(), bg=T["card"], fg=T["accent"],
                 font=("Poppins", 8, "bold")).pack(side="left")
        if required:
            tk.Label(row, text=" *", bg=T["card"],
                     fg=T["error"], font=("Poppins", 11, "bold")).pack(side="left")

    def _entry(self, parent, var, placeholder="", width=None):
        T = self.T
        kw = dict(textvariable=var, font=("Poppins", 11),
                  bg=T["input_bg"], fg=T["text_dark"],
                  insertbackground=T["accent"], relief="flat",
                  highlightbackground=T["border"], highlightthickness=1)
        if width:
            kw["width"] = width
        e = tk.Entry(parent, **kw)
        e.pack(fill="x", pady=(0, 14), ipady=8)
        if placeholder:
            def _on_focus_in(ev, e=e, ph=placeholder, fg=T["text_dark"], grey=T["text_grey"]):
                if e.get() == ph:
                    e.delete(0, "end")
                    e.config(fg=fg)
            def _on_focus_out(ev, e=e, ph=placeholder, grey=T["text_grey"]):
                if not e.get():
                    e.insert(0, ph)
                    e.config(fg=grey)
            e.insert(0, placeholder)
            e.config(fg=T["text_grey"])
            e.bind("<FocusIn>",  _on_focus_in)
            e.bind("<FocusOut>", _on_focus_out)
        return e

    def _two_col(self, parent):
        T = self.T
        row = tk.Frame(parent, bg=T["card"])
        row.pack(fill="x")
        left  = tk.Frame(row, bg=T["card"])
        right = tk.Frame(row, bg=T["card"])
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        right.pack(side="left", fill="x", expand=True)
        return left, right

    # ── Progress ──────────────────────────────────────────────────────────────

    def _build_progress(self, parent):
        T = self.T
        wrap = tk.Frame(parent, bg=T["card"],
                        highlightbackground=T["border"], highlightthickness=1)
        wrap.pack(fill="x", pady=(0, 16))
        inner = tk.Frame(wrap, bg=T["card"])
        inner.pack(fill="x", padx=20, pady=12)
        self._step_labels = []
        steps = ["Article Info", "Content", "Media", "Submit"]
        for i, name in enumerate(steps):
            circle = tk.Label(inner, text=str(i+1), width=2,
                              bg=T["accent"] if i == 0 else T["input_bg"],
                              fg=T["white"] if i == 0 else T["text_grey"],
                              font=("Poppins", 9, "bold"), relief="flat")
            circle.pack(side="left")
            lbl = tk.Label(inner, text=f" {name}", bg=T["card"],
                           fg=T["accent"] if i == 0 else T["text_grey"],
                           font=("Poppins", 9, "bold" if i == 0 else "normal"))
            lbl.pack(side="left")
            self._step_labels.append((circle, lbl))
            if i < len(steps) - 1:
                tk.Frame(inner, bg=T["border"], height=2,
                         width=30).pack(side="left", padx=8)

    def _update_progress(self):
        T = self.T
        try:
            author   = self.author_var.get().strip()
            cat      = self.category_var.get()
            headline = self.headline_var.get().strip()
            body     = self.content_text.get("1.0", "end-1c").strip()
            files    = bool(self.selected_files)
        except Exception:
            return
        step1_done = bool(author and cat and cat not in ("Select Category", ""))
        step2_done = step1_done and bool(headline and body)
        step3_done = step2_done
        states = [
            "done"   if step1_done else "active",
            "done"   if step2_done else ("active" if step1_done else "idle"),
            "done"   if (step3_done and files) else ("active" if step3_done else "idle"),
            "active" if step2_done else "idle",
        ]
        if not hasattr(self, "_step_labels"):
            return
        for i, (circle, lbl) in enumerate(self._step_labels):
            st = states[i]
            if st == "done":
                circle.config(bg=T["success"], fg=T["white"], text="✓")
                lbl.config(fg=T["success"], font=("Poppins", 9, "bold"))
            elif st == "active":
                circle.config(bg=T["accent"], fg=T["white"], text=str(i+1))
                lbl.config(fg=T["accent"], font=("Poppins", 9, "bold"))
            else:
                circle.config(bg=T["input_bg"], fg=T["text_grey"], text=str(i+1))
                lbl.config(fg=T["text_grey"], font=("Poppins", 9, "normal"))

    # ── Publish form ──────────────────────────────────────────────────────────

    def _build_publish_form(self):
        T = self.T

        hdr = tk.Frame(self.inner, bg=T["bg"])
        hdr.pack(fill="x", pady=(0, 14))
        tk.Label(hdr, text="Add Article", bg=T["bg"], fg=T["accent"],
                 font=("Poppins", 18, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Create and publish a new article, or save it as a draft.",
                 bg=T["bg"], fg=T["text_grey"],
                 font=("Poppins", 10)).pack(anchor="w")

        self._build_progress(self.inner)

        # ── CARD 1: Article Info ──────────────────────────────────────────────
        c1 = self._card(self.inner, "Article Info",
                        "Basic details about the article", "📄")
        left, right = self._two_col(c1)

        self._label(left, "Author", required=True)
        self.author_var = tk.StringVar()
        self._entry(left, self.author_var, "Author name")
        self.author_var.trace_add("write", self._on_var_change)

        self._label(right, "Category", required=True)
        self.category_var = tk.StringVar(value="")
        self.category_combo = ttk.Combobox(
            right, textvariable=self.category_var,
            values=self._load_category_names(),
            state="readonly", font=("Poppins", 11))
        self.category_combo.set("Select Category")
        self.category_combo.pack(fill="x", pady=(0, 14), ipady=6)
        self.category_combo.bind("<<ComboboxSelected>>", self._on_var_change)

        ph_col  = tk.Frame(c1, bg=T["card"])
        ph_col.pack(fill="x")
        ph_left = tk.Frame(ph_col, bg=T["card"])
        ph_left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Frame(ph_col, bg=T["card"]).pack(side="left", fill="x", expand=True)

        self._label(ph_left, "Photographer")
        self.photographer_var = tk.StringVar()
        self._entry(ph_left, self.photographer_var, "Photographer name (optional)")
        self.photographer_var.trace_add("write", self._on_var_change)

        # ── CARD 2: Content ───────────────────────────────────────────────────
        c2 = self._card(self.inner, "Content",
                        "Headline and full article body", "✏")

        self._label(c2, "Headline", required=True)
        self.headline_var = tk.StringVar()
        self._entry(c2, self.headline_var, "Short compelling headline")
        self.headline_var.trace_add("write", self._on_var_change)

        self._hl_counter_var = tk.StringVar(value="0 / 300")
        tk.Label(c2, textvariable=self._hl_counter_var,
                 bg=T["card"], fg=T["text_grey"],
                 font=("Poppins", 8), anchor="e").pack(fill="x", pady=(0, 8))
        self.headline_var.trace_add("write", self._update_headline_counter)

        self._label(c2, "Article Body", required=True)
        body_wrap = tk.Frame(c2, bg=T["border"])
        body_wrap.pack(fill="x", pady=(0, 4))
        self.content_text = tk.Text(
            body_wrap, height=10, wrap="word", font=("Poppins", 11),
            bg=T["input_bg"], fg=T["text_dark"],
            insertbackground=T["accent"],
            relief="flat", padx=10, pady=8, highlightthickness=0)
        self.content_text.pack(fill="x", padx=1, pady=1)
        self.content_text.bind("<<Modified>>", self._on_text_modified)

        self._body_counter_var = tk.StringVar(value="0 characters")
        tk.Label(c2, textvariable=self._body_counter_var,
                 bg=T["card"], fg=T["text_grey"],
                 font=("Poppins", 8), anchor="e").pack(fill="x", pady=(4, 0))

        # ── CARD 3: Media ─────────────────────────────────────────────────────
        c3 = self._card(self.inner, "Media",
                        "Upload images or videos (optional)", "🖼")

        tk.Button(c3, text="☁  Choose Files", command=self._choose_files,
                  bg=T["accent_soft"], fg=T["accent"],
                  activebackground=T["accent"], activeforeground=T["white"],
                  font=("Poppins", 10, "bold"), bd=0, relief="flat",
                  padx=16, pady=8, cursor="hand2").pack(anchor="w", pady=(0, 8))

        tk.Label(c3, text="Supports JPG, PNG, GIF, WEBP, MP4, MOV — max 50 MB each",
                 bg=T["card"], fg=T["text_grey"],
                 font=("Poppins", 8)).pack(anchor="w", pady=(0, 10))

        self.thumb_frame = tk.Frame(c3, bg=T["card"])
        self.thumb_frame.pack(fill="x")

        self.file_list_var = tk.StringVar(value="No files selected.")
        tk.Label(c3, textvariable=self.file_list_var,
                 bg=T["card"], fg=T["text_grey"],
                 font=("Poppins", 8), justify="left", anchor="w").pack(
                 fill="x", pady=(6, 0))

        # ── CARD 4: Submit ────────────────────────────────────────────────────
        c4 = self._card(self.inner, "Submit",
                        "Save as draft or send for superadmin approval", "📨")

        self._autosave_frame = tk.Frame(c4, bg=T["input_bg"],
                                        highlightbackground=T["border"],
                                        highlightthickness=1)
        self._autosave_frame.pack(fill="x", pady=(0, 12))
        as_inner = tk.Frame(self._autosave_frame, bg=T["input_bg"])
        as_inner.pack(fill="x", padx=12, pady=8)
        self._autosave_dot = tk.Label(as_inner, text="●", bg=T["input_bg"],
                                      fg=T["text_grey"], font=("Poppins", 8))
        self._autosave_dot.pack(side="left")
        self.autosave_var = tk.StringVar(
            value="Changes will autosave to Drafts after 3 seconds of inactivity.")
        tk.Label(as_inner, textvariable=self.autosave_var,
                 bg=T["input_bg"], fg=T["text_grey"],
                 font=("Poppins", 9)).pack(side="left", padx=(6, 0))

        notice = tk.Frame(c4, bg="#fff7f0",
                          highlightbackground="#f5c8a0", highlightthickness=1)
        notice.pack(fill="x", pady=(0, 16))
        notice_inner = tk.Frame(notice, bg="#fff7f0")
        notice_inner.pack(fill="x", padx=12, pady=10)
        tk.Label(notice_inner, text="ℹ", bg="#fff7f0", fg=T["accent"],
                 font=("Poppins", 12)).pack(side="left", anchor="n")
        tk.Label(notice_inner,
                 text="Submitted articles will be sent as Pending and must be approved\n"
                      "by a superadmin before they are published. Use Save to Drafts\n"
                      "to keep editing later.",
                 bg="#fff7f0", fg=T["text_grey"],
                 font=("Poppins", 9), justify="left", anchor="w",
                 wraplength=520).pack(side="left", padx=(8, 0))

        btn_row = tk.Frame(c4, bg=T["card"])
        btn_row.pack(fill="x")

        self.btn_draft = tk.Button(btn_row, text="💾  Save to Drafts",
                                   command=self._save_draft,
                                   bg=T["card"], fg=T["accent"],
                                   activebackground=T["accent_soft"],
                                   font=("Poppins", 10, "bold"),
                                   relief="solid", bd=1,
                                   highlightbackground=T["accent"],
                                   padx=20, pady=10, cursor="hand2")
        self.btn_draft.pack(side="left", padx=(0, 10))

        self.btn_submit = tk.Button(btn_row, text="📨  Submit for Review",
                                    command=self._publish,
                                    bg=T["accent"], fg=T["white"],
                                    activebackground="#d96800",
                                    font=("Poppins", 10, "bold"),
                                    bd=0, relief="flat",
                                    padx=20, pady=10, cursor="hand2")
        self.btn_submit.pack(side="left", padx=(0, 10))

        tk.Button(btn_row, text="↺", command=self._reset_confirm,
                  bg=T["card"], fg=T["text_grey"],
                  font=("Poppins", 12), relief="solid", bd=1,
                  highlightbackground=T["border"],
                  padx=12, pady=8, cursor="hand2").pack(side="left")

    # ── Counter updates ───────────────────────────────────────────────────────

    def _update_headline_counter(self, *_):
        try:
            n = len(self.headline_var.get())
            self._hl_counter_var.set(f"{n} / 300")
        except Exception:
            pass

    def _update_body_counter(self):
        try:
            n = len(self.content_text.get("1.0", "end-1c"))
            self._body_counter_var.set(f"{n:,} characters")
        except Exception:
            pass

    # ── File handling ─────────────────────────────────────────────────────────

    def _choose_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Images or Videos",
            filetypes=[
                ("Media files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp "
                                "*.mp4 *.mov *.avi *.mkv"),
                ("All files", "*.*"),
            ],
        )
        for p in paths:
            if p not in self.selected_files:
                self.selected_files.append(p)
        self._render_files()
        self._schedule_autosave()

    def _render_files(self):
        """
        Render thumbnail grid.

        Images  → opened directly with PIL (unchanged behaviour).
        Videos  → call get_local_thumbnail() in a background thread so the UI
                  doesn't freeze; a spinner label is shown while generating.
        """
        for w in self.thumb_frame.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

        T = self.T
        if not self.selected_files:
            self.file_list_var.set("No files selected.")
            return

        for i, path in enumerate(self.selected_files):
            cell = tk.Frame(self.thumb_frame, bg=T["border"],
                            highlightbackground=T["border"], highlightthickness=1)
            cell.pack(side="left", padx=(0, 8), pady=4)

            ext      = os.path.splitext(path)[1].lower()
            is_video = ext in VIDEO_EXTENSIONS
            is_image = ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")

            img_label = tk.Label(cell, bg=T["input_bg"])
            img_label.pack()

            if is_image and PIL_AVAILABLE and os.path.exists(path):
                # ── Image: load directly ──────────────────────────────────────
                try:
                    img = Image.open(path)
                    img = img.resize((90, 72), Image.LANCZOS)
                    ph  = ImageTk.PhotoImage(img)
                    self._thumb_refs.append(ph)
                    img_label.config(image=ph, width=90, height=72)
                except Exception as e:
                    print(f"[AdminPublish] image thumb error: {e}")
                    img_label.config(text="🖼", font=("Poppins", 24),
                                     fg=T["text_grey"], width=6, height=3)

            elif is_video and PIL_AVAILABLE:
                # ── Video: generate thumbnail in background thread ─────────────
                img_label.config(text="⏳", font=("Poppins", 24),
                                 fg=T["text_grey"], width=6, height=3)

                def _gen_thumb(p=path, lbl=img_label, cell=cell):
                    thumb_path = get_local_thumbnail(p)
                    if thumb_path and os.path.exists(thumb_path):
                        try:
                            img = Image.open(thumb_path)
                            img = img.resize((90, 72), Image.LANCZOS)
                            ph  = ImageTk.PhotoImage(img)
                            # Must update UI from main thread
                            def _apply(ph=ph, lbl=lbl):
                                try:
                                    self._thumb_refs.append(ph)
                                    lbl.config(image=ph, text="",
                                               width=90, height=72)
                                except Exception:
                                    pass
                            self.root.after(0, _apply)
                        except Exception as e:
                            print(f"[AdminPublish] video thumb apply error: {e}")
                            self.root.after(0, lambda lbl=lbl: lbl.config(
                                text="🎬", font=("Poppins", 24),
                                fg=T["text_grey"], width=6, height=3))
                    else:
                        # FFmpeg failed or not installed — fall back to emoji
                        self.root.after(0, lambda lbl=lbl: lbl.config(
                            text="🎬", font=("Poppins", 24),
                            fg=T["text_grey"], width=6, height=3))

                threading.Thread(target=_gen_thumb, daemon=True).start()

            else:
                # Already-uploaded filename or unknown type
                icon = "🎬" if is_video else "🖼"
                img_label.config(text=icon, font=("Poppins", 24),
                                 fg=T["text_grey"], width=6, height=3)

            # Remove button
            idx = i
            tk.Button(cell, text="✕",
                      command=lambda x=idx: self._remove_file(x),
                      bg="#e63a3a", fg="white",
                      activebackground="#c02020", activeforeground="white",
                      font=("Poppins", 7, "bold"),
                      bd=0, relief="flat", padx=3, pady=1,
                      cursor="hand2").pack(fill="x")

        names = [os.path.basename(str(p)) for p in self.selected_files]
        self.file_list_var.set(f"Files ({len(names)}): " + ", ".join(names))

    def _remove_file(self, index):
        if 0 <= index < len(self.selected_files):
            self.selected_files.pop(index)
        self._render_files()

    # ── Autosave ──────────────────────────────────────────────────────────────

    def _on_var_change(self, *_):
        self._update_progress()
        self._schedule_autosave()

    def _on_text_modified(self, event=None):
        if self.content_text.edit_modified():
            self._update_body_counter()
            self._update_progress()
            self._schedule_autosave()
            self.content_text.edit_modified(False)

    def _on_focus_out(self, event=None):
        if self._submitted:
            return
        try:
            if not self.content_text.winfo_exists():
                return
            self._do_autosave()
        except Exception as e:
            print(f"[Autosave] FocusOut error: {e}")

    def _schedule_autosave(self, *_):
        if self._autosave_job:
            self.root.after_cancel(self._autosave_job)
        self._autosave_job = self.root.after(AUTOSAVE_DELAY_MS, self._do_autosave)

    def _do_autosave(self):
        if self._submitted:
            return
        try:
            if not self.content_text.winfo_exists():
                return
        except Exception:
            return
        data = self._collect_form_data()
        if not any([data["author"], data["headline"],
                    data["content_text"], data["category"]]):
            return
        if not self._autosave_lock.acquire(blocking=False):
            return
        self._set_autosave_status("saving", "Autosaving…")
        threading.Thread(target=self._autosave_thread, args=(data,),
                         daemon=True).start()

    def _autosave_thread(self, data):
        try:
            cb = self.callbacks.get("save_draft")
            if cb:
                result = cb(data)
                if result and "id" in result:
                    uploaded = data.get("file_paths", [])
                    self.root.after(0, self._on_autosave_success,
                                    result["id"], uploaded)
                else:
                    self.root.after(0, self._on_autosave_fail,
                                    "Autosave failed — check DB connection.")
        except Exception as exc:
            self.root.after(0, self._on_autosave_fail, str(exc))
        finally:
            self._autosave_lock.release()

    def _on_autosave_success(self, new_id, uploaded_paths=None):
        self.draft_id = new_id
        if uploaded_paths:
            self.selected_files = uploaded_paths
            self._render_files()
        self._set_autosave_status(
            "saved", f"✔  Draft autosaved · {self._now_time()}")
        self.root.after(3500, lambda: self._set_autosave_status(
            "idle",
            "Changes will autosave to Drafts after 3 seconds of inactivity."))

    def _on_autosave_fail(self, msg):
        self._set_autosave_status("error", f"⚠  Autosave failed — {msg}")

    def _now_time(self):
        from datetime import datetime
        return datetime.now().strftime("%I:%M %p")

    def _set_autosave_status(self, state, msg):
        T = self.T
        colour_map = {
            "saving": T["accent"], "saved":  T["success"],
            "error":  T["error"],  "idle":   T["text_grey"],
        }
        col = colour_map.get(state, T["text_grey"])
        try:
            self.autosave_var.set(msg)
            self._autosave_dot.config(fg=col)
        except Exception:
            pass

    # ── Form actions ──────────────────────────────────────────────────────────

    def _collect_form_data(self) -> dict:
        cat = self.category_var.get()
        if cat in ("Select Category", ""):
            cat = ""

        flask_url = self.callbacks.get("flask_url", "http://127.0.0.1:5000")
        api_token = self.callbacks.get("api_token", "")

        def _is_local(path: str) -> bool:
            p = str(path)
            # Dicts are already-processed upload results — not local
            if isinstance(path, dict):
                return False
            return (os.path.isabs(p) or (len(p) > 1 and p[1] == ":")
                    or "/" in p or "\\" in p)

        local_files      = [f for f in self.selected_files if _is_local(f)]
        already_uploaded = [f for f in self.selected_files if not _is_local(f)]

        if local_files:
            # upload_files_to_flask now returns dicts for both images and videos
            newly_uploaded   = upload_files_to_flask(local_files, flask_url, api_token)
            self.selected_files = already_uploaded + newly_uploaded
            self._render_files()
        else:
            newly_uploaded = []

        uploaded = already_uploaded + newly_uploaded

        return {
            "draft_id":     self.draft_id,
            "author":       self.author_var.get().strip(),
            "photographer": self.photographer_var.get().strip(),
            "headline":     self.headline_var.get().strip(),
            "content_text": self.content_text.get("1.0", "end-1c").strip(),
            "category":     cat,
            "file_paths":   uploaded,   # list of dicts or bare strings
            "author_id":    self.user[3] if self.user and len(self.user) > 3 else None,
        }

    def _save_draft(self):
        if self._autosave_job:
            self.root.after_cancel(self._autosave_job)
            self._autosave_job = None
        data = self._collect_form_data()
        if not any([data["author"], data["headline"],
                    data["content_text"], data["category"]]):
            messagebox.showinfo("Save Draft", "Nothing to save yet.")
            return
        cb = self.callbacks.get("save_draft")
        if not cb:
            messagebox.showerror("Config Error",
                                 "save_draft callback is not wired up.")
            return
        try:
            result = cb(data)
            if result and "id" in result:
                self.draft_id = result["id"]
                uploaded = data.get("file_paths", [])
                if uploaded:
                    self.selected_files = uploaded
                    self._render_files()
                self._set_autosave_status(
                    "saved", f"✔  Saved to Drafts · {self._now_time()}")
                messagebox.showinfo("Saved", "Draft saved successfully.")
            else:
                messagebox.showerror("Failed", "Could not save draft.")
        except Exception as exc:
            messagebox.showerror("Error", f"Save failed:\n{exc}")

    def _publish(self):
        if self._autosave_job:
            self.root.after_cancel(self._autosave_job)
            self._autosave_job = None
        data   = self._collect_form_data()
        errors = []
        if not data["author"]:       errors.append("• Author is required.")
        if not data["headline"]:     errors.append("• Headline is required.")
        if not data["content_text"]: errors.append("• Content cannot be empty.")
        if not data["category"]:     errors.append("• Please select a Category.")
        if errors:
            messagebox.showwarning("Validation",
                                   "Please fix the following:\n" + "\n".join(errors))
            return
        if not messagebox.askyesno("Confirm Submission",
                                   f"Submit '{data['headline']}' for review?"):
            return
        cb = self.callbacks.get("submit_for_review")
        if not cb:
            messagebox.showerror("Config Error",
                                 "submit_for_review callback is not wired up.")
            return
        try:
            if not self.draft_id:
                save_cb = self.callbacks.get("save_draft")
                if save_cb:
                    result = save_cb(data)
                    if result and "id" in result:
                        self.draft_id    = result["id"]
                        data["draft_id"] = self.draft_id
            data["draft_id"] = self.draft_id
            result = cb(data)
            if result:
                self._submitted = True
                messagebox.showinfo("Submitted",
                                    "Article submitted for superadmin review.")
                self._clear_form()
            else:
                messagebox.showerror("Failed",
                                     "Submission failed. Check terminal for DB error.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not submit article:\n{exc}")

    def _reset_confirm(self):
        if not messagebox.askyesno("Clear Form",
                                   "Clear the entire form? Any unsaved changes will be lost."):
            return
        self._clear_form()

    def _clear_form(self):
        if self._autosave_job:
            self.root.after_cancel(self._autosave_job)
            self._autosave_job = None
        self.draft_id   = None
        self._submitted = False
        self.author_var.set("")
        self.photographer_var.set("")
        self.headline_var.set("")
        self.content_text.delete("1.0", "end")
        self.category_var.set("")
        self.category_combo.set("Select Category")
        self.selected_files.clear()
        self._render_files()
        self._set_autosave_status(
            "idle",
            "Changes will autosave to Drafts after 3 seconds of inactivity.")
        self._update_progress()


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    saved_drafts = []

    def _mock_save(data):
        did = data.get("draft_id")
        if did:
            for i, d in enumerate(saved_drafts):
                if d.get("draft_id") == did:
                    saved_drafts[i] = {**data, "draft_id": did}
                    print(f"[mock] Updated draft {did}: {data['headline']}")
                    return {"id": did}
        new_id = len(saved_drafts) + 1
        saved_drafts.append({**data, "draft_id": new_id})
        print(f"[mock] Created draft {new_id}: {data['headline']}")
        return {"id": new_id}

    root = tk.Tk()
    root.title("The Gears — Publish Article")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    AdminPublish(
        root,
        user=("Maria", "Santos", "maria@gears.com", 1, "admin"),
        db_callbacks={"save_draft": _mock_save},
    )
    root.mainloop()