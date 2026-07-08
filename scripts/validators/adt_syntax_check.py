import sys, requests, urllib3
urllib3.disable_warnings()
sys.path.insert(0, r'C:\Users\<USER>\.config\opencode\ntt-marketplace\plugins\abaper\skills\sap-adt\scripts')

with open(r'<PROJECT_ROOT>\conn_adt') as f:
    cfg = {}
    for line in f:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            cfg[k.strip()] = v.strip()

url  = cfg['ADT_SAP_URL']
user = cfg['ADT_SAP_USER']
pw   = cfg['ADT_SAP_PASSWORD']

session = requests.Session()
session.auth = (user, pw)
session.verify = False
session.headers.update({'sap-client': '100'})

r = session.get(url + '/sap/bc/adt/discovery', headers={'X-CSRF-Token': 'Fetch'})
token = r.headers.get('X-CSRF-Token', '')
print('CSRF Token:', bool(token))

# Activation to get full error messages
act_url = url + '/sap/bc/adt/activation?method=activate&preauditRequested=false'
body = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<adtcore:objectReferences xmlns:adtcore="http://www.sap.com/adt/core">'
    '<adtcore:objectReference adtcore:uri="/sap/bc/adt/oo/classes/zcl_zsd009_mizan"'
    ' adtcore:name="ZCL_ZSD001_MIZAN"/>'
    '</adtcore:objectReferences>'
)
r2 = session.post(act_url, data=body.encode('utf-8'),
    headers={'X-CSRF-Token': token,
             'Content-Type': 'application/vnd.sap.adt.activation.request+xml',
             'Accept': 'application/xml, application/vnd.sap.adt.activation.result+xml'})
print('Activation status:', r2.status_code)
print(r2.text[:8000])
