import os
import random
import string
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


EMAIL_ADDRESS  = os.getenv("SENDER_EMAIL", os.getenv("GMAIL_APP_PASSWORD", ""))
EMAIL_PASSWORD = os.getenv("SENDER_PASSWORD", os.getenv("GMAIL_APP_PASSWORD", ""))

_verification_store = {}


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def generate_code() -> str:
    """6-digit numeric OTP for email verification."""
    return str(random.randint(100000, 999999))


def generate_otp(length: int = 6) -> str:
    """6-digit numeric OTP for admin login."""
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _send(to_email: str, subject: str, html_body: str, plain_body: str) -> bool:
    """Internal helper — sends a multipart (plain + HTML) email via Gmail SMTP."""
    if not EMAIL_PASSWORD:
        raise ValueError(
            "GMAIL_APP_PASSWORD environment variable is not set.\n"
            "Run:  set GMAIL_APP_PASSWORD=your_app_password"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_ADDRESS
    msg["To"]      = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body,  "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

    return True


# ═══════════════════════════════════════════════════════════════
#  Verification code  (existing flow — unchanged behaviour)
# ═══════════════════════════════════════════════════════════════

def send_verification_email(to_email: str, user_id=None) -> bool:
    """Send a 6-digit OTP verification code. Stores it for 5 minutes."""
    code = generate_code()

    plain = f"""Hello,

Your The Gears verification code is:

{code}

This code will expire in 5 minutes.

If you did not request this, please ignore this email.
"""

    html = f"""
<div style="font-family:'Poppins',Arial,sans-serif;max-width:480px;
            margin:0 auto;border:1px solid #f0c2a0;border-radius:12px;
            overflow:hidden;">
  <div style="background:#f5821f;padding:22px 28px;">
    <h1 style="color:#fff;margin:0;font-size:20px;">The Gears</h1>
    <p style="color:#ffe0c0;margin:4px 0 0;font-size:12px;">
      Official Campus Publication
    </p>
  </div>
  <div style="padding:28px;">
    <p style="font-size:14px;color:#333;margin:0 0 14px;">Hello,</p>
    <p style="font-size:14px;color:#555;margin:0 0 20px;line-height:1.6;">
      Your verification code for <strong>The Gears</strong> is:
    </p>
    <div style="background:#fff8f0;border:1px solid #f5c08a;
                border-radius:8px;padding:16px 24px;text-align:center;
                margin-bottom:20px;">
      <p style="margin:0 0 4px;font-size:11px;color:#888;
                text-transform:uppercase;letter-spacing:0.08em;">
        Verification Code
      </p>
      <p style="margin:0;font-size:32px;font-weight:700;
                color:#f5821f;letter-spacing:0.18em;
                font-family:'Courier New',monospace;">
        {code}
      </p>
      <p style="margin:6px 0 0;font-size:12px;color:#aaa;">
        Expires in 5 minutes
      </p>
    </div>
    <p style="font-size:12px;color:#aaa;line-height:1.6;">
      If you did not request this code, please ignore this email.
    </p>
  </div>
  <div style="background:#fff6f0;padding:12px 28px;
              border-top:1px solid #f0c2a0;">
    <p style="margin:0;font-size:11px;color:#bbb;">
      © 2025 The Gears Campus Publication ·
      Write without favor. Express without fear.
    </p>
  </div>
</div>
"""

    _send(to_email, "The Gears — Verification Code", html, plain)

    key = user_id or to_email
    _verification_store[key] = {
        "code":       code,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "email":      to_email,
    }

    return True


def verify_user_code(user_id_or_email: str, code: str) -> bool:
    """Return True if the code matches and has not expired. Deletes on success."""
    data = _verification_store.get(user_id_or_email)

    if not data:
        return False

    if datetime.now() > data["expires_at"]:
        del _verification_store[user_id_or_email]
        return False

    if data["code"] != code:
        return False

    del _verification_store[user_id_or_email]
    return True


def resend_verification_code(user_id_or_email: str) -> bool:
    """Resend a fresh code to the same email that was registered."""
    data = _verification_store.get(user_id_or_email)

    if not data:
        return False

    return send_verification_email(data["email"], user_id_or_email)


# ═══════════════════════════════════════════════════════════════
#  Admin credentials email  (new admin / promoted user)
# ═══════════════════════════════════════════════════════════════

def send_admin_credentials(to_email: str,
                           recipient_name: str,
                           otp_password: str) -> bool:
    """
    Send a welcome email containing the generated one-time password
    to a newly created or promoted admin account.
    """
    plain = f"""Hello {recipient_name},

You have been granted Admin access to The Gears publication platform.

Your temporary login code is:
{otp_password}

Please log in and change this password immediately.

If you did not expect this email, contact your superadmin.

— The Gears Team
"""

    html = f"""
<div style="font-family:'Poppins',Arial,sans-serif;max-width:480px;
            margin:0 auto;border:1px solid #f0c2a0;border-radius:12px;
            overflow:hidden;">
  <div style="background:#f5821f;padding:22px 28px;">
    <h1 style="color:#fff;margin:0;font-size:20px;">The Gears</h1>
    <p style="color:#ffe0c0;margin:4px 0 0;font-size:12px;">
      Official Campus Publication
    </p>
  </div>
  <div style="padding:28px;">
    <p style="font-size:14px;color:#333;margin:0 0 12px;">
      Hello, <strong>{recipient_name}</strong>,
    </p>
    <p style="font-size:14px;color:#555;margin:0 0 20px;line-height:1.6;">
      You have been granted <strong>Admin access</strong> to
      <em>The Gears</em> platform. Use the temporary password below
      to log in — please change it immediately after signing in.
    </p>
    <div style="background:#fff8f0;border:1px solid #f5c08a;
                border-radius:8px;padding:16px 24px;text-align:center;
                margin-bottom:20px;">
      <p style="margin:0 0 6px;font-size:11px;color:#888;
                text-transform:uppercase;letter-spacing:0.08em;">
        Temporary Code
      </p>
      <p style="margin:0;font-size:22px;font-weight:700;
                color:#f5821f;letter-spacing:0.1em;
                font-family:'Courier New',monospace;">
        {otp_password}
      </p>
    </div>
    <p style="font-size:12px;color:#aaa;line-height:1.6;">
      Do <strong>not</strong> share this password with anyone.
      If you did not expect this email, please contact your superadmin.
    </p>
  </div>
  <div style="background:#fff6f0;padding:12px 28px;
              border-top:1px solid #f0c2a0;">
    <p style="margin:0;font-size:11px;color:#bbb;">
      © 2025 The Gears Campus Publication
    </p>
  </div>
</div>
"""

    return _send(to_email,
                 "Your Admin Account — The Gears Publication",
                 html, plain)


# ═══════════════════════════════════════════════════════════════
#  Role change notification  (promote / demote)
# ═══════════════════════════════════════════════════════════════

def send_role_change_notification(to_email: str,
                                  recipient_name: str,
                                  new_role: str) -> bool:
    """
    Notify a user that their role has changed.
    new_role accepts: "admin" | "superadmin" | "user"
    """
    labels = {
        "superadmin": "Superadmin",
        "admin":      "Admin",
        "user":       "Regular User",
    }
    label = labels.get(new_role, new_role.title())

    plain = f"""Hello {recipient_name},

Your account role on The Gears platform has been updated to: {label}

If you believe this was a mistake, contact your superadmin immediately.

— The Gears Team
"""

    html = f"""
<div style="font-family:'Poppins',Arial,sans-serif;max-width:480px;
            margin:0 auto;border:1px solid #f0c2a0;border-radius:12px;
            overflow:hidden;">
  <div style="background:#f5821f;padding:22px 28px;">
    <h1 style="color:#fff;margin:0;font-size:20px;">The Gears</h1>
    <p style="color:#ffe0c0;margin:4px 0 0;font-size:12px;">
      Official Campus Publication
    </p>
  </div>
  <div style="padding:28px;">
    <p style="font-size:14px;color:#333;margin:0 0 12px;">
      Hello, <strong>{recipient_name}</strong>,
    </p>
    <p style="font-size:14px;color:#555;margin:0 0 16px;line-height:1.6;">
      Your account role on <em>The Gears</em> platform has been updated to:
    </p>
    <div style="background:#fff8f0;border:1px solid #f5c08a;
                border-radius:8px;padding:14px 24px;text-align:center;
                margin-bottom:20px;">
      <p style="margin:0;font-size:20px;font-weight:700;
                color:#f5821f;letter-spacing:0.04em;">
        {label}
      </p>
    </div>
    <p style="font-size:12px;color:#aaa;line-height:1.6;">
      If you believe this was a mistake, contact your superadmin immediately.
    </p>
  </div>
  <div style="background:#fff6f0;padding:12px 28px;
              border-top:1px solid #f0c2a0;">
    <p style="margin:0;font-size:11px;color:#bbb;">
      © 2025 The Gears Campus Publication
    </p>
  </div>
</div>
"""

    return _send(to_email,
                 "Your Role Has Been Updated — The Gears",
                 html, plain)