---
name: feedback_adt-readback-md5-disk-md5-ile-dogrudan-kiyaslanamaz
description: "ADT readback md5'i disk md5'iyle DOĞRUDAN kıyaslanamaz — payload kapanış \n'ini taşımaz; ayrıca sap_sync_pull .ccimp'i hiç tazelemez"
metadata:
  node_type: memory
  type: feedback
---

İki ayrı ölçüm tuzağı, ikisi de **sahte ıraksama** üretir:

**① Kıyas tanımı.** ADT'nin döndürdüğü kaynak payload'ı dosyanın **kapanış `\n`'ini taşımaz**.
Bu yüzden readback md5'i ile disk md5'i **doğrudan kıyaslanamaz**. Doğru kural:
`CRLF→LF` normalize **et**, sonra disk metnine `txt.rstrip("\n")` uygula, **ondan sonra** kıyasla.

**② `sap_sync_pull --type class` yalnız `/source/main` çeker — `.ccimp`'i HİÇ tazelemez**
(aracın kendi uyarısı). ccimp'te "pull ettim, tazedir" demek sahte güvendir; ccimp canlısı
`adt_grep_source` + `include: "implementations"` ile okunur.

**Why:** 2026-09-16'da bir ccimp diskte `ae7acea1…`, SESSION_NOTES readback'inde `366de181…` çıktı.
CRLF **sebep değildi** (dosya zaten LF). "Bayat/ıraksadı" demek yerine **ÖLÇÜLEMEDİ** etiketlendi;
sonra ölçüldü: `rstrip("\n")` uygulanmış hash **birebir** tuttu (46587 baytta birebir = özdeş).
Kontrol grubu: aynı tablodaki **7 readback hash'inin 7'si** bu kuralla tuttu, ham hash ile **0/7**
(tek "tutmayan" bayat 1. tur hash'iydi, 2. tur değeri tuttu).

**How to apply:**
1. Bir readback hash'i tutmuyorsa **önce kıyas tanımını** sorgula, dosyayı değil.
2. Kapı koşarken md5 tutmazsa **DURMA** — diski kendin ölç, farkı raporun en başına yaz, devam et
   ([[feedback_kapi-kosarken-dosya-donar-md5-teyidi]]).
3. "satır hizası + birkaç noktada metin eşitliği" ≠ **byte özdeşliği**; niteliyi düşürme.

Son-doğrulama: 2026-09-16 · Applies-to: SAP ADT (s4_private), sınıf/ccimp readback
İlgili: [[feedback_sap-sync-pull-repo-ileri-ezme]] · [[feedback_behavior-pool-main-empty-ccimp-trap]] ·
[[feedback_arac-basarisizligini-zararsiz-sayma]]

---
**Son-dogrulama:** 2026-09-16 (ders yazim tarihi — o gunden beri YENIDEN OLCULMEDI) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
