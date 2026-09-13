## ADDED Requirements

### Requirement: Repository Ignore Policy

The repository MUST ignore local runtime artifacts, secrets, generated data, caches, and machine-specific outputs that do not belong in version control.

#### Scenario: Generated runtime artifacts stay local

- **GIVEN** a developer creates local virtual environments, `node_modules`, build output, local databases, model artifacts, or raw crawl outputs
- **WHEN** `git status --short` is run
- **THEN** these generated runtime artifacts are excluded by repository ignore policy
- **AND** source code, documentation, OpenSpec files, and project Codex collaboration assets remain versionable

### Requirement: Versioned Collaboration Assets

The repository MUST keep project collaboration assets under version control when they are needed to reproduce the agreed workflow.

#### Scenario: Collaboration assets remain available to new contributors

- **GIVEN** the project relies on `.codex/`, `openspec/`, and `AGENTS.md` to coordinate work
- **WHEN** a new collaborator clones the repository
- **THEN** those collaboration assets are present in the repository
- **AND** they do not depend on local secrets or machine-specific state

