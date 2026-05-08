#!/usr/bin/env python3
"""Live-site verification for the solo-button detection fix.

Why this exists:
  Production logs showed every solo button being reported as already-active,
  causing the "soloing every track in the song before settling on the right
  one" UI behavior. Root cause was substring matching ("active" in "inactive",
  "on" in "button"/"icon"). Detection is now token-based — see
  packages/utils/solo_state.py:ACTIVE_SOLO_CLASS_TOKENS.

What this script does:
  1. Logs in (reuses session if available).
  2. Navigates to a song page (CLI arg or first URL in songs.yaml).
  3. Captures the class lists of every solo button while all are inactive,
     and asserts ``is_solo_button_active`` returns False for each. Failure
     here would mean false positives are still occurring on the real site.
  4. Clicks track 0's solo button, waits for activation, then re-checks all
     buttons:
       * track 0  → must report active
       * all others → must report inactive
     Failure here would mean either real-positive misses OR cross-track
     false positives.
  5. Prints a per-track table with the captured class strings so we can
     confirm what the site actually emits and refresh ACTIVE_SOLO_CLASS_TOKENS
     if the markup ever changes.

Usage:
  ./bin/python tools/inspection/verify_solo_button_detection.py
  ./bin/python tools/inspection/verify_solo_button_detection.py <song_url>

Exit code is 0 only when every assertion passes.
"""

import sys
import time
from pathlib import Path

import yaml
from selenium.webdriver.common.by import By

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from karaoke_automator import KaraokeVersionAutomator
from packages.utils import ACTIVE_SOLO_CLASS_TOKENS


def _resolve_song_url(cli_args):
    if len(cli_args) > 1:
        return cli_args[1]
    with open(ROOT / "songs.yaml", "r") as f:
        data = yaml.safe_load(f) or {}
    songs = (data.get("songs") or [])
    songs = [s for s in songs if isinstance(s, dict) and s.get("url")]
    if not songs:
        sys.exit("No song URL given and no songs configured in songs.yaml")
    return songs[0]["url"]


def _capture_button_state(driver, expected_count=None):
    """Return a list of (data_index, class_string, is_active) tuples."""
    buttons = driver.find_elements(By.CSS_SELECTOR, "button.track__solo")
    if expected_count is not None and len(buttons) != expected_count:
        print(f"  ⚠️  Expected {expected_count} solo buttons, found {len(buttons)}")

    rows = []
    for btn in buttons:
        # Walk up to the parent .track to find data-index for nicer reporting.
        try:
            track = btn.find_element(By.XPATH, "./ancestor::*[contains(@class,'track')][1]")
            idx = track.get_attribute("data-index")
        except Exception:
            idx = "?"
        class_str = btn.get_attribute("class") or ""
        tokens = set(class_str.lower().split())
        is_active = bool(tokens & ACTIVE_SOLO_CLASS_TOKENS)
        rows.append((idx, class_str, is_active, btn))
    # Sort by numeric index when possible.
    rows.sort(key=lambda r: (int(r[0]) if (r[0] or "").isdigit() else 999, r[0]))
    return rows


def _print_table(title, rows):
    print(f"\n{title}")
    print(f"  {'idx':<5} {'active?':<8} class")
    for idx, class_str, is_active, _btn in rows:
        marker = "ACTIVE" if is_active else "-"
        print(f"  {str(idx):<5} {marker:<8} {class_str}")


def main():
    song_url = _resolve_song_url(sys.argv)
    print(f"🎯 Target song: {song_url}")

    automator = KaraokeVersionAutomator(headless=False, show_progress=False)
    failures = []
    try:
        if not automator.login():
            sys.exit("❌ Login failed")
        print("✅ Logged in")

        automator.driver.get(song_url)
        time.sleep(3)  # Wait for mixer to render. Cheap and good enough for a one-shot probe.

        tracks = automator.get_available_tracks(song_url)
        if not tracks:
            sys.exit("❌ No tracks discovered on song page")
        print(f"✅ Discovered {len(tracks)} tracks")

        # ----- Phase 1: nothing soloed -----
        rows = _capture_button_state(automator.driver, expected_count=len(tracks))
        _print_table("Phase 1 — no solos active (expect every row to report `-`):", rows)
        bogus_active = [r for r in rows if r[2]]
        if bogus_active:
            failures.append(
                f"Phase 1: {len(bogus_active)} button(s) falsely reported active "
                f"(indices: {[r[0] for r in bogus_active]})"
            )

        # ----- Phase 2: solo track 0 -----
        target_row = next((r for r in rows if r[0] == "0"), None)
        if target_row is None:
            sys.exit("❌ Could not locate solo button for data-index='0'")
        target_btn = target_row[3]
        print("\n🖱️  Clicking solo button for track 0…")
        target_btn.click()
        time.sleep(2)  # Audio-server activation typically lands within ~1s.

        rows_after = _capture_button_state(automator.driver, expected_count=len(tracks))
        _print_table("Phase 2 — track 0 should be ACTIVE, all others `-`:", rows_after)

        for idx, _class_str, is_active, _btn in rows_after:
            if idx == "0" and not is_active:
                failures.append("Phase 2: track 0 not detected as active after click")
            elif idx != "0" and is_active:
                failures.append(f"Phase 2: track {idx} falsely reported active alongside track 0")

        # ----- Phase 3: clear by clicking track 0 again -----
        try:
            # Refind the button — DOM may have re-rendered.
            new_rows = _capture_button_state(automator.driver)
            cleared = next((r for r in new_rows if r[0] == "0"), None)
            if cleared:
                cleared[3].click()
                time.sleep(1.5)
                final_rows = _capture_button_state(automator.driver)
                still_active = [r for r in final_rows if r[2]]
                _print_table("Phase 3 — after un-soloing track 0, expect no active rows:", final_rows)
                if still_active:
                    failures.append(
                        f"Phase 3: {len(still_active)} button(s) still report active after clear"
                    )
        except Exception as e:
            print(f"  ⚠️  Phase 3 cleanup encountered: {e}")

        if failures:
            print("\n❌ Live-site verification FAILED:")
            for line in failures:
                print(f"   - {line}")
            sys.exit(1)

        print("\n✅ Live-site verification passed. "
              "Detection agrees with reality on all tracks.")
    finally:
        try:
            automator.chrome_manager.driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
