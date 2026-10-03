"""
superadmin/superadmin_manage_users.py
──────────────────────────────────────
Manage Users page for The Gears Superadmin panel.

Inherits the full header + sidebar + scrollable shell from SuperadminLayout,
so this module only contains page-specific content.

Usage (same as before):
    ManageUsers(root, user=user_tuple, db_callbacks=callbacks)

db_callbacks keys:
    fetch_pending_users   → list of (id, first, last, email, email_verified)
    fetch_accepted_users  → same tuple format
    fetch_rejected_users  → same tuple format
    accept_user(user_id)  → bool
    reject_user(user_id)  → bool
    fetch_profile(user_id) → dict with optional "profile_image"
"""

import tkinter as tk
from tkinter import ttk, messagebox

try:
    from superadmin.superadmin_layout import SuperadminLayout
    from theme import COLORS, FONTS
except ImportError:
    from superadmin_layout import SuperadminLayout
    COLORS = {
        "primary_orange":       "#F19421",
        "primary_orange_dark":  "#D97E10",
        "primary_orange_light": "#FFF1DF",
        "primary_red":          "#B02029",
        "primary_red_dark":     "#8E1A21",
        "background":           "#F8F6F3",
        "background_alt":       "#F0EDE8",
        "card":                 "#FFFFFF",
        "white":                "#FFFFFF",
        "text_dark":            "#1A1A1A",
        "text_mid":             "#444444",
        "text_grey":            "#717171",
        "text_light":           "#9E9E9E",
        "border":               "#E5E0D8",
        "success":              "#2E7D32",
        "success_bg":           "#F1FBF3",
        "success_dark":         "#1B5E20",
        "error":                "#B02029",
        "error_bg":             "#FFF5F7",
        "row_alt":              "#FCFCFC",
    }
    FONTS = {
        "heading":    ("Poppins", 15, "bold"),
        "subheading": ("Poppins", 11),
        "section":    ("Poppins", 13, "bold"),
        "body":       ("Poppins", 10),
        "body_bold":  ("Poppins", 10, "bold"),
        "small":      ("Poppins", 9),
        "small_bold": ("Poppins", 9, "bold"),
        "button":     ("Poppins", 9, "bold"),
        "table_head": ("Poppins", 9, "bold"),
        "table_body": ("Poppins", 10),
        "modal_title":("Poppins", 14, "bold"),
        "tag":        ("Poppins", 8, "bold"),
    }


# ── Helpers ────────────────────────────────────────────────────────────────

def _rounded_button(parent, text, command, bg, fg, hover_bg,
                    font=None, padx=14, pady=6, width=None):
    kw = dict(
        text=text, command=command,
        bg=bg, fg=fg,
        activebackground=hover_bg, activeforeground=fg,
        relief="flat", bd=0, cursor="hand2",
        font=font or FONTS["button"],
        padx=padx, pady=pady,
    )
    if width:
        kw["width"] = width
    btn = tk.Button(parent, **kw)

    def on_enter(_): btn.config(bg=hover_bg)
    def on_leave(_): btn.config(bg=bg)
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


# ── Confirmation modal ─────────────────────────────────────────────────────

class _ConfirmModal(tk.Toplevel):
    def __init__(self, master, title, message, confirm_text,
                 on_confirm, btn_bg=None, btn_hover=None):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.title(title)
        self.configure(bg=COLORS["background"])
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        width, height = 400, 220
        self.update_idletasks()
        px = master.winfo_rootx() + master.winfo_width()  // 2 - width  // 2
        py = master.winfo_rooty() + master.winfo_height() // 2 - height // 2
        self.geometry(f"{width}x{height}+{px}+{py}")

        card = tk.Frame(self, bg=COLORS["card"],
                        highlightthickness=1,
                        highlightbackground=COLORS["border"])
        card.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(card, text=title, font=FONTS["modal_title"],
                 bg=COLORS["card"], fg=COLORS["primary_orange"],
                 anchor="w").pack(fill="x", padx=18, pady=(16, 2))

        ttk.Separator(card, orient="horizontal").pack(fill="x", padx=18)

        tk.Label(card, text=message, font=FONTS["body"],
                 bg=COLORS["card"], fg=COLORS["text_mid"],
                 wraplength=340, justify="left", anchor="w",
                 ).pack(fill="x", padx=18, pady=(12, 4))

        row = tk.Frame(card, bg=COLORS["card"])
        row.pack(fill="x", padx=18, pady=(12, 16))

        _rounded_button(row, "Cancel", self.destroy,
                        bg="#F1F1F1", fg="#555555",
                        hover_bg="#E2E2E2").pack(side="right", padx=(6, 0))

        bg_  = btn_bg    or COLORS["primary_orange"]
        hov_ = btn_hover or COLORS["primary_orange_dark"]
        _rounded_button(row, confirm_text,
                        lambda: [on_confirm(), self.destroy()],
                        bg=bg_, fg=COLORS["white"],
                        hover_bg=hov_).pack(side="right")


# ── ManageUsers page ───────────────────────────────────────────────────────

class ManageUsers(SuperadminLayout):
    """
    Superadmin page: Manage User Accounts.

    Inherits the full chrome (header, orange bar, sidebar, scrollable shell)
    from SuperadminLayout and only builds the page-specific content inside
    self.inner.
    """

    ACTIVE_NAV = "manage_users"

    TAB_PENDING  = "pending"
    TAB_ACCEPTED = "accepted"
    TAB_REJECTED = "rejected"

    def __init__(self, root, user=None, db_callbacks=None):
        # SuperadminLayout.__init__ builds the chrome and sets self.inner
        super().__init__(root, user, db_callbacks)

        self._active_tab = self.TAB_PENDING
        self._pending:  list = []
        self._accepted: list = []
        self._rejected: list = []

        self._build_page()

    # ══════════════════════════════════════════════════════════════════════
    #  Page construction  (populates self.inner)
    # ══════════════════════════════════════════════════════════════════════

    def _build_page(self):
        """Called by __init__ (and again by _rebuild_chrome on theme toggle)."""
        # Reset tab state so a theme rebuild starts fresh
        self._active_tab = getattr(self, "_active_tab", self.TAB_PENDING)

        self._build_page_header()
        self._build_table_card()
        self._load_users()

    # ── Page header + tab switcher ─────────────────────────────────────────

    def _build_page_header(self):
        T   = self.theme
        row = tk.Frame(self.inner, bg=T["background"])
        row.pack(fill="x", pady=(0, 8))

        left = tk.Frame(row, bg=T["background"])
        left.pack(side="left")
        tk.Label(
            left, text="MANAGE USER ACCOUNTS",
            font=FONTS["heading"],
            bg=T["background"], fg=T["primary_orange"],
        ).pack(anchor="w")
        tk.Label(
            left, text="Control comment access and user visibility.",
            font=FONTS["subheading"],
            bg=T["background"], fg=T["text_grey"],
        ).pack(anchor="w", pady=(2, 0))

        tab_frame = tk.Frame(row, bg=T["background"])
        tab_frame.pack(side="right", pady=4)

        self._tab_btns: dict[str, tk.Button] = {}
        for key, label in [
            (self.TAB_PENDING,  "Pending"),
            (self.TAB_ACCEPTED, "Accepted"),
            (self.TAB_REJECTED, "Rejected"),
        ]:
            btn = tk.Button(
                tab_frame, text=label,
                font=FONTS["button"], relief="flat", bd=0,
                cursor="hand2", padx=14, pady=6,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._tab_btns[key] = btn

        self._refresh_tab_styles()

    # ── Table card ─────────────────────────────────────────────────────────

    def _build_table_card(self):
        T = self.theme
        self._table_card = tk.Frame(
            self.inner, bg=T["card"],
            highlightthickness=1, highlightbackground=T["border"],
        )
        self._table_card.pack(fill="both", expand=True, pady=(4, 0))
        self._rebuild_table()

    def _rebuild_table(self):
        """Destroy and recreate table contents for the active tab."""
        for w in self._table_card.winfo_children():
            w.destroy()

        T   = self.theme
        tab = self._active_tab

        if tab == self.TAB_PENDING:
            title = "Pending Comment Access"
            data  = self._pending
        elif tab == self.TAB_ACCEPTED:
            title = "Accepted Users (Can Comment)"
            data  = self._accepted
        else:
            title = "Rejected Users (View Only)"
            data  = self._rejected

        # Card header
        hdr = tk.Frame(self._table_card, bg=T["background_alt"])
        hdr.pack(fill="x")

        left_hdr = tk.Frame(hdr, bg=T["background_alt"])
        left_hdr.pack(side="left", padx=18, pady=10)
        tk.Label(
            left_hdr, text=title, font=FONTS["section"],
            bg=T["background_alt"], fg=T["text_dark"],
        ).pack(anchor="w")

        self._badge_var = tk.StringVar(
            value=f"{len(data)} user{'s' if len(data) != 1 else ''}")
        tk.Label(
            hdr, textvariable=self._badge_var,
            font=FONTS["tag"],
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            relief="flat", padx=10, pady=4,
        ).pack(side="right", padx=18)

        ttk.Separator(self._table_card, orient="horizontal").pack(fill="x")

        # Treeview
        cols = ("full_name", "email", "email_status", "comment_status")
        self._tree = ttk.Treeview(
            self._table_card, columns=cols,
            show="headings", selectmode="browse",
        )

        col_cfg = {
            "full_name":      ("Full Name",      200),
            "email":          ("Email",           240),
            "email_status":   ("Email Status",    130),
            "comment_status": ("Comment Status",  130),
        }
        for c, (lbl, w) in col_cfg.items():
            self._tree.heading(c, text=lbl)
            self._tree.column(c, width=w, minwidth=60,
                              stretch=(c == "email"))

        style = ttk.Style()
        style.configure(
            "Treeview",
            font=FONTS["table_body"], rowheight=32,
            background=T["card"], fieldbackground=T["card"],
            foreground=T["text_dark"],
        )
        style.configure(
            "Treeview.Heading",
            font=FONTS["table_head"],
            background=T["background_alt"], foreground=T["text_grey"],
        )
        style.map(
            "Treeview",
            background=[("selected", T["primary_orange_light"])],
            foreground=[("selected", T["text_dark"])],
        )

        self._tree.tag_configure("even", background=COLORS["row_alt"])
        self._tree.tag_configure("odd",  background=T["card"])

        vsb = ttk.Scrollbar(self._table_card, orient="vertical",
                             command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        # Populate rows
        for i, u in enumerate(data):
            full   = f"{u[1]} {u[2]}".strip()
            email  = u[3]
            ev     = "✔ Verified" if u[4] else "✘ Not Verified"
            status = tab.capitalize()
            tag    = "even" if i % 2 == 0 else "odd"
            self._tree.insert(
                "", "end", iid=str(u[0]),
                values=(full, email, ev, status),
                tags=(tag,),
            )

        # Actions toolbar
        self._actions_bar = tk.Frame(self._table_card, bg=T["background"])
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
            font=FONTS["small"], bg=T["background"], fg=T["text_light"],
        )
        self._no_sel_label.pack(side="left")

        self._btn_accept = _rounded_button(
            self._actions_bar, "✔ Accept", self._on_accept,
            bg=COLORS["success"], fg=COLORS["white"],
            hover_bg=COLORS["success_dark"],
        )
        self._btn_reject = _rounded_button(
            self._actions_bar, "✕ Reject", self._on_reject,
            bg=COLORS["error"], fg=COLORS["white"],
            hover_bg=COLORS["primary_red_dark"],
        )
        for btn in (self._btn_accept, self._btn_reject):
            btn.pack_forget()

    # ══════════════════════════════════════════════════════════════════════
    #  Data
    # ══════════════════════════════════════════════════════════════════════

    def _load_users(self):
        try:
            self._pending  = self.callbacks.get("fetch_pending_users",  lambda: [])() or []
            self._accepted = self.callbacks.get("fetch_accepted_users", lambda: [])() or []
            self._rejected = self.callbacks.get("fetch_rejected_users", lambda: [])() or []
        except Exception as exc:
            messagebox.showerror("DB Error", str(exc))
            self._pending = self._accepted = self._rejected = []

        self._refresh_tab_counts()
        self._rebuild_table()

    def _refresh_tab_counts(self):
        self._tab_btns[self.TAB_PENDING].config(
            text=f"Pending ({len(self._pending)})")
        self._tab_btns[self.TAB_ACCEPTED].config(
            text=f"Accepted ({len(self._accepted)})")
        self._tab_btns[self.TAB_REJECTED].config(
            text=f"Rejected ({len(self._rejected)})")

    def _switch_tab(self, key: str):
        self._active_tab = key
        self._refresh_tab_styles()
        self._rebuild_table()

    def _refresh_tab_styles(self):
        T = self.theme
        for key, btn in self._tab_btns.items():
            if key == self._active_tab:
                btn.config(bg=T["tab_active"], fg=T["white"])
            else:
                btn.config(bg=T["background"], fg=T["tab_inactive_fg"])

    # ── Row selection ──────────────────────────────────────────────────────

    def _selected_user(self):
        sel = self._tree.selection()
        if not sel:
            return None
        uid = int(sel[0])
        for u in self._pending + self._accepted + self._rejected:
            if u[0] == uid:
                return u
        return None

    def _on_row_select(self, _=None):
        user = self._selected_user()
        self._no_sel_label.pack_forget()
        self._btn_accept.pack_forget()
        self._btn_reject.pack_forget()

        if user is None:
            self._no_sel_label.pack(side="left")
            return

        tab = self._active_tab
        if tab == self.TAB_PENDING:
            self._btn_accept.config(text="✔ Accept")
            self._btn_accept.pack(side="left", padx=(0, 6))
            self._btn_reject.config(text="✕ Reject")
            self._btn_reject.pack(side="left", padx=(0, 6))
        elif tab == self.TAB_ACCEPTED:
            self._btn_reject.config(text="↓ Set to View Only")
            self._btn_reject.pack(side="left", padx=(0, 6))
        elif tab == self.TAB_REJECTED:
            self._btn_accept.config(text="✔ Accept Again")
            self._btn_accept.pack(side="left", padx=(0, 6))

    # ── Action handlers ────────────────────────────────────────────────────

    def _on_accept(self):
        user = self._selected_user()
        if not user:
            return
        name = f"{user[1]} {user[2]}".strip()
        msg  = (
            f'Accept "{name}" and allow commenting?'
            if self._active_tab == self.TAB_PENDING
            else f'Accept "{name}" again and allow commenting?'
        )
        _ConfirmModal(
            self.root, "Accept User", msg, "Yes, Accept",
            on_confirm=lambda: self._do_accept(user[0]),
            btn_bg=COLORS["success"], btn_hover=COLORS["success_dark"],
        )

    def _do_accept(self, user_id):
        cb = self.callbacks.get("accept_user")
        if cb and cb(user_id):
            self._load_users()
        else:
            messagebox.showerror("Error", "Failed to accept user.")

    def _on_reject(self):
        user = self._selected_user()
        if not user:
            return
        name = f"{user[1]} {user[2]}".strip()
        msg  = (
            f'Reject "{name}" and set to view-only?'
            if self._active_tab == self.TAB_PENDING
            else f'Set "{name}" to view-only?'
        )
        _ConfirmModal(
            self.root, "Reject User", msg, "Yes, Reject",
            on_confirm=lambda: self._do_reject(user[0]),
            btn_bg=COLORS["error"], btn_hover=COLORS["primary_red_dark"],
        )

    def _do_reject(self, user_id):
        cb = self.callbacks.get("reject_user")
        if cb and cb(user_id):
            self._load_users()
        else:
            messagebox.showerror("Error", "Failed to reject user.")


# ── Quick standalone test ──────────────────────────────────────────────────

if __name__ == "__main__":
    SAMPLE_PENDING = [
        (1, "Ana",  "Reyes",  "ana@mail.com",  1),
        (2, "Ben",  "Santos", "ben@mail.com",  0),
    ]
    SAMPLE_ACCEPTED = [
        (3, "Cara", "Tan",    "cara@mail.com", 1),
        (4, "Dan",  "Cruz",   "dan@mail.com",  1),
    ]
    SAMPLE_REJECTED = [
        (5, "Eve",  "Lim",    "eve@mail.com",  0),
    ]

    callbacks = {
        "fetch_pending_users":  lambda: SAMPLE_PENDING,
        "fetch_accepted_users": lambda: SAMPLE_ACCEPTED,
        "fetch_rejected_users": lambda: SAMPLE_REJECTED,
        "accept_user": lambda uid: (print(f"[accept] {uid}"), True)[1],
        "reject_user": lambda uid: (print(f"[reject] {uid}"), True)[1],
    }

    root = tk.Tk()
    root.title("The Gears – Manage Users")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    ManageUsers(
        root,
        user=("Francis Jane", "Olvido", "admin@gears.com", 1, "superadmin"),
        db_callbacks=callbacks,
    )
    root.mainloop()