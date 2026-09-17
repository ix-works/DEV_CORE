---
name: feedback_kardes-artefakt-benzerligi-kip-semantigini-kanitlamaz
description: "Çalışan kardeş artefaktla aynı fonksiyonu kullanmak o fonksiyonun KİPİNİ kanıtlamaz; kanıt \"kullanılıyor\" değil \"bu parametre değeriyle koşmuş\" olmalı"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 48bcccdc-68ae-4a1a-96f1-4a32db57747e
---

Bir fonksiyon kardeş artefaktlarda **kullanılıyor** olması, senin kullandığın **kipte**
çalıştığını kanıtlamaz. Kanıt cümlesi *"bu fonksiyon çalışan pakette var"* değil,
**"bu fonksiyon BU PARAMETRE DEĞERİYLE çalışan bir koşuda ölçüldü"** olmalıdır.

**Vaka (2026-09-01, ZSD001 <MUSTERI-C>, bedeli 4 ölü IDoc + 2 yanlış teşhis):**
CPI `FixValues` fonksiyonu `vmstrategy=2` kipinde `vmdefault`'u **uygulamaz** — tabloda
eşleşme yoksa **girdiyi aynen geçirir**. Düğüm koşulumuz varsayılanın `X` döndürmesine
dayanıyordu; fonksiyon ham tarihi döndürüyordu ⇒ karşılaştırma hep false ⇒ **29 düğümün
hepsi sessizce sustu**. Hata yok, segment yok, tek satır log yok.

`FixValues` altı kardeş pakette de vardı ve *"kanıtlı sözlükte"* sayılıyordu — ama hepsi onu
**yalnız listelenmiş anahtarlarla** kullanıyordu; **varsayılan yolu o paketlerde hiç
koşmamıştı**. Benzerlik tam da ayırt edici olan yeri gizledi.

**Why:** Yapısal benzerlik (aynı `fname`, aynı brick şekli, aynı bağlam) güçlü bir sinyal
gibi görünür ve iki tur boyunca beni yanlış eksene kilitledi ("bağlam derinliği", sonra
"`context` niteliğinin kendisi"). İkisi de ölçümle çürüdü; asıl fark **parametre kipiydi**.
Sessiz-false dönen bir koşul, gürültülü hata veren bir koşuldan çok daha pahalıdır —
çünkü teşhis yüzeyi bırakmaz.

**How to apply:**
- Bir fonksiyonu "kanıtlı" saymadan önce sor: *kardeş artefakt onu **hangi parametre
  değeriyle** koşturuyor?* Kullandığın değer o kümede yoksa **kanıtlı değildir** — kanıtsız
  say ve işaretle.
- Varsayılan/fallback yoluna dayanan koşul kurma. Mümkünse **pozitif eşleşmeye** dayan:
  `stringEquals(FixValues(x, {…}), x)` gibi "pass-through oldu mu" idiomları varsayılanı
  hiç kullanmaz.
- Sessizce hep-false olabilecek her koşul için **prob alanı** planla — ara değeri koşulsuz
  bir hedefe yaz. Ama probu **tek değişkenli** kur: [[feedback_ters-yon-kontrolu]] ile aynı
  disiplin — prob v1'de hem bağlamı hem fonksiyonu birlikte değiştirdiğim için o tur hiçbir
  şeyi ayırt edemedi ve bir tur daha yandı.
- Üretece **kalıcı kapı** koy (bu vakada: dolu `vmdefault` = `exit 1`). Ders metni değil,
  kapı: [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]].

İlgili: [[feedback_ajan-bulgusu-dogru-mekanizmasi-yanlis]] ·
[[feedback_gurultulu-duser-iddiasi-olculmeden-yazilmaz]] ·
[[feedback_idoc-segment-alani-alfabesi-hedef-tablodan-farkli]]
