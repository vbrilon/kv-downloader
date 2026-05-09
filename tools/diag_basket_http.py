#!/usr/bin/env python3
"""Diagnostic: why is direct basket.php returning 500?

Logs in via Selenium, captures cookies + the exact basket.php URL the UI
generates, then replays that URL via Python requests with various header
permutations to find what's missing."""
import json
import logging
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from selenium.webdriver.common.by import By

from packages.browser import ChromeManager
from packages.browser.chrome_manager import ChromeManager as _CM
from packages.authentication import LoginManager
from packages.track_management import TrackManager
from packages.configuration.selectors import DOWNLOAD_BUTTON_SELECTORS

SONG_URL = ("https://www.karaoke-version.com/custombackingtrack/"
            "bryan-adams/18-til-i-die.html")

_orig_configure = _CM._configure_chrome_options
def _patched_configure(self):
    opts = _orig_configure(self)
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return opts
_CM._configure_chrome_options = _patched_configure


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        force=True)
    log = logging.getLogger("diag")

    chrome = ChromeManager(headless=False)
    chrome.setup_driver()
    chrome.setup_folders()
    driver = chrome.driver
    wait = chrome.wait
    driver.execute_cdp_cmd("Network.enable", {})

    try:
        login = LoginManager(driver, wait)
        if not login.login_with_session_persistence():
            return 2
        tm = TrackManager(driver, wait)
        tracks = tm.discover_tracks(SONG_URL)
        seed = next((t for t in tracks if str(t["index"]) == "1"), None)
        tm.ensure_intro_count_enabled(SONG_URL)
        tm.ensure_only_track_active(1, SONG_URL)
        tm.solo_track({"name": seed["name"], "index": 1}, SONG_URL)

        # Drain perf log, then trigger UI download to capture basket URL +
        # ALL its request headers (not just my filtered subset)
        list(driver.get_log("performance"))
        btn = None
        for sel in DOWNLOAD_BUTTON_SELECTORS:
            try:
                if sel.startswith("//"):
                    el = driver.find_element(By.XPATH, sel)
                else:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed() and el.is_enabled():
                    btn = el
                    break
            except Exception:
                continue
        driver.execute_script("arguments[0].click();", btn)
        log.info("clicked download in UI; waiting for basket.php capture")

        captured_url = None
        captured_headers = None
        deadline = time.time() + 20
        while time.time() < deadline and not captured_url:
            for entry in driver.get_log("performance"):
                try:
                    msg = json.loads(entry["message"])["message"]
                    if msg.get("method") == "Network.requestWillBeSent":
                        req = msg["params"]["request"]
                        if "basket.php" in req.get("url", ""):
                            captured_url = req["url"]
                            captured_headers = req.get("headers", {})
                            break
                except Exception:
                    continue
            time.sleep(0.2)

        if not captured_url:
            log.error("could not capture basket.php URL")
            return 1
        log.info(f"captured url ({len(captured_url)} chars)")
        log.info(f"captured headers: {json.dumps(captured_headers, indent=2)}")

        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        ua = driver.execute_script("return navigator.userAgent;")
    finally:
        chrome.quit()

    # Now replay through requests
    sess = requests.Session()
    for k, v in cookies.items():
        sess.cookies.set(k, v)

    log.info("=" * 70)
    log.info("Trial 1: bare GET, no extra headers")
    log.info("=" * 70)
    r = sess.get(captured_url, timeout=30)
    log.info(f"status={r.status_code}  len={len(r.text)}")
    log.info(f"headers received: {dict(r.headers)}")
    log.info(f"BODY:\n{r.text[:1500]}")

    log.info("=" * 70)
    log.info("Trial 2: with UA + Accept + Referer + X-Requested-With")
    log.info("=" * 70)
    headers = {
        "User-Agent": ua,
        "Accept": "*/*",
        "Referer": SONG_URL,
        "X-Requested-With": "XMLHttpRequest",
    }
    r = sess.get(captured_url, headers=headers, timeout=30)
    log.info(f"status={r.status_code}  len={len(r.text)}")
    log.info(f"BODY:\n{r.text[:1500]}")

    log.info("=" * 70)
    log.info("Trial 3: replay full captured headers verbatim")
    log.info("=" * 70)
    headers_full = dict(captured_headers)
    headers_full.setdefault("User-Agent", ua)
    r = sess.get(captured_url, headers=headers_full, timeout=30)
    log.info(f"status={r.status_code}  len={len(r.text)}")
    log.info(f"BODY:\n{r.text[:1500]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
