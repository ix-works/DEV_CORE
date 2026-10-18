---
name: gmail-smtp-gecersiz-kimlikte-535-degil-baglanti-keser
description: "Gmail SMTP (587) geçersiz/iptal App Password'de 535 DEMEZ, bağlantıyı keser — \"ağ engeli\" sanma; önce apppasswords sayfasına baktır"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 919c6579-5a4e-408b-8a41-aab3a251c60e
  modified: 2026-10-12T08:41:28.077Z
---

Gmail SMTP `smtp.gmail.com:587` girişinde kimlik bilgisi geçersizse (iptal olmuş App Password, yanlış şifre, hatta OLMAYAN hesap) bu makineden 535 "Username and Password not accepted" yerine **`SMTPServerDisconnected` (bağlantı 0,1-0,2 sn'de kesilir)** geldi. Üç kimlikte aynı belirti ⇒ "hesaptan bağımsız ⇒ şirket ağı/IP engeli" diye yanlış teşhis koydum. Gerçek sebep: eski App Password iptal olmuştu (`myaccount.google.com/apppasswords` listesinde YOKTU); yeni şifreyle aynı ağdan `235 2.7.0 Accepted` (2026-10-12).

**Why:** Kontrol grubum (yanlış şifre / olmayan hesap) da GEÇERSİZ kimlikti — geçerli bir kimlik yoktu, yani grup "ağ mı hesap mı" sorusunu ayıramıyordu. Belirtiyi açıklayan ikinci hipotez (Gmail geçersiz kimlikte keser) hiç test edilmedi. 2026-10-10'daki ilk vakada da kök neden "ölçülemedi" diye bırakılmıştı.

**How to apply:** `send_mail.py` / Gmail SMTP'de bağlantı AUTH anında kesiliyorsa: ① TCP 587 + STARTTLS + sertifika verenini ölç (ağ katmanı) ② sonra kullanıcıya `myaccount.google.com/apppasswords`'te şifrenin listede olup olmadığını sordur — yoksa yeni oluşturup `conn/.gmail_app_password`'e yazdır ③ tek giriş denemesi. Arka arkaya çok giriş denemesi yapma: Gmail banner'ı da geciktirmeye başladı (zaman aşımı). Ağ engeli iddiası için kontrol grubu GEÇERLİ bir kimlik ya da başka ağ (hotspot) olmalı.

Son-doğrulama: 2026-10-12 · Applies-to: Gmail SMTP App Password (core `scripts/utils/send_mail.py`), Windows kurumsal ağ
