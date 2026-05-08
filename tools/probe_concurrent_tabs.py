#!/usr/bin/env python3
"""
Tier 2 Phase 0 probe: can two tabs in the same Chrome session concurrently
download different tracks from the same Karaoke-Version.com song?

The worry being validated: does the site's *session/account* state get
confused when two simultaneous download requests are in flight from the same
logged-in user? Multi-tab single-Chrome is the most conservative test — if
this works, the multi-process Approach B from the Tier 2 plan will also work.

What this script does:
  1. Boots one Chrome via the existing ChromeManager (reuses chrome_profile).
  2. Logs in via LoginManager.
  3. Loads the song page in tab A and a NEW tab B.
  4. Solos a different track in each tab.
  5. Fires both download clicks within ~1 second.
  6. Waits for the readiness modal in each tab.
  7. Waits for files to land in a dedicated probe folder, snapshots them,
     hashes contents — distinct hashes confirm the server didn't serve the
     same mix to both requests (which would indicate session confusion).

Run:
    python tools/probe_concurrent_tabs.py
    python tools/probe_concurrent_tabs.py --track-a 2 --track-b 5
"""

import argparse
import hashlib
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from packages.browser import ChromeManager
from packages.authentication import LoginManager
from packages.configuration.selectors import (
    DOWNLOAD_BUTTON_SELECTORS,
    DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR,
    TRACK_ELEMENT_SELECTOR,
)

DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "electric-light-orchestra/don-t-bring-me-down.html"
)
LOG_PATH = ROOT / "logs" / "probe_concurrent_tabs.log"
DOWNLOAD_DIR = ROOT / "downloads" / "_probe_concurrent"


def setup_logging():
    LOG_PATH.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def find_track_element(driver, track_index):
    track_els = driver.find_elements(By.CSS_SELECTOR, TRACK_ELEMENT_SELECTOR)
    for el in track_els:
        if el.get_attribute("data-index") == str(track_index):
            return el
    return None


def get_track_name(track_el):
    try:
        caption = track_el.find_element(
            By.CSS_SELECTOR, ".track__caption, .custom__mixer-track-caption-name"
        )
        return caption.text.strip()
    except Exception:
        return "(unknown)"


def solo_track(driver, track_index, label):
    track_el = find_track_element(driver, track_index)
    if not track_el:
        raise RuntimeError(f"[{label}] No track with data-index={track_index}")
    name = get_track_name(track_el)
    solo_btn = track_el.find_element(By.CSS_SELECTOR, "button.track__solo")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", solo_btn)
    driver.execute_script("arguments[0].click();", solo_btn)
    logging.info(f"[{label}] Soloed track {track_index} ('{name}')")
    return name


def find_download_button(driver):
    for sel in DOWNLOAD_BUTTON_SELECTORS:
        try:
            if sel.startswith("//"):
                el = driver.find_element(By.XPATH, sel)
            else:
                el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed() and el.is_enabled():
                return el
        except Exception:
            continue
    return None


def click_download(driver, label):
    btn = find_download_button(driver)
    if not btn:
        raise RuntimeError(f"[{label}] No download button visible")
    driver.execute_script("arguments[0].click();", btn)
    logging.info(f"[{label}] Clicked download")


def wait_for_modal(driver, label, timeout=45):
    """Wait for both modal overlay open AND readiness text. Returns
    (overlay_ok, ready_text_ok, captured_text)."""
    overlay_ok = False
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR)
            )
        )
        overlay_ok = True
        logging.info(f"[{label}] Modal overlay opened (server mix done)")
    except Exception:
        logging.warning(f"[{label}] Modal overlay did NOT open within {timeout}s")
        return False, False, ""

    readiness_patterns = (
        "you can also click on the link below to manually begin your download",
        "your download will begin in a moment",
        "download will begin",
        "download is ready",
        "click here to download",
    )
    ready_ok = False
    captured = ""

    def check_ready(_d):
        nonlocal captured
        contents = _d.find_elements(By.CSS_SELECTOR, ".modal .modal__content")
        for c in contents:
            text = (c.text or "").strip()
            if not text:
                continue
            captured = text
            low = text.lower()
            for pat in readiness_patterns:
                if pat in low:
                    return True
        return False

    try:
        WebDriverWait(driver, timeout, poll_frequency=0.5).until(check_ready)
        ready_ok = True
        logging.info(f"[{label}] Modal readiness text detected")
    except Exception:
        logging.warning(f"[{label}] Modal readiness text NOT seen within {timeout}s")

    return overlay_ok, ready_ok, captured


def snapshot_files(folder):
    folder = Path(folder)
    if not folder.exists():
        return {}
    return {
        f.name: f.stat().st_size
        for f in folder.iterdir()
        if f.is_file() and not f.name.endswith(".crdownload")
    }


def hash_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def wait_for_n_completed(folder, baseline, n, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        cur = snapshot_files(folder)
        new = {k: v for k, v in cur.items() if k not in baseline}
        # Also exclude any in-progress
        in_progress = list(Path(folder).glob("*.crdownload"))
        if len(new) >= n and not in_progress:
            return new
        time.sleep(2)
    cur = snapshot_files(folder)
    return {k: v for k, v in cur.items() if k not in baseline}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--song-url", default=DEFAULT_SONG_URL)
    parser.add_argument("--track-a", type=int, default=1,
                        help="data-index of track to solo in tab A")
    parser.add_argument("--track-b", type=int, default=2,
                        help="data-index of track to solo in tab B")
    parser.add_argument("--headless", action="store_true",
                        help="run Chrome headless")
    parser.add_argument("--solo-settle", type=float, default=3.0,
                        help="seconds to wait after each solo click")
    parser.add_argument("--file-timeout", type=int, default=120,
                        help="max seconds to wait for both files to land")
    args = parser.parse_args()

    setup_logging()
    logging.info("=" * 70)
    logging.info("Tier 2 Phase 0 probe — concurrent tabs, single account")
    logging.info(f"Song: {args.song_url}")
    logging.info(f"Tab A track index: {args.track_a}")
    logging.info(f"Tab B track index: {args.track_b}")
    logging.info(f"Headless: {args.headless}")
    logging.info("=" * 70)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    tab_a_dir = DOWNLOAD_DIR / "tab_a"
    tab_b_dir = DOWNLOAD_DIR / "tab_b"
    tab_a_dir.mkdir(exist_ok=True)
    tab_b_dir.mkdir(exist_ok=True)

    chrome = ChromeManager(headless=args.headless)
    chrome.setup_driver()
    chrome.setup_folders()
    driver = chrome.driver
    wait = chrome.wait

    success = False
    try:
        login = LoginManager(driver, wait)
        if not login.login_with_session_persistence():
            logging.error("Login failed — aborting probe.")
            return 2

        baseline_a = snapshot_files(tab_a_dir)
        baseline_b = snapshot_files(tab_b_dir)
        logging.info(f"Baseline files: tab_a={len(baseline_a)} tab_b={len(baseline_b)}")

        # Tab A — existing window
        tab_a = driver.current_window_handle
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(tab_a_dir.resolve()),
        })
        logging.info(f"[A] Per-tab download path -> {tab_a_dir}")
        driver.get(args.song_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.download"))
        )
        logging.info(f"[A] Loaded song page (handle={tab_a})")

        # Tab B — open new tab, set its download path, navigate to same URL
        driver.switch_to.new_window("tab")
        tab_b = driver.current_window_handle
        driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(tab_b_dir.resolve()),
        })
        logging.info(f"[B] Per-tab download path -> {tab_b_dir}")
        driver.get(args.song_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.download"))
        )
        logging.info(f"[B] Loaded song page (handle={tab_b})")

        # Solo in tab A
        driver.switch_to.window(tab_a)
        name_a = solo_track(driver, args.track_a, "A")
        time.sleep(args.solo_settle)

        # Solo in tab B
        driver.switch_to.window(tab_b)
        name_b = solo_track(driver, args.track_b, "B")
        time.sleep(args.solo_settle)

        # Fire downloads back-to-back
        driver.switch_to.window(tab_a)
        t0 = time.time()
        click_download(driver, "A")
        driver.switch_to.window(tab_b)
        click_download(driver, "B")
        t1 = time.time()
        logging.info(
            f"Both download clicks fired (delta {(t1 - t0) * 1000:.0f} ms)"
        )

        # Wait for the readiness modals
        driver.switch_to.window(tab_a)
        a_overlay, a_ready, a_text = wait_for_modal(driver, "A")
        driver.switch_to.window(tab_b)
        b_overlay, b_ready, b_text = wait_for_modal(driver, "B")

        # Wait for files in PER-TAB folders (avoids filename collision)
        logging.info(f"Waiting up to {args.file_timeout}s for files in each tab folder...")
        deadline = time.time() + args.file_timeout
        new_a, new_b = {}, {}
        while time.time() < deadline:
            cur_a = snapshot_files(tab_a_dir)
            cur_b = snapshot_files(tab_b_dir)
            new_a = {k: v for k, v in cur_a.items() if k not in baseline_a}
            new_b = {k: v for k, v in cur_b.items() if k not in baseline_b}
            in_progress = (
                list(tab_a_dir.glob("*.crdownload"))
                + list(tab_b_dir.glob("*.crdownload"))
            )
            if new_a and new_b and not in_progress:
                break
            time.sleep(2)

        # Hash all landed files
        all_files = []
        for folder, files in [(tab_a_dir, new_a), (tab_b_dir, new_b)]:
            for fname, size in files.items():
                path = folder / fname
                try:
                    h = hash_file(path)
                except Exception as e:
                    logging.warning(f"Could not hash {path}: {e}")
                    h = ""
                all_files.append((folder.name, fname, size, h))

        # Report
        logging.info("=" * 70)
        logging.info("RESULTS")
        logging.info("=" * 70)
        logging.info(
            f"Tab A: track='{name_a}'  overlay={a_overlay}  ready_text={a_ready}"
        )
        if a_text:
            logging.info(f"  modal_text[A]: {a_text[:140]!r}")
        logging.info(
            f"Tab B: track='{name_b}'  overlay={b_overlay}  ready_text={b_ready}"
        )
        if b_text:
            logging.info(f"  modal_text[B]: {b_text[:140]!r}")
        logging.info(f"Files in tab_a/: {len(new_a)}; tab_b/: {len(new_b)}")
        for folder_name, fname, size, h in sorted(all_files):
            logging.info(
                f"  - {folder_name}/{fname}  ({size:,} bytes)  sha256={h[:16]}…"
            )

        a_landed = len(new_a) >= 1
        b_landed = len(new_b) >= 1
        hashes = [h for _, _, _, h in all_files if h]
        distinct = len(set(hashes)) == len(hashes) and len(hashes) >= 2
        if a_overlay and b_overlay and a_landed and b_landed and distinct:
            logging.info(
                "✅ CONCURRENCY CONFIRMED at N=2 — both tabs delivered distinct files."
            )
            success = True
        else:
            reasons = []
            if not a_overlay:
                reasons.append("tab A modal overlay never opened")
            if not b_overlay:
                reasons.append("tab B modal overlay never opened")
            if not a_landed:
                reasons.append("no file landed in tab_a/")
            if not b_landed:
                reasons.append("no file landed in tab_b/")
            if hashes and not distinct:
                reasons.append("delivered files have identical content (session confusion?)")
            logging.warning("⚠️ CONCURRENCY ISSUE: " + "; ".join(reasons))

            # Diagnostic page-source scan in each tab
            for label, h in [("A", tab_a), ("B", tab_b)]:
                driver.switch_to.window(h)
                page = driver.page_source.lower()
                for marker in (
                    "captcha", "rate limit", "still processing",
                    "too many", "denied", "error", "robot",
                ):
                    if marker in page:
                        logging.warning(f"[{label}] page contains '{marker}'")
    finally:
        if not args.headless:
            time.sleep(3)
        chrome.quit()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
