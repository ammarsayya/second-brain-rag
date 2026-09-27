"""Ownership-safe Obsidian vault writes (T-P4-13)."""

from sbr.vault.writer import (
    END_USER_SECTION,
    START_USER_SECTION,
    VaultDirtyError,
    VaultFolder,
    VaultGitError,
    VaultMutation,
    VaultOperation,
    VaultOwnershipError,
    VaultPathError,
    VaultWriteError,
    VaultWriter,
    VaultWriteResult,
)

__all__ = [
    "END_USER_SECTION",
    "START_USER_SECTION",
    "VaultDirtyError",
    "VaultFolder",
    "VaultGitError",
    "VaultMutation",
    "VaultOperation",
    "VaultOwnershipError",
    "VaultPathError",
    "VaultWriteError",
    "VaultWriteResult",
    "VaultWriter",
]
