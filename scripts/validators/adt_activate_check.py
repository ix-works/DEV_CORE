import requests, urllib3
urllib3.disable_warnings()

with open(r'<PROJECT_ROOT>\conn_adt') as f:
    cfg = {}
    for line in f:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            cfg[k.strip()] = v.strip()
url  = cfg.get('ADT_SAP_URL', cfg.get('URL', list(cfg.values())[0]))
user = cfg.get('ADT_USER',    cfg.get('USER', list(cfg.values())[1]))
pw   = cfg.get('ADT_PASS',    cfg.get('PASS', list(cfg.values())[2]))

session = requests.Session()
session.auth = (user, pw)
session.verify = False
session.headers.update({'sap-client': '100'})
r = session.get(url + '/sap/bc/adt/discovery',
    headers={'X-CSRF-Token': 'Fetch'})
token = r.headers.get('X-CSRF-Token', '')

act_url = url + '/sap/bc/adt/activation'
body = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
    '<adtcore:objectReference adtcore:uri="/sap/bc/adt/oo/classes/zcl_zsd001_mizan"'
    ' adtcore:name="ZCL_ZSD001_MIZAN"/>'
    '</adtcore:objectReferences>'
)
r2 = session.post(act_url, data=body.encode('utf-8'),
    headers={'X-CSRF-Token': token,
             'Content-Type': 'application/vnd.sap.adt.activation.request+xml'})
print('STATUS:', r2.status_code)
print(r2.text[:5000])
