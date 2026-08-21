import os
import sys
import time

class NeonHUD:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def boot_sequence():
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"{NeonHUD.CYAN}=================================================={NeonHUD.END}")
    print(f"{NeonHUD.BOLD}{NeonHUD.MAGENTA}       ⚡ ECHO PRO 2026: SOVEREIGN NODE ⚡       {NeonHUD.END}")
    print(f"{NeonHUD.CYAN}=================================================={NeonHUD.END}")
    print(f"{NeonHUD.YELLOW}[*] Initializing local decentralized environment...{NeonHUD.END}")
    time.sleep(0.5)
    print(f"{NeonHUD.GREEN}[+] Cyberpunk Neon HUD loaded successfully.{NeonHUD.END}")
    print(f"{NeonHUD.GREEN}[+] Secure Vault subsystem online.{NeonHUD.END}")
    print(f"{NeonHUD.CYAN}--------------------------------------------------{NeonHUD.END}\n")

if __name__ == "__main__":
    boot_sequence()

