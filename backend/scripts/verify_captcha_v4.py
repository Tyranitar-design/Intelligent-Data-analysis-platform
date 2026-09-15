# -*- coding: utf-8 -*-
"""V4 行为验证码三链实测（CapSolver token → 页面注入 → 服务端验证）

链：
1. reCAPTCHA v2 — https://www.google.com/recaptcha/api2/demo（官方 demo）
2. hCaptcha     — https://accounts.hcaptcha.com/demo（官方 demo）
3. Turnstile    — https://nopecha.com/demo/turnstile（练习靶）

key：--key-file 或 CAPSOLVER_API_KEY（不打印、不落盘）
证据：docs/evidence/captcha-v4/{result.txt,截图}

运行（backend/ 下）：
    .\\venv\\Scripts\\python.exe scripts\\verify_captcha_v4.py --key-file <path>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

EVIDENCE_DIR = BACKEND_DIR.parent / "docs" / "evidence" / "captcha-v4"

CHECKS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {name} -- {detail}", flush=True)


def load_key(args) -> str:
    if args.key_file:
        return Path(args.key_file).read_text(encoding="utf-8").strip()
    key = (os.environ.get("CAPSOLVER_API_KEY") or "").strip()
    if not key:
        print("[error] 需要 --key-file 或 CAPSOLVER_API_KEY", file=sys.stderr)
        raise SystemExit(2)
    return key


# --------------------------------------------------------------------------- #
# 链 1 · reCAPTCHA v2
# --------------------------------------------------------------------------- #
async def chain_recaptcha_v2(page, client) -> None:
    url = "https://www.google.com/recaptcha/api2/demo"
    t0 = time.time()
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(3000)
    sitekey = await page.evaluate(
        "() => { const el = document.querySelector('[data-sitekey]');"
        " return el && el.getAttribute('data-sitekey'); }"
    )
    if not sitekey:
        record("recaptcha-v2 出票+注入+验证", False, "sitekey 未找到")
        return
    print(f"    sitekey={sitekey[:20]}...", flush=True)
    result = await client.solve_recaptcha_v2(sitekey, url)
    if not result["success"]:
        record("recaptcha-v2 出票+注入+验证", False, f"出票失败: {result['error']}")
        return
    token = result["token"]
    print(f"    token ok ({len(token)} chars, {time.time() - t0:.0f}s)", flush=True)
    await page.evaluate(
        """(token) => {
            const ta = document.getElementById('g-recaptcha-response')
                    || document.querySelector('textarea[name="g-recaptcha-response"]');
            if (ta) { ta.value = token; ta.style.display = 'block'; }
        }""",
        token,
    )
    await page.wait_for_timeout(500)
    await page.click('input[type="submit"]')
    await page.wait_for_timeout(4500)
    body = await page.locator("body").inner_text()
    ok = "Success" in body or "success" in body.lower()
    record("recaptcha-v2 出票+注入+验证", ok, body[:90].replace("\n", " "))
    await page.screenshot(path=str(EVIDENCE_DIR / "recaptcha-v2.png"))


# --------------------------------------------------------------------------- #
# 链 2 · hCaptcha
# --------------------------------------------------------------------------- #
async def chain_hcaptcha(page, client) -> None:
    url = "https://accounts.hcaptcha.com/demo"
    t0 = time.time()
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(3500)
    sitekey = await page.evaluate(
        "() => { const el = document.querySelector('[data-sitekey]');"
        " return el && el.getAttribute('data-sitekey'); }"
    )
    if not sitekey:
        record("hcaptcha 出票+注入+验证", False, "sitekey 未找到")
        return
    print(f"    sitekey={sitekey[:20]}...", flush=True)
    result = await client.solve_hcaptcha(sitekey, url)
    if not result["success"]:
        record("hcaptcha 出票+注入+验证", False, f"出票失败: {result['error']}")
        return
    token = result["token"]
    print(f"    token ok ({len(token)} chars, {time.time() - t0:.0f}s)", flush=True)
    await page.evaluate(
        """(token) => {
            const ta = document.querySelector('textarea[name="h-captcha-response"]');
            if (ta) {
                ta.value = token;
                ta.dispatchEvent(new Event('input', { bubbles: true }));
                ta.dispatchEvent(new Event('change', { bubbles: true }));
            }
            const hidden = document.querySelector('input[name="h-captcha-response"]');
            if (hidden) { hidden.value = token; }
        }""",
        token,
    )
    await page.wait_for_timeout(600)
    # 提交按钮（demo 页）
    submitted = False
    for selector in ('button[type="submit"]', 'input[type="submit"]', "text=Submit"):
        try:
            await page.click(selector, timeout=3000)
            submitted = True
            break
        except Exception:
            continue
    if not submitted:
        record("hcaptcha 出票+注入+验证", False, "提交按钮未找到")
        return
    await page.wait_for_timeout(4500)
    body = await page.locator("body").inner_text()
    ok = "Success" in body or "success" in body.lower()
    record("hcaptcha 出票+注入+验证", ok, body[:90].replace("\n", " "))
    await page.screenshot(path=str(EVIDENCE_DIR / "hcaptcha.png"))


# --------------------------------------------------------------------------- #
# 链 3 · Turnstile
# --------------------------------------------------------------------------- #
async def chain_turnstile(page, client) -> None:
    url = "https://nopecha.com/demo/turnstile"
    t0 = time.time()
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(4000)
    sitekey = await page.evaluate(
        "() => { const el = document.querySelector('[data-sitekey]');"
        " return el && el.getAttribute('data-sitekey'); }"
    )
    if not sitekey:
        record("turnstile 出票+注入+验证", False, "sitekey 未找到")
        return
    print(f"    sitekey={sitekey[:20]}...", flush=True)
    result = await client.solve_turnstile(sitekey, url)
    if not result["success"]:
        record("turnstile 出票+注入+验证", False, f"出票失败: {result['error']}")
        return
    token = result["token"]
    print(f"    token ok ({len(token)} chars, {time.time() - t0:.0f}s)", flush=True)
    await page.evaluate(
        """(token) => {
            const el = document.querySelector('input[name="cf-turnstile-response"]');
            if (el) {
                el.value = token;
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }
            // 兜底：某些页面把 token 放在 textarea
            const ta = document.querySelector('textarea[name="cf-turnstile-response"]');
            if (ta) { ta.value = token; }
        }""",
        token,
    )
    await page.wait_for_timeout(600)
    # nopecha 的验证提交（页面上一般有 Submit / Verify 按钮）
    submitted = False
    for selector in ("#submit", "button:has-text('Submit')", "button:has-text('Verify')", 'button[type="submit"]'):
        try:
            await page.click(selector, timeout=3000)
            submitted = True
            break
        except Exception:
            continue
    await page.wait_for_timeout(3500)
    body = await page.locator("body").inner_text()
    ok = any(marker in body for marker in ("Success", "success", "passed", "Passed", "✔", "✅"))
    record(
        "turnstile 出票+注入+验证",
        bool(ok and submitted),
        f"submitted={submitted} :: " + body[:80].replace("\n", " "),
    )
    await page.screenshot(path=str(EVIDENCE_DIR / "turnstile.png"))


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
async def main() -> int:
    parser = argparse.ArgumentParser(description="V4 行为验证码三链实测")
    parser.add_argument("--key-file", default=None)
    parser.add_argument("--chains", default="recaptcha,hcaptcha,turnstile")
    args = parser.parse_args()

    key = load_key(args)
    print(f"[key] loaded (length={len(key)})", flush=True)

    from crawlers.anticrawl.capsolver_client import CapSolverClient

    client = CapSolverClient(api_key=key, poll_interval=3.0, max_polls=40)
    balance_before = await client.get_balance()
    print(f"[balance] {balance_before}", flush=True)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright

    chains = [c.strip() for c in args.chains.split(",") if c.strip()]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            if "recaptcha" in chains:
                print("== reCAPTCHA v2 ==", flush=True)
                try:
                    await chain_recaptcha_v2(page, client)
                except Exception as exc:  # noqa: BLE001
                    record("recaptcha-v2 出票+注入+验证", False, f"{type(exc).__name__}: {str(exc)[:130]}")
            if "hcaptcha" in chains:
                print("== hCaptcha ==", flush=True)
                try:
                    await chain_hcaptcha(page, client)
                except Exception as exc:  # noqa: BLE001
                    record("hcaptcha 出票+注入+验证", False, f"{type(exc).__name__}: {str(exc)[:130]}")
            if "turnstile" in chains:
                print("== Turnstile ==", flush=True)
                try:
                    await chain_turnstile(page, client)
                except Exception as exc:  # noqa: BLE001
                    record("turnstile 出票+注入+验证", False, f"{type(exc).__name__}: {str(exc)[:130]}")
        finally:
            await browser.close()

    balance_after = await client.get_balance()
    print(f"[balance] {balance_before} -> {balance_after}", flush=True)
    record("余额消耗", True, f"{balance_before} -> {balance_after}")

    print("\n=== CAPTCHA V4 RESULTS ===", flush=True)
    all_ok = all(ok for _name, ok, _detail in CHECKS if _name != "余额消耗")
    lines = [f"  [{'OK  ' if ok else 'FAIL'}] {name} -- {detail}" for name, ok, detail in CHECKS]
    for line in lines:
        print(line, flush=True)
    verdict = "all checks passed" if all_ok else "failures present"
    print(f"RESULT: {verdict}", flush=True)
    (EVIDENCE_DIR / "result.txt").write_text(
        "\n".join(lines) + f"\nRESULT: {verdict}\n", encoding="utf-8"
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
