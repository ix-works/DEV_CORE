---
name: feedback_deploy-ui-yarida-kesilince-bsp-yine-yaratilmis-olabilir
description: "deploy_ui yarıda durdurulsa da BSP (WAPA) + SICF düğümleri SAP'de yaratılmış ve göreve yazılmış olabilir — \"deploy olmadı\" varsayma; TADIR/E071 ile ölç, sonra baştan deploy + --verify-only"
metadata:
  node_type: memory
  type: feedback
  seed: evet
  originSessionId: e290e579-a7df-4674-adf5-40cace6f66e5
---

`core/scripts/deploy_ui.py` koşarken durdurulursa (TaskStop / ESC) SAP tarafında iz kalabilir: BSP uygulaması (`R3TR WAPA <BSP>`) ve SICF düğümleri yaratılmış, nesne transport görevine yazılmış olabilir — Component-preload canlıda olmasa bile.

**Why:** Vaka 31.10.2026 (bir Fiori rapor paketinin ilk deploy'u): BSP adı kararı için deploy durduruldu; TADIR'de `WAPA <BSP>` + 2 SICF kaydı, E071'de görev kaydı ölçüldü. "Yarıda kaldı = hiçbir şey yazılmadı" varsayımı yanlış olurdu; ayrıca yarım BSP bayat/eksik içerik sunabilir.

**How to apply:** Kesilen deploy'dan sonra: ① TADIR (`OBJ_NAME = <BSP>`) + E071 ile ne yaratıldığını ölç ② BSP adı değişmeyecekse aynı komutla baştan deploy ③ `deploy_ui.py --verify-only` + statik varlık varsa `verify_ui_static_assets.py`. BSP adı değişecekse eski BSP artık nesne olur — silme kararı kullanıcıya sorulur.

prior-art: yok (memory + core/playbook "deploy … yarıda/kesil" araması 0)
Son-doğrulama: 2026-10-31
Applies-to: freestyle UI5 deploy (deploy_ui.py), s4_private
