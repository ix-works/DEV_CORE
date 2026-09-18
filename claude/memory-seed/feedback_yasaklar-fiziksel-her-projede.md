---
name: feedback_yasaklar-fiziksel-her-projede
description: "KESİN YASAKLAR her projede FİZİKSEL kural olmalı, link/import'a bağlı değil"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 21e22493-385d-425d-a592-a90b3c167b75
---

Kullanıcı (2026-07-08): "Kesin yasaklar (tahmin etme/kanıtlı hareket et, standart objeye
dokunma vs.) her projenin altında özellikle KURAL olarak set edilmeli. Link/referans ile
taşımak riskli — her projede mutlaka uygulanacak hale getir."

**Why:** Canlı-çekirdek mimarisinde yasaklar yalnızca proje CLAUDE.md'sindeki
`@core/CLAUDE.core.md` import'uyla geliyordu → junction kırılırsa TALIMAT-seviyesi yasaklar
sessizce context'ten kaybolurdu (araç-seviyesi SAP-yazma zaten shim+MCP korumalı; boşluk
talimat-seviyesindeydi). Tek indirekt referansa asılı anayasa = tek kırılma noktası.

**How to apply:** Çözüm kuruldu — ADR 0021 (fiziksel damga + drift-guard). Yasaklar HER
projenin kök CLAUDE.md'sine FİZİKSEL damgalı (junction'sız doğrudan yüklenir). Tek kanonik:
`core/claude/kesin-yasaklar.canonical.md`. `init_project` damgalar · `check_kesin_yasaklar`
guard (run_all_validators HARD + session_start + pre_tool_guard SAP-yazma) drift'i BLOCKER
yapar · `sync_yasaklar.py --root <PROJELER-KOKU>` kanonik değişince yeniden damgalar. **Genel ders:
güvenlik-kritik kural link/import'a değil, guard-zorlamalı fiziksel artefakta bağlanır.**
Yeni proje açılışında damga otomatik; elle CLAUDE.md taşınırsa sync_yasaklar ZORUNLU.
[[project_coklu-proje-dev-core-mimarisi]] · [[feedback_kural-gate-lenmeli-yoksa-anlamsiz]]
