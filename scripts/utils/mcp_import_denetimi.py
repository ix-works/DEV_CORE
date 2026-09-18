# -*- coding: utf-8 -*-
"""mcp_import_denetimi — sap-adt MCP sunucusu IMPORT edilebiliyor mu? (TEK KAYNAK, Q335)

Tüketiciler (ikisi de BU modülü çağırır; deseni yeniden türetmez):
  · `scripts/team_setup.py::smoke`   — kurulum sonu; başarısızsa kurulum TAMAM DEMEZ (exit 1)
  · `scripts/ix_doctor.py::katman5`  — sağlık taraması 5c; `.conn_adt`'den BAĞIMSIZ koşar

NEDEN VAR (Issue #274, 2026-09-18): `requirements.txt` `mcp>=1.0.0` üst sınırsızdı; temiz
makinede pip `mcp 2.x` kurdu ve 2.x'te `mcp.server.fastmcp` bir SHIM'dir — import anında
`ModuleNotFoundError: ... This is mcp 2.x ... or pin 'mcp<2' ...` fırlatır. Sunucu hiç
açılmaz, oturumda sap-adt `Connection closed` görünür. Eski smoke bunu GÖRDÜ ama:
  (a) çıktının İLK 60 karakterini bastı → `Traceback (most recent call last): ...` — bilgi
      taşımayan başlık; asıl hata satırı (SON satır) görünmedi,
  (b) WARN saydı ve kurulum `team_setup TAMAM` diyerek exit 0 ile bitti,
  (c) `ix_doctor` bu yüzeye HİÇ bakmıyordu (K5 yalnız `server.py` dosya varlığı).

⛔ SON satır, İLK değil: Python traceback'inde bilgi taşıyan satır SONDADIR (istisna sınıfı +
mesaj). Boş satırlar atlanır; stderr önceliklidir, boşsa stdout'a bakılır.

⛔ PYTHONPATH ÖNE EKLENİR, EZİLMEZ (2026-09-18 davranış değişikliği; eski smoke
`PYTHONPATH=<core>` ile EZİYORDU): core kökü DAİMA İLK girdidir ⇒ kullanıcının PYTHONPATH'i
core modüllerini (`mcp_servers.*`) gölgeleyemez; yalnız core'da OLMAYAN paketler (örn. `mcp`)
kullanıcı yolundan gelebilir. Bu, MCP sunucusunun gerçek çalışma zamanına (kullanıcı
ortamını devralan süreç) daha yakındır ve fixture'ın sahte `mcp` paketiyle GERÇEK
`server.py` zincirini koşabilmesini sağlar. Değişen YALNIZ bu denetimin alt-sürecidir —
`.mcp.json` / MCP çalışma zamanı ortamına dokunulmaz.

KAPSAM BEYANI (çıktıya da yazılır): yalnız `import mcp_servers.sap_adt.server` ölçülür, BU
yorumlayıcıyla (`sys.executable`). Tool kaydı (`_register_all`), `.conn_adt` ve SAP
bağlantısı ÖLÇÜLMEZ. `.mcp.json`'daki yorumlayıcı farklıysa onun ortamı ÖLÇÜLMEMİŞTİR.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ISARET = "import-ok"
KOMUT = "import mcp_servers.sap_adt.server; print('import-ok')"
KAPSAM = ("yalnız `import mcp_servers.sap_adt.server` ölçüldü (bu yorumlayıcı); tool kaydı, "
          ".conn_adt ve SAP bağlantısı ÖLÇÜLMEDİ")
_AZAMI = 500


def son_anlamli_satir(metin: str | None) -> str:
    """Metnin boş olmayan SON satırı (kırpılmış); yoksa ""."""
    for satir in reversed((metin or "").splitlines()):
        s = satir.strip()
        if s:
            return s
    return ""


def alt_surec_ortami(core_root: Path, proje: Path, taban: dict | None = None) -> dict:
    """Denetim alt-sürecinin ortamı: core kökü PYTHONPATH'in BAŞINA (ezme değil) +
    `CLAUDE_PROJECT_DIR`. `taban` verilmezse `os.environ` kopyalanır."""
    env = dict(os.environ if taban is None else taban)
    onceki = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(core_root) + (os.pathsep + onceki if onceki else "")
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    return env


def mcp_import_denetimi(core_root: Path, proje: Path, timeout: int = 60) -> tuple[bool, str]:
    """(başarılı mı, ayrıntı). Başarısızlıkta ayrıntı = `exit <rc>: <son anlamlı satır>`.

    ⛔ ÖLÇÜLEMEDİ ≠ BAŞARILI: alt süreç başlatılamaz / zaman aşımına uğrarsa False döner
    (ayrıntıda neden yazar) — sessizce geçilmez.
    """
    try:
        r = subprocess.run([sys.executable, "-c", KOMUT], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(proje),
                           env=alt_surec_ortami(core_root, proje), timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT ({timeout} sn) — import tamamlanmadı"
    except Exception as e:  # noqa: BLE001
        return False, f"alt süreç başlatılamadı ({type(e).__name__}: {e})"
    if r.returncode == 0 and ISARET in [s.strip() for s in (r.stdout or "").splitlines()]:
        return True, ISARET
    son = son_anlamli_satir(r.stderr) or son_anlamli_satir(r.stdout) or "çıktı yok"
    if len(son) > _AZAMI:                     # bilgi SONDADIR → baş kırpılır, son korunur
        son = "…" + son[-(_AZAMI - 1):]
    return False, f"exit {r.returncode}: {son}"
