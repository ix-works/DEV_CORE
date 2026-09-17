---
name: feedback_debugger-farki-aslinda-kullanici-farki
description: "Debugger'la çalışıyor, debugger'sız çalışmıyor" belirtisi çoğu zaman KULLANICI/YETKİ farkıdır — kontrol grubunu aynı kullanıcıyla kur
metadata:
  type: feedback
---

**"Debugger'la çalışıyor, debugger'sız çalışmıyor" bir teşhis DEĞİL, kirli bir kontrol grubudur.**
Deneyi kim koşturdu — onu ölç. Geliştirici debugger'la, son kullanıcı debugger'sız denerse
**iki değişken üst üste biner** ve debugger suçlu sanılır.

**Why:** Vaka 2026-08-11 (EWM sanal paketleme). Belirti günlerce "Heisenbug" diye okundu;
**iki tur** bu varsayımla düzeltme yapıldı (BO yedeği, tetik daraltma) — ikisi de tutmadı.
Gerçek sebep **yetkiydi**: `I_PackingInstructionComponent` view'ının DCL'i (`LO_HU_PI`/`ACTVT 03`)
yetkisiz kullanıcının sorgusuna `'CDS_Access_Control' = 'DENY'` enjekte ediyor ⇒ sorgu **yapısı
gereği 0 satır** dönüyor, **hata vermiyor**. Debugger'lı koşuları yetkili kullanıcı yapmıştı.

**How to apply:**
- Belirti "bende çalışıyor, onda çalışmıyor" ise **İLK ÖLÇÜLECEK ŞEY KULLANICI** (belge/log/
  `MKPF-USNAM` gibi kalıcı bir iz üzerinden), debugger değil.
- Kontrol grubu **aynı kullanıcıyla** kurulur: aynı kişi hem debugger'lı hem debugger'sız koşsun.
  Bu yapılmadan "debugger sebep" sonucu ÇIKARILAMAZ.
- **Heisenbug'da breakpoint işe yaramaz** (semptomu yok eder) → girişimsiz gözlem: ST05 SQL trace.
  Cevap çoğu zaman SQL'in **kendi metninde** yazar.
- ⚠ DCL reddi hata değil, **sessiz boş sonuç** üretir → [[feedback_dogrulama-sezgileri-dort-kural]]

Son-doğrulama: 2026-08-11 · Applies-to: s4_private (CDS DCL'li her sistem); "bende çalışıyor" sınıfı genel
