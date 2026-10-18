---
name: feedback_core-index-dala-bagli
description: "CORE-INDEX proje reposunda ama içeriği `core/` junction'ının O AN hangi DALDA durduğuna bağlıdır. Core'da dal değiştirince indeks yeniden üretimi doküman sayısını DÜŞÜREBİLİR — 'doküman silinmiş' gibi görünür, oysa yalnız o dalda yok. Küçülen indeksi sorgusuz commit'leme."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a4cd7d32-a718-41a3-9b19-f70f390d9ff7
---

`governance/CORE-INDEX.md` **proje reposunda** durur ama `build_core_index.py` onu `core/`
junction'ının **çalışma ağacındaki** dosyalarından üretir. `core/` ayrı bir repodur
(`<CORE-KOKU>`) ve **kendi dalları** vardır ⇒ **indeksin içeriği, core'un o an hangi dalda
durduğuna bağlıdır.**

**Yaşanan vaka (2026-08-09):** Core'a bir playbook bölümü eklendi → `check_core_index_fresh`
**FAIL** verdi (doğru davranış). İndeks yeniden üretildi → doküman sayısı **87 → 86** düştü,
`playbook/` 48 → 47. İlk okuyuşta *"bir doküman silinmiş"* gibi görünüyor.
Gerçek sebep: lider core'u kendi PR dalına almıştı (`origin/main`'den açılmış bir fix dalı);
önceki indeks ise **başka bir dalda** (henüz merge edilmemiş bir doküman içeren) üretilmişti.
Core dokunulmadan önceki dalına geri alınınca sayı **87'ye döndü** ve fark yalnız üretim-zaman
damgası kaldı (o satır tazelik kıyasında zaten yok sayılıyor).

**Why:** Üretilmiş bir indeks, **üretildiği anın checkout durumunu** dondurur. O checkout'u
başka bir sebeple (PR dalı, worktree, deneme) değiştirmiş olabilirsin; indeks bunu "içerik
değişti" diye rapor eder. Küçülen bir indeksi sorgusuz commit'lemek, sonraki oturuma
*"bu doküman silindi"* diye **yanlış bir tarih** yazar — ve indeksin varlık sebebi (ajan doğru
yolu bulsun) tersine döner: yanlış yol verir.

**How to apply — indeks FAIL verince sıra:**
1. **Önce `git -C <CORE> branch --show-current`** — core hangi dalda? Beklediğin dal mı?
2. Yeniden üret, sonra **farkı OKU**: sayı **düştüyse** DUR. Düşüş neredeyse her zaman dal
   artefaktıdır, gerçek silme değil.
3. İndeks, **paylaşılan gerçeği** temsil eden daldan üretilmeli (`main` ya da ekibin çalışma
   dalı) — kişisel PR dalından DEĞİL.
4. Core'daki işini PR'a taşıdıktan sonra **junction'ı eski dalına geri al**; feature dalında
   gereğinden uzun oturma.
5. Fark yalnız damga satırıysa: `core-commit:` **değiştiyse** (core `main`'de — çekirdek
   güncellemesi) **commit ET**. Proje CI'ındaki `build_core_index --ci-check` tazeliği ancak
   damgadaki core-commit klonlanan `main` HEAD'ine eşitken ölçer; commit'siz damga C-IDX-01'i
   `SKIPPED` bırakır ve proje ağacını kirli tutar (sonraki güncellemede "kirli → DUR").
   `core-commit:` aynı, yalnız `uretim:` zamanı farklıysa zaten fark oluşmaz (dosya yeniden
   yazılmaz). *(2026-10-18 düzeltmesi — eski hâli "commit etme" diyordu.)*

⚠ Aynı sınıf worktree'de de geçerli: `_worktrees/` altında core'un ikinci bir çalışma ağacı
varsa, hangisinin junction'a bağlı olduğunu **varsayma, ölç**.

İlişkili: [[feedback_sonucu-olc-uygulamayi-degil]] (ilk görüntüye değil sonuca bak) ·
[[feedback_dogrulama-sezgileri-dort-kural]] (bulunamadı ≠ yok).

Son-doğrulama: 2026-10-18 (5. madde düzeltildi — CI `--ci-check` damgayı girdi olarak kullanır; ilk vaka 2026-08-09)
Applies-to: `core/` junction'lı TÜM projeler · CORE-INDEX / üretilmiş her indeks-benzeri artefakt
