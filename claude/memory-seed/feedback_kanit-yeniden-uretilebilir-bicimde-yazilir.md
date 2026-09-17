---
name: feedback_kanit-yeniden-uretilebilir-bicimde-yazilir
description: "Kanıtın BİÇİMİ üçüncü tarafça yeniden üretilebilir olmalı — satır-numarası çapası çürür (komut/alıntı ver), tarifi yazılmamış md5 kapı değildir"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 147413fa-85a8-4e1e-8abc-7c28606ff1f5
---

Bir iddianın **doğru olması yetmez**; onu doğrulayacak kişinin **aynı ölçümü tekrar
üretebilmesi** gerekir. Aksi hâlde kayıt bir *kanıt* değil, bir *hatıradır*. 2026-09-02'de
aynı sınıf **iki farklı biçimde** ölçüldü:

### ⛔ Ayak 1 — hâlâ düzenlenmekte olan dosyaya SATIR NUMARASIYLA çapalanma

`EK-B` kaydındaki tek bir iddia (*"FM'de `lt_msg`'e hiçbir yerde `APPEND` yok"*) **üç kez**
çapalandı: `:296/:385/:414` → `:340/:367` → `:344/:371`. **Üçü de bayatladı.** İddia
**her seferinde doğruydu** — çürüyen **çapaydı**: kaynak aynı gün 388 → 505 → 455 → 470
satır oldu (yorum eklendi/kırpıldı), numaralar her turda kaydı.

⭐ Kök neden ölçüldü: numaralar **yeniden ölçülmeden** önceki turdan kopyalandı
([[feedback_kanit-tazeligi-indeks-ve-zaman-sirasi]] VARYANT 5).

**Çözüm çapanın BİÇİMİNİ değiştirmekti**, içeriğini değil:

```bash
grep -n "lt_msg" <DOSYA>          # → 5 geçiş
grep -c "APPEND.*lt_msg" <DOSYA>  # → 0
```
\+ beklenen **şekil** (`DATA` · motorun `et_msg` bağlaması · bir `READ TABLE` · bir `lines( )`).
Bu çapa dosya büyüse de küçülse de **çürümez**.

### ⛔ Ayak 2 — tarifi yazılmamış md5 bir KAPI DEĞİLDİR

İki taraf **aynı dosya** için iki farklı digest üretti (`f88cfa04…` ↔ `cb4322df…`). Fark
kodda değil **hashleme adımındaydı**: tam **bir bayt** (sondaki `\n`). Üç varyant (CRLF
korunmuş / `\r` atılmış / sondaki boşluk kırpılmış) **aynı** değeri verdiği için farkın
içerikte olmadığı elenerek kanıtlandı.

⇒ Digest'in **tanımı** yazılmadıkça digest bir kapı değildir. Yazılan tarif:

```bash
tr -d '\r' < <DOSYA> | grep -v -E '^[[:space:]]*\*|^[[:space:]]*"|^[[:space:]]*$' | md5sum
```
Tanım: UTF-8 oku · `\r` at · `strip()`'i boş **veya** `*`/`"` ile başlayan satırları düşür ·
`\n` ile birleştir · **sonda tek `\n` bırak** · md5. (`[[:space:]]` bilerek — `\s` bir GNU
uzantısıdır, taşınmaz.)

⚠ Aynı sınıfın ölçülmüş üçüncü yüzü `Q223`: readback md5'inin **biçimi obje tipine
bağlıdır** (`.clas` ham · `.ccau` normalize · `.func` gövde-md5) ⇒ "md5 tutmadı" demeden
önce **hangi md5** olduğu sorulur.

⭐ **Dördüncü yüz — aynı dosyanın AYNI ANDA üç doğru md5'i olabilir** (aynı gün ölçüldü):
`.gitattributes`'ta `* text=auto` varsa çalışma kopyası **CRLF**, git blob'u **LF** olur ⇒
`md5(disk)` `7dc7af20…` · `md5(git show)` `ed02e372…` · kanonik kod-md5 `f88cfa04…`. Üçü de
doğru, hiçbiri kusur değil. ⛔ Bu yüzden bir md5 aktarırken **hangi baytları** hashlediğini
söylemek zorunludur; söylemezsen karşı taraf "içerik farklı" sanır. Ölçüm: `tr -d '\r'`
uygulanınca iki taraf eşitlendi, satır-bazlı `diff` **boş** döndü — yani fark **içerikte değil
kodlamadaydı**. Bu, canlı sisteme push readback'inde de aynen geçerlidir.

**Why:** İki ayak da aynı bedeli üretti — **doğru iddia, çürük kanıt**. Kanıt çürüyünce
tartışma iddianın kendisine kayıyor ve tur yiyor: satır çapası üç turda üç kez düzeltildi,
md5 uyuşmazlığı bir "kusur mu?" turu açtı (kusur değildi). Bu, ölçüm kültürünün en sinsi
sızıntısı: ölçüm **yapıldı**, ama **aktarılamadı**.

**How to apply:**
1. **Dosya donana kadar satır numarası verme.** Donmuş = git'te izlenir + o turda
   değişmeyecek. Değilse **komut** ver ya da **içerik alıntısı** ver.
2. ⭐ Bir kayıt/doküman ile kaynak **karşılıklı** atıf yapıyorsa, birinde yapılan taşıma
   **karşı yöndeki atıfı da** bozar — taşıdıktan sonra ters yönü de düzelt (bugün
   *"gerekçe kaynakta mayın olarak durur"* cümlesi taşımadan sonra yanlış yönü gösteriyordu).
3. **Hash'i kapı yapacaksan tarifini AYNI yere yaz** — hangi baytlar dahil, hangi satırlar
   düşüyor, satır sonu ne, sondaki `\n` var mı. Tarifsiz digest'i kabul etme, üretme.
4. İki digest tutmuyorsa **önce hashleme adımını ele**, içeriği suçlama: aynı dosyayı
   birkaç normalizasyon varyantıyla hashle — hepsi aynıysa fark **tarifte**dir.
5. Bu, kapıların da tasarım kuralıdır ([[feedback_kural-gate-lenmeli-yoksa-anlamsiz]]):
   üçüncü tarafça üretilemeyen bir ölçüt, **gate değil temennidir**.

Son-doğrulama: 2026-09-02 · prior-art arandı: [[feedback_kapi-kosarken-dosya-donar-md5-teyidi]]
(md5'i KİM ölçer — dondurma protokolü) ve [[feedback_kanit-tazeligi-indeks-ve-zaman-sirasi]]
(kanıt tazeliği) VAR; **kanıtın BİÇİMİ/yeniden-üretilebilirliği** kaydı YOKTU.
Applies-to: her proje · her kayıt/doküman/kapı; özellikle aktif düzenlenen kaynaklara atıf.

İlgili: [[feedback_iddia-yazma-aninda-kanit-kurallari]] · [[feedback_exit0-degil-cikti-kaniti]] ·
[[feedback_kapsam-niteleyicisini-dusurme]] · [[feedback_resolved-tooling-bugs]]
