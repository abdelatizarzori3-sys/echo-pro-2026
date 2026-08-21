import os
import base64

VAULT_FILE = "echo_vault.enc"

class NeonColors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def xor_cipher(data: str, key: str) -> str:
    return ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

def encrypt_vault():
    print(f"\n{NeonColors.CYAN}--- [ 🔐 ECHO SECURE VAULT: ENCRYPTION MODE ] ---{NeonColors.END}")
    key = input(f"{NeonColors.YELLOW}Enter Sovereign Master Key: {NeonColors.END}")
    secret_data = input(f"{NeonColors.YELLOW}Enter Secret Data to Lock: {NeonColors.END}")
    
    encrypted = base64.b64encode(xor_cipher(secret_data, key).encode()).decode()
    
    with open(VAULT_FILE, "w") as f:
        f.write(encrypted)
    
    print(f"{NeonColors.GREEN}⚡ [ECHO]: Vault successfully locked & encrypted to {VAULT_FILE}{NeonColors.END}\n")

def decrypt_vault():
    print(f"\n{NeonColors.CYAN}--- [ 🔓 ECHO SECURE VAULT: DECRYPTION MODE ] ---{NeonColors.END}")
    if not os.path.exists(VAULT_FILE):
        print(f"{NeonColors.RED}❌ [ECHO ERROR]: No vault file found!{NeonColors.END}\n")
        return
        
    key = input(f"{NeonColors.YELLOW}Enter Sovereign Master Key: {NeonColors.END}")
    
    try:
        with open(VAULT_FILE, "r") as f:
            encrypted_data = f.read()
            
        decoded_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = xor_cipher(decoded_bytes.decode(), key)
        
        print(f"{NeonColors.GREEN}⚡ [ECHO DECRYPTED DATA]: {NeonColors.BOLD}{decrypted}{NeonColors.END}\n")
    except Exception as e:
        print(f"{NeonColors.RED}❌ [ECHO ERROR]: Decryption failed! Invalid key or corrupted vault.{NeonColors.END}\n")

def main_menu():
    while True:
        print(f"{NeonColors.CYAN}=== ECHO PRO 2026: VAULT MANAGER ==={NeonColors.END}")
        print("1. Encrypt & Save Data")
        print("2. Decrypt & Read Data")
        print("3. Exit")
        choice = input(f"{NeonColors.YELLOW}Select Option (1-3): {NeonColors.END}")
        
        if choice == "1":
            encrypt_vault()
        elif choice == "2":
            decrypt_vault()
        elif choice == "3":
            print(f"{NeonColors.GREEN}Exiting Echo Vault. Stay secure, operator.{NeonColors.END}")
            break
        else:
            print(f"{NeonColors.RED}Invalid option. Try again.{NeonColors.END}")

if __name__ == "__main__":
    main_menu()

