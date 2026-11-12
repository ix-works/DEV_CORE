---
name: feedback_bash-heredoc-kacis-ve-utf8-bozulmasi
description: "Bash tool'una gecen komut metni ters-bolu kacislarini ve Turkce karakterleri BOZAR — tirnakli heredoc bile korumaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 08f4a439-ebf4-425b-9d0a-f815401919b3
---

Bash tool'una verilen komut **metni**, Python'a ulaşmadan önce bozulabilir. İki ölçülmüş vaka (2026-08-20, aynı oturumda):

1. **`python -c "...ÖZGÜ · canlı..."`** → Türkçe karakterler mojibake oldu, `SyntaxError: invalid character '·' (U+00B7)`.
2. **`python - <<'PY'` (TIRNAKLI heredoc)** içinde `'\\n'` yazdım — Python'a **gerçek newline** olarak ulaştı, literal `\n` değil. Tırnaklı heredoc'un shell-expansion'ı engellemesi bunu KURTARMADI. Sonuç: "iki satırı birleştir" düzeltmesi satırı **yeniden böldü** ve ben "birleştirildi" diye rapor ettim — `print()` sabit metni de aynı kaçıştan geçtiği için **çıktı da yalan söyledi**.

**Neden:** Bozulma tool katmanında, Python'dan önce olur — yani Python tarafında ne yaparsan yap, kaynak metin zaten yanlıştır.

**Nasıl uygula:**
- Türkçe/diakritik içeren dosya içeriği yazacaksan **Write/Edit tool'unu kullan** (Bash değil). Bkz. [[feedback_powershell-utf8-bom-trap]] — o PowerShell BOM'u içindi, bu ayrı bir sınıf.
- Ters-bölü gerekiyorsa script içinde **`chr(92)`** ile kur; kaynak metne `\` KOYMA.
- `export PYTHONIOENCODING=utf-8` konsol tarafını çözer ama **girdi bozulmasını çözmez** — ikisini karıştırma.
- ⭐ **Kendi `print('OK')` satırın kanıt değil**: sabit metin de aynı kaçış yolundan geçer. Düzeltmeyi **dosyayı yeniden okuyup ölçerek** doğrula ([[feedback_exit0-degil-cikti-kaniti]] aynı ders, farklı yüzey).

**3. vaka (2026-09-13) — kaçış hatası BAŞKA bir dosyanın gerçek yola yazmasına yol açtı:** gerçek dosyaya yazan betikten
"kopya yolunu kullanan deneme betiği" türetiyordum. Heredoc içindeki `.replace('\\', '/')` Python'a `'\'` olarak ulaştı →
`SyntaxError` → deneme betiği **yeniden üretilmedi**. Bir önceki (başarısız `sed`) adımdan kalan deneme betiği ise
**gerçek yolu** taşıyordu ve zincirde koştu: projenin `governance/infra-findings.md`'sine sahte SHA'larla yazdı (+37/-4). Kopyada
0 değişiklik görünce yakalandı, `git checkout --` ile geri alındı (dosyada başka commit'siz değişiklik yoktu — önceden ölçülmüştü).
- Türetilmiş/deneme betiğini üretmeden ÖNCE **sil** (`rm -f`); çalıştırmadan önce içinde gerçek yolun **olmadığını assert et**.
- Gerçek dosyaya yazan betik yolu mümkünse **argümanla** alsın (hardcode yol = deneme türetmeyi kırılgan yapar).
- Deneme koşumunda **gerçek dosyanın md5'ini önce/sonra** ölç — "kopyada değişiklik yok" belirtisi tek başına geç kalır.
- Üretici betiği heredoc ile değil **Write ile dosyaya** yaz (bu dersin 1. maddesi — tekrar edildi).

**4. vaka (2026-09-25) — regex kelime sınırı dosyaya KONTROL BAYTI olarak girdi:** heredoc'la çalışan düzenleme betiğinde
`r'\\b'` → hedef `.py` dosyasına `0x08` (backspace) yazıldı. Regex hiç eşleşmedi → fonksiyon canlıda "0 kayıt" döndü; ekranda
görünmez, Edit aracı da o satırı eşleştiremedi. Onarım: Write ile yazılmış bayt düzeltici (`bytes([8])` → `bytes([92, 98])`).
- Kod dosyası düzenlendikten sonra **`tr -cd '\010' < f | wc -c`** (0 olmalı) — bug-gate'e de bayt sayımını ekle.

**5. vaka (2026-10-14, AYNI OTURUMDA İKİ KEZ) — kabuk TEST VEKTÖRÜ üretimi sessizce geçersiz ölçüm verdi:** guard canlı
sondasında heredoc'taki Python'da `'it'\\''s'` / f-string içinde `\\''` yazdım → komut `'it'''s` oldu (kaçış yok). Sonuç
ilk seferde "apostrof düzeltmesi canlıda çalışmıyor" (sahte AÇIK), ikincisinde "4. turdan sonra regresyon" (sahte REGRESYON)
gibi okundu; ikisinde de ajana yanlış soru gidebilirdi. Yakalayan: komutu **yazdırıp gözle bakmak** + kontrol grubu.
- Kabuk vektörü üretirken ters-bölü DAİMA `chr(92)` ile; tek tırnak kaçışını `Q = "'" + chr(92) + "''"` gibi kur.
- Ölçüm tablosuna **üretilen komutun kendisini** de bas — sonuçtan önce vektörü doğrula.
- Eski guard sürümünü `.tmp/` altına kopyalayıp koşmak `rc 1` (import kırığı) verir — rc 1 ölçüm değildir, satırı at.

Son-doğrulama: 2026-10-14 · Applies-to: Windows Git Bash tool katmanı, python heredoc/`-c`, kabuk test vektörü üretimi · bu çekirdeği kullanan tüm projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
