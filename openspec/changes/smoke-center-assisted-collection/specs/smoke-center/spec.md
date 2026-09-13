## ADDED Requirements

### Requirement: Smoke Center SHALL provide a platform-native validation console
The system SHALL provide a dedicated Smoke Center inside `D:\智能数据分析平台` for operating and reviewing validation runs across the collection-to-analysis-to-report product chain.

#### Scenario: Operator opens Smoke Center
- **WHEN** the operator navigates to the Smoke Center page
- **THEN** the system SHALL display local smoke, live public smoke, and live assisted smoke sections as separate controllable areas

#### Scenario: Operator views structured run outcomes
- **WHEN** a smoke run completes or reaches a manual checkpoint
- **THEN** the system SHALL display the run status, current stage, crawl strategy, robots result, dataset result, analysis result, report result, and failure notes in a structured format

### Requirement: Smoke Center SHALL support layered validation modes
The system SHALL support smoke scenarios for `local`, `live-public`, and `live-assisted` validation modes.

#### Scenario: Operator runs local smoke
- **WHEN** the operator starts a local smoke scenario
- **THEN** the system SHALL validate the product chain using local or uploaded structured data without requiring an external website

#### Scenario: Operator runs live public smoke
- **WHEN** the operator starts a live public scenario with a target URL
- **THEN** the system SHALL validate the target through robots checking before attempting public collection

#### Scenario: Operator runs live assisted smoke
- **WHEN** the operator starts a live assisted scenario
- **THEN** the system SHALL prepare a human-collaboration flow instead of treating the login or captcha step as a fully automated crawl

