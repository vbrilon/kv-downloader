#!/usr/bin/env python3
"""
Network-protocol capture probe.

Goal: determine whether the karaoke-version.com mix-gen API is:
  (a) account-state-keyed: clicking solo updates server state, getMix
      reads server state at job time → parallel downloads on one account
      are impossible (the conclusion the cancelled Tier 2 plan rests on).
  (b) request-payload-carried: getMix accepts solo state as a parameter
      → parallel downloads via direct API calls become possible, even on
      a single account, by bypassing the UI's account-state coupling.

Captures all XHR/Fetch and POST traffic during one single-track download,
plus snapshots of the mixer JS object before/after each major step. Output
is dumped as JSON to logs/probe_network_capture.json for analysis.

Run:
    python tools/probe_network_capture.py
"""

import argparse
import json
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
from packages.browser.chrome_manager import ChromeManager as _CM
from packages.authentication import LoginManager
from packages.track_management import TrackManager
from packages.configuration.selectors import (
    DOWNLOAD_BUTTON_SELECTORS,
    DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR,
)


DEFAULT_SONG_URL = (
    "https://www.karaoke-version.com/custombackingtrack/"
    "bryan-adams/18-til-i-die.html"
)
OUTPUT = ROOT / "logs" / "probe_network_capture.json"


def setup_logging():
    OUTPUT.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        force=True,
    )


# Monkey-patch ChromeManager so we get goog:loggingPrefs without forking
# its setup. driver.get_log("performance") needs this set BEFORE driver
# creation; setting it via execute_cdp_cmd afterward doesn't work.
_orig_configure = _CM._configure_chrome_options


def _patched_configure(self):
    opts = _orig_configure(self)
    opts.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL", "browser": "ALL"},
    )
    return opts


_CM._configure_chrome_options = _patched_configure


def collect_logs(driver):
    """Drain Chrome's perf-log buffer and return parsed entries."""
    out = []
    try:
        for entry in driver.get_log("performance"):
            try:
                msg = json.loads(entry["message"])["message"]
                out.append({
                    "method": msg.get("method", ""),
                    "params": msg.get("params", {}),
                    "ts": entry.get("timestamp"),
                })
            except Exception:
                continue
    except Exception as e:
        logging.warning(f"perf log fetch failed: {e}")
    return out


def snapshot_mixer(driver):
    """Dump the JS `mixer` global if it exists. Strips functions and DOM
    refs to keep the JSON small. Limits depth to avoid blowing up."""
    return driver.execute_script(
        """
        const seen = new WeakSet();
        const safe = (obj, depth) => {
            if (depth > 4) return '[max-depth]';
            if (obj === null) return null;
            if (typeof obj === 'function') return '[fn]';
            if (typeof obj !== 'object') return obj;
            if (obj.nodeType) return '[DOM:' + obj.nodeName + ']';
            if (seen.has(obj)) return '[circular]';
            seen.add(obj);
            if (Array.isArray(obj)) {
                return obj.slice(0, 50).map(v => safe(v, depth + 1));
            }
            const out = {};
            for (const k of Object.keys(obj).slice(0, 100)) {
                try { out[k] = safe(obj[k], depth + 1); }
                catch (e) { out[k] = '[err]'; }
            }
            return out;
        };

        const result = {
            mixer_exists: typeof mixer !== 'undefined',
        };
        if (typeof mixer !== 'undefined') {
            try {
                result.mixer_keys = Object.keys(mixer || {});
                result.mixer_methods = Object.getOwnPropertyNames(mixer || {})
                    .filter(k => {
                        try { return typeof mixer[k] === 'function'; }
                        catch (e) { return false; }
                    });
                result.mixer_state = safe(mixer, 0);
            } catch (e) { result.mixer_error = e.message; }
        }

        // Hunt for related globals
        const candidates = [
            'app', 'player', 'audio', 'tracks', 'song',
            'KV', 'kv', 'CustomBackingTrack',
        ];
        result.other_globals = {};
        for (const name of candidates) {
            try {
                if (typeof window[name] !== 'undefined') {
                    result.other_globals[name] = {
                        keys: Object.keys(window[name] || {}).slice(0, 30),
                    };
                }
            } catch (e) {}
        }

        // Look for any global function that contains 'getMix' or 'mixer'
        result.global_keys_with_mix = Object.keys(window)
            .filter(k => /mix/i.test(k))
            .slice(0, 30);

        return result;
        """
    )


_INTERESTING_KEYWORDS = (
    "/api", "/mix", "/track", "/solo", "/download", "/render",
    "mixer", "getmix", "getMix", "render", "stem", "bulk", "batch",
    "recis.io",
)


def is_interesting(event):
    """Filter Network events to API-shaped traffic."""
    method = event["method"]
    params = event["params"]
    url = ""
    rt = (params.get("type") or "").lower()
    if method == "Network.requestWillBeSent":
        req = params.get("request", {}) or {}
        url = req.get("url") or ""
        if not url.startswith("http"):
            return False
        bare = url.split("?", 1)[0].lower()
        for ext in (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                    ".woff", ".woff2", ".ttf", ".ico", ".map"):
            if bare.endswith(ext):
                return False
        if (req.get("method") or "").upper() == "POST":
            return True
        if rt in ("xhr", "fetch"):
            return True
        if any(k in url.lower() for k in _INTERESTING_KEYWORDS):
            return True
        return False
    if method == "Network.responseReceived":
        resp = params.get("response", {}) or {}
        url = resp.get("url") or ""
        if not url.startswith("http"):
            return False
        if rt in ("xhr", "fetch"):
            return True
        if any(k in url.lower() for k in _INTERESTING_KEYWORDS):
            return True
        return False
    return False


def get_response_body(driver, request_id):
    try:
        result = driver.execute_cdp_cmd(
            "Network.getResponseBody", {"requestId": request_id}
        )
        body = result.get("body") or ""
        return {
            "body": body[:8000],
            "base64": result.get("base64Encoded", False),
            "truncated_at": 8000 if len(body) > 8000 else None,
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--song-url", default=DEFAULT_SONG_URL)
    p.add_argument("--track", type=int, default=1)
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()

    setup_logging()
    log = logging.getLogger("probe")
    log.info("=" * 70)
    log.info("Network capture probe — single-track download")
    log.info(f"Song:  {args.song_url}")
    log.info(f"Track: {args.track}")
    log.info("=" * 70)

    chrome = ChromeManager(headless=args.headless)
    chrome.setup_driver()
    chrome.setup_folders()
    driver = chrome.driver
    wait = chrome.wait
    driver.execute_cdp_cmd("Network.enable", {})

    # Drain pre-action logs so the timeline is clean.
    collect_logs(driver)

    timeline = []  # list of step records

    def record(step, network_events):
        try:
            snap = snapshot_mixer(driver)
        except Exception as e:
            snap = {"error": str(e)}
        timeline.append({
            "step": step,
            "ts": time.time(),
            "mixer_snapshot": snap,
            "network_events": network_events,
            "network_events_count": len(network_events),
        })
        log.info(
            f"[{step}] mixer={snap.get('mixer_exists') if isinstance(snap, dict) else 'err'}"
            f" events={len(network_events)}"
        )

    try:
        login = LoginManager(driver, wait)
        if not login.login_with_session_persistence():
            log.error("login failed")
            return 2
        collect_logs(driver)  # drain login traffic
        record("after_login", [])

        tm = TrackManager(driver, wait)
        tracks = tm.discover_tracks(args.song_url)
        if not tracks:
            log.error("no tracks discovered")
            return 1
        target = next(
            (t for t in tracks if str(t["index"]) == str(args.track)),
            None,
        )
        if not target:
            log.error(f"track {args.track} not in discovered list")
            return 1
        log.info(f"target: {target['name']}")

        record("after_discover", collect_logs(driver))

        tm.ensure_intro_count_enabled(args.song_url)
        record("after_intro_count", collect_logs(driver))

        tm.ensure_only_track_active(args.track, args.song_url)
        record("after_ensure_active", collect_logs(driver))

        tm.solo_track(
            {"name": target["name"], "index": args.track}, args.song_url
        )
        record("after_solo_track", collect_logs(driver))

        # Find and click download
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
            log.error("no download button")
            return 1

        record("before_click_download", collect_logs(driver))
        driver.execute_script("arguments[0].click();", download_btn)
        log.info("clicked download")
        time.sleep(0.3)
        record("after_click_download_immediate", collect_logs(driver))

        try:
            WebDriverWait(driver, 45).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, DOWNLOAD_MODAL_OVERLAY_OPEN_SELECTOR)
                )
            )
            log.info("modal overlay opened")
        except Exception:
            log.warning("modal overlay never opened")
        record("after_modal_open", collect_logs(driver))

        ready_pats = (
            "your download will begin",
            "you can also click on the link below",
        )

        def check(_d):
            for c in _d.find_elements(By.CSS_SELECTOR, ".modal .modal__content"):
                t = (c.text or "").lower()
                for pat in ready_pats:
                    if pat in t:
                        return True
            return False

        try:
            WebDriverWait(driver, 45, poll_frequency=0.5).until(check)
            log.info("modal ready")
        except Exception:
            log.warning("modal readiness not seen")
        record("after_modal_ready", collect_logs(driver))

        # File delivery / mp3 GET happens here
        time.sleep(8)
        record("after_file_delivery_window", collect_logs(driver))

        # Consolidate interesting requests
        interesting = {}
        for snap in timeline:
            for ev in snap["network_events"]:
                if not is_interesting(ev):
                    continue
                params = ev["params"]
                rid = params.get("requestId")
                if not rid:
                    continue
                slot = interesting.setdefault(rid, {})
                if ev["method"] == "Network.requestWillBeSent":
                    req = params.get("request", {}) or {}
                    slot["request"] = {
                        "url": req.get("url"),
                        "method": req.get("method"),
                        "postData": req.get("postData"),
                        "headers": {
                            k: v for k, v in (req.get("headers") or {}).items()
                            if k.lower() in (
                                "content-type", "accept", "x-requested-with",
                                "origin", "referer",
                            )
                        },
                    }
                    slot["resource_type"] = params.get("type")
                    slot["step_at_request"] = snap["step"]
                    # CDP requestWillBeSent has 'documentURL' & 'initiator'
                    slot["initiator"] = params.get("initiator")
                elif ev["method"] == "Network.responseReceived":
                    resp = params.get("response", {}) or {}
                    slot["response"] = {
                        "url": resp.get("url"),
                        "status": resp.get("status"),
                        "mimeType": resp.get("mimeType"),
                        "headers": {
                            k: v for k, v in (resp.get("headers") or {}).items()
                            if k.lower() in (
                                "content-type", "content-length",
                                "set-cookie", "location", "cache-control",
                            )
                        },
                    }
                    slot["step_at_response"] = snap["step"]

        # Pull response bodies for non-binary requests
        for rid, info in interesting.items():
            mime = (info.get("response", {}).get("mimeType") or "").lower()
            if any(t in mime for t in ("audio/", "video/",
                                       "application/octet-stream")):
                continue
            info["body"] = get_response_body(driver, rid)

        # Trim mixer snapshots' raw network events out of the output
        for snap in timeline:
            snap["network_events"] = []

        out = {
            "song_url": args.song_url,
            "track": args.track,
            "track_name": target["name"],
            "timeline": timeline,
            "interesting_requests": interesting,
        }
        OUTPUT.write_text(json.dumps(out, indent=2, default=str))
        log.info(f"wrote capture to {OUTPUT}")
        log.info(f"interesting requests: {len(interesting)}")
        # Print a quick summary
        for rid, info in interesting.items():
            req = info.get("request", {}) or {}
            resp = info.get("response", {}) or {}
            log.info(
                f"  · [{info.get('step_at_request') or '?'}] "
                f"{req.get('method', '?')} {(req.get('url') or '')[:120]}"
                f" → {resp.get('status')} {resp.get('mimeType')}"
            )
            if req.get("postData"):
                log.info(f"      postData: {req['postData'][:200]!r}")
    finally:
        chrome.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
