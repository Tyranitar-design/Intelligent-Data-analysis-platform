# Known Issues

## OpenSpec

- Existing `openspec/changes/*` entries currently fail validation under the latest OpenSpec delta rules.
- Likely cause: legacy change documents do not yet use the required delta headers and scenario blocks.

## Operational Notes

- If OpenSpec workflows are used for new changes, prefer creating fresh compliant changes instead of extending the old invalid ones until migration is complete.

