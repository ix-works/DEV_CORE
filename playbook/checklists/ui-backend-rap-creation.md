# Checklist — UI Uygulaması RAP Backend Oluşturma

> **Manuel + script gate.** RAP backend SAP-yazma → `run_review.py` (ADR 0006)
> ZATEN var ([`rap-creation.md`](rap-creation.md)). Bu liste onun ÜSTÜNE,
> ORDER'de yaşanan **patinajları ORDER'te tekrarlamamak** için sıra/karar
> kontrolüdür (reviewer bunları yakalamaz — sıralama/mimari kararlar).
>
> **İlgili:** [`../ui-backend-rap.md`](../ui-backend-rap.md) · kanonik:
> [`../adt-rap.md`](../adt-rap.md) §32 · standart: [`../../standards/05-coding-rap.md`](../../standards/05-coding-rap.md)

---

## Faz 1 — CDS mimari kararı (kod yazmadan)

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| BE-CDS-01 | Aggregation/count gerekiyorsa → ayrı **helper view** + assoc (root 1:1 korunur), root'a `group by` KONMADI | BLOCKER | §A2 |
| BE-CDS-02 | İfade (`cast/coalesce/case`) **interface** view'da, projeksiyon düz expose | BLOCKER | §A1 |
| BE-CDS-03 | Computed/türetilmiş alan interface'te; projeksiyon expose; BDEF'te `field(readonly)` ile bildirilmedi | WARNING | §A3 |
| BE-CDS-04 | Z obje masterLanguage TR (raw REST/TR shell), text tahmin değil | BLOCKER | ADR 0005 D · §E4 |

## Faz 2 — BDEF / numbering

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| BE-BDEF-01 | NR'li key → BDEF'te **`early numbering`** keyword VAR; CCIMP `earlynumbering_create FOR NUMBERING` + `NUMBER_GET_NEXT` | BLOCKER | §B1 |
| BE-BDEF-02 | Numara için **determination KULLANILMADI** (key-set determination = DETVAL/contract dump) | BLOCKER | §B2 |
| BE-BDEF-03 | `numbering : managed` CHAR key ile KULLANILMADI | BLOCKER | §B3 |
| BE-BDEF-04 | Composition child KEY alanı `field ( readonly : update )` (B.4) | BLOCKER | §B5 |
| BE-BDEF-05 | `authorization master ( global )` ise boş `get_global_authorizations` var | BLOCKER | §B6 |
| BE-AUDIT-01 | Tabloda audit alanı varsa: idempotent `setAdmin` det (root+child, `{create;update}`, instance-guard, `IN LOCAL MODE`); operatöre kural teyidi (create→tümü, update→updated_*). `with additional save` + early-numbering KULLANILMADI (create component boş). Edm.Time → UI/export Time tipi | BLOCKER | §F · ADR/std 05 §9A |

## Faz 3 — det/val izolasyon

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| BE-DV-01 | Önce SAF CRUD aktive + e2e YEŞİL doğrulandı | BLOCKER | §B4 |
| BE-DV-02 | det/val TEK TEK, her biri ayrı aktive+test ile eklendi (toplu değil) | WARNING | §B4 |

## Faz 4 — Aktivasyon sırası

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| BE-ACT-01 | Sıra: interface CDS → projection CDS → BDEF → behavior class → SRVD | BLOCKER | §C1 |
| BE-ACT-02 | CDS değişti → üstündeki BDEF re-activation yapıldı | BLOCKER | §C1 |
| BE-ACT-03 | Circular "CREATE not activated" → staged (BDEF tek aktive → sonra class) | BLOCKER | §C1/C3 |
| BE-ACT-04 | Aktivasyon sonrası `adtcore:version="active"` doğrulandı | BLOCKER | rap-creation C-RAP-ACT-01 |

## Faz 5 — Tooling

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| BE-TOOL-01 | Brand-new DDLS `populate_cds_views.py --only --force-recreate` ile (MCP push lock-cache bug); retry-loop YAPILMADI | BLOCKER | §E1 |
| BE-TOOL-02 | `run_review.py` çalıştırıldı (MCP timeout → skip_reviewer + manuel) | BLOCKER | §E3 · ADR 0006 |
| BE-TOOL-03 | "HTTP 400 pre-audit" tek seferde DROP edilmedi; gerçek hata alınıp tekrar denendi | WARNING | §A4 |

## Faz 6 — Servis & doğrulama

| ID | Kontrol | Severity | Ref |
|---|---|---|---|
| BE-SRV-01 | Yeni entity → SRVD `expose` + aktive; yeni alan (mevcut entity) → SRVD değişmez | BLOCKER | §D1/D2 |
| BE-SRV-02 | Kullanıcıya **tek** Unpublish→Publish talimatı verildi | BLOCKER | §D1 |
| BE-SRV-03 | Canlı `$metadata` GET → yeni alan/entity VAR mı deterministik kontrol (UI testine göndermeden) | BLOCKER | §D3 |
| BE-SRV-04 | e2e deep-create POST → 201 + numara + validasyon kanıtı | BLOCKER | §0.7 |
| BE-FIN-01 | Yeni backend patinajı varsa `ui-backend-rap.md`/`adt-rap.md`'ye eklendi (T1/T2) | WARNING | T1/T2 |

---

**Kullanım:** Faz 1-2 kod yazmadan; 3-5 geliştirme sırasında; 6 kapanış öncesi.
`run_review.py` (rap-creation.md) bu listenin yerine geçmez — ikisi birlikte.
