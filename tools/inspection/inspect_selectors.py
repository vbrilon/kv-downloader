#!/usr/bin/env python3
"""Inspect which DOM selectors actually match on the live mixer page.

Why: PLAN.md flagged that `.track` and `.track__caption` (the production code's
TRACK_ELEMENT_SELECTOR / TRACK_CAPTION_SELECTOR) match zero elements when
inspected via interactive Chrome 146, yet production logs show 15 tracks
discovered every run in headless mode. This script confirms whether the
discrepancy is UA-gated (headless sets UA=Chrome/120 in chrome_manager).

Usage:
    bin/python tools/inspection/inspect_selectors.py
    bin/python tools/inspection/inspect_selectors.py --override-ua 146
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from selenium.webdriver.common.by import By
from karaoke_automator import KaraokeVersionAutomator
from packages.browser import chrome_manager as cm_mod

SONG_URL = "https://www.karaoke-version.com/custombackingtrack/electric-light-orchestra/don-t-bring-me-down.html"


def patch_ua(version: str) -> None:
    """Monkeypatch chrome_manager to apply a UA override after driver init."""
    original_setup = cm_mod.ChromeManager.setup_driver

    def wrapped(self, *args, **kwargs):
        result = original_setup(self, *args, **kwargs)
        if version != "default":
            target_ua = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36"
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": target_ua})
            logging.info(f"Overrode UA to Chrome/{version}")
        return result

    cm_mod.ChromeManager.setup_driver = wrapped


def inspect():
    parser = argparse.ArgumentParser()
    parser.add_argument("--override-ua", default="default", help="Chrome major version to put in UA (default = let chrome_manager set Chrome/120)")
    parser.add_argument("--visible", action="store_true", help="Run in visible mode instead of headless")
    parser.add_argument("--wait", type=int, default=5, help="Seconds to wait after page load before sampling")
    args = parser.parse_args()

    if args.override_ua != "default":
        patch_ua(args.override_ua)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    automator = KaraokeVersionAutomator(headless=not args.visible, show_progress=False)

    try:
        # Login flow may redirect; use the verify_song_access helper so we get
        # the same code path production uses.
        automator.driver.get(SONG_URL)
        # Give the SPA time to render
        import time
        time.sleep(args.wait)

        d = automator.driver

        actual_ua = d.execute_script("return navigator.userAgent")
        print(f"\n=== Actual navigator.userAgent: {actual_ua}\n")

        cases = [
            (".track", "TRACK_ELEMENT_SELECTOR (legacy)"),
            (".custom__mixer-track-line", "new mixer container"),
            ("[data-index]", "any element with data-index"),
            (".track[data-index]", "legacy + data-index combo"),
            (".custom__mixer-track-line[data-index]", "new + data-index combo"),
            ("button.track__solo", "solo button (legacy compat alias)"),
            (".track__caption", "TRACK_CAPTION_SELECTOR (legacy)"),
            (".custom__mixer-track-caption-name", "new caption span"),
        ]

        print(f"Selector counts on {SONG_URL}:")
        print(f"{'count':>6}  selector")
        for sel, desc in cases:
            count = len(d.find_elements(By.CSS_SELECTOR, sel))
            print(f"{count:>6}  {sel:<40}  // {desc}")

        # Page source size + sample of class names actually present
        src = d.page_source
        print(f"\npage_source size: {len(src):,} chars")

        # Did we get redirected to login?
        print(f"current_url: {d.current_url}")
        print(f"page title: {d.title}")

        # Sample classes containing "track" as a token
        sample = d.execute_script("""
            const out = new Set();
            for (const el of document.querySelectorAll('[class*="track"]')) {
                const cls = el.className;
                if (typeof cls !== 'string') continue;
                for (const t of cls.split(/\\s+/)) {
                    if (t.includes('track')) out.add(t);
                }
                if (out.size > 30) break;
            }
            return Array.from(out).sort();
        """)
        print(f"\nDistinct 'track'-containing class tokens (sample, sorted):")
        for cls in sample:
            print(f"  {cls}")

        # Cookies / A-B markers
        cookies = d.get_cookies()
        cookie_names = sorted(c['name'] for c in cookies)
        print(f"\nCookie names: {cookie_names}")
        print(f"Cookie 'karaoke-version' value (truncated): {next((c['value'][:60] for c in cookies if c['name'] == 'karaoke-version'), '<missing>')}")

        markers = d.execute_script("""
            return {
                has_new_mixer_marker: document.body.innerHTML.includes('custom__mixer'),
                has_legacy_marker: document.body.innerHTML.includes('class=\"track\"'),
                nav_text_first_line: (document.querySelector('nav')?.innerText || '').split('\\n')[0],
            };
        """)
        print(f"has_new_mixer_marker: {markers['has_new_mixer_marker']}")
        print(f"has_legacy_marker:    {markers['has_legacy_marker']}")
        print(f"nav greeting:         {markers['nav_text_first_line']}")

        # Grab a sample of what `.track` actually returns
        containers = d.execute_script("""
            return {
                mixer_inner_count: document.querySelectorAll('.mixer__inner').length,
                mixer_inner_html_size: document.querySelector('.mixer__inner')?.outerHTML?.length || 0,
                custom_mixer_container_count: document.querySelectorAll('.custom__mixer-container').length,
                custom_mixer_html_size: document.querySelector('.custom__mixer-container')?.outerHTML?.length || 0,
                mixer_inner_visibility: (() => {
                    const m = document.querySelector('.mixer__inner');
                    if (!m) return null;
                    const s = getComputedStyle(m);
                    return { display: s.display, visibility: s.visibility, opacity: s.opacity, offsetHeight: m.offsetHeight };
                })(),
                has_track_dataindex_count: document.querySelectorAll('.track[data-index]').length,
            };
        """)
        print(f"\nMixer container stats:")
        import json
        print(json.dumps(containers, indent=2))

    finally:
        try:
            automator.driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    inspect()
