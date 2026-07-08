"""Tam temizleme + fresh yaratma — library activate_object kullanarak.

Adımlar:
  1. Mevcut DDL source varsa: LOCK + DELETE + activate-deletion (library)
  2. Verify GET 404
  3. POST shell + LOCK + PUT + UNLOCK
  4. activate-creation (library 2-phase)
  5. Verify SQL view DB'de
"""
import sys, urllib3, io, re, time, argparse
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
src_path = Path(f'<PROJECT_ROOT>/ERP/ZSD001_CLC/cds_src/{NAME}.cds')
source = src_path.read_text(encoding='utf-8')
sv_m = re.search(r"@AbapCatalog\.sqlViewName\s*:\s*'([^']+)'", source)
SQL_VIEW = sv_m.group(1)

print(f'=== {NAME} → {SQL_VIEW} ===')
c = SAPADTClient()

# Helper
def fresh_csrf():
    c._invalidate_csrf_cache()
    r = c.session.get(c.url + '/sap/bc/adt/discovery',
        params={'sap-client':'100','sap-language':'TR'},
        headers={'X-CSRF-Token':'Fetch'}, verify=False)
    return r.headers.get('X-CSRF-Token','')

# Clear any pending lock first
try: c.clear_enqueue_lock(object_url=obj_url)
except: pass

# ─── 1. Mevcut DDL source var mı ──────────────────────────────────────────────
r = c.session.get(c.url + obj_url, params={'sap-client':'100'}, verify=False)
print(f'\n[1] Pre GET: {r.status_code}')

if r.status_code == 200:
    print(f'\n[2] Var — LOCK + DELETE + activate-deletion')
    csrf = fresh_csrf()
    # LOCK
    lr = c.session.post(c.url + obj_url,
        params={'_action':'LOCK','accessMode':'MODIFY','corrNr':TRANSPORT},
        headers={'X-CSRF-Token':csrf,
                 'X-sap-adt-sessiontype':'stateful',
                 'Accept':'application/*,application/vnd.sap.as+xml;dataname=com.sap.adt.lock.result'},
        verify=False)
    lh_m = re.search(r'<LOCK_HANDLE[^>]*>([^<]+)</LOCK_HANDLE>', lr.text)
    if not lh_m:
        print(f'  LOCK FAIL: {lr.status_code}'); sys.exit(1)
    lh = lh_m.group(1)

    # DELETE
    dr = c.session.delete(c.url + obj_url,
        params={'corrNr':TRANSPORT,'lockHandle':lh},
        headers={'X-CSRF-Token':csrf,'X-sap-adt-sessiontype':'stateful'}, verify=False)
    print(f'  DELETE: {dr.status_code}')

    # UNLOCK explicit (delete bazen lock bırakıyor)
    ur1 = c.session.post(c.url + obj_url,
        params={'_action':'UNLOCK','lockHandle':lh},
        headers={'X-CSRF-Token':csrf,'X-sap-adt-sessiontype':'stateful'}, verify=False)
    print(f'  UNLOCK after DELETE: {ur1.status_code}')

    # Activate deletion (kendi yöntem)
    body = ('<?xml version="1.0"?>'
            '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
            f'<adtcore:objectReference adtcore:uri="{obj_url}" adtcore:type="DDLS/DF" adtcore:name="{NAME}"/>'
            '</adtcore:objectReferences>')
    ar = c.session.post(c.url + '/sap/bc/adt/activation',
        params={'method':'activate','preauditRequested':'true'},
        headers={'X-CSRF-Token':csrf,
                 'Content-Type':'application/xml',
                 'Accept':'application/vnd.sap.adt.objectactivation.result.v1+xml'},
        data=body.encode('utf-8'), verify=False)
    has_e = 'type="E"' in ar.text
    print(f'  activate-deletion: {ar.status_code}, has_err={has_e}')

    time.sleep(1)
    r2 = c.session.get(c.url + obj_url, params={'sap-client':'100'}, verify=False)
    print(f'  Post-delete GET: {r2.status_code}')

# ─── 3. POST shell ────────────────────────────────────────────────────────────
print(f'\n[3] POST shell (fresh)')
csrf = fresh_csrf()
shell = ('<?xml version="1.0" encoding="UTF-8"?>'
         '<ddl:ddlSource xmlns:ddl="http://www.sap.com/adt/ddic/ddlsources" '
         'xmlns:adtcore="http://www.sap.com/adt/core" '
         f'adtcore:name="{NAME}" adtcore:description="{xml_escape(NAME)}" '
         'adtcore:masterLanguage="TR">'
         '<adtcore:packageRef adtcore:uri="/sap/bc/adt/packages/zsd015_clc" '
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

# ─── 4. LOCK + PUT source ─────────────────────────────────────────────────────
print(f'\n[4] LOCK + PUT source/main')
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

# ─── 5. ACTIVATE creation (kendi yöntem) ──────────────────────────────────────
print(f'\n[5] activate-creation')
csrf = fresh_csrf()
body = ('<?xml version="1.0"?>'
        '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
        f'<adtcore:objectReference adtcore:uri="{obj_url}" adtcore:type="DDLS/DF" adtcore:name="{NAME}"/>'
        '</adtcore:objectReferences>')
ar = c.session.post(c.url + '/sap/bc/adt/activation',
    params={'method':'activate','preauditRequested':'true'},
    headers={'X-CSRF-Token':csrf,'Content-Type':'application/xml',
             'Accept':'application/vnd.sap.adt.objectactivation.result.v1+xml'},
    data=body.encode('utf-8'), verify=False)
has_e = 'type="E"' in ar.text
print(f'  status: {ar.status_code}, has_err: {has_e}')
if has_e:
    for m in re.finditer(r'<txt>([^<]+)</txt>', ar.text):
        print(f'    {m.group(1)}')
    sys.exit(1)

# ─── 6. Verify SQL view DB ────────────────────────────────────────────────────
print(f'\n[6] VERIFY DB: SELECT * FROM {SQL_VIEW}')
csrf = fresh_csrf()
sr = c.session.post(c.url + '/sap/bc/adt/datapreview/freestyle',
    params={'rowNumber':'5'},
    headers={'X-CSRF-Token':csrf,'Content-Type':'text/plain',
             'Accept':'application/xml,application/vnd.sap.adt.datapreview.table.v1+xml'},
    data=f'SELECT * FROM {SQL_VIEW}'.encode('utf-8'), verify=False)
total = re.search(r'<dataPreview:totalRows>(\d+)</dataPreview:totalRows>', sr.text)
print(f'  SQL: {sr.status_code}, totalRows: {total.group(1) if total else "?"}')

print(f'\n[OK] {NAME} → {SQL_VIEW} TAMAM')
