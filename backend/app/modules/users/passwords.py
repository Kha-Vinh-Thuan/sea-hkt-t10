"""Password hashing with stdlib scrypt (no extra dependency). Stored as `scrypt$n$r$p$salt_hex$hash_hex`."""

import hashlib
import hmac
import secrets

# OWASP minimum for scrypt; ~16 MB memory per hash.
N, R, P = 2**14, 8, 1

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P)
    return f"scrypt${N}${R}${P}${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, expected = stored.split("$")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected)
