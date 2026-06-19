"""Seed default demo users on first startup.

Creates three demo accounts (one per role) so a freshly deployed environment is
immediately usable. Seeding is idempotent: the user repository writes with a
``attribute_not_exists(user_id)`` condition, so existing users are never
overwritten and re-running on every container start is safe.

These are well-known demo credentials intended ONLY for non-production demo and
workshop environments. Disable by setting ``SEED_DEFAULT_USERS=false``.
"""

import logging

from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.services.password_service import hash_password

logger = logging.getLogger(__name__)

# (user_id, password, full_name, email, role)
_DEFAULT_USERS = [
    ("admin", "admin12345", "Demo Admin", "admin@example.com", UserRole.ADMIN),
    ("adjudicator", "Adjudicator123", "Demo Adjudicator", "adjudicator@example.com", UserRole.ADJUDICATOR),
    ("policyholder", "PolicyHolder123", "Demo Policyholder", "policyholder@example.com", UserRole.POLICYHOLDER),
]


def seed_default_users() -> None:
    """Create the demo users if they do not already exist (idempotent)."""
    repo = UserRepository()

    for user_id, password, full_name, email, role in _DEFAULT_USERS:
        # Skip if the user already exists so we never overwrite a changed password.
        if repo.get_user_by_id(user_id) is not None:
            logger.info("Seed user %r already exists; skipping.", user_id)
            continue

        try:
            repo.create_user(
                {
                    "user_id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "phone": None,
                    "role": role.value,
                    "password_hash": hash_password(password),
                }
            )
            logger.info("Seeded default user %r with role %r.", user_id, role.value)
        except ValueError:
            # Lost a race with another starting task; the user now exists. Fine.
            logger.info("Seed user %r created concurrently; skipping.", user_id)
        except Exception:  # noqa: BLE001 - seeding must never crash startup
            logger.warning("Failed to seed user %r.", user_id, exc_info=True)
