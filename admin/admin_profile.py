"""
admin/admin_profile.py
───────────────────────
Profile Settings page for The Gears Admin.

Inherits the full header + sidebar + scrollable shell from AdminLayout.
Only page-specific content lives here; all chrome is provided by the base class.

Features
────────
  • Profile photo — choose, preview (PIL), reset
  • Account Information — full name, email
  • Change Password — current / new / confirm
      • Live password-strength bar (Weak / Medium / Strong)
      • Passwords-match indicator
      • Show / Hide toggle per field
  • Save Changes button — disabled until form is dirty
  • Reset — restores all fields to loaded values
  • Danger Zone — Delete Account with confirm dialog
  • Dark mode toggle (inherited from AdminLayout)
  • Sidebar with Manage Articles dropdown (inherited)

db_callbacks keys (passed through to AdminLayout + used here):
  fetch_profile(user_id)                               → dict  {name, email, profile_image}
  update_profile(user_id, first, last, email, avatar)  → (bool, str)
  change_password(user_id, current_pw, new_pw)         → (bool, str)
  delete_account(user_id)                              → bool

user tuple: (first_name, last_name, email, id, role, ...)
             0            1          2     3   4
"""

import os
import tkinter as tk
from tkinter import messagebox, filedialog

from admin.admin_layout import AdminLayout

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
        "navy":                 "#0C1633",
        "shadow":               "#E8DDD5",
    }
    FONTS = {
        "heading":     ("Poppins", 20, "bold"),
        "section":     ("Poppins", 16, "bold"),
        "card_title":  ("Poppins", 13, "bold"),
        "body":        ("Poppins", 11),
        "body_bold":   ("Poppins", 11, "bold"),
        "small":       ("Poppins", 9),
        "small_bold":  ("Poppins", 9, "bold"),
        "button":      ("Poppins", 10, "bold"),
        "tag":         ("Poppins", 8, "bold"),
        "input":       ("Poppins", 11),
        "modal_title": ("Poppins", 18, "bold"),
    }

STRENGTH_COLORS = {"weak": "#E63946", "medium": "#F6A609", "strong": "#1B873F"}
DANGER_BG  = "#FFF5F5"
DANGER_CLR = "#E63946"


# ─────────────────────────────────────────────────────────────────────────────
class AdminProfile(AdminLayout):
    """
    Profile Settings page.  Inherits header, orange bar, sidebar, scrollable
    shell, user-menu, dark-mode toggle, and all navigation from AdminLayout.

    Only _build_page() and page-specific helpers live here.
    """

    ACTIVE_NAV = "profile"   # highlights the Profile item in the user-menu

    def __init__(self, root, user=None, db_callbacks=None):
        self._img_path = None   # newly chosen photo path (before save)
        super().__init__(root, user, db_callbacks)
        self._build_page()

    # =========================================================================
    # Page construction  (called by AdminLayout.__init__ via _build_page hook)
    # =========================================================================

    def _build_page(self):
        T = self.theme

        # ── Page heading ──────────────────────────────────────────────────────
        hdr = tk.Frame(self.inner, bg=T["background"])
        hdr.pack(fill="x", pady=(0, 20))
        tk.Label(
            hdr, text="PROFILE SETTINGS",
            bg=T["background"], fg=T["primary_orange"],
            font=("Poppins", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            hdr, text="Update your personal info and account security.",
            bg=T["background"], fg=T["text_grey"],
            font=FONTS["body"],
        ).pack(anchor="w", pady=(4, 0))

        # ── Two-column grid ───────────────────────────────────────────────────
        grid = tk.Frame(self.inner, bg=T["background"])
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=0, minsize=300)
        grid.columnconfigure(1, weight=1)

        left  = tk.Frame(grid, bg=T["background"])
        right = tk.Frame(grid, bg=T["background"])
        left.grid( row=0, column=0, sticky="nsew", padx=(0, 16))
        right.grid(row=0, column=1, sticky="nsew")

        self._build_left(left)
        self._build_right(right)

    # =========================================================================
    # LEFT — Profile Photo
    # =========================================================================

    def _build_left(self, parent):
        T = self.theme
        self._section_lbl(parent, "Profile")
        card = self._card(parent)

        tk.Label(
            card, text="Profile Photo",
            bg=T["card"], fg=T["primary_orange"],
            font=FONTS["card_title"],
        ).pack(anchor="w")
        tk.Label(
            card,
            text="Your photo and initials appear on articles\nand activity logs.",
            bg=T["card"], fg=T["text_light"],
            font=FONTS["small"], justify="left",
        ).pack(anchor="w", pady=(2, 16))

        # 96×96 avatar circle
        av_frame = tk.Frame(card, bg=T["card"])
        av_frame.pack()
        self._av_canvas = tk.Canvas(
            av_frame, width=96, height=96,
            bg=T["card"], highlightthickness=0,
        )
        self._av_canvas.pack()
        self._draw_page_avatar()

        tk.Label(
            card,
            text="Recommended: 400×400 px · JPG or PNG · max 2 MB",
            bg=T["card"], fg=T["text_light"],
            font=FONTS["small"], wraplength=250,
        ).pack(pady=(10, 6))

        self._file_lbl_var = tk.StringVar(value="No file selected")
        tk.Label(
            card, textvariable=self._file_lbl_var,
            bg=T["card"], fg=T["text_grey"],
            font=FONTS["small"],
        ).pack(pady=(0, 10))

        btns = tk.Frame(card, bg=T["card"])
        btns.pack()
        tk.Button(
            btns, text="📁  Choose Photo",
            command=self._choose_photo,
            bg=T["primary_orange_light"], fg=T["primary_orange"],
            activebackground=T["primary_orange"], activeforeground="white",
            font=FONTS["button"], bd=0, relief="flat",
            padx=14, pady=8, cursor="hand2",
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            btns, text="↺  Reset",
            command=self._reset_form,
            bg=T["background_alt"], fg=T["text_grey"],
            activebackground=T["border"], activeforeground=T["text_dark"],
            font=FONTS["button"], bd=1, relief="solid",
            highlightbackground=T["border"],
            padx=10, pady=7, cursor="hand2",
        ).pack(side="left")

    def _draw_page_avatar(self):
        import os, io as _io, urllib.request
        from dotenv import load_dotenv
        from PIL import Image, ImageTk, ImageDraw  # ← import sa TAAS, hindi sa loob ng if

        T = self.theme
        c = self._av_canvas
        c.delete("all")

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
        FLASK_URL = os.getenv("FLASK_URL", "http://127.0.0.1:5000")

        src = self._img_path or self._profile.get("profile_image")
        loaded_image = None

        if src:
            src = str(src).strip().replace("\\", "/")
            filename = src.split("/")[-1]
            project_root = BASE_DIR

            candidates = [
                src if os.path.isabs(src) else os.path.join(project_root, src),
                os.path.join(project_root, "static", "uploads", "avatars", filename),
                os.path.join(project_root, "static", "uploads", filename),
                os.path.join(project_root, "uploads", "avatars", filename),
                os.path.join(project_root, "uploads", filename),
            ]

            for path in candidates:
                path = os.path.normpath(path)
                if os.path.exists(path):
                    try:
                        loaded_image = Image.open(path).convert("RGBA").resize(
                            (96, 96), Image.LANCZOS)
                        print(f"[AdminProfile] ✅ Loaded local: {path}")
                        break
                    except Exception as e:
                        print(f"[AdminProfile] local error {path}: {e}")

            if loaded_image is None:
                for url in [
                    f"{FLASK_URL}/static/uploads/avatars/{filename}",
                    f"{FLASK_URL}/static/uploads/{filename}",
                ]:
                    try:
                        with urllib.request.urlopen(url, timeout=8) as resp:
                            loaded_image = Image.open(_io.BytesIO(resp.read())).convert(
                                "RGBA").resize((96, 96), Image.LANCZOS)
                        print(f"[AdminProfile] ✅ Fetched: {url}")
                        break
                    except Exception as e:
                        print(f"[AdminProfile] ❌ Flask fetch failed: {e}")

        if loaded_image:
            try:
                mask = Image.new("L", (96, 96), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, 95, 95), fill=255)
                loaded_image.putalpha(mask)
                self._av_photo = ImageTk.PhotoImage(loaded_image)
                c.create_image(48, 48, image=self._av_photo, anchor="center")
                return
            except Exception as e:
                print(f"[AdminProfile] render error: {e}")

        # Fallback initials
        c.create_oval(0, 0, 96, 96, fill=T["primary_orange"], outline="")
        c.create_text(48, 48, text=self.initials, fill="white",
                    font=("Poppins", 28, "bold"))
    def _choose_photo(self):
        path = filedialog.askopenfilename(
            title="Select Profile Photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.webp")],
        )
        if path:
            self._img_path = path
            self._file_lbl_var.set(os.path.basename(path))
            self._draw_page_avatar()
            self._mark_dirty()

    def _reset_form(self):
        self._name_var.set(self._orig_name)
        self._email_var.set(self._orig_email)
        self._img_path = None
        self._draw_page_avatar()
        self._file_lbl_var.set("No file selected")
        self._cur_pw_var.set("")
        self._new_pw_var.set("")
        self._conf_pw_var.set("")
        self._check_dirty()

    # =========================================================================
    # RIGHT — Account Info + Password + Save + Danger Zone
    # =========================================================================

    def _build_right(self, parent):
        self._section_lbl(parent, "Account & Security")
        self._build_account_card(parent)
        self._build_password_card(parent)
        self._build_save_card(parent)
        self._build_danger_card(parent)

    # ── Account Info ──────────────────────────────────────────────────────────

    def _build_account_card(self, parent):
        T    = self.theme
        card = self._card(parent)

        tk.Label(
            card, text="Account Information",
            bg=T["card"], fg=T["primary_orange"],
            font=FONTS["card_title"],
        ).pack(anchor="w")
        tk.Label(
            card, text="Keep your profile information up to date.",
            bg=T["card"], fg=T["text_light"],
            font=FONTS["small"],
        ).pack(anchor="w", pady=(2, 14))

        tk.Label(card, text="Full Name",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small_bold"]).pack(anchor="w")
        self._name_var = tk.StringVar(
            value=self._profile.get("name", self.display_name))
        self._entry(card, self._name_var).pack(fill="x", pady=(4, 14))
        self._name_var.trace_add("write", lambda *_: self._check_dirty())

        tk.Label(card, text="Email Address",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small_bold"]).pack(anchor="w")
        self._email_var = tk.StringVar(
            value=self._profile.get("email", self.display_email))
        self._entry(card, self._email_var).pack(fill="x", pady=(4, 4))
        self._email_var.trace_add("write", lambda *_: self._check_dirty())
        tk.Label(
            card, text="We'll send account-related notifications here.",
            bg=T["card"], fg=T["text_light"],
            font=FONTS["small"],
        ).pack(anchor="w")

        # Store originals for dirty-check / reset
        self._orig_name  = self._name_var.get()
        self._orig_email = self._email_var.get()

    # ── Change Password ───────────────────────────────────────────────────────

    def _build_password_card(self, parent):
        T    = self.theme
        card = self._card(parent)

        tk.Label(
            card, text="Change Password",
            bg=T["card"], fg=T["primary_orange"],
            font=FONTS["card_title"],
        ).pack(anchor="w")
        tk.Label(
            card, text="Use a strong password to keep your account secure.",
            bg=T["card"], fg=T["text_light"],
            font=FONTS["small"],
        ).pack(anchor="w", pady=(2, 14))

        # Current password
        tk.Label(card, text="Current Password",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small_bold"]).pack(anchor="w")
        self._cur_pw_var = tk.StringVar()
        self._pw_entry(card, self._cur_pw_var).pack(fill="x", pady=(4, 4))
        tk.Label(
            card, text="Required only if you're changing your password.",
            bg=T["card"], fg=T["text_light"],
            font=FONTS["small"],
        ).pack(anchor="w", pady=(0, 12))
        self._cur_pw_var.trace_add("write", lambda *_: self._check_dirty())

        # New + Confirm side-by-side
        row2 = tk.Frame(card, bg=T["card"])
        row2.pack(fill="x")
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)

        lf = tk.Frame(row2, bg=T["card"])
        lf.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        tk.Label(lf, text="New Password",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small_bold"]).pack(anchor="w")
        self._new_pw_var = tk.StringVar()
        self._pw_entry(lf, self._new_pw_var).pack(fill="x", pady=(4, 6))
        self._new_pw_var.trace_add("write", lambda *_: (
            self._upd_strength(), self._upd_match(), self._check_dirty()))

        # Strength bar
        sb_wrap = tk.Frame(lf, bg=T["card"])
        sb_wrap.pack(fill="x")
        sb_bg = tk.Frame(sb_wrap, bg=T["border"], height=5)
        sb_bg.pack(fill="x")
        sb_bg.pack_propagate(False)
        self._str_fill = tk.Frame(sb_bg, bg=T["border"], height=5)
        self._str_fill.place(x=0, y=0, relheight=1, width=0)
        self._str_bg  = sb_bg
        self._str_lbl = tk.Label(sb_wrap, text="",
                                 bg=T["card"], fg=T["text_light"],
                                 font=FONTS["small"])
        self._str_lbl.pack(anchor="w", pady=(2, 0))

        rf = tk.Frame(row2, bg=T["card"])
        rf.grid(row=0, column=1, sticky="ew")
        tk.Label(rf, text="Confirm New Password",
                 bg=T["card"], fg=T["text_grey"],
                 font=FONTS["small_bold"]).pack(anchor="w")
        self._conf_pw_var = tk.StringVar()
        self._pw_entry(rf, self._conf_pw_var).pack(fill="x", pady=(4, 6))
        self._conf_pw_var.trace_add("write", lambda *_: (
            self._upd_match(), self._check_dirty()))
        self._match_lbl = tk.Label(rf, text="",
                                   bg=T["card"], fg=T["text_light"],
                                   font=FONTS["small"])
        self._match_lbl.pack(anchor="w")

        tk.Label(
            card,
            text="Password must be at least 8 characters — "
                 "mix of letters and numbers.",
            bg=T["card"], fg=T["text_light"],
            font=FONTS["small"],
        ).pack(anchor="w", pady=(10, 0))

    # ── Save Changes ──────────────────────────────────────────────────────────

    def _build_save_card(self, parent):
        T    = self.theme
        card = self._card(parent)

        tk.Label(
            card, text="Save Changes",
            bg=T["card"], fg=T["primary_orange"],
            font=FONTS["card_title"],
        ).pack(anchor="w")
        tk.Label(
            card, text="Review your updates before saving.",
            bg=T["card"], fg=T["text_light"],
            font=FONTS["small"],
        ).pack(anchor="w", pady=(2, 12))

        btn_row = tk.Frame(card, bg=T["card"])
        btn_row.pack(anchor="w")

        self._save_btn = tk.Button(
            btn_row, text="💾  Save Changes",
            command=self._save,
            bg=T["border"], fg="white",
            activebackground=T["primary_orange_dark"], activeforeground="white",
            font=FONTS["button"], bd=0, relief="flat",
            padx=16, pady=10, cursor="hand2",
            state="disabled",
        )
        self._save_btn.pack(side="left", padx=(0, 10))

        tk.Button(
            btn_row, text="↺  Reset",
            command=self._reset_form,
            bg=T["background_alt"], fg=T["text_grey"],
            activebackground=T["border"], activeforeground=T["text_dark"],
            font=FONTS["button"], bd=1, relief="solid",
            highlightbackground=T["border"],
            padx=12, pady=9, cursor="hand2",
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_row, text="Cancel",
            command=self._go_dashboard,
            bg=T["background_alt"], fg=T["text_grey"],
            activebackground=T["border"], activeforeground=T["text_dark"],
            font=FONTS["button"], bd=1, relief="solid",
            highlightbackground=T["border"],
            padx=12, pady=9, cursor="hand2",
        ).pack(side="left")

    # ── Danger Zone ───────────────────────────────────────────────────────────

    def _build_danger_card(self, parent):
        T    = self.theme
        card = self._card(parent, bg=DANGER_BG, border=DANGER_CLR)

        tk.Label(
            card, text="Danger Zone",
            bg=DANGER_BG, fg=DANGER_CLR,
            font=FONTS["card_title"],
        ).pack(anchor="w")
        tk.Label(
            card,
            text=(
                "Deleting your account is permanent and cannot be undone.\n"
                "You will be signed out immediately."
            ),
            bg=DANGER_BG, fg=T["text_grey"],
            font=FONTS["small"], justify="left",
        ).pack(anchor="w", pady=(4, 14))

        tk.Button(
            card, text="🗑  Delete Account",
            command=self._confirm_delete,
            bg=DANGER_CLR, fg="white",
            activebackground="#C52936", activeforeground="white",
            font=FONTS["button"], bd=0, relief="flat",
            padx=14, pady=9, cursor="hand2",
        ).pack(anchor="e")

    # =========================================================================
    # Widget helpers (page-local)
    # =========================================================================

    def _section_lbl(self, parent, text: str):
        T = self.theme
        tk.Label(
            parent, text=text.upper(),
            bg=T["background"], fg=T["text_grey"],
            font=FONTS["tag"],
        ).pack(anchor="w", pady=(0, 8))

    def _card(self, parent, bg=None, border=None) -> tk.Frame:
        T   = self.theme
        bg  = bg     or T["card"]
        brd = border or T["border"]
        c   = tk.Frame(
            parent, bg=bg,
            highlightbackground=brd, highlightthickness=1,
            padx=20, pady=18,
        )
        c.pack(fill="x", pady=(0, 14))
        return c

    def _entry(self, parent, var) -> tk.Frame:
        """Single-line text entry with orange focus border."""
        T    = self.theme
        wrap = tk.Frame(parent, bg=T["border"])
        e    = tk.Entry(
            wrap, textvariable=var,
            font=FONTS["input"],
            bg=T["input_bg"], fg=T["text_dark"],
            relief="flat", bd=0,
            insertbackground=T["primary_orange"],
        )
        e.pack(fill="x", padx=1, pady=1, ipady=8, ipadx=8)
        e.bind("<FocusIn>",  lambda _: wrap.configure(bg=T["primary_orange"]))
        e.bind("<FocusOut>", lambda _: wrap.configure(bg=T["border"]))
        return wrap

    def _pw_entry(self, parent, var) -> tk.Frame:
        """Password entry with Show / Hide toggle."""
        T     = self.theme
        wrap  = tk.Frame(parent, bg=T["border"])
        inner = tk.Frame(wrap, bg=T["input_bg"])
        inner.pack(fill="x", padx=1, pady=1)

        e = tk.Entry(
            inner, textvariable=var, show="●",
            font=FONTS["input"],
            bg=T["input_bg"], fg=T["text_dark"],
            relief="flat", bd=0,
            insertbackground=T["primary_orange"],
        )
        e.pack(side="left", fill="x", expand=True, ipady=8, ipadx=8)

        tog = tk.Button(
            inner, text="Show",
            bg=T["input_bg"], fg=T["text_grey"],
            activebackground=T["input_bg"], activeforeground=T["primary_orange"],
            font=FONTS["small"], bd=0, relief="flat",
            cursor="hand2", padx=6,
        )
        tog.pack(side="right", padx=(0, 4))

        def _toggle():
            if e.cget("show") == "●":
                e.configure(show="");   tog.configure(text="Hide")
            else:
                e.configure(show="●"); tog.configure(text="Show")
        tog.configure(command=_toggle)

        e.bind("<FocusIn>",  lambda _: wrap.configure(bg=T["primary_orange"]))
        e.bind("<FocusOut>", lambda _: wrap.configure(bg=T["border"]))
        return wrap

    # =========================================================================
    # Live feedback
    # =========================================================================

    def _upd_strength(self):
        val = self._new_pw_var.get()
        if not val:
            text, clr, pct = "", self.theme["border"], 0
        elif len(val) < 6:
            text, clr, pct = "Strength: Weak",   STRENGTH_COLORS["weak"],   0.33
        elif len(val) < 10:
            text, clr, pct = "Strength: Medium", STRENGTH_COLORS["medium"], 0.66
        else:
            text, clr, pct = "Strength: Strong", STRENGTH_COLORS["strong"], 1.0

        self._str_lbl.configure(
            text=text,
            fg=clr if pct else self.theme["text_light"],
        )
        bw = self._str_bg.winfo_width() or 200
        self._str_fill.configure(bg=clr if pct else self.theme["border"])
        self._str_fill.place(x=0, y=0, relheight=1, width=max(int(bw * pct), 0))

    def _upd_match(self):
        nv, cv = self._new_pw_var.get(), self._conf_pw_var.get()
        if not nv and not cv:
            self._match_lbl.configure(text="", fg=self.theme["text_light"])
        elif nv and cv and nv == cv:
            self._match_lbl.configure(
                text="✔  Passwords match", fg=STRENGTH_COLORS["strong"])
        elif cv:
            self._match_lbl.configure(
                text="Passwords do not match yet", fg=STRENGTH_COLORS["weak"])
        else:
            self._match_lbl.configure(text="", fg=self.theme["text_light"])

    # =========================================================================
    # Dirty-state tracking
    # =========================================================================

    def _mark_dirty(self):
        try:
            self._save_btn.configure(
                state="normal", bg=self.theme["primary_orange"])
        except Exception:
            pass

    def _check_dirty(self):
        dirty = (
            self._name_var.get()  != self._orig_name  or
            self._email_var.get() != self._orig_email  or
            bool(self._new_pw_var.get() or self._cur_pw_var.get()) or
            self._img_path is not None
        )
        try:
            self._save_btn.configure(
                state="normal"    if dirty else "disabled",
                bg   =self.theme["primary_orange"] if dirty else self.theme["border"],
            )
        except Exception:
            pass

    # =========================================================================
    # Save / Delete
    # =========================================================================

    def _save(self):
        import shutil
        from services.api_client import APIClient
 
        name        = self._name_var.get().strip()
        email       = self._email_var.get().strip()
        cur_pw      = self._cur_pw_var.get()
        new_pw      = self._new_pw_var.get()
        conf_pw     = self._conf_pw_var.get()
        avatar_path = self._img_path          # local path chosen via filedialog
 
        # ── Upload avatar to Flask (single source of truth) ───────────────────
        if avatar_path and os.path.exists(avatar_path):
            api             = APIClient()
            remote_filename = api.upload_avatar(avatar_path)
 
            if not remote_filename:
                messagebox.showerror(
                    "Upload Error",
                    "Could not upload the profile photo to the server.\n"
                    "Make sure Flask is running and try again."
                )
                return
 
            # Also keep a local copy so the Tkinter widget renders without a
            # round-trip to Flask on every paint.
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            local_dir    = os.path.join(project_root, "static", "uploads", "avatars")
            os.makedirs(local_dir, exist_ok=True)
            try:
                shutil.copy2(avatar_path, os.path.join(local_dir, remote_filename))
            except Exception as e:
                print(f"[AdminProfile._save] local copy warning: {e}")
 
            # DB stores the relative path that both Flask and Tkinter understand
            avatar_path = f"avatars/{remote_filename}"
 
        # ── Password change ───────────────────────────────────────────────────
        if new_pw:
            if not cur_pw:
                messagebox.showerror(
                    "Error", "Please enter your current password to change it.")
                return
            if new_pw != conf_pw:
                messagebox.showerror("Error", "New passwords do not match.")
                return
 
            pwd_success, pwd_msg = self.callbacks.get(
                "change_password",
                lambda *a, **kw: (False, "No callback"),
            )(self.user_id, cur_pw, new_pw)
 
            if not pwd_success:
                messagebox.showerror("Error", f"Password: {pwd_msg}")
                return
 
            self._cur_pw_var.set("")
            self._new_pw_var.set("")
            self._conf_pw_var.set("")
            self._upd_strength()
            self._upd_match()
            messagebox.showinfo("Success", "Password updated successfully.")
 
        # ── Profile info (name / email / avatar) ──────────────────────────────
        update_cb = self.callbacks.get("update_profile")
        if update_cb and (name or email or avatar_path):
            parts     = (name or self.display_name).split(" ", 1)
            firstname = parts[0]
            lastname  = parts[1].strip() if len(parts) > 1 else ""
            ok, msg   = update_cb(self.user_id, firstname, lastname,
                                   email or self.display_email, avatar_path)
            if not ok and msg != "No changes detected.":
                messagebox.showerror("Error", msg or "Failed to update profile.")
                return
 
        messagebox.showinfo("Success", "Profile updated successfully.")
 
        # ── Refresh local state ───────────────────────────────────────────────
        self._orig_name  = self._name_var.get()
        self._orig_email = self._email_var.get()
        self._img_path   = None
        self._check_dirty()
 
        if avatar_path:
            self._profile["profile_image"] = avatar_path
 
        self._draw_page_avatar()
        self._draw_header_avatar()

    def _confirm_delete(self):
        if not messagebox.askyesno(
            "Delete Account",
            "This action CANNOT be undone.\n"
            "Are you sure you want to delete your account?\n"
            "You will be signed out immediately.",
            icon="warning", parent=self.root,
        ):
            return
        cb = self.callbacks.get("delete_account")
        if cb:
            ok = cb(self.user_id)
            if ok:
                messagebox.showinfo("Account Deleted", "Your account has been deleted.")
                if hasattr(self.root, "show_landing"):
                    self.root.show_landing()
                else:
                    self.root.destroy()
                return
            messagebox.showerror("Error", "Failed to delete account.", parent=self.root)
        else:
            messagebox.showinfo("Deleted (stub)", "delete_account callback not wired.")
            self.root.destroy()

    # =========================================================================
    # display_email convenience property
    # =========================================================================

    @property
    def display_email(self) -> str:
        return self.user[2] if self.user and len(self.user) > 2 else ""


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.title("The Gears — Profile Settings")
    root.geometry("1280x800")
    root.minsize(1050, 680)

    db_callbacks = {
        "fetch_profile": lambda uid: {
            "name":               "Maria Santos",
            "email":              "maria@gears.com",
            "profile_image": None,
        },
        "update_profile": lambda user_id, first, last, email, avatar=None: (
            True, "OK"
        ),
        "change_password": lambda user_id, cur, new: (
            (True, "Password changed") if cur == "secret"
            else (False, "Incorrect current password")
        ),
        "delete_account": lambda uid: True,
    }

    AdminProfile(
        root,
        user=("Maria", "Santos", "maria@gears.com", 1, "admin"),
        db_callbacks=db_callbacks,
    )
    root.mainloop()