---
name: feedback_python-yazdigi-liste-crlf-tasir-xargs-sessizce-bosa-koser
description: "Windows'ta Python'un yazdığı satır listesi CRLF taşır; git/xargs'a beslenince her ad sonunda \r kalır, eşleşme tutmaz ve işlem SESSİZCE hiçbir şey yapmaz. `| wc -l` çıktıyı sayarken HATA satırlarını sayar ⇒ başarı gibi görünür."
metadata:
  node_type: memory
  type: feedback
---

**KURAL:** Bir aracın (Python, PowerShell) yazdığı **satır listesini** başka bir araca
(`git`, `xargs`, `--pathspec-from-file`) besleyeceksen, Windows'ta **CRLF varsayımıyla
davran**: `tr -d '\r' < liste > liste2`. Ve sonucu **sayarak değil, kanıtla** doğrula.

**ÖLÇÜLMÜŞ VAKA (2026-09-09, <PROJE> dal temizliği).** Python ile 70 dal adını bir
dosyaya yazdım (`open(...).write("\n".join(...))` — Windows'ta metin kipi `\n`'i `\r\n`
yapar), sonra:
```
cat sil_td.txt | xargs -r git branch -D 2>&1 | wc -l   →  70
```
`70` gördüm ve *"70 dal silindi"* diye rapor ettim. **Hiçbiri silinmemişti.** Dal adları
`chore/agent-memory-gece-2\r` olarak gidiyordu, git bulamıyordu; o 70 satır **hata
mesajıydı**. Yakalanma anı: sonraki durum ölçümünde `git branch | wc -l` **70** dedi
(1 olmalıydı). Teşhis: `head -3 liste | cat -A` → `chore/...^M$`.

**Why:** İki kusur üst üste bindi ve ikisi de **sessiz**:
1. **Kodlama kusuru** — CRLF taşıyan ad hiçbir şeye eşleşmez, ama `git branch -D` bunu
   "hata" olarak stderr'e yazıp devam eder; kabuk zinciri kırılmaz.
2. **Ölçüm kusuru** — `2>&1 | wc -l` başarı ile başarısızlığı **aynı sayıya** çevirir.
   Bu, [[feedback_exit0-degil-cikti-kaniti]]'nın kardeşi: burada "exit 0" yerine
   "beklenen sayıda satır" sahte yeşil üretti.

**How to apply:**
- Python'dan liste yazarken **`newline="\n"`** ver (`open(p,"w",newline="\n")`) ya da
  tüketmeden önce `tr -d '\r'` uygula. `git add --pathspec-from-file` için de aynısı geçerli.
- Toplu işlemi `xargs ... | wc -l` ile **doğrulama**. Ya döngü kur ve **başarılı/başarısız
  ayrı say**, ya da işlemden **sonra durumu ölç** (`git branch | wc -l` → beklenen değer).
  Sayının kendisi kanıt değildir; **son durum** kanıttır.
- Bir listenin şüpheli olduğunu 2 saniyede anlamanın yolu: **`head -3 dosya | cat -A`** —
  `^M$` görünüyorsa CRLF'tir.
