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

def simple_xor_cipher(data: str, key: str) -> str:
    # خوارزمية تشفير محلية خفيفة وسريعة لتأمين البيانات داخل Termux
    return ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(data))

def init_vault():
    print(f"{NeonColors.CYAN}--- [ 🔐 ECHO SECURE VAULT INITIALIZATION ] ---{NeonColors.END}")
    key = input(f"{NeonColors.YELLOW}أدخل مفتاح التشفير السيادي الخاص بك: {NeonColors.END}")
    secret_data = input(f"{NeonColors.YELLOW}أدخل البيانات السرية المراد تأمينها (مفاتيح، ملاحظات): {NeonColors.END}")
    
    encrypted = base64.b64encode(simple_xor_cipher(secret_data, key).encode()).decode()
    
    with open(VAULT_FILE, "w") as f:
        f.write(encrypted)
    
    print(f"{NeonColors.GREEN}⚡ [ECHO]: تم تشفير وحفظ البيانات بنجاح داخل {VAULT_FILE}{NeonColors.END}")

if __name__ == "__main__":
    init_vault()

