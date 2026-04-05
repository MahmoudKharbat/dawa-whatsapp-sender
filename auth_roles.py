"""
Application roles and permission helpers.
"""

from typing import FrozenSet

ROLE_CONTACT_MANAGER = "ContactManager"
ROLE_MANAGER = "Manager"
ROLE_ADMIN = "Admin"

VALID_ROLES: FrozenSet[str] = frozenset(
    {ROLE_CONTACT_MANAGER, ROLE_MANAGER, ROLE_ADMIN}
)

ROLE_LABELS_AR = {
    ROLE_CONTACT_MANAGER: "مدير جهات اتصال",
    ROLE_MANAGER: "مدير",
    ROLE_ADMIN: "مسؤول",
}


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def role_label_ar(role: str) -> str:
    return ROLE_LABELS_AR.get(role, role)


def can_manage_contacts(role: str) -> bool:
    return role in VALID_ROLES


def can_use_messaging(role: str) -> bool:
    return role in (ROLE_MANAGER, ROLE_ADMIN)


def can_manage_users(role: str) -> bool:
    return role == ROLE_ADMIN
