"""
superadmin/superadmin_manage_admins.py
───────────────────────────────────────
Manage Admins page — inherits full chrome from SuperadminLayout.

Role hierarchy:
  is_eic = 1  →  Editor-in-Chief / founding superadmin
                 Can do EVERYTHING: create, edit, disable/enable,
                 promote/demote EB.

  is_editorial = 1, role = 'superadmin', is_eic = 0
               →  Promoted Editorial Board member.
                 Can edit their own profile, but CANNOT
                 promote or demote other admins (that's EIC-only).
                 In this page they can Edit admins but NOT
                 promote/demote/disable/enable other admins.

  role = 'admin', is_editorial = 0, is_eic = 0
               →  Regular admin. No special privileges here.

Admin tuple format (10 fields):
  (id, username, email, first_name, middle_name, last_name,
   is_active, is_editorial, role, is_eic)
    0    1         2      3          4             5
    6          7             8      9

db_callbacks keys:
  fetch_admins, create_admin, update_admin,
  disable_admin, enable_admin,
  promote_eb, demote_eb
"""

import tkinter as tk
from tkinter import ttk, messagebox

from superadmin.superadmin_layout import SuperadminLayout
from superadmin.superadmin_create_admin_modal import (
    CreateAdminModal,
    EditAdminModal,
    ConfirmModal,
    _generate_password,
    _rounded_button,
)

try:
    from theme import COLORS, FONTS
except ImportError:
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
        "shadow":               "#DED6CF",
        "navy":                 "#0C1633",
        "success":              "#2E7D32",
        "success_dark":         "#1B5E20",
        "error":                "#B02029",
        "promote_blue":         "#1976D2",
        "promote_blue_dark":    "#0D47A1",
        "demote_brown":         "#6D4C41",
        "demote_brown_dark":    "#4E342E",
        "input_bg":             "#F5F3F0",
        "tab_active":           "#F19421",
        "tab_inactive_fg":      "#777777",
        "row_alt":              "#FCFCFC",
        "row_hover":            "#F7F7F7",
        "info_bg":              "#FFF8E6",
        "info_border":          "#FFECB3",
        "info_text":            "#8A6D3B",
    }
    FONTS = {
        "heading":     ("Poppins", 15, "bold"),
        "subheading":  ("Poppins", 11),
        "section":     ("Poppins", 13, "bold"),
        "body":        ("Poppins", 10),
        "body_bold":   ("Poppins", 10, "bold"),
        "small":       ("Poppins", 9),
        "small_bold":  ("Poppins", 9, "bold"),
        "button":      ("Poppins", 9, "bold"),
        "table_head":  ("Poppins", 9, "bold"),
        "table_body":  ("Poppins", 10),
        "modal_title": ("Poppins", 14, "bold"),
        "input":       ("Poppins", 10),
        "tag":         ("Poppins", 8, "bold"),
        "card_title":  ("Poppins", 11, "bold"),
    }

# ── Page-specific colours not in theme.py ─────────────────────────────────────
_INFO_BG      = "#FFF8E6"
_INFO_BORDER  = "#FFECB3"
_INFO_TEXT    = "#8A6D3B"
_SUCCESS      = "#2E7D32"
_SUCCESS_DARK = "#1B5E20"
_PROMOTE_BG   = "#1976D2"
_PROMOTE_DARK = "#0D47A1"
_DEMOTE_BG    = "#6D4C41"
_DEMOTE_DARK  = "#4E342E"
_ERROR_DARK   = "#8E1A21"
_ROW_ALT      = "#FCFCFC"
_TAB_INACTIVE = "#777777"


# ─────────────────────────────────────────────────────────────────────────────
class ManageAdmins(SuperadminLayout):

    ACTIVE_NAV = "manage_admins"

    TAB_ACTIVE    = "active"
    TAB_DISABLED  = "disabled"
    TAB_EDITORIAL = "editorial"

    def __init__(self, root, user=None, db_callbacks=None):
        self._admins: list = []
        self._active_tab   = self.TAB_ACTIVE

        # ── Determine if the currently logged-in superadmin is the EIC ───────
        # user tuple: (first, last, email, id, role, is_eic, ...)
        # SuperadminLayout stores user as self.user — read is_eic from index 5
        # if available, otherwise default False (non-EIC superadmin).
        _is_eic_raw = user[5] if user and len(user) > 5 else False
        self._current_is_eic: bool = bool(_is_eic_raw)

        super().__init__(root, user, db_callbacks)
        self._build_page()
        self._load_admins()

    # =========================================================================
    # Page hook
    # =========================================================================

    def _build_page(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self._build_page_header(self.inner)
        self._build_info_box(self.inner)
        self._build_tabs(self.inner)
        self._build_table_card(self.inner)

    # =========================================================================
    # Page content builders
    # =========================================================================

    def _build_page_header(self, parent):
        T   = self.theme
        row = tk.Frame(parent, bg=T["background"])
        row.pack(fill="x", pady=(0, 4))

        left = tk.Frame(row, bg=T["background"])
        left.pack(side="left")

        tk.Label(
            left, text="MANAGE ADMIN ACCOUNTS",
            font=FONTS["heading"],
            bg=T["background"], fg=T["primary_orange"],
        ).pack(anchor="w")
        tk.Label(
            left,
            text="Create, edit, and manage admin accounts for The Gears.",
            font=FONTS["subheading"],
            bg=T["background"], fg=T["text_grey"],
        ).pack(anchor="w", pady=(2, 0))

        # Only EIC can create new admins
        # Only EIC can create new admins
        _rounded_button(
            row, "+ Add New Admin", self._open_create_modal,
            bg=T["primary_orange"], fg=T["white"],
            hover_bg=T["primary_orange_dark"],
        ).pack(side="right", pady=4)

    def _build_info_box(self, parent):
        """Yellow info box shown after a new admin is created."""
        self._info_frame = tk.Frame(
            parent, bg=_INFO_BG,
            highlightthickness=1,
            highlightbackground=_INFO_BORDER,
        )
        self._info_label = tk.Label(
            self._info_frame, text="",
            font=FONTS["body"],
            bg=_INFO_BG, fg=_INFO_TEXT,
            justify="left", anchor="w", wraplength=900,
        )
        self._info_label.pack(fill="x", padx=12, pady=8)
        # starts hidden

    def _build_tabs(self, parent):
        T       = self.theme
        tab_bar = tk.Frame(parent, bg=T["background"])
        tab_bar.pack(fill="x", pady=(8, 4))

        self._tab_btns: dict[str, tk.Button] = {}
        tabs = [
            (self.TAB_ACTIVE,    "Active"),
            (self.TAB_DISABLED,  "Disabled"),
            (self.TAB_EDITORIAL, "Editorial Board"),
        ]
        for key, label in tabs:
            btn = tk.Button(
                tab_bar, text=label,
                font=FONTS["button"], relief="flat", bd=0,
                cursor="hand2", padx=14, pady=6,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 6))
            self._tab_btns[key] = btn

        self._refresh_tab_styles()

    def _build_table_card(self, parent):
        T    = self.theme
        card = tk.Frame(
            parent, bg=T["card"],
            highlightthickness=1,
            highlightbackground=T["border"],
        )
        card.pack(fill="both", expand=True, pady=(6, 0))
        self._table_card = card

        # Card header
        hdr = tk.Frame(card, bg="#FAFAFA")
        hdr.pack(fill="x")

        left_hdr = tk.Frame(hdr, bg="#FAFAFA")
        left_hdr.pack(side="left", padx=18, pady=10)
        tk.Label(
            left_hdr, text="Admin List",
            font=FONTS["section"],
            bg="#FAFAFA", fg=T["text_dark"],
        ).pack(anchor="w")
        tk.Label(
            left_hdr,
            text="All users with admin privileges in the system.",
            font=FONTS["small"],
            bg="#FAFAFA", fg=T["text_grey"],
        ).pack(anchor="w")

        self._badge_var = tk.StringVar(value="0 admins")
        tk.Label(
            hdr, textvariable=self._badge_var,
            font=FONTS["tag"],
            bg="#FFF3E4", fg=T["primary_orange"],
            relief="flat", padx=10, pady=4,
        ).pack(side="right", padx=18)

        ttk.Separator(card, orient="horizontal").pack(fill="x")

        # Treeview
        cols = ("full_name", "username", "email", "role", "status")
        self._tree = ttk.Treeview(card, columns=cols,
                                  show="headings", selectmode="browse")

        col_widths = {"full_name": 200, "username": 160,
                      "email": 220, "role": 90, "status": 80}
        col_labels = {"full_name": "Full Name", "username": "Username",
                      "email": "Email", "role": "Role", "status": "Status"}
        for c in cols:
            self._tree.heading(c, text=col_labels[c])
            self._tree.column(c, width=col_widths[c], minwidth=60,
                              stretch=(c == "email"))

        style = ttk.Style()
        style.configure("Treeview",
                        font=FONTS["table_body"], rowheight=32,
                        background=T["card"],
                        fieldbackground=T["card"],
                        foreground=T["text_dark"])
        style.configure("Treeview.Heading",
                        font=FONTS["table_head"],
                        background="#FCFCFC", foreground="#999999")
        style.map("Treeview",
                  background=[("selected", T["primary_orange_light"])],
                  foreground=[("selected", T["text_dark"])])

        self._tree.tag_configure("even", background=_ROW_ALT)
        self._tree.tag_configure("odd",  background=T["card"])

        scrollbar = ttk.Scrollbar(card, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self._actions_bar = tk.Frame(card, bg=T["background"])
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
            font=FONTS["small"], bg=T["background"],
            fg=T["text_light"],
        )
        self._no_sel_label.pack(side="left")

        # Edit is available to all superadmins (EIC and promoted EB)
        self._btn_edit    = _rounded_button(
            self._actions_bar, "✎ Edit",       self._on_edit,
            _SUCCESS,         T["white"], _SUCCESS_DARK)

        # The following buttons are EIC-only
        self._btn_disable = _rounded_button(
            self._actions_bar, "✕ Disable",    self._on_disable,
            T["primary_red"],  T["white"], _ERROR_DARK)
        self._btn_enable  = _rounded_button(
            self._actions_bar, "✓ Enable",     self._on_enable,
            _SUCCESS,          T["white"], _SUCCESS_DARK)
        self._btn_promote = _rounded_button(
            self._actions_bar, "↑ Promote EB", self._on_promote_eb,
            _PROMOTE_BG,       T["white"], _PROMOTE_DARK)
        self._btn_demote  = _rounded_button(
            self._actions_bar, "↓ Demote EB",  self._on_demote_eb,
            _DEMOTE_BG,        T["white"], _DEMOTE_DARK)

        for btn in (self._btn_edit, self._btn_disable, self._btn_enable,
                    self._btn_promote, self._btn_demote):
            btn.pack_forget()

    # =========================================================================
    # Data loading
    # =========================================================================

    def _load_admins(self):
        cb = self.callbacks.get("fetch_admins")
        if cb:
            try:
                self._admins = cb() or []
            except Exception as exc:
                messagebox.showerror("DB Error", str(exc))
                self._admins = []
        self._refresh_table()
        self._refresh_badge()

    # =========================================================================
    # Tab switching
    # =========================================================================

    def _switch_tab(self, key: str):
        self._active_tab = key
        self._refresh_tab_styles()
        self._refresh_table()
        self._tree.selection_remove(self._tree.selection())
        self._update_action_buttons(None)

    def _refresh_tab_styles(self):
        for key, btn in self._tab_btns.items():
            if key == self._active_tab:
                btn.config(bg=COLORS["tab_active"], fg=COLORS["white"])
            else:
                btn.config(bg=self.theme["background"], fg=_TAB_INACTIVE)

    # =========================================================================
    # Table refresh
    # =========================================================================

    def _filtered_admins(self):
        result = []
        for a in self._admins:
            is_active    = bool(a[6])
            is_editorial = bool(a[7])
            if self._active_tab == self.TAB_ACTIVE:
                if is_active and not is_editorial:
                    result.append(a)
            elif self._active_tab == self.TAB_DISABLED:
                if not is_active:
                    result.append(a)
            elif self._active_tab == self.TAB_EDITORIAL:
                if is_active and is_editorial:
                    result.append(a)
        return result

    def _refresh_table(self):
        self._tree.delete(*self._tree.get_children())
        for i, a in enumerate(self._filtered_admins()):
            fn   = a[3] or ""
            mn   = a[4] or ""
            ln   = a[5] or ""
            full = f"{fn} {mn} {ln}".replace("  ", " ").strip()

            # Role label — show EB superadmin distinctly from EIC
            if a[9]:                          # is_eic
                role_lbl = "EIC"
            elif a[8] == "superadmin":        # promoted EB
                role_lbl = "EB Superadmin"
            else:
                role_lbl = "Admin"

            status_lbl = "Active" if a[6] else "Disabled"
            tag        = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end", iid=str(a[0]),
                              values=(full, a[1], a[2], role_lbl, status_lbl),
                              tags=(tag,))

    def _refresh_badge(self):
        total = len(self._admins)
        self._badge_var.set(f"{total} admin{'s' if total != 1 else ''}")
        active_ct    = sum(1 for a in self._admins if a[6] and not a[7])
        disabled_ct  = sum(1 for a in self._admins if not a[6])
        editorial_ct = sum(1 for a in self._admins if a[6] and a[7])
        self._tab_btns[self.TAB_ACTIVE].config(text=f"Active ({active_ct})")
        self._tab_btns[self.TAB_DISABLED].config(text=f"Disabled ({disabled_ct})")
        self._tab_btns[self.TAB_EDITORIAL].config(text=f"Editorial Board ({editorial_ct})")

    # =========================================================================
    # Row selection
    # =========================================================================

    def _selected_admin(self):
        sel = self._tree.selection()
        if not sel:
            return None
        iid = int(sel[0])
        for a in self._admins:
            if a[0] == iid:
                return a
        return None

    def _on_row_select(self, _event=None):
        self._update_action_buttons(self._selected_admin())

    def _update_action_buttons(self, admin):
        """
        Show/hide action buttons based on:
          1. Whether the currently logged-in user is EIC.
          2. The selected admin's own flags.

        Rules:
          • Edit           — any superadmin can edit any admin
                             EXCEPT: no one can edit the EIC account
          • Disable/Enable — EIC only; cannot disable the EIC account itself
          • Promote EB     — EIC only; target must be a plain active admin
          • Demote EB      — EIC only; target must be an EB member (non-EIC)
        """
        self._no_sel_label.pack_forget()
        for btn in (self._btn_edit, self._btn_disable, self._btn_enable,
                    self._btn_promote, self._btn_demote):
            btn.pack_forget()

        if admin is None:
            self._no_sel_label.pack(side="left")
            return

        target_is_active    = bool(admin[6])
        target_is_editorial = bool(admin[7])
        target_is_eic       = bool(admin[9])

        # Nobody can edit or action the EIC account
        if target_is_eic:
            self._no_sel_label.config(
                text="The EIC account cannot be modified.")
            self._no_sel_label.pack(side="left")
            return

        # ── Edit — available to all superadmins for non-EIC targets ──────────
        self._btn_edit.pack(side="left", padx=(0, 6))

        # ── EIC-only actions ─────────────────────────────────────────────────
        if not self._current_is_eic:
            # Non-EIC superadmin: show a note that further actions need EIC
            note = tk.Label(
                self._actions_bar,
                text="  Only the EIC can promote, demote, or disable admins.",
                font=FONTS["small"], bg=self.theme["background"],
                fg=self.theme["text_light"],
            )
            note.pack(side="left")
            # Store reference so we can clear it on next selection
            self._eic_note = note
            return

        # Clear any lingering EIC note from previous selection
        if hasattr(self, "_eic_note"):
            try:
                self._eic_note.destroy()
            except Exception:
                pass

        if target_is_active:
            self._btn_disable.pack(side="left", padx=(0, 6))
            if target_is_editorial:
                self._btn_demote.pack(side="left", padx=(0, 6))
            else:
                self._btn_promote.pack(side="left", padx=(0, 6))
        else:
            self._btn_enable.pack(side="left", padx=(0, 6))

    # =========================================================================
    # Action handlers
    # =========================================================================

    def _open_create_modal(self):
        CreateAdminModal(self.root, self._do_create_admin)

    def _do_create_admin(self, fn, mn, ln, em):
        cb = self.callbacks.get("create_admin")
        if not cb:
            messagebox.showerror("Error", "create_admin callback not set.")
            return
        pw     = _generate_password()
        new_id = cb(fn, mn, ln, em, pw)
        if new_id:
            self._show_info(
                f"✔  Admin created!  Generated password: {pw}   "
                "— Copy this and send it to the new admin. "
                "They will be asked to change it on first login."
            )
            self._load_admins()
        else:
            messagebox.showerror(
                "Error", "Failed to create admin. Check console for details.")

    def _show_info(self, msg: str):
        self._info_label.config(text=msg)
        self._info_frame.pack(fill="x", pady=(0, 8), before=self._table_card)

    def _on_edit(self):
        admin = self._selected_admin()
        if admin:
            EditAdminModal(self.root, admin, self._do_update_admin)

    def _do_update_admin(self, user_id, username, email):
        cb = self.callbacks.get("update_admin")
        if cb and cb(user_id, username, email):
            self._load_admins()
        else:
            messagebox.showerror("Error", "Failed to update admin.")

    # ── EIC-only below ────────────────────────────────────────────────────────

    def _on_disable(self):
        if not self._current_is_eic:
            return
        admin = self._selected_admin()
        if not admin:
            return
        ConfirmModal(
            self.root,
            title="Disable Admin",
            message=f'Are you sure you want to disable admin "{admin[1]}"?',
            confirm_text="Yes, Disable",
            on_confirm=lambda: self._do_disable(admin[0]),
            btn_bg=COLORS["error"],
            btn_hover=COLORS["primary_red_dark"],
        )

    def _do_disable(self, user_id):
        cb = self.callbacks.get("disable_admin")
        if cb and cb(user_id):
            self._load_admins()
        else:
            messagebox.showerror("Error", "Failed to disable admin.")

    def _on_enable(self):
        if not self._current_is_eic:
            return
        admin = self._selected_admin()
        if not admin:
            return
        ConfirmModal(
            self.root,
            title="Enable Admin",
            message=f'Are you sure you want to enable admin "{admin[1]}"?',
            confirm_text="Yes, Enable",
            on_confirm=lambda: self._do_enable(admin[0]),
        )

    def _do_enable(self, user_id):
        cb = self.callbacks.get("enable_admin")
        if cb and cb(user_id):
            self._load_admins()
        else:
            messagebox.showerror("Error", "Failed to enable admin.")

    def _on_promote_eb(self):
        if not self._current_is_eic:
            return
        admin = self._selected_admin()
        if not admin:
            return
        ConfirmModal(
            self.root,
            title="Promote to Editorial Board",
            message=(
                f'Promote "{admin[1]}" to Editorial Board?\n\n'
                "They will become a Superadmin but will NOT be able to "
                "promote or demote other admins — that remains EIC-only."
            ),
            confirm_text="Yes, Promote",
            on_confirm=lambda: self._do_promote_eb(admin[0]),
            btn_bg=COLORS["promote_blue"],
            btn_hover=COLORS["promote_blue_dark"],
        )

    def _do_promote_eb(self, user_id):
        cb = self.callbacks.get("promote_eb")
        if cb and cb(user_id):
            self._load_admins()
        else:
            messagebox.showerror("Error", "Failed to promote admin.")

    def _on_demote_eb(self):
        if not self._current_is_eic:
            return
        admin = self._selected_admin()
        if not admin:
            return
        ConfirmModal(
            self.root,
            title="Demote from Editorial Board",
            message=(
                f'Demote "{admin[1]}" from the Editorial Board?\n\n'
                "Their role will revert to Admin."
            ),
            confirm_text="Yes, Demote",
            on_confirm=lambda: self._do_demote_eb(admin[0]),
            btn_bg=COLORS["demote_brown"],
            btn_hover=COLORS["demote_brown_dark"],
        )

    def _do_demote_eb(self, user_id):
        cb = self.callbacks.get("demote_eb")
        if cb and cb(user_id):
            self._load_admins()
        else:
            messagebox.showerror("Error", "Failed to demote admin.")

    # =========================================================================
    # Navigation aliases  (show_* kept for backward compat)
    # =========================================================================

    def show_manage_admins(self):    self._go_manage_admins()
    def show_manage_users(self):     self._go_manage_users()
    def show_pending_articles(self): self._go_pending_articles()
    def show_categories(self):       self._go_categories()
    def show_activity_logs(self):    self._go_activity_logs()


# ── Quick standalone test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    SAMPLE_ADMINS = [
        # (id, uname, email, fn, mn, ln, is_active, is_editorial, role, is_eic)
        (1, "jdoe",   "jdoe@gears.com",   "John",  "A.", "Doe",   1, 0, "admin",      0),
        (2, "msmith", "msmith@gears.com", "Maria", "",   "Smith", 1, 1, "superadmin", 1),  # EIC
        (3, "rcruz",  "rcruz@gears.com",  "Rico",  "B.", "Cruz",  1, 0, "admin",      0),
        (4, "lreyes", "lreyes@gears.com", "Liza",  "",   "Reyes", 0, 0, "admin",      0),
        (5, "ktan",   "ktan@gears.com",   "Kevin", "C.", "Tan",   1, 1, "superadmin", 0),  # Promoted EB
    ]

    callbacks = {
        "fetch_admins":  lambda: SAMPLE_ADMINS,
        "create_admin":  lambda fn, mn, ln, em, pw: (
            print(f"[create] {fn} {ln} / {em} / {pw}"), 99)[1],
        "update_admin":  lambda uid, u, e: (
            print(f"[update] id={uid} {u} {e}"), True)[1],
        "disable_admin": lambda uid: (print(f"[disable] {uid}"), True)[1],
        "enable_admin":  lambda uid: (print(f"[enable]  {uid}"), True)[1],
        "promote_eb":    lambda uid: (print(f"[promo_eb] {uid}"), True)[1],
        "demote_eb":     lambda uid: (print(f"[demote_eb] {uid}"), True)[1],
    }

    root = tk.Tk()
    root.title("The Gears — Manage Admins (EIC view)")
    root.geometry("1100x700")
    root.minsize(800, 500)

    # Change is_eic (index 5) to False to test non-EIC superadmin view
    ManageAdmins(
        root,
        user=("Francis Jane", "Olvido", "admin@gears.com", 1, "superadmin", True),
        db_callbacks=callbacks,
    )
    root.mainloop()