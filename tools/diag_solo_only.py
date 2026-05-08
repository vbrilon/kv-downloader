#!/usr/bin/env python3
"""Solo-only diagnostic: navigate to a song, attempt to solo a track via the
production TrackManager, report whether the button actually became active.

No downloads. No multi-tab. Just a clean apples-to-apples test of whether the
production solo path works *right now* against a given song.
"""
import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.browser import ChromeManager
from packages.authentication import LoginManager
from packages.track_management import TrackManager
from packages.utils.solo_state import is_solo_button_active

DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "bryan-adams/18-til-i-die.html"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--song-url", default=DEFAULT_SONG_URL)
    ap.add_argument("--track", type=int, default=1)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        force=True,
    )
    log = logging.getLogger("diag")

    chrome = ChromeManager(headless=args.headless)
    chrome.setup_driver()
    chrome.setup_folders()
    driver = chrome.driver
    wait = chrome.wait
    try:
        login = LoginManager(driver, wait)
        if not login.login_with_session_persistence():
            log.error("login failed")
            return 2

        tm = TrackManager(driver, wait)
        tracks = tm.discover_tracks(args.song_url)
        if not tracks:
            log.error("no tracks discovered")
            return 1

        target = next(
            (t for t in tracks if str(t["index"]) == str(args.track)),
            None,
        )
        if not target:
            log.error(f"track {args.track} not in discovered list")
            return 1
        log.info(f"target: index={target['index']} name='{target['name']}'")

        # Production setup step
        tm.ensure_intro_count_enabled(args.song_url)

        # Solo via production path
        ok = tm.ensure_only_track_active(args.track, args.song_url)
        log.info(f"ensure_only_track_active returned: {ok}")
        ok2 = tm.solo_track({"name": target["name"], "index": args.track},
                            args.song_url)
        log.info(f"solo_track returned: {ok2}")

        # Independent verification: read the actual DOM state
        from selenium.webdriver.common.by import By
        from packages.configuration.selectors import (
            TRACK_ELEMENT_SELECTOR, SOLO_BUTTON_SELECTORS,
        )
        track_els = driver.find_elements(By.CSS_SELECTOR, TRACK_ELEMENT_SELECTOR)
        for el in track_els:
            di = el.get_attribute("data-index")
            if di == str(args.track):
                for sel in SOLO_BUTTON_SELECTORS:
                    try:
                        btn = el.find_element(By.CSS_SELECTOR, sel)
                        cls = btn.get_attribute("class") or ""
                        ap = btn.get_attribute("aria-pressed") or ""
                        ds = btn.get_attribute("data-state") or ""
                        active = is_solo_button_active(btn)
                        log.info(
                            f"DOM verify: track {di} solo button "
                            f"class='{cls}' aria_pressed='{ap}' "
                            f"data_state='{ds}' is_active={active}"
                        )
                        break
                    except Exception:
                        continue
                break

        # Sit for a moment so a visible browser can be eyeballed
        if not args.headless:
            time.sleep(2)
    finally:
        chrome.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
