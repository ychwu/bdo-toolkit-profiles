# NA/EU stable channel

`stable.json` is created only by `scripts/publish_profile.py` after the complete
verification checklist is confirmed. Its envelope must exactly match one file
in `profiles/na-eu/`.

The absence of `stable.json` means no complete maintainer-verified profile has
been published yet. Consumers must fail clearly or use an explicitly selected
local/historical profile; they must not guess or fall back to another region.

