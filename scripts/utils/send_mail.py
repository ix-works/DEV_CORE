#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""send_mail.py — Gmail (App Password + SMTP) ile ekli mail gönderir. JENERİK core aracı.

Kullanıcının açık talimatıyla, oturum içinde çağrılmak üzere (ör. kullanıcı dökümanlarını
bir alıcı listesine ek olarak yollamak). Proje kimliği GÖMÜLÜ DEĞİL — gönderen/liste/sır
env veya proje-config'ten gelir.

GÜVENLİK (KRİTİK):
  - App Password ASLA kaynağa/repoya yazılmaz. Sır sırası: env `GMAIL_APP_PASSWORD`
    → gitignore'lu dosya `<proje>/conn/.gmail_app_password`.
  - Alıcı listesi gitignore'lu `<proje>/conn/mail_list.txt` (repo'ya girmez).
  - VARSAYILAN = DRY-RUN: önizleme basar, GÖNDERMEZ. Gerçek gönderim için açıkça `--send`.
    Çağıran (Claude) önce dry-run önizlemesini kullanıcıya gösterir, açık onayla `--send`.
  - Alıcılar BCC eklenir (liste üyeleri birbirini görmez).

Proje kökü: env `CLAUDE_PROJECT_DIR` (yoksa cwd). Gönderen/ekler proje.yaml'dan da okunabilir
(`mail_sender`, `mail_attachments`) ama CLI argümanları önceliklidir.

Örnek:
  # önizleme (göndermez):
  python core/scripts/utils/send_mail.py --from <gonderen>@example.com \
      --subject "Kullanıcı Kılavuzu" --body-file docs/mail.txt --attach docs/KILAVUZ.pdf
  # gerçek gönderim:
  ... --send
"""
from __future__ import annotations

import argparse
import mimetypes
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

# Windows konsol UTF-8 koruması (C-ENC-01) — non-ASCII basınca UnicodeEncodeError ile
# ÇÖKMESİN (exit 1 gerçek FAIL'den ayırt edilemez).
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def proje_koku() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _cfg(key: str):
    """project.yaml'dan opsiyonel okuma — utils.project_config varsa kullan, yoksa None."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from project_config import cfg as _pc  # type: ignore
        return _pc(key)
    except Exception:
        return None


def die(msg: str, code: int = 2) -> None:
    print(f"[HATA] {msg}", file=sys.stderr)
    sys.exit(code)


def read_recipients(path: Path) -> list[str]:
    if not path.is_file():
        die(f"alıcı listesi yok: {path}\n"
            f"       Oluştur: her satıra bir e-posta (conn/mail_list.example.txt'e bak).")
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if "@" not in s or " " in s:
            die(f"geçersiz alıcı satırı ({path.name}): {s!r}")
        out.append(s)
    if not out:
        die(f"alıcı listesi boş: {path}")
    seen, uniq = set(), []
    for e in out:
        k = e.lower()
        if k not in seen:
            seen.add(k); uniq.append(e)
    return uniq


def read_app_password(proj: Path) -> str:
    env = os.environ.get("GMAIL_APP_PASSWORD")
    if env and env.strip():
        return env.strip().replace(" ", "")  # Google 4'lü grupları boşlukla gösterir
    secret = proj / "conn" / ".gmail_app_password"
    if secret.is_file():
        val = secret.read_text(encoding="utf-8").strip().replace(" ", "")
        if val:
            return val
    die("App Password bulunamadı. Ya `GMAIL_APP_PASSWORD` env değişkeni ayarla, "
        f"ya da tek satır olarak {secret} dosyasına yaz (ikisi de gitignore'lu).")
    return ""  # unreachable


def resolve_sender(cli_from: str | None) -> str:
    sender = cli_from or os.environ.get("GMAIL_SENDER") or _cfg("mail_sender")
    if not sender or "@" not in str(sender):
        die("gönderen adresi yok. `--from ADRES` ver, ya `GMAIL_SENDER` env, "
            "ya da project.yaml `mail_sender:` ayarla.")
    return str(sender)


def build_message(sender, recipients, subject, body, is_html, attachments) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr(("", sender))
    msg["To"] = formataddr(("", sender))          # To = gönderenin kendisi
    msg["Bcc"] = ", ".join(recipients)            # gerçek alıcılar gizli
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    if is_html:
        msg.set_content("Bu ileti HTML biçimindedir; HTML destekleyen bir istemcide görüntüleyin.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)
    for ap in attachments:
        if not ap.is_file():
            die(f"ek dosya yok: {ap}")
        ctype, encoding = mimetypes.guess_type(str(ap))
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        msg.add_attachment(ap.read_bytes(), maintype=maintype, subtype=subtype, filename=ap.name)
    return msg


def preview(sender, recipients, subject, body, is_html, attachments, will_send):
    line = "=" * 60
    print(line)
    print("GÖNDERİM" if will_send else "DRY-RUN (önizleme — GÖNDERİLMEYECEK)")
    print(line)
    print(f"Gönderen : {sender}")
    print(f"Alıcı     : {len(recipients)} kişi (BCC — birbirini görmez)")
    for i, r in enumerate(recipients, 1):
        print(f"   {i:>3}. {r}")
    print(f"Konu      : {subject}")
    print(f"Gövde     : {'HTML' if is_html else 'düz metin'}, {len(body)} karakter")
    if attachments:
        print(f"Ekler     : {len(attachments)}")
        for a in attachments:
            print(f"   - {a.name}  ({a.stat().st_size} bayt)")
    else:
        print("Ekler     : yok")
    print(line)


def main() -> int:
    proj = proje_koku()
    default_list = proj / "conn" / "mail_list.txt"

    ap = argparse.ArgumentParser(description="Gmail App Password ile ekli mail gönder (varsayılan dry-run).")
    ap.add_argument("--subject", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--body", help="gövde metni (doğrudan)")
    g.add_argument("--body-file", help="gövde dosyası (UTF-8)")
    ap.add_argument("--attach", nargs="*", default=None,
                    help="ek dosya yolları (verilmezse project.yaml mail_attachments)")
    ap.add_argument("--to-list", default=str(default_list), help=f"alıcı listesi (varsayılan {default_list})")
    ap.add_argument("--from", dest="sender", default=None, help="gönderen (yoksa GMAIL_SENDER env / project.yaml)")
    ap.add_argument("--html", action="store_true", help="gövde HTML")
    ap.add_argument("--send", action="store_true", help="GERÇEKTEN gönder (yoksa yalnız önizleme)")
    args = ap.parse_args()

    sender = resolve_sender(args.sender)
    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else args.body
    attach_src = args.attach if args.attach is not None else [str(x) for x in (_cfg("mail_attachments") or [])]
    attachments = [Path(a) for a in attach_src]
    recipients = read_recipients(Path(args.to_list))

    preview(sender, recipients, args.subject, body, args.html, attachments, args.send)

    if not args.send:
        print("[DRY-RUN] Gönderilmedi. Onaylıysa aynı komuta `--send` ekleyin.")
        return 0

    app_pw = read_app_password(proj)
    ctx = ssl.create_default_context()
    msg = build_message(sender, recipients, args.subject, body, args.html, attachments)
    all_rcpts = recipients + [sender]
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=60) as s:
            s.login(sender, app_pw)
            s.send_message(msg, from_addr=sender, to_addrs=all_rcpts)
    except smtplib.SMTPAuthenticationError:
        die("SMTP kimlik doğrulama başarısız. App Password yanlış ya da 2FA/App-Password kapalı.")
    except Exception as e:  # noqa: BLE001
        die(f"gönderim hatası: {type(e).__name__}: {e}")
    print(f"[ OK ] gönderildi → {len(recipients)} alıcı (BCC). Message-ID: {msg['Message-ID']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
