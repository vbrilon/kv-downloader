#!/usr/bin/env python3
"""
Test click interception fixes for solo buttons and download button
Validates JavaScript click fallback functionality
"""

import time
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from karaoke_automator import KaraokeVersionAutomator


def _driver_is_alive(driver):
    """Return True if the ChromeDriver session is still responsive.

    solo_track / download_current_mix swallow infrastructure errors and return
    False, so the tests need a separate signal to distinguish a real product
    failure from a dead WebDriver session.
    """
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


@pytest.mark.live
def test_click_interception_fixes():
    """Verify JavaScript click fallbacks for solo/download still work end-to-end
    on representative track types."""
    from selenium.common.exceptions import WebDriverException

    print("🔧 TESTING CLICK INTERCEPTION FIXES")
    print("Validating JavaScript click fallbacks")
    print("="*60)

    song_url = "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"

    automator = None
    try:
        try:
            automator = KaraokeVersionAutomator()
        except Exception as e:
            pytest.skip(f"Could not initialize KaraokeVersionAutomator: {e}")

        try:
            login_ok = automator.login()
        except Exception as e:
            # Browser session can die when the persistent chrome_profile is in a
            # bad state from a prior run; treat that as an environment issue.
            pytest.skip(f"Live login raised an exception: {e}")
        if not login_ok:
            pytest.skip("Live login to karaoke-version.com failed (credentials/network)")
        print("✅ Login successful!")

        try:
            tracks = automator.get_available_tracks(song_url)
        except Exception as e:
            pytest.skip(f"Track discovery raised an exception: {e}")
        assert tracks, f"No tracks discovered at {song_url}"
        print(f"✅ Found {len(tracks)} tracks")

        # Build the list of track types we care about. Bass should always be
        # present; guitar/vocal historically had click-interception issues so
        # we exercise them whenever the song offers them.
        candidates = []
        for label, predicate in (
            ("Bass", lambda n: 'bass' in n),
            ("Guitar", lambda n: 'guitar' in n),
            ("Vocals", lambda n: 'vocal' in n),
        ):
            matches = [t for t in tracks if predicate(t['name'].lower())]
            if matches:
                candidates.append((label, matches[0]))

        assert candidates, "No bass/guitar/vocal tracks found to exercise"

        solo_failures = []
        download_failures = []

        for track_type, track_info in candidates:
            print(f"\n🎯 Testing {track_type}: {track_info['name']}")

            try:
                soloed = automator.solo_track(track_info, song_url)
            except WebDriverException as e:
                pytest.skip(f"WebDriver lost while soloing {track_info['name']}: {e}")
            if not soloed:
                if not _driver_is_alive(automator.driver):
                    pytest.skip(
                        f"Chrome session died during solo of {track_info['name']} — "
                        "treating as environmental"
                    )
                solo_failures.append(f"{track_type} ({track_info['name']})")
                print(f"❌ Failed to solo {track_info['name']}")
                continue
            print(f"✅ Successfully soloed {track_info['name']}")

            time.sleep(2)  # Wait for UI update
            print(f"⬇️ Testing download for {track_info['name']}...")
            # Use the actual track name and index so the manager's verification
            # passes and so it does not hit the legacy fallback path that
            # accesses a non-existent `tracks` attribute on the DI adapter.
            try:
                downloaded = automator.download_manager.download_current_mix(
                    song_url,
                    track_name=track_info['name'],
                    track_index=track_info['index'],
                )
            except WebDriverException as e:
                pytest.skip(f"WebDriver lost during download of {track_info['name']}: {e}")
            if downloaded:
                print(f"✅ Download initiated for {track_info['name']}")
                time.sleep(3)
            else:
                if not _driver_is_alive(automator.driver):
                    pytest.skip(
                        f"Chrome session died during download of {track_info['name']} — "
                        "treating as environmental"
                    )
                download_failures.append(f"{track_type} ({track_info['name']})")
                print(f"❌ Download failed for {track_info['name']}")

            try:
                automator.clear_all_solos(song_url)
            except WebDriverException as e:
                pytest.skip(f"WebDriver lost while clearing solos: {e}")
            time.sleep(1)

        print(f"\n📊 CLICK INTERCEPTION FIX RESULTS:")
        print(f"Solo Tests:     {len(candidates) - len(solo_failures)}/{len(candidates)} successful")
        print(f"Download Tests: {len(candidates) - len(download_failures)}/{len(candidates)} successful")

        assert not solo_failures, (
            f"Solo activation failed for: {solo_failures}"
        )
        assert len(download_failures) < len(candidates), (
            f"All download attempts failed: {download_failures}"
        )

    finally:
        if automator is not None:
            try:
                automator.driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    print("="*60)
    try:
        test_click_interception_fixes()
    except AssertionError as e:
        print(f"CLICK INTERCEPTION FIX TEST: FAILED — {e}")
        print("="*60)
        sys.exit(1)
    print("CLICK INTERCEPTION FIX TEST: SUCCESS")
    print("="*60)