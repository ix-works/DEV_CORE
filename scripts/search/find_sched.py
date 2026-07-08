"""Find SCHED-related CDS views in DD02L."""
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

# CSRF
r = session.get(f"{url}/sap/bc/adt/discovery", headers={'X-CSRF-Token': 'Fetch'})
csrf = r.headers.get('X-CSRF-Token', '')
print(f"CSRF: {'OK' if csrf else 'FAIL'}\n")

# Various queries to find scheduling agreement related views
queries = [
    ("ISDSCHED*", "SELECT tabname FROM dd02l WHERE tabname LIKE 'ISDSCHED%' AND tabclass = 'VIEW' AND as4local = 'A'"),
    ("ISCHED*",   "SELECT tabname FROM dd02l WHERE tabname LIKE 'ISCHED%' AND tabclass = 'VIEW' AND as4local = 'A'"),
    ("ISCHDLG*",  "SELECT tabname FROM dd02l WHERE tabname LIKE 'ISCHDLG%' AND tabclass = 'VIEW' AND as4local = 'A'"),
    ("ISCHEDG*",  "SELECT tabname FROM dd02l WHERE tabname LIKE 'ISCHEDG%' AND tabclass = 'VIEW' AND as4local = 'A'"),
    ("ISDSC*",    "SELECT tabname FROM dd02l WHERE tabname LIKE 'ISDSC%' AND tabclass = 'VIEW' AND as4local = 'A'"),
    ("ISDSCHDLG*","SELECT tabname FROM dd02l WHERE tabname LIKE 'ISDSCHDLG%' AND tabclass = 'VIEW' AND as4local = 'A'"),
    ("Search by exact 'ISDSCHEDGAGRMTI'", "SELECT tabname FROM dd02l WHERE tabname = 'ISDSCHEDGAGRMTI'"),
    ("Search by 'ISDSASCHEDLINE'", "SELECT tabname FROM dd02l WHERE tabname = 'ISDSASCHEDLINE'"),
    ("Search ISDSA*", "SELECT tabname FROM dd02l WHERE tabname LIKE 'ISDSA%' AND tabclass = 'VIEW'"),
]

for label, sql in queries:
    print(f"\n=== {label} ===")
    r = session.post(
        f"{url}/sap/bc/adt/datapreview/freestyle",
        params={'rowNumber': 50, 'dataAging': 'true'},
        headers={'X-CSRF-Token': csrf, 'Content-Type': 'text/plain',
                 'Accept': 'application/xml, application/vnd.sap.adt.datapreview.table.v1+xml'},
        data=sql, timeout=30
    )
    if r.status_code == 200:
        values = re.findall(r'<dataPreview:data>([^<]+)</dataPreview:data>', r.text)
        print(f"  Found {len(values)} matches:")
        for v in values:
            print(f"    {v}")
    else:
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:300]}")
