#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAML SSO Login for SAP S/4HANA Cloud Public Edition (BTP Cloud)

Automates browser-based SAML login using Playwright (headless Chromium),
saves session cookies to .saml_cookies.json, and verifies authenticated
ADT access.

Usage:
    python login_saml_sso.py --cwd /path/to/project [--headed] [--timeout 120]

Requirements:
    pip install playwright
    playwright install chromium

After running, add to .conn_adt:
    ADT_SAML_COOKIES_FILE=.saml_cookies.json
"""
import sys
import os
import json
import argparse
from pathlib import Path
from urllib.parse import urlparse

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from sap_adt_lib import set_explicit_working_dir, find_conn_file


def load_config(cwd=None):
    """Load SAP connection config from .conn_adt."""
    if cwd:
        set_explicit_working_dir(cwd)

    conn_file = find_conn_file()
    if not conn_file:
        print('[FAIL] No .conn_adt file found. Please create one in your project directory.')
        return None

    from dotenv import load_dotenv
    load_dotenv(conn_file, override=True)

    url = os.getenv('ADT_SAP_URL', '').rstrip('/')
    user = os.getenv('ADT_SAP_USER', '')
    password = os.getenv('ADT_SAP_PASSWORD', '')

    if not url:
        print('[FAIL] ADT_SAP_URL not set in .conn_adt')
        return None

    explicit_dir = Path(cwd) if cwd else conn_file.parent
    cookies_file = explicit_dir / '.saml_cookies.json'

    return {
        'url': url,
        'username': user,
        'password': password,
        'cookies_file': cookies_file,
        'host': urlparse(url).netloc,
    }


def fill_login_form(page, username, password):
    """Attempt to fill SAML IdP login form fields."""
    USER_SELECTOR = "input[type='email'], input[name='logonuidfield'], input[name='username'], input[id*='email'], input[id*='user'], input[type='text']"
    SUBMIT_SELECTOR = "input[type='submit'], button[type='submit'], button[id*='submit'], button[id*='next']"
    try:
        page.wait_for_selector(USER_SELECTOR, timeout=15000, state='visible')
        user_field = page.locator(USER_SELECTOR).first
        user_field.fill(username)

        # Some IdPs show password on same page; others need a "Next" click first
        password_visible = False
        try:
            page.locator("input[type='password']").first.wait_for(state='visible', timeout=2000)
            password_visible = True
        except Exception:
            pass

        if not password_visible:
            try:
                page.locator(SUBMIT_SELECTOR).first.click()
                page.wait_for_selector("input[type='password']", timeout=10000, state='visible')
            except Exception:
                pass

        page.locator("input[type='password']").first.fill(password)
        page.locator(SUBMIT_SELECTOR).first.click()
        print('[INFO] Login form submitted.')
    except Exception as e:
        print(f'[WARN] Could not auto-fill login form: {e}')
        print('[INFO] If using --headed mode, complete login manually in the browser.')


def run_playwright_login(config, headed=False, timeout_sec=120):
    """Run Playwright to complete SAML login and capture cookies."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print('[FAIL] Playwright not installed.')
        print('[ACTION] Run: pip install playwright && playwright install chromium')
        return False

    timeout_ms = timeout_sec * 1000
    start_url = config['url'] + '/sap/bc/adt/discovery'
    sap_host = config['host']
    cookies_file = config['cookies_file']
    username = config['username']
    password = config['password']

    print(f'[INFO] Starting {"headed" if headed else "headless"} Playwright browser...')
    print(f'[INFO] Navigating to: {start_url}')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        page.goto(start_url, wait_until='domcontentloaded', timeout=timeout_ms)

        # Always attempt form fill — some IdPs redirect while staying on same domain
        # or use embedded iframes. Try login form regardless of current host.
        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except Exception:
            pass

        current_url = page.url
        if sap_host not in urlparse(current_url).netloc:
            print(f'[INFO] Redirected to IdP: {current_url}')

        if username and password:
            fill_login_form(page, username, password)
            # Wait for navigation after form submit (explicit networkidle, not fixed sleep)
            try:
                page.wait_for_load_state('networkidle', timeout=30000)
            except Exception:
                pass
        else:
            print('[INFO] No credentials in .conn_adt — complete login manually in browser.')

        # Wait for return to SAP host
        print('[INFO] Waiting for SAML assertion to complete...')
        deadline_ms = timeout_ms
        waited = 0
        while waited < deadline_ms:
            try:
                page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:
                pass
            if sap_host in urlparse(page.url).netloc:
                print(f'[INFO] Back on SAP host: {page.url}')
                break
            # Wait for any navigation event before polling again
            try:
                page.wait_for_url(f'**{sap_host}**', timeout=5000)
                break
            except Exception:
                pass
            waited += 10000
        else:
            print(f'[WARN] Timed out waiting to return to SAP host. Current URL: {page.url}')
            if not headed:
                browser.close()
                return False

        # Save cookies
        cookies = context.cookies()
        sap_cookies = {c['name']: c['value'] for c in cookies}
        data = {'cookies': sap_cookies, 'session_cookies': cookies}

        cookies_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        print(f'[OK] Saved {len(cookies)} cookies to: {cookies_file}')

        # Check for SAP session ID
        sap_session = next((c for c in cookies if c['name'].startswith('SAP_SESSIONID')), None)
        if sap_session:
            val = sap_session['value']
            print(f'[OK] SAP_SESSIONID found: ...{val[-20:]}')
        else:
            print('[WARN] SAP_SESSIONID not found — login may have failed.')

        browser.close()

    return True


def verify_cookies(config):
    """Verify the saved cookies actually work against a real authenticated ADT endpoint."""
    import requests
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    cookies_file = config['cookies_file']
    if not cookies_file.exists():
        print('[FAIL] Cookie file not found for verification.')
        return False

    data = json.loads(cookies_file.read_text(encoding='utf-8'))
    session = requests.Session()
    session.verify = False
    for c in data.get('session_cookies', []):
        session.cookies.set(c['name'], c['value'], domain=config['host'])

    # Probe a real authenticated endpoint
    probe_url = config['url'] + '/sap/bc/adt/repository/informationsystem/search'
    params = {'operation': 'quickSearch', 'query': 'T000', 'objectType': 'TABL', 'maxResults': '1'}
    try:
        resp = session.get(probe_url, params=params,
                           headers={'Accept': 'application/xml'}, timeout=30)
        ctype = resp.headers.get('Content-Type', '')
        body_start = resp.text[:100].lstrip().lower()
        if resp.status_code == 200 and 'html' not in ctype and not body_start.startswith('<html'):
            print('[OK] Authenticated ADT probe succeeded — cookies are valid.')
            return True
        else:
            print(f'[FAIL] ADT probe returned HTTP {resp.status_code} with Content-Type: {ctype}')
            if 'html' in body_start or 'html' in ctype:
                print('[FAIL] Got HTML login page — session cookies may have expired or login failed.')
            return False
    except Exception as e:
        print(f'[FAIL] ADT probe error: {e}')
        return False


def print_conn_adt_snippet(cookies_file):
    """Print the .conn_adt line the user needs to add."""
    print()
    print('=' * 60)
    print('[ACTION] Add the following line to your .conn_adt file:')
    print(f'  ADT_SAML_COOKIES_FILE={cookies_file.name}')
    print('=' * 60)


def main():
    parser = argparse.ArgumentParser(
        description='SAML SSO Login for SAP S/4HANA Cloud Public Edition'
    )
    parser.add_argument('--cwd', help='Project directory containing .conn_adt')
    parser.add_argument('--headed', action='store_true',
                        help='Run browser in visible (headed) mode for manual login/MFA')
    parser.add_argument('--timeout', type=int, default=120,
                        help='Login timeout in seconds (default: 120)')
    parser.add_argument('--no-verify', action='store_true',
                        help='Skip cookie verification after login')
    args = parser.parse_args()

    print('=' * 60)
    print('SAP S/4HANA Cloud SAML SSO Login')
    print('=' * 60)

    config = load_config(args.cwd)
    if not config:
        return 1

    print(f'[INFO] System URL : {config["url"]}')
    print(f'[INFO] Username   : {config["username"] or "(not set)"}')
    print(f'[INFO] Cookie file: {config["cookies_file"]}')
    print()

    ok = run_playwright_login(config, headed=args.headed, timeout_sec=args.timeout)
    if not ok:
        return 1

    if not args.no_verify:
        print()
        print('[INFO] Verifying cookies against authenticated ADT endpoint...')
        verify_cookies(config)

    print_conn_adt_snippet(config['cookies_file'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
