#!/usr/bin/env python3
"""Q1 confirmation — verify window.mixer holds every basket.php param.

The deep probe found:
  mixer.parameters.bkac = "editf"
  mixer.setPannings("1,0.2,0.3,...,-100.12,0.13,0")

So `window.mixer` is the live JS object the page uses to build basket.php
URLs. This probe dumps:
  - mixer.parameters (the full dict)
  - mixer.pannings (or whatever holds the result of setPannings)
  - mixer.tracks (per-track state including levels)

If mixer.parameters has {prodid, s, bkac, famid, method, pitch, precount}
and we can derive pannings + a trackslevels template from mixer state,
we can build the basket URL with zero UI clicks.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.browser import ChromeManager
from packages.authentication import LoginManager
from packages.track_management import TrackManager

DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "bryan-adams/18-til-i-die.html"
)
LOG_PATH = ROOT / "logs" / "probe_mixer_state.log"


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


PROBE_JS = r"""
const out = {parameters: null, pannings: null, tracks_summary: [],
             top_keys: [], errors: []};
try {
  if (!window.mixer) {
    out.errors.push('window.mixer not defined');
    return out;
  }
  out.top_keys = Object.keys(window.mixer);

  // 1. mixer.parameters (the basket-template dict, hopefully)
  if (window.mixer.parameters) {
    try { out.parameters = JSON.parse(JSON.stringify(window.mixer.parameters)); }
    catch (e) {
      // can't JSON-clone (cycles?) — list keys + values
      const p = {};
      for (const k of Object.keys(window.mixer.parameters)) {
        try { p[k] = String(window.mixer.parameters[k]).slice(0, 300); }
        catch (e2) { p[k] = '[unserializable]'; }
      }
      out.parameters = p;
    }
  }

  // 2. pannings — could be stored as mixer.pannings or computed
  const panningCandidates = ['pannings', 'panning', 'pans'];
  for (const k of panningCandidates) {
    if (window.mixer[k] !== undefined) {
      out.pannings = {key: k, value: String(window.mixer[k]).slice(0, 500)};
      break;
    }
    if (window.mixer.parameters && window.mixer.parameters[k] !== undefined) {
      out.pannings = {key: 'parameters.' + k,
                      value: String(window.mixer.parameters[k]).slice(0, 500)};
      break;
    }
  }
  // Also try invoking getPannings if it exists
  if (typeof window.mixer.getPannings === 'function') {
    try { out.pannings_from_getter = window.mixer.getPannings(); }
    catch (e) { out.errors.push('getPannings(): ' + e.message); }
  }

  // 3. tracks
  if (Array.isArray(window.mixer.tracks)) {
    window.mixer.tracks.forEach((t, i) => {
      const summary = {idx: i};
      ['id', 'level', 'volume', 'pan', 'panning', 'name',
       'trackslevels_id', 'data_index'].forEach(k => {
        if (t && t[k] !== undefined) summary[k] = String(t[k]).slice(0, 100);
      });
      summary.keys = t ? Object.keys(t).slice(0, 30) : [];
      out.tracks_summary.push(summary);
    });
  }

  // 4. Methods we might want to call
  const methods = [];
  for (const k of Object.getOwnPropertyNames(
       Object.getPrototypeOf(window.mixer) || window.mixer)) {
    if (typeof window.mixer[k] === 'function') methods.push(k);
  }
  for (const k of out.top_keys) {
    if (typeof window.mixer[k] === 'function' && !methods.includes(k))
      methods.push(k);
  }
  out.methods = methods;

} catch (e) {
  out.errors.push('top-level: ' + e.message);
}
return out;
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--song-url", default=DEFAULT_SONG_URL)
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()

    setup_logging()
    log = logging.getLogger("mixer-probe")

    log.info("=" * 70)
    log.info("Q1 confirmation: dump window.mixer state")
    log.info(f"Song: {args.song_url}")
    log.info("=" * 70)

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
        log.info(f"discovered {len(tracks)} tracks")

        # Pristine read
        log.info("-" * 70)
        log.info("Pass A: pristine page (just navigated)")
        log.info("-" * 70)
        pristine = driver.execute_script(PROBE_JS)
        report(log, pristine, "pristine")

        # After soloing one track + intro count
        log.info("-" * 70)
        log.info("Pass B: after soloing track 1 + intro count")
        log.info("-" * 70)
        if tracks:
            tm.ensure_intro_count_enabled(args.song_url)
            tm.ensure_only_track_active(1, args.song_url)
            seed = next((t for t in tracks if str(t["index"]) == "1"), None)
            if seed:
                tm.solo_track({"name": seed["name"], "index": 1}, args.song_url)
        seeded = driver.execute_script(PROBE_JS)
        report(log, seeded, "seeded")

        # Compare parameters dicts
        log.info("-" * 70)
        log.info("Diff: parameters that changed between pristine and seeded")
        log.info("-" * 70)
        a, b = pristine.get("parameters") or {}, seeded.get("parameters") or {}
        all_keys = set(a) | set(b)
        for k in sorted(all_keys):
            va, vb = a.get(k), b.get(k)
            if va != vb:
                log.info(f"  {k}: {va!r} → {vb!r}")

        # Save full dumps
        json_path = LOG_PATH.with_suffix(".json")
        json_path.write_text(json.dumps(
            {"pristine": pristine, "seeded": seeded}, indent=2))
        log.info(f"full dump → {json_path}")

    finally:
        chrome.quit()

    return 0


def report(log, snap, label):
    if snap.get("errors"):
        for e in snap["errors"]:
            log.warning(f"[{label}] error: {e}")
    log.info(f"[{label}] window.mixer top-level keys: {snap['top_keys']}")
    log.info(f"[{label}] mixer.parameters: {snap.get('parameters')}")
    log.info(f"[{label}] mixer.pannings: {snap.get('pannings')}")
    if "pannings_from_getter" in snap:
        log.info(f"[{label}] mixer.getPannings(): {snap['pannings_from_getter']!r}")
    log.info(f"[{label}] mixer.tracks ({len(snap['tracks_summary'])} entries):")
    for ts in snap["tracks_summary"][:5]:
        log.info(f"    track[{ts.get('idx')}]: {ts}")
    if len(snap["tracks_summary"]) > 5:
        log.info(f"    ... and {len(snap['tracks_summary']) - 5} more")
    log.info(f"[{label}] mixer methods: {snap.get('methods', [])[:30]}")


if __name__ == "__main__":
    sys.exit(main())
