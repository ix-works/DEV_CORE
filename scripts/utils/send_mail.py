import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ============================================================
# AYARLAR — Buraya kendi bilgilerini gir
# ============================================================
SENDER_EMAIL    = "<gonderen>@example.com"       # Gonderen Gmail adresi
SENDER_PASSWORD = "xxxx xxxx xxxx xxxx"          # Gmail App Password (bosluklu 16 karakter)

RECIPIENTS = [
    "<alici1>@example.com",
    "<alici2>@example.com",
]

SUBJECT = "SAP Gelistirme Dokumanlari"

BODY = """\
Merhaba,

Ekte ilgili SAP gelistirme dokumanlari yer almaktadir.

Iyi calismalar.
"""

# B10: ekler PROJE-CONFIG'ten (project.yaml mail_attachments: [yol, ...]) — core sabit-yol tasimaz
from utils.project_config import cfg as _cfg
ATTACHMENTS = [str(x) for x in (_cfg('mail_attachments') or [])]
# ============================================================

def send_mail():
    msg = MIMEMultipart()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = ", ".join(RECIPIENTS)
    msg["Subject"] = SUBJECT
    msg.attach(MIMEText(BODY, "plain", "utf-8"))

    missing = [f for f in ATTACHMENTS if not os.path.exists(f)]
    if missing:
        print("[HATA] Asagidaki dosyalar bulunamadi:")
        for f in missing:
            print("  -", f)
        return

    for filepath in ATTACHMENTS:
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)
        print(f"[OK] Eklendi: {filename}")

    print("\nBaglanti kuruluyor: smtp.gmail.com:587 ...")
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())
        print(f"[OK] Mail basariyla gonderildi -> {', '.join(RECIPIENTS)}")
    except smtplib.SMTPAuthenticationError:
        print("[HATA] Kimlik dogrulama basarisiz.")
        print("       Gmail App Password kullanildiginden emin olun.")
        print("       Ayarlar: https://myaccount.google.com/apppasswords")
    except Exception as e:
        print(f"[HATA] {e}")

if __name__ == "__main__":
    send_mail()
