#!/usr/bin/env python3
"""Q1 deep-dive probe — find pannings + bkac in the page DOM.

The first probe (probe_dom_scrape.py) found prodid/famid in inline scripts
and parent_id in hidden inputs (likely == basket `s`). Gaps were:
  - pannings: not matched by the simple `name [:=] value` regex
  - bkac: matched a variable reference, not the literal value
  - method: trivially "ajax"; ignore

This probe lists:
  1. Every window.* top-level global (just keys + types)
  2. Every line in inline scripts containing "pannings", "basket",
     "trackslevels", or "bkac" (with surrounding context)
  3. The mixer JS object (if window.mixer exists)
  4. Whether `pannings` lives on each .track element as a data-attr or
     mirrored in some hidden state
"""

import argparse
import json
import logging
import re
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
LOG_PATH = ROOT / "logs" / "probe_dom_deep.log"


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


WINDOW_DUMP_JS = r"""
const out = {keys: [], summary: {}};
for (const k of Object.keys(window)) {
  out.keys.push(k);
}
const interesting = ['mixer', 'pitch', 'precount', 'editf', 'basket',
                     'pannings', 'trackslevels', 'song', 'product',
                     'tracksData', 'track_data', 'mp_settings',
                     'mp', 'KV', 'kv'];
interesting.forEach(name => {
  try {
    const v = window[name];
    if (v === undefined || v === null) return;
    let dump;
    if (typeof v === 'function') dump = '[function]';
    else if (typeof v === 'object') {
      try { dump = JSON.stringify(v).slice(0, 1000); }
      catch (e) { dump = '[object: ' + Object.keys(v).join(',').slice(0, 300) + ']'; }
    } else dump = String(v).slice(0, 500);
    out.summary[name] = {type: typeof v, value: dump};
  } catch (e) {}
});
return out;
"""

CONTEXT_LINES_JS = r"""
const PATTERNS = arguments[0];
const out = {};
const allScripts = Array.from(document.querySelectorAll('script:not([src])'))
  .map((s, i) => ({idx: i, src: s.textContent || ''}));
PATTERNS.forEach(p => {
  out[p] = [];
  allScripts.forEach(({idx, src}) => {
    const lines = src.split('\n');
    lines.forEach((line, ln) => {
      if (line.toLowerCase().includes(p.toLowerCase())) {
        // Strip whitespace and limit length
        const clean = line.trim().slice(0, 400);
        if (clean.length > 0) {
          out[p].push({script: idx, line_num: ln + 1, text: clean});
        }
      }
    });
  });
});
return out;
"""

TRACK_ATTRS_JS = r"""
const out = [];
document.querySelectorAll('.track').forEach(t => {
  const attrs = {};
  for (const a of t.attributes) attrs[a.name] = a.value;
  // Also dump data-* attrs of any descendants that have them
  const childAttrs = [];
  t.querySelectorAll('[data-volume], [data-pan], [data-panning], ' +
                     '[data-pitch], [data-level]').forEach(el => {
    const ca = {};
    for (const a of el.attributes) {
      if (a.name.startsWith('data-')) ca[a.name] = a.value;
    }
    if (Object.keys(ca).length) {
      childAttrs.push({tag: el.tagName.toLowerCase(),
                       cls: (el.className || '').slice(0, 80),
                       attrs: ca});
    }
  });
  out.push({attrs: attrs, child_data_attrs: childAttrs});
});
return out;
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--song-url", default=DEFAULT_SONG_URL)
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()

    setup_logging()
    log = logging.getLogger("dom-deep")

    log.info("=" * 70)
    log.info("Q1 deep dive: find pannings + bkac in DOM/JS")
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

        # ---------- 1. Window globals ----------
        log.info("-" * 70)
        log.info("1. Window globals — interesting candidates")
        log.info("-" * 70)
        wg = driver.execute_script(WINDOW_DUMP_JS)
        log.info(f"total window keys: {len(wg['keys'])}")
        log.info("named candidates that exist:")
        for name, info in wg["summary"].items():
            log.info(f"  window.{name} ({info['type']}): {info['value'][:300]}")

        # Dump suspicious-looking keys (heuristics: not all-caps, not common
        # browser builtins, not starting with __ or _)
        BUILTINS = {
            "window", "document", "self", "location", "history",
            "navigator", "console", "screen", "frames", "parent", "top",
            "globalThis", "name", "length", "closed", "opener",
            "performance", "fetch", "Promise", "Symbol", "Math", "Date",
            "JSON", "Object", "Array", "String", "Number", "Boolean",
            "RegExp", "Error", "TypeError", "RangeError", "EvalError",
            "URIError", "SyntaxError", "ReferenceError", "URL",
            "URLSearchParams", "FormData", "Blob", "File", "FileList",
            "FileReader", "ImageData", "AudioContext", "Audio", "Image",
            "Event", "MouseEvent", "KeyboardEvent", "WheelEvent",
            "MessageEvent", "Worker", "WebSocket", "XMLHttpRequest",
            "localStorage", "sessionStorage", "indexedDB", "caches",
            "crypto", "atob", "btoa", "alert", "confirm", "prompt",
            "setTimeout", "clearTimeout", "setInterval", "clearInterval",
            "requestAnimationFrame", "cancelAnimationFrame",
            "addEventListener", "removeEventListener", "dispatchEvent",
            "scrollTo", "scrollBy", "scroll", "scrollX", "scrollY",
            "innerWidth", "innerHeight", "outerWidth", "outerHeight",
            "devicePixelRatio", "screenX", "screenY", "pageXOffset",
            "pageYOffset", "isSecureContext", "origin", "external",
            "menubar", "personalbar", "scrollbars", "statusbar", "toolbar",
            "locationbar", "speechSynthesis", "trustedTypes",
            "visualViewport", "matchMedia", "getSelection",
            "getComputedStyle", "open", "close", "stop", "print", "focus",
            "blur", "getMatchedCSSRules", "queueMicrotask", "structuredClone",
            "reportError", "createImageBitmap", "scheduler", "cookieStore",
        }
        suspicious = [
            k for k in wg["keys"]
            if k not in BUILTINS
            and not k.startswith("_")
            and not k.startswith("webkit")
            and not k.startswith("on")  # event handlers
            and not (k.isupper() and len(k) > 4)  # constants
            and len(k) < 40  # likely human-readable
        ]
        log.info(f"non-builtin window keys ({len(suspicious)}): "
                 f"{suspicious[:120]}")

        # ---------- 2. Find all references to key terms in scripts ----------
        log.info("-" * 70)
        log.info("2. Inline-script lines mentioning pannings/basket/trackslevels/bkac")
        log.info("-" * 70)
        terms = ["pannings", "basket", "trackslevels", "bkac",
                 "editf", "mixer.getMix", "mixer.audio_server"]
        ctx = driver.execute_script(CONTEXT_LINES_JS, terms)
        for term, hits in ctx.items():
            log.info(f"\n--- term: '{term}' ({len(hits)} matches) ---")
            for hit in hits[:30]:
                log.info(f"  script[{hit['script']}] L{hit['line_num']}: {hit['text']}")
            if len(hits) > 30:
                log.info(f"  ... and {len(hits) - 30} more")

        # ---------- 3. Track element attrs ----------
        log.info("-" * 70)
        log.info("3. Track-element data-* attrs (looking for per-track pan/level)")
        log.info("-" * 70)
        ta = driver.execute_script(TRACK_ATTRS_JS)
        log.info(f"discovered {len(ta)} .track elements")
        for i, t in enumerate(ta[:5]):
            log.info(f"  track[{i}] attrs: {t['attrs']}")
            for ca in t["child_data_attrs"][:5]:
                log.info(f"      child <{ca['tag']} class={ca['cls'][:30]!r}>: {ca['attrs']}")
        if len(ta) > 5:
            log.info(f"  ... and {len(ta) - 5} more (saved to JSON)")

        # Dump full JSON for offline inspection
        full = {"window": wg, "context_lines": ctx, "track_attrs": ta}
        json_path = LOG_PATH.with_suffix(".json")
        json_path.write_text(json.dumps(full, indent=2))
        log.info(f"full dump → {json_path}")

    finally:
        chrome.quit()

    return 0


if __name__ == "__main__":
    sys.exit(main())
