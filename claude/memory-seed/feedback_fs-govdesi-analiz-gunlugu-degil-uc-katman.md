---
name: feedback_fs-govdesi-analiz-gunlugu-degil-uc-katman
description: "FS/TS/KD gövdesi = kapanmış hedef durum; karar günlüğü (11-A/11-B/EK-B) ve analiz süreci AYRI katman — sürüm etiketi/gate-ID/'canlı ölçüldü'/kullanıcı alıntısı gövdeye yazılmaz (İLKE-2b)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: dcd53b29-1ed9-4bea-8e6c-e6e325631633
---

**Kullanıcı düzeltmesi (2026-08-17, <PAKET-A> FS v1.9):** "FS not-loglama gibi olmuş; yapılacak geliştirmeyi net tarif etmesi gereken bir döküman" — örnek: *"FKARA=F2 (siparişe bağlı, yalnız referans alanı); RESEARCH-02 §2 bu iki alanı ters okumuştu → FS'teki 'Fatura F2' ifadeleri <BELGE-TURU-A> olarak düzeltildi; TVAK-LFARV DEV'de ölçüldü <BELGE-TURU-B> (ilk turda alan adı yanlış LFART yazılmıştı, 400 dönmüştü)"* — FS'te olması gereken tek cümle: **"Fatura tipi <BELGE-TURU-A> (teslimata bağlı), teslimat tipi <BELGE-TURU-B>."**

**Why:** 9 sürüm boyunca doc-gate'e "kapatıldı" gösterebilmek için her düzeltme gövdeye `(doc-gate v1.5 H-C netleşme)`, `(v1.9, EK-A N-5)`, "canlı ölçüldü — ilk turda…" diye damgalandı; ölçüm: gövde satırlarının ~%25'i işaretli, §1.1 %9,3 (satır 3 KB), kapanmış 11-B %11,5 → belge onaya sunulamadı. Kök: (1) izlenebilirlik doğru amaç, **yeri yanlış**; (2) delta yazımı ("bu turda şu değişti") — [[feedback_tek-soru-ve-bagimsiz-dokuman]] ile aynı sınıf; (3) standartta kural yoktu → gate yoktu ([[feedback_kural-gate-lenmeli-yoksa-anlamsiz]]); (4) "iddia anında kanıt" çalışma disiplinimiz kullanıcıya giden belgeye sızdı. Dünya pratiği (ASAP issues DB, decision log, BABOK rationale, ISO 29148 Rationale/Source) 3 katmanı ayrı tutar (rapor: RESEARCH-FS-STANDART-DUNYA, 11 kaynak).

**How to apply:**
- Kanonik: `core/standards/04-documentation-fs-ts.md` **§2.0 İLKE-2b** (üç katman) + §2.2 (§1.1 kısa, §4.1 Kaynak/Gerekçe kolonu, 11-B kapanan karar birikmez) + §2.3; doc-checklist **DOC-FS-05/06/07**; gate `check_fs_no_analysis_log.py` (warn-first; post_validate `doc-fs` sınıfı FS/TS/KD/EK düzenlemesinde OKU-işaretçisi + özet basar); yeniden yazımda `scripts/doc_equivalence_check.py` (kimlik/mockup/değer/cümle denkliği — **veri kaybı = 0**, gövdeden çıkan her şey EK-B'ye TAŞINIR, silinmez).
- Gövde cümlesi testi: "bugün geçerli hâli mi anlatıyor, nasıl bulunduğunu mu?" İkincisiyse → EK-B / RESEARCH. Kısa atıf serbest: `(karar R-22)`.
- Doc-gate kapatırken bulguyu gövdeye "H-C netleşme" diye DAMGALAMA — gövdeyi düzelt, izi EK-B/gate raporuna yaz.
- Aynı kural FS eklerine (EK-A veri yürüyüşü) ve TS/KD'ye uygulanır; başlık büyük/küçük harf standardı ile birlikte (`04 §2.3`).
İlgili: [[feedback_fs-ts-iki-zihniyet-disiplini]] · [[feedback_review-bulgulari-bug-checkliste-routing]] · [[feedback_done-tam-kapsam-dogrula]]
