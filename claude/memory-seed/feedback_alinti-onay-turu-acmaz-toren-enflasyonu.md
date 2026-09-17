---
name: feedback_alinti-onay-turu-acmaz-toren-enflasyonu
description: "ALINTI onay turu AÇMAZ — provenance damgası (`[TS]`/`[ONERI]`) onay kuyruğu değildir; <PAKET-A>'de bu ayrımın kaybı 15 onay belgesi + çok turlu 'metin onay töreni' üretti (kardeş <PAKET-B>: 1750 anahtar, 0 belge)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c20182a3-2866-4571-9b91-5c1f1e595fd2
---

## ⛔ KURAL: **alıntı onay turu AÇMAZ**

`feedback_zli-obje-text-tahmin-yasak` zaten şunu söylüyor: *"Önce kanonik kaynağı ara.
**Bulunduysa öneri değil ALINTI yap.**"* ⇒ Alıntının onaya sunulacak bir şeyi yoktur.
Kullanıcı onayına **yalnız** şu ikisi gider:
1. **Yeni bir iş kavramının** görünen adı / durum metni (ölçümle türetilemez)
2. **Z'li objenin DDIC etiketleri** (ADR 0005-D, 4 field label)

⛔ **Bir anahtara `[TS]`/`[ONERI]` damgası vurup onayı ERTELEMEK yapılmaz.**
Damga **provenance**'tır — *"bunu şu belgeden aldım"*. Onay **kuyruğu** değildir.
Bu ayrım kaybolursa her build turu kuyruğu büyütür ve iş bitmez.

**Why:** Ölçüm (2026-09-05, <PROJE>):

| Paket | Uygulama | i18n anahtarı | Metin onay belgesi | SESSION_NOTES | RESUME |
|---|---|---|---|---|---|
| **<PAKET-A>** | 6 | 327 | **15** | 5491 | 3403 |
| <PAKET-B> | 15 | **1750** | **0** | 4725 | — |
| <PAKET-C> | 4 | 196 | **0** | 1259 | 549 |

<PAKET-B> **beş kat** büyük ve hiç metin onay turu yapılmadı. Yani gecikme uygulamanın
büyüklüğünden değil, **yalnız <PAKET-A>'ye uygulanan bir törenden** geldi. Sonuçta 327
anahtarın **283'ü** (43 + 7 + 233) alıntı/DDIC/emsal çıktı; gerçek öneri **7**, hiçbir
yerde olmayan **1** (o da onaylı iki kavramın birleşimi).

**How to apply:**
- Metin yazarken kaynağı bul → **alıntıysa yaz ve geç**, şerhe çapayı koy. Onay turu açma.
- Öneriysen (kaynak yok) **o an sor**, biriktirme. Biriken öneri = tören.
- Bir metin onay belgesi **kalemin kendisi** için tutulur, **envanter** için değil.
- Sayarken **onay kaydı korpusu** ile **spec korpusu** ayrı tutulur:
  *spec'te geçmek, onay kaydı olmak değildir* — ama tersi de: **spec'ten alıntı olmak,
  onay gerektirmek de değildir.** İkinci yarısı <PAKET-A>'de unutuldu.

## Aynı sınıftan ÖTEKİ tören enflasyonları (<PAKET-A>'de ölçüldü, kardeşlerde YOK)

- **TS'i 13 parçaya bölüp doküman derleme hattı kurmak** — `assemble.py` +
  `test_assemble_gfm.py` + `test_gfm_bos_satir.py` + 4 betik. Kardeş paketlerin
  hiçbirinde yok; TS tek dosyadır. Dokümanın **build sistemi + birim testi** olması
  ürüne değer katmaz, tur üretir.
- **Çapanın deftere dönmesi** — RESUME 3403 satır (<PAKET-C>: 549). `feedback_capa-liste-degil-KURAL-olmali`
  zaten bunu söylüyor; <PAKET-A>'de uygulanmadı.
- **Kapı turu enflasyonu** — SESSION_NOTES'ta 36 "gate/kapı" geçişi (<PAKET-C>: 10).
  Her düzeltme turu kendi kapısını, o kapı da yeni bulgu üretti.

⭐ **Ortak kök:** üçü de *"ölçmek"* kılığına girmiş **yeniden ölçmek**. Ölçüm işi bitirmek
için yapılır; iş bitmiyorsa ölçüm törene dönüşmüştür. Test: *"bu turun sonunda kullanıcının
elinde ÇALIŞAN ne var?"* — cevap yoksa tur gereksizdir.

İlgili: [[feedback_zli-obje-text-tahmin-yasak]] · [[feedback_capa-liste-degil-KURAL-olmali]] ·
[[feedback_curutme-de-bir-iddiadir-yerine-yazilan-sayi-olculur]] ·
[[feedback_karar-verimliligi-asiri-kapi-yok]]
