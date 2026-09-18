---
name: feedback_mesaj-envanteri-tasarim-asamasinda-kurgulanir
description: "Bir geliştirmenin üreteceği HER mesaj TS'te envanterlenir (no/tip/birebir metin ≤73/numaralı yer tutucu/üretim noktası/kullanıcı aksiyonu); build ortasında doğan mesaj bloke eden onay turu açar"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 199aed41-f1ec-4c03-ae34-a0b1b09c15be
---

Bir SAP geliştirmesinin üreteceği **HER** mesaj, TS'te bir **ENVANTER** olarak yazılır —
örnek tablo değil. Sütunlar: `Mesaj Sınıfı · No · Tip · Metin (birebir, ≤73 karakter) ·
&1..&4 anlamı · Üretim noktası (sınıf/metot) · Kullanıcı aksiyonu`.
Build sırasında yeni mesaj ihtiyacı doğarsa **TS revize edilir** — "sonra ekleriz" YOK.

**Why:** Mesaj metnini **yalnız kullanıcı verebilir** ([[feedback_zli-obje-text-tahmin-yasak]],
ADR 0005-D). Dolayısıyla TS'te eksik bırakılan her mesaj, build'in tam ortasında **bloke eden
bir onay turu** açar ve iş durur. Bu **iki kez ölçüldü**: <PAKET-A>'da `210/211/212`
(2026-08-24) ve `213`+`214` (2026-08-29) — aynı sınıf, beş gün arayla.
⚠ Sorun ARAÇ DEĞİLDİ: `create_message_class.py` + `populate_message_class.py --messages-csv`
sınıfın tamamını programatik yazıyor, SE91 gerekmiyor. Boşluk **kural-şekilliydi**.

**Nerede bağlı (2026-08-29 turunda kuruldu, F4'ün birebir aynası):**
- `core/standards/04-documentation-fs-ts.md` §10.1 → **★ MESAJ ENVANTERİ TAMLIĞI (MUST —
  eksikse TS eksiktir)** bloğu + 7 kolonlu tablo şeması. F4'ün `:745-753`'teki MUST bloğunun
  aynısı; o blok da *"Kolonu/etiketi eksik bırakılmış TS = eksik TS"* diye biter.
- `core/playbook/checklists/doc-checklist.md` → **`DOC-TS-05`** (HIGH/EKSİK). `bug-expert`
  her TS incelemesinde §C'yi zaten okuyor ⇒ ek kablolama gerekmedi.
- ⛔ **Otomatik gate YOK — bilinçli.** F4 de bu şart için gate taşımıyor; standart + checklist +
  reviewer ile taşınıyor ([[feedback_gate-moratoryumu-bes-sart]]).

**How to apply:**
- TS yazarken mesaj envanterini **doldur**; metni kullanıcıdan **iste** (numarasıyla, tipiyle,
  yer tutucularıyla birlikte) — hepsini MUTABAKAT'ta **tek turda** onaylat.
- **≤73 karakter** ölçülmüş bir sınırdır: T100-`TEXT` = `CHAR 73`
  (`populate_message_class.py:79 T100_TEXT_MAXLEN`, fail-closed). Aşan metin TS'e yazılamaz,
  kullanıcıdan kısaltılmışı istenir.
- Yer tutucular **numaralı** (`&1..&4`), çıplak `&` DEĞİL — sıra TS'ten okunamazsa
  `MESSAGE … WITH` sırası tahmine kalır.
- **Üretim noktası kolonu boş bırakılamaz:** `doc-checklist` `DOC-CR-01 ①` ters-yön kontrolü
  (*katalogdaki her mesaj bir üretim noktasına bağlı mı*) tam o kolonu okur.
- ⚠ **Uzun metin (long-text) İSTEĞE BAĞLI** ve yazılırsa *"SE91 gerektirir"* şerhi konur:
  programatik yol **YOKTUR** — `populate_message_class.py` `mc:documented="false"` değerini
  **sabit** yazar, CSV şemasında long-text sütunu yok (ölçüldü 2026-08-29).
  ⇒ Zorunlu kılınan her TS alanının arkasında ya bir kapı ya bir icra yolu olmalı; icra yolu
  elle SE91 olan bir alanı MUST yapmak kapatılamayacak bir madde üretir.
- Aynı aile: [[feedback_f4-arama-yardimi-tasarim-asamasinda-kurgulanir]] (aynı ilkenin F4
  hâli — mimari build'de değil TS'te kurgulanır) · [[feedback_spec-mutabakat-gate]] ·
  [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]].
