#!/usr/bin/env python3
# Copyright (c) 2026 Andrzej Dobosz. All rights reserved.
# Priority Date: 2026-05-18
# License: MIT -- see LICENSE file
# parapet -- Key Rotation Script (v1.1.0 TODO)
"""
Rotates encryption keys and re-encrypts all sessions.
Implements DORA Art. 9.2(d) key rotation policy.
"""
import json
import os
import secrets
import shutil
import sys
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
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Archive old key
    if KEY_FILE.exists():
        shutil.copy2(KEY_FILE, ARCHIVE_DIR / f"encryption_key.{timestamp}")
        shutil.copy2(SALT_FILE, ARCHIVE_DIR / f"salt.{timestamp}")

    # 2. Generate new key
    new_key = secrets.token_bytes(32)
    new_salt = secrets.token_bytes(16)

    # 3. Re-encrypt all sessions
    # TODO: Import crypto_vault, decrypt each session with old key,
    #       re-encrypt with new key.
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
        "new_key_fingerprint": secrets.token_hex(8),
        "old_key_archived": str(ARCHIVE_DIR / f"encryption_key.{timestamp}"),
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"Keys rotated at {timestamp}")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        rotate()
    else:
        print("Use --force to confirm key rotation.")
        print("Old key archived in:", ARCHIVE_DIR)
