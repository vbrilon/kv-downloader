#!/usr/bin/env python3
"""
Tier 2 Phase 0 probe v4: multi-tab + direct-URL fetch (Approach A).

Solves the filename-collision problem from probe v2 by extracting the actual
MP3 URL from each tab's "download ready" modal and fetching it via Python
``requests``, using session cookies copied from Selenium. Chrome's download
manager is taken out of the loop entirely.

If this works at N=2 cleanly, it scales naturally to N=5+ because:
  - The server has been shown to handle parallel mix-gen requests
    (probe_concurrent_tabs.py ran two in parallel, ~13s each).
  - Direct fetch bypasses Chrome's download manager, so filename collision
    and per-tab download-path quirks don't apply.
  - Sequential tab clicks (each ~100ms) mean 10 click-events fan out in ~1s.

Run:
    python tools/probe_direct_fetch.py
    python tools/probe_direct_fetch.py --tracks 0,1,2,3,4
"""

import argparse
import hashlib
import logging
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from packages.browser import ChromeManager
from packages.authentication import LoginManager
from packages.track_management import TrackManager
from packages.configuration.selectors import (
    DOWNLOAD_BUTTON_SELECTORS,
    DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR,
    TRACK_ELEMENT_SELECTOR,
)


SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "bryan-adams/18-til-i-die.html"
)
LOG_PATH = ROOT / "logs" / "probe_direct_fetch.log"
DOWNLOAD_DIR = ROOT / "downloads" / "_probe_direct_fetch"
CHROME_DROPPED_DIR = DOWNLOAD_DIR / "_chrome_auto"


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


def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def solo_track_via_track_manager(driver, wait, track_index, song_url):
    """Match production: discover_tracks → ensure_intro_count_enabled
    (forces mixer JS to bind by waiting on #precount and interacting with
    it) → ensure_only_track_active (does the click) → solo_track (verifies).
    Skipping ensure_intro_count_enabled means we click solo before the mixer
    is bound and the click is silently no-op'd."""
    tm = TrackManager(driver, wait)

    tracks = tm.discover_tracks(song_url)
    if not tracks:
        raise RuntimeError("no tracks discovered")
    target_info = next(
        (t for t in tracks if str(t["index"]) == str(track_index)),
        None,
    )
    if not target_info:
        raise RuntimeError(f"track {track_index} not in discovered list")
    name = target_info["name"]

    # Wait for the mixer panel to be fully bound (production's first setup step).
    if not tm.ensure_intro_count_enabled(song_url):
        logging.warning("ensure_intro_count_enabled returned False — proceeding")

    if not tm.ensure_only_track_active(track_index, song_url):
        raise RuntimeError(
            f"ensure_only_track_active failed for track {track_index}"
        )
    if not tm.solo_track({"name": name, "index": track_index}, song_url):
        raise RuntimeError(f"solo_track verify failed for track {track_index}")
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


def click_download(driver):
    btn = find_download_button(driver)
    if not btn:
        raise RuntimeError("download button not found")
    driver.execute_script("arguments[0].click();", btn)


def snapshot_state(driver, label):
    """Capture which solo buttons think they're active, plus key client state.
    Returns dict for logging."""
    # Active solos: find any solo button with 'is-active' / 'active' class or
    # aria-pressed='true'. Class names vary; check several signals.
    # Dump every solo button's state, NOT just ones that match my "active" heuristic
    actives = driver.execute_script(
        """
        const btns = document.querySelectorAll('button.track__solo');
        const out = [];
        btns.forEach(b => {
            const tr = b.closest('.track, .custom__mixer-track-line');
            const idx = tr ? tr.getAttribute('data-index') : null;
            out.push({
                idx: idx,
                classes: (b.className || ''),
                aria_pressed: b.getAttribute('aria-pressed') || '',
                data_state: b.getAttribute('data-state') || '',
            });
        });
        return out;
        """
    )
    # localStorage keys (just keys + value lengths to keep log light)
    ls_keys = driver.execute_script(
        """
        const out = [];
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            const v = localStorage.getItem(k) || '';
            out.push({key: k, len: v.length, head: v.slice(0, 60)});
        }
        return out;
        """
    )
    ss_keys = driver.execute_script(
        """
        const out = [];
        for (let i = 0; i < sessionStorage.length; i++) {
            const k = sessionStorage.key(i);
            const v = sessionStorage.getItem(k) || '';
            out.push({key: k, len: v.length, head: v.slice(0, 60)});
        }
        return out;
        """
    )
    return {"active_solos": actives, "localStorage": ls_keys, "sessionStorage": ss_keys}


def wait_modal_ready(driver, timeout=60):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR)
        )
    )
    patterns = (
        "your download will begin",
        "you can also click on the link below",
        "click here to download",
    )

    def check(_d):
        for c in _d.find_elements(By.CSS_SELECTOR, ".modal .modal__content"):
            t = (c.text or "").lower()
            for pat in patterns:
                if pat in t:
                    return True
        return False

    WebDriverWait(driver, timeout, poll_frequency=0.5).until(check)


def extract_mp3_url(driver):
    """Find the MP3 URL in the open modal. Returns (url, source) or (None, None)."""
    # 1) iframes
    for ifr in driver.find_elements(By.CSS_SELECTOR, ".modal iframe"):
        src = ifr.get_attribute("src") or ""
        low = src.lower()
        if any(k in low for k in (".mp3", "download", "mix", "media")):
            return src, "iframe"
    # 2) anchors with promising hrefs
    for a in driver.find_elements(By.CSS_SELECTOR, ".modal a"):
        href = a.get_attribute("href") or ""
        low = href.lower()
        if any(k in low for k in (".mp3", "download", "mix", "media")):
            return href, "anchor"
    # 3) regex sweep of modal HTML
    html = driver.find_element(By.CSS_SELECTOR, ".modal").get_attribute("outerHTML")
    m = re.search(r'https?://[^\s"\'<>]+\.mp3[^\s"\'<>]*', html, re.IGNORECASE)
    if m:
        return m.group(0), "regex_mp3"
    m = re.search(
        r'https?://[^\s"\'<>]*(?:download|getmix|mediafile|mix)[^\s"\'<>]+',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(0), "regex_keyword"
    return None, None


def fetch_with_cookies(url, cookies, dest, ua):
    headers = {
        "User-Agent": ua,
        "Referer": "https://www.karaoke-version.com/",
        "Accept": "*/*",
    }
    t0 = time.time()
    with requests.get(url, cookies=cookies, headers=headers, stream=True,
                      timeout=180, allow_redirects=True) as r:
        status = r.status_code
        ctype = r.headers.get("Content-Type", "")
        clen = r.headers.get("Content-Length")
        if status >= 400:
            body = r.text[:200] if r.text else ""
            raise RuntimeError(
                f"HTTP {status}; content-type={ctype}; body={body!r}"
            )
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    return {
        "size": dest.stat().st_size,
        "elapsed": time.time() - t0,
        "status": status,
        "content_type": ctype,
        "content_length": clen,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--song-url", default=SONG_URL)
    parser.add_argument("--tracks", default="1,2",
                        help="comma-separated track data-indices to fetch")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--solo-settle", type=float, default=2.5)
    parser.add_argument("--click-gap", type=float, default=0.0,
                        help="seconds to wait between successive tabs' "
                             "download clicks (0 = back-to-back)")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("probe")
    track_indices = [int(t) for t in args.tracks.split(",") if t.strip()]
    log.info("=" * 70)
    log.info("Tier 2 Phase 0 probe v4 — multi-tab + direct-URL fetch")
    log.info(f"Song:   {args.song_url}")
    log.info(f"Tracks: {track_indices}")
    log.info("=" * 70)

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CHROME_DROPPED_DIR.mkdir(parents=True, exist_ok=True)

    chrome = ChromeManager(headless=args.headless)
    chrome.setup_driver()
    chrome.setup_folders()
    driver = chrome.driver
    wait = chrome.wait

    # Redirect Chrome's auto-downloads to a side folder so we can see if and
    # what Chrome was about to fetch. Our authoritative outputs land in
    # DOWNLOAD_DIR via Python requests.
    chrome.set_download_path(str(CHROME_DROPPED_DIR.resolve()))

    rc = 1
    try:
        login = LoginManager(driver, wait)
        if not login.login_with_session_persistence():
            log.error("login failed")
            return 2

        # Open one tab per requested track and click download in each
        tabs = []
        for idx, tindex in enumerate(track_indices):
            if idx == 0:
                handle = driver.current_window_handle
            else:
                driver.switch_to.new_window("tab")
                handle = driver.current_window_handle
            # discover_tracks (via verify_song_access) handles navigation
            # AND waits for track elements — which is the right gate for
            # the mixer JS being bound, unlike "a.download" which appears
            # earlier in page-load and lets us click solo too soon.
            tname = solo_track_via_track_manager(driver, wait, tindex, args.song_url)
            log.info(
                f"[tab {idx}] handle={handle[:8]} solo'd track {tindex} "
                f"'{tname}' (via TrackManager)"
            )
            time.sleep(args.solo_settle)

            if idx > 0 and args.click_gap > 0:
                log.info(f"[tab {idx}] sleeping {args.click_gap}s before click")
                time.sleep(args.click_gap)

            state = snapshot_state(driver, f"tab{idx}")
            log.info(f"[tab {idx}] solo button state at click:")
            for b in state["active_solos"]:
                log.info(
                    f"  · idx={b['idx']} class='{b['classes']}' "
                    f"aria_pressed='{b['aria_pressed']}' "
                    f"data_state='{b['data_state']}'"
                )
            log.info(
                f"[tab {idx}]   localStorage keys: "
                f"{[k['key'] for k in state['localStorage']]}"
            )
            log.info(
                f"[tab {idx}]   sessionStorage keys: "
                f"{[k['key'] for k in state['sessionStorage']]}"
            )

            click_ts = time.time()
            click_download(driver)
            log.info(f"[tab {idx}] clicked download")
            tabs.append({
                "idx": idx, "handle": handle, "tindex": tindex,
                "tname": tname, "click_ts": click_ts,
                "state_at_click": state,
            })

        # Now wait for each tab's modal and extract the MP3 URL
        urls = []
        ua = driver.execute_script("return navigator.userAgent;")
        for t in tabs:
            driver.switch_to.window(t["handle"])
            try:
                wait_modal_ready(driver, timeout=60)
                t["modal_ts"] = time.time()
                log.info(
                    f"[tab {t['idx']}] modal ready "
                    f"(+{t['modal_ts'] - t['click_ts']:.1f}s)"
                )
            except Exception as e:
                log.warning(f"[tab {t['idx']}] modal not ready: {e}")
                continue
            url, src = extract_mp3_url(driver)
            if not url:
                html = driver.find_element(
                    By.CSS_SELECTOR, ".modal"
                ).get_attribute("outerHTML")
                log.warning(
                    f"[tab {t['idx']}] could not extract URL.\n"
                    f"  modal HTML head: {html[:600]!r}"
                )
                continue
            t["url"] = url
            t["url_source"] = src
            urls.append(t)
            log.info(f"[tab {t['idx']}] url[{src}]: {url[:140]}")

        if not urls:
            log.error("no URLs extracted — nothing to fetch")
            return 1

        # Snapshot cookies once (shared across all fetches)
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        log.info(f"snapshotted {len(cookies)} cookies for direct fetch")

        # Parallel fetch
        def safe(s):
            return re.sub(r"[^A-Za-z0-9._-]+", "_", s)

        log.info(f"fetching {len(urls)} URLs in parallel via requests...")
        t_fetch = time.time()
        results = []
        with ThreadPoolExecutor(max_workers=max(2, len(urls))) as ex:
            futs = {}
            for t in urls:
                dest = DOWNLOAD_DIR / (
                    f"track{t['tindex']:02d}_{safe(t['tname'])}.mp3"
                )
                futs[ex.submit(fetch_with_cookies, t["url"], cookies, dest, ua)] = (
                    t, dest
                )
            for fut in as_completed(futs):
                t, dest = futs[fut]
                try:
                    info = fut.result()
                    info.update({
                        "idx": t["idx"], "tindex": t["tindex"],
                        "tname": t["tname"], "dest": dest,
                        "sha256": hash_file(dest),
                    })
                    results.append(info)
                    log.info(
                        f"[tab {t['idx']}] fetched in {info['elapsed']:.1f}s "
                        f"({info['size']:,} bytes, ct={info['content_type']})"
                    )
                except Exception as e:
                    log.error(f"[tab {t['idx']}] fetch failed: {e}")
        wall = time.time() - t_fetch

        log.info("=" * 70)
        log.info(f"RESULTS — direct-fetch phase wall: {wall:.1f}s")
        log.info("=" * 70)
        for r in sorted(results, key=lambda r: r["idx"]):
            log.info(
                f"  - track {r['tindex']:>2} '{r['tname']}': "
                f"{r['dest'].name}  {r['size']:,} bytes  "
                f"sha256={r['sha256'][:16]}…  ct={r['content_type']}"
            )

        # Note any files Chrome auto-downloaded in parallel (informational)
        chrome_files = [
            f for f in CHROME_DROPPED_DIR.iterdir()
            if f.is_file() and not f.name.endswith(".crdownload")
        ]
        if chrome_files:
            log.info(f"Chrome auto-downloaded {len(chrome_files)} file(s) in parallel:")
            for f in chrome_files:
                log.info(f"  · {f.name} ({f.stat().st_size:,} bytes)")

        hashes = [r["sha256"] for r in results]
        distinct = len(set(hashes)) == len(hashes)
        if results and len(results) == len(urls) and distinct:
            log.info("✅ APPROACH A CONFIRMED — every track fetched, distinct content.")
            rc = 0
        elif results and not distinct:
            log.warning("⚠️ duplicate file content among fetches.")
        else:
            log.warning(f"⚠️ partial: {len(results)}/{len(urls)} fetches succeeded.")
        return rc
    finally:
        chrome.quit()


if __name__ == "__main__":
    sys.exit(main())
