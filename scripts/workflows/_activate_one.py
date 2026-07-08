"""Activate a single CDS via ADT."""
import sys, urllib3, io
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'<PROJECT_ROOT>/scripts')
from sap_adt_lib import set_explicit_working_dir, SAPADTClient
set_explicit_working_dir(r'<PROJECT_ROOT>')
client = SAPADTClient()

NAME = 'ZSD001_DDL_CONTAINER_TYPES'
obj_url = f'/sap/bc/adt/ddic/ddl/sources/{NAME.lower()}'

client._invalidate_csrf_cache()
r = client.session.get(client.url + '/sap/bc/adt/discovery',
    params={'sap-client':'100','sap-language':'TR'},
    headers={'X-CSRF-Token':'Fetch'}, verify=False)
csrf = r.headers.get('X-CSRF-Token','')

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
print(f'Status: {ar.status_code}')
print(f'Has error: {has_err}')
print(f'Body (first 800 chars):')
print(ar.text[:800])
