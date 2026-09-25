---
applies_to: [all]
layer: L2
scope: project-wide
applies-to: backend
version: 1.0
last-updated: 2026-09-25
status: active
source: ADR 0005 B (anayasal sıra) + standards/05 §2 + playbook/modules/sd.md SD-K3 + bug-checklist-backend BE-14/24/26/37/53/74 + playbook/adt-rap.md §33-§35 — dağınık sahada-yaşanmış dersler tek sıraya dizildi (sahip kararı 2026-09-25)
---

# Standart Veriye Yazma — API Seçimi Karar Ağacı

> **Kapsam:** SAP **standart iş nesnesine** create / update / delete / action (satış belgesi,
> teslimat, fatura, BP, malzeme…). Z tabloya yazma kapsam DIŞI (managed RAP, std/05 §2).
> **OKUMA kapsam DIŞI** — okumada released CDS tercih edilir: std/05 §9X · checklist C-RAP-REL-01.
>
> **Anayasal zemin:** ADR 0005 B — standart tabloya direkt `INSERT/UPDATE/DELETE/MODIFY`
> YASAK; izinli yollar **sıralı** aranır. Bu dosya o sıranın AYRINTISIDIR; kanonik kısa
> metin her projenin kök `CLAUDE.md`'sinde damgalıdır.
>
> **Neden ağaç:** yolları doğru sırada **bilmek** yetmiyor. Seçimi bozan dersler (operasyon
> kapalı · metin persist etmiyor · handler'da commit dump'ı · EEW alanı sessizce düşüyor)
> **aktivasyonda ya da yalnız çalışma zamanında** görünür. Ağaç, bunları seçim anına taşır.

---

## ADIM 0 — Kod hangi bağlamda koşuyor? *(seçimden ÖNCE; commit kuralını bu belirler)*

| Bağlam | Commit kimde | Kaynak |
|---|---|---|
| **RAP behavior handler / action** (kendi BO'n — managed, unmanaged, façade) | **Framework.** `COMMIT ENTITIES` · `COMMIT WORK` · `BAPI_TRANSACTION_COMMIT` · örtük commit (`WAIT UP TO`) YASAK → `BEHAVIOR_ILLEGAL_STATEMENT`. Commit'li BAPI/FM **ayrı LUW**'da (RFC) çağrılır | checklist BE-26 (gate `check_no_rap_commit`) · BE-76 · `playbook/modules/sd.md` SD-K5 |
| **Klasik rapor / dynpro / job** (RAP *consumer*) | **Sende.** `COMMIT ENTITIES` (EML) ya da `BAPI_TRANSACTION_COMMIT` (BAPI) **zorunlu**; sonrasında okumadan önce görünürlük kapısı | BE-73 |
| **SEGW DPC_EXT** | DPC içinde BAPI + commit/rollback | std/02 |
| **Side-by-side** (`btp_abap`) | Uzak released API (communication arrangement) | profil matrisi |

> Aynı yöntem (ör. EML) iki bağlamda **farklı** commit kuralı taşır. Prior-art'ı başka bir
> bağlamdan taşırken tek anlamlı mimari fark genellikle budur — ADIM 0'ı atlama.

---

## ADIM 1 — Released RAP BO var mı? → **EML** *(Clean Core Level A)*

Nesne + operasyon için released bir RAP BO (`I_*TP`) varsa **ilk aday** budur. "Var" demek
**dört CANLI teyit** ister — hafıza, doküman ya da SAP Help yetmez:

| # | Teyit | Nasıl | Tutmazsa |
|---|---|---|---|
| 1a | BDEF canlıda var, release durumu uygun | `adt_get` BDEF + ATC **"Usage of APIs"** (otorite; regex'le taklit edilmez) | ADIM 2 |
| 1b | **İstenen operasyon AÇIK** | *"operation UPDATE/CREATE is not activated for entity"* — yalnız aktivasyonda/çalışma zamanında görünür | BE-24 → ADIM 3 (OData) ya da ADIM 2 |
| 1c | Gereken alanlar **yazılabilir** | projeksiyon CDS kaynağında `@ObjectModel.editableFieldFor` / `readonly` / suppress | `playbook/adt-rap.md` §35 (key'in `…ForEdit` muadili) |
| 1d | Bilinen boşluklar kontrol edildi | metin (`CREATE BY \_Text`) buffer'da başarılı ama **persist etmez** → `SAVE_TEXT` · late numbering → numara handler'da **senkron dönmez** · mevcut belgeye `CREATE BY \_assoc` rolü boş bırakabilir | `playbook/adt-rap.md` §33-§35 |

- `reported`'daki **tüm** hata mesajları yüzeye çıkarılır (BE-53).
- Buffer başarısı (`fc=0`, `subrc=0`, HTTP 200) **persist kanıtı DEĞİLDİR** → read-back (std/05 "Persist ≠ buffer").

## ADIM 2 — Released klasik API: **BAPI / FM** *(Level B)*

EML yoksa ya da 1a-1d'den biri tutmadıysa. Sınıflandırmanın otoritesi yine ATC "Usage of APIs".

- Key-user (EEW) özel alanları → `CL_CFD_BAPI_MAPPING` (BE-37). Klasik ham imaj **sessizce yok sayılır**: belge yaratılır, alan boş kalır.
- `RETURN` (`BAPIRET2`) içindeki **tüm** E/A/X satırları yüzeye çıkar; kimlik taşıyan satır çözülür (BE-74).
- Boş göndermek ≠ hiç göndermemek: X-bayraklı yapılarda yalnız değişen alan işaretlenir.

## ADIM 3 — Released OData API (`API_*_SRV`) — **yalnız şu durumlarda**

- EML operasyonu kapalıysa (1b) ya da uzak tüketimde.
- Aynı sistemde iç çağrı **iç gateway proxy** ile yapılır (BE-14 · `playbook/adt-rap.md` §34); SM59/RFC-dest legacy'dir.
- Klasik GUI bağlamında EML ya da BAPI varken **seçilmez** — aynı BO'ya HTTP katmanı eklemek gereksiz karmaşadır.

## ADIM 4 — Released OLMAYAN ama resmi RFC FM / BAPI *(Level C)*

- Gerekçe TS'e yazılır (aşağıda). `cleancore_policy: strict` ve `s4_public`'te **kapalı**.
- ⛔ **İç FM API değildir.** BAPI'nin altındaki iç katman (ör. `SD_SALESDOCUMENT_CREATE`) iş mantığının bir kısmını atlar → seçilmez.

## ADIM 5 — BDC (transaction) · ADIM 6 — kullanıcıdan manuel

ADR 0005 akışının son iki adımı. BDC ekran-bağımlıdır, yavaştır, hata yakalaması zordur → son çare.
ADIM 6'ya gelindiyse **akış-dışı çözüm İCAT EDİLMEZ** (ADR 0005 B6).

### ⛔ HİÇBİR ZAMAN

- Standart tabloya SQL (`INSERT/UPDATE/DELETE/MODIFY`) — Z'li programda bile (ADR 0005 B5).
- Standart tabloya managed Z BO üzerinden `MODIFY ENTITIES` (std/05 §5 B satırı).
- İş mantığını atlayan iç FM (ADIM 4 ⛔).

---

## Profil ayarı *(profil matrisi REHBERDİR — hücreler canlı testle doğrulanır)*

| Profil / politika | Uygulanan adımlar | Durum |
|---|---|---|
| `s4_private` + `balanced` / `classic` | 1 → 6 tam zincir | ölçüldü (satış siparişi: EML + BAPI canlı) |
| `s4_private` + `strict` | 1 · 2 (yalnız released) · 3 → 6 | matristen (`released_apis_only: true`), ölçülmedi |
| `s4_public` | 1 · 2 (yalnız released) · 3 → 6 | matristen (platform-enforce), ölçülmedi |
| `btp_abap` | 3 (uzak released API) → 6 | matristen, ölçülmedi |
| `ecc` | 2 (BAPI) → 4 → 5 → 6 — released kavramı yok | matristen, ölçülmedi |

---

## Gerekçenin yazılacağı yer (MUST)

Standart nesneye yazan her geliştirmenin TS'inde **"API seçimi"** alt bölümü bulunur
(`standards/04` TS BÖLÜM 6.4). Asgari içerik:

| Yöntem | Sistemde? (canlı) | Released? | Commit (ADIM 0 bağlamında) | Hata yönetimi | Karar |
|---|---|---|---|---|---|
| EML `I_…TP` | 1a-1d sonucu | … | … | … | ★ seçilen / reddedildi: neden |
| BAPI `BAPI_…` | … | … | … | … | … |
| OData / FM / BDC | … | … | … | … | … |

+ Clean Core seviyesi (A/B/C/D — `01-naming.md` §5). **Reddedilen alternatif ve nedeni
yazılmadan seçim tamamlanmış sayılmaz** — sonraki geliştirici aynı araştırmayı baştan yapar.

## Sınırlar (kapsam beyanı)

- "EML önce" sırasının canlı kanıtı **satış siparişidir** (`I_SalesOrderTP` ile gerçek belge
  yaratıldı; aynı iş için BAPI da canlı çalıştı). Teslimat, fatura, MM, FI nesnelerinde released
  BO'nun operasyon/alan kapsamının eksiksiz olduğu **ölçülmedi** ⇒ ağaç *"önce EML'i TEYİT et"*
  der, *"EML zorunlu"* demez. Teyit tutmazsa ADIM 2'ye inmek kural ihlali değil, kuralın kendisidir.
- Bu standart yeni bir gate açmaz (ADR 0019). Zorlama: TS şablonu + bug-expert yargısı + mevcut
  BE-24/26/37 maddeleri (BE-26 zaten deterministik gate'li).

## İlgili

- [`../governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md`](../governance/decisions/0005-sap-standart-obje-koruma-ve-sistem-state-yasaklari.md) — anayasal sıra
- [`05-coding-rap.md`](05-coding-rap.md) §2 · §5 · §9X — RAP track, Clean Core okuma
- [`02-coding-backend.md`](02-coding-backend.md) — klasik track (SEGW + BAPI)
- [`../playbook/adt-rap.md`](../playbook/adt-rap.md) §33-§35 — EML reçeteleri ve tuzakları
- [`../playbook/checklists/bug-checklist-backend.md`](../playbook/checklists/bug-checklist-backend.md) — BE-14 · BE-24 · BE-26 · BE-37 · BE-53 · BE-73 · BE-74 · BE-76
- [`../playbook/modules/sd.md`](../playbook/modules/sd.md) SD-K3/K5 — SD'ye özgü BAPI örnekleri
