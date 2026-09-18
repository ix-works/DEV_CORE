---
name: check-annotasyonu-fail-yonunu-belirlemez
description: DCL `#CHECK` tek başına ne fail-open ne fail-closed demektir — yön TÜKETİCİNİN tasarımının özelliğidir; ayrıca DCL'in VAR olduğu ayrıca ölçülmelidir
metadata:
  node_type: memory
  type: feedback
---

Released CDS'e geçerken `@AccessControl.authorizationCheck: #CHECK` görüp
"fail-closed" (ya da "fail-open") sonucuna **varma**. `#CHECK` yalnızca
*"DCL VARSA uygula"* demektir. İki ayrı şey ölçülmeden yön bilinemez:

1. **DCL gerçekten var mı ve neyi kısıtlıyor?** Annotation'a bakmak yetmez —
   DCL'i oku (`adt_get … dcls`). <PAKET-A>'da ölçüldü: `I_Customer` →
   `F_KNA1_GEN`(actvt 03)+`F_KNA1_GRP`+`F_KNA1_BED`. `F_KNA1_GEN` koşulu
   `( ) = aspect pfcg_auth(…)` — alan listesi boş ve `?=` değil **`=`** ⇒
   yetkisiz kullanıcıda **her satır elenir**.
2. **Tüketici 0 satırı nasıl okuyor?** Yön buradadır. Varlık kapısı olan
   tüketici (`ev_found` ≠ `ev_blocked`, 0 satır → hata) **fail-closed**;
   değeri kolon olarak yayan, varlık kapısı olmayan projeksiyon 0 satırı
   "bloke değil" diye okur ⇒ **fail-open**. Aynı halef CDS, iki farklı yön.

**Bunu neden yazıyorum:** aynı paketin RESUME'ünde iki doğru ölçüm ("parser
fail-closed" ve "fail-open riski") tek cümleye sıkıştırılıp niteleyicileri
düşürülmüştü; sonraki tur bunu **çelişki** sanıp "hangisi hipotez" diye
aramaya çıktı. İkisi de ölçümdü, farklı nesneler hakkındaydı.

**Yan sonuç — devreye alma:** ham tablo okuması yetki süzgeci uygulamaz,
halef CDS uygular. Geçişten sonra **veri yokluğu ile yetki yokluğu ayırt
edilemez hale gelebilir**; job/arka plan kullanıcısının yetkisi ayrı bir
önkoşuldur ve genelde geliştiricinin kendi (geniş yetkili) kullanıcısıyla
ölçülemez. Bkz. [[feedback_clean-core-released-cds-proaktif]] ·
[[feedback_kapsam-niteleyicisini-dusurme]] · [[feedback_ters-yon-kontrolu]] ·
[[feedback_kod-yolu-vardi-veri-gecmemisti]]
