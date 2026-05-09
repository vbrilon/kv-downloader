#!/usr/bin/env python3
"""Q1 final — dump the inline script that initializes mixer.parameters.

The mixer probe showed mixer.parameters has only {famid, method, precount}
at probe time. The other params (prodid, s, bkac, pannings, pitch) get
assigned inside `mixer.getMixCallback` which only fires when download is
clicked. But the literal values ARE in the inline script source — we just
need to scrape them statically.

This probe dumps the full script[7] source so we can see all
`mixer.parameters.X = Y` assignments and decide if static scraping covers
everything.
"""

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.browser import ChromeManager
from packages.authentication import LoginManager

DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "bryan-adams/18-til-i-die.html"
)
LOG_PATH = ROOT / "logs" / "probe_script_source.log"


def setup_logging():
    LOG_PATH.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


# Find every inline script that mentions 'mixer.' and dump it (with index).
PROBE_JS = r"""
const out = [];
const scripts = Array.from(document.querySelectorAll('script:not([src])'));
scripts.forEach((s, i) => {
  const src = s.textContent || '';
  if (src.includes('mixer.') || src.includes('Mixer(') ||
      src.includes('new Mixer') || src.includes('basket.php')) {
    out.push({idx: i, length: src.length, source: src});
  }
});
return out;
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--song-url", default=DEFAULT_SONG_URL)
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()

    setup_logging()
    log = logging.getLogger("script-probe")

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

        driver.get(args.song_url)
        # Tiny wait for any deferred init
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".track"))
        )

        scripts = driver.execute_script(PROBE_JS)
        log.info(f"Found {len(scripts)} inline scripts mentioning mixer/basket")
        for s in scripts:
            log.info(f"\n{'=' * 70}")
            log.info(f"SCRIPT[{s['idx']}] ({s['length']} chars):")
            log.info(f"{'=' * 70}")
            for line_num, line in enumerate(s["source"].split("\n"), 1):
                log.info(f"  L{line_num:>3}: {line.rstrip()}")

    finally:
        chrome.quit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
