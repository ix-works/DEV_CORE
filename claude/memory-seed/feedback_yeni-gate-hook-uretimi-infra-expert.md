---
name: feedback_yeni-gate-hook-uretimi-infra-expert
description: "Yeni gate/hook-dalı/validator/paylaşılan araç ÜRETİMİ de infra-expert işidir (fix'e özgü değil) — lider yalnız EXPRESS-mekanik + tasarım kararı + diff-review + commit; 'kablolamayı garanti et' baskısı bunu kaldırmaz"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: dcd53b29-1ed9-4bea-8e6c-e6e325631633
---

**Kullanıcı sorusu (2026-08-17):** "infra'nın yapması gereken bir şeyse neden sen yaptın, infra konusunu hatırlamadın?" — bağlam: FS 3-katman kuralı için lider (ben) yeni validator (`check_fs_no_analysis_log`), `post_validate` doc-fs dalı ve `doc_equivalence_check` aracını **kendim** üretip commit'ledim; ilk sürüm `\n` kaçış hatasıyla hook'u 4 test boyunca kırdı.

**Why (kök neden, üç parça):** (1) Kural metni "İnfra-**Fix** prosedürü" adıyla hataya kuruluydu; yeni gate/hook üretimini "T3/T11 onboarding = lider işi" diye sınıfladım — ruhu (paylaşılan infra ÜRETİMİ = taze-spawn infra-expert, karar = lider; [[feedback_arac-kod-fix-lider-isi]] revizyonu 2026-08-01) açıktı ama metinde yalnız fix vardı. (2) "Tetiklendiğinden emin ol" talimatıyla hız baskısı → en kısa yol. (3) Yazma anında hiçbir nudge "EXPRESS mi kuyruk mu?" diye sormuyordu (PATTERN #30: kural vardı, konumu yoktu); JIT-recall howto'yu yalnız "hook bozuk/validator hatası" prompt'larında getiriyor.

**How to apply:**
- Paylaşılan infra'ya (`core/scripts/{hooks,validators}/`, `core/scripts/*.py`, proje `scripts/validators-local/`) yazma niyeti doğduğunda ÖNCE sor: **EXPRESS 4 şart** (mekanik · tek-nokta blast-radius · fixture ≤1 dk yeşil · gevşetme yok) sağlanıyor mu? Değilse → `governance/infra-findings.md` kuyruğu + **taze infra-expert** (worktree, F1-F5, üç-bağlam test, kalıcı fixture, gevşetme bayrağı, yayılım notu); lider brifingi yazar, diff'i inceler, testleri bağımsız koşar, commit eder.
- Bu **yeni özellik** için de geçerlidir (bug değil): kanonik `core/playbook/howto-infra-fix-proseduru.md` "KİM NE YAPAR" tablosuna satır eklendi (2026-08-17); infra-expert tanımı kapsamı genişletildi. Yazma-anı nudge'ı infra-expert'e yaptırıldı (kendim yazmadım — aynı hatayı tekrarlamamak için).
- Sapma olduysa: kabul et, kuyruğa kaydet, üretileni **merge'den önce** infra-expert F1-F5 turuna ver (2026-08-17'de yapıldı: `infra-fs-docstd`).
İlgili: [[feedback_arac-kod-fix-lider-isi]] · [[feedback_adt-infra-degisikligi-once-uyar-onay]] · [[feedback_hook-bakim-protokolu-t11]] · [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]]
