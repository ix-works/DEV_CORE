"""Wider search for SA-related CDS — also try by SQL view name."""
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

conn = {}
with open(r'<PROJECT_ROOT>\.conn_adt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line:
            k, v = line.split('=', 1)
            conn[k] = v

url = conn['ADT_SAP_URL']
auth = (conn['ADT_SAP_USER'], conn['ADT_SAP_PASSWORD'])
client = conn['ADT_SAP_CLIENT']
headers = {'sap-client': client, 'Accept': 'application/xml'}

# Search ADT — try DDLS prefix and also try without object filter (catch CDS DBs)
patterns_with_type = [
    ('ISD*',                  'DDLS/DF'),
    ('I_SD*',                 'DDLS/DF'),
    ('ISDSCHED*',             'DDLS/DF'),
    ('ISDSCHEDG*',            'DDLS/DF'),
    ('ISDSCH*',               'DDLS/DF'),
]

for pat, otype in patterns_with_type:
    print(f"\n========== Searching {pat} (type={otype}) ==========")
    r = requests.get(
        f"{url}/sap/bc/adt/repository/informationsystem/search",
        params={'operation': 'quickSearch', 'query': pat, 'maxResults': 30, 'objectType': otype},
        auth=auth, headers=headers, verify=False, timeout=30
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        text = r.text
        # Count matches
        import re
        names = re.findall(r'adtcore:name="([^"]+)"', text)
        print(f"Matches ({len(names)}):")
        for n in names[:30]:
            print(f"  - {n}")
