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
`SyntaxError` → deneme betiği **yeniden üretilmedi**. Bir önceki (başarısız `sed`) adımdan kalan `td_deneme.py` ise
**gerçek yolu** taşıyordu ve zincirde koştu: TD `governance/infra-findings.md`'ye sahte SHA'larla yazdı (+37/-4). Kopyada
0 değişiklik görünce yakalandı, `git checkout --` ile geri alındı (dosyada başka commit'siz değişiklik yoktu — önceden ölçülmüştü).
- Türetilmiş/deneme betiğini üretmeden ÖNCE **sil** (`rm -f`); çalıştırmadan önce içinde gerçek yolun **olmadığını assert et**.
- Gerçek dosyaya yazan betik yolu mümkünse **argümanla** alsın (hardcode yol = deneme türetmeyi kırılgan yapar).
- Deneme koşumunda **gerçek dosyanın md5'ini önce/sonra** ölç — "kopyada değişiklik yok" belirtisi tek başına geç kalır.
- Üretici betiği heredoc ile değil **Write ile dosyaya** yaz (bu dersin 1. maddesi — tekrar edildi).

Son-doğrulama: 2026-09-13 · Applies-to: Windows Git Bash tool katmanı, python heredoc/`-c`

---
**Son-dogrulama:** 2026-09-13 (ders yazim tarihi — o gunden beri YENIDEN OLCULMEDI) · **Applies-to:** bu cekirdegi kullanan tum projeler

⚠ **ARAC IDDIASI** — bu ders *"bugun su arac/kapi boyle davraniyor"* der, yapisal bir olgu
degil. Arac surumu degismis olabilir: davranisa **dayanmadan once bir kez olc**. (Vaka: bir
kardes ders, dayandigi kusur duzeltildikten sonra 3 hafta bayat yasadi; tohuma alinmadan
once olculup elendi.)
