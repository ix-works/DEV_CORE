#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAYIT-1 fixture — ADR 0010 tier: FAIL-CLOSED + TAM-ANAHTAR eslesmesi.

Neden bu fixture kalici: 2026-08-01 bug-avinda tier korumasinin girdisi eksikken
EN IZINLI degere (DEV) dustugu ve `ADT_SAP_TIER_OLD=DEV` gibi bir ONEK satirinin
gercek `ADT_SAP_TIER=PRD` satirini gasp ettigi bulundu. Iki kusur da SESSIZ'di.

Uc baglam (F3):
  (1) MCP surec baglami   -> mcp_servers/sap_adt/_conn.get_active_tier + guardrails
  (2) guard katmani       -> require_writable_tier / require_data_access dogrudan
  (3) GOREV-DISI baglam   -> scripts/switch_tier.py (ayri script) + scripts/statusline.py
                             (her prompt'ta kosan hafif script, sentetik PROJE kokunde)

Kosum: python tests/fixtures/tier_fail_closed/run.py   (exit 0 = hepsi beklendigi gibi)
Kosucu: tests/run_fixture_tests.py (OZEL_TESTLER)
"""
from __future__ import annotations

import os
import sys
import tempfile
import types
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

SONUC: list[tuple[bool, str]] = []


def kontrol(ad: str, kosul: bool, detay: str = "") -> None:
    SONUC.append((kosul, f"{ad}{(' -> ' + detay) if detay else ''}"))


def conn_yaz(dizin: Path, govde: str) -> Path:
    p = dizin / ".conn_adt"
    p.write_text(govde, encoding="utf-8")
    return p


def tier_oku(conn: Path | None) -> str:
    """get_active_tier'i, sap_adt_lib STUB'u ile izole cagir (agir kutuphane yok)."""
    stub = types.ModuleType("sap_adt_lib")
    stub.get_conn_path = lambda: conn  # type: ignore[attr-defined]
    sys.modules["sap_adt_lib"] = stub
    for m in [k for k in sys.modules if k.startswith("mcp_servers.sap_adt._conn")]:
        del sys.modules[m]
    from mcp_servers.sap_adt._conn import get_active_tier
    return get_active_tier()


GOVDE_TIERSIZ = "ADT_SAP_URL=https://ornek.test:44300\nADT_SAP_CLIENT=100\n"
# ONEK TUZAGI: sahte anahtar GERCEK anahtardan ONCE geliyor (gasp senaryosu).
GOVDE_ONEK_TUZAGI = (
    "ADT_SAP_URL=https://ornek.test:44300\n"
    "ADT_SAP_TIER_OLD=DEV\n"
    "ADT_SAP_TIER_YEDEK=DEV\n"
    "ADT_SAP_TIER=PRD\n"
)
GOVDE_TEMIZ_DEV = "ADT_SAP_URL=https://ornek.test:44300\nADT_SAP_TIER=DEV\n"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="tier_fc_"))
    os.environ.pop("ADT_SAP_TIER", None)

    from mcp_servers.sap_adt.data_guard import require_data_access
    from mcp_servers.sap_adt.guardrails import GuardrailViolation, require_writable_tier

    # ---------------------------------------------------------------- BAGLAM 1
    # (1a) BOZUK: tier satiri YOK -> UNKNOWN (eskiden DEV donuyordu = fail-open)
    d1 = tmp / "tiersiz"
    d1.mkdir()
    t = tier_oku(conn_yaz(d1, GOVDE_TIERSIZ))
    kontrol("1a tier-satirsiz .conn_adt -> UNKNOWN", t == "UNKNOWN", f"tier={t}")

    # (1b) BOZUK: onek tuzagi -> gercek satir kazanmali (PRD), gasp OLMAMALI
    d2 = tmp / "onek"
    d2.mkdir()
    t2 = tier_oku(conn_yaz(d2, GOVDE_ONEK_TUZAGI))
    kontrol("1b ADT_SAP_TIER_OLD=DEV once gelse de tier=PRD", t2 == "PRD", f"tier={t2}")

    # (1c) TEMIZ: dogru satir -> DEV (regresyon: mesru kurulum bloklanmamali)
    d3 = tmp / "temiz"
    d3.mkdir()
    t3 = tier_oku(conn_yaz(d3, GOVDE_TEMIZ_DEV))
    kontrol("1c ADT_SAP_TIER=DEV -> DEV", t3 == "DEV", f"tier={t3}")

    # (1d) Dosya yok + env var -> env fallback korunuyor
    os.environ["ADT_SAP_TIER"] = "QAS"  # alias -> QA
    t4 = tier_oku(None)
    os.environ.pop("ADT_SAP_TIER", None)
    kontrol("1d dosya yok + env=QAS -> QA (alias korunuyor)", t4 == "QA", f"tier={t4}")

    # (1e) AYNI PARSER'IN DIGER TUKETICISI: _conn_value (ADT_SAP_URL/CLIENT).
    # atom._guard_binding_current bunlari KIYASLAR (baglanti-kaymasi gate'i); onek gaspi
    # burada "yanlis sisteme yaziyorum" felaketini SESSIZCE gizleyebilirdi.
    d5 = tmp / "conn_value"
    d5.mkdir()
    conn5 = conn_yaz(d5, "ADT_SAP_URL_OLD=https://yanlis.test\n"
                         "ADT_SAP_URL=https://dogru.test\n"
                         "ADT_SAP_CLIENT_ESKI=999\nADT_SAP_CLIENT=100\n"
                         + GOVDE_TEMIZ_DEV)
    stub = types.ModuleType("sap_adt_lib")
    stub.get_conn_path = lambda: conn5  # type: ignore[attr-defined]
    sys.modules["sap_adt_lib"] = stub
    for m in [k for k in sys.modules if k.startswith("mcp_servers.sap_adt._conn")]:
        del sys.modules[m]
    from mcp_servers.sap_adt._conn import _conn_value
    u = _conn_value("ADT_SAP_URL", "")
    c = _conn_value("ADT_SAP_CLIENT", "")
    kontrol("1e _conn_value ADT_SAP_URL onek gaspina ugramaz",
            u == "https://dogru.test", f"url={u}")
    kontrol("1f _conn_value ADT_SAP_CLIENT onek gaspina ugramaz", c == "100", f"client={c}")

    # ---------------------------------------------------------------- BAGLAM 2
    def mutasyon_reddedildi(tier) -> bool:
        try:
            require_writable_tier(tier, what="test create")
            return False
        except GuardrailViolation:
            return True

    kontrol("2a require_writable_tier(UNKNOWN) REDDEDER", mutasyon_reddedildi("UNKNOWN"))
    kontrol("2b require_writable_tier(None) REDDEDER (ikinci fail-open katmani)",
            mutasyon_reddedildi(None))
    kontrol("2c require_writable_tier('') REDDEDER", mutasyon_reddedildi(""))
    kontrol("2d require_writable_tier('PRD') REDDEDER", mutasyon_reddedildi("PRD"))
    kontrol("2e require_writable_tier('DEV') SERBEST (temiz baglam)",
            not mutasyon_reddedildi("DEV"))

    # Mesaj yol gosteriyor mu (kullanilabilirlik: kapali kapi + cikis yolu)
    try:
        require_writable_tier(None)
        msg = ""
    except GuardrailViolation as gv:
        msg = str(gv)
    kontrol("2f UNKNOWN mesaji duzeltme komutunu soyluyor",
            "ADT_SAP_TIER" in msg and "switch_tier" in msg, msg[:60])

    # Salt-okuma gereksiz kisitlanmiyor mu? (hassas-OLMAYAN tablo UNKNOWN'da serbest)
    def veri_reddedildi(tier, tablo) -> bool:
        try:
            require_data_access(tier, tablo)
            return False
        except GuardrailViolation:
            return True

    kontrol("2g UNKNOWN + hassas-OLMAYAN tablo -> okuma SERBEST",
            not veri_reddedildi("UNKNOWN", "T000"))
    kontrol("2h UNKNOWN + hassas tablo, onaysiz -> REDDEDILIR (DEV muafiyeti yok)",
            veri_reddedildi("UNKNOWN", "PA0002"))
    kontrol("2i DEV + hassas tablo -> serbest (regresyon: DEV muafiyeti duruyor)",
            not veri_reddedildi("DEV", "PA0002"))
    # AYIRT EDICI: eski kod `(tier or "DEV")` ile None'i DEV sayip PII kapisini ACIYORDU.
    kontrol("2j require_data_access(None, hassas) -> REDDEDILIR (None != DEV)",
            veri_reddedildi(None, "PA0002"))
    kontrol("2k require_data_access('', hassas) -> REDDEDILIR",
            veri_reddedildi("", "PA0002"))

    # ------------------------------------------------- BAGLAM 3 (GOREV-DISI)
    # switch_tier: AYRI script, AYRI parser (ayni sinif hata oradaydi)
    import switch_tier  # noqa: E402

    slot_onek = tmp / "SLOT_ONEK.env"
    slot_onek.write_text(GOVDE_ONEK_TUZAGI, encoding="utf-8")
    slot_tiersiz = tmp / "SLOT_TIERSIZ.env"
    slot_tiersiz.write_text(GOVDE_TIERSIZ, encoding="utf-8")
    slot_yorum = tmp / "SLOT_YORUM.env"
    slot_yorum.write_text("# ADT_SAP_TIER=DEV\nADT_SAP_TIER=PRD\n", encoding="utf-8")

    st1 = switch_tier._tier_of_file(slot_onek)
    kontrol("3a switch_tier onek tuzagi -> PRD", st1 == "PRD", f"tier={st1}")
    st2 = switch_tier._tier_of_file(slot_tiersiz)
    kontrol("3b switch_tier tier-satirsiz slot -> None (DEV DEGIL)", st2 is None, f"tier={st2}")
    st3 = switch_tier._tier_of_file(slot_yorum)
    kontrol("3c switch_tier yorum satiri sayilmaz -> PRD", st3 == "PRD", f"tier={st3}")

    # statusline: sentetik PROJE kokunde (farkli proje sekli — mcp_servers yok)
    import statusline  # noqa: E402

    proje = tmp / "sentetik_proje"
    proje.mkdir()
    conn_yaz(proje, "ADT_SAP_SYSTEM_NAME_ESKI=YANLIS\nADT_SAP_SYSTEM_NAME=DOGRU\n"
                    + GOVDE_ONEK_TUZAGI)
    ad, tier = statusline.sap_system(proje)
    kontrol("3d statusline onek tuzaginda tier=PRD gosterir", tier == "PRD", f"tier={tier}")
    kontrol("3e statusline sistem adini onek satirina kaptirmaz", ad == "DOGRU", f"ad={ad}")

    proje2 = tmp / "sentetik_proje_tiersiz"
    proje2.mkdir()
    conn_yaz(proje2, GOVDE_TIERSIZ)
    _, tier2 = statusline.sap_system(proje2)
    kontrol("3f statusline tier-satirsiz -> None (DEV uydurmaz)", tier2 is None, f"tier={tier2}")

    # AYIRT EDICI (statusline SON-KAZANIR dongusu): tuzak GERCEK satirdan SONRA gelirse
    # eski onek-eslesmesi tier'i EZIYORDU (PRD sisteminde 'DEV' gosterirdi — en tehlikeli yon).
    proje3 = tmp / "sentetik_proje_tuzak_sonra"
    proje3.mkdir()
    conn_yaz(proje3, "ADT_SAP_SYSTEM_NAME=DOGRU\nADT_SAP_TIER=PRD\n"
                     "ADT_SAP_TIER_OLD=DEV\nADT_SAP_SYSTEM_NAME_ESKI=YANLIS\n")
    ad3, tier3 = statusline.sap_system(proje3)
    kontrol("3g statusline: tuzak SONRA gelse de tier=PRD (ezilmez)", tier3 == "PRD",
            f"tier={tier3}")
    kontrol("3h statusline: sistem adi sonraki onek satiriyla ezilmez", ad3 == "DOGRU",
            f"ad={ad3}")

    # switch_tier ayni yon: ilk-eslesme donduren parser icin tuzak-ONCE kritikti (3a);
    # tuzak-SONRA da regresyon olmamali.
    slot_sonra = tmp / "SLOT_TUZAK_SONRA.env"
    slot_sonra.write_text("ADT_SAP_TIER=PRD\nADT_SAP_TIER_OLD=DEV\n", encoding="utf-8")
    st4 = switch_tier._tier_of_file(slot_sonra)
    kontrol("3i switch_tier: tuzak SONRA -> PRD", st4 == "PRD", f"tier={st4}")

    # ------------------------------------------------------------------ rapor
    hata = [d for ok, d in SONUC if not ok]
    for ok, d in SONUC:
        print(f"  [{'OK' if ok else 'FAIL'}] {d}")
    print(f"\n{len(SONUC) - len(hata)}/{len(SONUC)} OK")
    return 1 if hata else 0


if __name__ == "__main__":
    raise SystemExit(main())
