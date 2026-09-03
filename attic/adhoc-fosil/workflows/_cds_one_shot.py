"""Tek CDS için: yarat + aktive et + DB SQL view doğrula. Tek atış."""
import sys, urllib3, io, re, argparse, subprocess
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'<PROJECT_ROOT>/scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
from pathlib import Path
set_explicit_working_dir(r'<PROJECT_ROOT>')

p = argparse.ArgumentParser()
p.add_argument('name', help='CDS name e.g. ZSD001_DDL_SHIPPING_TYPES')
args = p.parse_args()

NAME = args.name.upper()
src_path = Path(f'<PROJECT_ROOT>/<source_root>/ZSD001_CLC/cds_src/{NAME}.cds')
if not src_path.exists():
    print(f'[FAIL] {src_path} yok')
    sys.exit(1)

src = src_path.read_text(encoding='utf-8')
sv_match = re.search(r"@AbapCatalog\.sqlViewName\s*:\s*'([^']+)'", src)
if not sv_match:
    print(f'[FAIL] sqlViewName bulunamadı')
    sys.exit(1)
SQL_VIEW = sv_match.group(1)
print(f'=== {NAME} ===')
print(f'sqlViewName: {SQL_VIEW}')

# 1) create via populate_cds_views.py (pre-flight kontrol + force-recreate)
print(f'\n--- [1/3] CREATE (force-recreate) ---')
r = subprocess.run([
    sys.executable,
    r'<PROJECT_ROOT>/scripts/populate_cds_views.py',
    '--package','ZSD001_CLC','--transport','<TRANSPORT>',
    '--source-dir', r'<PROJECT_ROOT>/<source_root>/ZSD001_CLC/cds_src',
    '--cwd', r'<PROJECT_ROOT>',
    '--only', NAME, '--force-recreate'
], capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout)
if r.returncode != 0:
    print(r.stderr)
    print(f'[FAIL] CREATE return={r.returncode}')
    sys.exit(1)

# 2) Activate
print(f'--- [2/3] ACTIVATE ---')
client = SAPADTClient()
obj_url = f'/sap/bc/adt/ddic/ddl/sources/{NAME.lower()}'
client._invalidate_csrf_cache()
fr = client.session.get(client.url + '/sap/bc/adt/discovery',
    params={'sap-client':'100','sap-language':'TR'},
    headers={'X-CSRF-Token':'Fetch'}, verify=False)
csrf = fr.headers.get('X-CSRF-Token','')
body = ('<?xml version="1.0"?>'
        '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
        f'<adtcore:objectReference adtcore:uri="{obj_url}" adtcore:type="DDLS/DF" adtcore:name="{NAME}"/>'
        '</adtcore:objectReferences>')
ar = client.session.post(client.url + '/sap/bc/adt/activation',
    params={'method':'activate','preauditRequested':'true'},
    headers={'X-CSRF-Token':csrf,'Content-Type':'application/xml'},
    data=body.encode('utf-8'), verify=False)
err_marker = 'type="E"'
has_err = err_marker in ar.text
print(f'Status: {ar.status_code}, has_error: {has_err}')
if has_err:
    # Print error messages
    for m in re.finditer(r'<chkl:message[^>]*type="E"[^>]*>.*?</chkl:message>', ar.text, re.DOTALL):
        print(f'  ERR: {m.group(0)[:400]}')
    # Also show raw last 800 chars
    print(f'Body tail: {ar.text[-800:]}')
    sys.exit(1)

# 3) Verify: SELECT * FROM <sqlview> LIMIT 5
print(f'\n--- [3/3] VERIFY DB ({SQL_VIEW}) ---')
client._invalidate_csrf_cache()
fr = client.session.get(client.url + '/sap/bc/adt/discovery',
    params={'sap-client':'100','sap-language':'TR'},
    headers={'X-CSRF-Token':'Fetch'}, verify=False)
csrf = fr.headers.get('X-CSRF-Token','')
sr = client.session.post(client.url + '/sap/bc/adt/datapreview/freestyle',
    params={'rowNumber':'5','dataAging':'true'},
    headers={'X-CSRF-Token':csrf,
             'Content-Type':'text/plain',
             'Accept':'application/xml,application/vnd.sap.adt.datapreview.table.v1+xml'},
    data=f'SELECT * FROM {SQL_VIEW}'.encode('utf-8'), verify=False)
total = re.search(r'<dataPreview:totalRows>(\d+)</dataPreview:totalRows>', sr.text)
print(f'SQL status: {sr.status_code}, totalRows: {total.group(1) if total else "?"}')
if sr.status_code != 200:
    print(f'Body: {sr.text[:600]}')
    sys.exit(1)

print(f'\n[OK] {NAME} → {SQL_VIEW} yaratıldı + aktif + sorgulanabilir')
