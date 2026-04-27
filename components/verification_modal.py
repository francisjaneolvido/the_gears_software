import os
import random
import smtplib
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from dotenv import load_dotenv

from theme import COLORS, FONTS, RADIUS
from services.auth_services import mark_user_verified


# =========================
# ENV + EMAIL CONFIG
# =========================

load_dotenv()

SENDER_EMAIL = "olvidofrancisjane2003@gmail.com"
EMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

verification_codes = {}


def generate_code():
    return str(random.randint(100000, 999999))


def send_verification_email(to_email, user_id):
    if not EMAIL_PASSWORD:
        raise ValueError(
            "GMAIL_APP_PASSWORD is missing. Add it to your .env file."
        )

    code = generate_code()

    body = f"""
Hello,

Your The Gears verification code is:

{code}

This code will expire in 5 minutes.

If you did not request this, please ignore this email.
"""

    msg = MIMEText(body)
    msg["Subject"] = "The Gears - Verification Code"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)

    verification_codes[user_id] = {
        "code": code,
        "email": to_email,
        "expires_at": datetime.now() + timedelta(minutes=5),
    }

    return True


def verify_user_code(user_id, code):
    data = verification_codes.get(user_id)

    if not data:
        return False

    if datetime.now() > data["expires_at"]:
        del verification_codes[user_id]
        return False

    if data["code"] != code:
        return False

    del verification_codes[user_id]
    mark_user_verified(user_id)
    return True


# =========================
# UI HELPERS
# =========================

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
    return canvas.create_polygon(
        rounded_polygon_points(x1, y1, x2, y2, r),
        smooth=True,
        splinesteps=36,
        **kwargs
    )


class VerificationCodeEntry(tk.Frame):
    def __init__(self, parent, width=300, height=48):
        super().__init__(parent, bg=COLORS["card"])

        self.placeholder = "Enter Code"
        self.is_placeholder = True

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
            1, 1, width - 1, height - 1,
            r=RADIUS["input"] + 5,
            fill=COLORS["input_bg"],
            outline=COLORS["border"],
            width=1,
        )

        self.entry = tk.Entry(
            self.canvas,
            font=("Poppins", 17, "bold"),
            fg=COLORS["text_light"],
            bg=COLORS["input_bg"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            insertbackground=COLORS["primary_orange"],
            justify="center",
        )

        self.canvas.create_window(
            width // 2,
            height // 2,
            width=width - 28,
            window=self.entry,
        )

        self.entry.insert(0, self.placeholder)

        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<KeyRelease>", self._limit_code)
        self.canvas.bind("<Button-1>", lambda e: self.entry.focus_set())

    def _focus_in(self, event=None):
        self.canvas.itemconfig(self.bg_id, outline=COLORS["border_focus"], width=2)

        if self.is_placeholder:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=COLORS["text_dark"])
            self.is_placeholder = False

    def _focus_out(self, event=None):
        self.canvas.itemconfig(self.bg_id, outline=COLORS["border"], width=1)

        if not self.entry.get().strip():
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=COLORS["text_light"])
            self.is_placeholder = True

    def _limit_code(self, event=None):
        if self.is_placeholder:
            return

        value = self.entry.get()
        clean = "".join(ch for ch in value if ch.isdigit())[:6]

        if clean != value:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, clean)

    def get(self):
        if self.is_placeholder:
            return ""
        return self.entry.get().strip()


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
            1, 1, width - 1, height - 1,
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

    def set_disabled(self, disabled):
        self.disabled = disabled

        if disabled:
            self.itemconfig(
                self.shape,
                fill=COLORS["text_light"],
                outline=COLORS["text_light"],
            )
            self.config(cursor="arrow")
        else:
            self.itemconfig(
                self.shape,
                fill=self.default_bg,
                outline=self.default_bg,
            )
            self.config(cursor="hand2")

    def _on_enter(self, event=None):
        if not self.disabled:
            self.itemconfig(self.shape, fill=self.hover_bg, outline=self.hover_bg)

    def _on_leave(self, event=None):
        if not self.disabled:
            self.itemconfig(self.shape, fill=self.default_bg, outline=self.default_bg)

    def _on_click(self, event=None):
        if not self.disabled and self.command:
            self.command()


class LoadingSpinner(tk.Canvas):
    def __init__(self, parent, size=22):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
        )

        self.size = size
        self.angle = 0
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self._animate()

    def stop(self):
        self.running = False
        self.delete("all")

    def _animate(self):
        if not self.running:
            return

        self.delete("all")
        self.create_arc(
            3, 3,
            self.size - 3,
            self.size - 3,
            start=self.angle,
            extent=110,
            style="arc",
            outline=COLORS["primary_orange"],
            width=3,
        )

        self.angle = (self.angle + 18) % 360
        self.after(50, self._animate)


# =========================
# VERIFICATION MODAL
# =========================

class VerificationModal(tk.Toplevel):
    def __init__(
        self,
        parent,
        email,
        user_id,
        on_verified=None,
    ):
        super().__init__(parent)

        self.parent = parent
        self.email = email
        self.user_id = user_id
        self.on_verified = on_verified

        self.card_w = 390
        self.card_h = 465
        self.resend_seconds = 30
        self.loading = False
        self.closed = False

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLORS["card"])

        self._build_overlay()
        self._center()
        self._build_modal()
        self._send_initial_code()

        self.grab_set()
        self.bind("<Escape>", lambda e: self._close())

    def _build_overlay(self):
        self.overlay = tk.Toplevel(self.parent)
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-alpha", 0.35)
        self.overlay.configure(bg=COLORS["navy"])

        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()

        self.overlay.geometry(f"{pw}x{ph}+{px}+{py}")
        self.overlay.lift()

    def _center(self):
        self.update_idletasks()

        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()

        x = px + (pw - self.card_w) // 2
        y = py + (ph - self.card_h) // 2

        self.geometry(f"{self.card_w}x{self.card_h}+{x}+{y}")

    def _build_modal(self):
        outer = tk.Frame(self, bg=COLORS["card"])
        outer.pack(fill="both", expand=True)

        shadow_1 = tk.Frame(outer, bg="#D8D2CB")
        shadow_1.place(x=7, y=9, relwidth=1, relheight=1, width=-14, height=-16)

        shadow_2 = tk.Frame(outer, bg="#E7E1DA")
        shadow_2.place(x=4, y=5, relwidth=1, relheight=1, width=-10, height=-12)

        wrap = tk.Frame(outer, bg=COLORS["card"])
        wrap.place(x=0, y=0, relwidth=1, relheight=1, width=-8, height=-12)

        canvas = tk.Canvas(
            wrap,
            bg=COLORS["card"],
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill="both", expand=True)

        cw = self.card_w - 8
        ch = self.card_h - 12

        draw_rounded_rect(
            canvas,
            2, 2, cw - 2, ch - 2,
            r=RADIUS["modal"] + 8,
            fill=COLORS["card"],
            outline=COLORS["border"],
            width=1,
        )

        draw_rounded_rect(
            canvas,
            2, 2, cw - 2, 105,
            r=RADIUS["modal"] + 8,
            fill=COLORS["background_alt"],
            outline="",
        )

        canvas.create_rectangle(
            2, 64, cw - 2, 105,
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
            width=66,
            height=66,
            bg=COLORS["background_alt"],
            highlightthickness=0,
            bd=0,
        )
        logo.create_oval(
            3, 3, 63, 63,
            fill=COLORS["white"],
            outline=COLORS["border"],
            width=1,
        )
        logo.create_text(
            33,
            33,
            text="TG",
            fill=COLORS["primary_orange"],
            font=("Poppins", 16, "bold"),
        )
        canvas.create_window(cw // 2, 55, window=logo)

        content = tk.Frame(canvas, bg=COLORS["card"])
        canvas.create_window(
            cw // 2,
            125,
            anchor="n",
            window=content,
            width=cw - 58,
        )

        tk.Label(
            content,
            text="Verify Your Email",
            font=("Hedvig Letters Serif 24pt", 22, "bold"),
            fg=COLORS["navy"],
            bg=COLORS["card"],
        ).pack(pady=(4, 8))

        tk.Label(
            content,
            text=f"Enter the 6-digit code sent to\n{self.email}.",
            font=FONTS["small"],
            fg=COLORS["text_grey"],
            bg=COLORS["card"],
            justify="center",
        ).pack(pady=(0, 18))

        self.code_entry = VerificationCodeEntry(content, width=300, height=48)
        self.code_entry.pack(pady=(0, 16))

        self.verify_btn = RoundedButton(
            content,
            text="Verify Account",
            command=self._verify,
            width=300,
            height=44,
            bg=COLORS["primary_orange"],
            fg=COLORS["white"],
            hover_bg=COLORS["primary_orange_dark"],
            radius=22,
        )
        self.verify_btn.pack(pady=(0, 12))

        status_row = tk.Frame(content, bg=COLORS["card"])
        status_row.pack(pady=(0, 10))

        self.spinner = LoadingSpinner(status_row, size=22)
        self.spinner.pack(side="left", padx=(0, 8))

        self.status_lbl = tk.Label(
            status_row,
            text="Preparing verification...",
            font=FONTS["small"],
            fg=COLORS["text_grey"],
            bg=COLORS["card"],
        )
        self.status_lbl.pack(side="left")

        resend_row = tk.Frame(content, bg=COLORS["card"])
        resend_row.pack()

        tk.Label(
            resend_row,
            text="Didn't receive a code? ",
            font=FONTS["small"],
            fg=COLORS["text_grey"],
            bg=COLORS["card"],
        ).pack(side="left")

        self.resend_lbl = tk.Label(
            resend_row,
            text="Resend",
            font=FONTS["small_bold"],
            fg=COLORS["text_light"],
            bg=COLORS["card"],
            cursor="arrow",
        )
        self.resend_lbl.pack(side="left")
        self.resend_lbl.bind("<Button-1>", lambda e: self._resend())

    def _set_loading(self, loading, text="Processing..."):
        self.loading = loading

        if loading:
            self.spinner.start()
            self.status_lbl.config(text=text)
            self.verify_btn.set_disabled(True)
            self.verify_btn.set_text(text)
        else:
            self.spinner.stop()
            self.verify_btn.set_disabled(False)
            self.verify_btn.set_text("Verify Account")

    def _send_initial_code(self):
        self._set_loading(True, "Sending code...")

        try:
            send_verification_email(self.email, self.user_id)
            self.status_lbl.config(text="Code sent. Check your email.")
            self._start_countdown()
        except Exception as e:
            self.status_lbl.config(text="Failed to send code.")
            messagebox.showerror("Email Error", str(e), parent=self)

        self._set_loading(False)

    def _start_countdown(self):
        self.resend_seconds = 30
        self._tick_countdown()

    def _tick_countdown(self):
        if self.closed:
            return

        if self.resend_seconds > 0:
            self.resend_lbl.config(
                text=f"Resend in {self.resend_seconds}s",
                fg=COLORS["text_light"],
                cursor="arrow",
            )
            self.resend_seconds -= 1
            self.after(1000, self._tick_countdown)
        else:
            self.resend_lbl.config(
                text="Resend",
                fg=COLORS["primary_orange"],
                cursor="hand2",
            )

    def _verify(self):
        if self.loading:
            return

        code = self.code_entry.get()

        if not code:
            messagebox.showerror(
                "Verification Error",
                "Please enter your verification code.",
                parent=self,
            )
            return

        if len(code) != 6:
            messagebox.showerror(
                "Verification Error",
                "Verification code must be 6 digits.",
                parent=self,
            )
            return

        self._set_loading(True, "Verifying...")

        try:
            ok = verify_user_code(self.user_id, code)
        except Exception as e:
            self._set_loading(False)
            messagebox.showerror("Verification Error", str(e), parent=self)
            return

        self._set_loading(False)

        if not ok:
            messagebox.showerror(
                "Verification Failed",
                "Invalid or expired verification code.",
                parent=self,
            )
            return

        messagebox.showinfo(
            "Account Verified",
            "Your account has been verified successfully.",
            parent=self,
        )

        self._close()

        if self.on_verified:
            self.on_verified()

    def _resend(self):
        if self.loading or self.resend_seconds > 0:
            return

        self._set_loading(True, "Sending new code...")

        try:
            send_verification_email(self.email, self.user_id)
            self.status_lbl.config(text="New code sent. Check your email.")
            self._start_countdown()
        except Exception as e:
            self.status_lbl.config(text="Failed to resend code.")
            messagebox.showerror("Resend Failed", str(e), parent=self)

        self._set_loading(False)

    def _close(self):
        self.closed = True

        try:
            self.spinner.stop()
        except Exception:
            pass

        try:
            self.grab_release()
        except Exception:
            pass

        try:
            self.overlay.destroy()
        except Exception:
            pass

        self.destroy()


# =========================
# TEST
# =========================

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1100x720")
    root.configure(bg=COLORS["background"])

    tk.Button(
        root,
        text="Open Verification Modal",
        command=lambda: VerificationModal(
            root,
            email="olvidofrancisjane2003@gmail.com",
            user_id=1,
            on_verified=lambda: messagebox.showinfo("Success", "Testing successful!"),
        ),
    ).pack(pady=80)

    root.mainloop()