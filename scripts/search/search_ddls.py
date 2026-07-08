"""Search ADT for DDLS matching pattern."""
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

# Search ADT for objects matching various SA-related patterns
patterns = [
    'I_SCHEDULINGAGREEMENT*',
    'I_SDSCHEDU*',
    'I_SD_SCHED*',
    'I_SCHEDAGRMT*',
    'C_SCHEDULINGAGREEMENT*',
    'I_SchAgrmt*',
    'I_SCHEDG_AGRMT*',
]

for pat in patterns:
    print(f"\n========== Searching: {pat} ==========")
    r = requests.get(
        f"{url}/sap/bc/adt/repository/informationsystem/search",
        params={'operation': 'quickSearch', 'query': pat, 'maxResults': 30, 'objectType': 'DDLS/DF'},
        auth=auth, headers=headers, verify=False, timeout=30
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        # Parse simple — show first 4000 chars
        text = r.text
        print(text[:4000])
    else:
        print(f"Body: {r.text[:300]}")
