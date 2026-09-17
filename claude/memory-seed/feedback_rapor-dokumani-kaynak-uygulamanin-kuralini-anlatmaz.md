---
name: feedback_rapor-dokumani-kaynak-uygulamanin-kuralini-anlatmaz
description: "Rapor FS/TS'i yalnız raporda GÖRÜNENİ anlatır; veriyi üreten uygulamanın kuralını (kilit/zorunluluk/muafiyet) yazarsan her düzeltme turu yeni hata doğurur — iddia yüzeyini daralt"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4924b64d-79dd-407f-adb3-ac337efdbae4
---

2026-09-11 ZSD001 FS/TS v1.3 (69 kolon, plaka kolonları): doküman kapısı **5 tur** sürdü
(BLOCKER → WARNING → BLOCKER → BLOCKER → …). Kapı bulgusunu "düzeltirken" yazar her turda
rapor dokümanına **booking uygulamasının** kurallarını ekledi: "kalıcı kilit" → "belge var olduğu
sürece kilitli" → "iptal/silinirse kalkar" → "doldurmak zorundadır" → "KMY'de dorse ekranda gizli".
Her yeni kural ayrı bir kaynağa (FE binding, BDEF, ccimp, CDS matrisi) bağlıydı ve her birinde
yeni yanlış çıktı (kilit yalnız UI'daydı, "iptal" kodda yok, rapor dorse kolonunu her satırda gösterir).
Yöntem değişip ("rapor dokümanı yalnız raporda gözleneni anlatır, kurallar tek cümle atıfla sahibine")
iddia yüzeyi daraltılınca bulgular ana iddialardan noktasal kesinlik sorunlarına indi.

**Why:** Tüketici doküman, üretici uygulamanın kuralını anlatınca o kuralın TÜM kaynak zincirini
doğrulama yükümlülüğünü üstlenir — ama test edeni rapordan gözleyemez (KR-03). Düzeltme turu
"eksik nitelendirme" bulgusunu daha çok nitelendirme ekleyerek kapatmaya meyillidir; bu regresyon üretir
([[feedback_duzeltme-turu-kendi-regresyonunu-uretir]]).

**How to apply:** Kapı bir tüketici dokümanda (rapor FS/TS/KD) başka uygulamanın davranışına dair
bulgu verdiğinde düzeltme brifine ÖNCE şunu yaz: "cümleyi düzeltme — rapordan gözlenebilir mi? değilse
ÇIKAR". Test beklentisi yalnız rapor kolonuyla yazılır; canlı örnek BOOKIT gibi kaynak tabloda değil
**rapor view'inde** okunmuş olmalı. Aynı turda boş CHAR ↔ SQL NULL ayrımını da ölç (`IS NULL` ve `= ' '`
ayrı sorgu; ADT preview boşu `null` gösterir — [[feedback_adt-preview-bos-char-null-render]]).
Yönlendirme cümlesi hedef dokümanı adıyla verir ve hedefte içeriğin VAR olduğu doğrulanır.
İlgili: [[feedback_gocsuz-sema-degisikliginde-kilavuz-bos-diyemez]].
