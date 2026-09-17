---
name: feedback_sonucu-olc-uygulamayi-degil
description: "Bir işin yapılıp yapılmadığını ölçerken KENDİ hayalindeki uygulamayı arama — SONUCU ara. 'grep <benim-önerdiğim-sınıf-adı>' 0 dönebilir çünkü ajan gerekçeli olarak BAŞKA (ve daha doğru) bir uygulama seçmiştir. Doğru ölçüm: git diff / davranış / dosya-değişti-mi."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a4cd7d32-a718-41a3-9b19-f70f390d9ff7
---

Lider bir ajanın "şu işi yaptım" iddiasını doğrularken, brifingde **kendi önerdiği** uygulamayı
aradı: `grep -c 'zsd001ItemCompact'` → **0** ⇒ "yapılmamış" hükmü verdi ve ajanı yanlış yere
geri gönderdi. Gerçek: ajan o sınıfı **gerekçeli olarak kullanmamıştı** (o sınıf yalnız hücre
fontunu ayarlıyor, başlığa dokunmuyordu; istenen "hücre 0.6875 + başlık 0.75" kombinasyonu
karşılanmıyordu) ve **aynı dosyada, aynı desende yeni bir sınıf** tanımlamıştı.
Yani iş YAPILMIŞTI; ölçüm yanlış şeyi arıyordu.

**Why:** Bu, ajanlara sürekli yazdığımız *"grep 0 ≠ yok"* kuralının **liderdeki** hâli.
Brifingde bir uygulama ÖNERMEK meşrudur; ama doğrulama aşamasında o öneriyi **beklenen çıktı**
sanmak, ajanın daha iyi bir çözüm seçmesini "hata" gibi gösterir. Sonuç: gereksiz tur, ajanla
karşılıklı "yaptım/yapmadın" tartışması, güven kaybı.

**How to apply — doğrulama sırası:**
1. **`git status` / `git diff --stat`** — hangi dosyalar değişti? (uygulamadan bağımsız)
2. **Etkiyi ara, adı değil** — "font küçüldü mü" → `git diff <css>` içinde `font-size`;
   "kolon eklendi mi" → binding/kolon sayısı; "kural kondu mu" → davranış dalı.
3. Ancak bundan sonra spesifik ad ara — ve 0 dönerse **"başka nasıl yapılmış olabilir"** diye sor.
4. ⛔ Ölçüm ile ajanın raporu çelişiyorsa, **önce ölçümün doğru şeyi aradığını** doğrula;
   ajanı suçlamadan önce bu adımı atlama.

⚠ İkinci yüz: **`git diff` boş dönmesi "yapılmadı" demek DEĞİLDİR** eğer ajan henüz
commit'lememişse — çalışma ağacına bak (`git status --short`), HEAD'e değil. Ajanlar commit
etmez (commit=lider), dolayısıyla iş DAİMA çalışma ağacındadır.

📌 Operasyonel yan-ders (aynı turda): koşan bir ajana `SendMessage` ile gönderilen revizyon,
ajan işini bitirme aşamasındaysa **o tura yetişmeyebilir**. Ajan "yapmadım" değil "görmedim"
durumundadır. Revizyon kritikse: ajan idle olduktan SONRA gönder, ya da gönderdikten sonra
sonucu ölçüp teyit et. Suçlamadan önce zamanlamayı düşün.

Son-doğrulama: 2026-08-09 (ZSD001 portal dialog turu — lider iki kez yanlış hüküm verdi)
Applies-to: TÜM projeler · ajan çıktısı doğrulayan her lider adımı
