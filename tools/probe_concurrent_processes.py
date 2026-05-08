#!/usr/bin/env python3
"""
Tier 2 Phase 0 probe v3: TWO Chrome processes (Approach B from the plan)
running simultaneously, each downloading a different track from the same
song on the same Karaoke-Version.com account.

Why this exists: probe_concurrent_tabs.py confirmed the SERVER allows
concurrent mix generation from one account (both modal overlays opened in
parallel). What it could NOT confirm is end-to-end file delivery, because
Chrome's per-process download manager dropped one of the two same-named
files. Approach B isolates each worker in its own Chrome process with its
own download directory — which is what Tier 2 would actually ship.

Each worker uses a temporary user-data-dir (NOT the shared chrome_profile).
LoginManager reuses session cookies from .cache/session_data.pkl when
available, falling back to .env creds.

Run:
    python tools/probe_concurrent_processes.py
    python tools/probe_concurrent_processes.py --track-a 3 --track-b 7
"""

import argparse
import hashlib
import logging
import multiprocessing as mp
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "electric-light-orchestra/don-t-bring-me-down.html"
)
LOG_PATH = ROOT / "logs" / "probe_concurrent_processes.log"
DOWNLOAD_BASE = ROOT / "downloads" / "_probe_processes"


def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def worker(worker_id, song_url, track_index, profile_dir, download_dir,
           start_barrier, result_queue):
    """Run as a child process. Each child has its own Chrome + profile."""
    # Configure logging in the child (multiprocessing strips parent handlers).
    log_format = (
        f"%(asctime)s [W{worker_id}] [%(levelname)s] %(message)s"
    )
    logging.basicConfig(level=logging.INFO, format=log_format,
                        force=True, stream=sys.stdout)
    log = logging.getLogger(f"worker-{worker_id}")

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    from packages.authentication import LoginManager
    from packages.configuration.selectors import (
        DOWNLOAD_BUTTON_SELECTORS,
        DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR,
        TRACK_ELEMENT_SELECTOR,
    )

    result = {
        "worker_id": worker_id,
        "track_index": track_index,
        "track_name": "?",
        "modal_opened": False,
        "modal_ready": False,
        "modal_text_on_open": "",
        "files": [],
        "error": None,
        "click_ts": None,
        "modal_ts": None,
    }

    driver = None
    try:
        opts = Options()
        opts.add_argument(f"--user-data-dir={profile_dir}")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-extensions")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
            opts.binary_location = (
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            )
        opts.add_experimental_option("prefs", {
            "download.default_directory": str(Path(download_dir).resolve()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        })

        # Each worker uses its own debug port to avoid the chromedriver port
        # collision that ChromeManager hard-codes to 9515.
        driver_path = (
            "/opt/homebrew/bin/chromedriver"
            if os.path.exists("/opt/homebrew/bin/chromedriver")
            else None
        )
        if driver_path:
            service = Service(driver_path, port=9515 + worker_id)
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install(),
                              port=9515 + worker_id)

        driver = webdriver.Chrome(service=service, options=opts)
        wait = WebDriverWait(driver, 30)
        log.info(f"chrome up; profile={profile_dir} dl={download_dir}")

        # Login (uses session_data.pkl cookies if valid)
        login = LoginManager(driver, wait)
        if not login.login_with_session_persistence():
            raise RuntimeError("login failed")

        # Navigate
        driver.get(song_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.download"))
        )
        log.info("song page loaded")

        # Solo target track
        track_els = driver.find_elements(By.CSS_SELECTOR, TRACK_ELEMENT_SELECTOR)
        target = next(
            (el for el in track_els
             if el.get_attribute("data-index") == str(track_index)),
            None,
        )
        if not target:
            raise RuntimeError(f"no track with data-index={track_index}")
        try:
            caption = target.find_element(
                By.CSS_SELECTOR,
                ".track__caption, .custom__mixer-track-caption-name",
            )
            result["track_name"] = caption.text.strip() or "?"
        except Exception:
            pass
        solo_btn = target.find_element(By.CSS_SELECTOR, "button.track__solo")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});",
                              solo_btn)
        driver.execute_script("arguments[0].click();", solo_btn)
        log.info(f"soloed track {track_index} ('{result['track_name']}')")
        time.sleep(3)  # let solo settle

        # Synchronize across workers so the download click happens within ms
        log.info("ready — waiting at barrier")
        start_barrier.wait(timeout=120)

        # Click download
        download_btn = None
        for sel in DOWNLOAD_BUTTON_SELECTORS:
            try:
                if sel.startswith("//"):
                    el = driver.find_element(By.XPATH, sel)
                else:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed() and el.is_enabled():
                    download_btn = el
                    break
            except Exception:
                continue
        if not download_btn:
            raise RuntimeError("download button not found")
        click_ts = time.time()
        result["click_ts"] = click_ts
        driver.execute_script("arguments[0].click();", download_btn)
        log.info("clicked download")

        # Wait for modal overlay
        try:
            WebDriverWait(driver, 45).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR)
                )
            )
            result["modal_opened"] = True
            result["modal_ts"] = time.time()
            log.info(f"modal overlay opened (+{result['modal_ts'] - click_ts:.1f}s)")
            # Capture modal text immediately, before it changes
            try:
                contents = driver.find_elements(
                    By.CSS_SELECTOR, ".modal .modal__content"
                )
                grabbed = " | ".join(
                    (c.text or "").strip() for c in contents if (c.text or "").strip()
                )
                result["modal_text_on_open"] = grabbed[:500]
                log.info(f"modal text: {grabbed[:200]!r}")
            except Exception as e:
                log.warning(f"modal text capture failed: {e}")
        except Exception:
            log.warning("modal overlay did NOT open within 45s")

        # Wait for readiness text
        readiness_patterns = (
            "your download will begin",
            "you can also click on the link below",
            "click here to download",
            "download is ready",
        )

        def check_ready(_d):
            contents = _d.find_elements(By.CSS_SELECTOR, ".modal .modal__content")
            for c in contents:
                text = (c.text or "").lower()
                for pat in readiness_patterns:
                    if pat in text:
                        return True
            return False

        try:
            WebDriverWait(driver, 45, poll_frequency=0.5).until(check_ready)
            result["modal_ready"] = True
            log.info("modal readiness text detected")
        except Exception:
            log.warning("modal readiness text NOT seen")

        # Wait for the file
        deadline = time.time() + 120
        download_path = Path(download_dir)
        seen = set()
        while time.time() < deadline:
            files = [
                f for f in download_path.iterdir()
                if f.is_file() and not f.name.endswith(".crdownload")
            ]
            in_progress = list(download_path.glob("*.crdownload"))
            if files and not in_progress:
                seen = set(files)
                break
            time.sleep(2)

        for f in seen:
            try:
                result["files"].append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "sha256": hash_file(f),
                })
            except Exception as e:
                log.warning(f"hash error: {e}")
        log.info(f"finished — files={[f['name'] for f in result['files']]}")
    except Exception as e:
        log.exception(f"worker error: {e}")
        result["error"] = repr(e)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        result_queue.put(result)


def setup_logging():
    LOG_PATH.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [main] [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--song-url", default=DEFAULT_SONG_URL)
    parser.add_argument("--track-a", type=int, default=1)
    parser.add_argument("--track-b", type=int, default=2)
    parser.add_argument("--keep-profiles", action="store_true",
                        help="don't delete temp profile dirs after run")
    args = parser.parse_args()

    setup_logging()
    log = logging.getLogger("main")
    log.info("=" * 70)
    log.info("Tier 2 Phase 0 probe v3 — TWO Chrome processes (Approach B)")
    log.info(f"Song: {args.song_url}")
    log.info(f"Worker 0 track: {args.track_a}")
    log.info(f"Worker 1 track: {args.track_b}")
    log.info("=" * 70)

    DOWNLOAD_BASE.mkdir(parents=True, exist_ok=True)
    # Clean per-worker dirs
    w0_dir = DOWNLOAD_BASE / "w0"
    w1_dir = DOWNLOAD_BASE / "w1"
    for d in (w0_dir, w1_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    profile_root = Path(tempfile.mkdtemp(prefix="kv_probe_"))
    p0 = profile_root / "w0"
    p1 = profile_root / "w1"
    p0.mkdir()
    p1.mkdir()
    log.info(f"profile temp root: {profile_root}")

    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(2)
    queue = ctx.Queue()

    procs = [
        ctx.Process(
            target=worker,
            args=(0, args.song_url, args.track_a, str(p0), str(w0_dir),
                  barrier, queue),
        ),
        ctx.Process(
            target=worker,
            args=(1, args.song_url, args.track_b, str(p1), str(w1_dir),
                  barrier, queue),
        ),
    ]

    t0 = time.time()
    for p in procs:
        p.start()
    log.info("workers started; waiting for results")

    results = []
    for _ in procs:
        results.append(queue.get(timeout=600))
    for p in procs:
        p.join(timeout=10)
        if p.is_alive():
            p.terminate()

    elapsed = time.time() - t0
    log.info(f"workers complete in {elapsed:.1f}s")

    # Sort by worker_id for deterministic reporting
    results.sort(key=lambda r: r["worker_id"])

    log.info("=" * 70)
    log.info("RESULTS")
    log.info("=" * 70)
    for r in results:
        log.info(
            f"W{r['worker_id']}: track {r['track_index']} '{r['track_name']}' "
            f"modal={r['modal_opened']} ready={r['modal_ready']} "
            f"files={len(r['files'])} error={r['error']}"
        )
        if r["modal_text_on_open"]:
            log.info(f"  modal_text: {r['modal_text_on_open']!r}")
        for f in r["files"]:
            log.info(
                f"  - {f['name']}  {f['size']:,} bytes  sha256={f['sha256'][:16]}…"
            )

    if len(results) >= 2 and results[0]["click_ts"] and results[1]["click_ts"]:
        log.info(
            f"click time delta: "
            f"{abs(results[0]['click_ts'] - results[1]['click_ts']) * 1000:.0f} ms"
        )
    if all(r["modal_ts"] for r in results):
        log.info(
            f"modal-open delta: "
            f"{abs(results[0]['modal_ts'] - results[1]['modal_ts']) * 1000:.0f} ms"
        )

    all_hashes = [f["sha256"] for r in results for f in r["files"]]
    distinct = len(set(all_hashes)) == len(all_hashes) and len(all_hashes) >= 2
    all_files = all(len(r["files"]) >= 1 for r in results)
    all_modals = all(r["modal_opened"] for r in results)

    if all_modals and all_files and distinct:
        log.info("✅ APPROACH B CONFIRMED — N=2 concurrent processes work end-to-end.")
    else:
        reasons = []
        for r in results:
            if not r["modal_opened"]:
                reasons.append(f"W{r['worker_id']} modal didn't open")
            if not r["files"]:
                reasons.append(f"W{r['worker_id']} no file landed")
        if all_hashes and not distinct:
            reasons.append("workers got identical file content")
        log.warning("⚠️ ISSUE: " + "; ".join(reasons))

    if not args.keep_profiles:
        try:
            shutil.rmtree(profile_root)
            log.info(f"cleaned up profiles at {profile_root}")
        except Exception as e:
            log.warning(f"profile cleanup failed: {e}")
    else:
        log.info(f"keeping profiles at {profile_root}")


if __name__ == "__main__":
    main()
