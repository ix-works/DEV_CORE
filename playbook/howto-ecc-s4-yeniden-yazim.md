---
applies_to: [s4_private]
layer: L3
scope: project-wide
type: playbook
applies-to: both
last-updated: 2026-10-12
status: active
---

# HOWTO — ECC (legacy) geliştirmesini S/4'te YENİDEN YAZMAK

> **Ne zaman:** bir ECC/legacy programı, raporu ya da arayüzü S/4'te karşılanacak; legacy kaynak kodu,
> tablo dökümü ya da üretim verisi referans olarak elde.
> **Temel ilke (MUST):** legacy **iş anlayışı** kaynağıdır, **tasarım şablonu DEĞİLDİR.** Hedef kod
> S/4 standardına ve bu evin standartlarına göre **yeniden modellenir**; legacy yapı kopyalanmaz.

## 1. Kaynak ≠ hedef

Legacy kod sözdizimi bakımından modern görünebilir (yeni release, satır içi bildirim, CDS); asıl kısıt
**sözdizimi değil, kullanılabilir API ve deyim yüzeyidir**: hedefte hangi standart obje released, hangi
iş nesnesi hangi yolla yazılır (std 10), hangi klasik yapı bu projede kabul edilmiş bir yoldur (std 06,
ADR 0012). "Derleniyor" ≠ "hedefe uygun".

## 2. Legacy'den NE alınır, NE alınmaz

| Alınır (iş anlayışı) | Alınmaz (teknik seçim — yeniden değerlendirilir) |
|---|---|
| İş kuralları ve istisna/hata senaryoları | Z tablo/alan tasarımı, alan "geri kullanım" hileleri |
| Takip edilen büyüklükler (hangi alan, hangi kırılım) | IDoc temel tipi / partner tipi / mesaj yapısı seçimi |
| Hacim, sıklık, kullanıcı alışkanlıkları | Program/FM çağrı zinciri, ekran yapısı |
| Örnek veri (anlamak için — PII kuralları geçerli) | Mail/log mekanizması, eski çözümün geçici kısıtları |

**Her tasarım kararında üç soru, bu sırayla:** ① S/4 standardı bunu karşılıyor mu / ne öneriyor?
② Bu ihtiyaç bugün genel kabul görmüş biçimde nasıl çözülür? ③ Legacy'den farklıysa **neden** farklı —
*"legacy'de böyleydi"* tek başına gerekçe **DEĞİLDİR** (kullanıcı açıkça isterse başka).

**Sinyal:** FS/TS'te *"ECC ile aynı"* / *"eskisi gibi"* ifadesi → bu bir **iş kuralı** mı (kalır) yoksa
**teknik seçim** mi (yeniden değerlendirilir)? Belge kapısında sorulur: `checklists/doc-checklist.md` **DOC-TS-06**.

## 3. Yeniden yazım ön-kontrolü (TS'e girmeden)

| ID | Kontrol | Not |
|---|---|---|
| **C-PORT-01** | Hedef **dil sürümü / tier** yazılı mı (klasik ABAP mı, ABAP Cloud mu) ve `cleancore_policy` ile uyumlu mu? | [`../standards/12-clean-core-seviye-referansi.md`](../standards/12-clean-core-seviye-referansi.md) |
| **C-PORT-02** | Kullanılacak **her standart API/obje**nin released durumu **canlı ya da ATC ile** ölçüldü mü (doküman/hafıza tek başına yetmez)? | ATC "Usage of APIs" otoritedir — `standards/10` ADIM 1a; ölçülmediyse TS'te `ölçülmedi` yazılır |
| **C-PORT-03** | Legacy'deki Z view/sınıf **kopyalanmadan** yeniden modellendi mi (S/4 veri modeli: ör. replacement tablolar)? | Replacement tabloda sessiz 0 satır: `lessons-learned.md` PATTERN #21 |
| **C-PORT-04** | Released karşılığı **bulunamayan** her ihtiyaç kod yazılmadan **açık boşluk** olarak FS/TS'e yazıldı mı (sessizce iç objeye düşülmedi)? | Karar kullanıcıyla verilir; standart objeye dokunma ADR 0005-A |
| **C-PORT-05** | Paket ve transport **kullanıcıdan** alındı mı? | ADR 0005-C — AI yaratmaz/seçmez |

⚠ ABAP Cloud tier'ına özgü kontroller (yasak deyim taraması, Cloud readiness ATC varyantı) yalnız hedef
ABAP Cloud ise koşulur — klasik track bu evde kabul edilmiş yoldur (std 06, ADR 0012).

## 4. İlgili

- [`intake-triage.md`](intake-triage.md) §5 — çözüm merdiveni (standart karşılıyor mu → platform bildirimi → en küçük kod)
- [`checklists/doc-checklist.md`](checklists/doc-checklist.md) DOC-TS-06 · [`../standards/10-standart-veriye-yazma-api-secimi.md`](../standards/10-standart-veriye-yazma-api-secimi.md)
- prior-art: bulundu — ilke bugüne kadar yalnız `claude/memory-seed/feedback_ecc-referansi-is-anlayisi-icin-mimari-degil.md` dersinde yaşıyordu (bu sayfa terfisidir); ön-kontrol satırları dış bir çekirdekteki port listesinden uyarlanmıştır (kendi cümlelerimizle, bize uyan 5 madde).
