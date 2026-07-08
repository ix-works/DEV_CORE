---
name: feedback_arastir-once-patinaj-uretim-gorev
description: "Tanıdık olmayan üretim/araç görevinde (ör. resimli PDF) deneme-yanılma yerine ÖNCE kanıtlı yöntemi araştır; çıktıyı (resim sayısı vb.) doğrulamadan 'bitti' deme"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8c1257a6-fbd9-48f4-9ef0-5040be6f1540
---

ZSD001 KD kılavuzunu markdown→PDF'e çevirirken yaşanan patinaj (2026-06-11). Kullanıcı: **"patinaj yapıyon önce araştır bu resimli pdf oluşturma konusunu"**.

**Ders:** Tanıdık olmayan bir üretim/tooling görevinde (resimli/şık PDF, yeni format dönüşümü vb.) **deneme-yanılma ile yama yapma** — önce **kanıtlı yöntemi web'de araştır** (T10 patinaj disiplini), sonra tek seferde temiz uygula.

**Why:** Ardışık tahmin (md_in_html ham `<figure>` → bozuldu; sonra kod-fence içi resim → parse olmadı) pahalı + güven sarsar. Araştırma 2 aramada netleşti: **md→HTML→Chromium/Playwright `page.pdf`** (veya WeasyPrint) kanıtlı yöntem; sorun **araçta değil markdown KAYNAĞINDAYDI** (placeholder'lar ``` kod-bloğu içindeydi → markdown `![](..)` orada parse etmez; çözüm fence BLOĞUNUN tamamını resimle değiştir).

**How to apply:**
- Yeni üretim görevi → önce "X için kanıtlı yöntem/araç ne" araştır, sonra kod.
- Çıktıyı **say/doğrula**: PDF'i "üretildi" demeden önce `<img>` sayısı = beklenen mi (9 bekleniyordu, 1 çıkmıştı — kullanıcı yakaladı). [[feedback_done-tam-kapsam-dogrula]] ile aynı: "uploaded/oluştu" mesajına güvenme, içeriği say.
- Üreteç: `scripts/build_kd_pdf.py` (md→HTML+CSS, fence-blok→resim, figure/caption, PIL crop) + `page.pdf` HTTP üzerinden (file:// bloklu).

**TAM REÇETE (tekrar kullanım):** `playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md` — mock ekran çekimi (zengin-mock, TR locale, collapse iki-durum, JS ile pasif-buton aç, Devral ile doldur) + PDF kurulumu + doğrulama + patinaj-tuzakları tablosu. Yeni KD/FS/TS PDF'i ÖNCE bu dosyayı oku.
