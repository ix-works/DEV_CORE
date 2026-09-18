---
name: feedback_gecmis-temizligi-refs-pull-tuzagi
description: "Git geçmişi temizlenecekse: force-push YETMEZ (refs/pull kalır) + temizlikten SONRA PR açma"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1ddc4cef-62b9-4ee4-ba6a-a9a998ccdc69
---

**Bir repo public'e açılacak / git geçmişi yeniden yazılacaksa iki kural, sırayla:**

1. **`force-push` YETMEZ.** GitHub'ın `refs/pull/*` ref'leri force-push'tan etkilenmez ve eski
   (kirli) commit'leri "reachable" tutar. Boş bir dizinden `git fetch origin 'refs/pull/*/head:...'`
   ile herkes çekebilir — `main` tertemiz görünürken. Tek çözüm: **eski repoyu arşivle → aynı adla
   YENİ repo yarat → temiz geçmişi oraya push et** (yeni repoda pull-ref yoktur).

2. **Temizlikten SONRA PR AÇMA.** Yeni repoda bir PR açıp merge etmek, anında yeni bir kirli
   `refs/pull/N/head` yaratır ve tüm işi boşa çıkarır. Doğru sıra:
   `temizle → yeniden yarat → public yap → SONRA PR aç.`

**Why:** 2026-07-09'da bu iki kuralı da öğrendik, ikincisini `PROJECT_BOOTSTRAP.md`'ye yazdım —
sonra kendim ihlal ettim: temizlik + force-push sonrası PR açıp merge ettim, `refs/pull/1/head`
54 kirli commit'i public'e açtı. Aynı repoyu **iki kez** yeniden yaratmak zorunda kaldık.
Yazılı uyarı beni durdurmadı. (Kullanıcı: "tekrar yapmayacağın garanti mi?")

**How to apply:** Geçmiş yeniden yazma işi görünce ÖNCE bu sırayı yaz, sonra başla. Public yapmadan
önce **boş bir dizinden** `refs/pull/*` çekip hassas iz tara — `main` temiz olması yeterli değil.
Tarama listeni kendi filter-repo kurallarından TÜRETME (2026-07-09: `<PROJE>` yazdım, adın kısa kökünü
aramadım → müşteri adı public'te kaldı). Bağımsız tara: `git rev-list --all | git grep -lI <desen> <commit>`
(pickaxe `-S` yeniden yazılmış geçmişte yanıltıcıdır).

⛔ **Tarama reçetesinin kendi tuzağı (2026-09-18, ölçüldü):** blocklist desenleri Python regex'idir
(`(?:…)`, `(?<!…)` lookbehind). `git grep -E` (POSIX ERE) bunları **rc 128 ile reddeder**, stdout BOŞ
kalır ⇒ yalnız stdout'a bakan döngü *"396 commit'te 0 iz"* dedi; gerçek **311/396**. Doğrusu:
`git grep -P` (PCRE) + **her çağrıda `returncode ∉ {0,1}` = HATA say** + bilinen izli bir commit'le
**kontrol grubu** (`-P` ve bağımsız Python taraması aynı sayıyı verdi: 8 dosya).

İlgili: [[feedback_dogrula-once-flag]] [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]] · [[feedback_timeout-rg-shim-sessiz-sifir]] (aynı sınıf: araç hatası = sessiz sıfır)
