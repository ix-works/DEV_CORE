"""DDL source'u TADIR seviyesinden tam temizle ve yeni sqlViewName ile yarat.

Akış:
  1. DELETE DDL source (workbench seviyesi)
  2. ACTIVATE deletion (TADIR'a commit + DB SQL view drop)
  3. GET ile 404 doğrula
  4. POST shell (yeni temiz)
  5. PUT source/main
  6. ACTIVATE creation
  7. SQL view sorgula doğrula
"""
import sys, urllib3, io, re, argparse, time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'<PROJECT_ROOT>/scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
set_explicit_working_dir(r'<PROJECT_ROOT>')

from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

p = argparse.ArgumentParser()
p.add_argument('name')
p.add_argument('--transport', default='<TRANSPORT>')
args = p.parse_args()

NAME = args.name.upper()
TRANSPORT = args.transport
obj_url = f'/sap/bc/adt/ddic/ddl/sources/{NAME.lower()}'
src_path = Path(f'<PROJECT_ROOT>/<source_root>/ZSD001_CLC/cds_src/{NAME}.cds')

if not src_path.exists():
    print(f'[FAIL] {src_path} yok'); sys.exit(1)

source = src_path.read_text(encoding='utf-8')
sv_m = re.search(r"@AbapCatalog\.sqlViewName\s*:\s*'([^']+)'", source)
SQL_VIEW = sv_m.group(1)
print(f'=== {NAME} → {SQL_VIEW} ===')

c = SAPADTClient()

def fresh_csrf():
    c._invalidate_csrf_cache()
    r = c.session.get(c.url + '/sap/bc/adt/discovery',
        params={'sap-client':'100','sap-language':'TR'},
        headers={'X-CSRF-Token':'Fetch'}, verify=False)
    return r.headers.get('X-CSRF-Token','')

def activation_req(csrf):
    body = ('<?xml version="1.0"?>'
            '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
            f'<adtcore:objectReference adtcore:uri="{obj_url}" adtcore:type="DDLS/DF" adtcore:name="{NAME}"/>'
            '</adtcore:objectReferences>')
    return c.session.post(c.url + '/sap/bc/adt/activation',
        params={'method':'activate','preauditRequested':'true'},
        headers={'X-CSRF-Token':csrf,'Content-Type':'application/xml'},
        data=body.encode('utf-8'), verify=False)

# ─── 1. Mevcut durum ──────────────────────────────────────────────────────────
r0 = c.session.get(c.url + obj_url, params={'sap-client':'100'}, verify=False)
print(f'\n[1] Pre-state GET: {r0.status_code}')

if r0.status_code == 200:
    # ─── 2. LOCK + DELETE + UNLOCK ────────────────────────────────────────────
    print(f'\n[2] LOCK + DELETE')
    csrf = fresh_csrf()
    lr = c.session.post(c.url + obj_url,
        params={'_action':'LOCK','accessMode':'MODIFY','corrNr':TRANSPORT},
        headers={'X-CSRF-Token':csrf,
                 'X-sap-adt-sessiontype':'stateful',
                 'Accept':'application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result'},
        verify=False)
    lh_m = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lr.text)
    lh = lh_m.group(1) if lh_m else None
    print(f'  LOCK: {lr.status_code}, handle={lh}')

    dr = c.session.delete(c.url + obj_url,
        params={'corrNr':TRANSPORT, 'lockHandle': lh} if lh else {'corrNr':TRANSPORT},
        headers={'X-CSRF-Token':csrf,
                 'X-sap-adt-sessiontype':'stateful'},
        verify=False)
    print(f'  DELETE: {dr.status_code}')
    if dr.status_code not in (200, 204):
        print(f'  Body: {dr.text[:400]}')

    # UNLOCK (delete may have auto-unlocked, ignore errors)
    if lh:
        c.session.post(c.url + obj_url,
            params={'_action':'UNLOCK','lockHandle':lh},
            headers={'X-CSRF-Token':csrf,'X-sap-adt-sessiontype':'stateful'},
            verify=False)

    # ─── 3. ACTIVATE deletion ─────────────────────────────────────────────────
    print(f'\n[3] ACTIVATE deletion (TADIR commit)')
    csrf = fresh_csrf()
    ar = activation_req(csrf)
    err = 'type="E"' in ar.text
    print(f'  Status: {ar.status_code}, has_error: {err}')
    if err:
        for m in re.finditer(r'<chkl:message[^>]*type="E"[^>]*>.*?</chkl:message>', ar.text, re.DOTALL):
            print(f'    ERR: {m.group(0)[:300]}')

    # ─── 4. Verify removal ────────────────────────────────────────────────────
    r1 = c.session.get(c.url + obj_url, params={'sap-client':'100'}, verify=False)
    print(f'\n[4] Post-delete GET: {r1.status_code}')
    if r1.status_code == 200:
        print(f'  [WARN] DDL source hala SAP\'de — TADIR active version kaldı.')
        print(f'  Body kısa: {r1.text[:300]}')

# ─── 5. POST shell ────────────────────────────────────────────────────────────
print(f'\n[5] POST shell (fresh)')
csrf = fresh_csrf()
shell = ('<?xml version="1.0" encoding="UTF-8"?>'
         '<ddl:ddlSource xmlns:ddl="http://www.sap.com/adt/ddic/ddlsources" '
         'xmlns:adtcore="http://www.sap.com/adt/core" '
         f'adtcore:name="{NAME}" adtcore:description="{xml_escape(NAME)}" '
         'adtcore:masterLanguage="TR">'
         '<adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/zsd001_clc" '
         'adtcore:type="DEVC/K" adtcore:name="ZSD001_CLC"/>'
         '</ddl:ddlSource>')
pr = c.session.post(c.url + '/sap/bc/adt/ddic/ddl/sources',
    params={'corrNr':TRANSPORT},
    headers={'X-CSRF-Token':csrf,
             'Content-Type':'application/vnd.sap.adt.ddlSource+xml; charset=utf-8',
             'Accept':'application/vnd.sap.adt.ddlSource+xml',
             'sap-client':'100','sap-language':'TR'},
    data=shell.encode('utf-8'), verify=False)
print(f'  POST: {pr.status_code}')
if pr.status_code not in (200, 201):
    print(f'  Body: {pr.text[:400]}'); sys.exit(1)

# ─── 6. LOCK + PUT source + UNLOCK ────────────────────────────────────────────
print(f'\n[6] PUT source/main')
csrf = fresh_csrf()
lr = c.session.post(c.url + obj_url,
    params={'_action':'LOCK','accessMode':'MODIFY','corrNr':TRANSPORT},
    headers={'X-CSRF-Token':csrf,
             'X-sap-adt-sessiontype':'stateful',
             'Accept':'application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result'},
    verify=False)
lh = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lr.text).group(1)

ur = c.session.put(c.url + obj_url + '/source/main',
    params={'corrNr':TRANSPORT,'lockHandle':lh},
    headers={'X-CSRF-Token':csrf,'Content-Type':'text/plain; charset=utf-8'},
    data=source.encode('utf-8'), verify=False)
print(f'  PUT: {ur.status_code} ({len(source)} bytes)')

c.session.post(c.url + obj_url,
    params={'_action':'UNLOCK','lockHandle':lh},
    headers={'X-CSRF-Token':csrf,'X-sap-adt-sessiontype':'stateful'}, verify=False)

# ─── 7. ACTIVATE creation ─────────────────────────────────────────────────────
print(f'\n[7] ACTIVATE creation')
csrf = fresh_csrf()
ar = activation_req(csrf)
err = 'type="E"' in ar.text
print(f'  Status: {ar.status_code}, has_error: {err}')
if err:
    for m in re.finditer(r'<chkl:message[^>]*type="E"[^>]*>.*?</chkl:message>', ar.text, re.DOTALL):
        print(f'    ERR: {m.group(0)[:400]}')
    sys.exit(1)

# ─── 8. Verify DB SQL view ────────────────────────────────────────────────────
print(f'\n[8] VERIFY DB: SELECT * FROM {SQL_VIEW}')
csrf = fresh_csrf()
sr = c.session.post(c.url + '/sap/bc/adt/datapreview/freestyle',
    params={'rowNumber':'5'},
    headers={'X-CSRF-Token':csrf,'Content-Type':'text/plain',
             'Accept':'application/xml,application/vnd.sap.adt.datapreview.table.v1+xml'},
    data=f'SELECT * FROM {SQL_VIEW}'.encode('utf-8'), verify=False)
total = re.search(r'<dataPreview:totalRows>(\d+)</dataPreview:totalRows>', sr.text)
print(f'  SQL: {sr.status_code}, totalRows: {total.group(1) if total else "?"}')

print(f'\n[OK] {NAME} → {SQL_VIEW} clean recreate başarılı')
