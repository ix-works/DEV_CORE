#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""table_field_drop_tip fixture — DEV_CORE #408 (kayıt Q399): alan TİP değişikliği fiziksel tiple kıyaslanır.

NEDEN VAR (2026-11-11, kullanıcı onayı 2026-11-08 — plan A)
  `check_table_field_drop` alan tipini ilk ad parçasında kesiyordu ⇒ her yerleşik tip `abap` diye
  kaydediliyordu ⇒ `abap.int4`→`abap.int2`, `abap.char(100)`→`abap.char(10)`, `abap.dec(15,3)`→
  `abap.dec(13,3)` daralması GÖRÜNMÜYORDU (rc 0, "additive/güvenli"). Ters yönde ad metni kıyası,
  fiziksel tipi aynı kalan DTEL→DTEL ve yerleşik→DTEL geçişini BLOCKER yapıyordu.
  Düzeltme: tip TAM metinle alınır, DTEL ADT veri öğesi meta verisinden fiziksel tipe çözülür.

VEKTÖRLER (SAP yerine 127.0.0.1 sahte ADT ucu; alınan istekler listelenir — canlı SAP'ye istek yok)
  T1  bildirilen ① `abap.int4` → `abap.int2`            → rc 1 · TÜR DEĞİŞTİ (eski: rc 0)
  T2  bildirilen ② `abap.char(100)` → `abap.char(10)`   → rc 1 · DARALMA
  T3  bildirilen ③ `abap.dec(15,3)` → `abap.dec(13,3)`  → rc 1 · DARALMA
  T3b `abap.dec(15,3)` → `abap.dec(16,5)`: uzunluk + ondalık büyür ama TAM SAYI hanesi 12→11 → DARALMA
  T4  DTEL → DTEL, aynı fiziksel tip (CHAR 10)          → rc 0 · [INFO] · OK dtel-degisti-tip-ayni ⚠GEVŞETME
  T5  yerleşik → DTEL aynı tip (`abap.char(10)` → CHAR 10 DTEL) → rc 0 · [INFO]
  T5b sabit uzunluklu: `abap.int4` → INT4 DTEL (ADT uzunluğu 10, DDL'de uzunluk yok) → rc 0 · [INFO]
  T6  genişleme `abap.char(10)` → `abap.char(20)`        → rc 0 · stderr [WARNING] · FINDING tip-genisleme
  T6b DTEL → DTEL genişleme (CHAR 10 → CHAR 20)          → rc 0 · [WARNING]
  T7  çözülemeyen DTEL (404) tek BLOCKER nedeni           → rc 1 · ÖLÇÜLEMEDİ · FAIL measured=false
  T7b DTEL GET 500                                        → rc 1 · measured=false · neden http-500
  T8  ölçülmüş daralma + çözülemeyen DTEL birlikte        → rc 1 · measured=false BASILMAZ (lider pini)
  T9  onaysız DROP + çözülemeyen DTEL                     → rc 1 · measured=false BASILMAZ
  T10 `--ack-drop` + genişleme                            → rc 0 · ACK-WARNING + WARNING
  T10b `--ack-drop` + daralma                             → rc 1 (ack TİPİ kapsamaz)
  T11 aynı tip, boşluk farkı (`abap.char( 10 )`)          → rc 0 · additive · DTEL GET 0
  T12 DTEL tür değişikliği (CHAR DTEL → NUMC DTEL)        → rc 1 · TÜR DEĞİŞTİ
  T13 ÜÇÜNCÜ BAĞLAM: namespace'li tablo + DTEL (`/XNS/`, `%2F` yolu) · CRLF+BOM yerel dosya · XML
      öneki `de:` → [INFO] (T13a); aynı tabloda `dataType` BOŞ DTEL → ÖLÇÜLEMEDİ, rc 1 (T13b)
  T14 KAPSAM beyanı her kıyas koşumunda basılır (sıfır-bulgu anı dahil)
  T15 `abap.string(256)` → `abap.string(0)` (0 = sınırsız) → genişleme, rc 0
  T17 DTEL XML'inde `dataTypeLength` YOK → ÇÖZÜLEMEDİ (rc 1, measured=false) — eski kod 0 okuyup
      `abap.char(10)`'a geçişi "genişleme" rc 0 yapıyordu (düzeltme turu F4, ⚠SIKILAŞTIRMA)
  T17b `dataTypeLength` BOŞ öğe → aynı · T18 DEC DTEL'de `dataTypeDecimals` YOK → `dtel-ondalik-yok`
  DÜZELTME TURU 2: T19 CHAR `000000` → ÇÖZÜLEMEDİ (sıfır-uzunluk dalı) · T20 GEOM_EWKB `000000` A→B → INFO
      (ADT'de uzunluk 0 = sınırsız; eski: sahte ÖLÇÜLEMEDİ) · T21 `abap.utclong` → UTCLONG DTEL → INFO ·
      T22 `abap.decfloat16` → DECFLOAT16 DTEL → INFO · T23 `abap.decfloat34` → DECFLOAT34 DTEL → INFO ·
      T24 uzunluk `²` (isdigit True, int() patlar) → ÇÖZÜLEMEDİ, Traceback YOK
  DÜZELTME TURU 3 (yerleşik yazım SAP'nin tablo DDL'indeki gibi; `abap.d16n`/`d34n` DDL'de yok):
      T25 `abap.df16_raw` → DF16_RAW DTEL → INFO · T26 `abap.decfloat16` → DECFLOAT34 DTEL → TÜR DEĞİŞTİ ·
      T27 `abap.decfloat16` → DF16_RAW DTEL → TÜR DEĞİŞTİ · T28 `abap.df34_raw` → DF34_RAW DTEL (uzunluğu
      ölçülmedi, sabit sayılmaz) → ÖLÇÜLEMEDİ rc 1 + measured=false (fail-closed)
  T16 istekler yalnız sahte uca, yalnız tablo kaynağı + veri öğesi yolu; kumda `.conn_adt` oluşmadı
  TÜKETİCİLER (lider talebi: genişleme rc 0'ın ve measured=false'un sonucu SAYIYLA)
  R1  run_review table_update, genişleme → drop-guard kaydı PASS + `sessiz_bulgu_gates`'te
  R2  run_review table_update, yalnız çözülemeyen DTEL → drop-guard kaydı FAIL, verdict BLOCKER
  R3  run_review table_update, daralma → drop-guard kaydı FAIL, verdict BLOCKER
  K1  checklist_check BE-16, genişleme → PASS (bulgu 0)
  K2  checklist_check BE-16, yalnız çözülemeyen DTEL → ÖLÇÜLEMEDİ (⚠GEVŞETME 2. hücre: eski FAIL)
  K3  checklist_check BE-16, daralma + çözülemeyen DTEL → FAIL kalır

KULLANIM
  python tests/fixtures/table_field_drop_tip/run.py                  # vektörler
  python tests/fixtures/table_field_drop_tip/run.py --kok <ağaç>     # başka ağaç (taban / mutant kum)
  python tests/fixtures/table_field_drop_tip/run.py --mutasyon-<ad>  # tek mutasyon (KIPLER)
  Mutasyon çıkışı: 1 = ilan edilen küme TAM düştü · 2 = SAPMA · 3 = kurulamadı.
"""
from __future__ import annotations

import contextlib
import http.server
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import types
from pathlib import Path
from urllib.parse import unquote

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

BURASI = Path(__file__).resolve().parent
REPO = BURASI.parents[2]
_GATE = "check_table_field_drop"

# Alt süreç ADT_* değişkenlerini ortamdan okur; BTP/IAS/SAML/vekil ve `.conn_adt` arama adayları silinir.
_SIL = ("ADT_BTP_SERVICE_KEY_PATH", "ADT_BTP_AUTH_TYPE", "ADT_IAS_TOKEN_URL", "ADT_IAS_CLIENT_ID",
        "ADT_IAS_CLIENT_SECRET", "ADT_SAML_COOKIES_FILE", "HTTP_PROXY", "HTTPS_PROXY", "http_proxy",
        "https_proxy", "ALL_PROXY", "all_proxy", "CLAUDE_CWD", "INIT_CWD", "COPILOT_CWD", "PWD",
        "IX_CEVRIMDISI")


def _oge(onek: str, ad: str, deger) -> str:
    """deger None → öğe YOK · "" → boş öğe (`<x/>`) · int → 6 haneli."""
    if deger is None:
        return ""
    if deger == "":
        return f"<{onek}:{ad}/>"
    if isinstance(deger, str):                   # ham değer (ör. '²' — isdigit True, int() patlar)
        return f"<{onek}:{ad}>{deger}</{onek}:{ad}>"
    return f"<{onek}:{ad}>{deger:06d}</{onek}:{ad}>"


def dtel_xml(dt: str, uz, on=0, onek: str = "dtel") -> str:
    tip = f"<{onek}:dataType/>" if dt == "" else f"<{onek}:dataType>{dt}</{onek}:dataType>"
    return ('<?xml version="1.0" encoding="utf-8"?><blue:wbobj adtcore:version="active" '
            'adtcore:name="X" adtcore:type="DTEL/DE" xmlns:blue="http://www.sap.com/wbobj/dictionary/dtel" '
            'xmlns:adtcore="http://www.sap.com/adt/core">'
            f'<{onek}:dataElement xmlns:{onek}="http://www.sap.com/adt/dictionary/dataelements">'
            f'<{onek}:typeKind>domain</{onek}:typeKind><{onek}:typeName>X</{onek}:typeName>{tip}'
            + _oge(onek, "dataTypeLength", uz) + _oge(onek, "dataTypeDecimals", on)
            + f'</{onek}:dataElement></blue:wbobj>')


DTEL = {
    "zsd001_e_c10a": (200, dtel_xml("CHAR", 10)),
    "zsd001_e_c10b": (200, dtel_xml("CHAR", 10)),
    "zsd001_e_c20": (200, dtel_xml("CHAR", 20)),
    "zsd001_e_n10": (200, dtel_xml("NUMC", 10)),
    "zsd001_e_int4": (200, dtel_xml("INT4", 10)),
    "zsd001_e_hata": (500, ""),
    "/xns/e_a": (200, dtel_xml("CHAR", 12, onek="de")),
    "/xns/e_b": (200, dtel_xml("CHAR", 12, onek="de")),
    "/xns/e_bos": (200, dtel_xml("", 0, onek="de")),
    # F4 (düzeltme turu): öğe eksik/boş — eski kod 0 okuyordu (gerçek tip CHAR 40 / DEC 15,5 varsayımı)
    "zsd001_e_uzyok": (200, dtel_xml("CHAR", None)),
    "zsd001_e_uzbos": (200, dtel_xml("CHAR", "")),
    "zsd001_e_onyok": (200, dtel_xml("DEC", 15, None)),
    # Düzeltme turu 2: sıfır uzunluk dalı · GEOM_EWKB · ADT ad eşlemesi · '²'
    "zsd001_e_c0": (200, dtel_xml("CHAR", 0)),
    "zsd001_e_geoa": (200, dtel_xml("GEOM_EWKB", 0)),
    "zsd001_e_geob": (200, dtel_xml("GEOM_EWKB", 0)),
    "zsd001_e_utcl": (200, dtel_xml("UTCLONG", 27)),
    "zsd001_e_d16": (200, dtel_xml("DECFLOAT16", 16)),
    "zsd001_e_d34": (200, dtel_xml("DECFLOAT34", 34)),
    "zsd001_e_d16r": (200, dtel_xml("DF16_RAW", 16)),
    "zsd001_e_d34r": (200, dtel_xml("DF34_RAW", 34)),
    "zsd001_e_sup": (200, dtel_xml("CHAR", "²")),
}


def tablo(govde: str, ad: str = "zsd001_t_demo") -> str:
    satirlar = ["@EndUserText.label : 'Demo'",
                "@AbapCatalog.tableCategory : #TRANSPARENT",
                f"define table {ad} {{",
                "  key mandt : mandt not null;",
                "  key id : abap.numc(3) not null;"]
    return "\n".join(satirlar) + "\n" + govde + "}\n"


class Sunucu:
    """127.0.0.1 sahte ADT ucu: tablo kaynağı + veri öğesi XML'i; gerisi 404. İstekler listelenir."""

    def __init__(self):
        self.canli: dict[str, str] = {}
        self.istekler: list[tuple[str, str, str]] = []
        dis = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                dis.istekler.append(("GET", self.path, self.headers.get("Host", "")))
                yol = self.path.split("?", 1)[0]
                kod, govde, tur = 404, "", "text/plain"
                m = re.match(r"^/sap/bc/adt/ddic/tables/([^/]+)/source/main$", yol)
                if m and unquote(m.group(1)).lower() in dis.canli:
                    kod, govde = 200, dis.canli[unquote(m.group(1)).lower()]
                m = re.match(r"^/sap/bc/adt/ddic/dataelements/([^/]+)$", yol)
                if m and unquote(m.group(1)).lower() in DTEL:
                    kod, govde = DTEL[unquote(m.group(1)).lower()]
                    tur = "application/vnd.sap.adt.dataelements.v2+xml; charset=utf-8"
                b = govde.encode("utf-8")
                self.send_response(kod)
                self.send_header("Content-Type", tur)
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def log_message(self, *_a):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def env(self, kum: Path) -> dict:
        e = {k: v for k, v in os.environ.items() if k not in _SIL}
        e.update(ADT_SAP_URL=self.url, ADT_SAP_USER="fixture", ADT_SAP_PASSWORD="fixture",
                 ADT_SAP_CLIENT="100", ADT_SAP_LANGUAGE="EN", NO_PROXY="127.0.0.1,localhost",
                 no_proxy="127.0.0.1,localhost", CLAUDE_PROJECT_DIR=str(kum))
        return e

    def kapat(self):
        self.srv.shutdown()
        self.srv.server_close()


S: list[tuple[str, bool, str]] = []


def ekle(ad: str, ok: bool, detay: str) -> None:
    S.append((ad, bool(ok), detay))


_BEYAN = re.compile(r"^IX-GATE-STATUS:\s+gate=(\S+)\s+status=(\S+)\s+measured=(true|false)\s+reason=(\S+)\s*$", re.M)


def beyan(out: str):
    m = [b for b in _BEYAN.findall(out) if b[0] == _GATE]
    return m[-1] if m else None


def yaz(yol: Path, metin: str, crlf: bool = False, bom: bool = False) -> Path:
    yol.parent.mkdir(parents=True, exist_ok=True)
    veri = metin.replace("\n", "\r\n") if crlf else metin
    yol.write_bytes((b"\xef\xbb\xbf" if bom else b"") + veri.encode("utf-8"))
    return yol


def kos(kok: Path, kum: Path, srv: Sunucu, ad: str, canli: str, yerel: str, *argv: str,
        tablo_adi: str = "zsd001_t_demo", crlf: bool = False, bom: bool = False):
    srv.canli = {tablo_adi.lower(): canli}
    srv.istekler.clear()
    dosya = yaz(kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "tables" / f"{ad}.tabl.ddl", yerel, crlf, bom)
    r = subprocess.run([sys.executable, str(kok / "scripts" / "validators" / "check_table_field_drop.py"),
                        str(dosya), *argv], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120, cwd=str(kum), env=srv.env(kum))
    return r.returncode, r.stdout, r.stderr, list(srv.istekler), dosya


def dtel_get_sayisi(ist) -> int:
    return sum(1 for _m, y, _h in ist if "/ddic/dataelements/" in y)


def dogrudan(kok: Path, kum: Path, srv: Sunucu) -> list:
    tum_istek = []

    def k(ad, canli_g, yerel_g, *argv, **kw):
        tad = kw.get("tablo_adi", "zsd001_t_demo")
        rc, out, err, ist, _ = kos(kok, kum, srv, ad, tablo(canli_g, tad), tablo(yerel_g, tad), *argv, **kw)
        tum_istek.extend(ist)
        return rc, out, err, ist

    rc, out, err, _ = k("t1", "  cnt : abap.int4;\n", "  cnt : abap.int2;\n")
    ekle("T1", rc == 1 and "TÜR DEĞİŞTİ abap.int4 → abap.int2" in err and "measured=false" not in out,
         f"rc={rc} err={err[-300:]!r}")
    rc, out, err, _ = k("t2", "  note : abap.char(100);\n", "  note : abap.char(10);\n")
    ekle("T2", rc == 1 and "DARALMA abap.char(100) → abap.char(10) (CHAR(100) → CHAR(10))" in err,
         f"rc={rc} err={err[-300:]!r}")
    rc, out, err, _ = k("t3", "  qty : abap.dec(15,3);\n", "  qty : abap.dec( 13, 3 );\n")
    ekle("T3", rc == 1 and "DARALMA abap.dec(15,3) → abap.dec(13,3)" in err, f"rc={rc} err={err[-300:]!r}")
    rc, out, err, _ = k("t3b", "  qty : abap.dec(15,3);\n", "  qty : abap.dec(16,5);\n")
    ekle("T3b", rc == 1 and "DARALMA abap.dec(15,3) → abap.dec(16,5)" in err, f"rc={rc} err={err[-300:]!r}")
    rc, out, err, ist = k("t4", "  ref : zsd001_e_c10a;\n", "  ref : zsd001_e_c10b;\n")
    ekle("T4", rc == 0 and "[INFO]" in out and "fiziksel tip aynı" in out and dtel_get_sayisi(ist) == 2
         and beyan(out) == (_GATE, "OK", "true", "dtel-degisti-tip-ayni") and "[BLOCKER]" not in err,
         f"rc={rc} beyan={beyan(out)} get={dtel_get_sayisi(ist)} err={err[-200:]!r}")
    rc, out, err, _ = k("t5", "  ref : abap.char(10);\n", "  ref : zsd001_e_c10a;\n")
    ekle("T5", rc == 0 and "[INFO]" in out and beyan(out) == (_GATE, "OK", "true", "dtel-degisti-tip-ayni"),
         f"rc={rc} beyan={beyan(out)} err={err[-200:]!r}")
    rc, out, err, _ = k("t5b", "  cnt : abap.int4;\n", "  cnt : zsd001_e_int4;\n")
    ekle("T5b", rc == 0 and "[INFO]" in out and "(INT4 → INT4)" in out,
         f"rc={rc} out={out[-300:]!r} err={err[-200:]!r}")
    rc, out, err, _ = k("t6", "  note : abap.char(10);\n", "  note : abap.char(20);\n")
    ekle("T6", rc == 0 and "[WARNING]" in err and "GENİŞLEDİ" in err
         and beyan(out) == (_GATE, "FINDING", "true", "tip-genisleme"),
         f"rc={rc} beyan={beyan(out)} err={err[-200:]!r}")
    rc, out, err, _ = k("t6b", "  ref : zsd001_e_c10a;\n", "  ref : zsd001_e_c20;\n")
    ekle("T6b", rc == 0 and "[WARNING]" in err and "(CHAR(10) → CHAR(20))" in err, f"rc={rc} err={err[-200:]!r}")
    rc, out, err, _ = k("t7", "  ref : zsd001_e_c10a;\n", "  ref : zsd001_e_yok;\n")
    ekle("T7", rc == 1 and "ÖLÇÜLEMEDİ" in err and "dtel-get-http-404" in err
         and beyan(out) == (_GATE, "FAIL", "false", "fiziksel-tip-cozulemedi"),
         f"rc={rc} beyan={beyan(out)} err={err[-300:]!r}")
    rc, out, err, _ = k("t7b", "  ref : zsd001_e_c10a;\n", "  ref : zsd001_e_hata;\n")
    ekle("T7b", rc == 1 and "dtel-get-http-500" in err
         and beyan(out) == (_GATE, "FAIL", "false", "fiziksel-tip-cozulemedi"),
         f"rc={rc} beyan={beyan(out)} err={err[-300:]!r}")
    rc, out, err, _ = k("t8", "  note : abap.char(100);\n  ref : zsd001_e_c10a;\n",
                        "  note : abap.char(10);\n  ref : zsd001_e_yok;\n")
    ekle("T8", rc == 1 and "DARALMA" in err and "ÖLÇÜLEMEDİ" in err and "measured=false" not in out,
         f"rc={rc} out={out[-200:]!r} err={err[-300:]!r}")
    rc, out, err, _ = k("t9", "  eski : zsd001_e_c10a;\n  ref : zsd001_e_c10a;\n", "  ref : zsd001_e_yok;\n")
    ekle("T9", rc == 1 and "DROP" in err and "ÖLÇÜLEMEDİ" in err and "measured=false" not in out,
         f"rc={rc} out={out[-200:]!r} err={err[-300:]!r}")
    rc, out, err, _ = k("t10", "  eski : zsd001_e_c10a;\n  note : abap.char(10);\n", "  note : abap.char(20);\n",
                        "--ack-drop", "eski")
    ekle("T10", rc == 0 and "[ACK-WARNING]" in out and "[WARNING]" in err
         and beyan(out) == (_GATE, "FINDING", "true", "tip-genisleme"),
         f"rc={rc} beyan={beyan(out)} err={err[-200:]!r}")
    rc, out, err, _ = k("t10b", "  eski : zsd001_e_c10a;\n  note : abap.char(100);\n", "  note : abap.char(10);\n",
                        "--ack-drop", "eski")
    ekle("T10b", rc == 1 and "DARALMA" in err and "onaylıydı ama" in err, f"rc={rc} err={err[-300:]!r}")
    rc, out, err, ist = k("t11", "  note : abap.char(10);\n", "  note : abap.char( 10 );\n  yeni : zsd001_e_c20;\n")
    ekle("T11", rc == 0 and beyan(out) == (_GATE, "OK", "true", "additive-guvenli") and dtel_get_sayisi(ist) == 0,
         f"rc={rc} beyan={beyan(out)} get={dtel_get_sayisi(ist)}")
    ekle("T14", out.count("KAPSAM: bakılan = canlı DDL kaynağı") == 1 and "BAKILMAYAN: include/append" in out,
         f"out={out[:300]!r}")
    rc, out, err, _ = k("t12", "  ref : zsd001_e_c10a;\n", "  ref : zsd001_e_n10;\n")
    ekle("T12", rc == 1 and "TÜR DEĞİŞTİ zsd001_e_c10a → zsd001_e_n10 (CHAR(10) → NUMC(10))" in err,
         f"rc={rc} err={err[-300:]!r}")
    # T13 ÜÇÜNCÜ BAĞLAM: namespace'li tablo + DTEL, CRLF + BOM yerel dosya, `de:` önekli XML
    rc, out, err, ist = k("t13", "  /xns/fld : /xns/e_a;\n", "  /xns/fld : /xns/e_b;\n",
                          tablo_adi="/xns/t_demo", crlf=True, bom=True)
    ekle("T13a", rc == 0 and "[INFO]" in out and "(CHAR(12) → CHAR(12))" in out
         and any("/ddic/tables/%2Fxns%2Ft_demo/" in y for _m, y, _h in ist)
         and any("/ddic/dataelements/%2Fxns%2Fe_b" in y for _m, y, _h in ist),
         f"rc={rc} out={out[-300:]!r} err={err[-200:]!r} ist={[y for _m, y, _h in ist]}")
    rc, out, err, _ = k("t13b", "  /xns/fld : /xns/e_a;\n", "  /xns/fld : /xns/e_bos;\n",
                        tablo_adi="/xns/t_demo", crlf=True, bom=True)
    ekle("T13b", rc == 1 and "dtel-veri-tipi-yok" in err
         and beyan(out) == (_GATE, "FAIL", "false", "fiziksel-tip-cozulemedi"),
         f"rc={rc} beyan={beyan(out)} err={err[-300:]!r}")
    rc, out, err, _ = k("t15", "  txt : abap.string(256);\n", "  txt : abap.string(0);\n")
    ekle("T15", rc == 0 and "[WARNING]" in err and "(STRING(256) → STRING)" in err,
         f"rc={rc} err={err[-300:]!r}")
    # F4 (⚠SIKILAŞTIRMA): uzunluk/ondalık öğesi yok ya da boş ⇒ ÇÖZÜLEMEDİ (eski: 0 ⇒ "genişleme" rc 0)
    rc, out, err, _ = k("t17", "  ref : zsd001_e_uzyok;\n", "  ref : abap.char(10);\n")
    ekle("T17", rc == 1 and "dtel-uzunluk-yok" in err and beyan(out) == (_GATE, "FAIL", "false", "fiziksel-tip-cozulemedi"),
         f"rc={rc} beyan={beyan(out)} err={err[-300:]!r}")
    rc, out, err, _ = k("t17b", "  ref : zsd001_e_uzbos;\n", "  ref : abap.char(10);\n")
    ekle("T17b", rc == 1 and "dtel-uzunluk-yok" in err, f"rc={rc} err={err[-300:]!r}")
    rc, out, err, _ = k("t18", "  qty : zsd001_e_onyok;\n", "  qty : abap.dec(16,0);\n")
    ekle("T18", rc == 1 and "dtel-ondalik-yok" in err, f"rc={rc} err={err[-300:]!r}")
    # Düzeltme turu 2
    rc, out, err, _ = k("t19", "  ref : zsd001_e_c0;\n", "  ref : abap.char(10);\n")
    ekle("T19", rc == 1 and "dtel-uzunluk-yok" in err, f"rc={rc} err={err[-300:]!r}")
    rc, out, err, _ = k("t20", "  geo : zsd001_e_geoa;\n", "  geo : zsd001_e_geob;\n")
    ekle("T20", rc == 0 and "[INFO]" in out and "(GEOM_EWKB → GEOM_EWKB)" in out,
         f"rc={rc} out={out[-300:]!r} err={err[-300:]!r}")
    rc, out, err, _ = k("t21", "  ts : abap.utclong;\n", "  ts : zsd001_e_utcl;\n")
    ekle("T21", rc == 0 and "[INFO]" in out and "(UTCLONG → UTCLONG)" in out,
         f"rc={rc} out={out[-300:]!r} err={err[-300:]!r}")
    rc, out, err, _ = k("t22", "  df : abap.decfloat16;\n", "  df : zsd001_e_d16;\n")
    ekle("T22", rc == 0 and "[INFO]" in out and "(DECFLOAT16 → DECFLOAT16)" in out,
         f"rc={rc} out={out[-300:]!r} err={err[-300:]!r}")
    rc, out, err, _ = k("t23", "  df : abap.decfloat34;\n", "  df : zsd001_e_d34;\n")
    ekle("T23", rc == 0 and "[INFO]" in out and "(DECFLOAT34 → DECFLOAT34)" in out,
         f"rc={rc} out={out[-300:]!r} err={err[-300:]!r}")
    rc, out, err, _ = k("t24", "  ref : zsd001_e_sup;\n", "  ref : abap.char(10);\n")
    ekle("T24", rc == 1 and "dtel-uzunluk-yok" in err and "Traceback" not in err, f"rc={rc} err={err[-300:]!r}")
    # Düzeltme turu 3
    rc, out, err, _ = k("t25", "  df : abap.df16_raw;\n", "  df : zsd001_e_d16r;\n")
    ekle("T25", rc == 0 and "[INFO]" in out and "(DF16_RAW → DF16_RAW)" in out,
         f"rc={rc} out={out[-300:]!r} err={err[-300:]!r}")
    rc, out, err, _ = k("t26", "  df : abap.decfloat16;\n", "  df : zsd001_e_d34;\n")
    ekle("T26", rc == 1 and "TÜR DEĞİŞTİ abap.decfloat16 → zsd001_e_d34 (DECFLOAT16 → DECFLOAT34)" in err,
         f"rc={rc} err={err[-300:]!r}")
    rc, out, err, _ = k("t27", "  df : abap.decfloat16;\n", "  df : zsd001_e_d16r;\n")
    ekle("T27", rc == 1 and "TÜR DEĞİŞTİ abap.decfloat16 → zsd001_e_d16r (DECFLOAT16 → DF16_RAW)" in err,
         f"rc={rc} err={err[-300:]!r}")
    rc, out, err, _ = k("t28", "  df : abap.df34_raw;\n", "  df : zsd001_e_d34r;\n")
    ekle("T28", rc == 1 and "değişken uzunluklu tipte uzunluk yazılmamış" in err
         and "measured=false" in out, f"rc={rc} out={out[-200:]!r} err={err[-300:]!r}")
    return tum_istek


def reviewer(kok: Path, kum: Path, srv: Sunucu) -> list:
    tum = []

    def rv(ad, canli_g, yerel_g):
        srv.canli = {"zsd001_t_demo": tablo(canli_g)}
        srv.istekler.clear()
        dosya = yaz(kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "tables" / f"{ad}.tabl.ddl", tablo(yerel_g))
        r = subprocess.run([sys.executable, str(kok / "scripts" / "validators" / "run_review.py"), "--task",
                            "table_update", "--artifact", str(dosya), "--json"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300, cwd=str(kum), env=srv.env(kum))
        tum.extend(srv.istekler)
        try:
            js = json.loads(r.stdout[r.stdout.index("{"):])
        except Exception:
            return None, None, f"rc={r.returncode} json yok: {r.stdout[-200:]!r} {r.stderr[-200:]!r}"
        kay = next((x for x in js.get("results", []) if x["validator"] == "check_table_field_drop.py"), None)
        return js, kay, (f"run_review rc={r.returncode} verdict={js.get('verdict')} "
                         f"drop-guard={kay and kay['status']} sessiz={js.get('sessiz_bulgu_gates')}")

    js, kay, d = rv("r1", "  note : abap.char(10);\n", "  note : abap.char(20);\n")
    ekle("R1", kay is not None and kay["status"] == "PASS" and "[WARNING]" in kay["stderr"]
         and "check_table_field_drop.py" in (js.get("sessiz_bulgu_gates") or []), d)
    print(f"  · R1 ölçüm: {d}")
    js, kay, d = rv("r2", "  ref : zsd001_e_c10a;\n", "  ref : zsd001_e_yok;\n")
    ekle("R2", kay is not None and kay["status"] == "FAIL" and kay["severity"] == "BLOCKER"
         and js.get("verdict") == "BLOCKER", d)
    print(f"  · R2 ölçüm: {d}")
    js, kay, d = rv("r3", "  note : abap.char(100);\n", "  note : abap.char(10);\n")
    ekle("R3", kay is not None and kay["status"] == "FAIL" and js.get("verdict") == "BLOCKER", d)
    print(f"  · R3 ölçüm: {d}")
    return tum


def checklist(kok: Path, kum: Path, srv: Sunucu) -> list:
    tum = []
    spec = importlib.util.spec_from_file_location("_cc_tfd", kok / "scripts" / "validators" / "checklist_check.py")
    cc = importlib.util.module_from_spec(spec)
    sys.modules["_cc_tfd"] = cc          # dataclass modülü sys.modules'te arar
    eski_argv = sys.argv
    try:
        sys.argv = ["checklist_check.py"]
        spec.loader.exec_module(cc)  # type: ignore[union-attr]
    finally:
        sys.argv = eski_argv

    @contextlib.contextmanager
    def ortam():
        # env ÖNCE hesaplanır: clear() sonrası hesaplanırsa SYSTEMROOT/PATH düşer, Windows'ta alt
        # sürecin soketi açılamaz ⇒ "bağlantı yok" measured=false (ilk kurulumda böyle sahte K1/K3).
        # cwd kum: k_be16 alt süreci cwd vermez; şablon `.conn_adt` proje köküne yazılmasın.
        yeni, eski, eski_cwd = srv.env(kum), dict(os.environ), os.getcwd()
        try:
            os.environ.clear()
            os.environ.update(yeni)
            os.chdir(kum)
            yield
        finally:
            os.chdir(eski_cwd)
            os.environ.clear()
            os.environ.update(eski)

    def kb(ad, canli_g, yerel_g):
        srv.canli = {"zsd001_t_demo": tablo(canli_g)}
        srv.istekler.clear()
        dosya = yaz(kum / "SOURCE_CODES" / "SD" / "ZSD001_CLC" / "tables" / f"{ad}.tabl.ddl", tablo(yerel_g))
        with ortam():
            b = cc.k_be16(types.SimpleNamespace(yol=dosya), types.SimpleNamespace(sap_kok=kum, repo=kum))
        tum.extend(srv.istekler)
        sonuc = "PASS" if not b else b[0].durum
        return sonuc, f"BE-16 sonuc={sonuc} kanit={[x.mesaj[:100] for x in b]}"

    s, d = kb("k1", "  note : abap.char(10);\n", "  note : abap.char(20);\n")
    ekle("K1", s == "PASS", d)
    print(f"  · K1 ölçüm: {d}")
    s, d = kb("k2", "  ref : zsd001_e_c10a;\n", "  ref : zsd001_e_yok;\n")
    ekle("K2", s == "ÖLÇÜLEMEDİ", d)
    print(f"  · K2 ölçüm: {d}")
    s, d = kb("k3", "  note : abap.char(100);\n  ref : zsd001_e_c10a;\n",
              "  note : abap.char(10);\n  ref : zsd001_e_yok;\n")
    ekle("K3", s == "FAIL", d)
    print(f"  · K3 ölçüm: {d}")
    return tum


def main(kok: Path) -> int:
    kum = Path(tempfile.mkdtemp(prefix="tfd_kum_"))
    srv = Sunucu()
    try:
        yaz(kum / "project.yaml", "source_root: SOURCE_CODES\nsap_profile: s4_private\n")
        ist = dogrudan(kok, kum, srv)
        ist += reviewer(kok, kum, srv)
        ist += checklist(kok, kum, srv)
        host = srv.url.split("//", 1)[1]
        izinli = ("/sap/bc/adt/ddic/tables/", "/sap/bc/adt/ddic/dataelements/")
        yabanci = [(m, y, h) for m, y, h in ist if h != host]
        drop_disi = sorted({y.split("?")[0] for _m, y, _h in ist if not y.startswith(izinli)})
        ekle("T16", bool(ist) and not yabanci and not (kum / ".conn_adt").exists(),
             f"istek={len(ist)} yabanci={yabanci[:3]} conn={(kum / '.conn_adt').exists()}")
        if drop_disi:
            print(f"  · not: zincirin öteki gate'lerinin istekleri (hepsi sahte uca): {drop_disi[:6]}")
    finally:
        srv.kapat()
        shutil.rmtree(kum, ignore_errors=True)
    for ad, ok, d in S:
        print(f"  [{'PASS' if ok else 'FAIL'}] {ad}" + ("" if ok else f"\n         -> {d}"))
    n = sum(1 for _, ok, _ in S if ok)
    print(f"\n{n}/{len(S)} OK")
    return 0 if n == len(S) else 1


# ─────────────────────────────────────────────────────────────────────────────
# MUTASYON — her kural için kontrol grubu. Kum: ağacın `scripts/` kopyası + bu fixture;
# çapa tam 1 kez geçmeli (yoksa 3), düşen küme ilan edilenle TAM aynı olmalı (yoksa 2).
# ─────────────────────────────────────────────────────────────────────────────
_D = "scripts/validators/check_table_field_drop.py"
_BLK = "    tip_blocker = [h for h in tip_hukmu if h[3] in ('daralma', 'tur', 'olculemedi')]\n"
MUTASYONLAR = {
    # tip konumunu eski gibi ilk ad parçasında kes (#408'in kendisi)
    "--mutasyon-tip-kesik": (
        _D, "    + r'(?:\\s*\\.\\s*[A-Za-z0-9_]+(?:\\s*\\(\\s*\\d+\\s*(?:,\\s*\\d+\\s*)?\\))?)?)',\n",
        "    + r')',\n",
        # K1 (genişleme → PASS) düşmez: kesik tipte değişiklik görünmez, sonuç yine PASS. T8/K3 düşer:
        # daralma görünmez ⇒ tek neden çözülemeyen DTEL kalır ⇒ measured=false basılır.
        # T21-T23/T25-T28: `abap.utclong`/`abap.decfloat16`/`abap.decfloat34`/`abap.df16_raw`/`abap.df34_raw` kesilince `abap` kalır.
        {"T1", "T2", "T3", "T3b", "T5", "T5b", "T6", "T8", "T10", "T10b", "T15", "T21", "T22", "T23",
         "T25", "T26", "T27", "T28", "R1", "R3", "K3"}),
    # aynı fiziksel tip yine BLOCKER (gevşetme geri alınır)
    "--mutasyon-ayni-blocker": (
        _D, _BLK, _BLK.replace("'olculemedi')", "'olculemedi', 'ayni')"),
        {"T4", "T5", "T5b", "T13a", "T20", "T21", "T22", "T23", "T25"}),
    # genişleme BLOCKER
    "--mutasyon-genisleme-blocker": (
        _D, _BLK, _BLK.replace("'olculemedi')", "'olculemedi', 'genisleme')"),
        {"T6", "T6b", "T10", "T15", "R1", "K1"}),
    # daralma genişleme sayılır
    "--mutasyon-daralma-gecer": (
        _D, "        return 'genisleme'\n    return 'daralma'\n",
        "        return 'genisleme'\n    return 'genisleme'\n",
        {"T2", "T3", "T3b", "T8", "T10b", "R3", "K3"}),
    # çözülemeyen tip bloklamaz
    "--mutasyon-olculemedi-gecer": (
        _D, _BLK, _BLK.replace(", 'olculemedi')", ")"),
        {"T7", "T7b", "T8", "T9", "T13b", "T17", "T17b", "T18", "T19", "T24", "T28", "R2", "K2"}),   # T8/T17*/T18: ÖLÇÜLEMEDİ satırı da kaybolur
    # measured=false ölçülmüş BLOCKER yanında da basılır (lider pini)
    "--mutasyon-measured-genis": (
        _D, "    if not unack_dropped and all(h[3] == 'olculemedi' for h in tip_blocker):\n",
        "    if any(h[3] == 'olculemedi' for h in tip_blocker):\n",
        {"T8", "T9", "K3"}),
    # measured=false hiç basılmaz (2. gevşetme hücresi yok)
    "--mutasyon-measured-yok": (
        _D, "        gate_status(_GATE, 'FAIL', False, 'fiziksel-tip-cozulemedi')\n",
        "        pass\n",
        {"T7", "T7b", "T13b", "T17", "T28", "K2"}),   # T17/T28 measured=false beyanını da ister
    # sabit uzunluklu tip kümesi körleşir
    "--mutasyon-sabit-kor": (
        _D, "    if dt in SABIT_UZUNLUK:\n        return 'ayni'\n",
        "    if False:\n        return 'ayni'\n",
        {"T5b", "T21", "T22", "T23", "T25"}),   # T21-T23/T25: yerleşikte uzunluk yok, sabit uzunluklu
    # STRING uzunluk 0 = sınırsız kuralı körleşir
    "--mutasyon-sinirsiz-kor": (_D, "    if dt in SINIRSIZ_SIFIR:\n", "    if False:\n", {"T15"}),
    # tam sayı hanesi yerine yalnız toplam uzunluk
    "--mutasyon-ondalik-kor": (
        _D, "    tam_e, tam_y = uz_e - on_e, uz_y - on_y", "    tam_e, tam_y = uz_e, uz_y", {"T3b"}),
    # ack tip blocker'ını da affeder
    "--mutasyon-ack-tip": (
        _D, "    if not unack_dropped and not tip_blocker:\n",
        "    if not unack_dropped and (not tip_blocker or ack_dropped):\n",
        {"T10b"}),
    # kapsam beyanı kalkar
    "--mutasyon-kapsam-yok": (_D, "    print(_KAPSAM_BEYANI)\n", "", {"T14"}),
    # F4: eksik/boş uzunluk yine 0 okunur (eski fail-open; blok TÜMDEN kalkar — yalnız ilk
    # koşulu kapatmak `int(None)` çökmesi üretirdi, çökme ≠ ölçülen kaçak)
    "--mutasyon-uzunluk-yok-gecer": (
        _D, ("    if dt not in SABIT_UZUNLUK:\n        if uz is None:\n"
             "            return None, 'dtel-uzunluk-yok'\n        if dt not in SINIRSIZ_SIFIR and uz == 0:\n"
             "            return None, 'dtel-uzunluk-yok'\n"),
        "    pass\n",
        {"T17", "T17b", "T19", "T24"}),
    # düzeltme turu 2: yalnız sıfır-uzunluk dalı
    "--mutasyon-sifir-uzunluk-gecer": (
        _D, "        if dt not in SINIRSIZ_SIFIR and uz == 0:\n", "        if False:\n", {"T19"}),
    # GEOM_EWKB sınırsız sayılmaz (sahte ÖLÇÜLEMEDİ geri gelir)
    "--mutasyon-geom-kor": (
        _D, "SINIRSIZ_SIFIR = frozenset({'STRING', 'RAWSTRING', 'GEOM_EWKB'})",
        "SINIRSIZ_SIFIR = frozenset({'STRING', 'RAWSTRING'})", {"T20"}),
    # DECFLOAT34 / DF16_RAW sabit uzunluklu sayılmaz (düzeltme turu 3)
    "--mutasyon-d34-sabit-yok": (
        _D, "'DECFLOAT16', 'DECFLOAT34',", "'DECFLOAT16',", {"T23", "T26"}),   # T26: gösterim DECFLOAT34(34)
    "--mutasyon-df16raw-sabit-yok": (
        _D, "                           'DF16_RAW', 'ACCP', 'PREC'})",
        "                           'ACCP', 'PREC'})", {"T25", "T27"}),   # T27: gösterim DF16_RAW(16)
    # tür kıyası körleşir (DECFLOAT16 ≠ DECFLOAT34 ≠ DF16_RAW çivisi)
    "--mutasyon-tur-kor": (
        _D, "    if eski[0] != yeni[0]:\n        return 'tur'\n", "    if False:\n        return 'tur'\n",
        {"T1", "T12", "T26", "T27"}),
    # UTCLONG sabit uzunluklu sayılmaz
    "--mutasyon-utclong-sabit-yok": (
        _D, "'UTCL', 'UTCLONG', 'DECFLOAT16',", "'UTCL', 'DECFLOAT16',", {"T21"}),
    # tam rakam eşleşmesi yerine isdigit (Ö1: '²' yakalanmamış ValueError)
    "--mutasyon-isdigit": (
        _D, "_RAKAM_RE.fullmatch(ham)", "ham.isdigit()", {"T24"}),
    # F4: eksik ondalık yine 0 okunur
    "--mutasyon-ondalik-yok-gecer": (
        _D, "    if dt in ONDALIKLI and on is None:\n",
        "    if False:\n",
        {"T18"}),
}
KIPLER = sorted(MUTASYONLAR)


def _mutasyon(kip: str) -> int:
    yol, eski, yeni, beklenen = MUTASYONLAR[kip]
    kum = Path(tempfile.mkdtemp(prefix="tfd_mut_"))
    try:
        shutil.copytree(REPO / "scripts", kum / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
        hedef = kum / "tests" / "fixtures" / BURASI.name
        shutil.copytree(BURASI, hedef, ignore=shutil.ignore_patterns("__pycache__"))
        dosya = kum / yol
        asil = dosya.read_bytes().decode("utf-8")
        if asil.count(eski) != 1:
            print(f"[KURULAMADI] {kip} -> capa {asil.count(eski)} kez ({yol})")
            return 3
        mutant = asil.replace(eski, yeni, 1)
        try:
            compile(mutant, str(dosya), "exec")
        except SyntaxError as exc:
            print(f"[KURULAMADI] {kip} -> mutant derlenmedi: {exc}")
            return 3
        dosya.write_bytes(mutant.encode("utf-8"))
        r = subprocess.run([sys.executable, str(hedef / "run.py"), "--kok", str(kum)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=900, cwd=str(kum))
        m = re.search(r"^(\d+)/(\d+) OK$", r.stdout, re.M)
        if not m:
            son = [x for x in (r.stdout + r.stderr).splitlines() if x.strip()][-1:] or ["-"]
            print(f"[ALT-SUREC SAYI VERMEDI] {kip} rc={r.returncode} son={son[0][:160]}")
            return 3
        dusen = {x.split()[1] for x in r.stdout.splitlines() if x.strip().startswith("[FAIL]")}
        print(f"{kip}: {m.group(0)} · dusen={sorted(dusen)} · ilan={sorted(beklenen)}")
        if dusen == beklenen:
            print("MUTASYON DUSTU (ilan edilen kume TAM)")
            return 1
        print(f"[SAPMA] fazla={sorted(dusen - beklenen)} eksik={sorted(beklenen - dusen)}")
        return 2
    finally:
        shutil.rmtree(kum, ignore_errors=True)


if __name__ == "__main__":
    _kipler = [a for a in sys.argv[1:] if a.startswith("--mutasyon")]
    if _kipler:
        if len(_kipler) != 1 or _kipler[0] not in MUTASYONLAR:
            print(f"[KULLANIM] gecerli kipler: {KIPLER}")
            sys.exit(2)
        sys.exit(_mutasyon(_kipler[0]))
    _kok = REPO
    if "--kok" in sys.argv:
        _kok = Path(sys.argv[sys.argv.index("--kok") + 1]).resolve()
    sys.exit(main(_kok))
