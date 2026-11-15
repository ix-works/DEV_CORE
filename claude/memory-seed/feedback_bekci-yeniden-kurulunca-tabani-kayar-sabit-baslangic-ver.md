---
name: feedback_bekci-yeniden-kurulunca-tabani-kayar-sabit-baslangic-ver
description: "agent_stall_watch'ı Monitor'la her 30 dk yeniden kurarken taban (simdi - gecmis-dk) ileri kayar; tabandan ÖNCE takılan ajan hiç görünmez — sessizlik \"takılan yok\" değildir. Sabit --baslangic ver, BAKMADIGI satırını süzme."
metadata:
  node_type: memory
  type: feedback
  seed: evet
---

`agent_stall_watch.py` yalnız TABANDAN SONRA başlamış araç çağrılarını sayar (taban = `--baslangic`, verilmezse `simdi - --gecmis-dk`). Monitor her 30 dk'da sona erip yeniden kurulduğunda taban her seferinde ileri kayar. Bu yüzden bir önceki pencerede takılmış ajan sonraki pencerede GÖRÜNMEZ. Araç bunu her koşumda `[bekci] BAKMADIGI: taban ONCESI dogmus arac cagrilari…` satırıyla bildirir.

**Vaka (2026-11-08 gece):** dört ajan (iki build ajanı ve iki bug-gate) 4–6,5 saat boyunca tek bir Bash çağrısında bekledi. Çağrılar `rm -rf …` ya da `cp -r …` içeriyordu ve makinede bunlara ait bir süreç yoktu. Bekçi 6'dan fazla kez "0 olay" ile doldu ve iki `--tek-atim` kontrolü `asili=0` dedi. Lider bunu "takılan yok" diye okudu. Oysa lider `grep -v "KAPSAM|IMZALAR|BAKMADIGI"` süzgeciyle aracın KAPSAM BEYANI'nı kendisi gizlemişti. Fark ancak transkript mtime'larına bakılınca görüldü.

**Why:** Kapsam beyanına en çok sıfır bulgu anında ihtiyaç vardır (core §7 KAPSAM BEYANI). Beyanı süzmek, aracın neye bakmadığını söyleyen tek sinyali kör eder. "Kontrol grubu" da aynı kör pencereden koşulduğu için gerçek bir kontrol değildi.

**How to apply:**
- Uzun gece izlemesinde Monitor'u SABİT tabanla kur: `--baslangic <ilk kurulum ISO>` ver ve her yeniden kurulumda aynı değeri kullan.
- `KAPSAM`/`BAKMADIGI` satırlarını süzme. Yalnız `IMZALAR` gürültüsü süzülebilir.
- Belirli aralıklarla (ör. her 1–2 saatte bir) ajan transkriptlerinin son yazım zamanına bak (`find <seans>/subagents -name '*.jsonl' -printf '%TT %p\n'`). Saatlerdir yazmayan bir ajan için durumu sorgula.
- Gece onay verecek kimse yoktur. Onay penceresi açabilecek komutları (rm/rmdir/cp -r/kill) brifte baştan yasakla. Kural sonradan eklenirse önceden spawn edilmiş ajanlara ulaşmaz: mesaj yalnız ajanın bir sonraki araç turunda teslim edilir ve takılı ajanın bir sonraki turu yoktur.

Son-doğrulama: 2026-11-08 · Applies-to: Monitor + agent_stall_watch ile çok-ajanlı uzun koşumlar
prior-art: bulundu — core/scripts/agent_stall_watch.py ("taban ONCESI asilmis ajan yakalanmaz — bilincli tasarim"), core/governance/agent-teams-operating-model.md (taban filtresi gerekçesi). Bu dersin yeni getirdiği: yeniden kurulumda tabanın kayması ve kapsam beyanının süzülmesi bir kullanım hatasıdır.
İlgili: [[feedback_agent-stall-watchdog-mekanizmasi]] · [[feedback_alt-ajan-spawn-edince-bekci-baslat-onay-beklemesin]]
