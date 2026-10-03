import tkinter as tk
from tkinter import messagebox

from theme import COLORS, FONTS, RADIUS
from services.auth_services import login_user, register_user
from components.verification_modal import VerificationModal


# ── Drawing helpers ────────────────────────────────────────────────────────────

def _rounded_polygon_points(x1, y1, x2, y2, r):
    return [
        x1 + r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r,
        x1, y1 + r, x1, y1,
    ]


def draw_rounded_rect(canvas, x1, y1, x2, y2, r=12, **kwargs):
    pts = _rounded_polygon_points(x1, y1, x2, y2, r)
    return canvas.create_polygon(pts, smooth=True, splinesteps=36, **kwargs)


# ── RoundedEntry ──────────────────────────────────────────────────────────────

class RoundedEntry(tk.Frame):
    def __init__(self, parent, label, placeholder="", show=None,
                 width=300, height=46, has_toggle=False):
        super().__init__(parent, bg=COLORS["card"])

        self.placeholder  = placeholder
        self.real_show    = show
        self.is_placeholder = True
        self.hidden       = bool(show)

        tk.Label(self, text=label, font=FONTS["small_bold"],
                 fg=COLORS["text_dark"], bg=COLORS["card"],
                 anchor="w").pack(fill="x", pady=(0, 5))

        self.canvas = tk.Canvas(self, height=height,
                        bg=COLORS["card"], highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", expand=True)

        self.bg_id = draw_rounded_rect(
            self.canvas, 1, 1, width - 1, height - 1,
            r=RADIUS["input"] + 4,
            fill=COLORS["input_bg"],
            outline=COLORS["border"], width=1,
        )

        entry_width = width - (60 if has_toggle else 32)

        self.entry = tk.Entry(
            self.canvas,
            font=FONTS["input"],
            fg=COLORS["text_light"],
            bg=COLORS["input_bg"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            insertbackground=COLORS["primary_orange"]
        )

        # IMPORTANT: store this
        self.entry_id = self.canvas.create_window(
            16, height // 2,
            anchor="w",
            width=entry_width,
            window=self.entry
        )

        # 🔥 THIS FIXES THE OVERFLOW
        self.canvas.bind("<Configure>", self._resize_bg)
        self.canvas.bind("<Configure>", self._resize_entry, add="+")
        self.entry.insert(0, placeholder)

        self.entry.bind("<FocusIn>",  self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<FocusIn>",  self._focus_style_on,  add="+")
        self.entry.bind("<FocusOut>", self._focus_style_off, add="+")
        self.canvas.bind("<Button-1>", lambda e: self.entry.focus_set())

        if has_toggle:
            self.toggle_btn = tk.Label(
                self.canvas, text="◌",
                font=("Poppins", 10), fg=COLORS["text_light"],
                bg=COLORS["input_bg"], cursor="hand2",
            )
            self.canvas.create_window(width - 22, height // 2,
                                      window=self.toggle_btn)
            self.toggle_btn.bind("<Button-1>", self._toggle_password)

    def _focus_style_on(self, _):
        self.canvas.itemconfig(self.bg_id,
                               outline=COLORS["border_focus"], width=1.5)

    def _focus_style_off(self, _):
        self.canvas.itemconfig(self.bg_id, outline=COLORS["border"], width=1)

    def _on_focus_in(self, _):
        if self.is_placeholder:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=COLORS["text_dark"])
            if self.real_show and self.hidden:
                self.entry.config(show=self.real_show)
            self.is_placeholder = False

    def _on_focus_out(self, _):
        if not self.entry.get().strip():
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=COLORS["text_light"], show="")
            self.is_placeholder = True

    def _toggle_password(self, _=None):
        if self.is_placeholder or not self.real_show:
            return
        self.hidden = not self.hidden
        self.entry.config(show=self.real_show if self.hidden else "")
        self.toggle_btn.config(text="◌" if self.hidden else "◉")

    def _resize_bg(self, event):
        points = _rounded_polygon_points(
            1, 1,
            event.width - 1,
            event.height - 1,
            RADIUS["input"] + 4
        )
        self.canvas.coords(self.bg_id, *points)

    def _resize_entry(self, event):
        padding = 52 if hasattr(self, "toggle_btn") else 26
        entry_width = max(50, event.width - padding)  # prevent negative width
        self.canvas.itemconfig(self.entry_id, width=entry_width)

    def get(self):
        return "" if self.is_placeholder else self.entry.get().strip()


# ── RoundedButton ─────────────────────────────────────────────────────────────

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=300, height=44,
                 bg=COLORS["primary_orange"], fg=COLORS["white"],
                 hover_bg=COLORS["primary_orange_dark"], radius=22):
        super().__init__(parent, width=width, height=height,
                         bg=parent.cget("bg"), highlightthickness=0,
                         bd=0, cursor="hand2")

        self.command     = command
        self.default_bg  = bg
        self.hover_bg    = hover_bg
        self.disabled    = False

        self.shape = draw_rounded_rect(self, 1, 1, width - 1, height - 1,
                                       r=radius, fill=bg, outline=bg)
        self.text_id = self.create_text(width // 2, height // 2,
                                        text=text, fill=fg,
                                        font=FONTS["button"])

        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_text(self, text):
        self.itemconfig(self.text_id, text=text)

    def set_disabled(self, disabled=True):
        self.disabled = disabled
        color = COLORS["text_light"] if disabled else self.default_bg
        self.itemconfig(self.shape, fill=color, outline=color)

    def _on_enter(self, _):
        if not self.disabled:
            self.itemconfig(self.shape,
                            fill=self.hover_bg, outline=self.hover_bg)

    def _on_leave(self, _):
        if not self.disabled:
            self.itemconfig(self.shape,
                            fill=self.default_bg, outline=self.default_bg)

    def _on_click(self, _):
        if not self.disabled and self.command:
            self.command()


# ── AuthModal ─────────────────────────────────────────────────────────────────

class AuthModal(tk.Toplevel):
    """
    Login / Sign-up modal.

    Layout (both modes)
    ────────────────────
    ┌──────────────────────────────┐  ← modal window
    │  [orange accent bar, 5 px]   │
    │  [header: logo + title]      │  fixed height
    │  ─────────────────────────── │
    │  [scrollable form area]      │  expands if needed
    │  ─────────────────────────── │
    │  [submit button]             │  always visible
    │  [footer link]               │  always visible
    └──────────────────────────────┘

    The scrollable area is capped so the submit + footer never get hidden.
    """

    # Sizes
    MODAL_W     = 420
    LOGIN_H     = 540
    SIGNUP_H    = 760
    HEADER_H    = 165          # accent(5)+logo(44)+pads+title+subtitle ~ 165
    FOOTER_H    = 120          # submit(44)+pady+divider+link+bottom pad
    FORM_MAX_H  = 290          # scrollable form height cap

    def __init__(self, parent, mode="login"):
        super().__init__(parent)

        self.parent  = parent
        self.mode    = mode
        self.loading = False
        self.entries = {}

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLORS["card"])

        self.card_h = self.LOGIN_H if mode == "login" else self.SIGNUP_H

        self._build_overlay()
        self._center()
        self._build_modal()

        self.grab_set()
        self.bind("<Escape>", lambda e: self._close())

    # ── Overlay ───────────────────────────────────────────────────────────────

    def _build_overlay(self):
        self._overlay = tk.Toplevel(self.parent)
        self._overlay.overrideredirect(True)
        self._overlay.attributes("-alpha", 0.35)
        self._overlay.configure(bg=COLORS["navy"])

        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()

        self._overlay.geometry(f"{pw}x{ph}+{px}+{py}")
        self._overlay.lift()
        self._overlay.bind("<Button-1>", lambda e: self._close())

    def _center(self):
        self.update_idletasks()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()

        # Allow up to 92% of the window height — enough for both modes
        self.card_h = min(self.card_h, int(ph * 0.92))
        x = px + (pw - self.MODAL_W) // 2
        y = py + (ph - self.card_h)  // 2
        self.geometry(f"{self.MODAL_W}x{self.card_h}+{x}+{y}")

    def _close(self):
        try: self.grab_release()
        except Exception: pass
        try: self._overlay.destroy()
        except Exception: pass
        self.destroy()

    # ── Modal skeleton ────────────────────────────────────────────────────────

    def _build_modal(self):
        W = self.MODAL_W
        H = self.card_h

        # Outer shell with a subtle layered shadow effect
        self.configure(
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )

        root_frame = tk.Frame(self, bg=COLORS["card"])
        root_frame.pack(fill="both", expand=True)

        # ── Orange top accent bar ─────────────────────────────────────────
        accent = tk.Frame(root_frame, bg=COLORS["primary_orange"], height=5)
        accent.pack(fill="x")

        # ── Header block (logo + title + subtitle) ────────────────────────
        self._build_header(root_frame, W)

        # Separator
        tk.Frame(root_frame, bg=COLORS["border"], height=1).pack(fill="x",
                                                                   padx=28)

        # ── Form area + footer — mode-specific ────────────────────────────
        if self.mode == "login":
            self._build_login_body(root_frame, W)
        else:
            self._build_signup_body(root_frame, W)

    def _build_header(self, parent, W):
        hdr = tk.Frame(parent, bg=COLORS["background_alt"])
        hdr.pack(fill="x")

        # Close button — top-right
        close = tk.Label(hdr, text="✕", font=("Poppins", 11, "bold"),
                         fg=COLORS["text_mid"], bg=COLORS["background_alt"],
                         cursor="hand2")
        close.place(relx=1.0, x=-16, y=14, anchor="ne")
        close.bind("<Button-1>", lambda e: self._close())
        close.bind("<Enter>", lambda e: close.config(fg=COLORS["primary_red"]))
        close.bind("<Leave>", lambda e: close.config(fg=COLORS["text_mid"]))

        # Logo
        try:
            from PIL import Image, ImageTk
            import os
            BASE_DIR  = os.path.dirname(__file__)
            logo_path = os.path.join(BASE_DIR, "..", "assets", "gears_logo.png")
            img = Image.open(logo_path).resize((44, 44))
            self._logo_img = ImageTk.PhotoImage(img)
            tk.Label(hdr, image=self._logo_img,
                     bg=COLORS["background_alt"]).pack(pady=(18, 6))
        except Exception:
            # Fallback: orange circle with TG
            logo_c = tk.Canvas(hdr, width=44, height=44,
                               bg=COLORS["background_alt"], highlightthickness=0)
            logo_c.pack(pady=(18, 6))
            logo_c.create_oval(2, 2, 42, 42,
                               fill=COLORS["primary_orange"], outline="")
            logo_c.create_text(22, 22, text="TG", fill="white",
                               font=("Poppins", 14, "bold"))

        # Title
        title = "Welcome Back" if self.mode == "login" else "Create Account"
        tk.Label(hdr, text=title, font=("Poppins", 16, "bold"),
                 fg=COLORS["text_dark"],
                 bg=COLORS["background_alt"]).pack()

        # Subtitle
        sub = ("Log in to your The Gears account"
               if self.mode == "login"
               else "Sign up and start writing with The Gears")
        tk.Label(hdr, text=sub, font=FONTS["small"],
                 fg=COLORS["text_grey"],
                 bg=COLORS["background_alt"]).pack(pady=(2, 16))

    # ── LOGIN body ────────────────────────────────────────────────────────────

    def _build_login_body(self, parent, W):
        """Login: footer anchored bottom-first, fields above."""
        ENTRY_W = W - 68

        # ── Footer packed FIRST so it anchors to the bottom ───────────────
        footer = tk.Frame(parent, bg=COLORS["card"])
        footer.pack(side="bottom", fill="x", padx=34, pady=(0, 16))

        tk.Frame(footer, bg=COLORS["border"], height=1).pack(fill="x", pady=(0, 12))

        bottom = tk.Frame(footer, bg=COLORS["card"])
        bottom.pack()
        tk.Label(bottom, text="Don't have an account?  ",
                 font=FONTS["small"], fg=COLORS["text_mid"],
                 bg=COLORS["card"]).pack(side="left")
        sw = tk.Label(bottom, text="Sign up",
                      font=FONTS["small_bold"],
                      fg=COLORS["primary_orange"], bg=COLORS["card"],
                      cursor="hand2")
        sw.pack(side="left")
        sw.bind("<Enter>", lambda e: sw.config(fg=COLORS["primary_orange_dark"]))
        sw.bind("<Leave>", lambda e: sw.config(fg=COLORS["primary_orange"]))
        sw.bind("<Button-1>", lambda e: self._switch("signup"))

        # ── Fields above footer ───────────────────────────────────────────
        body = tk.Frame(parent, bg=COLORS["card"])
        body.pack(fill="both", expand=True, padx=34, pady=(20, 0))

        self.entries["email"] = RoundedEntry(
            body, "Email", "you@example.com", width=ENTRY_W)
        self.entries["email"].pack(pady=(0, 10))

        self.entries["password"] = RoundedEntry(
            body, "Password", "••••••••", show="•",
            width=ENTRY_W, has_toggle=True)
        self.entries["password"].pack(pady=(0, 6))

        tk.Label(body, text="Forgot password?", font=FONTS["small"],
                 fg=COLORS["text_grey"], bg=COLORS["card"],
                 cursor="hand2", anchor="e").pack(fill="x", pady=(0, 20))

        self.submit_btn = RoundedButton(
            body, text="Log in", command=self._submit,
            width=ENTRY_W, height=44,
            bg=COLORS["primary_orange"], fg=COLORS["white"],
            hover_bg=COLORS["primary_orange_dark"], radius=22)
        self.submit_btn.pack(pady=(0, 0))

    # ── SIGNUP body ───────────────────────────────────────────────────────────

    def _build_signup_body(self, parent, W):
        """
        Signup layout — footer anchored to bottom FIRST so it never gets pushed off:
          ┌──────────────┐
          │ scrollable   │  ← fills remaining space
          ├──────────────┤
          │ submit btn   │  ← always visible (packed bottom first)
          │ divider      │
          │ footer link  │  ← always visible
          └──────────────┘
        """
        ENTRY_W = W - 68

        # ── Footer packed FIRST so it always anchors to the bottom ────────
        footer = tk.Frame(parent, bg=COLORS["card"])
        footer.pack(side="bottom", fill="x", padx=34, pady=(8, 14))

        self.submit_btn = RoundedButton(
            footer, text="Sign up", command=self._submit,
            width=ENTRY_W, height=44,
            bg=COLORS["primary_orange"], fg=COLORS["white"],
            hover_bg=COLORS["primary_orange_dark"], radius=22)
        self.submit_btn.pack(pady=(0, 12))

        tk.Frame(footer, bg=COLORS["border"], height=1).pack(
            fill="x", pady=(0, 10))

        bottom = tk.Frame(footer, bg=COLORS["card"])
        bottom.pack()
        tk.Label(bottom, text="Already have an account?  ",
                 font=FONTS["small"], fg=COLORS["text_mid"],
                 bg=COLORS["card"]).pack(side="left")
        sw = tk.Label(bottom, text="Log in",
                      font=FONTS["small_bold"],
                      fg=COLORS["primary_orange"], bg=COLORS["card"],
                      cursor="hand2")
        sw.pack(side="left")
        sw.bind("<Enter>", lambda e: sw.config(fg=COLORS["primary_orange_dark"]))
        sw.bind("<Leave>", lambda e: sw.config(fg=COLORS["primary_orange"]))
        sw.bind("<Button-1>", lambda e: self._switch("login"))

        # ── Scrollable form packed AFTER footer (fills remaining space) ───
        scroll_outer = tk.Frame(parent, bg=COLORS["card"])
        scroll_outer.pack(fill="both", expand=True, padx=34, pady=(14, 0))

        sc = tk.Canvas(scroll_outer, bg=COLORS["card"],
                       highlightthickness=0, bd=0)
        sc.pack(side="left", fill="both", expand=True)

        vsb = tk.Scrollbar(scroll_outer, orient="vertical", command=sc.yview,
                           width=8, relief="flat", bd=0, highlightthickness=0,
                           bg=COLORS["background_alt"],
                           troughcolor=COLORS["background"],
                           activebackground=COLORS["primary_orange_light"])
        vsb.pack(side="right", fill="y")
        sc.configure(yscrollcommand=vsb.set)

        form = tk.Frame(sc, bg=COLORS["card"])
        fw   = sc.create_window((0, 0), window=form, anchor="nw")

        form.bind("<Configure>",
                  lambda e: sc.configure(scrollregion=sc.bbox("all")))
        sc.bind("<Configure>",
                lambda e: sc.itemconfig(fw, width=e.width))

        sc.bind("<Enter>",
                lambda e: sc.bind_all("<MouseWheel>",
                    lambda ev: sc.yview_scroll(int(-1*(ev.delta/120)), "units")))
        sc.bind("<Leave>",
                lambda e: sc.unbind_all("<MouseWheel>"))

        # ── Fields ────────────────────────────────────────────────────────
        def field(key, label, ph, **kw):
            e = RoundedEntry(form, label, ph, width=ENTRY_W, **kw)
            e.pack(pady=(0, 8))
            self.entries[key] = e

        field("last_name",   "Last Name",         "Dela Cruz")
        field("first_name",  "First Name",         "Juan")
        field("middle_name", "Middle Name",        "Reyes (Optional)")
        field("username",    "Username",           "juanwriter")
        field("email",       "Email",              "you@example.com")
        field("password",    "Password",           "••••••••",
              show="•", has_toggle=True)

        # Password strength indicator
        strength_row = tk.Frame(form, bg=COLORS["card"])
        strength_row.pack(fill="x", pady=(0, 8))

        self._strength_bar_frame = tk.Frame(strength_row, bg=COLORS["border"],
                                            height=4)
        self._strength_bar_frame.pack(fill="x", pady=(0, 4))
        self._strength_bar = tk.Frame(self._strength_bar_frame,
                                      bg=COLORS["primary_orange"],
                                      height=4, width=0)
        self._strength_bar.place(x=0, y=0, height=4)

        self.strength_label = tk.Label(strength_row, text="Strength: —",
                                       font=FONTS["small"],
                                       fg=COLORS["text_light"],
                                       bg=COLORS["card"], anchor="w")
        self.strength_label.pack(fill="x")

        self.entries["password"].entry.bind("<KeyRelease>", self._update_strength)

        field("confirm_pw",  "Confirm Password",   "••••••••",
              show="•", has_toggle=True)

    # ── Password strength ─────────────────────────────────────────────────────

    def _check_password_strength(self, password):
        import re
        score = 0
        if len(password) >= 8:            score += 1
        if re.search(r"[A-Z]", password) and re.search(r"[a-z]", password):
                                           score += 1
        if re.search(r"\d", password):    score += 1
        if re.search(r"[!@#$%^&*()]", password): score += 1
        levels = [
            ("Very Weak", "#E74C3C", 0.20),
            ("Weak",      "#E67E22", 0.45),
            ("Good",      "#F1C40F", 0.70),
            ("Strong",    "#2ECC71", 1.00),
        ]
        label, color, pct = levels[min(score - 1, 3)] if score else levels[0]
        if score == 0:
            pct = 0.05
        return label, color, pct

    def _update_strength(self, event=None):
        pw = self.entries["password"].get()
        if not pw:
            self.strength_label.config(text="Strength: —",
                                       fg=COLORS["text_light"])
            self._strength_bar.config(width=0)
            return

        label, color, pct = self._check_password_strength(pw)
        self.strength_label.config(text=f"Strength: {label}", fg=color)

        # Update bar width after geometry is known
        self.after_idle(lambda: self._animate_bar(color, pct))

    def _animate_bar(self, color, pct):
        try:
            total = self._strength_bar_frame.winfo_width()
            self._strength_bar.config(bg=color,
                                      width=max(1, int(total * pct)))
        except Exception:
            pass

    # ── Loading state ─────────────────────────────────────────────────────────

    def _set_loading(self, loading, text="Processing…"):
        self.loading = loading
        if hasattr(self, "submit_btn"):
            self.submit_btn.set_disabled(loading)
            default = "Log in" if self.mode == "login" else "Sign up"
            self.submit_btn.set_text(text if loading else default)

    # ── Submit ────────────────────────────────────────────────────────────────

    def _submit(self):
        if self.loading:
            return

        email    = self.entries["email"].get()
        password = self.entries["password"].get()

        if not email:
            messagebox.showerror("Error", "Please enter your email.", parent=self)
            return
        if not password:
            messagebox.showerror("Error", "Please enter your password.", parent=self)
            return

        if self.mode == "signup":
            self._submit_signup(email, password)
        else:
            self._submit_login(email, password)

    def _submit_signup(self, email, password):
        last_name   = self.entries["last_name"].get()
        first_name  = self.entries["first_name"].get()
        middle_name = self.entries["middle_name"].get()
        username    = self.entries["username"].get()
        confirm_pw  = self.entries["confirm_pw"].get()

        if not first_name or not last_name:
            messagebox.showerror("Error", "Please enter your full name.", parent=self)
            return
        if not username:
            messagebox.showerror("Error", "Please enter a username.", parent=self)
            return
        if password != confirm_pw:
            messagebox.showerror("Error", "Passwords do not match.", parent=self)
            return

        self._set_loading(True, "Creating account…")
        try:
            user_id = register_user(first_name, last_name, middle_name,
                                    username, email, password)
        except ValueError as e:
            self._set_loading(False)
            messagebox.showerror("Registration Failed", str(e), parent=self)
            return
        except Exception as e:
            self._set_loading(False)
            messagebox.showerror("Error", f"Something went wrong: {e}", parent=self)
            return

        self._set_loading(False)

        if not user_id:
            messagebox.showerror(
                "Registration Failed",
                "Email or username may already be in use.", parent=self)
            return

        self._open_verification_modal(user_id=user_id,
                                      email=email, password=password)

    def _submit_login(self, email, password):
        self._set_loading(True, "Logging in…")
        db_user = login_user(email, password)
        self._set_loading(False)

        if not db_user:
            messagebox.showerror("Error", "Invalid email or password.", parent=self)
            return

        if "is_verified" in db_user and not db_user["is_verified"]:
            messagebox.showwarning("Email Not Verified",
                                   "Please verify your email before logging in.",
                                   parent=self)
            self._open_verification_modal(user_id=db_user["id"],
                                          email=db_user["email"],
                                          password=password)
            return

        user = (db_user["first_name"], db_user["last_name"],
        db_user["email"], db_user["id"], db_user["role"],
        db_user.get("is_eic", False))

        if db_user.get("must_change_password"):
            self._open_change_password_modal(db_user)
            return

        self._close()
        self._route_by_role(user)

    # ── Verification ─────────────────────────────────────────────────────────

    def _open_verification_modal(self, user_id, email, password):
        def after_verified():
            db_user = login_user(email, password)
            if not db_user:
                messagebox.showerror(
                    "Login Failed",
                    "Account verified, but login failed. Please log in manually.",
                    parent=self.parent)
                AuthModal(self.parent, mode="login")
                return
            user = (db_user["first_name"], db_user["last_name"],
                    db_user["email"], db_user["id"], db_user["role"])
            self._route_by_role(user)

        self._close()
        VerificationModal(self.parent, email=email,
                          user_id=user_id, on_verified=after_verified)

    # ── Change password ───────────────────────────────────────────────────────

    def _open_change_password_modal(self, user):
        """Themed change-password dialog shown when must_change_password = True."""
        win = tk.Toplevel(self)
        win.title("Change Password")
        win.resizable(False, True)
        win.configure(bg=COLORS["card"])
        win.grab_set()
        win.transient(self)

        W = 380

        # Center on parent
        self.update_idletasks()
        px = self.winfo_rootx() + self.winfo_width()  // 2 - W // 2
        py = self.winfo_rooty() + self.winfo_height() // 2 - 200
        win.geometry(f"{W}x400+{px}+{py}")

        # Orange top bar
        tk.Frame(win, bg=COLORS["primary_orange"], height=5).pack(fill="x")

        inner = tk.Frame(win, bg=COLORS["card"])
        inner.pack(fill="both", expand=True, padx=32, pady=(20, 24))

        tk.Label(inner, text="Set Your New Password",
                 font=("Poppins", 14, "bold"),
                 fg=COLORS["primary_orange"],
                 bg=COLORS["card"]).pack(pady=(0, 4))
        tk.Label(inner,
                 text="Your account requires a password change\nbefore you can continue.",
                 font=FONTS["small"], fg=COLORS["text_grey"],
                 bg=COLORS["card"], justify="center").pack(pady=(0, 18))

        e_new = RoundedEntry(inner, "New Password", "••••••••",
                             show="•", width=W - 64, has_toggle=True)
        e_new.pack(pady=(0, 10))

        e_confirm = RoundedEntry(inner, "Confirm Password", "••••••••",
                                 show="•", width=W - 64, has_toggle=True)
        e_confirm.pack(pady=(0, 16))

        def submit():
            pw  = e_new.get()
            cpw = e_confirm.get()
            if not pw or not cpw:
                messagebox.showerror("Error", "All fields are required.", parent=win)
                return
            if pw != cpw:
                messagebox.showerror("Error", "Passwords do not match.", parent=win)
                return
            lbl, _, _ = self._check_password_strength(pw)
            if lbl in ("Very Weak", "Weak"):
                messagebox.showerror("Weak Password",
                                     "Please choose a stronger password.", parent=win)
                return

            import bcrypt
            from db import get_connection
            hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("""
                UPDATE users
                SET password = %s, must_change_password = FALSE
                WHERE id = %s
            """, (hashed, user["id"]))
            conn.commit()
            cur.close()
            conn.close()

            messagebox.showinfo("Success",
                                "Password updated successfully!", parent=win)
            win.destroy()
            self._close()
            self._route_by_role((user["first_name"], user["last_name"],
                     user["email"], user["id"], user["role"],
                     user.get("is_eic", False)))

        RoundedButton(inner, text="Save New Password", command=submit,
                      width=W - 64, height=44,
                      bg=COLORS["primary_orange"], fg=COLORS["white"],
                      hover_bg=COLORS["primary_orange_dark"],
                      radius=22).pack()

    # ── Routing ───────────────────────────────────────────────────────────────

    def _route_by_role(self, user):
        role = user[4] if len(user) > 4 else "user"
        root = self.parent
        root.current_user = user

        if role == "superadmin":
            if hasattr(root, "show_superadmin"):
                root.show_superadmin()
            else:
                from superadmin.superadmin_dashboard import SuperadminDashboard
                for w in root.winfo_children():
                    w.destroy()
                SuperadminDashboard(root, user=user)

        elif role == "admin":
            if hasattr(root, "show_admin"):
                root.show_admin()
            else:
                from admin.admin_dashboard import AdminDashboard
                for w in root.winfo_children():
                    w.destroy()
                AdminDashboard(root, user=user)

        else:
            root.show_articles(user)

    def _switch(self, new_mode):
        self._close()
        AuthModal(self.parent, mode=new_mode)