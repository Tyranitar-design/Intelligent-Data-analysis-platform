# CloakBrowser Smart v2 Integration

## Summary

Add `CloakBrowser` as an optional stealth browser engine for the intelligent crawler stack, focused on improving dynamic JS rendering and protected-page handling while preserving robots.txt compliance and the existing human-in-the-loop auth flow.

## Why

- Current `PlaywrightStrategy` is the main browser fallback, but some pages benefit from a stealthier Chromium runtime.
- The project already has smart v2 probing, strategy fallback, login/session handling, and Smoke Center validation.
- We want a drop-in enhancement that improves success rate on difficult dynamic pages without replacing the current crawler architecture.

## Scope

- Add an optional `CloakBrowser`-backed browser strategy.
- Let smart v2 choose it as a fallback or preferred strategy when a probe indicates dynamic/protected content.
- Keep robots.txt checks first-class.
- Keep human-assisted login/captcha as the approved path for protected flows.

## Non-goals

- No automatic bypass of access controls.
- No rewrite of the crawler pipeline.
- No replacement of Playwright or the existing adaptive strategy stack.
