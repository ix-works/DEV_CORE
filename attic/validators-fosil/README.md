# validators-fosil — 2026-07-31 attic taşıması (denetim T0.4 / Ek-D kararı)

Neden: 4 dosya da hiçbir runner'a kablolu değildi ve ÇALIŞTIRILAMAZ durumdaydı
(placeholder yollar: `<PROJECT_ROOT>`, biri opencode-marketplace path'ine sys.path
ekliyor; `_verify_sqlview` tek objeye hardcoded). Tek-seferlik debug fosilleri.
Ek gerekçe: `adt_syntax_check.py` adı MCP tool'u `adt_syntax_check` ile çakışıyordu
(PATTERN #20 sonrası aktif karışıklık riski). Kanıt: proje reposu
governance/DENETIM-2026-07-31-envanter-ve-verimlilik.md Ek-D D-2.
