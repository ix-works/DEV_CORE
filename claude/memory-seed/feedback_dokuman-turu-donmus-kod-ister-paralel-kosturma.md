---
name: feedback_dokuman-turu-donmus-kod-ister-paralel-kosturma
description: "Doküman turu (FS/TS/KD + ekran görüntüsü) DONMUŞ koda bağlıdır. Kod düzeltme turuyla PARALEL koşturulursa aynı bedel üç kez ödenir: md5 çapası bayatlar, satır referansları kayar, ekran görüntüleri yeniden çekilir. Duvar saatinden kazanmaz, kaybettirir."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7be4eb27-4593-4b9b-a0fd-793cd5aa7970
---

**KURAL:** Doküman üretimi (FS/TS/KD, ekran görüntüleri, PDF) kodun **donmuş** olmasını
gerektirir. Kod düzeltme turu hâlâ uçuşta iken doküman ajanı başlatma. Sıra **seri**dir:
**KOD DONDU (md5 çapası) → doküman turu**. Paralel koşturmak duvar saati kazandırmaz,
rework üretir.

**ÖLÇÜLMÜŞ VAKA (2026-09-09, ZSD001 teslimat toplama listesi).** FE düzeltme turu
(`toplama-fe-fix`) ile iki doküman turunu (`doc-kd-toplama`, `doc-fs-ts-toplama`) aynı anda
başlattım. Aynı bedel **üç kez** ödendi:
1. Ajanlara verdiğim FE md5 çapaları **iki kez bayatladı**; ikisi de yeniden ölçmek zorunda
   kaldı ve biri "senin çapan tutmadı" diye ayrı bir raporlama turu harcadı.
2. TS, düzeltme İNMEDEN önceki dosyaya göre yazıldı ⇒ §10.1 mesaj envanterindeki **13
   referanstan 8'i tam +10 kaydı** (düzeltmenin eklediği yorum bloğu kadar). `:2749`
   `msgPickPrintNotFound` sanılıyordu, gerçekte eşik dalıydı. Lider yakaladı → elle düzeltti
   → ajan yapısal çözümü getirdi (satır-no → **metod/dal çapası**). **Üç tur.**
3. FE düzeltmesi inince KD'nin ekran görüntüleri **yeniden çekilmek** zorunda kaldı
   (mock-shim kaldırma + 2 görüntünün yeniden üretimi).

Ayrıca aynı pencerede bir **kayıp-güncelleme** doğdu: lider, ajanın sahibi olduğu TS'e haber
vermeden yazdı; ajan bunu mtime + md5 ile fark edip sordu. Bu da paralelliğin bedeliydi.

**Why:** Doküman, kodun **o anki** hâlinin bir fotoğrafıdır — md5, satır numarası, ekran
görüntüsü, mesaj metni, hepsi koda çapalıdır. Kod oynadıkça fotoğraf sessizce yalanlanır ve
bu **sessiz** bir kusurdur: belge derlenir, kapı yeşil yanar, PDF üretilir; yanlışlığı ancak
biri satırı açıp bakınca görünür. Paralellikten beklenen kazanç (iki iş aynı anda) yanlış
hesaptır, çünkü ikinci işin **girdisi** birinci işin çıktısıdır.
[[feedback_kapi-kosarken-dosya-donar-md5-teyidi]] aynı ailedendir — orada kapı için geçerli
olan şey burada doküman için geçerli. [[feedback_lider-ajan-paralel-yazim-cakismasi]] bunun
dosya-sahipliği yüzüdür.

**How to apply:**
- Kod düzeltme turu varsa doküman ajanını **BAŞLATMA**. Önce "KOD DONDU + md5" al, sonra
  brifle. Duvar saati kaygısıyla üst üste bindirme.
- Zorunlu olarak binmişse: doküman ajanına **sabit md5 çapası verme** — "işe başlarken
  kendin ölç, tutmuyorsa DUR ve sor" de. Çapa vermek, bayatlayınca **yanlış güven** üretir.
- Belgeyi koda **satır numarasıyla** bağlama. Oynak artefaktta çapa = **metod/dal adı**
  (adları da yazmadan önce ölç — bu turda `_openPickPrintAsk` sanılan yer aslında
  `onPickPrintFromResult` çıktı). [[feedback_capayi-ada-cevirmek-de-bir-olcumdur]]
- Dosya sahipliğini **açıkça** böl (FS/TS bir ajan · KD + görüntüler öbürü · lider yalnız
  commit). Liderin "küçük bir düzeltme" diye ajanın dosyasına yazması kayıp-güncelleme üretir.
- Ekran görüntüsü üreten harness'i, ürettiği görüntülerin **tamamını** kapsayacak biçimde
  tut: bu turda script 17 görüntünün 13'ünü üretiyordu, kapsam dışı kalan 3'ünden 2'si
  aylardır çöp veri taşıyordu ve yeniden yayımlanan kılavuzda canlıya gidiyordu.
