# Crawler / Smart v2 CloakBrowser Integration

## ADDED Requirements

### Requirement: Optional stealth browser strategy
The crawler system SHALL support `CloakBrowser` as an optional browser automation strategy for smart v2 crawling.

#### Scenario: Dynamic page chooses stealth browser
- **GIVEN** a URL probed as dynamic or protected
- **AND** the stealth browser strategy is installed and available
- **WHEN** smart v2 selects a browser fallback
- **THEN** the engine MAY choose `CloakBrowser` before ordinary Playwright for that request
- **AND** the returned crawl result SHALL remain normalized to the existing `StrategyResult` / `CrawlResult` schema.

### Requirement: Robots compliance remains first
The crawler system SHALL continue to run robots.txt checks before any browser strategy is used.

#### Scenario: Blocked target
- **GIVEN** robots.txt disallows the target path
- **WHEN** a smoke or crawl request is submitted
- **THEN** the system SHALL return `blocked_by_robots`
- **AND** SHALL NOT launch `CloakBrowser` or Playwright.

### Requirement: Human-assisted auth remains the approved path
The crawler system SHALL keep the existing assisted-auth flow for login/captcha targets.

#### Scenario: Login-required page
- **GIVEN** a URL that requires login or captcha
- **WHEN** smart v2 probes the page
- **THEN** the system SHALL surface the assisted-auth path
- **AND** SHALL NOT attempt to auto-bypass authentication.

### Requirement: Graceful fallback when unavailable
The crawler system SHALL fall back to current strategies if `CloakBrowser` cannot be started or is not installed.

#### Scenario: Missing stealth browser
- **GIVEN** the new strategy is configured as preferred
- **AND** the runtime cannot import or launch `CloakBrowser`
- **WHEN** a crawl request is executed
- **THEN** the engine SHALL continue with the next available strategy
- **AND** SHALL record the fallback reason in the crawl result metadata.
