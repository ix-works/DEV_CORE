# KALDIRILMIŞ KONTROLLER SÖZLÜĞÜ (T4.4 — sahte-koruma süpürmesinin beslemesi)

> **Amaç:** Bir gate/guard/validator/anahtar KALDIRILDIĞINDA adı buraya yazılır (kaldırma-DoD'si,
> PR şablonu adım-2). İçerik-sağlık radarı her turda bu listedeki adlarla core+proje grep'i yapar;
> "hâlâ aktif" anlatan her metin = bulgu. (R9/R10 vakası: kaldırılan kural 16 gün 10 dokümanda
> "aktif" yazdı — bu dosya o sınıfın kalıcı panzehiri.)

| Ad / anahtar | Kaldırılış | Neden | Bilinen kalıntı-notu |
|---|---|---|---|
| `R9` (özyinelemeli-silme bloğu) | 2026-07-10 | fiil-listesi hedef sormuyordu; araç değiştirtip sonucu değiştirmiyordu | tarihçe-dili serbest |
| `R10` / freeze-guard | 2026-07-10 | aynı sınıf; 6 yoldan sızıyordu | 2026-07-31 D3'te 3 aktif-anlatım düzeltildi |
| `frozen_readonly_paths` (project.yaml) | 2026-07-10 | R10 ile birlikte; hiçbir guard okumuyor | MAINTENANCE "ÖLÜ ANAHTAR" satırı kanonik |
| sızıntı-commit runtime kuralı | 2026-07-10 | katman zaten pre-commit+CI'da | — |
| applies_to runtime kuralı | 2026-07-10 | validator katmanı taşıyor | — |
| `adt_activate_check.py` `adt_prog_check.py` `adt_syntax_check.py`(script) `_verify_sqlview.py` | 2026-07-31 T0.4 | çalıştırılamaz fosiller → attic | `attic/validators-fosil/README` |
| `_audit_state.py` `_check_old_style.py` (proje) | 2026-07-31 T0.5 | eski-kök hardcoded, hiç koşamazlardı | — |
| pre-commit adım-2 (`build_core_index --check`) | 2026-07-31 T1.11 | aynı commit'te run_all C-IDX-01 aynı işi yapıyor | — |
| `REPO_WIDE_SCANNERS` üyeliği: `check_amdp_comment_apostrophe` | 2026-07-31 T1.12 | tek-artifact modu geldi; repo-geneli run_all+CI'da | küme BOŞ ama mekanizma durur |
| AGENTS.md (L1c katmanı) | 2026-08-01 D1 | hiç yüklenmiyordu; tekil içerik taşındı | SUPERSEDED band; tarihsel atıflar radar süpürmesinde |
| session_start 4-satır yasak-özeti + SKILL TIER-0 kopyası | 2026-08-01 D6 | 9→4 kopya azaltma; damga kanonik | atıf satırları kaldı (bilinçli) |
| davranis-manifesti yuzeyi: `.claude/settings.local.json` | 2026-08-01 bug-avi AV-20 | Claude Code dosyayi HER izin onayinda kendisi yaziyor -> manifest-diff kalici alarm veriyordu (session_start "cikti'ya GUVENME" + config_change_guard exit 2); surekli calan alarm gercek tamper'i ayirt edilemez kiliyordu | `settings.json` YUZEYDE KALIR (asil davranis yuzeyi); kaybedilen kapsam: o dosyaya ELLE eklenen izin artik alarm uretmez (bilincli takas, kullanici onayli) |
| `scripts/create_package.py` | 2026-08-01 bug-avi E2 | Tek isi SAP paketi (DEVC) yaratmakti = ADR 0005-C'nin YASAKLADIGI fiil; ustelik `check_package.py` kullaniciyi ona YONLENDIRIYORDU (yasagi anlatan ADR ve AGENTS.md ise onu 'yasak ornegi' diye aniyordu) | Kullanici karari: ajan paket yaratmamali -> script silindi. Atiflar mekanizma diline cevrildi; uc yerde 'silindi, geri eklenmez' notu birakildi. Operator SE21/SE80 kullanir. MCP'de paket yaratan tool YOK (dogrulandi) |
| `scripts/create_program.py` | 2026-08-01 bug-avi kuyrugu | Calistirilamaz fosil: argparse YOK, baglanti yolu `<PROJECT_ROOT>\conn_adt` (NOKTASIZ — gercek dosya `.conn_adt`), yani calistirilsa bile dosyayi bulamaz. Hicbir yerden cagrilmiyor, playbook referansi yok | Ikame MEVCUT: `scaffold_classic_program.py` + MCP `adt_push_source(object_type='program')` (URI segmenti `programs/programs` kayitli). Klasik program deseni playbook/adt-programs.md'de |
