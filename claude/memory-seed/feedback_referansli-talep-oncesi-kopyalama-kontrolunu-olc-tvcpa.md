---
name: feedback_referansli-talep-oncesi-kopyalama-kontrolunu-olc-tvcpa
description: "Faturaya referanslı Z talep (K/L) yaratma tasarlanmadan önce TVCPA'da fatura türü → hedef sipariş türü kopyalama kontrolü ÖLÇÜLÜR — Z dekont talebi türlerinde hiç kayıt olmayabilir (kontrol grubu standart L2/G2); yoksa API/EML referanslı yaratma reddeder"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: 8865df6b-2e94-44e8-8952-84b42fc53742
  modified: 2026-10-16T15:50:07.357Z
---

Faturaya referanslı dekont talebi (VBTYP K/L) yaratan bir geliştirme tasarlanırken (EML `CreateWithReference`, BAPI ya da VA01 referansla) önce **kopyalama kontrolü** ölçülür: `TVCPA` WHERE `AUARN IN (<hedef türler>)` — kaynak `FKARV`/fatura türü → hedef sipariş türü kaydı var mı. Belge türünün TVAK'ta var olması, faturalama türü / blok / şema tanımlı olması kopyalama kontrolünün varlığını **kanıtlamaz**.

**Why:** 2026-10-16 bir Z dekont-talebi türü çiftinde (borç L / alacak K; TVAK, şema, Z'li fiyat koşulu, sipariş nedeni hepsi tanımlı) TVCPA hedef kaydı **0** çıktı; kontrol grubu standart L2/G2/CR1/DR1 ~1.200'er kayıtla dolu. Ölçülmeseydi API denemesi "kopyalama kontrolü yok" reddiyle başarısız olur, sebep tasarımda aranırdı. Ayrıca DEV'de elle yaratılan örnek belge **referanssız** yaratılmıştı — çalışan bir örnek belge referanslı yolun çalıştığını göstermez.

**How to apply:** Ölçümü kontrol grubuyla yap (standart L2/G2 kaydı sayısı yanında). Kayıt yoksa bunu FS'e **ön koşul** (SD customizing, VTAF) ve açık soru olarak yaz; DEV API denemesini o tanımdan sonraya koy. Alan anlamları için [[feedback_alan-anlamini-ddic-etiketinden-dogrula-tvak-fkara-fkarv]]. prior-art: yok (TVCPA ölçüm kuralı memory/core'da yazılı değildi).

**Vaka 2 (2026-10-17):** aynı pakette "önceki farkı referanslı talepten bul" kuralı FS'e yazılmıştı; sonradan ölçülünce mevcut fark taleplerinin **tamamı referanssız** çıktı (VGBEL boş, FBUDA boş) ⇒ kural gerçek belgeyi hiç yakalamıyordu. Ders genişler: mevcut belgeleri bir bağ alanıyla (VGBEL/AUBEL/hizmet tarihi) eşleştiren kural yazmadan önce o alanın **gerçek belgelerdeki doluluğu** ölçülür; boşsa eşleştirme anahtarını (org+müşteri+malzeme+dönem) yeniden kur.

Son-doğrulama: 2026-10-17 · Applies-to: SD (s4_private / ecc), faturaya referanslı belge yaratan geliştirme
