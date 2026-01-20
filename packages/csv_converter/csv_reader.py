"""CSV file reader for song/artist pairs"""

import csv
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SongEntry:
    """Represents a song entry from the CSV file"""
    song: str
    artist: str
    row_number: int

    def __str__(self) -> str:
        return f"{self.song} by {self.artist}"


class CSVReader:
    """Reads and validates CSV files with song/artist pairs"""

    REQUIRED_COLUMNS = {'song', 'artist'}

    def __init__(self, file_path: str):
        """
        Initialize CSV reader

        Args:
            file_path: Path to the CSV file
        """
        self.file_path = Path(file_path)
        self.entries: List[SongEntry] = []
        self.errors: List[str] = []

    def validate_file(self) -> bool:
        """
        Validate that the CSV file exists and is readable

        Returns:
            True if file is valid, False otherwise
        """
        if not self.file_path.exists():
            self.errors.append(f"File not found: {self.file_path}")
            return False

        if not self.file_path.suffix.lower() == '.csv':
            self.errors.append(f"File is not a CSV: {self.file_path}")
            return False

        return True

    def read(self) -> List[SongEntry]:
        """
        Read and parse the CSV file

        Returns:
            List of SongEntry objects
        """
        if not self.validate_file():
            for error in self.errors:
                logging.error(error)
            return []

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                # Detect delimiter (comma or semicolon)
                sample = f.read(1024)
                f.seek(0)

                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
                reader = csv.DictReader(f, dialect=dialect)

                # Validate header columns
                if not self._validate_headers(reader.fieldnames):
                    return []

                # Read entries
                for row_num, row in enumerate(reader, start=2):
                    entry = self._parse_row(row, row_num)
                    if entry:
                        self.entries.append(entry)

                logging.info(f"Read {len(self.entries)} song entries from {self.file_path}")
                return self.entries

        except csv.Error as e:
            error_msg = f"CSV parsing error: {e}"
            self.errors.append(error_msg)
            logging.error(error_msg)
            return []
        except Exception as e:
            error_msg = f"Error reading CSV file: {e}"
            self.errors.append(error_msg)
            logging.error(error_msg)
            return []

    def _validate_headers(self, fieldnames: Optional[List[str]]) -> bool:
        """
        Validate that required columns exist in the CSV

        Args:
            fieldnames: List of column names from CSV

        Returns:
            True if valid, False otherwise
        """
        if not fieldnames:
            self.errors.append("CSV file has no headers")
            return False

        # Normalize column names to lowercase for comparison
        normalized = {name.lower().strip() for name in fieldnames}

        missing = self.REQUIRED_COLUMNS - normalized
        if missing:
            self.errors.append(f"Missing required columns: {missing}")
            logging.error(f"Missing required columns: {missing}")
            return False

        return True

    def _parse_row(self, row: dict, row_num: int) -> Optional[SongEntry]:
        """
        Parse a single row from the CSV

        Args:
            row: Dictionary of column name -> value
            row_num: Row number for error reporting

        Returns:
            SongEntry or None if invalid
        """
        # Normalize keys to lowercase
        normalized_row = {k.lower().strip(): v for k, v in row.items()}

        song = normalized_row.get('song', '').strip()
        artist = normalized_row.get('artist', '').strip()

        if not song:
            warning = f"Row {row_num}: Empty song name, skipping"
            logging.warning(warning)
            return None

        if not artist:
            warning = f"Row {row_num}: Empty artist name for '{song}', skipping"
            logging.warning(warning)
            return None

        return SongEntry(song=song, artist=artist, row_number=row_num)
