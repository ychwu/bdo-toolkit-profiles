"""Publish one complete local opcode profile into archive/channel envelopes."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import tempfile
from pathlib import Path
from typing import Any

from profile_common import (
    PROFILE_SCHEMA_VERSION,
    REQUIRED_VERIFICATION,
    ProfileRepositoryError,
    profile_sha256,
    read_json,
    render_json,
    validate_envelope,
    validate_profile,
)


def _atomic_write(path: Path, text: str, *, refuse_changed_existing: bool) -> bool:
    encoded = text.encode("utf-8")
    if path.exists():
        existing = path.read_bytes()
        if existing == encoded:
            return False
        if refuse_changed_existing:
            raise ProfileRepositoryError(
                f"refusing to rewrite immutable profile revision: {path}"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return True


def _utc_now() -> str:
    return (
        dt.datetime.now(tz=dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_envelope(args: argparse.Namespace) -> dict[str, Any]:
    profile = validate_profile(read_json(args.profile))
    verified_at = args.verified_at or _utc_now()
    envelope = {
        "schema_version": 1,
        "manifest": {
            "minimum_toolkit_version": args.minimum_toolkit_version,
            "patch_label": args.patch_label,
            "profile_schema_version": PROFILE_SCHEMA_VERSION,
            "profile_sha256": profile_sha256(profile),
            "region": args.region,
            "revision": args.revision,
            "verification": sorted(REQUIRED_VERIFICATION),
            "verified_at": verified_at,
        },
        "profile": profile,
    }
    return validate_envelope(envelope)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="publish a complete verified BDO Toolkit opcode profile"
    )
    parser.add_argument("profile", type=Path, help="validated local profile JSON")
    parser.add_argument("--region", default="na-eu")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--patch-label", required=True)
    parser.add_argument("--verified-at", default=None, metavar="UTC_TIMESTAMP")
    parser.add_argument("--minimum-toolkit-version", default="0.1.0")
    parser.add_argument(
        "--confirm-verified",
        action="store_true",
        help="confirm every live/regression check in CONTRIBUTING.md passed",
    )
    parser.add_argument(
        "--promote-stable",
        action="store_true",
        help="also replace channels/REGION/stable.json",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.confirm_verified:
        raise ProfileRepositoryError(
            "publication requires --confirm-verified after completing "
            "CONTRIBUTING.md"
        )
    envelope = build_envelope(args)
    rendered = render_json(envelope)
    archive = (
        args.repository_root / "profiles" / args.region / f"{args.revision}.json"
    )
    wrote_archive = _atomic_write(
        archive,
        rendered,
        refuse_changed_existing=True,
    )
    print(("wrote" if wrote_archive else "unchanged"), archive)
    if args.promote_stable:
        stable = args.repository_root / "channels" / args.region / "stable.json"
        wrote_stable = _atomic_write(
            stable,
            rendered,
            refuse_changed_existing=False,
        )
        print(("wrote" if wrote_stable else "unchanged"), stable)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ProfileRepositoryError) as exc:
        raise SystemExit(f"error: {exc}") from exc

