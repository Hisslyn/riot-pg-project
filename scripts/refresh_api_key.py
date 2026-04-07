"""
Automatically regenerate a Riot Games development API key and update .env.

Requires:
    pip install playwright
    playwright install chromium

Usage:
    python scripts/refresh_api_key.py            # headless
    python scripts/refresh_api_key.py --headed   # show browser (useful for debugging)

Credentials are read from .env:
    RIOT_USERNAME=your@email.com
    RIOT_PASSWORD=yourpassword
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ENV_FILE = Path(__file__).parent.parent / ".env"
DASHBOARD_URL = "https://developer.riotgames.com/"


def load_credentials() -> tuple[str, str]:
    load_dotenv(ENV_FILE, override=True)
    username = os.getenv("RIOT_USERNAME")
    password = os.getenv("RIOT_PASSWORD")
    if not username or not password:
        print("❌  RIOT_USERNAME and RIOT_PASSWORD must be set in your .env file.")
        sys.exit(1)
    return username, password


def update_env_file(new_key: str) -> None:
    """Replace the RIOT_API_KEY line in .env, preserving everything else."""
    content = ENV_FILE.read_text()
    updated = re.sub(
        r"^RIOT_API_KEY=.*$",
        f"RIOT_API_KEY={new_key}",
        content,
        flags=re.MULTILINE,
    )
    if updated == content:
        # Key line didn't exist yet — append it
        updated = content.rstrip("\n") + f"\nRIOT_API_KEY={new_key}\n"
    ENV_FILE.write_text(updated)
    print(f"✅  .env updated with new key: {new_key[:12]}...")


def refresh_key(headed: bool = False) -> str:
    username, password = load_credentials()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = browser.new_page()

        # ── 1. Go to the developer portal ──────────────────────────────────
        print("🌐  Opening Riot developer portal...")
        page.goto(DASHBOARD_URL, wait_until="networkidle")

        # ── 2. Click Login ──────────────────────────────────────────────────
        try:
            page.click("a[href='/login'], a:has-text('Login'), button:has-text('Login')", timeout=8_000)
        except PlaywrightTimeout:
            print("⚠️   Could not find Login button — may already be logged in, continuing...")

        # ── 3. Handle Riot OAuth (auth.riotgames.com) ───────────────────────
        # Wait for either the auth page or a redirect back to the dashboard
        page.wait_for_load_state("networkidle")

        if "auth.riotgames.com" in page.url:
            print("🔑  Logging in via Riot OAuth...")

            # Username step
            page.fill("input[name='username'], input[type='text']", username)

            # Some flows show username + password together; others are two steps
            try:
                page.fill("input[name='password'], input[type='password']", password)
                page.click("button[type='submit']", timeout=4_000)
            except PlaywrightTimeout:
                # Two-step: submit username first, then password appears
                page.click("button[type='submit']", timeout=4_000)
                page.wait_for_selector("input[name='password'], input[type='password']", timeout=8_000)
                page.fill("input[name='password'], input[type='password']", password)
                page.click("button[type='submit']", timeout=4_000)

            # Wait for redirect back to developer portal
            page.wait_for_url("**/developer.riotgames.com/**", timeout=15_000)
            page.wait_for_load_state("networkidle")
            print("✅  Logged in.")
        else:
            print("ℹ️   Already authenticated.")

        # ── 4. Find and click the Regenerate button ─────────────────────────
        print("🔄  Looking for Regenerate API Key button...")
        try:
            page.click(
                "button:has-text('Regenerate'), "
                "a:has-text('Regenerate'), "
                "button:has-text('Generate API Key'), "
                "input[value='Regenerate API Key']",
                timeout=10_000,
            )
        except PlaywrightTimeout:
            print(
                "❌  Could not find the Regenerate button.\n"
                "    Run with --headed to inspect the dashboard manually.\n"
                "    You may need to update the selector in this script."
            )
            browser.close()
            sys.exit(1)

        page.wait_for_load_state("networkidle")

        # ── 5. Confirm any modal / dialog if present ────────────────────────
        try:
            page.click(
                "button:has-text('Confirm'), button:has-text('Yes'), button:has-text('OK')",
                timeout=4_000,
            )
            page.wait_for_load_state("networkidle")
        except PlaywrightTimeout:
            pass  # No confirmation dialog — that's fine

        # ── 6. Read the new API key ─────────────────────────────────────────
        print("🔍  Reading new API key...")
        try:
            # The key is typically shown in a <code>, <input>, or <span> element
            key_el = page.wait_for_selector(
                "code:has-text('RGAPI-'), "
                "input[value^='RGAPI-'], "
                "span:has-text('RGAPI-'), "
                "p:has-text('RGAPI-')",
                timeout=10_000,
            )
            raw = key_el.input_value() if key_el.evaluate("el => el.tagName") == "INPUT" else key_el.inner_text()
            # Extract the key with a regex in case there's surrounding whitespace/text
            match = re.search(r"RGAPI-[0-9a-f\-]{36}", raw)
            if not match:
                raise ValueError(f"Unexpected key format: {raw!r}")
            new_key = match.group(0)
        except (PlaywrightTimeout, ValueError) as exc:
            print(
                f"❌  Could not read the API key from the page: {exc}\n"
                "    Run with --headed to see what the dashboard looks like."
            )
            browser.close()
            sys.exit(1)

        browser.close()

    update_env_file(new_key)
    return new_key


def main():
    parser = argparse.ArgumentParser(description="Refresh Riot dev API key in .env")
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    args = parser.parse_args()
    refresh_key(headed=args.headed)


if __name__ == "__main__":
    main()
