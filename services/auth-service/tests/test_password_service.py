"""Tests for password hashing and verification."""

import secrets

from app.services.password_service import hash_password, verify_password


def _make_password() -> str:
    """Generate a random password for tests (no hardcoded credentials)."""
    return secrets.token_urlsafe(12)


def test_hash_password_returns_hash():
    """Hashing a password should return a bcrypt hash."""
    password = _make_password()
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    """Verifying correct password should return True."""
    password = _make_password()
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Verifying incorrect password should return False."""
    correct = _make_password()
    wrong = _make_password()
    hashed = hash_password(correct)
    assert verify_password(wrong, hashed) is False


def test_hash_password_unique():
    """Same password should produce different hashes (salt)."""
    password = _make_password()
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    assert hash1 != hash2
