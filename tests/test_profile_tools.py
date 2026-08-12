from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from profile_common import (  # noqa: E402
    REQUIRED_PROFILE_FAMILIES,
    REQUIRED_VERIFICATION,
    ProfileRepositoryError,
    profile_sha256,
    validate_envelope,
    validate_profile,
)
from publish_profile import main as publish_main  # noqa: E402


def _complete_profile() -> dict[str, object]:
    specs: dict[str, list[dict[str, object]]] = {
        family: [{"event": family, "opcode": "0x0001", "length": 10}]
        for family in REQUIRED_PROFILE_FAMILIES
    }
    specs["STORAGE_ITEM_DELTA"] = [
        {
            "context_offset": 1,
            "destination_instance_offset": 10,
            "event": "STORAGE_ITEM_DELTA",
            "item_id_offset": 5,
            "length": 20,
            "opcode": "0x0001",
            "record_count_offset": 3,
            "repeat_stride": 10,
        }
    ]
    return {
        "calibration_item_id": 15156,
        "profile_active": True,
        "specs": specs,
        "updated_at": "2026-08-11T00:00:00Z",
        "version": 1,
    }


def _envelope(profile: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "manifest": {
            "minimum_toolkit_version": "0.1.0",
            "patch_label": "2026-08-11",
            "profile_schema_version": 1,
            "profile_sha256": profile_sha256(profile),
            "region": "na-eu",
            "revision": "na-eu-2026-08-11-r1",
            "verification": sorted(REQUIRED_VERIFICATION),
            "verified_at": "2026-08-11T00:00:00Z",
        },
        "profile": profile,
    }


class ProfileToolTests(unittest.TestCase):
    def test_boolean_schema_versions_are_rejected(self) -> None:
        profile = _complete_profile()
        profile["version"] = True
        with self.assertRaisesRegex(ProfileRepositoryError, "profile version"):
            validate_profile(profile)

        envelope = _envelope(_complete_profile())
        envelope["schema_version"] = True
        with self.assertRaisesRegex(ProfileRepositoryError, "schema_version"):
            validate_envelope(envelope)

        envelope = _envelope(_complete_profile())
        envelope["manifest"]["profile_schema_version"] = True
        with self.assertRaisesRegex(
            ProfileRepositoryError,
            "profile_schema_version",
        ):
            validate_envelope(envelope)

    def test_incomplete_profile_cannot_be_published(self) -> None:
        profile = _complete_profile()
        profile["specs"]["LOOT_PREVIEW"] = []  # type: ignore[index]

        with self.assertRaisesRegex(ProfileRepositoryError, "LOOT_PREVIEW"):
            validate_profile(profile)

    def test_envelope_digest_binds_embedded_profile(self) -> None:
        profile = _complete_profile()
        envelope = {
            "schema_version": 1,
            "manifest": {
                "minimum_toolkit_version": "0.1.0",
                "patch_label": "2026-08-11",
                "profile_schema_version": 1,
                "profile_sha256": profile_sha256(profile),
                "region": "na-eu",
                "revision": "na-eu-2026-08-11-r1",
                "verification": sorted(REQUIRED_VERIFICATION),
                "verified_at": "2026-08-11T00:00:00Z",
            },
            "profile": profile,
        }
        validate_envelope(envelope)
        profile["calibration_item_id"] = 7003

        with self.assertRaisesRegex(ProfileRepositoryError, "digest mismatch"):
            validate_envelope(envelope)

    def test_publisher_writes_matching_archive_and_stable_channel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "candidate.json"
            input_path.write_text(
                json.dumps(_complete_profile()),
                encoding="utf-8",
            )
            result = publish_main(
                [
                    str(input_path),
                    "--repository-root",
                    str(root),
                    "--revision",
                    "na-eu-2026-08-11-r1",
                    "--patch-label",
                    "2026-08-11",
                    "--verified-at",
                    "2026-08-11T00:00:00Z",
                    "--confirm-verified",
                    "--promote-stable",
                ]
            )
            self.assertEqual(result, 0)
            archive = root / "profiles/na-eu/na-eu-2026-08-11-r1.json"
            stable = root / "channels/na-eu/stable.json"
            self.assertEqual(archive.read_bytes(), stable.read_bytes())
            validate_envelope(json.loads(archive.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
