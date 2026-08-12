"""Validate every public profile envelope and stable/archive relationship."""

from __future__ import annotations

from pathlib import Path

from profile_common import ProfileRepositoryError, read_json, validate_envelope


FORBIDDEN_SUFFIXES = {".key", ".pcap", ".pcapng", ".pem"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    problems: list[str] = []
    validated = 0
    for path in sorted((root / "profiles").glob("*/*.json")):
        try:
            envelope = validate_envelope(read_json(path))
            expected_name = f"{envelope['manifest']['revision']}.json"
            if path.name != expected_name:
                raise ProfileRepositoryError(
                    f"archive filename must be {expected_name}"
                )
            if path.parent.name != envelope["manifest"]["region"]:
                raise ProfileRepositoryError(
                    "archive directory must match manifest region"
                )
            validated += 1
        except ProfileRepositoryError as exc:
            problems.append(f"{path}: {exc}")

    for stable in sorted((root / "channels").glob("*/stable.json")):
        try:
            envelope = validate_envelope(read_json(stable))
            region = envelope["manifest"]["region"]
            revision = envelope["manifest"]["revision"]
            if stable.parent.name != region:
                raise ProfileRepositoryError(
                    "stable channel directory must match manifest region"
                )
            archive = root / "profiles" / region / f"{revision}.json"
            if not archive.is_file():
                raise ProfileRepositoryError(
                    f"stable channel has no immutable archive: {archive}"
                )
            if read_json(archive) != envelope:
                raise ProfileRepositoryError(
                    "stable channel differs from its immutable archive"
                )
            validated += 1
        except ProfileRepositoryError as exc:
            problems.append(f"{stable}: {exc}")

    for path in root.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden private/sensitive file: {path}")

    if problems:
        raise SystemExit("\n".join(f"ERROR: {problem}" for problem in problems))
    print(f"validated {validated} published profile envelope(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

