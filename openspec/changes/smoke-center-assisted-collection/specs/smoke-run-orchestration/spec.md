## ADDED Requirements

### Requirement: Smoke runs SHALL be executed through a scenario registry
The system SHALL execute smoke validations through named scenarios with explicit mode, robots policy, auth requirements, preferred strategy, and post-processing steps.

#### Scenario: System lists available scenarios
- **WHEN** the operator requests available smoke scenarios
- **THEN** the system SHALL return stable scenario identifiers, labels, mode, input requirements, and auth requirements

#### Scenario: Operator runs a scenario
- **WHEN** the operator starts a scenario
- **THEN** the system SHALL execute the corresponding validation workflow using the registered scenario definition rather than ad hoc branching

### Requirement: Smoke runs SHALL produce a standardized result model
The system SHALL normalize smoke execution outputs into a unified run result model regardless of whether the underlying path uses URL crawl, smart v2 crawl, assisted auth, or local data flow.

#### Scenario: Public crawl succeeds
- **WHEN** a public smoke scenario completes successfully
- **THEN** the run result SHALL record the selected crawl strategy, dataset save result, analysis result, report result, and supporting artifacts

#### Scenario: Manual checkpoint interrupts execution
- **WHEN** an assisted-auth scenario pauses for human intervention
- **THEN** the run result SHALL preserve the scenario identifier, current stage, partial evidence, and the `manual_checkpoint_required` status

#### Scenario: Robots policy blocks execution
- **WHEN** robots checking disallows the target
- **THEN** the run result SHALL be marked `blocked_by_robots` and SHALL include the robots decision evidence

### Requirement: Smoke runs SHALL support staged operator visibility
The system SHALL expose the current stage of a smoke run so the operator can understand whether the system is probing, crawling, waiting for human action, saving data, analyzing data, or generating a report.

#### Scenario: Operator polls a run
- **WHEN** the operator loads or refreshes an in-progress smoke run
- **THEN** the system SHALL return the current stage and step-level status summary for the run

### Requirement: Smoke runs SHALL preserve evidence without duplicating secrets
The system SHALL persist run summaries and step results while avoiding duplication of sensitive authentication material inside smoke run records.

#### Scenario: Assisted-auth run stores evidence
- **WHEN** an assisted-auth run captures a reusable session
- **THEN** the system SHALL store the run summary and session validity result without copying raw cookies or secrets into the smoke run result record
