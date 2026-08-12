# Profile publication checklist

Publishing `stable.json` asserts more than successful calibration. Complete
all checks against the same candidate profile and patch before running the
publisher with `--confirm-verified`.

## Required profile evidence

- `LOOT_PREVIEW` is populated and a real supported loot source decodes.
- `INVENTORY_TRANSFER` is populated; single and multi-record withdrawals
  decode every record.
- `SOURCE_CONTAINER_DECREMENT`, `SOURCE_ITEM_REFERENCE`, and
  `SOURCE_STACK_DECREMENT` are populated.
- `STORAGE_ITEM_DELTA` has destination, count, instance, and repeat-stride
  authority.
- A stackable manual deposit resolves the correct town and `manual` origin.
- An unstackable multi-record manual deposit emits every record as `manual`.
- A real worker completion resolves the correct town and `worker` origin.
- Character switching does not flood the live activity stream.
- Character-load inventory and storage hydration reports compatible decoder
  health and plausible totals/towns.

## Required regression gates

Run in the `bdo-toolkit` repository:

```powershell
python -m pytest -q -W error -p no:cacheprovider
python -m mypy src/bdo_toolkit
```

Replay the current saved verification captures with the candidate profile and
retain their output privately. Never copy raw captures into this repository.

## Review requirements

- Use a new immutable revision for every published byte change.
- Never rewrite an existing historical revision.
- Review all changed opcodes, offsets, lengths, strides, source evidence, and
  verification metadata before promotion.
- Do not promote while any required feature is untested or inconclusive.
- If a published profile is later disproved, remove it from the stable channel
  immediately but retain the historical file and document the superseding
  revision in the commit message.

