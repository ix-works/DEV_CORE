---
name: feedback_adt-include-objesi-prog-tipiyle-404-sahte-negatif
description: ADT araclarinda include objesi 'prog' tipiyle sorgulanirsa 404/exists:false doner — SAHTE NEGATIF; dogru tip 'include'
metadata:
  type: feedback
---

`adt_get` / `adt_lock_check` çağrılarında bir **include** objesi `object_type: 'prog'`
ile sorgulanırsa **`404` → `exists: false`** döner. Bu bir SAHTE NEGATİFTİR — obje
canlıda vardır. Doğru tip **`'include'`**'dur (ADT ucu `/programs/includes/`).

Ölçüm (2026-09-06, <SISTEM>/100, `ZSD001_I_TP_LOAD_C01`+`T01`):
`adt_get(type='prog')` → 404/exists:false · aynı anda `TADIR`+`TRDIR` → obje VAR,
`SUBC='I'`, `DELFLAG` null. `type='include'` ile aynı obje okundu ve readback yapıldı.

Ek: `adt_lock_check` bir include için `locked: null` + `http_404` dönebiliyor
(kilit ucu yok). Bu **"kilitli değil" DEĞİL, "ÇÖZÜLEMEDİ"** demektir — kilit kanıtı
push'un 409 vermemesinden gelir, bu dönüşten değil.

**Why:** "obje yok" sonucu geri dönülemez kararlara yol açar — yeniden yaratmaya,
"push edilmemiş" teşhisine, yanlış paket/transport kararına. Araç tipi yanlışken
alınan negatif, objenin durumu hakkında hiçbir şey söylemez.

**How to apply:** Include sorgularken tipi `'include'` ver. Bir ADT aracı
`exists:false`/`404` dönerse ve obje canlıda olmalıysa, **TADIR/TRDIR ile çapraz
kontrol et** — negatifi tek araç dönüşüne dayandırma. `locked: null` gördüğünde
"kilitsiz" yazma, "ölçülemedi" yaz. İlgili: [[feedback_exit0-degil-cikti-kaniti]],
[[feedback_arac-basarisizligini-zararsiz-sayma]],
[[feedback_ajan-olumsuz-donusu-kanitla-sorgula]].
