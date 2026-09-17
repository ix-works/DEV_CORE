---
name: feedback_tr-karakter-varyantli-arama
description: "Müşteri/metin aramasında Türkçe İ/Ş/Ç varyantı — ASCII LIKE 'yok' der (TRİGO vakası)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 147413fa-85a8-4e1e-8abc-7c28606ff1f5
---

DEV'de `KNA1 NAME1 LIKE '%TRIGO%'` (UPPER dahil) **0 satır** döndü; kayıt "TRİGO GROUP" (Türkçe büyük İ) idi — tam dump'ta bulundu (2026-08-16, RESEARCH-02 §1).

**Why:** SAP metinlerinde Türkçe karakter (İ/I, Ş/S, Ç/C, Ğ/G, Ö/O, Ü/U) yaygın; ASCII LIKE sahte "bulunamadı" üretir → yanlış "master data yok" kararı.

**How to apply:** ad/metin aramasında varyantları birlikte dene (`LIKE '%TRIGO%' OR LIKE '%TRİGO%'`), küçük tabloda tam dump ile çapraz kontrol; "0 satır" tek başına kanıt sayılmaz ("bulunamadı ≠ yok" ailesi). İlgili: [[feedback_dogrulama-sezgileri-dort-kural]]

---

**2. VAKA — SAP dışında da geçerli, ve en tehlikeli yeri KABUL ÖLÇÜTÜ (2026-09-01, lider hatası, ajan yakaladı).**
Bir düzeltme turunun kabul ölçütüne *"şu deseni tara → kalıntı 0 olsun"* yazdım; deseni **diyakritikli**
verdim: `düşer|gürültülü|zararsız|etkisiz`. Kaynak dosyalar **ASCII** yazıyor (`duser`, `GURULTULU`,
`zararsiz`) ⇒ desenim **yapısal olarak hiçbir şey bulamazdı**. Ajan iki varyantı da yazdı
(`d[uü][sş]er|g[uü]r[uü]lt[uü]l[uü]|zarars[iı]z|etkisiz`), **4 eşleşme** çıktı, 3'ü gerçek kalıntıydı.
Tek varyantla tarasaydım **"kalıntı 0" SAHTE SIFIRI** kabul ölçütü olarak kayda geçecekti.

⇒ İki ek kural:
1. **Kaynak alfabesini VARSAYMA — ÖLÇ.** Türkçe metin ASCII'ye düzleştirilmiş olabilir (kod
   yorumları, log'lar, assert mesajları neredeyse HEP öyledir). Önce geniş bir turla gör
   (`grep -o 'g.r.lt.l.'` gibi), sonra deseni yaz.
2. ⛔ **Desen bir EMRE/kabul ölçütüne dönüşüyorsa iki kat sorumluluk:** yanlış desen artık senin
   sıfırın değil, **kapının** sıfırı olur ve "ölçüldü" damgası yer
   ([[feedback_aktardigin-olcum-emre-donusunce-kanitini-tasi]]).
⚠ Aynı sınıf **aynı gün ikinci kez**: `grep 'vmdefault="[^"]\+"'` de gerçek XML biçimi
`<param name="vmdefault"><value>D</value></param>` olduğu için hiçbir şey yakalayamamıştı
([[feedback_kopya-sayimi-tek-sozdizimi-desenine-dayanma]] §3). **Sıfır sonuç iki anlamlıdır:**
"yok" ya da "desen tutmadı" — ayırt etmeden ilerleme. Kontrol grubu koy: bilerek EŞLEŞMESİ
gereken bir örneği deseninle test et; o da 0 veriyorsa desen bozuktur.

---

**3. VAKA — ÜRETİLEN HTML'de metin ENTITY olarak kodlanır; düz arama sahte sıfır verir (2026-09-08, lider hatası, ajan yakaladı).**
ZSD001 toplama listesi mock'unda *"⚠ TEMSİLİ VERİ — MOCK"* damgasının basılıp basılmadığını
ölçtüm: üretilen HTML'de `temsi` araması **0** döndü ⇒ kullanıcıya **"damga eksik" diye rapor
ettim**. Yanlıştı: metin HTML'e `&#304;` (İ) gibi **karakter entity**'leriyle yazılmıştı, düz
string araması yapısal olarak bulamazdı. Damga iki sayfada da **vardı** — bağımsız doğrulama
yapan ikinci ajan entity'yi görüp düzeltti.
⚠ Aynı turda **ikinci** bir sahte sıfır daha ürettim: aradığım metin gövde HTML'inde değil
**`render_pdf.js`'in headerTemplate'inde** basılıyordu ⇒ *"yanlış dosyada aramak"* da aynı
sınıftır ([[feedback_hicbir-yerde-yok-demeden-once-nerelere-baktigini-yaz]]).

⇒ Üç ek kural:
1. **Üretilen çıktıda (HTML/XML/JSON) metin arama, KODLAMA katmanından geçer.** Entity
   (`&#304;` `&uuml;` `&amp;`), unicode escape (`İ`), URL-encode — hepsi düz aramayı kırar.
   Doğru ölçüm: **render edilmiş metin** üzerinde ara (PDF ise `pypdf` text-extract; HTML ise
   entity çözerek `html.unescape()`), ya da ASCII-yalın bir çapa kelime seç (`MOCK` gibi).
2. **Aramadan önce "bu metin hangi dosyada ÜRETİLİYOR" sorusunu cevapla.** Başlık/altbilgi
   `headerTemplate`/`footerTemplate` üzerinden basılıyorsa gövde HTML'inde **hiç yoktur**.
3. ⛔ **Sahte sıfırla KULLANICIYA rapor etme.** Bu vakada "eksik" hükmü doğrudan kullanıcıya
   gitti ve düzeltme gerektirdi. Bir eksiklik iddiası yazmadan önce **kontrol grubu** koş:
   var olduğunu bildiğin bir örneği aynı desenle ara; o da 0 veriyorsa desen/dosya yanlıştır.
