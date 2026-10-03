"""
admin/admin_under_review.py
───────────────────────────
"Under Review" page for The Gears Admin.
Inherits the full header + sidebar + scrollable shell from AdminLayout.

db_callbacks keys (all optional — page degrades gracefully)
───────────────────────────────────────────────────────────
  fetch_under_review()
      → list of tuples (10+ fields):
          (id, author, category, date_submitted, admin_name,
           None, autosaved, photographer, headline, content_text,
           media_json [optional index 10])

  withdraw_submission(article_id: int) → bool
      Moves the article back to 'draft' status.
"""

import json
import os
import tkinter as tk
from tkinter import Image, messagebox, ttk

from admin.admin_layout import AdminLayout, FONTS, COLORS


# ─────────────────────────────────────────────────────────────────────────────
class AdminUnderReview(AdminLayout):
    """
    "Under Review" admin page.

    Inherits the full chrome (header, orange bar, sidebar, user-dropdown,
    dark-mode toggle, navigation, geometry management) from AdminLayout.
    Only the page-specific table + modal live here.
    """

    ACTIVE_NAV = "under_review"

    def __init__(self, root, user=None, db_callbacks=None):
        self._articles = []
        super().__init__(root, user, db_callbacks)
        self._build_page()
        self._load_data()

    # =========================================================================
    # AdminLayout hook — called on first build AND after dark-mode toggle
    # =========================================================================

    def _build_page(self):
        self._articles = []          # reset before repopulating
        self._build_panel()

    # =========================================================================
    # Data
    # =========================================================================

    def _load_data(self):
        cb = self.callbacks.get("fetch_under_review")
        if cb:
            try:
                self._articles = cb() or []
            except Exception as exc:
                print(f"[AdminUnderReview] fetch error: {exc}")
                self._articles = []
        else:
            self._articles = []
        self._populate_table()

    # =========================================================================
    # Panel + table
    # =========================================================================

    def _build_panel(self):
        T = self.theme

        panel = tk.Frame(
            self.inner, bg=T["card"],
            highlightbackground=T["border"], highlightthickness=1,
            padx=22, pady=18,
        )
        panel.pack(fill="x")

        # Orange top accent bar
        tk.Frame(panel, bg=T["primary_orange"], height=3).pack(
            fill="x", pady=(0, 14)
        )

        # Title row
        title_row = tk.Frame(panel, bg=T["card"])
        title_row.pack(fill="x", pady=(0, 4))

        tk.Frame(title_row, bg=T["primary_orange"],
                 width=4, height=22).pack(side="left", padx=(0, 10))
        tk.Label(
            title_row,
            text="ARTICLES UNDER REVIEW",
            bg=T["card"], fg=T["primary_orange"],
            font=FONTS["section"],
        ).pack(side="left")

        tk.Button(
            title_row, text="↻  Refresh", command=self._load_data,
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            activebackground=T["primary_orange"],
            activeforeground=T["white"],
            font=FONTS["small_bold"],
            bd=0, relief="flat", padx=10, pady=4, cursor="hand2",
        ).pack(side="right")

        # Subtitle
        sub_frame = tk.Frame(panel, bg=T["card"])
        sub_frame.pack(fill="x", pady=(0, 16))
        tk.Label(
            sub_frame,
            text=(
                "These articles have been submitted to Superadmin and are awaiting approval.  "
                "Status: Waiting for Approval."
            ),
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["body"], anchor="w",
        ).pack(fill="x")

        # Divider
        tk.Frame(panel, bg=T["border"], height=1).pack(fill="x", pady=(0, 14))

        # Keep a reference so _show/_hide empty notice and _populate_table can use it
        self._table_panel = panel
        self._build_table(panel)

    def _build_table(self, parent):
        T = self.theme

        cols = ("headline", "category", "date_submitted", "status", "actions")
        self._tree = ttk.Treeview(
            parent, columns=cols, show="headings", selectmode="browse"
        )

        col_config = {
            "headline":       ("Title",          340, True),
            "category":       ("Category",       130, False),
            "date_submitted": ("Date Submitted", 150, False),
            "status":         ("Status",         110, False),
            "actions":        ("Actions",        130, False),
        }
        for c, (label, width, stretch) in col_config.items():
            self._tree.heading(c, text=label)
            self._tree.column(c, width=width, minwidth=60, stretch=stretch)

        style = ttk.Style()
        style.configure(
            "Treeview",
            font=("Poppins", 10),
            rowheight=32,
            background=T["card"],
            fieldbackground=T["card"],
            foreground=T["text_dark"],
        )
        style.configure(
            "Treeview.Heading",
            font=("Poppins", 9, "bold"),
            background=T["background_alt"],
            foreground=T["text_grey"],
        )
        style.map(
            "Treeview",
            background=[("selected", T["primary_orange_light"])],
            foreground=[("selected", T["text_dark"])],
        )

        self._tree.tag_configure("even", background=T.get("row_alt", "#FCFCFC"))
        self._tree.tag_configure("odd",  background=T["card"])

        tree_sb = ttk.Scrollbar(parent, orient="vertical",
                                command=self._tree.yview)
        self._tree.configure(yscrollcommand=tree_sb.set)
        tree_sb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        # Actions toolbar below the table
        self._actions_bar = tk.Frame(parent, bg=T["card"])
        self._actions_bar.pack(fill="x", padx=18, pady=8)
        self._build_actions_toolbar()

        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)

    def _build_actions_toolbar(self):
        T = self.theme
        for w in self._actions_bar.winfo_children():
            w.destroy()

        self._no_sel_label = tk.Label(
            self._actions_bar,
            text="Select a row to see available actions.",
            font=FONTS["small"],
            bg=T["card"],
            fg=T["text_light"],
        )
        self._no_sel_label.pack(side="left")

        self._btn_view = tk.Button(
            self._actions_bar, text="👁  View",
            command=self._on_view,
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            activebackground=T["primary_orange"],
            activeforeground=T["white"],
            font=FONTS["small_bold"],
            bd=0, relief="flat", padx=10, pady=5, cursor="hand2",
        )
        self._btn_draft = tk.Button(
            self._actions_bar, text="⏪  Move to Draft",
            command=self._on_draft,
            bg=T["background_alt"], fg=T["text_mid"],
            activebackground=T["border"],
            activeforeground=T["text_dark"],
            font=FONTS["small_bold"],
            bd=0, relief="flat", padx=10, pady=5, cursor="hand2",
        )
        # Start hidden; shown on row selection
        self._btn_view.pack_forget()
        self._btn_draft.pack_forget()

    # ── Table population ─────────────────────────────────────────────────────

    def _populate_table(self):
        self._tree.delete(*self._tree.get_children())

        if not self._articles:
            self._show_empty_notice()
            return

        self._hide_empty_notice()

        for i, article in enumerate(self._articles):
            headline = str(article[8]) if len(article) > 8 and article[8] else "(Untitled)"
            cat      = str(article[2]) if len(article) > 2 and article[2] else "—"
            date     = str(article[3]) if len(article) > 3 and article[3] else "—"
            tag      = "even" if i % 2 == 0 else "odd"

            self._tree.insert(
                "", "end", iid=str(article[0]),
                values=(headline, cat, date, "⏳ Waiting", "View / Draft"),
                tags=(tag,),
            )

    def _show_empty_notice(self):
        if hasattr(self, "_empty_frame") and self._empty_frame.winfo_exists():
            return
        T = self.theme
        self._empty_frame = tk.Frame(self._table_panel, bg=T["card"], pady=40)
        self._empty_frame.pack(fill="x")
        tk.Label(self._empty_frame, text="📤",
                 bg=T["card"], fg=T["text_light"],
                 font=("Poppins", 32)).pack()
        tk.Label(self._empty_frame,
                 text="No articles waiting for approval yet.",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["body"]).pack(pady=(8, 4))
        tk.Label(self._empty_frame,
                 text="Submit an article from Drafts first.",
                 bg=T["card"], fg=T["text_light"],
                 font=FONTS["small"]).pack()

    def _hide_empty_notice(self):
        if hasattr(self, "_empty_frame"):
            try:
                self._empty_frame.destroy()
            except Exception:
                pass

    # ── Row selection ────────────────────────────────────────────────────────

    def _on_row_select(self, _event=None):
        article = self._selected_article()
        self._no_sel_label.pack_forget()
        self._btn_view.pack_forget()
        self._btn_draft.pack_forget()

        if article is None:
            self._no_sel_label.pack(side="left")
        else:
            self._btn_view.pack(side="left", padx=(0, 6))
            self._btn_draft.pack(side="left", padx=(0, 6))

    def _selected_article(self):
        sel = self._tree.selection()
        if not sel:
            return None
        iid = int(sel[0])
        return next((a for a in self._articles if a[0] == iid), None)

    def _on_view(self):
        article = self._selected_article()
        if article:
            self._open_view_modal(article)

    def _on_draft(self):
        article = self._selected_article()
        if article:
            self._withdraw(article)

    # =========================================================================
    # View modal
    # =========================================================================

    def _open_view_modal(self, article):
        """Full-screen two-panel modal: media left, content right."""
        T = self.theme

        overlay = tk.Toplevel(self.root)
        overlay.title("View Article")
        overlay.configure(bg="#000000")
        overlay.transient(self.root)
        overlay.grab_set()
        try:
            overlay.attributes("-alpha", 0.98)
        except tk.TclError:
            pass

        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        mw = min(max(int(rw * 0.88), 860), 1300)
        mh = min(max(int(rh * 0.85), 560), 800)
        x  = self.root.winfo_x() + (rw - mw) // 2
        y  = self.root.winfo_y() + (rh - mh) // 2
        overlay.geometry(f"{mw}x{mh}+{x}+{y}")
        overlay.resizable(True, True)

        card = tk.Frame(overlay, bg=T["card"],
                        highlightbackground=T["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Button(
            card, text="✕", command=overlay.destroy,
            bg=T["card"], fg=T["text_grey"],
            activebackground=T["background_alt"],
            activeforeground=T["text_dark"],
            font=("Poppins", 18), bd=0, relief="flat", cursor="hand2",
        ).place(x=mw - 56, y=6)

        # ── Split layout ──────────────────────────────────────────────────────
        left_panel  = tk.Frame(card, bg="#111111")
        right_panel = tk.Frame(card, bg=T["card"])
        left_panel.place( relx=0,    rely=0, relwidth=0.55, relheight=1)
        right_panel.place(relx=0.55, rely=0, relwidth=0.45, relheight=1)

        # ── Media panel ───────────────────────────────────────────────────────
        file_paths = self._extract_media_paths(article)
        self._media_index = 0
        self._media_paths = file_paths

        media_canvas = tk.Canvas(left_panel, bg="#111111", highlightthickness=0)
        media_canvas.pack(fill="both", expand=True)

        media_label = tk.Label(left_panel, bg="#111111", fg="#cccccc",
                            font=FONTS["body"])
        media_label.place(relx=0.5, rely=0.5, anchor="center")

        def _load_image_from_server(fname):
            """
            Try root uploads first, then avatars subfolder.
            Returns a PIL Image or raises Exception.
            """
            import urllib.request, io as _io
            from PIL import Image

            flask_url = self.callbacks.get("flask_url", "http://127.0.0.1:5000")

            # If it's a local path that exists, open directly
            if os.path.exists(fname):
                return Image.open(fname)

            base = os.path.basename(fname.replace("\\", "/"))
            last_exc = None
            for subfolder in ("", "avatars/"):
                url = f"{flask_url}/static/uploads/{subfolder}{base}"
                try:
                    with urllib.request.urlopen(url, timeout=8) as resp:
                        img = Image.open(_io.BytesIO(resp.read()))
                        img.load()
                        return img
                except Exception as e:
                    last_exc = e
                    continue

            raise Exception(f"Image not found: {base} — {last_exc}")

        def _show_media():
            media_canvas.delete("all")
            media_label.config(text="")

            if not self._media_paths:
                media_label.config(text="No media uploaded.")
                return

            path = self._media_paths[self._media_index]
            ext  = os.path.splitext(path.lower())[1]

            try:
                from PIL import Image, ImageTk

                if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"):
                    img = _load_image_from_server(path)
                    cw  = media_canvas.winfo_width()  or 420
                    ch  = media_canvas.winfo_height() or 520
                    resample = getattr(Image, "Resampling", Image)
                    img.thumbnail((cw - 24, ch - 24), resample.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img)
                    media_canvas._img = tk_img
                    media_canvas.create_image(cw // 2, ch // 2,
                                            image=tk_img, anchor="center")
                    return
            except Exception as exc:
                print(f"[AdminUnderReview] image preview error: {exc}")

            media_label.config(
                text=f"{os.path.basename(path)}\nPreview not available for this file type."
            )

        counter_var = tk.StringVar(value="")

        def _update_counter():
            if self._media_paths:
                counter_var.set(f"{self._media_index + 1} / {len(self._media_paths)}")
            else:
                counter_var.set("0 / 0")

        def _prev():
            if self._media_paths:
                self._media_index = (self._media_index - 1) % len(self._media_paths)
                _show_media()
                _update_counter()

        def _next():
            if self._media_paths:
                self._media_index = (self._media_index + 1) % len(self._media_paths)
                _show_media()
                _update_counter()

        if len(file_paths) > 1:
            tk.Button(
                left_panel, text="‹", command=_prev,
                bg="#222", fg="white", activebackground="#444",
                font=("Poppins", 20, "bold"), bd=0, relief="flat",
                width=2, cursor="hand2",
            ).place(x=10, rely=0.5, anchor="w")
            tk.Button(
                left_panel, text="›", command=_next,
                bg="#222", fg="white", activebackground="#444",
                font=("Poppins", 20, "bold"), bd=0, relief="flat",
                width=2, cursor="hand2",
            ).place(relx=1.0, x=-10, rely=0.5, anchor="e")
            tk.Label(
                left_panel, textvariable=counter_var,
                bg="#111111", fg="#888888", font=FONTS["small"],
            ).place(relx=0.5, rely=1.0, anchor="s", y=-8)

        overlay.after(100, lambda: (_show_media(), _update_counter()))

        # ── Content panel ─────────────────────────────────────────────────────
        ci = tk.Frame(right_panel, bg=T["card"])
        ci.pack(fill="both", expand=True, padx=22, pady=18)

        tk.Frame(ci, bg=T["primary_orange"], height=3).pack(fill="x", pady=(0, 14))

        headline = str(article[8]) if len(article) > 8 and article[8] else "(Untitled)"
        tk.Label(
            ci, text=headline,
            bg=T["card"], fg=T["primary_orange"],
            font=("Poppins", 16, "bold"),
            wraplength=int(mw * 0.42), justify="left", anchor="w",
        ).pack(fill="x", pady=(0, 4))

        cat  = str(article[2]) if len(article) > 2 and article[2] else "—"
        date = str(article[3]) if len(article) > 3 and article[3] else "—"
        tk.Label(
            ci,
            text=f"Category: {cat}   •   Submitted: {date}",
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["small"], anchor="w",
        ).pack(fill="x", pady=(0, 12))

        # Status + author row
        pill_row = tk.Frame(ci, bg=T["card"])
        pill_row.pack(fill="x", pady=(0, 14))
        tk.Label(
            pill_row, text="⏳  Waiting for Approval",
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            font=FONTS["tag"], padx=10, pady=4,
        ).pack(side="left")

        author = str(article[1]) if len(article) > 1 and article[1] else "—"
        tk.Label(
            pill_row, text=f"By: {author}",
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["small"],
        ).pack(side="right")

        tk.Frame(ci, bg=T["border"], height=1).pack(fill="x", pady=(0, 12))

        # Scrollable body text
        body_text = str(article[9]) if len(article) > 9 and article[9] else "(No content)"
        body_frame = tk.Frame(ci, bg=T["background_alt"],
                            highlightbackground=T["border"], highlightthickness=1)
        body_frame.pack(fill="both", expand=True, pady=(0, 14))

        body_sb = tk.Scrollbar(body_frame, orient="vertical")
        body_sb.pack(side="right", fill="y")
        body_txt = tk.Text(
            body_frame, wrap="word", font=FONTS["body"],
            bg=T["background_alt"], fg=T["text_dark"],
            relief="flat", bd=0,
            yscrollcommand=body_sb.set,
            padx=12, pady=10,
        )
        body_txt.insert("1.0", body_text)
        body_txt.config(state="disabled")
        body_txt.pack(side="left", fill="both", expand=True)
        body_sb.config(command=body_txt.yview)

        # Action buttons
        btn_row = tk.Frame(ci, bg=T["card"])
        btn_row.pack(fill="x", pady=(4, 0))

        tk.Button(
            btn_row, text="⏪  Move Back to Drafts",
            command=lambda: (overlay.destroy(), self._withdraw(article)),
            bg=T["background_alt"], fg=T["text_mid"],
            activebackground=T["border"],
            activeforeground=T["text_dark"],
            font=FONTS["button"], bd=0, relief="flat",
            padx=14, pady=8, cursor="hand2",
        ).pack(side="left")

        tk.Button(
            btn_row, text="✕  Close",
            command=overlay.destroy,
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            activebackground=T["primary_orange"],
            activeforeground=T["white"],
            font=FONTS["button"], bd=0, relief="flat",
            padx=14, pady=8, cursor="hand2",
        ).pack(side="right")

    # =========================================================================
    # Withdraw action
    # =========================================================================

    def _withdraw(self, article):
        article_id = article[0]
        headline   = str(article[8]) if len(article) > 8 and article[8] else "(Untitled)"

        if not messagebox.askyesno(
            "Move Back to Drafts",
            f'Move "{headline}" back to Drafts?\n\n'
            "The article will no longer be under review.",
        ):
            return

        cb = self.callbacks.get("withdraw_submission")
        if cb:
            ok = False
            try:
                ok = cb(article_id)
            except Exception as exc:
                print(f"[AdminUnderReview] withdraw error: {exc}")

            if ok:
                messagebox.showinfo("Done", "Article moved back to Drafts.")
                self._load_data()
            else:
                messagebox.showerror("Error", "Could not move the article. Try again.")
        else:
            messagebox.showinfo(
                "Withdraw",
                f"withdraw_submission({article_id}) would be called here.",
            )
            # Simulate removal for demo
            self._articles = [a for a in self._articles if a[0] != article_id]
            self._populate_table()

    # =========================================================================
    # Media helper
    # =========================================================================

    def _extract_media_paths(self, article) -> list:
        """
        Parse media paths from article[10] (JSON string, dict, or list)
        or from a dict article with "file_paths" / "media" keys.
        """
        media = None

        if isinstance(article, dict):
            media = (
                article.get("media_json")
                or article.get("file_paths")
                or article.get("media")
            )
        elif len(article) > 10:
            media = article[10]

        if not media:
            return []

        try:
            if isinstance(media, str):
                media = json.loads(media)

            if isinstance(media, dict):
                paths = media.get("file_paths", []) or media.get("paths", [])
            elif isinstance(media, list):
                paths = media
            else:
                paths = []
        except Exception as exc:
            print(f"[AdminUnderReview] media parse error: {exc}")
            paths = []

        return [p for p in paths if p and isinstance(p, str)]


# =============================================================================
# DB service helper
# =============================================================================

def build_under_review_callbacks(author_id: int = None) -> dict:
    """
    Wire up DB callbacks for AdminUnderReview.

    Usage in main.py:
        from admin.admin_under_review import AdminUnderReview, build_under_review_callbacks
        cbs = build_under_review_callbacks(current_user_id)
        AdminUnderReview(root, user=user_tuple, db_callbacks=cbs)
    """
    try:
        from services.admin_db_service import fetch_under_review, withdraw_submission
        return {
            "fetch_under_review":  lambda: fetch_under_review(author_id),
            "withdraw_submission": withdraw_submission,
        }
    except ImportError:
        return {}


# =============================================================================
# Standalone demo
# =============================================================================

if __name__ == "__main__":
    SAMPLE = [
        (1, "Maria Santos",  "Campus News",    "2025-05-01 09:30", "admin@gears.com",
         None, 0, "Juan Dela Cruz",
         "Campus paper launches new digital desktop edition",
         "This is a sample article body. " * 30,
         '{"file_paths": [], "author": "Maria Santos"}'),
        (2, "Jose Reyes",    "Opinion",        "2025-05-02 14:15", "admin@gears.com",
         None, 0, "",
         "Why student voices matter in modern campus journalism",
         "Another sample article with deeper content. " * 25,
         '{"file_paths": []}'),
        (3, "Ana Cruz",      "Creative Works", "2025-05-03 11:00", "admin@gears.com",
         None, 0, "",
         "A collection of poems from young writers",
         "Poetry and creativity bloom here. " * 20,
         None),
    ]

    root = tk.Tk()
    root.title("The Gears — Under Review")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    AdminUnderReview(
        root,
        user=("Maria", "Santos", "maria@gears.com", 1, "admin"),
        db_callbacks={
            "fetch_under_review":  lambda: SAMPLE,
            "withdraw_submission": lambda aid: (
                print(f"Withdraw article {aid}") or True
            ),
        },
    )
    root.mainloop()