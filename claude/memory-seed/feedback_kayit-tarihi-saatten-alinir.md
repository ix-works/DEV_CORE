---
name: feedback_kayit-tarihi-saatten-alinir
description: "Kayda yazılan tarih ÇIKARIMLA yazılmaz — `date` / `git log` çıktısından alınır; bir oturumda 102 geçişte ertesi günün tarihi yazıldı"
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

Bir kayda (karar günlüğü, RESUME, SESSION_NOTES, TS notu vb.) tarih yazarken tarihi **o anda ölç**: `date +%F` ya da `git log -1 --format=%ad --date=short`. Tarihi bağlamdaki "bugün" algısından, özetten ya da önceki kaydın tarihinden **türetme**.

**Why:** 2026-11-08'de bir oturumda kararlar, ölçümler ve notlar **ertesi günün tarihiyle** (11-09) yazıldı; oysa bütün commit'ler 2026-11-08 tarihliydi. Yanlış tarih 15 dosyada 102 geçişe yayıldı. Farkı bug-gate "tarih farkı" diye işaretledi, ama lider bunu ancak kullanıcıya rapor yazarken gördü. Kök neden: özetteki tarih algısı sorgulanmadan kopyalandı ve her yeni kayıt bir öncekini örnek aldı.
Ayrıca ilk sayım `grep -c` ile yapıldı. `grep -c` geçişleri değil **satırları** sayar: 73 satır vardı ama 102 geçiş. Bir sayı bildirirken aracın NEYİ saydığını yaz.

**How to apply:** Kayda tarih koymadan önce `date +%F` çalıştır. Compact sonrasındaki ilk kayıtta tarihi mutlaka yeniden ölç. Toplu sayımda `grep -o … | wc -l` (geçiş sayar) ile `grep -c` (satır sayar) arasındaki farkı göz önünde tut.

Son-doğrulama: 2026-11-08
Applies-to: tüm projeler, kayıt/günlük yazımı
