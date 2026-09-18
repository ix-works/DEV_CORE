---
name: feedback_metadata-alan-dogrulama-tip-kapsamli-olmali
description: "$metadata'da alan doğrulaması DAİMA tip-kapsamlı yapılır — belge-geneli arama SAP__Signature/SADL altyapı tiplerinden sahte eşleşme üretir (canlı vaka 2026-08-07)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9274e391-5e92-433d-99ec-c9744b364de6
---

**Kural:** OData `$metadata`'da bir alanın tipini/özelliğini doğrularken **önce tipi izole et**
(`ComplexType Name="X"` … `</ComplexType>` ya da `EntityType Name="Y"` bloğu), **sonra** `Property`
ara. Belge-geneli `Name="Alan"` araması **sahte eşleşme** üretir.

**Neden (canlı vaka 2026-08-07, <PAKET-B> M1):** İki ajan aynı servisi okuyup çelişen sonuç bildirdi —
biri *"`Reason` MaxLength YOK"*, diğeri *"`MaxLength="256"`"*. **İkisi de gerçek bir satır okumuştu:**

| Nerede | Satır | MaxLength |
|---|---|---|
| `ComplexType ZSD001_I_OPENQTY_R` ← **bizim sözleşmemiz** | `<Property Name="Reason" Type="Edm.String" sap:label=""/>` | **YOK** |
| `EntityType SAP__Signature` ← **SAP Gateway/SADL altyapısı** | `<Property Name="Reason" … MaxLength="256" …/>` | 256 |

`SAP__Signature` **her** OData V2 servisinin metadata'sında bulunur; bizim yazdığımız bir obje değil.
Aynı belgede `MaxLength="256"` taşıyan **11** altyapı Property'si var (`Title`, `Name`, `Type`,
`Value`, `Header`, `FileName`…) ⇒ 256 orada **çok yaygın bir desen**, alana özel bir şey değil.

**Zararı:** yanlış ölçüm, olmayan bir kusur için doküman/kod düzeltmeye ya da gereksiz republish'e
yol açar. Bu vakada hakem turuyla yakalandı; yakalanmasaydı doğru bir CDS yorumu "yanlış" diye
düzeltilecekti.

**Uygulama:** ajan brifinglerinde `$metadata` doğrulaması istenirken **"tip-kapsamlı ara"** açıkça
yazılır; rapora **satırın kendisi** yapıştırılır ("MaxLength yok" demek yetmez — hangi tipin içinden
okuduğu görünsün).

**Genel sınıf:** bu, *"aynı ada sahip iki şey"* tuzağıdır — grep'in kapsamı daraltılmadığında en
yaygın/ilk eşleşme kazanır. Aynı refleks `where-used`, `$metadata`, TADIR ve i18n aramalarında da
geçerli. İlgili: [[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_ayni-hash-degil-olu-kod]]

**Son-doğrulama:** 2026-08-07 (gateway hakem ölçümü; iki servis, taze GET, sha256'lı)
**Applies-to:** OData V2/V4 `$metadata` okuyan her rol (lider + alt-ajanlar) · profil-bağımsız
**CORE'a terfi:** metodoloji-nitelikli → `playbook/lessons-learned.md` PATTERN adayı.
