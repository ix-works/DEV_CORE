"""Verify SQL view name in DB via TADIR + ddl source readback."""
import sys, urllib3, io
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'<PROJECT_ROOT>/scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
set_explicit_working_dir(r'<PROJECT_ROOT>')
client = SAPADTClient()

NAME = 'ZSD001_DDL_CONTAINER_TYPES'

# 1) DDL source readback
r = client.session.get(client.url + f'/sap/bc/adt/ddic/ddl/sources/{NAME.lower()}/source/main',
    params={'sap-client':'100'}, verify=False)
print(f'--- DDL Source ({r.status_code}, {len(r.text)} bytes) ---')
print(r.text[:200])

# 2) Run SQL query to confirm physical SQL view exists
print('\n--- SQL query on ZSD001_V_CONTY ---')
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
    data=b'SELECT * FROM ZSD001_V_CONTY', verify=False)
print(f'Status: {sr.status_code}')
print(sr.text[:1000])
