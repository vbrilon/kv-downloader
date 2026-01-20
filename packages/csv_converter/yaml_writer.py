"""YAML writer for songs configuration"""

import logging
from pathlib import Path
from typing import List
from dataclasses import dataclass

import yaml


@dataclass
class SongConfig:
    """Configuration for a single song"""
    url: str
    name: str = ""  # Optional, auto-extracted if empty
    key: int = 0    # Optional pitch adjustment


class YAMLWriter:
    """Writes songs configuration to YAML file"""

    DEFAULT_OUTPUT = "songs_generated.yaml"

    def __init__(self, output_path: str = None):
        """
        Initialize the YAML writer

        Args:
            output_path: Path for output file (default: songs_generated.yaml)
        """
        self.output_path = Path(output_path or self.DEFAULT_OUTPUT)

    def write(self, songs: List[SongConfig]) -> bool:
        """
        Write songs to YAML file

        Args:
            songs: List of SongConfig objects

        Returns:
            True if successful, False otherwise
        """
        if not songs:
            logging.warning("No songs to write")
            return False

        try:
            # Build the YAML structure
            yaml_data = self._build_yaml_structure(songs)

            # Write to file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    yaml_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False
                )

            logging.info(f"Wrote {len(songs)} songs to {self.output_path}")
            return True

        except Exception as e:
            logging.error(f"Error writing YAML file: {e}")
            return False

    def _build_yaml_structure(self, songs: List[SongConfig]) -> dict:
        """
        Build the YAML data structure

        Args:
            songs: List of SongConfig objects

        Returns:
            Dictionary for YAML output
        """
        song_entries = []

        for song in songs:
            entry = {'url': song.url}

            # Only include optional fields if they have non-default values
            if song.name:
                entry['name'] = song.name
            if song.key != 0:
                entry['key'] = song.key

            song_entries.append(entry)

        return {'songs': song_entries}

    def preview(self, songs: List[SongConfig]) -> str:
        """
        Generate a preview of the YAML output

        Args:
            songs: List of SongConfig objects

        Returns:
            YAML string preview
        """
        yaml_data = self._build_yaml_structure(songs)
        return yaml.dump(
            yaml_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

    @classmethod
    def from_match_results(cls, match_results: list, output_path: str = None) -> 'YAMLWriter':
        """
        Create a YAMLWriter and convert match results to songs

        Args:
            match_results: List of MatchResult objects
            output_path: Output file path

        Returns:
            YAMLWriter instance with songs prepared
        """
        writer = cls(output_path)
        writer.songs = [
            SongConfig(url=result.result_url)
            for result in match_results
            if result.is_high_confidence
        ]
        return writer
