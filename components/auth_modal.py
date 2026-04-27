import tkinter as tk
from tkinter import messagebox

from theme import COLORS, FONTS, RADIUS
from services.auth_services import login_user, register_user
from components.verification_modal import VerificationModal


def rounded_polygon_points(x1, y1, x2, y2, r):
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


def draw_rounded_rect(canvas, x1, y1, x2, y2, r=12, **kwargs):
    pts = rounded_polygon_points(x1, y1, x2, y2, r)
    return canvas.create_polygon(pts, smooth=True, splinesteps=36, **kwargs)


class RoundedEntry(tk.Frame):
    def __init__(
        self,
        parent,
        label,
        placeholder="",
        show=None,
        width=300,
        height=46,
        has_toggle=False,
    ):
        super().__init__(parent, bg=COLORS["card"])

        self.placeholder = placeholder
        self.real_show = show
        self.is_placeholder = True
        self.hidden = True if show else False

        tk.Label(
            self,
            text=label,
            font=FONTS["small_bold"],
            fg=COLORS["text_dark"],
            bg=COLORS["card"],
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=COLORS["card"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.bg_id = draw_rounded_rect(
            self.canvas,
            1,
            1,
            width - 1,
            height - 1,
            r=RADIUS["input"] + 4,
            fill=COLORS["input_bg"],
            outline=COLORS["border"],
            width=1,
        )

        entry_width = width - (48 if has_toggle else 24)

        self.entry = tk.Entry(
            self.canvas,
            font=FONTS["input"],
            fg=COLORS["text_light"],
            bg=COLORS["input_bg"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            insertbackground=COLORS["primary_orange"],
            width=1,
        )

        self.canvas.create_window(
            14,
            height // 2,
            anchor="w",
            width=entry_width,
            window=self.entry,
        )

        self.entry.insert(0, placeholder)

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<FocusIn>", self._focus_style_on, add="+")
        self.entry.bind("<FocusOut>", self._focus_style_off, add="+")

        self.canvas.bind("<Button-1>", lambda e: self.entry.focus_set())

        if has_toggle:
            self.toggle_btn = tk.Label(
                self.canvas,
                text="◌",
                font=("Poppins", 10),
                fg=COLORS["text_light"],
                bg=COLORS["input_bg"],
                cursor="hand2",
            )
            self.canvas.create_window(width - 22, height // 2, window=self.toggle_btn)
            self.toggle_btn.bind("<Button-1>", self._toggle_password)

    def _focus_style_on(self, _):
        self.canvas.itemconfig(self.bg_id, outline=COLORS["border_focus"], width=1.5)

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

    def get(self):
        return "" if self.is_placeholder else self.entry.get().strip()


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command,
        width=300,
        height=44,
        bg=COLORS["primary_orange"],
        fg=COLORS["white"],
        hover_bg=COLORS["primary_orange_dark"],
        radius=22,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )

        self.command = command
        self.default_bg = bg
        self.hover_bg = hover_bg
        self.disabled = False

        self.shape = draw_rounded_rect(
            self,
            1,
            1,
            width - 1,
            height - 1,
            r=radius,
            fill=bg,
            outline=bg,
        )

        self.text_id = self.create_text(
            width // 2,
            height // 2,
            text=text,
            fill=fg,
            font=FONTS["button"],
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_text(self, text):
        self.itemconfig(self.text_id, text=text)

    def set_disabled(self, disabled=True):
        self.disabled = disabled
        color = COLORS["text_light"] if disabled else self.default_bg
        self.itemconfig(self.shape, fill=color, outline=color)

    def _on_enter(self, _):
        if not self.disabled:
            self.itemconfig(self.shape, fill=self.hover_bg, outline=self.hover_bg)

    def _on_leave(self, _):
        if not self.disabled:
            self.itemconfig(self.shape, fill=self.default_bg, outline=self.default_bg)

    def _on_click(self, _):
        if not self.disabled and self.command:
            self.command()


class AuthModal(tk.Toplevel):
    def __init__(self, parent, mode="login"):
        super().__init__(parent)

        self.parent = parent
        self.mode = mode
        self.loading = False

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLORS["card"])

        self.card_w = 380 if mode == "login" else 420
        self.card_h = 500 if mode == "login" else 640

        self._build_overlay()
        self._center()
        self._build_modal()

        self.grab_set()
        self.bind("<Escape>", lambda e: self._close())

    def _build_overlay(self):
        self._overlay = tk.Toplevel(self.parent)
        self._overlay.overrideredirect(True)
        self._overlay.attributes("-alpha", 0.30)
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

        max_h = max(420, ph - 40)
        self.card_h = min(self.card_h, max_h)

        x = px + (pw - self.card_w) // 2
        y = py + (ph - self.card_h) // 2

        self.geometry(f"{self.card_w}x{self.card_h}+{x}+{y}")

    def _close(self):
        try:
            self.grab_release()
        except Exception:
            pass

        try:
            self._overlay.destroy()
        except Exception:
            pass

        self.destroy()

    def _build_modal(self):
        outer = tk.Frame(self, bg=COLORS["card"], bd=0, highlightthickness=0)
        outer.pack(fill="both", expand=True)

        shadow_1 = tk.Frame(outer, bg="#D8D2CB", bd=0, highlightthickness=0)
        shadow_1.place(x=6, y=8, relwidth=1, relheight=1, width=-12, height=-14)

        shadow_2 = tk.Frame(outer, bg="#E7E1DA", bd=0, highlightthickness=0)
        shadow_2.place(x=3, y=4, relwidth=1, relheight=1, width=-8, height=-10)

        card_wrap = tk.Frame(outer, bg=COLORS["card"], bd=0, highlightthickness=0)
        card_wrap.place(x=0, y=0, relwidth=1, relheight=1, width=-8, height=-12)

        canvas = tk.Canvas(
            card_wrap,
            bg=COLORS["card"],
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill="both", expand=True)

        cw = self.card_w - 8
        ch = self.card_h - 12

        draw_rounded_rect(
            canvas,
            2,
            2,
            cw - 2,
            ch - 2,
            r=RADIUS["modal"] + 6,
            fill=COLORS["card"],
            outline=COLORS["border"],
            width=1,
        )

        draw_rounded_rect(
            canvas,
            2,
            2,
            cw - 2,
            86,
            r=RADIUS["modal"] + 6,
            fill=COLORS["background_alt"],
            outline="",
        )

        canvas.create_rectangle(
            2,
            50,
            cw - 2,
            86,
            fill=COLORS["background_alt"],
            outline="",
        )

        close_btn = tk.Label(
            canvas,
            text="✕",
            font=("Poppins", 12, "bold"),
            fg=COLORS["text_mid"],
            bg=COLORS["background_alt"],
            cursor="hand2",
        )
        canvas.create_window(cw - 24, 24, window=close_btn)
        close_btn.bind("<Button-1>", lambda e: self._close())

        logo = tk.Canvas(
            canvas,
            width=54,
            height=54,
            bg=COLORS["background_alt"],
            highlightthickness=0,
            bd=0,
        )
        logo.create_oval(2, 2, 52, 52, fill=COLORS["white"], outline=COLORS["border"])
        logo.create_text(
            27,
            27,
            text="TG",
            fill=COLORS["primary_orange"],
            font=("Poppins", 15, "bold"),
        )
        canvas.create_window(cw // 2, 44, window=logo)

        content = tk.Frame(canvas, bg=COLORS["card"])
        canvas.create_window(cw // 2, 96, anchor="n", window=content, width=cw - 52)

        title = "Welcome Back" if self.mode == "login" else "Create your account"
        subtitle = (
            "Log in to your The Gears account"
            if self.mode == "login"
            else "Sign up to start writing with The Gears"
        )

        tk.Label(
            content,
            text=title,
            font=("Poppins", 20, "bold"),
            fg=COLORS["navy"],
            bg=COLORS["card"],
        ).pack(pady=(6, 4))

        tk.Label(
            content,
            text=subtitle,
            font=FONTS["small"],
            fg=COLORS["text_grey"],
            bg=COLORS["card"],
        ).pack(pady=(0, 18))

        self.entries = {}

        if self.mode == "login":
            self._build_login_form(content)
        else:
            self._build_signup_form(content)

    def _build_login_form(self, parent):
        form = tk.Frame(parent, bg=COLORS["card"])
        form.pack(fill="x")

        self.entries["email"] = RoundedEntry(form, "Email", "you@example.com", width=300)
        self.entries["email"].pack(pady=(0, 10))

        self.entries["password"] = RoundedEntry(
            form,
            "Password",
            "••••••••",
            show="•",
            width=300,
            has_toggle=True,
        )
        self.entries["password"].pack(pady=(0, 8))

        forgot = tk.Label(
            form,
            text="Forgot password?",
            font=FONTS["small"],
            fg=COLORS["text_grey"],
            bg=COLORS["card"],
            cursor="hand2",
        )
        forgot.pack(anchor="e", pady=(0, 18))

        self.submit_btn = RoundedButton(
            parent,
            text="Log in",
            command=self._submit,
            width=300,
            height=42,
            bg=COLORS["primary_orange"],
            fg=COLORS["white"],
            hover_bg=COLORS["primary_orange_dark"],
            radius=22,
        )
        self.submit_btn.pack(pady=(0, 14))

        divider = tk.Frame(parent, bg=COLORS["border"], height=1)
        divider.pack(fill="x", pady=(0, 10))

        bottom = tk.Frame(parent, bg=COLORS["card"])
        bottom.pack()

        tk.Label(
            bottom,
            text="Don't have an account? ",
            font=FONTS["small"],
            fg=COLORS["text_mid"],
            bg=COLORS["card"],
        ).pack(side="left")

        switch = tk.Label(
            bottom,
            text="Sign up",
            font=FONTS["small_bold"],
            fg=COLORS["primary_orange"],
            bg=COLORS["card"],
            cursor="hand2",
        )
        switch.pack(side="left")
        switch.bind("<Button-1>", lambda e: self._switch("signup"))

    def _build_signup_form(self, parent):
        body_wrap = tk.Frame(parent, bg=COLORS["card"])
        body_wrap.pack(fill="both", expand=True)

        scroll_canvas = tk.Canvas(
            body_wrap,
            width=320,
            height=355,
            bg=COLORS["card"],
            highlightthickness=0,
            bd=0,
        )
        scroll_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(
            body_wrap,
            orient="vertical",
            command=scroll_canvas.yview,
            width=10,
            relief="flat",
            bd=0,
            highlightthickness=0,
            activebackground=COLORS["border"],
            bg=COLORS["background_alt"],
            troughcolor=COLORS["background"],
        )
        scrollbar.pack(side="right", fill="y")

        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        form = tk.Frame(scroll_canvas, bg=COLORS["card"])
        form_window = scroll_canvas.create_window((0, 0), window=form, anchor="nw")

        form.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")),
        )

        scroll_canvas.bind(
            "<Configure>",
            lambda e: scroll_canvas.itemconfig(form_window, width=e.width),
        )

        def _wheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        scroll_canvas.bind("<Enter>", lambda e: scroll_canvas.bind_all("<MouseWheel>", _wheel))
        scroll_canvas.bind("<Leave>", lambda e: scroll_canvas.unbind_all("<MouseWheel>"))

        self.entries["last_name"] = RoundedEntry(form, "Last Name", "Dela Cruz", width=300)
        self.entries["last_name"].pack(pady=(0, 8))

        self.entries["first_name"] = RoundedEntry(form, "First Name", "Juan", width=300)
        self.entries["first_name"].pack(pady=(0, 8))

        self.entries["middle_name"] = RoundedEntry(
            form,
            "Middle Name",
            "Reyes (Optional)",
            width=300,
        )
        self.entries["middle_name"].pack(pady=(0, 8))

        self.entries["username"] = RoundedEntry(form, "Username", "juanwriter", width=300)
        self.entries["username"].pack(pady=(0, 8))

        self.entries["email"] = RoundedEntry(form, "Email", "you@example.com", width=300)
        self.entries["email"].pack(pady=(0, 8))

        self.entries["password"] = RoundedEntry(
            form,
            "Password",
            "••••••••",
            show="•",
            width=300,
            has_toggle=True,
        )
        self.entries["password"].pack(pady=(0, 4))

        tk.Label(
            form,
            text="Strength: —",
            font=FONTS["small"],
            fg=COLORS["text_light"],
            bg=COLORS["card"],
            anchor="w",
        ).pack(fill="x", padx=6, pady=(0, 8))

        self.entries["confirm_pw"] = RoundedEntry(
            form,
            "Confirm Password",
            "••••••••",
            show="•",
            width=300,
            has_toggle=True,
        )
        self.entries["confirm_pw"].pack(pady=(0, 12))

        self.submit_btn = RoundedButton(
            parent,
            text="Sign up",
            command=self._submit,
            width=300,
            height=42,
            bg=COLORS["primary_orange"],
            fg=COLORS["white"],
            hover_bg=COLORS["primary_orange_dark"],
            radius=22,
        )
        self.submit_btn.pack(pady=(14, 14))

        divider = tk.Frame(parent, bg=COLORS["border"], height=1)
        divider.pack(fill="x", pady=(0, 10))

        bottom = tk.Frame(parent, bg=COLORS["card"])
        bottom.pack()

        tk.Label(
            bottom,
            text="Already have an account? ",
            font=FONTS["small"],
            fg=COLORS["text_mid"],
            bg=COLORS["card"],
        ).pack(side="left")

        switch = tk.Label(
            bottom,
            text="Log in",
            font=FONTS["small_bold"],
            fg=COLORS["primary_orange"],
            bg=COLORS["card"],
            cursor="hand2",
        )
        switch.pack(side="left")
        switch.bind("<Button-1>", lambda e: self._switch("login"))

    def _set_loading(self, loading, text="Processing..."):
        self.loading = loading

        if hasattr(self, "submit_btn"):
            self.submit_btn.set_disabled(loading)
            self.submit_btn.set_text(text if loading else ("Log in" if self.mode == "login" else "Sign up"))

    def _submit(self):
        if self.loading:
            return

        email = self.entries["email"].get()
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
        last_name = self.entries["last_name"].get()
        first_name = self.entries["first_name"].get()
        middle_name = self.entries["middle_name"].get()
        username = self.entries["username"].get()
        confirm_pw = self.entries["confirm_pw"].get()

        if not first_name or not last_name:
            messagebox.showerror("Error", "Please enter your full name.", parent=self)
            return

        if not username:
            messagebox.showerror("Error", "Please enter a username.", parent=self)
            return

        if password != confirm_pw:
            messagebox.showerror("Error", "Passwords do not match.", parent=self)
            return

        self._set_loading(True, "Creating account...")

        user_id = register_user(
            first_name,
            last_name,
            middle_name,
            username,
            email,
            password,
        )

        self._set_loading(False)

        if not user_id:
            messagebox.showerror(
                "Registration Failed",
                "Email or username may already be in use.",
                parent=self,
            )
            return

        self._open_verification_modal(
            user_id=user_id,
            email=email,
            password=password,
        )

    def _open_verification_modal(self, user_id, email, password):
        def after_verified():
            db_user = login_user(email, password)

            if not db_user:
                messagebox.showerror(
                    "Login Failed",
                    "Account verified, but login failed. Please log in manually.",
                    parent=self.parent,
                )
                AuthModal(self.parent, mode="login")
                return

            user = (
                db_user["first_name"],
                db_user["last_name"],
                db_user["email"],
                db_user["id"],
                db_user["role"],
            )

            self._route_by_role(user)

        self._close()

        VerificationModal(
            self.parent,
            email=email,
            user_id=user_id,
            on_verified=after_verified,
        )

    def _submit_login(self, email, password):
        self._set_loading(True, "Logging in...")

        db_user = login_user(email, password)

        self._set_loading(False)

        if not db_user:
            messagebox.showerror("Error", "Invalid email or password.", parent=self)
            return

        if "is_verified" in db_user and not db_user["is_verified"]:
            messagebox.showwarning(
                "Email Not Verified",
                "Please verify your email before logging in.",
                parent=self,
            )

            self._open_verification_modal(
                user_id=db_user["id"],
                email=db_user["email"],
                password=password,
            )
            return

        user = (
            db_user["first_name"],
            db_user["last_name"],
            db_user["email"],
            db_user["id"],
            db_user["role"],
        )

        self._close()
        self._route_by_role(user)

    def _route_by_role(self, user):
        role = user[4] if len(user) > 4 else "user"
        root = self.parent

        if role == "superadmin":
            if hasattr(root, "show_superadmin"):
                root.show_superadmin(user)
            else:
                from superadmin.superadmin_dashboard import SuperadminDashboard

                for w in root.winfo_children():
                    w.destroy()

                SuperadminDashboard(root, user=user)

        elif role == "admin":
            if hasattr(root, "show_admin"):
                root.show_admin(user)
            else:
                messagebox.showinfo(
                    "Admin Login",
                    f"Welcome, {user[0]}!\nAdmin dashboard coming soon.",
                    parent=root,
                )

        else:
            root.show_articles(user)

    def _switch(self, new_mode):
        self._close()
        AuthModal(self.parent, mode=new_mode)