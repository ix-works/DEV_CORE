---
name: feedback_tablo-yaratma-onay-gate
description: "DDIC tablo/yapı yaratmadan ÖNCE alan+data element tasarımını göster, açık onay al; onaysız yaratım yasak — toplu dalga onayı ve TS'teki 'DTEL'siz' kararı tasarım onayı DEĞİLDİR"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9032e66e-45f9-47c0-af9b-23b771ffe0a7
---

Yeni DDIC tablo yaratmadan **ÖNCE** tasarımı kullanıcıya göster ve **açık onay** al; onaysız `create_table` YASAK (kullanıcı kuralı, 2026-06-08).

Gösterilecek: tüm alanlar + her alanın **data element'i** + key/uzunluk + delivery class/category.

**Why:** ZSD000_T_UIVAR'ı onaysız yarattım; client/abap.clnt + raw char60 alanlarıyla çıktı, kullanıcı düzeltti (MANDT DTEL, std data element'ler). Önceden tasarım onayı bu round-trip'i önler + DDIC standartlarına (std DTEL kullanımı) uyumu garantiler.

**How to apply:** create_table çağırmadan önce alan tablosu sun → onay bekle. Kurallar: (1) client alanı = `mandt : mandt` (DTEL **MANDT**), "client : abap.clnt" DEĞİL; (2) mümkün olan her alanda **mevcut standart data element** kullan (ör. variant adı → DTEL `VARIANT` CHAR14; kullanıcı → `xubname`; UUID → `sysuuid_x16`; timestamp → `timestampl`), raw `abap.char(n)`'den kaçın; (3) audit alanı varsa std §F determinasyon. DDIC tablo adı **max 16 karakter** (uzun olursa "daha kısa ad seç" 422). Kayıt: claude/rules/sap-source-protokolu.md §10 (D1 taşındı) "Kullanıcıdan TEYIT" tablosu. İlgili: [[feedback_done-tam-kapsam-dogrula]]

**İkinci vaka (2026-11-08, namespace'li ürün paketi, 29 tablo):** kural 3 yerde yazılıydı (`claude/rules/sap-source-protokolu.md` §10, BE-13 BLOCKER ve bu ders) ve yine kaçtı. Mekanizma:
① TS'te alanlar bilinçli olarak "DTEL'siz / doğrudan tip" yazılmıştı. Bu bir lider kararıydı; "kullanıcı onayı bekler" diye işaretlenmişti ama kullanıcıya ayrıca sorulmadı.
② **Toplu dalga onayı ("29 tablo yaz") bir kapsam onayıdır; BE-13'ün istediği alan + DTEL tasarım onayı DEĞİLDİR.**
③ Bug-gate'ler yerel kaynağa bakıp "tablo yaratımı yok → UYGULANMAZ" dedi ve yaratımı yapan gateway'in brifinde BE-13 yoktu.
Sonuçta 33 DTEL'siz alan canlıya gitti ve tüm kapılar PASS verdi. Kullanıcı durumu SE11 ekranından yakaladı. **Kural yapılar (structure) için de aynen geçerlidir** (kullanıcı). Çekirdek Issue: DEV_CORE#406.
**How to apply (ek):** tablo ya da yapı yazımı içeren her dalga onayından ÖNCE alan × DTEL tablosunu göster ve DTEL'siz alanları AYRICA işaretle. TS'teki "DTEL'siz" kararını kullanıcı onayı sayma. Gateway brifine şu satırı koy: "BE-13 onay kanıtı (karar kaydı) yoksa tablo/yapı yaratma". Kanonik kural: `claude/agents/adt-gateway.md` BE-13.
Son-doğrulama: 2026-11-08 · Applies-to: tüm profiller, DDIC tablo + yapı yaratımı
