#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""conn_cift_anahtar fixture — `.conn_adt`'de ayni anahtarin IKI KEZ gecmesi.

NEDEN VAR (2026-08-01 adversarial bug-avi, W2-MG-01):
Iki okuyucu ayni dosyayi FARKLI okuyordu:
  `mcp_servers/sap_adt/_conn.py`  -> kendi satir dongusu, ILK kazanir
  `scripts/sap_adt_lib.py`        -> `load_dotenv`, SON kazanir  (GERCEK BAGLANTI)
Olculdu (DEV ustte / PRD altta bir dosyada):
  get_active_tier() -> DEV   (guard "mutasyon serbest" der)
  dotenv/istemci    -> PRD   (baglanti PRD'ye gider)
=> guard ile baglanti AYRISIR: SESSIZ YANLIS-SISTEM YAZIMI.

Tetikleyici bizim KENDI mesajimizdi: tier fail-closed uyarisi ".conn_adt'ye
ADT_SAP_TIER=... EKLE" diyor; ekleyen kisi cift anahtar uretir. (`switch_tier`
dosyanin TAMAMINI kopyaladigi icin cift uretmez — kaynak elle duzenlemedir.)

POLITIKA (kodda da yazili):
  * otorite dotenv'dir -> SON deger alinir (`_conn_value` artik son-kazanir)
  * tier'da FARKLI degerlerle cakisma varsa hangi sistemde oldugumuzu BILMIYORUZ
    -> UNKNOWN (fail-closed, mutasyon reddedilir). Ayni degerle tekrar zararsizdir.

Senaryolar: kontrol (tek DEV / tek PRD) · cift-cakisik -> UNKNOWN · cift-ayni -> deger
· onek tuzagi regresyonu (ADT_SAP_TIER_OLD gaspetmemeli) · tier yok -> UNKNOWN.
Her senaryoda AYRICA `_conn_value(URL)` == dotenv(URL) dogrulanir (ayrisma capasi).
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
if not (REPO / "mcp_servers").is_dir():
    raise SystemExit(f"[fixture-hatasi] repo koku yanlis cozuldu: {REPO}")
for p in (REPO, REPO / "scripts", REPO / "scripts" / "utils"):
    sys.path.insert(0, str(p))

try:
    from dotenv import dotenv_values
except Exception as exc:                                   # pragma: no cover
    raise SystemExit(f"[fixture-hatasi] dotenv yok (sessiz gecme YOK): {exc}")


def _dene(ad: str, icerik: str, beklenen_tier: str) -> tuple:
    d = Path(tempfile.mkdtemp(prefix="conn_fx_"))
    (d / ".conn_adt").write_text(icerik, encoding="utf-8")
    os.environ.pop("ADT_SAP_TIER", None)
    # ⛔ K4 SINIFI, IKINCI UYE (2026-08-20 olculdu): asagidaki `sal.get_conn_path`
    #    yonlendirmesi GEC KALIR. `import sap_adt_lib` IMPORT ANINDA
    #    `find_conn_file()` + `load_dotenv()` kosar; repo KOKUNDE bir `.conn_adt`
    #    varsa oradaki `ADT_SAP_TIER=DEV` os.environ'a YAZILIR ve yonlendirme
    #    kurulmadan once tier ZATEN kirlenmis olur. Sonuc: "tier YOK -> UNKNOWN"
    #    vektoru DEV okur ve SAHTE FAIL verir.
    #    ⚠ Suit kosum ORTASINDA repo koküne bir `.conn_adt` yaziyor (olculdu:
    #    kosumun ~39. saniyesi, 1087 B) ⇒ bu fixture ONCE kosarsa gecer, SONRA
    #    kosarsa duser: kaynagi belirsiz, ARALIKLI bir kirmizi.
    #    Cozum: import-anindaki kok cozumlemesini de KUMA yonlendir.
    os.environ["CLAUDE_PROJECT_DIR"] = str(d)

    # Modulu TAZE yukle: `get_active_tier` cache'li ve `get_conn_path` modul-duzeyinde
    # cozulur. Yonlendirme yapilmazsa GERCEK proje dosyasi okunur ve fixture hicbir sey
    # olcmez (ilk kurulumda tam bu oldu: 6 vakanin hepsi "DEV" dondu; kontrol grubu
    # "tek PRD -> PRD" beklerken DEV verince harness hatasi anlasildi).
    for m in ("cn_fx", "sap_adt_lib"):
        sys.modules.pop(m, None)
    spec = importlib.util.spec_from_file_location("cn_fx", REPO / "mcp_servers/sap_adt/_conn.py")
    c = importlib.util.module_from_spec(spec)               # type: ignore[arg-type]
    sys.modules["cn_fx"] = c
    spec.loader.exec_module(c)                              # type: ignore[union-attr]
    import sap_adt_lib as sal                               # type: ignore
    sal.get_conn_path = lambda p=(d / ".conn_adt"): p       # kontrollu yonlendirme
    if hasattr(c.get_active_tier, "cache_clear"):
        c.get_active_tier.cache_clear()

    tier = c.get_active_tier()
    url = c._conn_value("ADT_SAP_URL", "")
    dv = dotenv_values(str(d / ".conn_adt"))
    url_es = (url == (dv.get("ADT_SAP_URL") or ""))
    ok = (tier == beklenen_tier) and url_es
    return (ad, ok, f"tier={tier} beklenen={beklenen_tier} url==dotenv:{url_es}")


def main() -> int:
    U = "https://dev.test"
    P = "https://prd.test"
    vakalar = [
        ("KONTROL tek-anahtar DEV", f"ADT_SAP_TIER=DEV\nADT_SAP_URL={U}\n", "DEV"),
        ("KONTROL tek-anahtar PRD", f"ADT_SAP_TIER=PRD\nADT_SAP_URL={P}\n", "PRD"),
        ("CIFT cakisik DEV+PRD -> UNKNOWN",
         f"ADT_SAP_TIER=DEV\nADT_SAP_URL={U}\nADT_SAP_TIER=PRD\nADT_SAP_URL={P}\n", "UNKNOWN"),
        ("CIFT ayni deger -> zararsiz", f"ADT_SAP_TIER=DEV\nADT_SAP_URL={U}\nADT_SAP_TIER=DEV\n", "DEV"),
        ("REGRESYON onek tuzagi (_OLD gaspetmemeli)",
         f"ADT_SAP_TIER_OLD=DEV\nADT_SAP_TIER=PRD\nADT_SAP_URL={P}\n", "PRD"),
        ("tier YOK -> UNKNOWN", f"ADT_SAP_URL={U}\n", "UNKNOWN"),
    ]
    sonuc = [_dene(*v) for v in vakalar]
    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, detay in sonuc:
        print(f"  [{'OK' if ok else 'FAIL'}] {ad} -> {detay}")
    print(f"\n{gecen}/{len(sonuc)} OK")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
