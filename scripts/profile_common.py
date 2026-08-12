"""Shared validation for the BDO Toolkit profile-distribution repository."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any


ENVELOPE_SCHEMA_VERSION = 1
PROFILE_SCHEMA_VERSION = 1
REGION_PATTERN = re.compile(r"^[a-z0-9-]+$")
REVISION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_PROFILE_FAMILIES = frozenset(
    {
        "INVENTORY_TRANSFER",
        "LOOT_PREVIEW",
        "SOURCE_CONTAINER_DECREMENT",
        "SOURCE_ITEM_REFERENCE",
        "SOURCE_STACK_DECREMENT",
        "STORAGE_ITEM_DELTA",
    }
)

REQUIRED_VERIFICATION = frozenset(
    {
        "character-load-hydration",
        "item-receipts",
        "loot-preview",
        "manual-storage",
        "worker-storage",
    }
)


class ProfileRepositoryError(ValueError):
    """Raised when a profile repository artifact is not publishable."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileRepositoryError(f"could not read JSON {path}: {exc}") from exc


def canonical_profile_bytes(profile: dict[str, Any]) -> bytes:
    try:
        text = json.dumps(
            profile,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ProfileRepositoryError(
            f"profile cannot be canonically encoded: {exc}"
        ) from exc
    return text.encode("utf-8")


def profile_sha256(profile: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_profile_bytes(profile)).hexdigest()


def validate_profile(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ProfileRepositoryError("profile must be a JSON object")
    if profile.get("profile_active") is not True:
        raise ProfileRepositoryError("profile_active must be true")
    profile_version = profile.get("version")
    if (
        isinstance(profile_version, bool)
        or not isinstance(profile_version, int)
        or profile_version != PROFILE_SCHEMA_VERSION
    ):
        raise ProfileRepositoryError(
            f"profile version must be {PROFILE_SCHEMA_VERSION}"
        )
    specs = profile.get("specs")
    if not isinstance(specs, dict):
        raise ProfileRepositoryError("profile specs must be an object")
    missing = sorted(REQUIRED_PROFILE_FAMILIES - set(specs))
    if missing:
        raise ProfileRepositoryError(
            "profile is missing required families: " + ", ".join(missing)
        )
    empty = sorted(
        family
        for family in REQUIRED_PROFILE_FAMILIES
        if not isinstance(specs.get(family), list) or not specs[family]
    )
    if empty:
        raise ProfileRepositoryError(
            "profile has unverified/empty required families: " + ", ".join(empty)
        )
    for family, entries in specs.items():
        if not isinstance(family, str) or not isinstance(entries, list):
            raise ProfileRepositoryError("every profile family must contain a list")
        if any(not isinstance(entry, dict) for entry in entries):
            raise ProfileRepositoryError(
                f"every {family} profile entry must be an object"
            )

    storage_entries = specs["STORAGE_ITEM_DELTA"]
    required_storage_fields = {
        "context_offset",
        "destination_instance_offset",
        "item_id_offset",
        "record_count_offset",
        "repeat_stride",
    }
    for index, entry in enumerate(storage_entries):
        absent = sorted(
            field for field in required_storage_fields if entry.get(field) is None
        )
        if absent:
            raise ProfileRepositoryError(
                f"STORAGE_ITEM_DELTA[{index}] lacks publication authority: "
                + ", ".join(absent)
            )
    return profile


def validate_envelope(envelope: Any) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise ProfileRepositoryError("envelope must be a JSON object")
    envelope_version = envelope.get("schema_version")
    if (
        isinstance(envelope_version, bool)
        or not isinstance(envelope_version, int)
        or envelope_version != ENVELOPE_SCHEMA_VERSION
    ):
        raise ProfileRepositoryError(
            f"schema_version must be {ENVELOPE_SCHEMA_VERSION}"
        )
    manifest = envelope.get("manifest")
    if not isinstance(manifest, dict):
        raise ProfileRepositoryError("manifest must be a JSON object")
    revision = manifest.get("revision")
    region = manifest.get("region")
    patch_label = manifest.get("patch_label")
    verified_at = manifest.get("verified_at")
    minimum_toolkit_version = manifest.get("minimum_toolkit_version")
    digest = manifest.get("profile_sha256")
    verification = manifest.get("verification")
    if not isinstance(revision, str) or not REVISION_PATTERN.fullmatch(revision):
        raise ProfileRepositoryError("manifest revision is invalid")
    if not isinstance(region, str) or not REGION_PATTERN.fullmatch(region):
        raise ProfileRepositoryError("manifest region is invalid")
    if not isinstance(patch_label, str) or not patch_label.strip():
        raise ProfileRepositoryError("manifest patch_label must not be empty")
    if not isinstance(verified_at, str) or not verified_at.endswith("Z"):
        raise ProfileRepositoryError("manifest verified_at must be UTC and end in Z")
    manifest_profile_version = manifest.get("profile_schema_version")
    if (
        isinstance(manifest_profile_version, bool)
        or not isinstance(manifest_profile_version, int)
        or manifest_profile_version != PROFILE_SCHEMA_VERSION
    ):
        raise ProfileRepositoryError(
            f"manifest profile_schema_version must be {PROFILE_SCHEMA_VERSION}"
        )
    if not isinstance(minimum_toolkit_version, str) or not VERSION_PATTERN.fullmatch(
        minimum_toolkit_version
    ):
        raise ProfileRepositoryError("minimum_toolkit_version must be X.Y.Z")
    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
        raise ProfileRepositoryError("manifest profile_sha256 is invalid")
    if not isinstance(verification, list) or any(
        not isinstance(item, str) for item in verification
    ):
        raise ProfileRepositoryError("manifest verification must be a string list")
    missing_verification = sorted(REQUIRED_VERIFICATION - set(verification))
    if missing_verification:
        raise ProfileRepositoryError(
            "manifest lacks required verification: "
            + ", ".join(missing_verification)
        )
    profile = validate_profile(envelope.get("profile"))
    actual = profile_sha256(profile)
    if not hmac.compare_digest(actual, digest):
        raise ProfileRepositoryError(
            f"profile digest mismatch: manifest={digest}, actual={actual}"
        )
    return envelope


def render_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"
