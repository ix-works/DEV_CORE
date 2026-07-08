import sys, urllib3, requests
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
csrf = r.headers.get('X-CSRF-Token', '')
print('CSRF:', bool(csrf))

PROG_NAME = 'ZSD001_P_FITTINS_MIZAN'
PACKAGE   = 'ZSD001_CLC'
TRANSPORT = '<TRANSPORT>'
DESC      = 'Fittings Musteri Mizan Raporu'

create_body = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<program:abapProgram xmlns:program="http://www.sap.com/adt/programs/programs"'
    ' xmlns:adtcore="http://www.sap.com/adt/core"'
    ' adtcore:description="' + DESC + '"'
    ' adtcore:name="' + PROG_NAME + '"'
    ' adtcore:responsible="<SAP_USER>">'
    '<adtcore:packageRef adtcore:name="' + PACKAGE + '"/>'
    '</program:abapProgram>'
)

resp = session.post(
    url + '/sap/bc/adt/programs/programs',
    params={'corrNr': TRANSPORT},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'application/vnd.sap.adt.programs.program.v2+xml; charset=utf-8',
        'Accept': 'application/vnd.sap.adt.programs.program.v2+xml'
    },
    data=create_body.encode('utf-8')
)
print('Create status:', resp.status_code)
print(resp.text[:500])
