import requests, urllib3
urllib3.disable_warnings()

with open(r'<PROJECT_ROOT>\conn_adt') as f:
    cfg = {k.strip(): v.strip() for l in f if '=' in l for k, v in [l.split('=', 1)]}

url  = cfg['ADT_SAP_URL']
user = cfg['ADT_SAP_USER']
pw   = cfg['ADT_SAP_PASSWORD']

session = requests.Session()
session.auth = (user, pw)
session.verify = False
session.headers.update({'sap-client': '100'})

r = session.get(url + '/sap/bc/adt/discovery', headers={'X-CSRF-Token': 'Fetch'})
token = r.headers.get('X-CSRF-Token', '')

act_url = url + '/sap/bc/adt/activation?method=activate&preauditRequested=false'
body = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
    '<adtcore:objectReference adtcore:uri="/sap/bc/adt/programs/programs/zsd001_p_fittins_mizan"'
    ' adtcore:name="ZSD001_P_FITTINS_MIZAN"/>'
    '</adtcore:objectReferences>'
)
r2 = session.post(act_url, data=body.encode('utf-8'),
    headers={'X-CSRF-Token': token,
             'Content-Type': 'application/vnd.sap.adt.activation.request+xml',
             'Accept': 'application/xml, application/vnd.sap.adt.activation.result+xml'})
print('Status:', r2.status_code)
print(r2.text[:4000])
