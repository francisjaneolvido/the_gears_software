import os
import random
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText


EMAIL_ADDRESS = "olvidofrancisjane2003@gmail.com"

# Put your NEW app password in an environment variable:
# Windows CMD:
# set GMAIL_APP_PASSWORD=your_new_app_password
#
# PowerShell:
# $env:GMAIL_APP_PASSWORD="your_new_app_password"

EMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

_verification_store = {}


def generate_code():
    return str(random.randint(100000, 999999))


def send_verification_email(to_email, user_id=None):
    if not EMAIL_PASSWORD:
        raise ValueError("GMAIL_APP_PASSWORD environment variable is not set.")

    code = generate_code()

    subject = "The Gears - Verification Code"
    body = f"""
Hello,

Your The Gears verification code is:

{code}

This code will expire in 5 minutes.

If you did not request this, please ignore this email.
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

    key = user_id or to_email
    _verification_store[key] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "email": to_email,
    }

    return True


def verify_user_code(user_id_or_email, code):
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


def resend_verification_code(user_id_or_email):
    data = _verification_store.get(user_id_or_email)

    if not data:
        return False

    return send_verification_email(data["email"], user_id_or_email)