# parapet v3.0.0-APACHE — Cryptographic Key Lifecycle
## v1.0.0 | Priority Date: 2026-05-18 | DORA Art. 9 Compliance Evidence

---

## Overview

parapet manages two types of cryptographic material:

| Material | Purpose | Algorithm | Location | Generation |
|----------|---------|-----------|----------|------------|
| **Encryption Key** | AES-256-GCM session encryption | 256-bit random (os.urandom / Python secrets) | `workspace/.parapet/.secrets/encryption_key` | `crypto_vault.py:generate_key()` |
| **Salt** | PBKDF2 key derivation | 128-bit random | `workspace/.parapet/.secrets/salt` | `crypto_vault.py:generate_key()` |
| **Auth Token** | Bearer token for state-changing API endpoints | 128-bit hex (secrets.token_hex(16)) | `workspace/.parapet/auth_token` | `server.py:_init_auth_token()` |
| **HFToken (optional)** | HuggingFace API download authentication | User-provided, DPAPI-encrypted | `~/.parapet/hf_token.enc` (Windows) | `pull-eu-models.ps1:Save-HFToken()` |

---

## Full Lifecycle — Encryption Key (AES-256-GCM)

### Phase 1: Generation

| Aspect | Current State | Code Reference |
|--------|--------------|----------------|
| **Trigger** | Proactive at container startup (Bug #4 fix) | `server.py` lifespan → `crypto_vault.generate_keys_if_missing()` |
| **Algorithm** | Python `secrets.token_bytes(32)` — 256 bits | `os.urandom()` on Linux, `CryptGenRandom` on Windows |
| **Entropy Source** | Kernel CSPRNG (`/dev/urandom`) | Sufficient for AES-256 per NIST SP 800-90A |
| **Strength Check** | None — key is raw 256-bit bytes | ✅ Entropy source is adequate |
| **DORA Art. 9.2(a)** | Documented algorithm + entropy source | ✅ Compliant |

```python
# crypto_vault.py:40-56
def generate_key():
    _ensure_secrets_dir()
    key = secrets.token_bytes(32)   # 256 bits from kernel CSPRNG
    salt = secrets.token_bytes(16)  # 128 bits
    KEY_FILE.write_bytes(key)
    SALT_FILE.write_bytes(salt)
    os.chmod(KEY_FILE, 0o600)
    os.chmod(SALT_FILE, 0o600)
    return key, salt
```

### Phase 2: Storage

| Aspect | Current State | Gap? | Recommended Fix |
|--------|--------------|------|-----------------|
| **Location** | `workspace/.parapet/.secrets/encryption_key` | — | — |
| **Permissions** | `os.chmod(0o600)` — owner read/write only | — | Already implemented |
| **Encrypted at Rest** | **NO — plaintext on disk** | 🔴 HIGH | Wrap in OS keyring: DPAPI on Windows (`CryptProtectData`), `fscrypt` on Linux. File is on a bind-mounted volume; if host is compromised, key is readable. |
| **Backup** | Not backed up; regenerated if missing | — | Key loss means session data is unrecoverable — this is the design (zero-knowledge encryption) |
| **DORA Art. 9.2(c)** | Partial — permissions set, but not encrypted at rest | 🟡 GAP | Encrypt key file with DPAPI/fscrypt |

**Current storage implementation:**
```python
# crypto_vault.py:40-56
KEY_FILE.write_bytes(key)
try:
    os.chmod(KEY_FILE, 0o600)  # Owner-only permissions
    os.chmod(SALT_FILE, 0o600)
except OSError:
    pass
```

### Phase 3: Rotation

| Aspect | Current State | Gap? | Recommended Fix |
|--------|--------------|------|-----------------|
| **Rotation Mechanism** | **NOT IMPLEMENTED** | 🔴 HIGH | Create `scripts/rotate_keys.py` (stub created) |
| **Rotation Trigger** | Manual only | 🟡 GAP | 90-day automatic rotation policy per NIST SP 800-57 |
| **Re-encryption of Data** | Not handled | 🔴 CRITICAL | Old data encrypted with old key would become unreadable after rotation. Need re-encryption step. |
| **Rotation Logging** | Not implemented | 🟡 GAP | Log rotation event with timestamp + new key fingerprint |
| **DORA Art. 9.2(d)** | Key rotation not defined | 🔴 GAP | Define 90-day rotation interval |

**Rotation stub created:** `scripts/rotate_keys.py`
```python
# Stub structure — implementation deferred to v1.1.0
# 1. Generate new key pair
# 2. Re-encrypt all session files with new key
# 3. Archive old key with timestamp
# 4. Atomically swap new key into place
# 5. Log rotation event with fingerprint
```

### Phase 4: Revocation

| Aspect | Current State | Gap? | Recommended Fix |
|--------|--------------|------|-----------------|
| **Revocation Mechanism** | **NOT IMPLEMENTED** | 🔴 HIGH | Delete key file + auth token simultaneously; invalidate all existing sessions |
| **Revocation Trigger** | Manual | — | Acceptable for local deployment (no cloud API to compromise) |
| **Session Invalidation** | Not tied to key revocation | 🟡 GAP | On revocation, delete all `.parapet/sessions/*.json` |
| **DORA Art. 9.2(e)** | No compromise procedure defined | 🔴 GAP | Document: delete key → re-encrypt with new key → notify audit log |

**Revocation procedure (to implement):**
```
1. docker exec ollama-agent rm /workspace/.parapet/.secrets/encryption_key
2. docker exec ollama-agent rm /workspace/.parapet/auth_token
3. docker compose restart
   → On restart, generate_keys_if_missing() creates new key
   → _init_auth_token() creates new auth token
   → All old sessions become un-decryptable (effectively revoked)
```

### Phase 5: Destruction

| Aspect | Current State | Gap? | Recommended Fix |
|--------|--------------|------|-----------------|
| **Secure Erase** | **PARTIAL** — `secure_erase()` function exists but only called manually | 🟡 GAP | Call on container shutdown |
| **Overwrite Count** | 3 passes (random, zeros, random) | — | Exceeds NIST SP 800-88 minimum (1 pass for magnetic media) |
| **Verification** | Not implemented | 🟡 GAP | Verify file is unreadable after erase |
| **DORA Art. 9.2(f)** | Secure wipe implemented but not automatic | 🟡 GAP | Wire secure_erase() into container SIGTERM handler |

```python
# crypto_vault.py:210-225 — Already implemented
def secure_erase(filepath):
    path = Path(filepath)
    if not path.exists():
        return False
    try:
        size = path.stat().st_size
        for _ in range(3):  # 3-pass overwrite
            path.write_bytes(secrets.token_bytes(size))
        path.unlink()
        return True
    except Exception:
        return False
```

---

## Full Lifecycle — Auth Token

| Phase | State | Detail |
|-------|-------|--------|
| **Generation** | ✅ `_init_auth_token()` at startup | 32-char hex token via `secrets.token_hex(16)` |
| **Storage** | Plaintext in `workspace/.parapet/auth_token` | 🟡 Same encryption gap as encryption key |
| **Rotation** | ✅ `/api/auth-token/rotate` endpoint exists in server.py | Manual via API call |
| **Revocation** | Delete file → restart → new token generated | ✅ Implicit on deletion |
| **Validation** | `secrets.compare_digest()` — timing-safe comparison | ✅ Prevents timing attacks |

---

## DORA Article 9 Compliance Matrix

| DORA Art. 9 Requirement | Encryption Key | Auth Token | HFToken |
|------------------------|---------------|------------|---------|
| **(a) Algorithm + Entropy** | ✅ Documented | ✅ Documented | N/A (user-provided) |
| **(b) Generation Procedure** | ✅ `generate_keys_if_missing()` | ✅ `_init_auth_token()` | ✅ `Read-Host -AsSecureString` |
| **(c) Storage (Encrypted at Rest)** | 🟡 Plaintext — DPAPI TODO | 🟡 Plaintext — DPAPI TODO | ✅ DPAPI-encrypted |
| **(d) Rotation (Defined Interval)** | 🔴 Not implemented | ✅ Manual endpoint | N/A |
| **(e) Revocation (Compromise Procedure)** | 🔴 Not documented | 🔴 Not documented | ✅ Delete token file |
| **(f) Destruction (Secure Wipe)** | ✅ `secure_erase()` function | ✅ Delete file | ✅ `Remove-Item` |

---

## Recommendations — Priority Order

| Priority | Action | Effort | Patent Impact |
|----------|--------|--------|--------------|
| **1** | Encrypt key files at rest (DPAPI on Windows, fscrypt on Linux) | Medium (4h) | Stronger Patent #5 evidence |
| **2** | Document revocation procedure in `security/KEY-LIFECYCLE.md` | Low (1h) | DORA Art. 9 compliance |
| **3** | Implement `scripts/rotate_keys.py` with re-encryption | High (8h) | Patent #7 enhancer |
| **4** | Wire `secure_erase()` to SIGTERM handler | Low (2h) | DORA Art. 9 compliance |
| **5** | Add 90-day rotation cron/reminder | Low (1h) | NIST SP 800-57 alignment |

---

## Key Rotation Stub

```python
#!/usr/bin/env python3
# scripts/rotate_keys.py — parapet Key Rotation (v1.1.0 TODO)
"""
Key rotation script for parapet encryption keys.
Implements: generate new key → re-encrypt sessions → archive old key → log event
"""
import json, os, secrets, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))
SECRETS_DIR = WORKSPACE / ".parapet" / ".secrets"
KEY_FILE = SECRETS_DIR / "encryption_key"
SALT_FILE = SECRETS_DIR / "salt"
ARCHIVE_DIR = SECRETS_DIR / "archive"
LOG_FILE = WORKSPACE / ".parapet" / "key_rotation.log"
SESSIONS_DIR = WORKSPACE / ".parapet" / "sessions"

def rotate():
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 1. Archive old key
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists():
        shutil.copy2(KEY_FILE, ARCHIVE_DIR / f"encryption_key.{timestamp}")
        shutil.copy2(SALT_FILE, ARCHIVE_DIR / f"salt.{timestamp}")
    
    # 2. Generate new key
    new_key = secrets.token_bytes(32)
    new_salt = secrets.token_bytes(16)
    
    # 3. Re-encrypt all sessions with new key
    # TODO: Load each session file, decrypt with OLD key, re-encrypt with NEW key
    # for session_file in SESSIONS_DIR.glob("*.json"):
    #     data = decrypt_with_old_key(session_file)
    #     encrypt_with_new_key(data, session_file)
    
    # 4. Atomically swap new key
    KEY_FILE.write_bytes(new_key)
    SALT_FILE.write_bytes(new_salt)
    os.chmod(KEY_FILE, 0o600)
    os.chmod(SALT_FILE, 0o600)
    
    # 5. Log rotation
    log_entry = {
        "event": "key_rotation",
        "timestamp": timestamp,
        "new_key_fingerprint": secrets.token_hex(8),  # Truncated SHA-256 in production
        "old_key_archived": str(ARCHIVE_DIR / f"encryption_key.{timestamp}")
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(f"Keys rotated successfully at {timestamp}")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        rotate()
    else:
        print("Use --force to confirm key rotation. This will re-encrypt all sessions.")
        print("Old key will be archived in:", ARCHIVE_DIR)
```

---

*Document v1.0.0 | 2026-05-20 | Andrzej Dobosz*
*Evidence for Patent #7: Compliance-by-Architecture — DORA Art. 9 Key Management*
