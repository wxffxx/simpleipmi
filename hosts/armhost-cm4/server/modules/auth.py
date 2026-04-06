"""
SI BMC — Authentication module
Simple JWT-based auth for API protection.
Uses hashlib for password hashing (no bcrypt dependency issues).
"""

import time
import hashlib
import secrets
import logging
from typing import Optional
from jose import JWTError, jwt

logger = logging.getLogger("si-bmc.auth")


def hash_password(password: str, salt: str = None) -> str:
    """Hash password with SHA-256 + salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    try:
        salt, expected_hash = hashed.split("$", 1)
        h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
        return secrets.compare_digest(h, expected_hash)
    except (ValueError, AttributeError):
        return False


class AuthManager:
    """JWT token-based authentication."""

    def __init__(self, config: dict):
        self.enabled = config.get("enabled", False)
        self.secret = config.get("secret_key", "default-secret")
        self.algorithm = config.get("algorithm", "HS256")
        self.expire_minutes = config.get("token_expire_minutes", 1440)
        self.default_user = config.get("default_user", "admin")
        self.default_password_hash = hash_password(
            config.get("default_password", "admin")
        )

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate user and return JWT token if successful.
        Returns None if auth fails.
        """
        if username != self.default_user:
            return None
        if not verify_password(password, self.default_password_hash):
            return None

        # Create token
        expire = time.time() + (self.expire_minutes * 60)
        payload = {
            "sub": username,
            "exp": expire,
        }
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        logger.info(f"User '{username}' authenticated")
        return token

    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify JWT token. Returns username if valid, None otherwise.
        """
        if not self.enabled:
            return "admin"  # Bypass when auth is disabled

        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            username = payload.get("sub")
            exp = payload.get("exp", 0)
            if exp < time.time():
                return None
            return username
        except JWTError:
            return None

    def check_request(self, authorization: Optional[str] = None) -> bool:
        """
        Check if a request is authorized.
        authorization: "Bearer <token>" header value
        """
        if not self.enabled:
            return True

        if not authorization:
            return False

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return False

        return self.verify_token(parts[1]) is not None
