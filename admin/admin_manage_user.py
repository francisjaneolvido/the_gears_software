"""
admin/admin_manage_user.py
───────────────────────────
Manage Users page for The Gears Admin panel.

Inherits the full header + sidebar + scrollable shell from AdminLayout.
Only the user management table and its logic live here.

User tuple format (5 fields):
  (id, first_name, last_name, email, email_verified)
    0       1           2        3         4

db_callbacks keys:
  fetch_pending_users()   → list[(id, first, last, email, email_verified)]
  fetch_accepted_users()  → same
  fetch_rejected_users()  → same
  accept_user(user_id)    → bool
  reject_user(user_id)    → bool
"""

import tkinter as tk
from tkinter import ttk, messagebox

from admin.admin_layout import AdminLayout, FONTS, COLORS

DARK_COLORS = {
    **COLORS,
    "background":           "#141414",
    "background_alt":       "#1A1A1A",
    "card":                 "#1F1F1F",
    "text_dark":            "#F0F0F0",
    "text_mid":             "#D0D0D0",
    "text_grey":            "#A0A0A0",
    "text_light":           "#787878",
    "border":               "#2E2219",
    "input_bg":             "#252525",
    "primary_orange_light": "#3A2210",
    "row_alt":              "#252525",
    "white":                "#FFFFFF",
    "tab_active":           "#F19421",
    "tab_inactive_fg":      "#A0A0A0",
    "success":              "#2E7D32",
    "success_dark":         "#1B5E20",
    "error":                "#B02029",
    "primary_red_dark":     "#8E1A21",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

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


class _ConfirmModal(tk.Toplevel):
    def __init__(self, master, title, message, confirm_text,
                 on_confirm, btn_bg=None, btn_hover=None, theme=None):
        super().__init__(master)
        T = theme or COLORS
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.title(title)
        self.configure(bg=T["background"])
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        width = 400
        self.update_idletasks()
        px = master.winfo_rootx() + master.winfo_width()  // 2 - width // 2
        py = master.winfo_rooty() + master.winfo_height() // 2 - 100
        self.geometry(f"{width}x220+{px}+{py}")

        card = tk.Frame(self, bg=T["card"],
                        highlightthickness=1, highlightbackground=T["border"])
        card.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(card, text=title, font=FONTS["modal_title"],
                 bg=T["card"], fg=T["primary_orange"],
                 anchor="w").pack(fill="x", padx=18, pady=(16, 2))
        tk.Frame(card, bg=T["border"], height=1).pack(fill="x", padx=18, pady=(0, 6))
        tk.Label(card, text=message, font=FONTS["body"],
                 bg=T["card"], fg=T["text_mid"],
                 wraplength=340, justify="left", anchor="w"
                 ).pack(fill="x", padx=18, pady=(6, 4))

        row = tk.Frame(card, bg=T["card"])
        row.pack(fill="x", padx=18, pady=(12, 16))

        _rounded_button(row, "Cancel", self.destroy,
                        bg=T["background_alt"], fg=T["text_mid"],
                        hover_bg=T["border"]).pack(side="right", padx=(6, 0))

        _rounded_button(row, confirm_text,
                        lambda: [on_confirm(), self.destroy()],
                        bg=btn_bg or T["primary_orange"],
                        fg=T["white"],
                        hover_bg=btn_hover or T["primary_orange_dark"]
                        ).pack(side="right")


# ─────────────────────────────────────────────────────────────────────────────
class AdminManageUsers(AdminLayout):

    ACTIVE_NAV = "manage_users"

    TAB_PENDING  = "pending"
    TAB_ACCEPTED = "accepted"
    TAB_REJECTED = "rejected"

    def __init__(self, root, user=None, db_callbacks=None):
        self._active_tab = self.TAB_PENDING
        self._pending:  list = []
        self._accepted: list = []
        self._rejected: list = []

        super().__init__(root, user, db_callbacks)
        self._build_page()
        self._load_users()

    # ── Page content ──────────────────────────────────────────────────────────

    def _build_page(self):
        self._build_page_header()
        self._build_table_card()

    # ── Page header ───────────────────────────────────────────────────────────

    def _build_page_header(self):
        T   = self.theme
        row = tk.Frame(self.inner, bg=T["background"])
        row.pack(fill="x", pady=(0, 10))

        left = tk.Frame(row, bg=T["background"])
        left.pack(side="left")
        tk.Label(left, text="MANAGE USER ACCOUNTS",
                 font=FONTS["heading"], bg=T["background"],
                 fg=T["primary_orange"]).pack(anchor="w")
        tk.Label(left, text="Control comment access and user visibility.",
                 font=FONTS.get("subheading", ("Poppins", 11)),
                 bg=T["background"], fg=T["text_grey"]).pack(anchor="w", pady=(2, 0))

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

    # ── Table card ────────────────────────────────────────────────────────────

    def _build_table_card(self):
        T = self.theme
        self._table_card = tk.Frame(
            self.inner, bg=T["card"],
            highlightthickness=1, highlightbackground=T["border"],
        )
        self._table_card.pack(fill="both", expand=True, pady=(4, 0))
        self._rebuild_table()

    def _rebuild_table(self):
        T = self.theme
        for w in self._table_card.winfo_children():
            w.destroy()

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

        lh = tk.Frame(hdr, bg=T["background_alt"])
        lh.pack(side="left", padx=18, pady=10)
        tk.Label(lh, text=title, font=FONTS["section"],
                 bg=T["background_alt"], fg=T["text_dark"]).pack(anchor="w")

        tk.Label(hdr,
                 text=f"{len(data)} user{'s' if len(data) != 1 else ''}",
                 font=FONTS["tag"],
                 bg=T["primary_orange_light"], fg=T["primary_orange"],
                 relief="flat", padx=10, pady=4
                 ).pack(side="right", padx=18, pady=10)

        tk.Frame(self._table_card, bg=T["border"], height=1).pack(fill="x")

        # Treeview
        style      = ttk.Style()
        style_name = "Dark.Treeview" if self.dark_mode else "Treeview"

        if self.dark_mode:
            style.configure("Dark.Treeview",
                            font=FONTS["table_body"], rowheight=32,
                            background=T["card"], fieldbackground=T["card"],
                            foreground=T["text_dark"])
            style.configure("Dark.Treeview.Heading",
                            font=FONTS["table_head"],
                            background=T["background_alt"],
                            foreground=T["text_grey"])
            style.map("Dark.Treeview",
                      background=[("selected", T["primary_orange_light"])],
                      foreground=[("selected", T["text_dark"])])
        else:
            style.configure("Treeview",
                            font=FONTS["table_body"], rowheight=32,
                            background=T["card"], fieldbackground=T["card"],
                            foreground=T["text_dark"])
            style.configure("Treeview.Heading",
                            font=FONTS["table_head"],
                            background=T["background_alt"],
                            foreground=T["text_grey"])
            style.map("Treeview",
                      background=[("selected", T["primary_orange_light"])],
                      foreground=[("selected", T["text_dark"])])

        cols = ("full_name", "email", "email_status", "comment_status")
        self._tree = ttk.Treeview(self._table_card, columns=cols,
                                  show="headings", selectmode="browse",
                                  style=style_name)

        col_cfg = {
            "full_name":      ("Full Name",     200),
            "email":          ("Email",          240),
            "email_status":   ("Email Status",   130),
            "comment_status": ("Comment Status", 130),
        }
        for c, (lbl, w) in col_cfg.items():
            self._tree.heading(c, text=lbl)
            self._tree.column(c, width=w, minwidth=60, stretch=(c == "email"))

        row_alt = T.get("row_alt", T["background_alt"])
        self._tree.tag_configure("even", background=row_alt)
        self._tree.tag_configure("odd",  background=T["card"])

        tsb = tk.Scrollbar(self._table_card, orient="vertical",
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=tsb.set)
        tsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        for i, u in enumerate(data):
            full   = f"{u[1]} {u[2]}".strip()
            email  = u[3]
            ev     = "✔ Verified" if u[4] else "✘ Not Verified"
            status = tab.capitalize()
            tag    = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end", iid=str(u[0]),
                              values=(full, email, ev, status), tags=(tag,))

        # Actions bar
        self._actions_bar = tk.Frame(self._table_card, bg=T["background_alt"])
        self._actions_bar.pack(fill="x", padx=18, pady=10)
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
            bg=T["background_alt"],
            fg=T["text_light"],
        )
        self._no_sel_label.pack(side="left")

        self._btn_accept = _rounded_button(
            self._actions_bar, "✔ Accept", self._on_accept,
            bg=COLORS["success"],       fg=COLORS["white"],
            hover_bg=COLORS.get("success_dark", "#1B5E20"),
        )
        self._btn_reject = _rounded_button(
            self._actions_bar, "✕ Reject", self._on_reject,
            bg=COLORS["primary_red"],   fg=COLORS["white"],
            hover_bg=COLORS.get("primary_red_dark", "#8E1A21"),
        )
        for btn in (self._btn_accept, self._btn_reject):
            btn.pack_forget()

    # ── Data ──────────────────────────────────────────────────────────────────

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
        self._refresh_tab_styles()

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
                btn.config(bg=T["background"], fg=T.get("tab_inactive_fg", T["text_grey"]))

    # ── Row selection ─────────────────────────────────────────────────────────

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
            self._btn_accept.pack(side="left", padx=(0, 6))
            self._btn_reject.config(text="✕ Reject")
            self._btn_reject.pack(side="left", padx=(0, 6))
        elif tab == self.TAB_ACCEPTED:
            self._btn_reject.config(text="↓ Set to View Only")
            self._btn_reject.pack(side="left", padx=(0, 6))
        elif tab == self.TAB_REJECTED:
            self._btn_accept.config(text="✔ Accept Again")
            self._btn_accept.pack(side="left", padx=(0, 6))

    # ── Action handlers ───────────────────────────────────────────────────────

    def _on_accept(self):
        user = self._selected_user()
        if not user:
            return
        name = f"{user[1]} {user[2]}".strip()
        msg  = (f'Accept "{name}" and allow commenting?'
                if self._active_tab == self.TAB_PENDING
                else f'Accept "{name}" again and allow commenting?')
        _ConfirmModal(
            self.root, "Accept User", msg, "Yes, Accept",
            on_confirm=lambda: self._do_accept(user[0]),
            btn_bg=COLORS["success"],
            btn_hover=COLORS.get("success_dark", "#1B5E20"),
            theme=self.theme,
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
        msg  = (f'Reject "{name}" and set to view-only?'
                if self._active_tab == self.TAB_PENDING
                else f'Set "{name}" to view-only?')
        _ConfirmModal(
            self.root, "Reject User", msg, "Yes, Reject",
            on_confirm=lambda: self._do_reject(user[0]),
            btn_bg=COLORS["primary_red"],
            btn_hover=COLORS.get("primary_red_dark", "#8E1A21"),
            theme=self.theme,
        )

    def _do_reject(self, user_id):
        cb = self.callbacks.get("reject_user")
        if cb and cb(user_id):
            self._load_users()
        else:
            messagebox.showerror("Error", "Failed to reject user.")


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    SAMPLE = {
        "pending":  [(1, "Ana",  "Reyes",  "ana@mail.com",  1),
                     (2, "Ben",  "Santos", "ben@mail.com",  0)],
        "accepted": [(3, "Cara", "Tan",    "cara@mail.com", 1)],
        "rejected": [(4, "Dan",  "Cruz",   "dan@mail.com",  0)],
    }

    cbs = {
        "fetch_pending_users":  lambda: SAMPLE["pending"],
        "fetch_accepted_users": lambda: SAMPLE["accepted"],
        "fetch_rejected_users": lambda: SAMPLE["rejected"],
        "accept_user": lambda uid: (print(f"[accept] {uid}"), True)[1],
        "reject_user": lambda uid: (print(f"[reject] {uid}"), True)[1],
    }

    root = tk.Tk()
    root.title("The Gears — Admin Manage Users")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    AdminManageUsers(
        root,
        user=("Maria", "Santos", "maria@gears.com", 1, "admin"),
        db_callbacks=cbs,
    )
    root.mainloop()