---
name: feedback_bos-gondermek-hic-gondermemek-degildir
description: "SAP API/BAPI'de bir alanı BOŞ göndermek ile HİÇ göndermemek farklı sonuç verir: boş = boş yaz, yok = kaynaktan türet"
metadata:
  type: feedback
---

Bir SAP API/BAPI çağrısında bir alanı **boş değerle göndermek**, o alanı **hiç göndermemekle**
aynı şey değildir:
- **boş gönderirsen** → hedef belgeye **boş yazılır** (aktif bir "bunu boşalt" emri)
- **hiç göndermezsen** → SAP alanı **kaynak belgeden türetir** (sipariş → teslimat gibi)

**Ölçülmüş vaka (2026-09-10, ZSD001 sevk emri → teslimat):** Sevk emri ekranından Incoterms
alanı kaldırılacaktı. Lider *"teslimata gitmiyor"* diye ölçmüştü — ölçüm dardı: doğru olan
**"bizim kodumuz göndermiyor"**. Kullanıcı işin gerçeğini verdi: *"teslimat Incoterms taşıyor
ama sen bir şey vermeyince siparişte ne ise onu alır, ayrışma gerekiyorsa teslimatı ayrıştırır."*
⇒ Alanı kaldırırken payload'a **boş** koymak, bugün doğru çalışan türetmeyi bozacaktı.
✅ O evde tehlike yapısal olarak kapalıydı: teslimat deep-create JSON'u **alan alan elle**
kuruluyor, `MOVE-CORRESPONDING`/toplu yapı kopyası yok
(`ZCL_SD015_DELIVERY_API.ccimp.abap:505-521`, dosyada `inco` = 0 eşleşme).

**Why:** Bir alanı "kaldırmak" iki farklı teknik eyleme çevrilebilir ve ikisi de kodda
masum görünür (`lv_x = ''` ile alanı hiç yazmamak). Fark yalnız **hedef sistemin
davranışında** ortaya çıkar ve orada da **sessizdir** — hata vermez, belge yaratılır,
yanlış olan tek şey bir alanın içeriğidir. Bu yüzden testte de kolayca gözden kaçar.
Ayrıca "kısıtı kaldırırsak yanlış belge oluşur mu?" korkusunun cevabı çoğu zaman
**standardın kendi ayrıştırma/türetme mekanizmasıdır** — kısıt eklemeden önce standardın
zaten ne yaptığını sor.

**How to apply:**
- Bir alanı bir çağrıdan çıkarırken **payload'da boş bırakma — satırı tamamen sil**.
  BAPI'lerde ayrıca X-yapısı/alan maskesi varsa orada da işaretleme.
- Payload'ın **nasıl kurulduğunu** ölç: alan alan elle mi, yoksa `MOVE-CORRESPONDING`/
  `CORRESPONDING #( )` ile toplu mu? Toplu kopyada istenmeyen alan **sessizce sızar**;
  o zaman "kaldırmak" için açık bir `CLEAR` değil, açık bir **dışlama** gerekir.
- ⛔ *"Bizim kodumuz göndermiyor"* ile *"hedef belge o alanı taşımıyor"* AYRI iddialardır —
  ikincisini iddia edeceksen hedef belgede ÖLÇ ([[feedback_kapsam-niteleyicisini-dusurme]]).
- Türetmeye güveniyorsan bunu **koda yorum olarak yaz** — sonraki tur "alan eksik" sanıp
  doldurmasın.

İlgili: [[feedback_kod-yolu-vardi-veri-gecmemisti]] · [[feedback_ecc-referansi-is-anlayisi-icin-mimari-degil]]
