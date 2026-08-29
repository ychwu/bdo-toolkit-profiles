# BDO Toolkit Verified Profiles

This repository publishes maintainer-verified opcode profiles for the item
decoder in [`bdo-toolkit`](https://github.com/ychwu/bdo-toolkit). It is kept
separate from the Python package because game patches and profile verification
have a weekly lifecycle while toolkit code releases do not.

Profiles contain protocol metadata only. Never commit packet captures, account
data, session identifiers, local calibration inputs, or signing keys here.

## Consumer endpoints

The current verified NA/EU profile will be published at:

```text
https://ychwu.github.io/bdo-toolkit-profiles/channels/na-eu/stable.json
```

Every stable envelope is also retained under an immutable revision URL:

```text
https://ychwu.github.io/bdo-toolkit-profiles/profiles/na-eu/REVISION.json
```

The stable endpoint intentionally does not exist until the first complete
profile passes every publication gate. A partial transfer-only profile must
not be presented as the general decoder authority.

Toolkit users install a profile explicitly before capture:

```powershell
bdo-toolkit profile fetch `
  https://ychwu.github.io/bdo-toolkit-profiles/channels/na-eu/stable.json `
  --output opcodes.verified.json
```

Capture and replay never contact this repository automatically. Historical
PCAP replay must use the immutable profile from the recording's own patch era,
not the current `stable.json`.

## Weekly publication

1. Calibrate a fresh local profile after the patch.
2. Complete the live and historical verification checklist in
   [CONTRIBUTING.md](CONTRIBUTING.md).
3. Publish an immutable revision and update the stable channel in one command:

   ```powershell
   python scripts/publish_profile.py C:\path\to\opcodes.local `
     --revision na-eu-2026-08-11-r1 `
     --patch-label 2026-08-11 `
     --confirm-verified `
     --promote-stable
   ```

4. Run `python scripts/validate_repository.py`.
5. Review the generated JSON diff before committing it.

The publisher refuses inactive or incomplete profiles, refuses to overwrite an
immutable revision with different bytes, computes the canonical profile
SHA-256, and writes the channel pointer atomically.

## Trust boundary

The version-1 envelope digest detects corruption and binds its manifest to the
embedded profile. It is not a digital signature: consumers trust the HTTPS
endpoint and this repository's GitHub access controls. A future signed-envelope
schema can strengthen publisher authentication without changing archived
version-1 envelopes.

