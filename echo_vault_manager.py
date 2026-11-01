import os
import base64
from getpass import getpass

from pro_notes_backup import (
    BackupError,
    ProDemoNotesBackupService,
    SubscriptionVerificationRequired,
    UnconfiguredProEntitlementGateway,
)

VAULT_FILE = "echo_vault.enc"
DEMO_NOTES_BACKUP_FILE = "echo_demo_notes.backup.json"


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
    except Exception:
        print(f"{NeonColors.RED}❌ [ECHO ERROR]: Decryption failed! Invalid key or corrupted vault.{NeonColors.END}\n")


def _pro_backup_service() -> ProDemoNotesBackupService:
    """Return the fail-closed service until a server entitlement gateway is configured."""
    return ProDemoNotesBackupService(UnconfiguredProEntitlementGateway())


def _require_pro_backup_access(service: ProDemoNotesBackupService) -> bool:
    try:
        service.require_access()
        return True
    except SubscriptionVerificationRequired:
        print(
            f"{NeonColors.RED}❌ [ECHO PRO]: Encrypted demo-note backups are unavailable. "
            "A server-verified account and active subscription must be configured first; "
            f"purchase setup is currently required.{NeonColors.END}\n"
        )
        return False


def _collect_demo_notes() -> list[dict[str, str]]:
    print(
        f"{NeonColors.YELLOW}Demo notes only: do not enter wallet keys, credentials, "
        f"or production secrets.{NeonColors.END}"
    )
    print("Leave the title empty when you have finished adding notes.")
    notes: list[dict[str, str]] = []
    while len(notes) < 50:
        title = input(f"{NeonColors.YELLOW}Demo note title: {NeonColors.END}").strip()
        if not title:
            break
        body = input(f"{NeonColors.YELLOW}Demo note body (one line): {NeonColors.END}")
        notes.append({"title": title, "body": body})
    return notes


def export_demo_notes_backup():
    """Export the new Pro-only AES-GCM demo-notes backup, never the legacy vault."""
    print(f"\n{NeonColors.CYAN}--- [ ECHO PRO: DEMO-NOTES BACKUP EXPORT ] ---{NeonColors.END}")
    service = _pro_backup_service()
    if not _require_pro_backup_access(service):
        return

    notes = _collect_demo_notes()
    if not notes:
        print(f"{NeonColors.RED}❌ [ECHO PRO]: No demo notes were entered.{NeonColors.END}\n")
        return
    passphrase = getpass("Backup passphrase (12+ characters): ")
    if passphrase != getpass("Confirm backup passphrase: "):
        print(f"{NeonColors.RED}❌ [ECHO PRO]: Passphrases did not match.{NeonColors.END}\n")
        return
    try:
        service.export_backup(notes, passphrase, DEMO_NOTES_BACKUP_FILE)
        print(f"{NeonColors.GREEN}⚡ [ECHO PRO]: Demo-note backup exported.{NeonColors.END}\n")
    except BackupError:
        print(f"{NeonColors.RED}❌ [ECHO PRO]: Backup export failed.{NeonColors.END}\n")


def import_demo_notes_backup():
    """Import a new Pro-only AES-GCM demo-notes backup after server authorization."""
    print(f"\n{NeonColors.CYAN}--- [ ECHO PRO: DEMO-NOTES BACKUP IMPORT ] ---{NeonColors.END}")
    service = _pro_backup_service()
    if not _require_pro_backup_access(service):
        return

    passphrase = getpass("Backup passphrase: ")
    try:
        notes = service.import_backup(passphrase, DEMO_NOTES_BACKUP_FILE)
        print(
            f"{NeonColors.GREEN}⚡ [ECHO PRO]: Imported {len(notes)} demo note(s). "
            f"Note bodies are not printed.{NeonColors.END}\n"
        )
    except BackupError:
        print(f"{NeonColors.RED}❌ [ECHO PRO]: Backup import failed.{NeonColors.END}\n")


def main_menu():
    while True:
        print(f"{NeonColors.CYAN}=== ECHO PRO 2026: VAULT MANAGER ==={NeonColors.END}")
        print("1. Encrypt & Save Data (legacy XOR vault)")
        print("2. Decrypt & Read Data (legacy XOR vault)")
        print("3. Export Pro encrypted demo-notes backup (subscription required)")
        print("4. Import Pro encrypted demo-notes backup (subscription required)")
        print("5. Exit")
        choice = input(f"{NeonColors.YELLOW}Select Option (1-5): {NeonColors.END}")

        if choice == "1":
            encrypt_vault()
        elif choice == "2":
            decrypt_vault()
        elif choice == "3":
            export_demo_notes_backup()
        elif choice == "4":
            import_demo_notes_backup()
        elif choice == "5":
            print(f"{NeonColors.GREEN}Exiting Echo Vault. Stay secure, operator.{NeonColors.END}")
            break
        else:
            print(f"{NeonColors.RED}Invalid option. Try again.{NeonColors.END}")


if __name__ == "__main__":
    main_menu()
