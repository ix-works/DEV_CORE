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

---

⛔ **NİTELEYİCİ (2026-09-08, ölçüldü):** `ALL FIELDS WITH`, **hedef entity'nin kaynak view'ı
anahtarını tutmuyorsa DUMP ettirir.** Canlı vaka (bir projede, booking BO'su): CCIMP'te
`ENTITY Booking BY \_Container ALL FIELDS WITH ...` → **HANA SQL code 305** ("single-row query
returns more than one row") / `CX_SY_OPEN_SQL_DB` / `SQL dbsl rc: 99`, component
**BC-ESI-RAP-CSP**. Zincir: bir agregat view (`ZSD001_I_CONTAINER_GROSS` temsilî) `key BookingNo,
key BookingItem` ilan ediyor ama `GROUP BY BookingNo, BookingItem, gewei` yapıyor ⇒ karışık birimli
veri doğduğu gün `[0..1]` ilan edilmiş association'lar **kardinalite ihlaline** düşüyor, child satırı
çoğalıyor, tekil okuma patlıyor. ⚠ Keys-only okuma bu vakada **patlamazdı** — "her zaman ALL FIELDS
WITH" alışkanlığı burada kusurun **taşıyıcısı** oldu.

⚠ Bu bir **geri alma değil**: yukarıdaki ders (non-key alan `FROM` ile sessizce INITIAL kalır) aynen
geçerli. Kural metni zaten iki biçimi de verir (`core/standards/05-coding-rap.md` §5.1: `ALL FIELDS WITH`
**veya** `FIELDS ( f1 f2 ) WITH`; aynısı `bug-checklist-backend.md` BE-20) — zorunlu olan **`WITH`**'tir,
`ALL FIELDS` değil. Eksik olan yalnız **hangisinin tercih edileceğine dair YÖN**dü.

⭐ **Mekanizma (ölçüldü):** `ALL FIELDS` **türetilmiş** alanları da `SELECT`'e sokar (association path
expression, CASE, agregat). Vakadaki tetikleyici bir CASE alanıydı; CASE **tek değer** ister ⇒ `[0..1]`
association **skaler alt-sorguya** çevrilir ⇒ kardinalite ihlalinde HANA **-305**. Dar alan listesiyle
aynı okuma **patlamadı** (ölçüldü: 4 alan → 38/38 tekil, zehirli kayıtta bile temiz).

**How to apply (niteleyiciyle):** varsayılan **`ALL FIELDS WITH` olmasın** — gerçekten okuduğun
alanları `FIELDS ( … ) WITH` ile say. `ALL FIELDS WITH` yalnız alan kümesi gerçekten değişkense.
Ayrıca hedef entity'nin projeksiyonundaki her `[0..1]` association için **hedef view'ın `key` kümesi ⊇
`GROUP BY` kümesi** mi diye bak ([[feedback_cds-tekillik-olcumunde-alan-listesi-bulguyu-degistirir]]);
tutmuyorsa önce view'ı onar. ⚠ Dar `FIELDS` bir **savunma katmanıdır, kök neden düzeltmesi DEĞİL** —
kırık view'ı başka bir tüketici (ör. OData'ya açılmış aynı alan) yine patlatabilir.
Son-doğrulama: 2026-11-12 (tohum geri akışı) · Applies-to: RAP BO (managed/unmanaged) EML okumaları
