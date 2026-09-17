---
name: feedback_yabanci-runtime-artefakti-once-tek-vaka-turu
description: "Koşturamadığın bir çalışma zamanı için artefakt üretiyorsan (CPI mapping, başka sistemin config/DSL dosyası), yerel doğrulayıcıların yalnız KENDİ NİYETİNİ ölçer — hedef sistemin İCRASINI değil. Genellemeden önce TEK vakayla gerçek tur şart."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c31f28ee-4a43-48ea-97e0-cc0425bce1b8
---

**KURAL:** Çıktıyı **senin çalıştıramadığın** bir motor yorumlayacaksa (SAP CPI message mapping,
başka bir sistemin config/DSL/şema dosyası), kendi yazdığın doğrulayıcı **hedef semantiği değil,
senin o semantiğe dair varsayımını** test eder. Bu yüzden:

> **Genellemeden ÖNCE tek vakayla gerçek tur.** Bir dosya → hedef sistemde koş → çıktıyı kaynakla
> karşılaştır. Ancak ondan sonra 1300 dosyaya/6 müşteriye yay.

**Ölçülmüş vaka (2026-08-24, ZSD001 <MUSTERI-D> CPI mapping):**
Üretilen `.mmap` için üç yerel kapı kuruldu ve **üçü de yeşildi**:
`batch.py` 1313/1313 dosyada XSD+segment sayısı · `align.py` 232.106 termin + 12.922 sevk notunun
**değer sırası** birebir · `verify_cpixml.py` CPI'ın **kendi ürettiği kaynak XML** üzerinde 2/11/505/87.
Üçüncüsü bilerek "kontrol grubu" diye kurulmuştu ve kaynak-XML şeklini gerçekten akladı.

**Yine de CPI'da koştuğunda:** 505 termin satırı yerine **11** üretildi ve değerler
**yanlış kalemlere** yazıldı (kalem 1'in ilk 11 satırı 11 ayrı kaleme dağıldı).
Kök sebep: `.mmap`'te **bağlam (context) korunmuyordu** — her kaynak alanı tek düz kuyruğa iniyordu.
Hiçbir yerel kapı bunu yakalayamazdı, çünkü hepsi **benim** motorumdan geçiyordu.

**İki alt-ders:**

1. **"Kontrol grubu" kısmi olabilir.** Kaynak XML'i hedef sistemden almak *girdi şeklini* akladı
   ama *icra semantiğini* aklamadı. Kanıtın **tam olarak neyi** kanıtladığını yaz (DARALT).

2. ⛔ **"Kanıtlanmamış yapıyı kullanma" kuralı ters tepebilir.** Elimdeki tek format örneği
   yalnız tek-değerli başlık alanları içeriyordu; ben de "örnekte geçmeyen fonksiyonu kullanmam"
   diyerek `createIf`'ten kaçındım ve `ifWithoutElse`'i **yanlış rolde** kullandım.
   Dosya hedefte **açıldı ve koştu** ⇒ risk formatta değil **semantikteydi**.
   Örnek bir yeteneği *hiç zorlamıyorsa*, o örnek o konuda **kanıt değil boşluktur** —
   kaçınmak değil, **yer gerçeği istemek** gerekir.

**Aynı hataya iki tur harcandı** (iki farklı fonksiyon denendi, ikisi de aynı sınıfta kaldı).
Sinyal: *pahalı bir çare ilk denemede tutmadıysa tekrarlama, **dayandığı kanıtı** sorgula* —
değişkeni değiştirmek işe yaramıyorsa çevrilen kol yanlıştır.

**Uygulama:** böyle bir teslimde ilk teslim = **1 vaka + geri bildirim kanalı**, tam paket değil.
Ve hedef sistemde üretilmiş bir **referans artefakt** iste; yapılamayanı dışarıdan tahmin etme.

---

## ⭐ EK DERS (2026-08-26) — referans artefakt ÇOĞU ZAMAN ZATEN SENDE

Yukarıdaki "referans artefakt iste" maddesinin **daha ucuz ve daha kesin** hâli:

> **Hedef sistemin KABUL ETTİĞİ bir örnek, kendi sistemin/repo'n içinde duruyor olabilir.**
> Yabancı runtime'a artefakt üretmeden ÖNCE sor: *"bu hedefe daha önce KABUL EDİLEN bir şey
> ürettik mi?"* — üretildiyse o örnek **şartnamenin ta kendisidir**, tahmine gerek kalmaz.

**Vaka:** <MUSTERI-D> CPI mapping 3 tur boyunca `V4 050` "geçersiz tarih" aldı. Üç hipotez ölçülüp
çürütüldü (E1EDP16 tarihleri · `ABNRD` boşluğu · `BSTDK` boşluğu) — 4 canlı IDoc dökümü harcandı.
Cevap **Temmuz'dan beri kendi kod tabanımızda**, çalışan üreticinin yorum satırındaydı:
`ls_p16-edatub = ls_s-edatu.  " = EDATUV (gun; bos -> "gecersiz tarih")`.
Aynı sistemde **statü 53** ile kayıt olmuş 6 IDoc, o programın ürünüydü.

**İki operasyonel kural:**

1. **Kabul edilmiş örneği DURUM ALANINDAN ara, ad'dan değil.** Envanteri "başarı durumu" ile
   sorgula (`EDIDC.STATUS='53'`, başarılı job/log, arşiv), çünkü *"bunu daha önce yaptık mı"*
   sorusunun cevabı obje adında değil **çalışma-zamanı kaydındadır**. Tek SQL yetti:
   `SELECT status, COUNT(*) FROM edidc WHERE mestyp='DELINS' GROUP BY status` → 6 adet statü 53.
2. **Çalışan örnek + çalışmayan örnek = kontrol grubu; farkı ALAN ALAN çıkar.** Diff'i üç kovaya
   ayır (yalnız çalışanda dolu · yalnız çalışmayanda dolu · ikisinde farklı değer). "Yalnız
   çalışanda dolu" kovası **doğrudan iş listesidir** — burada `EDATUB`, `BSTDK`, kalem-düzeyi
   `ABNRD` çıktı ve üçü de gerçekti.

⛔ **Yan tuzak — "savunmacı mapping" boş alan üretir.** Hedefte var olan ama kaynağın
göndermediği bir alanı "ileride gelirse dolar" diye bağlamak, düğümü **yaratıp boş bırakır**.
Tip semantiği burada belirleyicidir: `DATS` alanında **boşluk ≠ `00000000`** — SAP birincisine
"tarih yok" değil **"GEÇERSİZ tarih"** der ve tüm belgeyi reddeder. Kaynağı olmayan alanı
bağlama; bağlayacaksan **gerçek bir değerle** besle.

İlgili: [[feedback_placeholder-tuzagi-once-mevcut-artefakt]] · [[feedback_alan-anlamini-ddic-etiketinden-dogrula-tvak-fkara-fkarv]]

İlgili: [[feedback_sonucu-olc-uygulamayi-degil]] · [[feedback_yesil-sinyalin-kapsamini-sor]] ·
[[feedback_kod-yolu-vardi-veri-gecmemisti]] · [[feedback_dogrulama-sezgileri-dort-kural]]
