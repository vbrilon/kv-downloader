#!/usr/bin/env python3
"""Q1 probe — can we scrape every basket.php param from the song-page DOM
without triggering a UI download click?

Background: probe_direct_api.py captured the basket.php URL by clicking the
UI download button and watching Chrome's perf log. That works but costs
~14s/song (the click triggers a real mix-gen + download). If the same
params live in the page DOM, capture_session becomes a near-instant read.

Target params (from probe_direct_api capture):
  prodid, s, pannings, pitch, precount, bkac, famid, method, trackslevels

For each one we look in:
  1. hidden <input> fields anywhere in the document
  2. data-* attributes on .track, .mixer, body, html, [class*=mixer]
  3. JS globals reachable via window.<param>
  4. inline <script> source — regex search for `<param>\\s*[:=]\\s*"..."`
  5. <meta> tags
  6. URL query params on the song page itself

Run: tools/probe_dom_scrape.py [--headless]
Output: logs/probe_dom_scrape.log + console with a verdict per param.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.browser import ChromeManager
from packages.authentication import LoginManager
from packages.track_management import TrackManager

DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "bryan-adams/18-til-i-die.html"
)
LOG_PATH = ROOT / "logs" / "probe_dom_scrape.log"
TARGET_PARAMS = [
    "prodid", "s", "pannings", "pitch", "precount",
    "bkac", "famid", "method", "trackslevels",
]


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


# Single JS snippet that returns a structured introspection of the page.
# Runs in one round-trip to avoid Selenium per-call latency.
INTROSPECT_JS = r"""
const TARGETS = arguments[0];
const out = {hidden_inputs: [], data_attrs: [], window_globals: {},
             script_matches: {}, meta_tags: [], url_query: {}};

// 1. hidden inputs
document.querySelectorAll('input[type=hidden]').forEach(el => {
  out.hidden_inputs.push({
    name: el.name || el.id || '(unnamed)',
    value: (el.value || '').slice(0, 200),
  });
});

// 2. data-* attrs on relevant elements
const selectors = ['.track', '.mixer', 'body', 'html',
                   '[class*="mixer"]', '[class*="player"]',
                   '[id*="mixer"]', '[id*="player"]'];
const seen = new Set();
selectors.forEach(sel => {
  document.querySelectorAll(sel).forEach(el => {
    if (seen.has(el)) return;
    seen.add(el);
    const attrs = {};
    for (const a of el.attributes) {
      if (a.name.startsWith('data-')) attrs[a.name] = (a.value || '').slice(0, 200);
    }
    if (Object.keys(attrs).length) {
      out.data_attrs.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className || '').slice(0, 100),
        id: el.id || '',
        attrs: attrs,
      });
    }
  });
});

// 3. window globals
TARGETS.forEach(name => {
  try {
    const v = window[name];
    if (v !== undefined) {
      let dump;
      if (typeof v === 'object') dump = JSON.stringify(v).slice(0, 300);
      else dump = String(v).slice(0, 200);
      out.window_globals[name] = {type: typeof v, value: dump};
    }
  } catch (e) {}
});

// 4. inline script regex search for each target
const scripts = Array.from(document.querySelectorAll('script:not([src])'))
  .map(s => s.textContent || '').join('\n\n/*--script-boundary--*/\n\n');
TARGETS.forEach(name => {
  // Look for `name : "value"`, `name = "value"`, `"name": ...`, `'name': ...`
  // Use template literal to avoid quote-escape headaches.
  const re = new RegExp(`["']?${name}["']?\\s*[:=]\\s*["']?([^,;}\\n"']{1,200})`, 'gi');
  const matches = [];
  let m, i = 0;
  while ((m = re.exec(scripts)) !== null && i < 5) {
    matches.push(m[1].trim().slice(0, 150));
    i++;
  }
  if (matches.length) out.script_matches[name] = matches;
});

// 5. meta tags
document.querySelectorAll('meta').forEach(el => {
  const n = el.getAttribute('name') || el.getAttribute('property') || '';
  const c = el.getAttribute('content') || '';
  if (TARGETS.some(t => n.toLowerCase().includes(t.toLowerCase()) ||
                        c.toLowerCase().includes(t.toLowerCase()))) {
    out.meta_tags.push({name: n, content: c.slice(0, 200)});
  }
});

// 6. current URL query
try {
  const url = new URL(window.location.href);
  url.searchParams.forEach((v, k) => { out.url_query[k] = v.slice(0, 200); });
} catch (e) {}

return out;
"""


def find_param_locations(introspect, target):
    """Return a list of '<source>: <value>' strings showing where a param
    appears in the introspection result."""
    found = []
    for hi in introspect["hidden_inputs"]:
        if hi["name"].lower() == target.lower():
            found.append(f"hidden_input[name={hi['name']}]: {hi['value']!r}")
    for d in introspect["data_attrs"]:
        for an, av in d["attrs"].items():
            if an.lower() == f"data-{target.lower()}":
                found.append(f"{d['tag']}.{d['cls'][:30]}#{d['id']} [{an}]: {av!r}")
    if target in introspect["window_globals"]:
        wg = introspect["window_globals"][target]
        found.append(f"window.{target} ({wg['type']}): {wg['value']!r}")
    if target in introspect["script_matches"]:
        for m in introspect["script_matches"][target][:3]:
            found.append(f"<script> match: {m!r}")
    for m in introspect["meta_tags"]:
        if target.lower() in m["name"].lower() or target.lower() in m["content"].lower():
            found.append(f"<meta name={m['name']!r}>: {m['content']!r}")
    if target in introspect["url_query"]:
        found.append(f"url?{target}={introspect['url_query'][target]!r}")
    return found


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--song-url", default=DEFAULT_SONG_URL)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--seed-track", type=int, default=1,
                   help="Solo this track before introspecting — basket params "
                        "may only populate after a track is selected")
    args = p.parse_args()

    setup_logging()
    log = logging.getLogger("dom-probe")

    log.info("=" * 70)
    log.info("Q1 probe: scrape basket.php params from song-page DOM")
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
        if not tracks:
            log.error("no tracks discovered")
            return 1
        log.info(f"discovered {len(tracks)} tracks")

        # ---------- PASS 1: introspect with NO solo, NO interaction ----------
        log.info("-" * 70)
        log.info("PASS 1: pristine page (no solo, no interaction)")
        log.info("-" * 70)
        intro_pristine = driver.execute_script(INTROSPECT_JS, TARGET_PARAMS)
        report(log, intro_pristine, "pristine")

        # ---------- PASS 2: solo a track, then re-introspect ----------
        seed = next(
            (t for t in tracks if str(t["index"]) == str(args.seed_track)),
            None,
        )
        if seed:
            log.info("-" * 70)
            log.info(f"PASS 2: after soloing track {args.seed_track} '{seed['name']}'")
            log.info("-" * 70)
            tm.ensure_intro_count_enabled(args.song_url)
            tm.ensure_only_track_active(args.seed_track, args.song_url)
            tm.solo_track(
                {"name": seed["name"], "index": args.seed_track},
                args.song_url,
            )
            intro_seeded = driver.execute_script(INTROSPECT_JS, TARGET_PARAMS)
            report(log, intro_seeded, "seeded")

            # Diff: anything that appeared only after soloing?
            log.info("-" * 70)
            log.info("DIFF: params that appeared only after soloing")
            log.info("-" * 70)
            for p_name in TARGET_PARAMS:
                pre = find_param_locations(intro_pristine, p_name)
                post = find_param_locations(intro_seeded, p_name)
                added = [x for x in post if x not in pre]
                if added:
                    log.info(f"  {p_name}: NEW after solo:")
                    for a in added:
                        log.info(f"    + {a}")
        else:
            log.warning(f"seed track {args.seed_track} not found — skipping pass 2")

    finally:
        chrome.quit()

    return 0


def report(log, intro, label):
    """Per-param verdict + raw counts."""
    log.info(f"[{label}] hidden_inputs: {len(intro['hidden_inputs'])}, "
             f"data_attr_elements: {len(intro['data_attrs'])}, "
             f"window_globals_seen: {len(intro['window_globals'])}, "
             f"script_matches: {len(intro['script_matches'])}, "
             f"meta_tags: {len(intro['meta_tags'])}, "
             f"url_query: {len(intro['url_query'])}")

    log.info(f"[{label}] per-param locations:")
    coverage = {}
    for param in TARGET_PARAMS:
        locations = find_param_locations(intro, param)
        coverage[param] = bool(locations)
        if locations:
            log.info(f"  ✓ {param}:")
            for loc in locations:
                log.info(f"      {loc}")
        else:
            log.info(f"  ✗ {param}: NOT FOUND")

    log.info(f"[{label}] coverage: {sum(coverage.values())}/{len(TARGET_PARAMS)} "
             f"params found in DOM")
    if all(coverage.values()):
        log.info(f"[{label}] ✅ all params reachable — UI download click NOT needed")
    else:
        missing = [k for k, v in coverage.items() if not v]
        log.info(f"[{label}] ⚠ missing: {missing} — UI download click still needed "
                 f"(or partial scrape + UI capture for missing)")

    # Dump a sample of hidden inputs and data attrs for visual scan
    log.info(f"[{label}] sample hidden_inputs (first 10):")
    for hi in intro["hidden_inputs"][:10]:
        log.info(f"    - {hi['name']}={hi['value'][:80]!r}")
    log.info(f"[{label}] sample data_attrs (first 10 elements):")
    for d in intro["data_attrs"][:10]:
        log.info(f"    - <{d['tag']} class={d['cls'][:40]!r} id={d['id']!r}>")
        for an, av in list(d["attrs"].items())[:8]:
            log.info(f"        {an}={av[:80]!r}")

    # Dump full result as JSON next to the log for offline inspection
    json_path = LOG_PATH.with_suffix(f".{label}.json")
    json_path.write_text(json.dumps(intro, indent=2))
    log.info(f"[{label}] full introspection dumped to {json_path}")


if __name__ == "__main__":
    sys.exit(main())
