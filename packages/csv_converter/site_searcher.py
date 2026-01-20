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
            # Wait for either results or no-results message
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".song-row, .no-results, .search-results"))
            )
        except TimeoutException:
            # Page might have loaded differently, continue anyway
            logging.debug("Timeout waiting for search results, continuing...")

    def _extract_results(self) -> List[SearchResult]:
        """
        Extract search results from the page

        Returns:
            List of SearchResult objects
        """
        results = []

        try:
            # Find all song result rows
            # The site uses .song-row or similar for results
            result_selectors = [
                ".song-row",
                ".search-item",
                "[data-song-id]",
                ".result-item"
            ]

            song_elements = []
            for selector in result_selectors:
                song_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if song_elements:
                    logging.debug(f"Found results using selector: {selector}")
                    break

            # If no structured results, try to parse the page differently
            if not song_elements:
                results = self._extract_results_fallback()
                return results

            for element in song_elements[:10]:  # Limit to first 10 results
                result = self._parse_result_element(element)
                if result:
                    results.append(result)

        except Exception as e:
            logging.error(f"Error extracting results: {e}")

        return results

    def _extract_results_fallback(self) -> List[SearchResult]:
        """
        Fallback method to extract results when standard selectors don't work

        Returns:
            List of SearchResult objects
        """
        results = []

        try:
            # Look for links to custom backing track pages
            links = self.driver.find_elements(
                By.CSS_SELECTOR,
                'a[href*="/custombackingtrack/"]'
            )

            seen_urls = set()
            for link in links:
                try:
                    href = link.get_attribute('href')

                    # Skip if not a song page or already seen
                    if not href or '/search.html' in href or href in seen_urls:
                        continue

                    # Check if it's a valid song URL pattern
                    if '.html' not in href:
                        continue

                    seen_urls.add(href)

                    # Try to extract song/artist from the link or surrounding context
                    result = self._parse_link_result(link, href)
                    if result:
                        results.append(result)

                except Exception as e:
                    logging.debug(f"Error parsing link: {e}")
                    continue

        except Exception as e:
            logging.error(f"Fallback extraction error: {e}")

        return results[:10]  # Limit results

    def _parse_result_element(self, element) -> Optional[SearchResult]:
        """
        Parse a search result element

        Args:
            element: Selenium WebElement for a result row

        Returns:
            SearchResult or None
        """
        try:
            # Try various selectors for song title
            song = None
            song_selectors = [
                ".song-title", ".title", "h3", "h4",
                "[data-song-title]", ".name"
            ]
            for selector in song_selectors:
                try:
                    song_elem = element.find_element(By.CSS_SELECTOR, selector)
                    song = song_elem.text.strip()
                    if song:
                        break
                except NoSuchElementException:
                    continue

            # Try various selectors for artist
            artist = None
            artist_selectors = [
                ".artist", ".artist-name", "[data-artist]",
                ".song-artist", ".subtitle"
            ]
            for selector in artist_selectors:
                try:
                    artist_elem = element.find_element(By.CSS_SELECTOR, selector)
                    artist = artist_elem.text.strip()
                    if artist:
                        break
                except NoSuchElementException:
                    continue

            # Get the URL
            url = None
            try:
                link = element.find_element(By.CSS_SELECTOR, 'a[href*="/custombackingtrack/"]')
                url = link.get_attribute('href')
            except NoSuchElementException:
                # Try getting URL from element itself if it's a link
                if element.tag_name == 'a':
                    url = element.get_attribute('href')

            if song and url:
                return SearchResult(song=song, artist=artist or '', url=url)

        except Exception as e:
            logging.debug(f"Error parsing result element: {e}")

        return None

    def _parse_link_result(self, link, href: str) -> Optional[SearchResult]:
        """
        Parse a result from a link element

        Args:
            link: Selenium WebElement for the link
            href: URL of the link

        Returns:
            SearchResult or None
        """
        try:
            # Extract song and artist from URL path
            # URL pattern: /custombackingtrack/artist/song.html
            path = urllib.parse.urlparse(href).path
            parts = path.strip('/').split('/')

            if len(parts) >= 3 and parts[0] == 'custombackingtrack':
                artist_slug = parts[1]
                song_slug = parts[2].replace('.html', '')

                # Convert slugs to readable names
                artist = self._slug_to_name(artist_slug)
                song = self._slug_to_name(song_slug)

                # Try to get better names from the link text
                link_text = link.text.strip()
                if link_text and link_text != href:
                    # Sometimes the link text has the song name
                    song = link_text

                # Look for artist in parent or sibling elements
                try:
                    parent = link.find_element(By.XPATH, '..')
                    parent_text = parent.text
                    if '-' in parent_text:
                        # Format might be "Artist - Song"
                        parts = parent_text.split('-')
                        if len(parts) >= 2:
                            artist = parts[0].strip()
                            song = parts[1].strip()
                except Exception:
                    pass

                return SearchResult(song=song, artist=artist, url=href)

        except Exception as e:
            logging.debug(f"Error parsing link result: {e}")

        return None

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
