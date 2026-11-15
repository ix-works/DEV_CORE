---
name: feedback_kapi-raporu-kaydi-verify-report-tuzaklari
description: "Bug-gate raporunu dosyaya kaydedip checklist_check --verify-report koşarken tuzaklar: rapor metni alt-ajan transkriptinde, --repo zorunlu/--diff+--files birlikte olmaz, gruplu hüküm satırı eşlenmez ('birleşik satır' kategorisi), repo dışı --files glob'a girmez"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: b1b58519-2c91-4830-aeab-6f0c875a0510
---

Lider bug-gate raporunu kaydedip `checklist_check --verify-report` koşarken (bir build turu, 30.10.2026) üç kez takıldı:

1. **Rapor metninin tamamı ana oturum transkriptinde olmayabilir.** Handback mesajı ana `<sid>.jsonl`'a geç düşer ya da hiç düşmez. Tam metin `~/.claude/projects/<proje>/<sid>/subagents/agent-<id>.jsonl` dosyasında durur. Ana transkriptte arayınca kendi komutların eşleşir; 5-20 satırlık yanlış parça kaydedilir ve verify "satır yok: 76" der.
2. **`checklist_check` `--repo .` ister. `--diff` ile `--files` birlikte verilemez.** Biri yoksa "KULLANIM HATASI" alırsın.
3. **Gruplu hüküm satırı hiçbir maddeye eşlenmez.** "| BE-01,03,10a | A | PASS |", `BE-10a/b`, `BE-22..25`, `BE-10a / BE-10b` gibi satırlar 2026-11-15'ten beri **"birleşik satır"** kategorisine düşer (önceden "satır yok" diye düşüyordu, nedeni yazmıyordu); exit 1 aynen kalır, çünkü tek hükmü birden çok maddeye yaymak sahte PASS olurdu. Brifte açıkça iste: "her madde için ayrı satır". Gelirse içeriğe dokunmadan satırları madde başına aç ve bunu başlıkta not et.

4. **`--files` ile REPO DIŞI dosya verirsen klasörlü glob hiç eşleşmez** (2026-11-02, #381): araç `relative_to(repo)` başarısız olunca `rel = p.name` (yalnız dosya adı) kullanır ⇒ `**/webapp/**/*.js` gibi her desen sessizce düşer, KAPSAM BEYANI yine "globa girmeyen dosya: yok" der. Ölçüldü: aynı controller worktree içinde 41 FE maddesi, scratchpad'de 3. Bir map glob'unun ulaşımını ölçerken dosyayı repo İÇİNDE geçici oluştur, sonra sil. Bug-expert de aynı tuzağa düşüp "FE-53 controller'a ulaşmıyor" demişti.

**Why:** Her seferinde kayıt 2-3 deneme sürdü. Yanlış parça kaydı, eksik raporu "doğrulanmış" sanma riskini doğurur.
**How to apply:** Kapı raporunu kaydetmeden önce alt-ajan jsonl'ından en uzun "VERDICT + hüküm tablosu" metnini al. Komutu `--repo . --files …` (ya da `--diff`) ile koş. Bug-expert brifine "hüküm tablosu madde başına tek satır" yaz.

Son-doğrulama: 2026-11-15 (madde 3 yeni kategoriye hizalandı) · Applies-to: tüm projeler, lider bug-gate kaydı + map glob ulaşım ölçümü
prior-art: yok (kapı-raporu kaydı için; [[feedback_kapi-kosarken-dosya-donar-md5-teyidi]] komşu)
