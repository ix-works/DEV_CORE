---
name: feedback_tarama-ciktisi-hipotezdir-is-listesi-degil
description: Kaba grep/tarama çıktısı bir HİPOTEZDİR — brifinge iş listesi diye yazmadan önce her kalemi kendi semantiğiyle doğrula; eşleşen parça ile sembolün adı aynı şey değildir
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 48bcccdc-68ae-4a1a-96f1-4a32db57747e
---

Bir tarama (grep / desen eşleşmesi / dosya sayımı) sana **aday** verir, **envanter** vermez.
O çıktıyı doğrudan bir iş listesine ya da ajan brifingine tablo olarak yazarsan, taramanın
**yanlış pozitiflerini ve eksiklerini** iş emri hâline getirmiş olursun. ⛔ Özellikle: bir
regex'in **eşleşen parçası** ile aradığın **sembolün adı** aynı şey değildir.

**Why:** 2026-08-22'de aynı sınıf hatayı **ÜÇ kez** yaptım ve üçünü de ajanlar/kapı düzeltti:
- **A1:** statik tarama *"9 fixture kusurlu"* dedi (dizge yok diye); **davranış** ölçümü **7**
  dedi — ikisi `argparse` kullandığı için bilinmeyen bayrağı zaten reddediyordu. Tarama
  ayrıştırma **biçimini** göremez.
- **N3:** `grep -oE "_(KABUK|SAP|YAZMA|TOOL)[A-Z_]*\s*="` ile *"tool kümesi tanımlayan
  hook'lar"* listesi çıkardım ve **eşleşen parçayı sabit adı sanıp** brifinge tablo yazdım.
  Beş addan **üçü uydurmaydı** (`_TOOLLARI` · `_YAZMA` · `_SAP_KOMUT_IMZALARI` yok) ve iki
  hook'u (`itg_backstop`, `pull_before_edit`) tümden atlamıştım. Ajan beklenen kümeyi
  **AST'den türetti**: gerçek kapsam 5/12 değil **7/10** çıktı. Elle tablo teslim edilseydi
  gate iki sabiti bulamayıp **sessizce boş tarardı**.
- **`B31` reçetesi:** bir test korpusunun mutasyon haritasını **elle** yazdım — **beş noktada
  yanlıştı** (iki vektör ters · *"13 kip"* (gerçek **14**) · harita hatalı · turun **merkezî
  kararının tek çivisi** olan mutasyon satırı **eksik** · *"`exit 2`"* (gerçek `rc=1`)).
  Kapı ölçüp düzeltti; harita **aracın kendi çıktısından** yeniden üretildi (**14/14 birebir**).
  ⭐ **Kaldıraç:** reçete kendi girişinde *"F0 okuması buraya bakar, fixture'ın docstring'ine
  değil"* diyordu ⇒ **bir dokümanın "tek kaynak" olduğunu iddia etmesi, doğruluk borcunu ARTIRIR.**

- **2026-09-01 (ZSD001 EDI):** <MUSTERI-A> korpusunu (746 dosya) `NAD+BY` için taradım ve *"belgelenmemiş
  7. kod: `7181`"* diye kullanıcıya **bulgu olarak sundum** — üretecin docstring'i 6 kod diyordu,
  ben "docstring bayat" diye yorumladım. ⛔ Gerçekte klasör **karışıktı**: 10.071 `DELFOR` + **19
  `ORDERS`** mesajı; `7181` YALNIZ `ORDERS`'ta geçiyor (ve orada tesis `NAD+ST`'de, `NAD+BY`'de
  değil). Mesaj tipine (`UNH`) göre ayırınca sayılar docstring ile **rakam rakam** tuttu
  (`30008`=7777). Kullanıcı *"bunu daha önce vermemişsin, Excel'de de yok"* diye sorunca çıktı.
  ⭐ **Ders:** bir korpus klasörünün adı ("GELEN/<MUSTERI-A>") **tek mesaj tipi** demek DEĞİLDİR.
  Segment sayarken önce **kapsayıcıyı** (mesaj tipi / şema / sürüm) ayır, sonra say — yoksa
  başka bir akışın alanını kendi akışının "yeni değeri" sanırsın. Mevcut ölçümle (docstring)
  çelişen bir tarama, önce **kendi kapsamını** sorgulamalı.

**How to apply:**
- Tarama sonucunu **hipotez** diye etiketle; brifinge yazmadan önce her satırı **kendi
  semantiğiyle** doğrula (sembol gerçekten var mı · davranış gerçekten öyle mi).
- Bir **envanter** üretiyorsan (hangi dosyalar/semboller kapsamda), kaynağı **yapıdan türet**
  (AST / import / **aracın kendi çıktısı**) — metin desenine güvenme. Türetilen envanter bayatlamaz.
- ⭐ **Aracın kendi listesini bastırabiliyorsan onu KOPYALA.** Geçersiz bir argüman
  (`--mutasyon-ZIRVA` gibi) çoğu koşucuda geçerli seçenekleri basar; elle yazmak yerine o
  çıktıyı al ve **karşılaştırarak doğrula** (sıfır fark bekle).
- Brifinge tablo koyuyorsan **nasıl ölçtüğünü de yaz** — ajan çelişki görürse düzeltebilsin.
  ⭐ Bu iki vakada da beni kurtaran şey buydu: brifte *"ölç, varsayma"* yazılıydı ve ajan
  tabloyu koda karşı sınadı.
- ⛔ *"Ajan zaten kontrol eder"* diye gevşeme: brifing yanlışsa ajanın **kapsamı** yanlış
  başlar; düzeltmesi bir tur maliyetidir, bazen hiç fark edilmez.

İlgili: [[once-yuzey-taramasi-sonra-is-listesi]] (taramayı YAP) · [[exit0-degil-cikti-kaniti]] ·
[[sonucu-olc-uygulamayi-degil]] · [[kopya-sayimi-tek-sozdizimi-desenine-dayanma]]
