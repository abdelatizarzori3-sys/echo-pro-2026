"""Pro demo-notes backup support.

This module deliberately handles only low-sensitivity demonstration notes.  It
uses `cryptography` primitives (Scrypt and AES-GCM); it does not read, migrate,
or reinterpret the legacy XOR vault format.

A real deployment must supply a server-backed entitlement gateway that derives
the account from an authenticated session and verifies subscription state and
data ownership.  The bundled gateway is intentionally unconfigured and denies
all Pro operations.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol, Sequence

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


BACKUP_FORMAT = "echo-pro-demo-notes-backup-v1"
BACKUP_VERSION = 1
FEATURE_NAME = "encrypted_demo_notes_backup"
MAX_NOTES = 50
MAX_TITLE_CHARACTERS = 140
MAX_BODY_CHARACTERS = 10_000
MAX_PLAINTEXT_BYTES = 1_000_000
MAX_BACKUP_BYTES = 2_000_000
MIN_PASSWORD_CHARACTERS = 12
MAX_PASSWORD_BYTES = 4_096
_SALT_BYTES = 16
_NONCE_BYTES = 12
_KEY_BYTES = 32
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_AAD = BACKUP_FORMAT.encode("ascii")


class BackupError(Exception):
    """Base error for the encrypted demonstration-notes backup format."""


class BackupValidationError(BackupError):
    """The caller supplied notes or a passphrase outside the supported limits."""


class BackupIntegrityError(BackupError):
    """The backup is malformed, altered, or cannot be opened with this passphrase."""


class BackupReadError(BackupError):
    """The requested backup file cannot be safely read."""


class BackupWriteError(BackupError):
    """The requested backup file cannot be safely written."""


class SubscriptionVerificationRequired(BackupError):
    """A Pro operation lacks verified, server-backed subscription access."""


class ProEntitlementGateway(Protocol):
    """Server-backed authorization boundary for the Pro feature.

    Implementations must obtain the account identity from an authenticated
    server session (not a CLI value, local storage value, or return URL), check
    that the subscription is active and not cancelled or expired, and enforce
    that the authenticated account owns the requested data before returning.
    """

    def require_active_subscription(self, feature: str) -> None:
        """Return only after the server has authorized this Pro feature."""


class UnconfiguredProEntitlementGateway:
    """Production-safe default: deny access until a real server gateway exists."""

    def require_active_subscription(self, feature: str) -> None:
        if feature != FEATURE_NAME:
            raise SubscriptionVerificationRequired("Unknown Pro feature.")
        raise SubscriptionVerificationRequired(
            "Pro backup is unavailable until server-backed account and subscription "
            "verification are configured."
        )


class ProDemoNotesBackupService:
    """The only supported application entry point for encrypted Pro backups."""

    def __init__(self, entitlement_gateway: ProEntitlementGateway) -> None:
        self._entitlement_gateway = entitlement_gateway

    def require_access(self) -> None:
        """Fail closed unless the configured server gateway authorizes the feature."""
        self._entitlement_gateway.require_active_subscription(FEATURE_NAME)

    def export_backup(
        self,
        notes: Sequence[dict[str, str]],
        passphrase: str,
        destination: str | Path,
    ) -> Path:
        """Authorize and atomically export encrypted demonstration notes."""
        self.require_access()
        return _write_encrypted_backup(notes, passphrase, destination)

    def import_backup(self, passphrase: str, source: str | Path) -> list[dict[str, str]]:
        """Authorize and import encrypted demonstration notes."""
        self.require_access()
        return _read_encrypted_backup(passphrase, source)


def _validate_passphrase(passphrase: str) -> bytes:
    if not isinstance(passphrase, str):
        raise BackupValidationError("A passphrase is required.")
    if len(passphrase) < MIN_PASSWORD_CHARACTERS:
        raise BackupValidationError(
            f"Use a passphrase of at least {MIN_PASSWORD_CHARACTERS} characters."
        )
    encoded = passphrase.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise BackupValidationError("The passphrase is too long.")
    return encoded


def _validated_notes(notes: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    if not isinstance(notes, (list, tuple)):
        raise BackupValidationError("Notes must be a list of demonstration notes.")
    if not notes:
        raise BackupValidationError("Add at least one demonstration note before exporting.")
    if len(notes) > MAX_NOTES:
        raise BackupValidationError(f"A backup may contain at most {MAX_NOTES} notes.")

    normalized: list[dict[str, str]] = []
    for note in notes:
        if not isinstance(note, dict) or set(note) != {"title", "body"}:
            raise BackupValidationError("Each note must contain only title and body text.")
        title = note["title"]
        body = note["body"]
        if not isinstance(title, str) or not isinstance(body, str):
            raise BackupValidationError("Note titles and bodies must be text.")
        if not title.strip():
            raise BackupValidationError("A note title cannot be empty.")
        if len(title) > MAX_TITLE_CHARACTERS or len(body) > MAX_BODY_CHARACTERS:
            raise BackupValidationError("A demonstration note exceeds the allowed size.")
        normalized.append({"title": title, "body": body})

    payload = json.dumps(
        {"kind": "demo_notes", "notes": normalized},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(payload) > MAX_PLAINTEXT_BYTES:
        raise BackupValidationError("Demonstration notes exceed the backup size limit.")
    return normalized


def _derive_key(passphrase: bytes, salt: bytes) -> bytes:
    return Scrypt(
        salt=salt,
        length=_KEY_BYTES,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    ).derive(passphrase)


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64decode(value: Any) -> bytes:
    if not isinstance(value, str):
        raise BackupIntegrityError("Unable to open backup.")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError):
        raise BackupIntegrityError("Unable to open backup.") from None


def _build_encrypted_backup(notes: Sequence[dict[str, str]], passphrase: str) -> bytes:
    """Build an authenticated encrypted backup blob for tests and service internals."""
    validated_notes = _validated_notes(notes)
    passphrase_bytes = _validate_passphrase(passphrase)
    plaintext = json.dumps(
        {"kind": "demo_notes", "notes": validated_notes},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    salt = os.urandom(_SALT_BYTES)
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(_derive_key(passphrase_bytes, salt)).encrypt(nonce, plaintext, _AAD)
    envelope = {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "kdf": {
            "name": "scrypt",
            "n": _SCRYPT_N,
            "r": _SCRYPT_R,
            "p": _SCRYPT_P,
            "length": _KEY_BYTES,
            "salt": _b64encode(salt),
        },
        "cipher": {
            "name": "AES-256-GCM",
            "nonce": _b64encode(nonce),
            "ciphertext": _b64encode(ciphertext),
        },
    }
    return json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _parse_envelope(blob: bytes) -> tuple[bytes, bytes, bytes]:
    if not isinstance(blob, bytes) or len(blob) > MAX_BACKUP_BYTES:
        raise BackupIntegrityError("Unable to open backup.")
    try:
        envelope = json.loads(blob.decode("utf-8"))
        if not isinstance(envelope, dict) or set(envelope) != {
            "format",
            "version",
            "kdf",
            "cipher",
        }:
            raise ValueError
        if envelope["format"] != BACKUP_FORMAT or envelope["version"] != BACKUP_VERSION:
            raise ValueError
        kdf = envelope["kdf"]
        cipher = envelope["cipher"]
        if not isinstance(kdf, dict) or set(kdf) != {
            "name",
            "n",
            "r",
            "p",
            "length",
            "salt",
        }:
            raise ValueError
        if not isinstance(cipher, dict) or set(cipher) != {"name", "nonce", "ciphertext"}:
            raise ValueError
        if (
            kdf["name"] != "scrypt"
            or kdf["n"] != _SCRYPT_N
            or kdf["r"] != _SCRYPT_R
            or kdf["p"] != _SCRYPT_P
            or kdf["length"] != _KEY_BYTES
            or cipher["name"] != "AES-256-GCM"
        ):
            raise ValueError
        salt = _b64decode(kdf["salt"])
        nonce = _b64decode(cipher["nonce"])
        ciphertext = _b64decode(cipher["ciphertext"])
        if len(salt) != _SALT_BYTES or len(nonce) != _NONCE_BYTES or len(ciphertext) < 16:
            raise ValueError
        return salt, nonce, ciphertext
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise BackupIntegrityError("Unable to open backup.") from None


def _decrypt_encrypted_backup(blob: bytes, passphrase: str) -> list[dict[str, str]]:
    """Open a backup blob and report one error for alteration or a wrong passphrase."""
    passphrase_bytes = _validate_passphrase(passphrase)
    salt, nonce, ciphertext = _parse_envelope(blob)
    try:
        plaintext = AESGCM(_derive_key(passphrase_bytes, salt)).decrypt(nonce, ciphertext, _AAD)
        payload = json.loads(plaintext.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"kind", "notes"}:
            raise ValueError
        if payload["kind"] != "demo_notes":
            raise ValueError
        return _validated_notes(payload["notes"])
    except (
        InvalidTag,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        BackupValidationError,
    ):
        raise BackupIntegrityError("Unable to open backup.") from None


def _write_encrypted_backup(
    notes: Sequence[dict[str, str]], passphrase: str, destination: str | Path
) -> Path:
    blob = _build_encrypted_backup(notes, passphrase)
    path = Path(destination)
    parent = path.parent
    if not path.name or not parent.is_dir():
        raise BackupWriteError("Backup destination is unavailable.")

    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(blob)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
        try:
            os.chmod(path, 0o600)
        except OSError:
            # The atomic content write succeeded; permission support varies by platform.
            pass
        return path
    except OSError as exc:
        raise BackupWriteError("Backup destination is unavailable.") from exc
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass


def _read_encrypted_backup(passphrase: str, source: str | Path) -> list[dict[str, str]]:
    path = Path(source)
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as backup_file:
            blob = backup_file.read(MAX_BACKUP_BYTES + 1)
    except OSError as exc:
        raise BackupReadError("Backup file is unavailable.") from exc
    return _decrypt_encrypted_backup(blob, passphrase)
