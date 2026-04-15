"""
webhook.py — Gumroad sale webhook → generate key → Google Sheets + email
Deploy on Railway: https://railway.app
"""
import json
import os
import random
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request, status
from google.oauth2.service_account import Credentials

load_dotenv()

app = FastAPI(title="CV Analyzer — Gumroad Webhook")

# ── Config ────────────────────────────────────────────────────────────────────

GOOGLE_SHEET_ID         = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
SMTP_HOST               = os.environ["SMTP_HOST"]
SMTP_PORT               = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER               = os.environ["SMTP_USER"]
SMTP_PASSWORD           = os.environ["SMTP_PASSWORD"]
SMTP_FROM               = os.getenv("SMTP_FROM", SMTP_USER)
KEY_USES                = int(os.getenv("KEY_USES", "30"))
GUMROAD_SELLER_ID       = os.getenv("GUMROAD_SELLER_ID", "")  # optional extra check

# ── Google Sheets client ──────────────────────────────────────────────────────

def _get_worksheet() -> gspread.Worksheet:
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    return spreadsheet.worksheet("claves")


# ── Key generation ────────────────────────────────────────────────────────────

def _generate_key() -> str:
    """Return a key in the format CLAVE-XXXX-YYYY (uppercase alphanumeric)."""
    chars = string.ascii_uppercase + string.digits
    part1 = "".join(random.choices(chars, k=4))
    part2 = "".join(random.choices(chars, k=4))
    return f"CLAVE-{part1}-{part2}"


def _key_exists(ws: gspread.Worksheet, key: str) -> bool:
    return ws.find(key, in_column=1) is not None


def _create_unique_key(ws: gspread.Worksheet) -> str:
    for _ in range(10):
        key = _generate_key()
        if not _key_exists(ws, key):
            return key
    raise RuntimeError("Could not generate a unique key after 10 attempts.")


# ── Google Sheets writer ──────────────────────────────────────────────────────

def _add_key_to_sheet(ws: gspread.Worksheet, key: str, email: str) -> None:
    """Append a new row: [clave, usos_restantes, email_comprador]."""
    ws.append_row([key, KEY_USES, email], value_input_option="USER_ENTERED")


# ── Email sender ──────────────────────────────────────────────────────────────

_EMAIL_SUBJECT = "Tu clave de acceso — Analizador de CVs con IA"

_EMAIL_BODY_ES = """\
¡Gracias por tu compra!

Tu clave de acceso es:

    {key}

Úsala en la aplicación para empezar a analizar CVs.
La clave tiene {uses} usos incluidos.

Si tienes problemas, responde este correo.

Saludos,
El equipo de CV Analyzer
"""

_EMAIL_BODY_HTML = """\
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:24px">
  <h2 style="color:#1a1a2e">¡Gracias por tu compra!</h2>
  <p>Tu clave de acceso es:</p>
  <div style="background:#f0f4ff;border:2px solid #4f46e5;border-radius:8px;
              padding:16px;text-align:center;margin:20px 0">
    <span style="font-size:1.5rem;font-weight:bold;letter-spacing:2px;
                 color:#4f46e5;font-family:monospace">{key}</span>
  </div>
  <p>Ingrésala en la aplicación para empezar a analizar CVs.<br>
     La clave tiene <strong>{uses} usos</strong> incluidos.</p>
  <p style="color:#666;font-size:0.85rem">
    Si tienes problemas, responde este correo.
  </p>
</body>
</html>
"""


def _send_email(to_email: str, key: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = _EMAIL_SUBJECT
    msg["From"]    = SMTP_FROM
    msg["To"]      = to_email

    msg.attach(MIMEText(_EMAIL_BODY_ES.format(key=key, uses=KEY_USES), "plain", "utf-8"))
    msg.attach(MIMEText(_EMAIL_BODY_HTML.format(key=key, uses=KEY_USES), "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.sendmail(SMTP_FROM, to_email, msg.as_string())


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def health():
    return {"status": "ok", "service": "cv-analyzer-webhook"}


@app.post("/webhook/gumroad", status_code=status.HTTP_200_OK)
async def gumroad_webhook(request: Request):
    """
    Gumroad sends a POST with form-encoded data on every sale.
    Required fields: email, sale_id, test (bool string).
    """
    # Gumroad posts form data, not JSON
    try:
        form = await request.form()
    except Exception:
        raise HTTPException(status_code=400, detail="Bad request body")

    email   = form.get("email", "").strip()
    sale_id = form.get("sale_id", "").strip()
    is_test = str(form.get("test", "false")).lower() == "true"

    if not email:
        raise HTTPException(status_code=400, detail="Missing email field")

    # Optional: verify seller ID
    if GUMROAD_SELLER_ID:
        seller_id = form.get("seller_id", "").strip()
        if seller_id != GUMROAD_SELLER_ID:
            raise HTTPException(status_code=403, detail="Unknown seller")

    try:
        ws  = _get_worksheet()
        key = _create_unique_key(ws)
        _add_key_to_sheet(ws, key, email)
    except Exception as exc:
        # Log to stdout (visible in Railway logs)
        print(f"[ERROR] Sheets error for {email} (sale {sale_id}): {exc}")
        raise HTTPException(status_code=500, detail="Could not create key") from exc

    try:
        _send_email(email, key)
    except Exception as exc:
        # Key was created but email failed — log so you can resend manually
        print(f"[WARN] Key {key} created but email to {email} failed: {exc}")
        # Still return 200 so Gumroad doesn't keep retrying (which would create duplicate keys)

    log_prefix = "[TEST]" if is_test else "[SALE]"
    print(f"{log_prefix} sale_id={sale_id} email={email} key={key}")
    return {"ok": True, "key": key if is_test else "***"}
