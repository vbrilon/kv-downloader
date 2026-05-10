#!/usr/bin/env python3
"""For a given song, calls basket.php for each non-edge position in the
captured trackslevels template and reports the URL filename the server
returns. Useful for verifying the position-to-track mapping when the
behavior of a new song is in doubt.

Usage:
    bin/python tools/probe_track_mapping.py [--song-url URL]
"""
import argparse
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, unquote

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.browser import ChromeManager
from packages.authentication import LoginManager
from packages.track_management import TrackManager
from packages.download_management.direct_api.session_capture import capture_session
from packages.download_management.direct_api.trackslevels import parse_segments
from packages.download_management.direct_api.direct_downloader import (
    extract_mp3_url, url_hash,
)


DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "led-zeppelin/good-times-bad-times.html"
)
BASKET_URL = "https://www.karaoke-version.com/basket.php"
BEGIN_URL = "https://www.karaoke-version.com/my/begin_download.html"
_FILENAME_RE = re.compile(r"/([^/]+\.mp3)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--song-url", default=DEFAULT_SONG_URL)
    parser.add_argument("--no-headless", dest="headless",
                        action="store_false", default=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        force=True)
    log = logging.getLogger("probe")

    chrome = ChromeManager(headless=args.headless)
    chrome.setup_driver()
    chrome.setup_folders()
    driver = chrome.driver
    wait = chrome.wait

    template_params = None
    cookies = None
    ua = None
    tracks = None
    mixer_tracks = None
    try:
        login = LoginManager(driver, wait)
        if not login.login_with_session_persistence():
            return 2
        ctx = capture_session(driver, args.song_url)
        template_params = ctx.template_params
        cookies = ctx.cookies
        ua = ctx.ua
        mixer_tracks = ctx.mixer_tracks
        tm = TrackManager(driver, wait)
        tracks = tm.discover_tracks(args.song_url)
    finally:
        chrome.quit()

    log.info("DOM tracks (data-index → name):")
    for t in sorted(tracks, key=lambda x: int(x["index"])):
        log.info(f"  data-index={t['index']:>2} → {t['name']!r}")

    log.info(f"\nmixer.tracks ({len(mixer_tracks)} entries):")
    for mt in mixer_tracks:
        log.info(
            f"  index={mt.index:>2} src_id={mt.src_id:>2} "
            f"is_click={mt.is_click!s:>5}  desc={mt.description!r}"
        )

    sess = requests.Session()
    for k, v in cookies.items():
        sess.cookies.set(k, v)
    sess.headers.update({
        "User-Agent": ua or "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": args.song_url,
        "X-Requested-With": "XMLHttpRequest",
    })

    template = template_params["trackslevels"]
    segs = parse_segments(template)
    log.info(f"\ncaptured trackslevels template ({len(segs)} segments):")
    for pos, sid, lvl in segs:
        if sid is None:
            log.info(f"  pos={pos:>2}  bare={lvl!r}")
        else:
            log.info(f"  pos={pos:>2}  id={sid:>3}  level={lvl}")

    def begin():
        url = (
            f"{BEGIN_URL}?id={template_params['prodid']}"
            f"&famid={template_params.get('famid', '5')}"
            f"&produced=1&method=ajax"
        )
        return extract_mp3_url(sess.get(url, timeout=30).text)

    def call_basket_with_template_position(pos: int) -> str:
        """Build trackslevels by mutating the captured template (preserving
        bare flags and existing id labels)."""
        out = []
        for i, sid, raw in segs:
            if sid is None:
                out.append(raw)
            elif i == pos:
                out.append(f"100.{sid}")
            else:
                out.append(f"0.{sid}")
        levels = ",".join(out)
        params = dict(template_params)
        params["trackslevels"] = levels
        url = BASKET_URL + "?" + urlencode(params, safe=",.-")
        sess.get(url, timeout=30)
        return levels

    def poll_for_fresh(prev_hash, max_wait=60, interval=2.0):
        deadline = time.monotonic() + max_wait
        while True:
            url = begin()
            if url:
                h = url_hash(url)
                if h != prev_hash:
                    return url, h
            if time.monotonic() >= deadline:
                return None, None
            time.sleep(interval)

    snap_url = begin()
    last_hash = url_hash(snap_url) if snap_url else None
    log.info(f"\nbaseline url={snap_url!r} hash={last_hash}")

    dom_map = {int(t["index"]): t["name"] for t in tracks}
    results = []
    for pos in range(1, len(segs) - 1):
        if segs[pos][1] is None:
            continue
        levels = call_basket_with_template_position(pos)
        url, h = poll_for_fresh(last_hash)
        if url is None:
            log.warning(f"pos={pos}: TIMEOUT")
            results.append((pos, None))
            continue
        m = _FILENAME_RE.search(url)
        fname = unquote(m.group(1)) if m else None
        log.info(f"pos={pos:>2} → server filename: {fname!r}")
        results.append((pos, fname))
        last_hash = h

    print("\n=== SUMMARY ===")
    print(f"{'pos':>3}  {'server says':50}  {'expected: mixer.tracks[pos-1]':40}")
    print("-" * 100)
    for pos, fname in results:
        expected = (mixer_tracks[pos - 1].description
                    if 0 <= pos - 1 < len(mixer_tracks) else "?")
        print(f"{pos:>3}  {(fname or 'TIMEOUT'):50}  {expected:40}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
