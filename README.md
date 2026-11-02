# Echo Pro 2026

Echo Pro 2026 is a local Python terminal experiment for Termux/Python. The
repository currently contains a legacy vault utility and a separate Pro
foundation for encrypted backups of **low-sensitivity demonstration notes**.
It is not an AI node or a real-time crypto tracker.

## Pro: encrypted demonstration-notes backup

The new Pro workflow is exposed from `echo_vault_manager.py` as export/import
menu entries. Its implementation is isolated in `pro_notes_backup.py` and:

- encrypts only a constrained `title`/`body` demonstration-notes format;
- derives an AES-256-GCM key from a passphrase using Scrypt, with a fresh salt
  and nonce for every export;
- authenticates the encrypted data and uses one safe error for a changed backup
  or an incorrect valid passphrase;
- writes the new backup atomically and requests owner-only file permissions
  where the platform supports them;
- does not read, delete, migrate, or reinterpret `echo_vault.enc`.

Do **not** enter wallet keys, credentials, API tokens, or production secrets in
demonstration notes. This feature has not received a security audit and does
not make the repository suitable for high-sensitivity secret storage.

### Subscription and entitlement state

The shipped CLI uses `UnconfiguredProEntitlementGateway`, which denies every
Pro export/import attempt before it accepts notes or a passphrase. It has no
manual activation, local flag, query-string switch, development user, or
client-side payment proof.

A release must replace that gateway with a server-backed implementation that:

1. obtains the account from an authenticated server session;
2. verifies a current subscription (including expiry and cancellation) with the
   selected payment/Android distribution channel; and
3. authorizes that account's ownership of the requested data before permitting
   the Pro operation.

No payment provider, checkout, in-app subscription purchase, server account
system, or Android billing channel is configured in this repository. Therefore
purchase setup is required and no purchase is represented as complete.

## Legacy XOR vault

Menu options 1 and 2 keep the pre-existing `echo_vault.enc` XOR behavior only
for compatibility. XOR plus Base64 is not a secure credential vault, is not a
Pro feature, is not covered by the new entitlement boundary, and must not be
used for wallets or other secrets.

## Local setup and tests

Python 3.9+ is required. Install the maintained cryptography dependency in an
isolated environment, then run the local tests:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v test_pro_notes_backup.py
python echo_vault_manager.py
```

The tests include Unicode round trips, wrong-passphrase/tamper handling,
invalid note input, an unconfigured entitlement denial, and a test-only
synthetic gateway to exercise the authorized service path. That synthetic
gateway is not part of the application.
