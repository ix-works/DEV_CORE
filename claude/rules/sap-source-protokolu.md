---
paths: **/*.abap, **/*.ddls, **/*.asddls, **/*.bdef, **/*.behavior, **/*.srvd, **/*.srvb, **/*.ddlx, **/.rules.md
---

# SAP kaynağına dokunurken (L1b — bu kural eşleşen dosya okununca yüklenir)

## 1. PULL-BEFORE-EDIT (ADR 0016) — ANALİZDEN ÖNCE
Repo kopyası SAP'deki aktif sürümden bayat olabilir. **Tazelik doğrulanmadan edit YOK.**
Gate: `core/scripts/hooks/pull_before_edit.py`. Drift varsa önce çek, sonra düşün.

## 2. REVIEWER PRE-FLIGHT (ADR 0006) — SAP'YE YAZMADAN ÖNCE
`python core/scripts/validators/run_review.py` →
`PASS` → yaz · `WARNING` → yaz + raporla · **`BLOCKER` → YAZMA.**

## 3. ADT İŞLEM SIRASI
DDIC (domain → DTEL → struct → tablo) → CDS → BDEF → behavior class → SRVD → SRVB publish.
- Aktivasyon **HTTP 200 sahte-OK verir**: `activationExecuted` + `type="E"/"A"` ile değerlendir.
  `severity=` attribute'u YOKTUR. "Activated" mesajına güvenme → `adt_get` ile canlı doğrula.
- BDEF + behavior class **BİRLİKTE** aktive edilir.
- Inline aktivasyon YASAK (sahte-OK). `adt_activate` kullan.

## 4. YAZMA TEK KAPIDAN
SAP'ye yazan **tek rol `adt-gateway`**'dir. Diğer ajanlar tasarlar + yerel kaynak hazırlar.
Gateway **commit/push etmez** — push/activate yapar, lider'e raporlar.

## 5. DOSYA YERLEŞİMİ
`<source_root>/<MODULE>/<PKG>/` altında obje-tipi klasörleri. Paket kuralları o paketin
`.rules.md`'sinde (L4). Yeni paket → `bootstrap_package.py`.

## 6. KESİN YASAKLAR (ADR 0005 — hatırlatma; tam metin kök CLAUDE.md'de)
Z/Y ile başlamayan standart objeye dokunma · standart tablo verisine direkt SQL yok
(BAPI→RFC→BDC→manuel) · transport/package yaratma-release yok · Z obje = `master_language`
login + 4 alan label TAM.

📖 Derin referans (otomatik yüklenmez): `core/AGENTS.md` §5.5, §5.6, §6 · `core/playbook/`
