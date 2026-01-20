"""Site searcher for karaoke-version.com"""

import logging
import time
import urllib.parse
from typing import List, Dict, Optional
from dataclasses import dataclass

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from packages.browser import ChromeManager


@dataclass
class SearchResult:
    """Represents a search result from the site"""
    song: str
    artist: str
    url: str


class SiteSearcher:
    """Searches karaoke-version.com for songs"""

    BASE_URL = "https://www.karaoke-version.com"
    SEARCH_URL = f"{BASE_URL}/custombackingtrack/search.html"

    # Rate limiting
    SEARCH_DELAY = 2.5  # seconds between searches

    def __init__(self, chrome_manager: ChromeManager):
        """
        Initialize the searcher

        Args:
            chrome_manager: Initialized ChromeManager instance
        """
        self.chrome_manager = chrome_manager
        self.driver = chrome_manager.driver
        self.wait = chrome_manager.wait
        self._last_search_time = 0

    def search(self, song: str, artist: str) -> List[SearchResult]:
        """
        Search for a song on karaoke-version.com

        Args:
            song: Song title to search for
            artist: Artist name to search for

        Returns:
            List of SearchResult objects
        """
        self._rate_limit()

        # Build search query
        query = f"{song} {artist}"
        encoded_query = urllib.parse.quote(query)
        search_url = f"{self.SEARCH_URL}?query={encoded_query}"

        logging.info(f"Searching for: {song} by {artist}")
        logging.debug(f"Search URL: {search_url}")

        try:
            self.driver.get(search_url)

            # Wait for page to load
            self._wait_for_page_load()

            # Extract search results
            results = self._extract_results()

            logging.info(f"Found {len(results)} results")
            return results

        except TimeoutException:
            logging.warning(f"Timeout searching for: {song} by {artist}")
            return []
        except Exception as e:
            logging.error(f"Error searching for {song} by {artist}: {e}")
            return []

    def _rate_limit(self):
        """Apply rate limiting between searches"""
        elapsed = time.time() - self._last_search_time
        if elapsed < self.SEARCH_DELAY:
            sleep_time = self.SEARCH_DELAY - elapsed
            logging.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self._last_search_time = time.time()

    def _wait_for_page_load(self):
        """Wait for search results page to load"""
        try:
            # Wait for any link to a custom backing track page
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/custombackingtrack/"][href$=".html"]'))
            )
        except TimeoutException:
            # Page might have loaded differently, continue anyway
            logging.debug("Timeout waiting for search results, continuing...")

    def _extract_results(self) -> List[SearchResult]:
        """
        Extract search results from the page

        The site structure has song links followed by artist links:
        - Song link: /custombackingtrack/artist/song.html (with song title as text)
        - Artist link: /custombackingtrack/artist/ (with artist name as text)

        Returns:
            List of SearchResult objects
        """
        results = []
        seen_urls = set()

        try:
            # Find all song links (end with .html, exclude search.html)
            song_links = self.driver.find_elements(
                By.CSS_SELECTOR,
                'a[href*="/custombackingtrack/"][href$=".html"]:not([href*="search.html"])'
            )

            logging.debug(f"Found {len(song_links)} potential song links")

            for song_link in song_links:
                try:
                    href = song_link.get_attribute('href')

                    # Skip duplicates
                    if not href or href in seen_urls:
                        continue

                    # Validate URL pattern: /custombackingtrack/artist/song.html
                    path = urllib.parse.urlparse(href).path
                    parts = path.strip('/').split('/')
                    if len(parts) != 3 or parts[0] != 'custombackingtrack':
                        continue

                    seen_urls.add(href)

                    # Get song name from link text
                    song_name = song_link.text.strip()
                    if not song_name:
                        # Fallback to slug
                        song_name = self._slug_to_name(parts[2].replace('.html', ''))

                    # Try to find artist from sibling link
                    artist_name = self._find_artist_for_song_link(song_link, parts[1])

                    result = SearchResult(song=song_name, artist=artist_name, url=href)
                    results.append(result)
                    logging.debug(f"  Found: {song_name} by {artist_name}")

                    # Limit to first 10 results
                    if len(results) >= 10:
                        break

                except Exception as e:
                    logging.debug(f"Error parsing song link: {e}")
                    continue

        except Exception as e:
            logging.error(f"Error extracting results: {e}")

        return results

    def _find_artist_for_song_link(self, song_link, artist_slug: str) -> str:
        """
        Find the artist name for a song link by looking at sibling elements

        Args:
            song_link: Selenium WebElement for the song link
            artist_slug: Artist slug from URL as fallback

        Returns:
            Artist name
        """
        try:
            # Look for sibling link that points to artist page
            # Artist links have pattern: /custombackingtrack/artist/ (no .html)
            parent = song_link.find_element(By.XPATH, '..')

            # Find artist link in the parent container
            artist_links = parent.find_elements(
                By.CSS_SELECTOR,
                f'a[href*="/custombackingtrack/{artist_slug}/"]'
            )

            for artist_link in artist_links:
                href = artist_link.get_attribute('href')
                # Artist page links don't end with .html
                if href and not href.endswith('.html'):
                    text = artist_link.text.strip()
                    if text:
                        return text

            # Try finding any artist-like link in parent
            all_links = parent.find_elements(By.TAG_NAME, 'a')
            for link in all_links:
                href = link.get_attribute('href') or ''
                # Artist links end with / and contain /custombackingtrack/
                if '/custombackingtrack/' in href and href.endswith('/') and not href.endswith('custombackingtrack/'):
                    text = link.text.strip()
                    if text and text != song_link.text.strip():
                        return text

        except Exception as e:
            logging.debug(f"Error finding artist: {e}")

        # Fallback to slug
        return self._slug_to_name(artist_slug)

    def _slug_to_name(self, slug: str) -> str:
        """
        Convert a URL slug to a readable name

        Args:
            slug: URL slug (e.g., 'green-day')

        Returns:
            Readable name (e.g., 'Green Day')
        """
        # Replace hyphens with spaces and title case
        name = slug.replace('-', ' ')
        return name.title()

    def get_result_as_dict(self, result: SearchResult) -> Dict:
        """
        Convert SearchResult to dictionary format

        Args:
            result: SearchResult object

        Returns:
            Dictionary with song, artist, url keys
        """
        return {
            'song': result.song,
            'artist': result.artist,
            'url': result.url
        }
