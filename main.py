#!/usr/bin/env python3
# main.py - Thomas Scanner Launcher
# Version: 6.0 - Thomas Edition

import sys
import os
import subprocess
import time

def show_banner():
    banner = f"""
\033[94m╔═══════════════════════════════════════════════════════╗
║  \033[92mTHOMAS VOUCHER SCANNER \033[94m                              ║
║  \033[93mTelegram: @Thomas_Shelby2218 \033[94m                       ║
║  \033[96mChannel: https://t.me/Skyblue021 \033[94m                   ║
╚═══════════════════════════════════════════════════════╝\033[0m
"""
    print(banner)

def check_dependencies():
    """Check if required packages are installed"""
    required = ['aiohttp', 'ddddocr', 'cv2', 'numpy', 'requests', 'urllib3']
    missing = []

    for pkg in required:
        try:
            if pkg == 'cv2':
                import cv2
            else:
                __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"\033[93m[!] Missing packages: {', '.join(missing)}\033[0m")
        print("\033[96m[*] Installing missing packages...\033[0m")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("\033[92m[✓] All packages installed!\033[0m")
        return True
    return True

def run_scanner():
    """Run the main scanner"""
    try:
        import kenobe  # or thomas, depending on what you named the file
        import asyncio
        asyncio.run(kenobe.async_main())
    except ImportError:
        print("\033[91m[✗] Scanner module (kenobe.py) not found!\033[0m")
        print("\033[96m[*] Please make sure kenobe.py is in the same directory.\033[0m")
        return False
    except KeyboardInterrupt:
        print("\n\033[93m[!] Scanner stopped by user\033[0m")
    except Exception as e:
        print(f"\033[91m[✗] Error: {e}\033[0m")
        return False
    return True

def show_menu():
    print(f"""
\033[94m═══════════════════════════════════════════════════════\033[0m
  \033[92m1.\033[0m Start THOMAS Scanner (Password Protected)
  \033[92m2.\033[0m Install/Update Dependencies
  \033[92m3.\033[0m View Results
  \033[92m4.\033[0m Clear Results
  \033[92m5.\033[0m Exit
\033[94m═══════════════════════════════════════════════════════\033[0m
""")

def view_results():
    result_file = os.path.expanduser("~/scan_results.txt")
    if os.path.exists(result_file):
        print(f"\n\033[96m[*] Results from {result_file}:\033[0m\n")
        with open(result_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.strip():
                print(content)
            else:
                print("\033[93m[!] No results yet\033[0m")
    else:
        print("\033[93m[!] No results file found\033[0m")

def clear_results():
    result_file = os.path.expanduser("~/scan_results.txt")
    if os.path.exists(result_file):
        confirm = input("\033[93mAre you sure you want to clear all results? (y/n): \033[0m")
        if confirm.lower() == 'y':
            os.remove(result_file)
            print("\033[92m[✓] Results cleared!\033[0m")
        else:
            print("\033[93m[!] Cancelled\033[0m")
    else:
        print("\033[93m[!] No results file found\033[0m")

def main():
    os.system('clear' if os.name == 'posix' else 'cls')
    show_banner()

    check_dependencies()

    while True:
        show_menu()
        choice = input("\033[92m➜ \033[0m").strip()

        if choice == "1":
            run_scanner()
        elif choice == "2":
            check_dependencies()
        elif choice == "3":
            view_results()
        elif choice == "4":
            clear_results()
        elif choice == "5":
            print("\n\033[93m[*] Exiting...\033[0m")
            break
        else:
            print("\033[91m[✗] Invalid choice!\033[0m")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\033[93m[*] Exiting...\033[0m")
    except Exception as e:
        print(f"\033[91m[✗] Error: {e}\033[0m")
