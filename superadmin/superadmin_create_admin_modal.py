import tkinter as tk
from tkinter import ttk, messagebox
import string, secrets

# import shared theme
from theme import COLORS, FONTS


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.isupper() for c in pw)
                and any(c.islower() for c in pw)
                and any(c.isdigit() for c in pw)):
            return pw


def _rounded_button(parent, text, command, bg, fg, hover_bg,
                    font=None, padx=14, pady=6, width=None):
    """Flat button that simulates rounded pill style."""
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

class BaseModal(tk.Toplevel):
    """Shared modal frame: dimmed overlay + white card."""

    def __init__(self, master, title_text, subtitle_text, width=420):
        super().__init__(master)
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.title(title_text)
        self.configure(bg=COLORS["background"])
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.update_idletasks()
        px = master.winfo_rootx() + master.winfo_width() // 2 - width // 2
        py = master.winfo_rooty() + master.winfo_height() // 2 - 180
        self.geometry(f"{width}x520+{px}+{py}")

        card = tk.Frame(self, bg=COLORS["card"],
                        highlightthickness=1,
                        highlightbackground=COLORS["border"])
        card.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(card, text=title_text, font=FONTS["modal_title"],
                 bg=COLORS["card"], fg=COLORS["primary_orange"],
                 anchor="w").pack(fill="x", padx=18, pady=(16, 2))

        if subtitle_text:
            tk.Label(card, text=subtitle_text, font=FONTS["small"],
                     bg=COLORS["card"], fg=COLORS["text_grey"],
                     wraplength=width - 60, justify="left",
                     anchor="w").pack(fill="x", padx=18, pady=(0, 8))

        ttk.Separator(card, orient="horizontal").pack(fill="x", padx=18)

        self._card = card

    def _action_row(self):
        row = tk.Frame(self._card, bg=COLORS["card"])
        row.pack(fill="x", padx=18, pady=(12, 16))
        return row

    def _cancel_btn(self, row):
        return _rounded_button(
            row, "Cancel", self.destroy,
            bg="#F1F1F1", fg="#555555", hover_bg="#E2E2E2",
        )

    def _confirm_btn(self, row, text, command, bg=None, hover_bg=None):
        bg = bg or COLORS["primary_orange"]
        hover_bg = hover_bg or COLORS["primary_orange_dark"]
        return _rounded_button(row, text, command,
                               bg=bg, fg=COLORS["white"],
                               hover_bg=hover_bg)


# ── Confirmation modals ────────────────────────────────────────────────────

class ConfirmModal(BaseModal):
    def __init__(self, master, title, message, confirm_text,
                 on_confirm, btn_bg=None, btn_hover=None):
        super().__init__(master, title, "")
        tk.Label(self._card, text=message,
                 font=FONTS["body"], bg=COLORS["card"],
                 fg=COLORS["text_mid"], wraplength=360,
                 justify="left", anchor="w"
                 ).pack(fill="x", padx=18, pady=(12, 4))

        row = self._action_row()
        self._cancel_btn(row).pack(side="right", padx=(6, 0))
        self._confirm_btn(row, confirm_text,
                          lambda: [on_confirm(), self.destroy()],
                          bg=btn_bg, hover_bg=btn_hover
                          ).pack(side="right")


# ── Create Admin Modal ─────────────────────────────────────────────────────

class CreateAdminModal(BaseModal):
    def __init__(self, master, on_create):
        super().__init__(master,
                         "Add New Admin",
                         "Fill in the details to create a new admin account.")
        self._on_create = on_create
        self._build()

    def _field(self, label, required=True):
        tk.Label(self._card, text=label + (" *" if required else ""),
                 font=FONTS["label"], bg=COLORS["card"],
                 fg=COLORS["text_mid"], anchor="w"
                 ).pack(fill="x", padx=18, pady=(8, 0))
        var = tk.StringVar()
        e = tk.Entry(self._card, textvariable=var,
                     font=FONTS["input"], relief="solid", bd=1,
                     bg=COLORS["input_bg"],
                     highlightthickness=1,
                     highlightcolor=COLORS["primary_orange"],
                     highlightbackground=COLORS["border"])
        e.pack(fill="x", padx=18, pady=(2, 0), ipady=5)
        return var

    def _build(self):
        self._fn = self._field("First Name")
        self._mn = self._field("Middle Name", required=False)
        self._ln = self._field("Last Name")
        self._em = self._field("Email")

        row = self._action_row()
        self._cancel_btn(row).pack(side="right", padx=(6, 0))
        self._confirm_btn(row, "Create Admin", self._submit).pack(side="right")

    def _submit(self):
        fn = self._fn.get().strip()
        mn = self._mn.get().strip()
        ln = self._ln.get().strip()
        em = self._em.get().strip()

        if not fn or not ln or not em:
            messagebox.showerror("Validation Error",
                                 "First Name, Last Name, and Email are required.",
                                 parent=self)
            return
        if "@" not in em:
            messagebox.showerror("Validation Error",
                                 "Please enter a valid email address.",
                                 parent=self)
            return

        ConfirmModal(
            self,
            title="Confirm Create Admin",
            message=f'Create admin account for "{fn} {ln}"?',
            confirm_text="Yes, Create",
            on_confirm=lambda: self._do_create(fn, mn, ln, em),
        )

    def _do_create(self, fn, mn, ln, em):
        self.destroy()
        self._on_create(fn, mn, ln, em)


# ── Edit Admin Modal ───────────────────────────────────────────────────────

class EditAdminModal(BaseModal):
    def __init__(self, master, admin, on_save):
        super().__init__(master, "Edit Admin",
                         "Update the admin's username and email.")
        self._admin = admin
        self._on_save = on_save
        self._build()

    def _field(self, label, initial):
        tk.Label(self._card, text=label,
                 font=FONTS["label"], bg=COLORS["card"],
                 fg=COLORS["text_mid"], anchor="w"
                 ).pack(fill="x", padx=18, pady=(8, 0))
        var = tk.StringVar(value=initial)
        e = tk.Entry(self._card, textvariable=var,
                     font=FONTS["input"], relief="solid", bd=1,
                     bg=COLORS["input_bg"],
                     highlightthickness=1,
                     highlightcolor=COLORS["primary_orange"],
                     highlightbackground=COLORS["border"])
        e.pack(fill="x", padx=18, pady=(2, 0), ipady=5)
        return var

    def _build(self):
        self._uname = self._field("Username", self._admin[1])
        self._email = self._field("Email",    self._admin[2])

        row = self._action_row()
        self._cancel_btn(row).pack(side="right", padx=(6, 0))
        self._confirm_btn(row, "Update Admin", self._submit).pack(side="right")

    def _submit(self):
        uname = self._uname.get().strip()
        email = self._email.get().strip()
        if not uname or not email:
            messagebox.showerror("Validation Error",
                                 "Username and Email are required.", parent=self)
            return
        self.destroy()
        self._on_save(self._admin[0], uname, email)
