---
name: feedback_multiinput-yazili-metin-validator-zorunlu
description: "Rapor seçim ekranında MultiInput'a addValidator konmazsa yazılan değer (ör. bir org kodu + Enter) token olmaz; Listele yalnız getTokens() okuyorsa değer $filter'a SESSİZCE girmez → süzgeçsiz geniş rapor. Her yeni/kopyalanan filtre ekranında validator + Listele kapısı + büyük harf + MaxLength zorunlu (core FE-50)"
metadata:
  type: feedback
  seed: evet
  originSessionId: 8865df6b-2e94-44e8-8952-84b42fc53742
  modified: 2026-10-16T07:52:19.583Z
---

Kullanıcı sordu: "satış org'a elle org kodunu yazınca kabul etmiyor, mutlaka seçmek mi gerekiyor?" Ölçüm (2026-10-16, canlı DEV):
SD rapor uygulamasında bir org kodu (temsilî `<VKORG>`) + Enter/Tab → token 0. Zorunlu alanda "zorunlu alan" uyarısı çıktı (görünür). Zorunlu olmayan
Müşteri alanına yazılan bir müşteri numarası (temsilî `<KUNNR>`) ise **`$filter`'a hiç girmedi**, rapor süzgeçsiz geniş sonuç döndü (sessiz).
Kök neden: `addValidator` yok + `onList` yalnız `getTokens()` okuyor. Kardeş taraması: aynı şablondan türeyen 8 SD rapor
uygulamasının 8'inde eksik; yalnız iki uygulamada vardı. Kök neden standarttaydı:
core std/03 FE-32 "kanonik referans: kopyala" diyordu ve o kopyada validator yoktu.

**Why:** kullanıcı girdisini yok sayan filtre hata vermez, *daha fazla* veri döndürür; "çalışıyor" görünür. Kullanıcı
kararı: "hepsinde düzeltelim, bundan sonraki geliştirmelerde buna uyumlu hareket etmek için kalıcı hale getirelim" +
"bug-expert'in checklist'inde de olsun".

**How to apply:** her yeni ya da kopyalanan rapor filtre ekranında, her `MultiInput`'ta:
- validator (VH token'ıyla aynı anlam)
- kod alanında büyük harf (VH range dahil)
- `MaxLength` + toast
- yazılı koşul işaretini reddet
- Listele'de token'a dönüşmemiş metin kapısı (`msg.untokenized`)
- VH Tamam'da kalan metni koru

Ölçüm kaynak okumasıyla değil: yaz + Enter → Listele ağ izinde `$filter`. Vaka projesindeki referans uygulamada
yardımcı `makeValidator` adıyla `util/ValueHelp.js`'te durur (tüketici repoda).
Kanonik: core std/03 §10.0.1 *Yazılı metin → token* · bug-checklist-frontend **FE-50** · ui-freestyle-odata-v2 §C C6 · lessons-learned PATTERN #43 (core PR #333).

Son-doğrulama: 2026-10-16
Applies-to: freestyle UI5 1.120 + OData V2 rapor seçim ekranları (MultiInput + ValueHelpDialog)
prior-art: yok (core `addValidator|untokenized` = 0; memory'de VH küçük harf dersi komşu: [[feedback_vh-kosul-sekmesi-kucuk-harf-sessiz-bos-sonuc]])
