## ADDED Requirements

### Requirement: Assisted authentication collection SHALL support human collaboration
The system SHALL support human-assisted authentication and captcha handling for collection scenarios that require login or manual verification.

#### Scenario: Assisted login begins
- **WHEN** the operator starts an assisted-auth smoke run for a supported platform
- **THEN** the system SHALL move the run into a human-collaboration lifecycle instead of failing immediately or attempting automated captcha bypass

#### Scenario: Manual checkpoint is required
- **WHEN** the collection flow reaches a login, verification, or captcha checkpoint
- **THEN** the system SHALL mark the run as `manual_checkpoint_required` and present the operator with a clear continuation point

#### Scenario: Human completes login and verification
- **WHEN** the operator finishes the required login or verification steps
- **THEN** the system SHALL continue by capturing the resulting session and validating whether the session can be reused for collection

### Requirement: Assisted authentication SHALL be platform-extensible
The system SHALL treat Bilibili as the first verified assisted-auth platform while keeping the assisted-auth flow extensible to additional platforms and custom sites.

#### Scenario: First supported platform is Bilibili
- **WHEN** the first assisted-auth smoke scenario is configured
- **THEN** the system SHALL support Bilibili as the initial operator-tested platform

#### Scenario: New platform is added later
- **WHEN** a future platform requires human-assisted login or captcha
- **THEN** the system SHALL reuse the shared assisted-auth lifecycle with platform-specific login entry, success-check URL, and session reuse configuration

### Requirement: Assisted authentication SHALL never bypass compliance boundaries automatically
The system MUST NOT attempt automated captcha breaking or implicit bypass of site security controls during assisted-auth smoke runs.

#### Scenario: Captcha is encountered
- **WHEN** a target site presents captcha or similar verification
- **THEN** the system SHALL require human intervention and SHALL NOT claim that the verification was completed automatically

#### Scenario: Site disallows collection
- **WHEN** robots checking determines the target is not allowed for collection
- **THEN** the system SHALL stop the smoke run with `blocked_by_robots` before collection proceeds

