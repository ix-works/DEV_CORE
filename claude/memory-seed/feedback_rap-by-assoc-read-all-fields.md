---
name: feedback_rap-by-assoc-read-all-fields
description: RAP READ ENTITIES BY \_assoc FROM <key> YALNIZ KEY döner; non-key alan için ALL FIELDS WITH ŞART
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5ecec217-78c0-499b-ad67-bf1afb7f70a6
---

RAP'te `READ ENTITIES OF bo IN LOCAL MODE ENTITY parent BY \_child FROM <kaynak-key> RESULT lt` ifadesi target (child) entity'nin **YALNIZCA KEY alanlarını** doldurur. Non-key alan (örn. tarih/durum/tutar/SeType) okumak istiyorsan **`ALL FIELDS WITH <kaynak-key>`** (tüm alanlar) veya **`FIELDS ( f1 f2 ) WITH <kaynak-key>`** (seçili; `FROM` DEĞİL `WITH`) KULLAN. `FROM` formunda non-key alan **INITIAL** kalır → validasyon/determination sessizce yanlış çalışır.

**Why:** 2026-06-17 voyage testinde bulundu (kullanıcı runtime). valDestinations `BY \_Destination FROM CORRESPONDING` → ArrivalDatePlan (non-key) INITIAL → her save'de "plan tarihi zorunlu" yanlış-fire (dolu veride bile). Smoking gun: existence (key) kontrolü geçiyor ama non-key alan kontrolü fire ediyor. Aynı bug 2 yerde daha: SEVKEMRI.ccimp (SeType/SoldTo non-key boş → get_strategy başarısız → **dispatch bakiye/kalem validasyonları SESSİZCE HİÇ KOŞMUYORDU**) + BOOKING.ccimp (ContainerNo=KEY okuduğu için şanslıca çalışıyordu; yorum "tüm alanlar gelir" YANLIŞ varsayımı yayıyordu). Hatalı düzeltme: syntax hatası verince ('WITH expected after )') FIELDS'i KALDIRMAK → keys-only'a düşürür; doğru fix FROM→WITH (FIELDS koru) veya ALL FIELDS WITH.

**How to apply:** ccimp validation/determination'da `BY \_assoc` read yazarken non-key alan okuyacaksan **ALL FIELDS WITH** kullan. Mevcut `BY \_assoc FROM ...` read'lerini tarayıp non-key alan tüketen var mı kontrol et (grep `BY \\_` + RESULT kullanım). Bug RUNTIME'da çıkar (syntax 0-error verir, aktive olur) → e2e/runtime test şart ([[feedback_ui5-v2-plumbing-reuse-traps]]). İlgili: [[feedback_abaplint-parser-error-gercek-olabilir]] (orijinal FIELDS-FROM hatası gerçekti).
