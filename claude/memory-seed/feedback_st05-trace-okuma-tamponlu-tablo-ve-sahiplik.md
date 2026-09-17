---
name: feedback_st05-trace-okuma-tamponlu-tablo-ve-sahiplik
description: "ST05 trace'inde bir tablonun yokluğu/varlığı kanıt değildir — önce TAMPON durumunu ve o tabloyu BAŞKA KİMİN okuduğunu ölç"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 414b9f97-d5b7-49bd-86f5-e7e1616c1af4
---

ST05 SQL trace teşhiste en güçlü araçtır **ama iki tuzağı vardır ve ikisi de sessizdir.**

**① TAMPONLU TABLO TRACE'TE GÖRÜNMEZ.** Yokluğu "okunmadı" demek DEĞİLDİR.
Ölçüldü (DD09L `PUFFERUNG`): `KOTP001`/`KOTP100` = `X` · `T683S` = `G` · `ZSD000_T_PARTI` = `X`
⇒ üçü de trace'te **hiç** çıkmaz. Buna karşılık `KONDP` · `PACKKP` · `PACKPO` · `/SCDL/DB_*`
tamponsuzdur ⇒ **onların yokluğu anlamlıdır.**
→ Bir tabloyu "ara ve yoksa şu sonucu çıkar" demeden ÖNCE `DD09L`'den tampon durumunu ölç.

**② VARLIĞI DA KANIT DEĞİL — o tabloyu BAŞKA KİM OKUYOR?**
`/SCDL/DB_PROCI_O` trace'te vardı ve bir an "bizim yedek yolumuz koştu" sanıldı; oysa o tablo
EWM'in **kendi** teslimat kalem tablosudur, standart mal çıkışı boyunca sürekli okur ⇒ varlığı da
yokluğu da bizim kodumuz hakkında **hiçbir şey** kanıtlamaz.
→ Ayırt edici olarak yalnız **bize özel** okumalar kullanılır.

**Why:** Vaka 2026-08-11. Yukarıdaki iki hata da yapıldı; ikisi de yanlış çıkarıma götürdü.
Doğru kanıt sonunda trace'in **satır metninden** çıktı: SQL'in WHERE'ine
`AND N'CDS_Access_Control' = N'DENY'` enjekte edilmişti (CDS yetki reddi).

**How to apply:**
- Trace'i **PROGRAM kolonuyla filtrele** — kendi sınıfının adıyla. Kaç SQL çıktığı tek başına
  teşhistir ("tek SQL var" = akış orada durmuş).
- Trace dosyası CSV'dir; `OBJECT` + `STATEMENT_WITH_VALUES` + `PROGRAM` + `USER_NAME` kolonları
  ham WHERE koşulunu ve **kimin koştuğunu** verir. Ham dosyayı oku, ST22/ST05 ekran özetiyle yetinme.
- İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_debugger-farki-aslinda-kullanici-farki]]

Son-doğrulama: 2026-08-11 · Applies-to: s4_private · ECC dahil tüm ST05 kullanımları
