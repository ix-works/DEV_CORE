#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aciklama_412_retry — `sap_set_object_description.py` PUT 412 retry + PUT sonrası inaktif kalma (Q175).

CANLI ÖLÇÜLEN MEKANİZMA (2026-09-13, DDLS, gateway; ham gövdeler genericize edilip buraya alındı):
  · envelope GET (parametresiz) ETag'i = aktif sürümünki; sunucu PUT'ta başka bir "object ETag" ister
  · PUT → 412 `SADT_RESOURCE 043` "Client ETag <A> does not match the object ETag <B>" (obje DÜŞMEZ)
  · <B> ile, YENİ lock döngüsünde tek retry → 200, boş gövde → obje HEMEN aktive-bekleyen listesinde
  · aktivasyon → `activationExecuted="true"` → liste temiz, açıklama aktif sürümde

SAHTE SUNUCU bu kuralları MODELLER (senaryo listesi değil): PUT'un `If-Match`'i sunucunun beklediği
ETag'e eşitse 200, değilse 412 döner; 200 objeyi (ayar kapatılmadıkça) inaktife düşürür. Gerçek
`sap_adt_lib.SAPADTClient`'ın `activate_object` · `_parse_activation_response` · `get_inactive_objects`
· `_request_with_csrf_retry` · `_get_headers` metotları KOŞAR; yalnız HTTP oturumu, lock/unlock ve
423 teşhisi sahtedir. Script kaynağı bellekte `exec` edilir (`__file__` gerçek yola çivili), yazma yok.

KULLANIM:
    python tests/fixtures/aciklama_412_retry/run.py                  # 17 vektör + 12 mutasyon, exit 0
    python tests/fixtures/aciklama_412_retry/run.py --kaynak <dosya> # vektörleri BAŞKA kaynakta koş
                                                                     # (eski-kod karşıtlığı; mutasyon yok)
Eski kod karşıtlığı (reçete B48): `git show <taban>:scripts/sap_set_object_description.py > <kum>/taban.py`
→ `--kaynak <kum>/taban.py` → yalnız V5 · V10 · V13 · V15 geçer (4/17).
⚠ V16 = GEVŞETME SINIRI: sunucunun ETag'iyle retry `If-Match` korumasını atlar; retry yalnız envelope
ilk okumadan beri bayt bayt aynıysa yapılır. V16/M12 SİLİNMEZ.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
SCRIPTS = KOK / "scripts"
HEDEF = SCRIPTS / "sap_set_object_description.py"
IZ_ISARETI = "@@Q175IZ@@"

ETAG_AKTIF = "200001010000000013SAHTEaktifETAGxxxxxxxxxx="
ETAG_OBJE = "200001010000000003SAHTEobjeETAGxxxxxxxxxxx="
KAYNAK_ETAG = "200001010000000011"          # atom:link etag'i (source/main) — envelope ETag'i DEĞİL
ESKI_DESC = "Eski Demo Aciklama"
YENI_DESC = "Yeni Demo Açıklama"

# ─────────────────────────────────────────────────────────────────────────────
# MUTASYONLAR — (ad, eski_parca, yeni_parca). Parça kaynakta TAM 1 kez geçmeli; yoksa KURULAMADI.
# ─────────────────────────────────────────────────────────────────────────────
MUTASYONLAR = [
    ("M1 412 retry dalı kaldırıldı",
     "    if status == 412:\n        server_etag = _etag_from_412(text)",
     "    if False:\n        server_etag = _etag_from_412(text)"),
    ("M2 retry ESKİ ETag ile (412 gövdesi yok sayıldı)",
     "data, server_etag,\n", "data, etag,\n"),
    ("M3 retry sınırsız (döngü koruması yok)",
     "        if status == 412:\n            print(f\"[FAIL] retry de HTTP 412",
     "        while status == 412:\n            status, text, eff_transport = _lock_put_unlock("
     "adt, url, full, ctype, data, server_etag, args.transport)\n"
     "        if status == 412:\n            print(f\"[FAIL] retry de HTTP 412"),
    ("M4 aktivasyon dalı kaldırıldı",
     "    if listed:\n        print(f\"[INFO] açıklama PUT'u",
     "    if False:\n        print(f\"[INFO] açıklama PUT'u"),
    ("M5 aktivasyon sonrası bağımsız liste okuması kaldırıldı (yanıta güven)",
     "        listed, trace = _inactive_listed(adt, name, url)\n        if listed is not False:",
     "        listed, trace = False, \"\"\n        if listed is not False:"),
    ("M6 readback aktif sürüm yerine parametresiz GET (eski readback)",
     "params={\"version\": \"active\"},\n                         timeout",
     "\n                         timeout"),
    ("M7 412 ETag'i yanlış alandan (T100KEY-V1 = gönderilen)",
     "r'<entry key=\"T100KEY-V2\">", "r'<entry key=\"T100KEY-V1\">"),
    ("M8 LOCK ile PUT arasına GET girdi (423 sınıfı sıra bozumu)",
     "        headers = adt._get_headers(ctype, ctype)\n",
     "        adt.session.get(full, headers={\"Accept\": \"application/*\"}, "
     "timeout=adt.timeout_default)\n        headers = adt._get_headers(ctype, ctype)\n"),
    ("M9 lock döngüsünde UNLOCK atlandı",
     "            adt.unlock_object(url, lock_handle)", "            pass"),
    ("M10 --force-put yok sayıldı (aynı metin daima NOOP)",
     "        if not args.force_put:", "        if True:"),
    ("M11 URI eşleşmesi sınırsız önek (komşu obje eşleşir)",
     "e_uri.startswith(root + \"/\")", "e_uri.startswith(root)"),
    ("M12 ⚠GEVŞETME SINIRI kaldırıldı: envelope değişmiş olsa da retry",
     "(fresh.text or \"\") != body", "False"),
]


# ═════════════════════════════════════════════════════════════════════════════
# SÜRÜCÜ (alt süreç) — sahte sunucu + script exec
# ═════════════════════════════════════════════════════════════════════════════
class _Yanit:
    def __init__(self, kod, metin="", basliklar=None, url=""):
        self.status_code = kod
        self.text = metin
        self.headers = basliklar or {}
        self.cookies = None
        self.url = url


def _govde_412(istemci, obje, bicim):
    if bicim == "parse_yok":
        return ('<?xml version="1.0" encoding="utf-8"?><exc:exception xmlns:exc="http://www.sap.com/'
                'abapxml/types/communicationframework"><namespace id="com.sap.adt"/><type id="'
                'ExceptionPreconditionFailed"/><message lang="EN">Precondition failed</message>'
                '</exc:exception>')
    if bicim == "ayni":
        obje = istemci
    msg = f"Client ETag {istemci} does not match the object ETag {obje} in the server"
    return ('<?xml version="1.0" encoding="utf-8"?><exc:exception xmlns:exc="http://www.sap.com/abapxml/'
            'types/communicationframework"><namespace id="com.sap.adt"/><type id="ExceptionPrecondition'
            f'Failed"/><message lang="EN">{msg}</message><localizedMessage lang="TR">{msg}'
            '</localizedMessage><properties><entry key="com.sap.adt.communicationFramework.subType">'
            'IfMatch</entry><entry key="T100KEY-ID">SADT_RESOURCE</entry><entry key="T100KEY-NO">043'
            f'</entry><entry key="T100KEY-V1">{istemci}</entry><entry key="T100KEY-V2">{obje}</entry>'
            '</properties></exc:exception>')


def _envelope(ad, tip_kodu, surum, desc):
    return ('<?xml version="1.0" encoding="utf-8"?><ddl:ddlSource adtcore:responsible="SAHTE_KULLANICI" '
            f'adtcore:masterLanguage="TR" adtcore:name="{ad}" adtcore:type="{tip_kodu}" '
            f'adtcore:version="{surum}" adtcore:description="{desc}" adtcore:language="TR" '
            'xmlns:ddl="http://www.sap.com/adt/ddic/ddlsources" xmlns:adtcore="http://www.sap.com/adt/core">'
            f'<atom:link href="source/main" rel="http://www.sap.com/adt/relations/source" etag="{KAYNAK_ETAG}"'
            ' xmlns:atom="http://www.w3.org/2005/Atom"/></ddl:ddlSource>')


def _wl_girdi(uri, tip, ad):
    return ('<ioc:entry><ioc:object ioc:user="SAHTE" ioc:deleted="false"><ioc:ref '
            f'adtcore:uri="{uri}" adtcore:type="{tip}" adtcore:name="{ad}" '
            'xmlns:adtcore="http://www.sap.com/adt/core"/></ioc:object><ioc:transport/></ioc:entry>')


class _Sunucu:
    """ETag kuralını + inaktif sürümü + aktive-bekleyen listesini modelleyen sahte ADT sunucusu."""

    def __init__(self, s):
        self.s = s
        self.sinif = s.get("tip") == "class"
        self.ad = "ZDEMO_CL_ORNEK" if self.sinif else "ZDEMO_DDL_ORNEK"
        self.url = ("/sap/bc/adt/oo/classes/zdemo_cl_ornek" if self.sinif
                    else "/sap/bc/adt/ddic/ddl/sources/zdemo_ddl_ornek")
        self.tip_kodu = "CLAS/OC" if self.sinif else "DDLS/DF"
        self.aktif_desc = s.get("mevcut_desc", ESKI_DESC)
        self.inaktif_desc = None
        self.inaktif = False
        self.bekledigi = ETAG_AKTIF if s.get("sunucu_aktif_etag_kabul") else ETAG_OBJE
        self.olaylar: list = []
        self.put_sayisi = 0
        self.lock_sayisi = 0

    # ── HTTP ────────────────────────────────────────────────────────────────
    def _yol(self, url):
        if "://" not in url:
            return url
        return "/" + url.split("://", 1)[1].split("/", 1)[-1]

    def get(self, url, headers=None, params=None, timeout=None, **kw):
        yol = self._yol(url)
        surum = (params or {}).get("version")
        self.olaylar.append(["GET", yol, surum])
        if yol != self.url:
            return _Yanit(404, "yok", url=url)
        if surum == "active":
            desc = self.aktif_desc
        elif self.inaktif and surum in (None, "inactive"):
            desc = self.inaktif_desc
        else:
            desc = self.aktif_desc
        etag = ETAG_OBJE if surum == "inactive" else ETAG_AKTIF
        return _Yanit(200, _envelope(self.ad, self.tip_kodu, surum or "active", desc),
                      {"ETag": etag, "Content-Type": "application/vnd.sap.adt.ddic.ddlsource.v1+xml"},
                      url=url)

    def put(self, url, headers=None, params=None, data=None, timeout=None, **kw):
        self.put_sayisi += 1
        ifm = (headers or {}).get("If-Match")
        lh = (params or {}).get("lockHandle")
        if self.put_sayisi > 6:                       # sınırsız retry mutasyonunu bitir
            self.olaylar.append(["PUT", ifm, lh, 500])
            return _Yanit(500, "sahte sunucu: PUT siniri")
        if self.s.get("put_423"):
            self.olaylar.append(["PUT", ifm, lh, 423])
            return _Yanit(423, "Resource is not locked (sahte)")
        if ifm != self.bekledigi or self.s.get("hep_412"):
            self.olaylar.append(["PUT", ifm, lh, 412])
            if self.s.get("eszamanli"):               # başka biri araya yazdı
                self.aktif_desc = "Baska Kullanici Degistirdi"
            return _Yanit(412, _govde_412(ifm, self.bekledigi, self.s.get("govde_412", "normal")))
        yeni = (data or b"").decode("utf-8")
        import re as _re
        m = _re.search(r'adtcore:description="([^"]*)"', yeni)
        desc = m.group(1) if m else None
        if self.s.get("inaktife_dusmez"):
            self.aktif_desc = desc
        else:
            self.inaktif, self.inaktif_desc = True, desc
        self.olaylar.append(["PUT", ifm, lh, 200])
        return _Yanit(200, "")

    def request(self, method, url, headers=None, timeout=None, **kw):
        yol = self._yol(url)
        if method == "get" and yol == "/sap/bc/adt/activation/inactiveobjects":
            if self.s.get("worklist") == "500":
                self.olaylar.append(["WL", 500])
                return _Yanit(500, "sahte hata")
            girdiler = [_wl_girdi("/sap/bc/adt/ddic/ddl/sources/zdemo_ddl_ornek2", "DDLS/DF",
                                  "ZDEMO_DDL_ORNEK2"),
                        _wl_girdi("/sap/bc/adt/oo/classes/zdemo_cl_baska", "CLAS/OC", "ZDEMO_CL_BASKA")]
            if self.inaktif and self.s.get("worklist") != "gizli":
                if self.sinif:
                    girdiler.append(_wl_girdi(self.url + "/source/main#type=CLAS%2FOM;name=YAP",
                                              "CLAS/OM", "YAP"))
                else:
                    girdiler.append(_wl_girdi(self.url, self.tip_kodu, self.ad))
            govde = ('<?xml version="1.0" encoding="utf-8"?><ioc:inactiveObjects xmlns:ioc="http://www.sap.'
                     'com/abapxml/inactiveCtsObjects"><ioc:entry><ioc:object/><ioc:transport ioc:user="SAHTE"'
                     ' ioc:linked="false"><ioc:ref adtcore:uri="/sap/bc/adt/cts/transportrequests/SAHK900001"'
                     ' adtcore:type="/RQ" adtcore:name="SAHK900001" xmlns:adtcore="http://www.sap.com/adt/core"'
                     '/></ioc:transport></ioc:entry>' + "".join(girdiler) + "</ioc:inactiveObjects>")
            self.olaylar.append(["WL", 200, self.inaktif])
            return _Yanit(200, govde, url=url)
        if method == "post" and yol == "/sap/bc/adt/activation":
            govde_ist = kw.get("data") or ""
            self.olaylar.append(["POST", yol, (kw.get("params") or {}).get("preauditRequested"),
                                 self.tip_kodu in govde_ist and self.url in govde_ist])
            kip = self.s.get("akt", "ok")
            if kip == "hata":
                return _Yanit(200, '<?xml version="1.0" encoding="utf-8"?><chkl:messages xmlns:chkl="http://'
                                   'www.sap.com/abapxml/checklist"><chkl:properties checkExecuted="true" '
                                   'activationExecuted="false" generationExecuted="false"/><msg type="E" '
                                   'line="1"><shortText><txt>Sahte sozdizimi hatasi</txt></shortText></msg>'
                                   '</chkl:messages>', url=url)
            if kip == "ok" or kip == "sahte":
                if kip == "ok":
                    self.inaktif = False
                if self.inaktif_desc is not None:
                    self.aktif_desc = self.inaktif_desc
                return _Yanit(200, '<?xml version="1.0" encoding="utf-8"?><chkl:messages xmlns:chkl="http://'
                                   'www.sap.com/abapxml/checklist"><chkl:properties checkExecuted="true" '
                                   'activationExecuted="true" generationExecuted="false"/></chkl:messages>',
                              url=url)
        self.olaylar.append(["?", method, yol])
        return _Yanit(599, "sahte sunucu: beklenmeyen istek")


def _sahte_adt(lib, sunucu):
    class _SahteAdt(lib.SAPADTClient):
        def __init__(self):                           # noqa: D401 — gerçek __init__ bağlantı arar
            self.url = "https://sap.example.test:44300"
            self.session = sunucu
            self.csrf_token = "SAHTE-CSRF"
            self.client = "000"
            self._auth_provider = None
            self.debug_enabled = False
            self.timeout_default = 5
            self.timeout_short = 5
            self._last_lock_effective_transport = None

        def _get_auth_header(self):
            return "Basic SAHTE"

        def fetch_csrf_token(self, force_refresh=False):
            return self.csrf_token

        def _update_cookies(self, response):
            return None

        def lock_object(self, object_url, access_mode="MODIFY", transport=None, **kw):
            sunucu.lock_sayisi += 1
            n = sunucu.lock_sayisi
            if sunucu.s.get("lock_hata_sirasi") == n:
                sunucu.olaylar.append(["LOCK", n, False])
                raise lib.SAPLockError("sahte kilit hatasi")
            sunucu.olaylar.append(["LOCK", n, True])
            self._last_lock_effective_transport = transport
            return f"LH{n}"

        def unlock_object(self, object_url, lock_handle):
            sunucu.olaylar.append(["UNLOCK", lock_handle])
            return True

        def put_423_diagnosis(self, object_url, transport=None):
            sunucu.olaylar.append(["D423"])
            return "[423-TESHIS] sahte"

    return _SahteAdt()


def _surucu() -> int:
    kaynak_yol = Path(os.environ["Q175_KAYNAK"])
    mut_idx = int(os.environ.get("Q175_MUT", "-1"))
    kaynak = kaynak_yol.read_text(encoding="utf-8")
    if mut_idx >= 0:
        _, eski, yeni = MUTASYONLAR[mut_idx]
        kaynak = kaynak.replace(eski, yeni, 1)
    sys.path.insert(0, str(SCRIPTS))
    import types
    import sap_adt_lib as lib
    kod = compile(kaynak, str(HEDEF), "exec")
    sonuclar = []
    gercek_out, gercek_err = sys.stdout, sys.stderr
    for v in VEKTORLER:
        sunucu = _Sunucu(v)
        adt = _sahte_adt(lib, sunucu)
        sc = types.ModuleType("sap_client")

        class _SAPClient:
            def __init__(self, _adt=adt):
                self.adt_client = _adt
        sc.SAPClient = _SAPClient
        sys.modules["sap_client"] = sc
        desc = v.get("desc", YENI_DESC)
        sys.argv = [str(HEDEF), sunucu.ad, "--type", v.get("tip", "ddls"), "--desc", desc,
                    "--transport", "SAHK900001"] + v.get("ek", [])
        cap_out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
        cap_err = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")
        sys.stdout, sys.stderr = cap_out, cap_err
        rc = None
        try:
            exec(kod, {"__name__": "__main__", "__file__": str(HEDEF)})
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        except BaseException as e:                    # çökme != FAIL: ölç
            rc = f"COKTU {type(e).__name__}: {e}"
        yakala = []
        for akis, cap in ((sys.stdout, cap_out), (sys.stderr, cap_err)):
            try:
                akis.flush()
                yakala.append(cap.buffer.getvalue().decode("utf-8", "replace"))
            except Exception as e:                    # noqa: BLE001
                yakala.append(f"<yakalanamadi {e}>")
        sys.stdout, sys.stderr = gercek_out, gercek_err
        sonuclar.append({"ad": v["ad"], "rc": rc, "out": yakala[0], "err": yakala[1],
                         "olaylar": sunucu.olaylar, "inaktif_son": sunucu.inaktif,
                         "aktif_desc_son": sunucu.aktif_desc})
    sys.stdout.write(IZ_ISARETI + json.dumps(sonuclar, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    return 0


# ═════════════════════════════════════════════════════════════════════════════
# VEKTÖRLER + ölçütler
# ═════════════════════════════════════════════════════════════════════════════
VEKTORLER = [
    {"ad": "V1 412->200->aktivasyon OK: tek retry (yeni lock, 412 govdesindeki ETag), aktif readback, exit 0"},
    {"ad": "V2 412->412: TEK retry, ikinci 412 = exit!=0 (dongu yok)", "hep_412": True},
    {"ad": "V3 412->200->aktivasyon HATA: exit!=0 + 'INAKTIF KALDI'", "akt": "hata"},
    {"ad": "V4 ilk PUT 200 (retry yok) ama obje inaktife dustu: aktivasyon + exit 0",
     "sunucu_aktif_etag_kabul": True},
    {"ad": "V5 NOOP: ayni metin -> LOCK/PUT/aktivasyon YOK, exit 0 (degismedi)", "desc": ESKI_DESC},
    {"ad": "V6 412 govdesinden ETag CIKARILAMAZ: exit!=0, retry yok", "govde_412": "parse_yok"},
    {"ad": "V6b 412 govdesindeki ETag gonderilenle AYNI: exit!=0, retry yok", "govde_412": "ayni"},
    {"ad": "V7 aktivasyon yaniti 'true' ama obje HALA listede (Q187 sinifi): exit!=0",
     "sunucu_aktif_etag_kabul": True, "akt": "sahte"},
    {"ad": "V8 aktive-bekleyen listesi OKUNAMAZ (HTTP 500): exit!=0 DOGRULANAMADI, aktivasyon yok",
     "sunucu_aktif_etag_kabul": True, "worklist": "500"},
    {"ad": "V9 obje inaktif ama listede GORUNMUYOR: aktif-surum readback yakalar, exit!=0",
     "sunucu_aktif_etag_kabul": True, "worklist": "gizli"},
    {"ad": "V10 FP CAPASI: PUT inaktife dusurmez + listede komsu adlar -> aktivasyon YOK, exit 0",
     "sunucu_aktif_etag_kabul": True, "inaktife_dusmez": True},
    {"ad": "V11 3.BAGLAM class: 412->200, liste girdisi alt-include URI'si -> CLAS/OC aktivasyonu, exit 0",
     "tip": "class"},
    {"ad": "V12 --force-put ayni metin: yazma yolu kosar (412->200->aktivasyon), exit 0",
     "desc": ESKI_DESC, "ek": ["--force-put"]},
    {"ad": "V13 423: ortak teshis basilir, retry YOK, exit!=0 (degismedi)", "put_423": True},
    {"ad": "V14 retry LOCK'u alinamaz: exit!=0, aktivasyon yok", "lock_hata_sirasi": 2},
    {"ad": "V15 --dry-run: LOCK/PUT yok, exit 0 (degismedi)", "ek": ["--dry-run"]},
    {"ad": "V16 GEVSETME SINIRI: 412 ama envelope arada DEGISMIS (eszamanli yazim) -> retry YOK, exit!=0",
     "eszamanli": True},
]


def _say(ol, tur):
    return sum(1 for o in ol if o[0] == tur)


def _puts(ol):
    return [o for o in ol if o[0] == "PUT"]


def _sira_temiz(ol):
    """Her PUT'tan hemen önceki olay kendi LOCK'u olmalı (LOCK↔PUT arasında GET/WL/POST yok)."""
    for i, o in enumerate(ol):
        if o[0] == "PUT":
            onceki = ol[i - 1] if i else None
            if not onceki or onceki[0] != "LOCK" or onceki[2] is not True:
                return False
    return True


def _kilit_dengeli(ol):
    return _say([o for o in ol if o[0] == "LOCK" and o[2]], "LOCK") == _say(ol, "UNLOCK")


def _olcut(v, r):
    """(gecti, detay) — her vektörün ölçütü."""
    ol, out, rc = r["olaylar"], r["out"] + r["err"], r["rc"]
    p = _puts(ol)
    ifm = [x[1] for x in p]
    akt = _say(ol, "POST")
    ad = v["ad"].split()[0]
    d = f"rc={rc} PUT={[(x[1][:22] if x[1] else None, x[3]) for x in p]} POST={akt} WL={_say(ol, 'WL')} " \
        f"LOCK={_say(ol, 'LOCK')} UNLOCK={_say(ol, 'UNLOCK')} inaktif_son={r['inaktif_son']} " \
        f"cikti_son={out.strip().splitlines()[-1][:160] if out.strip() else ''!r}"
    temel = _sira_temiz(ol) and _kilit_dengeli(ol)
    if ad == "V1":
        ok = (rc == 0 and ifm == [ETAG_AKTIF, ETAG_OBJE] and _say(ol, "LOCK") == 2 and akt >= 1
              and r["inaktif_son"] is False and r["aktif_desc_son"] == YENI_DESC and "[OK]" in out
              and "[RETRY]" in out)
    elif ad == "V2":
        ok = rc not in (0, None) and len(p) == 2 and akt == 0 and "ikinci retry YOK" in out
    elif ad == "V3":
        ok = rc not in (0, None) and len(p) == 2 and "İNAKTİF KALDI" in out
    elif ad == "V4":
        ok = (rc == 0 and ifm == [ETAG_AKTIF] and akt >= 1 and r["inaktif_son"] is False
              and "[RETRY]" not in out and "[OK]" in out)
    elif ad == "V5":
        ok = rc == 0 and not p and _say(ol, "LOCK") == 0 and akt == 0 and "[NOOP]" in out
    elif ad == "V6":
        ok = rc not in (0, None) and len(p) == 1 and _say(ol, "LOCK") == 1 and "ÇIKARILAMADI" in out
    elif ad == "V6b":
        ok = rc not in (0, None) and len(p) == 1 and _say(ol, "LOCK") == 1 and "AYNI" in out
    elif ad == "V7":
        ok = rc not in (0, None) and akt >= 1 and "İNAKTİF KALDI" in out
    elif ad == "V8":
        ok = rc not in (0, None) and akt == 0 and "DOĞRULANAMADI" in out
    elif ad == "V9":
        ok = rc not in (0, None) and "AKTİF sürümdeki" in out
    elif ad == "V10":
        ok = rc == 0 and akt == 0 and len(p) == 1 and "[OK]" in out
    elif ad == "V11":
        posts = [o for o in ol if o[0] == "POST"]
        ok = (rc == 0 and ifm == [ETAG_AKTIF, ETAG_OBJE] and posts and all(o[3] for o in posts)
              and r["inaktif_son"] is False)
    elif ad == "V12":
        ok = rc == 0 and len(p) == 2 and akt >= 1 and "[FORCE-PUT]" in out and "[OK]" in out
    elif ad == "V13":
        ok = rc not in (0, None) and len(p) == 1 and _say(ol, "D423") == 1 and _say(ol, "LOCK") == 1
    elif ad == "V14":
        ok = rc not in (0, None) and len(p) == 1 and _say(ol, "LOCK") == 2 and akt == 0
    elif ad == "V15":
        ok = rc == 0 and not p and _say(ol, "LOCK") == 0 and "[DRY-RUN]" in out
    elif ad == "V16":
        ok = (rc not in (0, None) and len(p) == 1 and _say(ol, "LOCK") == 1 and akt == 0
              and "DEĞİŞMİŞ" in out and r["aktif_desc_son"] == "Baska Kullanici Degistirdi")
    else:
        ok = False
    return (ok and temel), (d if temel else d + " [SIRA/KILIT DENGESI BOZUK]")


def _kos(kaynak: Path, kum: Path, mut_idx: int = -1):
    env = dict(os.environ)
    env.update({"Q175_KAYNAK": str(kaynak), "Q175_MUT": str(mut_idx), "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1", "CLAUDE_PROJECT_DIR": str(kum)})
    env.pop("ADT_SAP_URL", None)
    p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--_surucu"], cwd=str(kum),
                       env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    for satir in (p.stdout or "").splitlines():
        if satir.startswith(IZ_ISARETI):
            return json.loads(satir[len(IZ_ISARETI):]), ""
    return None, f"surucu iz basmadi (rc={p.returncode}): {(p.stderr or p.stdout)[-600:]}"


def _degerlendir(sonuclar):
    return [(v["ad"],) + _olcut(v, r) for v, r in zip(VEKTORLER, sonuclar)]


def main() -> int:
    if "--_surucu" in sys.argv:
        return _surucu()
    kaynak = HEDEF
    if "--kaynak" in sys.argv:
        kaynak = Path(sys.argv[sys.argv.index("--kaynak") + 1]).resolve()
    kum = Path(tempfile.mkdtemp(prefix="aciklama_412_"))
    try:
        print("=" * 78)
        print(f"aciklama_412_retry (Q175) — kaynak: {kaynak.name}")
        print("=" * 78)
        sonuclar, hata = _kos(kaynak, kum)
        if sonuclar is None:
            print(f"[KURULAMADI] {hata}")
            return 2
        deger = _degerlendir(sonuclar)
        for ad, ok, detay in deger:
            print(f"  [{'PASS' if ok else 'FAIL'}] {ad}")
            if not ok:
                print(f"         gorulen: {detay}")
        gecen = sum(1 for _, ok, _ in deger if ok)
        print(f"\n{gecen}/{len(deger)} OK")
        if kaynak != HEDEF:
            return 0 if gecen == len(deger) else 1

        print("\n--- MUTASYONLAR (her biri en az bir vektoru KIRMIZI yapmali) ---")
        ham = HEDEF.read_text(encoding="utf-8")
        mut_kirik = []
        for i, (mad, eski, _yeni) in enumerate(MUTASYONLAR):
            adet = ham.count(eski)
            if adet != 1:
                print(f"  [KURULAMADI] {mad} -> capa {adet} kez gecti (beklenen 1)")
                mut_kirik.append(mad + " (KURULAMADI)")
                continue
            m_son, m_hata = _kos(HEDEF, kum, i)
            if m_son is None:
                print(f"  [KURULAMADI] {mad} -> {m_hata}")
                mut_kirik.append(mad + " (KURULAMADI)")
                continue
            kiranlar = [a.split()[0] for a, ok, _ in _degerlendir(m_son) if not ok]
            print(f"  [{'YAKALANDI' if kiranlar else 'KACTI'}] {mad}"
                  + (f"  <- {', '.join(kiranlar)}" if kiranlar else ""))
            if not kiranlar:
                mut_kirik.append(mad)
        print("\n" + "=" * 78)
        if gecen != len(deger) or mut_kirik:
            if mut_kirik:
                print("FAIL — mutasyon KACTI/KURULAMADI: " + "; ".join(mut_kirik))
            return 1
        print(f"PASS — {len(deger)} vektor + {len(MUTASYONLAR)} mutasyon")
        return 0
    finally:
        shutil.rmtree(kum, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
