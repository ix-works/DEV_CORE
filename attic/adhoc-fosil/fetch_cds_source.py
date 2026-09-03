"""
Fetch a CDS view source from SAP ADT REST API.
Usage: python fetch_cds_source.py <CDS_NAME>
"""
import sys
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Read .conn_adt
conn = {}
with open(r'<PROJECT_ROOT>\.conn_adt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line:
            k, v = line.split('=', 1)
            conn[k] = v

url = conn['ADT_SAP_URL']
user = conn['ADT_SAP_USER']
pwd = conn['ADT_SAP_PASSWORD']
client = conn['ADT_SAP_CLIENT']

def fetch_ddls(name):
    """Try ADT endpoint for DDLS source."""
    endpoint = f"{url}/sap/bc/adt/ddic/ddl/sources/{name}"
    params = {'content': 'true'}
    headers = {'sap-client': client, 'Accept': 'application/vnd.sap.adt.ddlSource+xml'}
    try:
        r = requests.get(endpoint, params=params, auth=(user, pwd),
                         headers=headers, verify=False, timeout=30)
        return r.status_code, r.text, r.headers
    except Exception as e:
        return None, str(e), {}


# Try multiple name variants
candidates = sys.argv[1:] if len(sys.argv) > 1 else [
    'I_SDScheduleAgreementItem',
    'ISDSCHEDGAGRMTI',
    'I_SD_SCHED_AGRMT_ITM',
]

for name in candidates:
    print(f"\n===== Trying: {name} =====")
    status, body, headers = fetch_ddls(name)
    print(f"Status: {status}")
    if status == 200:
        print(f"Content-Type: {headers.get('Content-Type', '?')}")
        print(f"--- BODY (first 6000 chars) ---")
        print(body[:6000])
        if len(body) > 6000:
            print(f"\n... [{len(body) - 6000} more chars truncated]")
        break
    else:
        # Show first 500 chars of error response
        print(f"Body preview: {body[:500]}")
