"""Fastly bot-challenge detection.

Since 2026-10 karaoke-version.com is behind Fastly bot management. Normal
browsers pass a silent check; the Selenium-driven browser is escalated to an
image CAPTCHA page titled "Client Challenge" (assets under /_fs-ch-<id>/).
Plain HTTP clients get the same page as an HTTP 200 HTML body.

A human solve in the automation's own browser sets `_fs_ch_*` clearance
cookies in chrome_profile/, which later (headless) runs reuse. We never try
to solve or evade the challenge — we detect it and hand it to the user.
"""

import subprocess

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

CHALLENGE_TITLE = "Client Challenge"
CHALLENGE_ASSET_MARKER = "/_fs-ch-"

# How long a visible run waits for the user to solve the CAPTCHA.
CHALLENGE_SOLVE_TIMEOUT_S = 180

HEADLESS_INSTRUCTIONS = (
    "karaoke-version.com is showing a Fastly bot-check CAPTCHA. Re-run with "
    "--debug (visible browser) and solve it in the Chrome window; later "
    "headless runs reuse the clearance."
)


class BotChallengeError(RuntimeError):
    """The site served a bot challenge that was not (or cannot be) solved."""


def notify_user(message: str) -> None:
    """Get the user's attention: terminal bell plus a macOS notification."""
    print("\a", end="", flush=True)
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "kv-downloader" sound name "Glass"'],
            check=False, timeout=5, capture_output=True,
        )
    except Exception:
        pass  # non-macOS or osascript unavailable: the bell + log line remain


def is_challenge_html(text) -> bool:
    """True if an HTTP response body is the Fastly challenge page."""
    return bool(text) and CHALLENGE_ASSET_MARKER in text


def is_challenge_page(driver) -> bool:
    """True if the browser is currently showing the Fastly challenge page."""
    return driver.title == CHALLENGE_TITLE


def wait_for_clearance(driver, timeout=CHALLENGE_SOLVE_TIMEOUT_S, poll=2) -> bool:
    """Wait for the user to solve the challenge; True once the page moves on."""
    try:
        WebDriverWait(driver, timeout, poll_frequency=poll).until(
            lambda d: not is_challenge_page(d)
        )
        return True
    except TimeoutException:
        return False
