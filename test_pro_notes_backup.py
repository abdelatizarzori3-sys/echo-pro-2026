"""Tests for the Pro demonstration-notes backup feature.

The synthetic gateways in this test file exist only to exercise the production
boundary.  No allow-list gateway is shipped with the application.
"""

import json
import stat
import tempfile
import unittest
from pathlib import Path

from pro_notes_backup import (
    BackupIntegrityError,
    BackupValidationError,
    ProDemoNotesBackupService,
    SubscriptionVerificationRequired,
    UnconfiguredProEntitlementGateway,
    _build_encrypted_backup,
    _decrypt_encrypted_backup,
)


class DeniedGateway:
    def __init__(self) -> None:
        self.features: list[str] = []

    def require_active_subscription(self, feature: str) -> None:
        self.features.append(feature)
        raise SubscriptionVerificationRequired("Denied by test gateway.")


class AllowedGateway:
    """Test-only gateway; production ships no locally granting gateway."""

    def __init__(self) -> None:
        self.features: list[str] = []

    def require_active_subscription(self, feature: str) -> None:
        self.features.append(feature)


class ProNotesBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.notes = [
            {"title": "Deployment", "body": "Use staging first."},
            {"title": "ملاحظة تجريبية", "body": "نص Unicode محفوظ في النسخة."},
        ]
        self.passphrase = "correct horse battery staple"

    def test_round_trip_preserves_unicode_notes_and_hides_plaintext(self) -> None:
        blob = _build_encrypted_backup(self.notes, self.passphrase)
        self.assertNotIn("Use staging first.".encode("utf-8"), blob)
        self.assertNotIn("ملاحظة تجريبية".encode("utf-8"), blob)
        self.assertEqual(_decrypt_encrypted_backup(blob, self.passphrase), self.notes)

    def test_wrong_passphrase_and_tampering_have_same_safe_error(self) -> None:
        blob = _build_encrypted_backup(self.notes, self.passphrase)
        with self.assertRaisesRegex(BackupIntegrityError, "^Unable to open backup\\.$"):
            _decrypt_encrypted_backup(blob, "a different valid passphrase")

        envelope = json.loads(blob)
        ciphertext = envelope["cipher"]["ciphertext"]
        replacement = "A" if ciphertext[-1] != "A" else "B"
        envelope["cipher"]["ciphertext"] = ciphertext[:-1] + replacement
        tampered = json.dumps(envelope, separators=(",", ":")).encode("utf-8")
        with self.assertRaisesRegex(BackupIntegrityError, "^Unable to open backup\\.$"):
            _decrypt_encrypted_backup(tampered, self.passphrase)

    def test_default_gateway_fails_closed(self) -> None:
        service = ProDemoNotesBackupService(UnconfiguredProEntitlementGateway())
        with self.assertRaises(SubscriptionVerificationRequired):
            service.require_access()

    def test_denied_gateway_blocks_export_before_writing_or_reading(self) -> None:
        denied = DeniedGateway()
        service = ProDemoNotesBackupService(denied)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "demo-backup.json"
            with self.assertRaises(SubscriptionVerificationRequired):
                service.export_backup(self.notes, self.passphrase, destination)
            self.assertFalse(destination.exists())
            with self.assertRaises(SubscriptionVerificationRequired):
                service.import_backup(self.passphrase, destination)
        self.assertEqual(len(denied.features), 2)

    def test_authorized_test_gateway_exports_imports_and_restricts_file_permissions(self) -> None:
        allowed = AllowedGateway()
        service = ProDemoNotesBackupService(allowed)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "demo-backup.json"
            service.export_backup(self.notes, self.passphrase, destination)
            self.assertEqual(service.import_backup(self.passphrase, destination), self.notes)
            if hasattr(stat, "S_IRUSR"):
                self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
        self.assertEqual(len(allowed.features), 2)

    def test_invalid_note_schema_is_rejected(self) -> None:
        with self.assertRaisesRegex(BackupValidationError, "title and body"):
            _build_encrypted_backup([{"title": "Only title"}], self.passphrase)


if __name__ == "__main__":
    unittest.main()
