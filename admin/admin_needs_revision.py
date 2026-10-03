"""
admin/admin_needs_revision.py
──────────────────────────────
Needs Revision page for The Gears Admin.
Inherits the full header + sidebar + scrollable shell from AdminLayout.

Shows articles returned by Superadmin with revision notes / inline comments.
Admin can:
  • View the article + superadmin feedback in a modal
  • Edit the headline and body inline in the modal
  • Submit the revised article back for review

The revision modal lives in admin/admin_revision_modal.py and is imported here.

db_callbacks keys:
  fetch_needs_revision()                         → list of tuples
  submit_revision(article_id)                    → bool
  save_revision_edit(article_id, headline, body) → bool

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
  11 feedback          superadmin revision notes
"""

import tkinter as tk
from tkinter import messagebox, ttk

from admin.admin_layout import AdminLayout, FONTS

try:
    from admin.admin_revision_modal import open_revision_modal
except ImportError:
    from admin_revision_modal import open_revision_modal


def _rounded_button(parent, text, command, bg, fg, hover_bg=None, **kwargs):
    """Styled button with optional hover colour swap."""
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg,
        activebackground=hover_bg or bg,
        activeforeground=fg,
        font=FONTS.get("button", ("Poppins", 9, "bold")),
        bd=0, relief="flat", cursor="hand2",
        padx=14, pady=6,
        **kwargs,
    )
    if hover_bg:
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


# ─────────────────────────────────────────────────────────────────────────────
class AdminNeedsRevision(AdminLayout):
    """
    Needs Revision admin page.

    Inherits the full chrome from AdminLayout; only the revision-specific
    table, badge, and action buttons live here.
    """

    ACTIVE_NAV = "needs_revision"

    def __init__(self, root, user=None, db_callbacks=None):
        self.articles = []
        super().__init__(root, user, db_callbacks)
        self._build_page()
        self._refresh()

    # =========================================================================
    # AdminLayout hook
    # =========================================================================

    def _build_page(self):
        self.articles = []
        self._build_page_header()
        self._build_table_card()

    # =========================================================================
    # Data
    # =========================================================================

    def _fetch(self) -> list:
        cb = self.callbacks.get("fetch_needs_revision")
        if cb:
            try:
                return cb() or []
            except Exception as exc:
                print(f"[AdminNeedsRevision] fetch error: {exc}")
        return []

    def _refresh(self):
        self.articles = self._fetch()
        self._repopulate_table()
        self._refresh_badge()
        self._update_action_buttons(None)

    # =========================================================================
    # Page header
    # =========================================================================

    def _build_page_header(self):
        T = self.theme

        row = tk.Frame(self.inner, bg=T["background"])
        row.pack(fill="x", pady=(0, 4))

        left = tk.Frame(row, bg=T["background"])
        left.pack(side="left")

        tk.Label(
            left, text="NEEDS REVISION",
            font=FONTS["heading"],
            bg=T["background"], fg=T["primary_orange"],
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Articles returned by Superadmin with feedback. "
                 "Edit and resubmit for review.",
            font=FONTS["body"],
            bg=T["background"], fg=T["text_grey"],
        ).pack(anchor="w", pady=(2, 0))

    # =========================================================================
    # Table card
    # =========================================================================

    def _build_table_card(self):
        T = self.theme

        card = tk.Frame(
            self.inner, bg=T["card"],
            highlightthickness=1,
            highlightbackground=T["border"],
        )
        card.pack(fill="both", expand=True, pady=(10, 0))
        self._table_card = card

        # ── Card header ───────────────────────────────────────────────────────
        hdr_bg = T.get("row_alt", "#FAFAFA")
        hdr = tk.Frame(card, bg=hdr_bg)
        hdr.pack(fill="x")

        left_hdr = tk.Frame(hdr, bg=hdr_bg)
        left_hdr.pack(side="left", padx=18, pady=10)
        tk.Label(left_hdr, text="Article List",
                 font=FONTS["section"],
                 bg=hdr_bg, fg=T["text_dark"]).pack(anchor="w")
        tk.Label(left_hdr,
                 text="Articles flagged for revision by Superadmin.",
                 font=FONTS["small"],
                 bg=hdr_bg, fg=T["text_grey"]).pack(anchor="w")

        right_hdr = tk.Frame(hdr, bg=hdr_bg)
        right_hdr.pack(side="right", padx=18, pady=10)

        tk.Button(
            right_hdr, text="↻  Refresh", command=self._refresh,
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            activebackground=T["primary_orange"],
            activeforeground=T["white"],
            font=FONTS["small_bold"],
            bd=0, relief="flat", padx=10, pady=4, cursor="hand2",
        ).pack(side="right", padx=(8, 0))

        self._badge_var = tk.StringVar(value="0 articles")
        tk.Label(
            right_hdr, textvariable=self._badge_var,
            font=FONTS["tag"],
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            relief="flat", padx=10, pady=4,
        ).pack(side="right")

        ttk.Separator(card, orient="horizontal").pack(fill="x")

        # ── Treeview ──────────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "NR.Treeview",
            background=T["card"],
            fieldbackground=T["card"],
            foreground=T["text_dark"],
            rowheight=32,
            font=FONTS["body"],
            borderwidth=0,
        )
        style.configure(
            "NR.Treeview.Heading",
            background=T.get("row_alt", "#FCFCFC"),
            foreground=T["text_grey"],
            font=FONTS["small_bold"],
            relief="flat",
        )
        style.map(
            "NR.Treeview",
            background=[("selected", T["primary_orange_light"])],
            foreground=[("selected", T["text_dark"])],
        )

        cols = ("headline", "author", "category", "last_updated", "status")
        self.tree = ttk.Treeview(
            card, columns=cols, show="headings",
            style="NR.Treeview", selectmode="browse",
        )

        col_cfg = {
            "headline":     ("Headline",      320, True),
            "author":       ("Author",        160, False),
            "category":     ("Category",      120, False),
            "last_updated": ("Last Updated",  140, False),
            "status":       ("Status",        140, False),
        }
        for cid, (lbl, w, stretch) in col_cfg.items():
            self.tree.heading(cid, text=lbl)
            self.tree.column(cid, width=w, minwidth=60, stretch=stretch, anchor="w")

        self.tree.tag_configure("odd",  background=T["card"])
        self.tree.tag_configure("even", background=T.get("row_alt", "#FCFCFC"))

        vsb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>",         lambda e: self._view_selected())
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

        # ── Actions toolbar ───────────────────────────────────────────────────
        self._actions_bar = tk.Frame(card, bg=T["background_alt"])
        self._actions_bar.pack(fill="x", padx=18, pady=8)
        self._build_actions_toolbar()

    def _build_actions_toolbar(self):
        T = self.theme
        for w in self._actions_bar.winfo_children():
            w.destroy()

        self._no_sel_label = tk.Label(
            self._actions_bar,
            text="Select a row to see available actions.",
            font=FONTS["small"],
            bg=T["background_alt"],
            fg=T["text_light"],
        )
        self._no_sel_label.pack(side="left")

        self._btn_view = _rounded_button(
            self._actions_bar,
            "👁  View & Edit",
            self._view_selected,
            bg=T["primary_orange"],
            fg=T["white"],
            hover_bg=T["primary_orange_dark"],
        )
        self._btn_submit = _rounded_button(
            self._actions_bar,
            "📤  Submit for Review",
            self._submit_selected,
            bg="#22C55E",
            fg=T["white"],
            hover_bg="#16A34A",
        )
        self._btn_view.pack_forget()
        self._btn_submit.pack_forget()

    # =========================================================================
    # Table population
    # =========================================================================

    def _repopulate_table(self):
        self.tree.delete(*self.tree.get_children())

        if not self.articles:
            self.tree.insert("", "end",
                             values=("No articles need revision. ✅", "", "", "", ""),
                             tags=("odd",))
            return

        for i, a in enumerate(self.articles):
            def col(idx, fallback="-", _a=a):
                try:
                    return _a[idx] if _a[idx] not in (None, "") else fallback
                except IndexError:
                    return fallback

            headline = col(8, col(3, "(Untitled)")) or "(Untitled)"
            tag      = "even" if i % 2 == 0 else "odd"

            self.tree.insert(
                "", "end",
                iid=f"art_{i}_{col(0)}",
                values=(headline, col(10, col(1)),
                        col(2), col(7), "🛠  Needs Revision"),
                tags=(tag,),
            )

    def _refresh_badge(self):
        if hasattr(self, "_badge_var"):
            n = len(self.articles)
            self._badge_var.set(f"{n} article{'s' if n != 1 else ''}")

    # =========================================================================
    # Row selection
    # =========================================================================

    def _on_row_select(self, _event=None):
        self._update_action_buttons(self._get_selected_article())

    def _get_selected_article(self):
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        return next((a for a in self.articles if iid.endswith(f"_{a[0]}")), None)

    def _update_action_buttons(self, article):
        self._no_sel_label.pack_forget()
        self._btn_view.pack_forget()
        self._btn_submit.pack_forget()

        if article is None:
            self._no_sel_label.pack(side="left")
        else:
            self._btn_view.pack(side="left", padx=(0, 6))
            self._btn_submit.pack(side="left", padx=(0, 6))

    def _get_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select an article first.")
            return None, None
        iid = sel[0]
        art = next((a for a in self.articles if iid.endswith(f"_{a[0]}")), None)
        return iid, art

    # =========================================================================
    # Actions
    # =========================================================================

    def _view_selected(self):
        _, art = self._get_selected()
        if art is None:
            return
        open_revision_modal(
            root         = self.root,
            art          = art,
            theme        = self.theme,
            callbacks    = self.callbacks,
            on_saved     = self._refresh,
            on_submitted = self._refresh,
        )

    def _submit_selected(self):
        _, art = self._get_selected()
        if art is None:
            return

        headline = (art[8] if len(art) > 8 and art[8]
                    else art[3] if len(art) > 3 else "(Untitled)")

        if not messagebox.askyesno(
            "Submit for Review",
            f"Submit '{headline}' back to Superadmin for review?",
        ):
            return

        cb = self.callbacks.get("submit_revision")
        if cb:
            if cb(art[0]):
                messagebox.showinfo("Submitted",
                    "Article submitted for Superadmin review.")
                self._refresh()
            else:
                messagebox.showerror("Error", "Failed to submit article.")
        else:
            messagebox.showinfo("Stub", "submit_revision callback not wired.")


# =============================================================================
# Standalone demo
# =============================================================================

if __name__ == "__main__":
    import tkinter as tk

    SAMPLE = [
        (
            1, "Maria Santos", "News",
            "Campus Paper Launches New Edition",
            "The Gears officially launched its new digital desktop edition "
            "this semester. The platform was developed by the IT department "
            "in collaboration with the editorial board.",
            "", "", "2025-05-01 10:22",
            "Campus Paper Launches New Edition",
            "The Gears officially launched its new digital desktop edition.",
            "Maria Santos",
            "GENERAL NOTES:\nPlease expand the introduction and clarify the timeline.\n\n"
            "INLINE COMMENTS:\n"
            '1. Text: "IT department"\n'
            "   Comment: Spell out the full department name on first use.",
        ),
        (
            2, "Juan Dela Cruz", "Opinion",
            "Why Student Voices Still Matter",
            "In an era dominated by social media, the role of campus journalism "
            "remains crucial.",
            "", "", "2025-04-28 09:15",
            "Why Student Voices Still Matter",
            "In an era dominated by social media, the role of campus journalism "
            "remains crucial.",
            "Juan Dela Cruz",
            "GENERAL NOTES:\nStrong piece but needs a stronger conclusion.",
        ),
    ]

    root = tk.Tk()
    root.title("The Gears — Needs Revision")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    AdminNeedsRevision(
        root,
        user=("Maria", "Santos", "maria@gears.com", 1, "admin"),
        db_callbacks={
            "fetch_needs_revision": lambda: SAMPLE,
            "save_revision_edit":   lambda aid, h, b: (
                print(f"save({aid}) h={h} b={b[:40]}") or True),
            "submit_revision":      lambda aid: (
                print(f"submit({aid})") or True),
        },
    )
    root.mainloop()