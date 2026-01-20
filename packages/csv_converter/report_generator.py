"""Report generator for unmatched and partial match songs"""

import logging
from pathlib import Path
from typing import List
from datetime import datetime
from dataclasses import dataclass

from .match_scorer import MatchResult, MatchConfidence


@dataclass
class UnmatchedEntry:
    """Entry for a song that couldn't be matched"""
    song: str
    artist: str
    reason: str


class ReportGenerator:
    """Generates reports for songs that need manual attention"""

    DEFAULT_OUTPUT = "unmatched_songs.txt"

    def __init__(self, output_path: str = None):
        """
        Initialize the report generator

        Args:
            output_path: Path for output file (default: unmatched_songs.txt)
        """
        self.output_path = Path(output_path or self.DEFAULT_OUTPUT)
        self.unmatched: List[UnmatchedEntry] = []
        self.partial_matches: List[MatchResult] = []

    def add_unmatched(self, song: str, artist: str, reason: str = "No results found"):
        """
        Add an unmatched song to the report

        Args:
            song: Song title
            artist: Artist name
            reason: Reason for no match
        """
        self.unmatched.append(UnmatchedEntry(song=song, artist=artist, reason=reason))

    def add_partial_match(self, match: MatchResult):
        """
        Add a partial match (medium confidence) to the report

        Args:
            match: MatchResult with medium confidence
        """
        if match.confidence == MatchConfidence.MEDIUM:
            self.partial_matches.append(match)

    def add_low_confidence_match(self, match: MatchResult):
        """
        Add a low confidence match to unmatched list

        Args:
            match: MatchResult with low confidence
        """
        if match.confidence == MatchConfidence.LOW:
            self.unmatched.append(UnmatchedEntry(
                song=match.search_song,
                artist=match.search_artist,
                reason=f"Low confidence ({match.combined_score:.0%}): "
                       f"Best match was '{match.result_song}' by '{match.result_artist}'"
            ))

    def write(self) -> bool:
        """
        Write the report to file

        Returns:
            True if successful or no issues to report, False on error
        """
        if not self.unmatched and not self.partial_matches:
            logging.info("No unmatched songs or partial matches to report")
            return True

        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                self._write_header(f)
                self._write_unmatched_section(f)
                self._write_partial_match_section(f)
                self._write_footer(f)

            total_issues = len(self.unmatched) + len(self.partial_matches)
            logging.info(f"Wrote report with {total_issues} items to {self.output_path}")
            return True

        except Exception as e:
            logging.error(f"Error writing report: {e}")
            return False

    def _write_header(self, f):
        """Write report header"""
        f.write("=" * 70 + "\n")
        f.write("KARAOKE-VERSION.COM - SONG MATCHING REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        # Summary
        f.write("SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Unmatched songs:  {len(self.unmatched)}\n")
        f.write(f"Partial matches:  {len(self.partial_matches)}\n")
        f.write("\n")

    def _write_unmatched_section(self, f):
        """Write the unmatched songs section"""
        if not self.unmatched:
            return

        f.write("UNMATCHED SONGS (Require Manual Lookup)\n")
        f.write("-" * 40 + "\n")
        f.write("These songs could not be found or had very low match scores.\n")
        f.write("Please search manually at: https://www.karaoke-version.com\n\n")

        for i, entry in enumerate(self.unmatched, 1):
            f.write(f"{i}. {entry.song} - {entry.artist}\n")
            f.write(f"   Reason: {entry.reason}\n\n")

        f.write("\n")

    def _write_partial_match_section(self, f):
        """Write the partial matches section"""
        if not self.partial_matches:
            return

        f.write("PARTIAL MATCHES (Review Recommended)\n")
        f.write("-" * 40 + "\n")
        f.write("These songs had medium confidence matches (70-85%).\n")
        f.write("They were included in the YAML but may not be correct.\n\n")

        for i, match in enumerate(self.partial_matches, 1):
            f.write(f"{i}. Searched: {match.search_song} - {match.search_artist}\n")
            f.write(f"   Found:    {match.result_song} - {match.result_artist}\n")
            f.write(f"   Score:    {match.combined_score:.0%} "
                    f"(Song: {match.song_score:.0%}, Artist: {match.artist_score:.0%})\n")
            f.write(f"   URL:      {match.result_url}\n\n")

        f.write("\n")

    def _write_footer(self, f):
        """Write report footer"""
        f.write("=" * 70 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 70 + "\n")

    def get_summary(self) -> str:
        """
        Get a brief summary of issues

        Returns:
            Summary string
        """
        parts = []
        if self.unmatched:
            parts.append(f"{len(self.unmatched)} unmatched")
        if self.partial_matches:
            parts.append(f"{len(self.partial_matches)} partial matches")

        if parts:
            return f"Issues found: {', '.join(parts)}"
        return "All songs matched successfully"

    def has_issues(self) -> bool:
        """
        Check if there are any issues to report

        Returns:
            True if there are unmatched or partial matches
        """
        return bool(self.unmatched or self.partial_matches)
