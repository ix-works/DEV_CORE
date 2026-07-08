"""Find ISDSCHEDGAGRMTI via DD02L lookup with CSRF token."""
import urllib3
import requests
import re

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

session = requests.Session()
session.auth = auth
session.verify = False
session.headers.update({'sap-client': client})

# Step 1: Get CSRF token + cookies
print("=== Step 1: Get CSRF token ===")
r = session.get(
    f"{url}/sap/bc/adt/discovery",
    headers={'X-CSRF-Token': 'Fetch', 'Accept': 'application/atomsvc+xml'},
    timeout=30
)
csrf = r.headers.get('X-CSRF-Token', '')
print(f"Status: {r.status_code} — CSRF: {csrf[:20] if csrf else 'NONE'}...")

if not csrf:
    print("CSRF fetch failed, exit.")
    exit(1)

# Step 2: Run SQL on DD02L to find views with target name
print("\n=== Step 2: SQL — find views starting with 'ISD' ===")
sql = "SELECT tabname FROM dd02l WHERE tabname LIKE 'ISD%' AND tabclass = 'VIEW' AND as4local = 'A' ORDER BY tabname"
r = session.post(
    f"{url}/sap/bc/adt/datapreview/freestyle",
    params={'rowNumber': 200, 'dataAging': 'true'},
    headers={
        'X-CSRF-Token': csrf,
        'Content-Type': 'text/plain',
        'Accept': 'application/xml, application/vnd.sap.adt.datapreview.table.v1+xml',
    },
    data=sql,
    timeout=30
)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    # Parse the response - looking for tabname values
    text = r.text
    print(f"Body length: {len(text)}")
    # Extract tabname values
    # The XML structure has <dataPreview:column><dataPreview:data>VALUE</dataPreview:data></dataPreview:column>
    values = re.findall(r'<dataPreview:data>([^<]+)</dataPreview:data>', text)
    print(f"Found {len(values)} values:")
    for v in values:
        if 'SCHED' in v.upper():
            print(f"  ⭐ {v}  (SCHED match)")
        else:
            print(f"  - {v}")
else:
    print(f"Body: {r.text[:1500]}")
