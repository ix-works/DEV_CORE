---
name: feedback_klasik-alv-quickinfo-char30-symsgv-char50
description: "Klasik GUI uzunluk sınırları: ALV toolbar STB_BUTTON-QUICKINFO = ICONQUICK CHAR30 (uzun ipucu kesilir) · MESSAGE … WITH &1 = SYMSGV CHAR50 (uzun dosya yolu kesilir)"
metadata:
  type: feedback
  seed: evet
---

- `cl_gui_alv_grid` toolbar düğmesi `STB_BUTTON-QUICKINFO` tipi `ICONQUICK` = **CHAR30** ⇒ 30'u aşan ipucu sessizce kesilir; ipuçlarını ≤30 karaktere yaz (ör. toplu seçim düğmeleri: "Görünen tüm satırları seç" vb.).
- `MESSAGE sNNN(cls) WITH lv_file` → `SY-MSGV1` = `SYMSGV` **CHAR50** ⇒ uzun yerel dosya yolu &1'de kesilir (ör. "Şablon kaydedilemedi: &1"). Tam yol gerekiyorsa yolu böl (&1..&4) ya da mesajda yalnız dosya adını göster.

**How to apply:** klasik ALV/mesaj metni tasarlarken DDIC uzunluğunu ölç; syntax/ATC uyarmaz.
Son-doğrulama: 2026-10-05 · Applies-to: klasik dialog (ecc/s4_private)
