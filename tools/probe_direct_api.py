#!/usr/bin/env python3
"""
Direct-API probe — tests whether parallelism on a single account is
achievable by bypassing the UI and calling karaoke-version.com's basket
and download endpoints directly.

Background: probe_network_capture.py revealed the download flow is two
HTTP calls:
  1. GET  /basket.php?...&trackslevels=...&pannings=...&prodid=PRODID
     — overwrites the server-side basket for this account+song.
  2. GET  /my/begin_download.html?id=PRODID&...
     — returns the modal HTML with the c*.recis.io MP3 URL once the mix
       is ready.

The earlier multi-tab probe collision happened because both tabs share
PRODID (account+song specific): tab 1's basket.php overwrote tab 0's
before either begin_download.html resolved.

This probe runs two tests:
  SEQUENTIAL — basket(A) → begin → URL_A, basket(B) → begin → URL_B.
    Confirms direct-API access works at all and produces distinct mixes
    when the basket changes between calls.
  RACE — basket(A) → start begin(A) in a thread, sleep 0.8s,
    basket(B) → start begin(B) in a thread, wait for both.
    The critical test: does begin_download.html capture the basket
    SYNCHRONOUSLY at request time (good — we get URL_A and URL_B as
    distinct mixes → parallelism is possible) or LAZILY at job-execution
    time (bad — both return URL_B → still blocked)?
"""

import argparse
import hashlib
import json
import logging
import re
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from selenium.webdriver.common.by import By

from packages.browser import ChromeManager
from packages.browser.chrome_manager import ChromeManager as _CM
from packages.authentication import LoginManager
from packages.track_management import TrackManager
from packages.configuration.selectors import DOWNLOAD_BUTTON_SELECTORS

DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "bryan-adams/18-til-i-die.html"
)
LOG_PATH = ROOT / "logs" / "probe_direct_api.log"
DOWNLOAD_DIR = ROOT / "downloads" / "_probe_direct_api"


# Enable Chrome perf logging so we can capture the basket.php URL the
# UI generates (so we don't have to reverse-engineer the param shape).
_orig_configure = _CM._configure_chrome_options


def _patched_configure(self):
    opts = _orig_configure(self)
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return opts


_CM._configure_chrome_options = _patched_configure


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
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


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


def grab_basket_url(driver, log, timeout=30):
    """Trigger one real download via the UI and capture the basket.php URL
    it generates."""
    list(driver.get_log("performance"))  # drain
    btn = find_download_button(driver)
    if not btn:
        raise RuntimeError("download button not found")
    driver.execute_script("arguments[0].click();", btn)
    log.info("clicked UI download to capture basket.php template")
    deadline = time.time() + timeout
    while time.time() < deadline:
        for entry in driver.get_log("performance"):
            try:
                msg = json.loads(entry["message"])["message"]
                if msg.get("method") == "Network.requestWillBeSent":
                    url = msg["params"]["request"]["url"]
                    if "basket.php" in url:
                        return url
            except Exception:
                continue
        time.sleep(0.3)
    raise RuntimeError(f"basket.php URL not captured within {timeout}s")


def parse_basket_params(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    return {k: v[0] for k, v in qs.items()}


def build_trackslevels(template, target_pos, level=100):
    """Take the captured trackslevels template and build a new one with
    only `target_pos` at `level`, all other `level.id` segments at 0.

    Bare-numeric segments (positions without a `.id` suffix, typically
    the leading and trailing slots) are preserved verbatim — they appear
    to encode site-level flags (e.g. precount), and changing them
    triggers HTTP 500 from basket.php (server-side consistency check)."""
    segments = template.split(",")
    out = []
    for i, seg in enumerate(segments):
        if "." in seg:
            _, id_part = seg.split(".", 1)
            out.append(f"{level if i == target_pos else 0}.{id_part}")
        else:
            out.append(seg)  # preserve as-is
    return ",".join(out)


def describe_segments(template):
    """Return a human-readable list of (position, id, level)."""
    out = []
    for i, seg in enumerate(template.split(",")):
        if "." in seg:
            lvl, sid = seg.split(".", 1)
            out.append((i, sid, lvl))
        else:
            out.append((i, "(none)", seg))
    return out


def call_basket(session, params, trackslevels):
    p = dict(params)
    p["trackslevels"] = trackslevels
    url = "https://www.karaoke-version.com/basket.php?" + urlencode(p, safe=",.-")
    return session.get(url, timeout=30)


def call_begin_download(session, params, timeout=180):
    url = (
        "https://www.karaoke-version.com/my/begin_download.html"
        f"?id={params['prodid']}&famid={params.get('famid', 5)}"
        f"&produced=1&method=ajax"
    )
    return session.get(url, timeout=timeout)


_MP3_URL_RE = re.compile(
    r'https?://c\d+\.recis\.io/sl/[^"\'<>\s]+\.mp3[^"\'<>\s]*',
    re.IGNORECASE,
)


def extract_mp3_url(html):
    m = _MP3_URL_RE.search(html or "")
    return m.group(0) if m else None


def begin_download_polling(session, params, log, label, timeout=120,
                           interval=2.0, watch_for_hash_change_from=None):
    """Poll begin_download.html until either:
    - we see a fresh MP3 URL whose hash differs from
      `watch_for_hash_change_from` (if provided), OR
    - we see ANY MP3 URL (if no hash filter), OR
    - timeout."""
    deadline = time.time() + timeout
    last_status = None
    last_body_excerpt = ""
    attempt = 0
    last_url = None
    while time.time() < deadline:
        attempt += 1
        t0 = time.time()
        r = call_begin_download(session, params, timeout=60)
        elapsed = time.time() - t0
        last_status = r.status_code
        last_body_excerpt = r.text[:200]
        url = extract_mp3_url(r.text)
        last_url = url or last_url
        url_hash = None
        if url:
            m = re.search(r"/sl/[^/]+/([a-f0-9]+)/", url)
            url_hash = m.group(1) if m else None
        log.info(
            f"[{label}] begin_download attempt {attempt}: "
            f"{r.status_code} in {elapsed:.1f}s, "
            f"body_len={len(r.text)}, mp3_url={'FOUND' if url else 'none'}, "
            f"hash={url_hash[:12] + '…' if url_hash else 'none'}"
        )
        if url:
            if watch_for_hash_change_from is None:
                return url, attempt, last_status
            if url_hash and url_hash != watch_for_hash_change_from:
                log.info(
                    f"[{label}] URL hash CHANGED "
                    f"({watch_for_hash_change_from[:12]}… → "
                    f"{url_hash[:12]}…)"
                )
                return url, attempt, last_status
        time.sleep(interval)
    log.warning(
        f"[{label}] timeout after {attempt} attempts. "
        f"last_url={last_url}  last_status={last_status}"
    )
    return last_url, attempt, last_status


def url_hash(url):
    m = re.search(r"/sl/[^/]+/([a-f0-9]+)/", url or "")
    return m.group(1) if m else None


def fetch_mp3(session, url, dest, log, label):
    headers = {
        "Referer": "https://www.karaoke-version.com/",
        "Accept": "*/*",
    }
    t0 = time.time()
    with session.get(url, headers=headers, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    elapsed = time.time() - t0
    size = dest.stat().st_size
    log.info(f"[{label}] fetched {size:,} bytes in {elapsed:.1f}s")
    return size, elapsed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--song-url", default=DEFAULT_SONG_URL)
    p.add_argument("--seed-track", type=int, default=1,
                   help="data-index of track to seed the UI mixer with "
                        "before grabbing the basket template")
    p.add_argument("--pos-a", type=int, default=2,
                   help="trackslevels position to set to level=100 in test A")
    p.add_argument("--pos-b", type=int, default=3,
                   help="trackslevels position to set to level=100 in test B")
    p.add_argument("--mode", choices=["sequential", "race", "both"],
                   default="both")
    p.add_argument("--race-gap", type=float, default=0.8,
                   help="seconds between basket-A+begin-A and basket-B+begin-B")
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()

    setup_logging()
    log = logging.getLogger("probe")
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    log.info("=" * 70)
    log.info("Direct-API probe: basket.php / begin_download.html parallelism")
    log.info(f"Song: {args.song_url}")
    log.info(f"Mode: {args.mode}; pos_a={args.pos_a} pos_b={args.pos_b}")
    log.info("=" * 70)

    chrome = ChromeManager(headless=args.headless)
    chrome.setup_driver()
    chrome.setup_folders()
    driver = chrome.driver
    wait = chrome.wait
    driver.execute_cdp_cmd("Network.enable", {})

    cookies = None
    template_params = None
    ua = None
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
        log.info(f"discovered {len(tracks)} tracks")
        seed = next(
            (t for t in tracks if str(t["index"]) == str(args.seed_track)),
            None,
        )
        if not seed:
            log.error(f"seed track {args.seed_track} not found")
            return 1

        tm.ensure_intro_count_enabled(args.song_url)
        tm.ensure_only_track_active(args.seed_track, args.song_url)
        tm.solo_track(
            {"name": seed["name"], "index": args.seed_track},
            args.song_url,
        )
        log.info(f"seeded mixer: track {args.seed_track} '{seed['name']}'")

        basket_url = grab_basket_url(driver, log)
        log.info(f"captured basket URL ({len(basket_url)} chars)")
        template_params = parse_basket_params(basket_url)
        log.info("basket params keys: " + ", ".join(template_params.keys()))
        log.info(f"  trackslevels: {template_params.get('trackslevels')}")
        log.info(f"  pannings:     {template_params.get('pannings')}")
        log.info(f"  prodid:       {template_params.get('prodid')}")
        log.info(f"  s (song id):  {template_params.get('s')}")
        log.info(f"  pitch:        {template_params.get('pitch')}")
        log.info(f"  bkac:         {template_params.get('bkac')}")
        log.info("trackslevels segment breakdown:")
        for pos, sid, lvl in describe_segments(template_params["trackslevels"]):
            marker = "  ← seeded" if lvl == "100" else ""
            log.info(f"  pos={pos:>2} id={sid:>3} level={lvl}{marker}")

        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        ua = driver.execute_script("return navigator.userAgent;")
        log.info(f"snapshotted {len(cookies)} cookies")
    finally:
        chrome.quit()

    if not template_params or not cookies:
        log.error("missing prerequisites; aborting")
        return 1

    session = requests.Session()
    for k, v in cookies.items():
        session.cookies.set(k, v)
    session.headers.update({
        "User-Agent": ua,
        "Accept": "*/*",
        "Referer": args.song_url,
        "X-Requested-With": "XMLHttpRequest",
    })

    template_levels = template_params["trackslevels"]
    rc = 0

    if args.mode in ("sequential", "both"):
        log.info("=" * 70)
        log.info("SEQUENTIAL TEST — does basket.php trigger regeneration?")
        log.info("=" * 70)

        # First call: A (same as seed). Should return cached URL.
        levels_a = build_trackslevels(template_levels, args.pos_a, level=100)
        log.info(f"[seq-A] basket levels: {levels_a}")
        bk_a = call_basket(session, template_params, levels_a)
        log.info(f"[seq-A] basket.php → {bk_a.status_code} "
                 f"({len(bk_a.text)} bytes)")
        url_a, _, _ = begin_download_polling(
            session, template_params, log, "seq-A"
        )
        seed_hash = url_hash(url_a)
        log.info(f"[seq-A] url={url_a}  hash={seed_hash}")

        # Second call: B (different basket). Watch for hash change.
        levels_b = build_trackslevels(template_levels, args.pos_b, level=100)
        log.info(f"[seq-B] basket levels: {levels_b}")
        bk_b = call_basket(session, template_params, levels_b)
        log.info(f"[seq-B] basket.php → {bk_b.status_code} "
                 f"({len(bk_b.text)} bytes)")
        # Critical: poll up to 60s, watching for the hash to change.
        # If hash changes → basket.php IS triggering server-side regen
        #   asynchronously → we just need to wait.
        # If hash never changes → basket.php is not actually triggering
        #   regeneration; some other endpoint is needed.
        url_b, attempts_b, _ = begin_download_polling(
            session, template_params, log, "seq-B",
            timeout=60, interval=3.0,
            watch_for_hash_change_from=seed_hash,
        )
        new_hash = url_hash(url_b)
        log.info(f"[seq-B] final url={url_b}  hash={new_hash}")
        log.info(f"[seq-B] hash changed: {new_hash != seed_hash} "
                 f"({attempts_b} polls)")

        if url_a and url_b:
            dest_a = DOWNLOAD_DIR / "seq_A.mp3"
            dest_b = DOWNLOAD_DIR / "seq_B.mp3"
            fetch_mp3(session, url_a, dest_a, log, "seq-A")
            fetch_mp3(session, url_b, dest_b, log, "seq-B")
            ha, hb = hash_file(dest_a), hash_file(dest_b)
            log.info(f"  A sha256: {ha[:16]}…")
            log.info(f"  B sha256: {hb[:16]}…")
            if ha != hb:
                log.info(
                    "✅ SEQUENTIAL test PASSED — direct API produces distinct "
                    "mixes. Direct-API workflow is viable."
                )
            else:
                log.warning(
                    "⚠ Different URLs (or same), but IDENTICAL content. "
                    "basket.php → begin_download.html alone does NOT trigger "
                    "server-side regeneration. Some other call (likely "
                    "internal to mixer JS) is needed. Investigate further."
                )
                rc = 1
        else:
            log.error("could not extract URLs from begin_download responses")
            rc = 1

    if args.mode in ("race", "both"):
        log.info("=" * 70)
        log.info("RACE TEST — does basket.php(B) cancel basket.php(A)'s "
                 "in-progress mix-gen, or does the server queue/parallelize?")
        log.info("=" * 70)

        # Snapshot current state so we know what the "old" hash is
        bd0 = call_begin_download(session, template_params)
        prev_url = extract_mp3_url(bd0.text)
        prev_hash = url_hash(prev_url)
        log.info(f"pre-race hash: {prev_hash[:12]}…  url={prev_url}")

        # Fire BOTH basket.php calls in quick succession
        levels_a = build_trackslevels(template_levels, args.pos_a, level=100)
        levels_b = build_trackslevels(template_levels, args.pos_b, level=100)

        ta = time.time()
        bk_a = call_basket(session, template_params, levels_a)
        log.info(f"  basket.php(A: pos {args.pos_a}) → {bk_a.status_code} "
                 f"in {time.time()-ta:.2f}s")
        time.sleep(args.race_gap)
        tb = time.time()
        bk_b = call_basket(session, template_params, levels_b)
        log.info(f"  basket.php(B: pos {args.pos_b}) → {bk_b.status_code} "
                 f"in {time.time()-tb:.2f}s")
        log.info(f"both baskets fired (gap={args.race_gap}s); "
                 f"now polling begin_download.html for hash changes...")

        # Poll begin_download.html and watch for hash changes. Record EVERY
        # distinct hash we see, with timestamps.
        observed = []  # list of (timestamp, hash, filename)
        seen_hashes = set()
        if prev_hash:
            seen_hashes.add(prev_hash)
        deadline = time.time() + 60
        t_start = time.time()
        while time.time() < deadline:
            r = call_begin_download(session, template_params, timeout=30)
            url = extract_mp3_url(r.text)
            h = url_hash(url) if url else None
            if h and h not in seen_hashes:
                seen_hashes.add(h)
                fname_match = re.search(r"/([^/]+\.mp3)", url or "")
                fname = fname_match.group(1) if fname_match else "?"
                observed.append((time.time() - t_start, h, fname, url))
                log.info(f"  [+{time.time()-t_start:>5.1f}s] NEW hash "
                         f"{h[:12]}…  filename={fname}")
                # Stop once we've seen 2 new hashes (or just 1 over 25s)
                if len(observed) >= 2:
                    break
            time.sleep(2.0)

        log.info(f"observed {len(observed)} distinct new hash(es) over "
                 f"{time.time() - t_start:.1f}s of polling")
        for t, h, fname, _ in observed:
            log.info(f"  · t=+{t:.1f}s  hash={h[:12]}…  {fname}")

        # Verify by fetching what we found
        fetched = []
        for i, (_, _, fname, url) in enumerate(observed):
            dest = DOWNLOAD_DIR / f"race_{i}_{fname}"
            try:
                size, _ = fetch_mp3(session, url, dest, log, f"race-#{i}")
                fetched.append((fname, hash_file(dest), size))
            except Exception as e:
                log.warning(f"could not fetch {url}: {e}")
        for fname, h, size in fetched:
            log.info(f"  fetched {fname}  sha256={h[:16]}…  size={size:,}")

        if len(observed) >= 2:
            log.info(
                "✅ RACE PRODUCED ≥2 DISTINCT MIXES. Server queues/processes "
                "both basket changes — basket.php(B) does NOT cancel A's "
                "mix-gen. Parallel single-account downloads are POSSIBLE "
                "via fire-multiple-baskets-then-collect-URLs pattern."
            )
            # Quick sanity: verify the filenames correspond to A and B
            names = [f for f, _, _ in fetched]
            log.info(f"  filenames: {names}")
        elif len(observed) == 1:
            fname = observed[0][2]
            log.warning(
                f"⚠ Only ONE new hash appeared after both basket changes. "
                f"Filename: {fname}. Likely the server CANCELLED basket A's "
                f"mix-gen when basket B arrived (last-write-wins on "
                f"in-progress jobs). Parallelism via this approach is BLOCKED."
            )
            rc = 1
        else:
            log.warning("⚠ NO new hashes observed within 60s.")
            rc = 1

    return rc


if __name__ == "__main__":
    sys.exit(main())
