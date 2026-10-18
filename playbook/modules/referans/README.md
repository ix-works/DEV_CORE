---
applies_to: [s4_private]
layer: L3
type: reference
scope: project-wide
status: active
purpose: Modül-bilgi katmanı — SAP fonksiyonel modüllerinin (SD/MM/FI...) standart referansı (tablo, BAPI, enhancement, SPRO, tcode, akış)
---

# Modül-Bilgi Katmanı — `playbook/modules/referans/<mod>/`

> **Ne bu:** SAP fonksiyonel modüllerinin semantik **referansı** — kilit tablolar, BAPI/FM,
> enhancement noktaları, customizing, tcode, iş akışları. `sap-abap-dev` skill'i o modülde
> çalışırken bu dosyalara yönlendirir (Tier 2).
> **Ne DEĞİL:** intake triage kural-paketi. O, bir üst dizinde `playbook/modules/<mod>.md`
> dosyasıdır (tetik-haritası + kontrol + soru; ADR 0022). İkisi ayrı amaçlıdır: kural-paketi
> *ne sorulmalı / neye bakılmalı* der, bu klasör *standart SAP'de ne nerede* der.
>
> **Konum geçmişi:** 2026-10-18'e kadar bir proje reposunun `governance/modules/` klasöründe
> yaşıyordu; core skill'i o yola atıf yaptığı için diğer projelerde ölü yoldu. Proje/paket
> izleri ayıklanarak buraya taşındı.

## Şablon (her modül 6 dosya)
`tables.md` · `bapi.md` · `enhancements.md` · `spro.md` · `tcodes.md` · `workflows.md`

## Mevcut modüller
| Modül | Klasör |
|---|---|
| **SD** (Sales & Distribution) | [`sd/`](sd/) |
| MM / FI / CO / PP / PM / QM ... | modül işi başlayınca **artımlı** yazılır (14 modülü baştan yazma) |

> ⚠️ İçerik standart SAP **referans** bilgisidir (okuma/farkındalık) — **otorite değil,
> hipotezdir.** ADR 0005-A: bu standart objelere dokunulmaz. **Ne zaman doğrula:** bir alan/
> tablo/BAPI adını koda veya spec'e yazmadan önce, o sistemde varlığını ve released durumunu
> canlıda teyit et (alan adları sürüm/sistem bağımlıdır; S/4'te bazı tablolar gömülüdür).
