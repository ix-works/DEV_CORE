---
name: feedback_ters-yon-kontrolu
description: "Her \"A→B var mı\" kontrolünün İKİZİ koşulmalı: \"B var, atıf alıyor mu?\" Tek yön temiz olması yarım sonuçtur — ileri yön build'i kırar (gürültülü), ters yön SESSİZ ölü/eksik iş bırakır"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 500a163e-c3ce-4b97-9c3d-35322425892b
---

**Tek yönlü varlık kontrolü yarım kontroldür.** Çoğu denetim refleks olarak **ileri yönü** kurar
(*"kullanılan her şey tanımlı mı?"*) çünkü kırılan yön odur. Ama **ters yön** (*"tanımlı her şey
kullanılıyor mu?"*) kırılmaz — **sessizce ölü ya da eksik iş** bırakır.

**Vaka (2026-08-19, ZSD001).** *"Belgede anılan her mesaj katalogda var mı"* → **temiz** (build'i
kıran yön). Kimse *"katalogdaki her `E` mesajının bir üretim noktası var mı"* diye sormamıştı;
sorulunca **4 bulgu** çıktı — ve **ikisinde arkasındaki iş kuralı hiç yazılmamıştı**:
onaylı bir *"miktar sıfırdan büyük olmalıdır"* mesajı vardı ama aktarım ön koşullarında
**pozitif-miktar guard'ı yoktu**; onaylı bir *"beyanname tarihi ileri tarihli olamaz"* mesajı vardı
ama **böyle bir kural hiçbir yerde tanımlı değildi** (ve o tarih FIFO sırasının kaynağı).
Aynı turda ters yön üç bulgu daha verdi: onaylı **13 obje** build planında yoktu · **175 alanın**
bir kısmının yazanı/okuyanı yoktu · **7 kabul kriterinin** hiçbir testi yoktu.

**Why:** İleri yön **gürültülüdür** — eksikse kod patlar, aktivasyon düşer, biri fark eder.
Ters yön **sessizdir** — fazlalık ya da bağlanmamış tanım hiçbir alarm üretmez, yalnız *"yapıldı
sanılan iş"* olarak durur. Bu yüzden ters yön **kasten** aranmalıdır; kendiliğinden ortaya çıkmaz.

**How to apply — her denetimde ikizi kur:**
| İleri (refleks) | Ters (unutulan) |
|---|---|
| Kullanılan her mesaj katalogda mı? | Katalogdaki her mesajın **üretim noktası** var mı? |
| Kullanılan her ad onaylı mı? | Onaylı her ad **planda/uygulamada** geçiyor mu? |
| Her test bir kabul kriterine bağlı mı? | Her **kabul kriteri** bir teste bağlı mı? |
| Okunan her alan tanımlı mı? | Tanımlı her alanın **yazanı ve okuyanı** var mı? |
| Çağrılan her obje mevcut mu? | Mevcut her objenin **tüketicisi** var mı? |

⚠ Ters yön **yanlış pozitife** meyillidir (bir alan prose'da kavram adıyla anılıyor olabilir).
Çıktıyı **üç kovaya** ayır: *kesin yetim* (hiç geçmiyor) · *şüpheli* (yalnız kavram adıyla) ·
*temiz* — ve **yalnız birinci kova bulgudur**.

İlgili: [[feedback_duzeltme-turu-kendi-ciktisina-kapi-ister]] · [[feedback_yesil-sinyalin-kapsamini-sor]] ·
[[feedback_dogrulama-sezgileri-dort-kural]] · [[feedback_ayni-hash-degil-olu-kod]]
