"""Find DDLS by SQL view name via DD02L lookup using ADT data preview."""
import urllib3
import requests
from xml.sax.saxutils import escape

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

# Method 1: Try ADT freestyle SQL preview to query DD02L for tabname like '%SCHEDG%'
# Endpoint: POST /sap/bc/adt/datapreview/freestyle
# Body: SQL query
print("=== Method 1: SQL via ADT data preview ===")
sql_query = "SELECT tabname FROM dd02l WHERE tabname LIKE 'ISD%' AND tabclass = 'VIEW' AND as4local = 'A'"
r = requests.post(
    f"{url}/sap/bc/adt/datapreview/freestyle",
    params={'rowNumber': 100, 'dataAging': 'true'},
    auth=auth,
    headers={'sap-client': client, 'Content-Type': 'text/plain', 'Accept': 'application/xml, application/vnd.sap.adt.datapreview.table.v1+xml'},
    data=sql_query,
    verify=False, timeout=30
)
print(f"Status: {r.status_code}")
print(r.text[:4000])

# Method 2: Try direct ADT search with various patterns
print("\n=== Method 2: Search SQL view 'ISDSCHEDGAGRMTI' as obj name ===")
for pat in ['ISDSCHEDGAGRMTI', 'ISDSCHEDGAGRMTI*', '*SCHEDGAGRMT*', '*SCHEDG*']:
    r = requests.get(
        f"{url}/sap/bc/adt/repository/informationsystem/search",
        params={'operation': 'quickSearch', 'query': pat, 'maxResults': 30},
        auth=auth,
        headers={'sap-client': client, 'Accept': 'application/xml'},
        verify=False, timeout=30
    )
    import re
    names = re.findall(r'adtcore:name="([^"]+)" adtcore:type="([^"]+)"', r.text)
    print(f"Pattern '{pat}': {len(names)} matches")
    for n, t in names[:15]:
        print(f"  - [{t}] {n}")
