## ADDED Requirements

### Requirement: Canonical Runtime Entry Points

The project MUST document canonical runtime entry points for backend, frontend, and Docker-based development until the architecture convergence phase is complete.

#### Scenario: A developer starts local work from the documented baseline

- **GIVEN** a developer needs to run the current recommended stack
- **WHEN** they consult the development baseline
- **THEN** the canonical backend entry point is `backend/api/main.py`
- **AND** the canonical frontend package is `frontend/package.json`
- **AND** the canonical Docker stack is `docker-compose-v2.yml`
- **AND** legacy entry points are treated as historical until convergence work is finished

### Requirement: Active OpenSpec Changes Use Current Delta Format

The project MUST keep only current-format active changes under `openspec/changes/`.

#### Scenario: Legacy proposal folders are preserved without breaking validation

- **GIVEN** historical OpenSpec-style documents exist but do not match the current delta format
- **WHEN** the project baseline is maintained
- **THEN** those historical documents are preserved in a legacy area outside the active change set
- **AND** active changes are limited to files that pass current OpenSpec validation
