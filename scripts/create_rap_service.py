#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""create_rap_service.py — RAP Service Definition + Binding + PUBLISH (ADT REST).

ORDER pilotu make-or-break aracı. Endpoint'ler web araştırmasından (abap-adt-api
kanonik client, 2026-05-15) — playbook/adt-rap.md §32.4/§32.5. SEGW/operatör YOK.

Adımlar (--step ile tek tek çalıştırılabilir, gözlemlenebilir):
  srvd     : Service Definition source yarat + aktive   (/ddic/srvd/sources, DDLS-twin)
  srvb     : Service Binding yarat                       (/businessservices/bindings)
  publish  : Binding'i publish et                        (/businessservices/odatav2/publishjobs)
  verify   : Canlı $metadata GET 200 doğrula
  all      : srvd→srvb→publish→verify

ADR 0005: yeni TR/paket YARATMAZ; transport kullanıcıdan. Z text TR + tam.
Kullanım:
  python scripts/create_rap_service.py --step srvd --transport <TRANSPORT>
"""
import argparse
import re
import sys
import urllib3
from xml.sax.saxutils import escape as xml_escape

sys.path.insert(0, __import__("os").path.dirname(__file__))
from sap_adt_lib import SAPADTClient

urllib3.disable_warnings()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PKG = "ZSD001_CLC"                      # default; main() --package ile override
SRVD_NAME = "ZSD001_UI_ORDER"          # Service Definition
SRVB_NAME = "ZSD001_UI_ORDER_O2"       # Service Binding (V2, NTTDATA _O2)
EXPOSE_CDS = "ZSD001_C_ORDER"          # projection
SRVD_LABEL = "Sefer servisi"
SRVB_LABEL = ""                        # SRVB (servis bağlama) description; --srvb-label ile
                                       # set edilir. BOŞSA SRVD_LABEL'dan türetilir (aşağıda
                                       # srvb_xml). ORDER default sızması fix'i (2026-06-25):
                                       # eskiden SRVB hep "Sefer servisi baglama" alıyordu —
                                       # per-servis label YOKTU.

SRVD_BASE = "/sap/bc/adt/ddic/srvd/sources"
SRVB_BASE = "/sap/bc/adt/businessservices/bindings"
PUBLISH_V2 = "/sap/bc/adt/businessservices/odatav2/publishjobs"
ACTIVATION = "/sap/bc/adt/activation"
ODATA_V2_BASE = "/sap/opu/odata/sap"


def verify_active(names_types):
    """Aktivasyon SONRASI obje gerçekten active + source-dolu mu — check_sap_
    active_version.py (içerik-farkindalikli) ile teyit. 'activate 200/return OK'
    YETMEZ (2026-06-10 bos-children vakasi). bdef tipi validator'da yok → atlanir."""
    import subprocess
    val = __import__("os").path.join(__import__("os").path.dirname(__file__),
                                     "validators", "check_sap_active_version.py")
    allok = True
    print("  --- post-activate verify (active + source dolu) ---")
    for nm, tp in names_types:
        r = subprocess.run([sys.executable, val, "--name", nm, "--object-type", tp],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        line = (r.stdout.strip() or r.stderr.strip() or "").splitlines()
        print(f"  [{'OK' if r.returncode == 0 else 'FAIL'}] {nm}: {line[0] if line else ''}")
        if r.returncode != 0:
            allok = False
    return allok


def csrf(client):
    client._invalidate_csrf_cache()
    r = client.session.get(
        client.url + "/sap/bc/adt/discovery",
        params={"sap-client": "100", "sap-language": "TR"},
        headers={"X-CSRF-Token": "Fetch"}, verify=False, timeout=30,
    )
    tok = r.headers.get("X-CSRF-Token", "")
    if not tok:
        raise SystemExit("[FAIL] CSRF alınamadı")
    print(f"[OK] CSRF: {tok[:20]}...")
    return tok


def srvd_shell_xml(name, desc, pkg):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<srvd:srvdSource xmlns:srvd="http://www.sap.com/adt/ddic/srvdsources"\n'
        '                 xmlns:adtcore="http://www.sap.com/adt/core"\n'
        f'                 adtcore:name="{name.upper()}"\n'
        f'                 adtcore:description="{xml_escape(desc)}"\n'
        '                 adtcore:type="SRVD/SRV"\n'
        '                 srvd:srvdSourceType="S"\n'
        '                 adtcore:masterLanguage="TR">\n'
        f'  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{pkg.lower()}"\n'
        '                      adtcore:type="DEVC/K"\n'
        f'                      adtcore:name="{pkg.upper()}"/>\n'
        '</srvd:srvdSource>'
    )


# Default = ORDER (geriye uyumlu). CONTAINER_REPORT vb. için main()
# --expose-extra ile override edilir.
EXPOSE_EXTRA = ["ZSD001_C_ORDERDEST", "ZSD000_I_BPNAME",
                "ZSD001_I_PORTVH", "ZSD000_I_VKORGVH"]


def srvd_source():
    lines = [
        f"@EndUserText.label: '{SRVD_LABEL}'",
        f"define service {SRVD_NAME}",
        "{",
        f"  expose {EXPOSE_CDS};",
    ]
    for e in EXPOSE_EXTRA:
        lines.append(f"  expose {e};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def srvb_xml(name, srvd, pkg):
    # GROUNDED: canlı ZSD001_UI_ORDER_O2'nin gerçek ADT payload'undan
    # (2026-05-15, kullanıcı Eclipse'te yarattı → raw GET ile yakalandı).
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<srvb:serviceBinding srvb:contract="C1"\n'
        '                     xmlns:srvb="http://www.sap.com/adt/ddic/ServiceBindings"\n'
        '                     xmlns:adtcore="http://www.sap.com/adt/core"\n'
        f'                     adtcore:name="{name.upper()}"\n'
        '                     adtcore:type="SRVB/SVB"\n'
        f'                     adtcore:description="{xml_escape(SRVB_LABEL or (SRVD_LABEL + " bağlama"))}"\n'
        '                     adtcore:masterLanguage="TR" adtcore:language="TR">\n'
        f'  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{pkg.lower()}"\n'
        f'                      adtcore:type="DEVC/K" adtcore:name="{pkg.upper()}"/>\n'
        f'  <srvb:services srvb:name="{name.upper()}">\n'
        '    <srvb:content srvb:version="0001" srvb:minorVersion="0"\n'
        '                  srvb:patchVersion="0" srvb:buildVersion=""\n'
        '                  srvb:releaseState="NOT_RELEASED">\n'
        f'      <srvb:serviceDefinition adtcore:uri="/sap/bc/adt/ddic/srvd/sources/{srvd.lower()}"\n'
        f'          adtcore:type="SRVD/SRV" adtcore:name="{srvd.upper()}"/>\n'
        '    </srvb:content>\n'
        '  </srvb:services>\n'
        '  <srvb:binding srvb:type="ODATA" srvb:version="V2" srvb:category="0">\n'
        f'    <srvb:implementation adtcore:name="{name.upper()}"/>\n'
        '  </srvb:binding>\n'
        '</srvb:serviceBinding>'
    )


def publish_xml(binding):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">\n'
        f'  <adtcore:objectReference adtcore:uri="{SRVB_BASE}/{binding.lower()}"\n'
        f'      adtcore:name="{binding.upper()}"/>\n'
        '</adtcore:objectReferences>'
    )


def activate(client, tok, name, obj_uri):
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">\n'
        f'  <adtcore:objectReference adtcore:uri="{obj_uri}" adtcore:name="{name.upper()}"/>\n'
        '</adtcore:objectReferences>'
    )
    r = client.session.post(
        client.url + ACTIVATION,
        params={"method": "activate", "preauditRequested": "false"},
        headers={"X-CSRF-Token": tok, "Content-Type": "application/xml",
                 "Accept": "application/xml"},
        data=body.encode("utf-8"), verify=False, timeout=60,
    )
    # DÜZELTİLDİ (2026-06-11): eski mantık `A and B or C` → C clause sahte-OK üretiyordu.
    # HTTP 200 KANIT DEĞİL → activationExecuted + type=E parse et.
    executed, errs = _activation_failures(r.text)
    ok = r.status_code in (200, 202) and executed and not errs
    print(f"[{'OK' if ok else 'FAIL'}] activate {name} status={r.status_code} executed={executed}")
    if not ok and errs:
        for e in errs[:6]:
            print("   E: " + e)
    return ok


def _activation_failures(resp_text):
    """Aktivasyon yanıtından gerçek durum. HTTP 200 KANIT DEĞİL.
    Döner (executed: bool, errors: list[str]). Aktif = executed True ve errors boş."""
    import re
    t = resp_text or ""
    m = re.search(r'activationExecuted="(\w+)"', t)
    # activationExecuted yoksa eski stil yanıt olabilir → severity tabanlı fallback
    executed = (m.group(1) == "true") if m else ('severity="E"' not in t and 'severity="A"' not in t)
    errs = re.findall(r'type="[EA]"[^>]*>.*?<txt>([^<]+)', t, re.S)
    return executed, errs


def activate_and_verify(client, tok, refs):
    """Çoklu obje aktivasyonu + ZORUNLU doğrulama. refs: [(uri, NAME), ...].
    activationExecuted!="true" VEYA type=E mesajı → RuntimeError (sahte 'OK' imkansiz).
    2026-06-11 dersi: POST 200 döndü ama activationExecuted=false → metadata eski kaldı.
    Custom inline /activation POST yazma — BU helper'ı kullan (adt-rap §34-D)."""
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">\n'
            + "".join(f'  <adtcore:objectReference adtcore:uri="{u}" adtcore:name="{n.upper()}"/>\n'
                      for u, n in refs)
            + '</adtcore:objectReferences>')
    r = client.session.post(
        client.url + ACTIVATION,
        params={"method": "activate", "preauditRequested": "false"},
        headers={"X-CSRF-Token": tok, "Content-Type": "application/xml", "Accept": "application/xml"},
        data=body.encode("utf-8"), verify=False, timeout=120,
    )
    executed, errs = _activation_failures(r.text)
    names = ", ".join(n for _, n in refs)
    if not executed or errs:
        raise RuntimeError(
            f"AKTİVASYON BAŞARISIZ ({names}): activationExecuted={executed}; hatalar={errs[:6]}")
    print(f"[OK] activate+verify: {names} (activationExecuted=true, hata yok)")
    return True


def step_srvd(client, tok, transport):
    name = SRVD_NAME
    obj = f"{SRVD_BASE}/{name.lower()}"
    print(f"\n=== SRVD: {name} ===")
    r = client.session.post(
        client.url + SRVD_BASE, params={"corrNr": transport},
        headers={"X-CSRF-Token": tok,
                 "Content-Type": "application/vnd.sap.adt.ddic.srvd.v1+xml; charset=utf-8",
                 "Accept": "application/vnd.sap.adt.ddic.srvd.v1+xml",
                 "sap-client": "100", "sap-language": "TR"},
        data=srvd_shell_xml(name, SRVD_LABEL, PKG).encode("utf-8"),
        verify=False, timeout=60,
    )
    print(f"[shell] POST status={r.status_code}")
    already = r.status_code == 400 and "AlreadyExists" in r.text
    if r.status_code not in (200, 201) and not already:
        print("   BODY: " + r.text[:600].replace("\n", " "))
        return False
    if already:
        print("   (zaten var → source güncelle + reactivate)")
    lr = client.session.post(
        client.url + obj,
        params={"_action": "LOCK", "accessMode": "MODIFY", "corrNr": transport},
        headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful",
                 "Accept": "application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result"},
        verify=False, timeout=20,
    )
    m = re.search(r"<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>", lr.text)
    handle = m.group(1) if m else None
    if not handle:
        print(f"[FAIL] LOCK status={lr.status_code} :: {lr.text[:300]}")
        return False
    try:
        pr = client.session.put(
            client.url + obj + "/source/main",
            params={"corrNr": transport, "lockHandle": handle},
            headers={"X-CSRF-Token": tok, "Content-Type": "text/plain; charset=utf-8",
                     "Accept": "*/*"},
            data=srvd_source().encode("utf-8"), verify=False, timeout=60,
        )
        print(f"[source] PUT status={pr.status_code}")
        if pr.status_code not in (200, 201, 204):
            print("   BODY: " + pr.text[:600].replace("\n", " "))
            return False
    finally:
        client.session.post(client.url + obj, params={"_action": "UNLOCK", "lockHandle": handle},
                             headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful"},
                             verify=False, timeout=10)
    return activate(client, tok, name, obj)


BDEF_NAME = "ZSD001_I_ORDER"          # = root entity adı (SAP zorunlu)
BDEF_BASE = "/sap/bc/adt/bo/behaviordefinitions"
BDEF_CT = "application/vnd.sap.adt.blues.v1+xml"


def bdef_shell_xml(name, desc, pkg):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<blue:blueSource xmlns:blue="http://www.sap.com/wbobj/blue"\n'
        '                 xmlns:adtcore="http://www.sap.com/adt/core"\n'
        f'                 adtcore:name="{name.upper()}"\n'
        f'                 adtcore:description="{xml_escape(desc)}"\n'
        '                 adtcore:type="BDEF/BDO"\n'
        '                 adtcore:masterLanguage="TR">\n'
        f'  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{pkg.lower()}"\n'
        '                      adtcore:type="DEVC/K"\n'
        f'                      adtcore:name="{pkg.upper()}"/>\n'
        '</blue:blueSource>'
    )


def step_bdef(client, tok, transport, bdef_source_path, bdef_name=BDEF_NAME):
    name = bdef_name
    obj = f"{BDEF_BASE}/{name.lower()}"
    print(f"\n=== BDEF: {name} ===")
    src = open(bdef_source_path, encoding="utf-8").read()
    r = client.session.post(
        client.url + BDEF_BASE, params={"corrNr": transport},
        headers={"X-CSRF-Token": tok,
                 "Content-Type": BDEF_CT + "; charset=utf-8", "Accept": BDEF_CT,
                 "sap-client": "100", "sap-language": "TR"},
        data=bdef_shell_xml(name, "Sefer Başlık davranışı", PKG).encode("utf-8"),
        verify=False, timeout=60,
    )
    print(f"[shell] POST status={r.status_code}")
    already = r.status_code == 400 and "AlreadyExists" in r.text
    if r.status_code not in (200, 201) and not already:
        print("   BODY: " + r.text[:600].replace("\n", " "))
        return False
    if already:
        print("   (zaten var → source güncelle + devam)")
    lr = client.session.post(
        client.url + obj,
        params={"_action": "LOCK", "accessMode": "MODIFY", "corrNr": transport},
        headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful",
                 "Accept": "application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result"},
        verify=False, timeout=20,
    )
    m = re.search(r"<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>", lr.text)
    handle = m.group(1) if m else None
    if not handle:
        print(f"[FAIL] LOCK status={lr.status_code} :: {lr.text[:300]}")
        return False
    try:
        pr = client.session.put(
            client.url + obj + "/source/main",
            params={"corrNr": transport, "lockHandle": handle},
            headers={"X-CSRF-Token": tok, "Content-Type": "text/plain; charset=utf-8",
                     "Accept": "*/*"},
            data=src.encode("utf-8"), verify=False, timeout=60,
        )
        print(f"[source] PUT status={pr.status_code}")
        if pr.status_code not in (200, 201, 204):
            print("   BODY: " + pr.text[:600].replace("\n", " "))
            return False
    finally:
        client.session.post(client.url + obj, params={"_action": "UNLOCK", "lockHandle": handle},
                             headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful"},
                             verify=False, timeout=10)
    print("[OK] BDEF source pushed (inactive — behavior class sonrası birlikte aktive)")
    return True


BCLASS_NAME = "ZCL_SD001_ORDER"
BCLASS_BASE = "/sap/bc/adt/oo/classes"
BCLASS_CT = "application/vnd.sap.adt.oo.classes.v4+xml"
BCLASS_SOURCE = (
    "CLASS zcl_sd015_voyage DEFINITION\n"
    "  PUBLIC ABSTRACT FINAL\n"
    "  FOR BEHAVIOR OF ZSD001_I_ORDER.\n"
    "ENDCLASS.\n\n"
    "CLASS zcl_sd015_voyage IMPLEMENTATION.\n"
    "ENDCLASS.\n"
)


def bclass_shell_xml(name, desc, pkg):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<class:abapClass xmlns:class="http://www.sap.com/adt/oo/classes"\n'
        '                 xmlns:adtcore="http://www.sap.com/adt/core"\n'
        f'                 adtcore:name="{name.upper()}"\n'
        f'                 adtcore:description="{xml_escape(desc)}"\n'
        '                 adtcore:type="CLAS/OC"\n'
        '                 adtcore:masterLanguage="TR"\n'
        '                 adtcore:language="TR"\n'
        '                 class:final="true"\n'
        '                 class:visibility="public">\n'
        f'  <adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/{pkg.lower()}"\n'
        '                      adtcore:type="DEVC/K"\n'
        f'                      adtcore:name="{pkg.upper()}"/>\n'
        '</class:abapClass>'
    )


def step_bclass(client, tok, transport):
    """Behavior class'ı RAW REST + masterLanguage=TR ile yarat (ADR 0005 D).
    MCP adt_post_shell class'ı EN yaratıyor — bu yüzden raw REST."""
    name = BCLASS_NAME
    obj = f"{BCLASS_BASE}/{name.lower()}"
    print(f"\n=== BCLASS (TR): {name} ===")
    r = client.session.post(
        client.url + BCLASS_BASE, params={"corrNr": transport},
        headers={"X-CSRF-Token": tok,
                 "Content-Type": BCLASS_CT + "; charset=utf-8", "Accept": BCLASS_CT,
                 "sap-client": "100", "sap-language": "TR"},
        data=bclass_shell_xml(name, "Sefer Başlık davranış uygulaması", PKG).encode("utf-8"),
        verify=False, timeout=60,
    )
    print(f"[shell] POST status={r.status_code}")
    already = r.status_code == 400 and "AlreadyExists" in r.text
    if r.status_code not in (200, 201) and not already:
        print("   BODY: " + r.text[:600].replace("\n", " "))
        return False
    if already:
        print("   (zaten var → source güncelle + devam)")
    lr = client.session.post(
        client.url + obj,
        params={"_action": "LOCK", "accessMode": "MODIFY", "corrNr": transport},
        headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful",
                 "Accept": "application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result"},
        verify=False, timeout=20,
    )
    m = re.search(r"<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>", lr.text)
    handle = m.group(1) if m else None
    if not handle:
        print(f"[FAIL] LOCK status={lr.status_code} :: {lr.text[:300]}")
        return False
    try:
        pr = client.session.put(
            client.url + obj + "/source/main",
            params={"corrNr": transport, "lockHandle": handle},
            headers={"X-CSRF-Token": tok, "Content-Type": "text/plain; charset=utf-8",
                     "Accept": "*/*"},
            data=BCLASS_SOURCE.encode("utf-8"), verify=False, timeout=60,
        )
        print(f"[source] PUT status={pr.status_code}")
        if pr.status_code not in (200, 201, 204):
            print("   BODY: " + pr.text[:600].replace("\n", " "))
            return False
    finally:
        client.session.post(client.url + obj, params={"_action": "UNLOCK", "lockHandle": handle},
                             headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful"},
                             verify=False, timeout=10)
    print("[OK] TR behavior class source pushed (inactive — bactivate ile birlikte)")
    return True


def step_cdsactivate(client, tok):
    """Birden çok DDLS'i BİRLİKTE aktive (RAP composition/redirect mutual dep)."""
    names = ["ZSD001_I_ORDERDEST", "ZSD001_I_ORDER",
             "ZSD001_C_ORDERDEST", "ZSD001_C_ORDER"]
    print(f"\n=== CDS BİRLİKTE AKTİVE: {', '.join(names)} ===")
    refs = "".join(
        f'  <adtcore:objectReference '
        f'adtcore:uri="/sap/bc/adt/ddic/ddl/sources/{n.lower()}" '
        f'adtcore:name="{n}"/>\n' for n in names
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">\n'
        + refs +
        '</adtcore:objectReferences>'
    )
    r = client.session.post(
        client.url + ACTIVATION,
        params={"method": "activate", "preauditRequested": "false"},
        headers={"X-CSRF-Token": tok, "Content-Type": "application/xml",
                 "Accept": "application/xml", "sap-client": "100", "sap-language": "TR"},
        data=body.encode("utf-8"), verify=False, timeout=120,
    )
    print(f"[activate] status={r.status_code}")
    print("   " + r.text[:900].replace("\n", " "))
    bad = ('severity="E"' in r.text) or ('severity="A"' in r.text) or r.status_code >= 400
    return not bad


def step_ccimp(client, tok, transport, ccimp_path):
    """Behavior class CCIMP (Local Types / includes/implementations) push —
    RAP determination/validation handler (lhc_*)."""
    cls = BCLASS_NAME.lower()
    obj = f"/sap/bc/adt/oo/classes/{cls}"
    inc = obj + "/includes/implementations"
    src = open(ccimp_path, encoding="utf-8").read()
    print(f"\n=== CCIMP push: {cls}/includes/implementations ===")
    lr = client.session.post(
        client.url + obj,
        params={"_action": "LOCK", "accessMode": "MODIFY", "corrNr": transport},
        headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful",
                 "Accept": "application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result"},
        verify=False, timeout=20,
    )
    m = re.search(r"<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>", lr.text)
    handle = m.group(1) if m else None
    if not handle:
        print(f"[FAIL] LOCK status={lr.status_code} :: {lr.text[:300]}")
        return False
    try:
        pr = client.session.put(
            client.url + inc,
            params={"corrNr": transport, "lockHandle": handle},
            headers={"X-CSRF-Token": tok, "Content-Type": "text/plain; charset=utf-8",
                     "Accept": "*/*"},
            data=src.encode("utf-8"), verify=False, timeout=60,
        )
        print(f"[ccimp PUT] status={pr.status_code}")
        if pr.status_code not in (200, 201, 204):
            print("   BODY: " + pr.text[:600].replace("\n", " "))
            return False
    finally:
        client.session.post(client.url + obj, params={"_action": "UNLOCK", "lockHandle": handle},
                             headers={"X-CSRF-Token": tok, "X-sap-adt-sessiontype": "stateful"},
                             verify=False, timeout=10)
    print("[OK] CCIMP pushed (inactive — pbactivate ile birlikte)")
    return True


def step_pbactivate(client, tok):
    """Interface BDEF + Projection BDEF + behavior class BİRLİKTE aktive."""
    print("\n=== ACTIVATE interface+projection BDEF + class ===")
    proj = BDEF_NAME.upper().replace('_I_', '_C_')
    refs = (
        f'  <adtcore:objectReference adtcore:uri="{BDEF_BASE}/{BDEF_NAME.lower()}" adtcore:name="{BDEF_NAME.upper()}"/>\n'
        f'  <adtcore:objectReference adtcore:uri="{BDEF_BASE}/{proj.lower()}" adtcore:name="{proj}"/>\n'
        f'  <adtcore:objectReference adtcore:uri="/sap/bc/adt/oo/classes/{BCLASS_NAME.lower()}" adtcore:name="{BCLASS_NAME.upper()}"/>\n'
    )
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">\n'
            + refs + '</adtcore:objectReferences>')
    r = client.session.post(
        client.url + ACTIVATION,
        params={"method": "activate", "preauditRequested": "false"},
        headers={"X-CSRF-Token": tok, "Content-Type": "application/xml",
                 "Accept": "application/xml", "sap-client": "100", "sap-language": "TR"},
        data=body.encode("utf-8"), verify=False, timeout=120,
    )
    print(f"[activate] status={r.status_code}")
    print("   " + r.text[:900].replace("\n", " "))
    return not (('severity="E"' in r.text) or ('severity="A"' in r.text) or r.status_code >= 400)


def step_bactivate(client, tok):
    """BDEF + behavior class BİRLİKTE aktive (RAP circular dependency)."""
    print(f"\n=== ACTIVATE BDEF+CLASS birlikte ===")
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">\n'
        f'  <adtcore:objectReference adtcore:uri="{BDEF_BASE}/{BDEF_NAME.lower()}"\n'
        f'      adtcore:name="{BDEF_NAME.upper()}"/>\n'
        f'  <adtcore:objectReference adtcore:uri="/sap/bc/adt/oo/classes/{BCLASS_NAME.lower()}"\n'
        f'      adtcore:name="{BCLASS_NAME.upper()}"/>\n'
        '</adtcore:objectReferences>'
    )
    r = client.session.post(
        client.url + ACTIVATION,
        params={"method": "activate", "preauditRequested": "false"},
        headers={"X-CSRF-Token": tok, "Content-Type": "application/xml",
                 "Accept": "application/xml", "sap-client": "100", "sap-language": "TR"},
        data=body.encode("utf-8"), verify=False, timeout=90,
    )
    print(f"[activate] status={r.status_code}")
    print("   " + r.text[:900].replace("\n", " "))
    bad = ('severity="E"' in r.text) or ('severity="A"' in r.text) or r.status_code >= 400
    return not bad


def step_srvb(client, tok, transport):
    name = SRVB_NAME
    print(f"\n=== SRVB: {name} ===")
    r = client.session.post(
        client.url + SRVB_BASE, params={"corrNr": transport},
        headers={"X-CSRF-Token": tok,
                 "Content-Type": "application/vnd.sap.adt.businessservices.servicebinding.v2+xml; charset=utf-8",
                 "Accept": "application/vnd.sap.adt.businessservices.servicebinding.v2+xml",
                 "X-sap-adt-sessiontype": "stateful",
                 "sap-client": "100", "sap-language": "TR"},
        data=srvb_xml(name, SRVD_NAME, PKG).encode("utf-8"),
        verify=False, timeout=60,
    )
    print(f"[create] POST status={r.status_code}")
    print("   BODY: " + r.text[:700].replace("\n", " "))
    return r.status_code in (200, 201)


def step_srvbactivate(client, tok):
    # SRVB create inactive döner (bindingCreated="false"); publish job
    # aktif binding ister. Kanonik /sap/bc/adt/activation (SRVD/BDEF/CDS'te
    # kanıtlı) SRVB obj URI'sine uygulanır.
    name = SRVB_NAME
    print(f"\n=== SRVB ACTIVATE: {name} ===")
    return activate(client, tok, name, f"{SRVB_BASE}/{name.lower()}")


def step_publish(client, tok):
    print(f"\n=== PUBLISH: {SRVB_NAME} ===")
    # discovery: /businessservices/odatav2/publishjobs{?servicename,serviceversion}
    r = client.session.post(
        client.url + PUBLISH_V2,
        params={"servicename": SRVB_NAME, "serviceversion": "0001"},
        headers={"X-CSRF-Token": tok, "Content-Type": "application/xml",
                 "Accept": "application/xml, application/vnd.sap.as+xml;charset=UTF-8;dataname=com.sap.adt.StatusMessage",
                 "sap-client": "100", "sap-language": "TR"},
        data=publish_xml(SRVB_NAME).encode("utf-8"), verify=False, timeout=120,
    )
    print(f"[publish] POST status={r.status_code}")
    print("   BODY: " + r.text[:900].replace("\n", " "))
    return r.status_code in (200, 201, 202)


def step_e2e(client):
    """Canli servise composition deep-create: header + 1 varis limani.
    Numbering (NR ZSD001_VN) + KR-VOY validasyon + composition CRUD kaniti."""
    base = f"{ODATA_V2_BASE}/{SRVB_NAME}"
    # CSRF — OData servisinin kendi token'i
    rg = client.session.get(client.url + base + "/", params={"sap-client": "100"},
                            headers={"X-CSRF-Token": "Fetch"}, verify=False, timeout=30)
    tok = rg.headers.get("X-CSRF-Token", "")
    print(f"[e2e] OData CSRF: {tok[:16]}... status={rg.status_code}")
    import json as _j
    body = {
        "VoyageNo": "9000000005",
        "Description": "E2E Test Sefer",
        "SalesOrganization": "1500",
        "DeparturePort": "TRIST",
        "to_Destination": {"results": [{"DestinationPort": "DEHAM"}]},
    }
    r = client.session.post(
        client.url + base + "/ZSD001_C_ORDER",
        params={"sap-client": "100", "sap-language": "TR"},
        headers={"X-CSRF-Token": tok, "Content-Type": "application/json",
                 "Accept": "application/json"},
        data=_j.dumps(body).encode("utf-8"), verify=False, timeout=60,
    )
    print(f"[e2e] deep-create POST status={r.status_code}")
    print("   " + r.text[:1200].replace("\n", " "))
    return r.status_code in (200, 201)


def step_verify(client):
    url = client.url + f"{ODATA_V2_BASE}/{SRVB_NAME}/$metadata"
    r = client.session.get(url, params={"sap-client": "100"}, verify=False, timeout=30)
    print(f"\n=== VERIFY $metadata ===\n{url}\nstatus={r.status_code} len={len(r.text)}")
    print("   " + r.text[:300].replace("\n", " "))
    return r.status_code == 200


def step_discover(client):
    """ADT discovery: srvd/businessservices collection'larının kabul ettiği
    content-type template'lerini sistemin kendisinden oku (tahminsiz)."""
    r = client.session.get(client.url + "/sap/bc/adt/discovery",
                            params={"sap-client": "100"}, verify=False, timeout=30)
    txt = r.text
    print(f"[discovery] status={r.status_code} len={len(txt)}")
    # collection href + accept template'leri yakala
    for kw in ("oo/classes", "abapClass", "classes</atom:title"):
        idx = 0
        low = txt.lower()
        while True:
            p = low.find(kw, idx)
            if p == -1:
                break
            seg = txt[max(0, p - 400): p + 400]
            print(f"\n--- '{kw}' @ {p} ---\n{seg}")
            idx = p + len(kw)
    return True


def step_probe(client, url, accept=None):
    h = {"sap-client": "100", "sap-language": "TR"}
    if accept:
        h["Accept"] = accept
    r = client.session.get(client.url + url, headers=h, verify=False, timeout=30)
    print(f"[probe GET] {url}\nstatus={r.status_code} len={len(r.text)}\n")
    print(r.text[:4000])
    return r.status_code == 200


def main():
    global SRVD_NAME, SRVB_NAME, EXPOSE_CDS, SRVD_LABEL, SRVB_LABEL, EXPOSE_EXTRA, PKG
    global BDEF_NAME, BCLASS_NAME, BCLASS_SOURCE
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True,
                    choices=["discover", "types", "probe", "srvd", "bdef",
                             "bclass", "ccimp", "bactivate", "pbactivate",
                             "cdsactivate", "srvb", "srvbactivate",
                             "publish", "verify", "e2e", "all"])
    ap.add_argument("--transport", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--accept", default="")
    ap.add_argument("--bdef-source",
                    default="ERP/SD/ZSD001_CLC/cds/ZSD001_I_ORDER.bdef")
    ap.add_argument("--bdef-name", default=BDEF_NAME)
    ap.add_argument("--ccimp-source",
                    default="ERP/SD/ZSD001_CLC/classes/ZCL_SD001_ORDER.ccimp.abap")
    ap.add_argument("--bclass-name", default="",
                    help="behavior class adı (override; default ZCL_SD001_ORDER)")
    ap.add_argument("--srvd-name", default="")
    ap.add_argument("--srvb-name", default="")
    ap.add_argument("--expose-root", default="")
    ap.add_argument("--srvd-label", default="")
    ap.add_argument("--srvb-label", default="",
                    help="SRVB (servis bağlama) description (per-servis); boşsa "
                         "SRVD_LABEL'dan '<label> bağlama' türetilir")
    ap.add_argument("--expose-extra", default="",
                    help="virgülle ayrılmış ek expose CDS listesi")
    ap.add_argument("--package", default="",
                    help="hedef paket (default ZSD001_CLC; başka modül/paket "
                         "için ZORUNLU override — yoksa objeler yanlış pakete "
                         "yaratılır)")
    a = ap.parse_args()
    if a.package:
        PKG = a.package
    if a.bdef_name:
        BDEF_NAME = a.bdef_name
    if a.bclass_name:
        BCLASS_NAME = a.bclass_name
        BCLASS_SOURCE = (
            f"CLASS {a.bclass_name.lower()} DEFINITION\n"
            "  PUBLIC ABSTRACT FINAL\n"
            f"  FOR BEHAVIOR OF {BDEF_NAME}.\n"
            "ENDCLASS.\n\n"
            f"CLASS {a.bclass_name.lower()} IMPLEMENTATION.\n"
            "ENDCLASS.\n"
        )
    if a.srvd_name:
        SRVD_NAME = a.srvd_name
    if a.srvb_name:
        SRVB_NAME = a.srvb_name
    if a.expose_root:
        EXPOSE_CDS = a.expose_root
    if a.srvd_label:
        SRVD_LABEL = a.srvd_label
    if a.srvb_label:
        SRVB_LABEL = a.srvb_label
    if a.expose_extra:
        EXPOSE_EXTRA = [x.strip() for x in a.expose_extra.split(",")
                        if x.strip()]
    c = SAPADTClient()
    tok = csrf(c)
    ok = True
    if a.step == "discover":
        return 0 if step_discover(c) else 1
    if a.step == "types":
        return 0 if step_probe(c, "/sap/bc/adt/ddic/srvd/sourceTypes") else 1
    if a.step == "probe":
        return 0 if step_probe(c, a.url, a.accept or None) else 1
    if a.step == "cdsactivate":
        ok = step_cdsactivate(c, tok)
        if ok:
            ok = verify_active([("ZSD001_I_ORDERDEST", "ddls"), ("ZSD001_I_ORDER", "ddls"),
                                ("ZSD001_C_ORDERDEST", "ddls"), ("ZSD001_C_ORDER", "ddls")])
        return 0 if ok else 1
    if a.step == "ccimp":
        return 0 if step_ccimp(c, tok, a.transport, a.ccimp_source) else 1
    if a.step == "pbactivate":
        ok = step_pbactivate(c, tok)
        if ok:
            ok = verify_active([(BCLASS_NAME, "class")])
        return 0 if ok else 1
    if a.step == "e2e":
        return 0 if step_e2e(c) else 1
    if a.step in ("srvd", "all"):
        ok = step_srvd(c, tok, a.transport)
    if ok and a.step in ("bdef", "all"):
        ok = step_bdef(c, tok, a.transport, a.bdef_source, a.bdef_name)
    if ok and a.step in ("bclass", "all"):
        ok = step_bclass(c, tok, a.transport)
    if ok and a.step in ("bactivate", "all"):
        ok = step_bactivate(c, tok)
        if ok:
            ok = verify_active([(BCLASS_NAME, "class")])
    if ok and a.step in ("srvb", "all"):
        ok = step_srvb(c, tok, a.transport)
    if ok and a.step in ("srvbactivate", "all"):
        ok = step_srvbactivate(c, tok)
    if ok and a.step in ("publish", "all"):
        ok = step_publish(c, tok)
    if ok and a.step in ("verify", "all"):
        ok = step_verify(c)
    print(f"\n=== Sonuç: {'OK' if ok else 'FAIL/incomplete'} ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
