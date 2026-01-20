"""Match scoring for song/artist comparisons"""

import logging
from difflib import SequenceMatcher
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class MatchConfidence(Enum):
    """Confidence levels for matches"""
    HIGH = "high"        # >= 85% - Auto-include in yaml
    MEDIUM = "medium"    # 70-85% - Include in report as partial match
    LOW = "low"          # < 70% - Skip, report as unmatched


@dataclass
class MatchResult:
    """Result of a match comparison"""
    song_score: float
    artist_score: float
    combined_score: float
    confidence: MatchConfidence
    search_song: str
    search_artist: str
    result_song: str
    result_artist: str
    result_url: str

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence == MatchConfidence.HIGH

    @property
    def is_acceptable(self) -> bool:
        return self.confidence in (MatchConfidence.HIGH, MatchConfidence.MEDIUM)


class MatchScorer:
    """Scores match quality between search terms and results"""

    HIGH_THRESHOLD = 0.85
    MEDIUM_THRESHOLD = 0.70

    # Weight song more heavily than artist (song name is more important)
    SONG_WEIGHT = 0.6
    ARTIST_WEIGHT = 0.4

    def __init__(self, high_threshold: float = 0.85, medium_threshold: float = 0.70):
        """
        Initialize the scorer

        Args:
            high_threshold: Minimum score for high confidence (default 85%)
            medium_threshold: Minimum score for medium confidence (default 70%)
        """
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def score_match(
        self,
        search_song: str,
        search_artist: str,
        result_song: str,
        result_artist: str,
        result_url: str
    ) -> MatchResult:
        """
        Score the match between search terms and a result

        Args:
            search_song: Song name being searched for
            search_artist: Artist name being searched for
            result_song: Song name from search result
            result_artist: Artist name from search result
            result_url: URL from search result

        Returns:
            MatchResult with scores and confidence level
        """
        song_score = self._calculate_similarity(search_song, result_song)
        artist_score = self._calculate_similarity(search_artist, result_artist)

        # Combined score with weights
        combined_score = (
            song_score * self.SONG_WEIGHT +
            artist_score * self.ARTIST_WEIGHT
        )

        # Determine confidence level
        confidence = self._determine_confidence(combined_score, song_score, artist_score)

        result = MatchResult(
            song_score=song_score,
            artist_score=artist_score,
            combined_score=combined_score,
            confidence=confidence,
            search_song=search_song,
            search_artist=search_artist,
            result_song=result_song,
            result_artist=result_artist,
            result_url=result_url
        )

        logging.debug(
            f"Match score: '{search_song}' vs '{result_song}' = {song_score:.2%}, "
            f"'{search_artist}' vs '{result_artist}' = {artist_score:.2%}, "
            f"combined = {combined_score:.2%} ({confidence.value})"
        )

        return result

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0

        # Normalize strings for comparison
        norm1 = self._normalize_for_comparison(str1)
        norm2 = self._normalize_for_comparison(str2)

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, norm1, norm2).ratio()

    def _normalize_for_comparison(self, text: str) -> str:
        """
        Normalize text for comparison

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        import re

        # Convert to lowercase
        normalized = text.lower()

        # Remove common prefixes/suffixes that don't affect identity
        prefixes = ['the ', 'a ', 'an ']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]

        # Remove special characters but keep spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Normalize whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def _determine_confidence(
        self,
        combined_score: float,
        song_score: float,
        artist_score: float
    ) -> MatchConfidence:
        """
        Determine confidence level based on scores

        Args:
            combined_score: Weighted combined score
            song_score: Individual song match score
            artist_score: Individual artist match score

        Returns:
            MatchConfidence level
        """
        # High confidence: good combined score AND decent individual scores
        if combined_score >= self.high_threshold:
            # Extra check: both components should be reasonably good
            if song_score >= 0.70 and artist_score >= 0.50:
                return MatchConfidence.HIGH

        # Medium confidence
        if combined_score >= self.medium_threshold:
            return MatchConfidence.MEDIUM

        # Fallback: if song is exact but artist is different, still medium
        if song_score >= 0.95:
            return MatchConfidence.MEDIUM

        return MatchConfidence.LOW

    def find_best_match(
        self,
        search_song: str,
        search_artist: str,
        results: list
    ) -> Optional[MatchResult]:
        """
        Find the best matching result from a list

        Args:
            search_song: Song name being searched for
            search_artist: Artist name being searched for
            results: List of dicts with 'song', 'artist', 'url' keys

        Returns:
            Best MatchResult or None if no acceptable match found
        """
        if not results:
            return None

        best_match = None
        best_score = 0

        for result in results:
            match = self.score_match(
                search_song=search_song,
                search_artist=search_artist,
                result_song=result.get('song', ''),
                result_artist=result.get('artist', ''),
                result_url=result.get('url', '')
            )

            if match.combined_score > best_score:
                best_score = match.combined_score
                best_match = match

        # Only return if meets minimum threshold
        if best_match and best_match.combined_score >= self.medium_threshold:
            return best_match

        return best_match  # Return even low confidence for reporting
