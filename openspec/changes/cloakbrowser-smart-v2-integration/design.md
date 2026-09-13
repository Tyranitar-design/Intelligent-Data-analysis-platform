# Design

## Architecture

Introduce a new browser strategy wrapper around `CloakBrowser` and register it inside the intelligent crawler strategy stack alongside `PlaywrightStrategy`, `Crawl4AIStrategy`, `ScraplingStrategy`, and `HttpxStrategy`.

The new strategy should:
- expose a capability profile similar to Playwright
- support navigation, DOM extraction, cookies/session reuse, and page-content capture
- stay behind the existing adaptive selection logic

## Data Flow

1. `crawl.py` receives URL/probe/crawl requests.
2. `AdaptiveScraper.probe()` classifies the target as static, dynamic, protected, or auth-requiring.
3. `IntentEngine` / strategy selection can choose the new `CloakBrowser` strategy when the page is dynamic or protected and the strategy is available.
4. The strategy returns normalized `StrategyResult` data so downstream analysis, dataset persistence, and Smoke Center reporting remain unchanged.

## Interfaces

- Add a new strategy class under `backend/crawlers/intelligent/strategies/`.
- Extend the strategy registry / default loader to optionally include it when installed.
- Add a strategy capability label that makes the engine understand it is a browser-automation fallback, not a new auth bypass path.

## Failure & Fallback

- If `CloakBrowser` is unavailable, fall back to existing Playwright behavior.
- If the page requires login/captcha, keep the current human-assisted checkpoint flow.
- If the engine errors or fails quality checks, degrade to the next available strategy.

## Validation

- Unit test strategy discovery and fallback order.
- Add a smoke test that forces a dynamic page to prefer the stealth browser path when available.
- Verify build/imports do not fail when `CloakBrowser` is absent.
