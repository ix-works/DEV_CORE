# -*- coding: utf-8 -*-
"""mcp_import_denetimi — sap-adt MCP sunucusu IMPORT edilebiliyor mu? (TEK KAYNAK, Q335)

Tüketiciler (ikisi de BU modülü çağırır; deseni yeniden türetmez):
  · `scripts/team_setup.py::smoke`   — kurulum sonu; başarısızsa kurulum TAMAM DEMEZ (exit 1)
  · `scripts/ix_doctor.py::katman5`  — sağlık taraması 5b2; `.conn_adt`'den BAĞIMSIZ koşar

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

⛔ ORTAM = `.mcp.json` ORTAMI (2026-09-18 düzeltme — bug-gate F1): denetim alt-sürecinin ortamı,
MCP sunucusunun GERÇEK çalışma zamanının ortamıdır ve **aynı kaynaktan türetilir**, yeniden
türetilmez: `<proje>/.mcp.json` → `mcpServers["sap-adt"]["env"]` (`${VAR}` / `${VAR:-varsayılan}`
genişletilir; `CLAUDE_PROJECT_DIR` = proje). Şablona düşüş YALNIZ dosya HİÇ YOKKEN: o zaman
aynı değerin ÜRETİCİSİ `init_project.py::MCP_JSON` okunur (AST ile, import yan etkisi yok); o
da okunamazsa ÖLÇÜLEMEDİ = başarısız. ⛔ Dosya VAR ama okunamıyor / geçersiz JSON / `sap-adt`
sunucusu yok / sunucu ya da `env` nesne değil ⇒ **ÖLÇÜLEMEDİ = başarısız, şablona DÜŞÜLMEZ**
(bug-gate-2 M1, 2026-09-18: ilk sürüm bu durumda şablona düşüp `import-ok` diyordu — oysa
çalışma zamanı o bozuk dosyayla sunucuyu hiç açmaz; ölçülen ortam ≠ çalışma zamanı ortamı).
`sap-adt` var ama `env` anahtarı YOKSA çalışma zamanı ortamı kullanıcının ortamıdır ⇒ `{}`
kabul edilir (şablona düşülmez); o durumda import çoğunlukla `No module named 'mcp_servers'`
ile düşer ve çare metni (`onarim_metni`) pip DEĞİL `.mcp.json`/`core` bağını gösterir. Çalışma zamanı env'i
`"PYTHONPATH": "${CLAUDE_PROJECT_DIR:-.}/core"` ile kullanıcının PYTHONPATH'ini EZER ⇒ denetim
de EZER. ⚠ İlk sürüm (aynı gün) core'u kullanıcı yolunun ÖNÜNE ekleyip kullanıcı yolunu
koruyordu, gerekçe "gerçek çalışma zamanına daha yakın" idi — **YANLIŞTI** (`.mcp.json`'a
bakılmamıştı): kullanıcı PYTHONPATH'inde çalışan bir `mcp 1.x`, site-packages'ta `2.x` varken
denetim PASS, sunucu AÇILMAZDI (sahte-yeşil). `ek_yol` parametresi YALNIZ TEST içindir
(fixture'ın sahte `mcp` paketini site-packages benzeri, `.mcp.json` yolunun ARKASINA koyar);
üretimde hiçbir çağıran vermez ⇒ varsayılan `None` iken ortam `.mcp.json` ortamına EŞİTTİR.

KAPSAM BEYANI (çıktıya da yazılır): yalnız `import mcp_servers.sap_adt.server` ölçülür, BU
yorumlayıcıyla (`sys.executable`) ve `.mcp.json` sap-adt ORTAMIYLA. `.mcp.json`'un `command`
alanı (yorumlayıcı) UYGULANMAZ — farklıysa onun site-packages'ı ÖLÇÜLMEMİŞTİR. Tool kaydı
(`_register_all`), `.conn_adt` ve SAP bağlantısı ÖLÇÜLMEZ.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# C-ENC-01 (check_console_utf8): bu modül KENDİSİ hiçbir şey BASMAZ — gate, aşağıdaki `KOMUT`
# dizesindeki `print(` metnini (alt-süreç komutu) çıktı çağrısı sayar (metin arar, çalıştırmaz;
# `utils/kapsam.py` notundaki aynı sınıf). Koruma yine de konur, ama KOŞULLU: yalnız akış
# UTF-8 DEĞİLSE yeniden yapılandırılır ⇒ zaten UTF-8 kurmuş çağıranın (`team_setup` ·
# `ix_doctor`, ikisi de modül başında kurar) `errors` politikası import yan etkisiyle
# DEĞİŞMEZ (koşulsuz kardeş deseni `errors="replace"`i sessizce dayatırdı — ölçüldü 2026-09-18).
for _akis in (sys.stdout, sys.stderr):
    try:
        if (getattr(_akis, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

ISARET = "import-ok"
KOMUT = "import mcp_servers.sap_adt.server; print('import-ok')"
KAPSAM = ("yalnız `import mcp_servers.sap_adt.server` ölçüldü (bu yorumlayıcı + .mcp.json "
          "sap-adt ortamı; .mcp.json `command` yorumlayıcısı uygulanmadı); tool kaydı, "
          ".conn_adt ve SAP bağlantısı ÖLÇÜLMEDİ")
SUNUCU = "sap-adt"
_DEGISKEN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
_AZAMI = 500


def son_anlamli_satir(metin: str | None) -> str:
    """Metnin boş olmayan SON satırı (kırpılmış); yoksa ""."""
    for satir in reversed((metin or "").splitlines()):
        s = satir.strip()
        if s:
            return s
    return ""


def _sunucu_env(metin: str) -> tuple[dict | None, str]:
    """`.mcp.json` metninden (`mcpServers["sap-adt"]["env"]`, neden). Bozuksa (None, neden).
    `env` anahtarı YOKSA `{}` (çalışma zamanı kullanıcı ortamıyla açılır — bozukluk değil)."""
    try:
        veri = json.loads(metin)
    except Exception as e:  # noqa: BLE001
        return None, f"geçersiz JSON ({type(e).__name__}: {str(e)[:80]})"
    sunucular = veri.get("mcpServers") if isinstance(veri, dict) else None
    if not isinstance(sunucular, dict) or SUNUCU not in sunucular:
        return None, f"`mcpServers.{SUNUCU}` sunucusu YOK"
    s = sunucular[SUNUCU]
    if not isinstance(s, dict):
        return None, f"`{SUNUCU}` girdisi nesne değil ({type(s).__name__})"
    if "env" not in s:
        return {}, "env yok (kullanıcı ortamı)"
    env = s["env"]
    if not isinstance(env, dict):
        return None, f"`{SUNUCU}.env` nesne değil ({type(env).__name__})"
    return {str(k): str(v) for k, v in env.items()}, ""


def _sablon_metni(core_root: Path) -> str | None:
    """`init_project.py::MCP_JSON` — `.mcp.json`'u ÜRETEN şablon (AST; modül import EDİLMEZ)."""
    try:
        agac = ast.parse((Path(core_root) / "scripts" / "init_project.py").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    for dugum in agac.body:
        if isinstance(dugum, ast.Assign) and any(
                isinstance(h, ast.Name) and h.id == "MCP_JSON" for h in dugum.targets):
            try:
                return ast.literal_eval(dugum.value)
            except Exception:  # noqa: BLE001
                return None
    return None


def mcp_calisma_env(core_root: Path, proje: Path) -> tuple[dict | None, str]:
    """(sap-adt sunucusunun `.mcp.json` env'i — HAM, genişletilmemiş · kaynak etiketi).

    Dosya VARSA yalnız o okunur — bozuksa (None, neden) ⇒ çağıran ÖLÇÜLEMEDİ der (şablona
    DÜŞÜLMEZ: çalışma zamanı bozuk dosyayla sunucuyu açmaz). Dosya YOKSA
    `init_project.py::MCP_JSON` şablonu (aynı değerin üreticisi); o da yoksa (None, neden)."""
    mj = Path(proje) / ".mcp.json"
    if mj.exists():
        try:
            env, neden = _sunucu_env(mj.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            env, neden = None, f"okunamadı ({type(e).__name__})"
        if env is not None:
            return env, str(mj)
        return None, f"{mj} bozuk: {neden} — şablona DÜŞÜLMEZ (çalışma zamanı bu dosyayla açılmaz)"
    sablon = _sablon_metni(core_root)
    env, neden = _sunucu_env(sablon) if sablon is not None else (None, "okunamadı")
    if env is not None:
        return env, "init_project.py MCP_JSON şablonu (.mcp.json YOK)"
    return None, f".mcp.json YOK; init_project.py MCP_JSON şablonu da kullanılamadı ({neden})"


def _genislet(deger: str, ortam: dict) -> str:
    """`${VAR}` / `${VAR:-varsayılan}` — tanımsız ve varsayılansız değişken OLDUĞU GİBİ kalır
    (sessizce boşaltılmaz; import başarısızlığı ayrıntıda görünür)."""
    def _yerine(m: re.Match) -> str:
        v = ortam.get(m.group(1))
        if v:
            return v
        return m.group(2) if m.group(2) is not None else m.group(0)
    return _DEGISKEN.sub(_yerine, deger)


def alt_surec_ortami(core_root: Path, proje: Path, taban: dict | None = None,
                     ek_yol: list[str] | None = None) -> tuple[dict | None, str]:
    """(denetim alt-sürecinin ortamı · kaynak). Ortam = `taban` (varsayılan `os.environ`)
    + `CLAUDE_PROJECT_DIR=proje` + `.mcp.json` sap-adt env'i (genişletilmiş; aynı anahtarı
    EZER — çalışma zamanı gibi). `ek_yol` YALNIZ TEST: PYTHONPATH'in SONUNA eklenir."""
    ham, kaynak = mcp_calisma_env(core_root, proje)
    if ham is None:
        return None, kaynak
    env = dict(os.environ if taban is None else taban)
    env["CLAUDE_PROJECT_DIR"] = str(proje)
    for k, v in ham.items():
        env[k] = _genislet(v, env)
    if ek_yol:
        env["PYTHONPATH"] = os.pathsep.join([p for p in [env.get("PYTHONPATH", "")] if p]
                                            + [str(y) for y in ek_yol])
    return env, kaynak


_MCP_SERVERS_YOK = re.compile(r"No module named '(mcp_servers)(\.[\w.]+)?'")


def onarim_metni(ayrinti: str, req_file: Path | str, python: str) -> str:
    """Başarısızlık AYRINTISINDAN (son anlamlı satır) çare metni — tek kaynak (team_setup +
    ix_doctor). ⛔ `mcp_servers` bulunamıyorsa sorun PAKET değil YOLDUR: `pip install` onu
    düzeltmez (tekrar koşunca aynı FAIL — bug-gate-2 L1) ⇒ `.mcp.json`/`core` bağı çaresi.
    Ortam türetilemediyse (`ÖLÇÜLEMEDİ`) çare `.mcp.json`'u onarmaktır. Diğer her durum
    (`mcp` paketi / bağımlılık / shim hatası) ⇒ pip + requirements (`mcp<2` sınırı)."""
    if ayrinti.startswith("ÖLÇÜLEMEDİ"):
        return ("proje `.mcp.json`'unu onar — geçerli JSON, `mcpServers.sap-adt` nesnesi ve "
                "`env` nesnesi olmalı (üretici şablon: `init_project.py` MCP_JSON, "
                "`env.PYTHONPATH` = `${CLAUDE_PROJECT_DIR:-.}/core`); pip ÇARE DEĞİL")
    if _MCP_SERVERS_YOK.search(ayrinti):
        return ("`mcp_servers` YOLDA YOK — proje `.mcp.json` sap-adt `env.PYTHONPATH` "
                "`${CLAUDE_PROJECT_DIR:-.}/core` olmalı ve proje kökünde `core` bağı (junction) "
                "bulunmalı (`team_setup --repair-junctions`); pip ÇARE DEĞİL")
    return (f"\"{python}\" -m pip install -r \"{req_file}\" (requirements `mcp<2` sınırını "
            f"taşır)")


def mcp_import_denetimi(core_root: Path, proje: Path, timeout: int = 60,
                        ek_yol: list[str] | None = None) -> tuple[bool, str]:
    """(başarılı mı, ayrıntı). Başarısızlıkta ayrıntı = `exit <rc>: <son anlamlı satır>`.

    ⛔ ÖLÇÜLEMEDİ ≠ BAŞARILI: alt süreç başlatılamaz / zaman aşımına uğrarsa False döner
    (ayrıntıda neden yazar) — sessizce geçilmez.
    """
    env, kaynak = alt_surec_ortami(core_root, proje, ek_yol=ek_yol)
    if env is None:
        return False, f"ÖLÇÜLEMEDİ — sap-adt MCP ortamı türetilemedi ({kaynak})"
    try:
        r = subprocess.run([sys.executable, "-c", KOMUT], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(proje),
                           env=env, timeout=timeout)
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
