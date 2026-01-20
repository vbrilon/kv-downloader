"""Artist name normalization and abbreviation expansion"""

import logging
from typing import Dict, Optional


class ArtistNormalizer:
    """Normalizes artist names by expanding abbreviations"""

    # Dictionary of common artist abbreviations
    ABBREVIATIONS: Dict[str, str] = {
        # Rock bands
        'rhcp': 'Red Hot Chili Peppers',
        'gnr': "Guns N' Roses",
        'ccr': 'Creedence Clearwater Revival',
        'acdc': 'AC/DC',
        'ac/dc': 'AC/DC',
        'zz top': 'ZZ Top',
        'elo': 'Electric Light Orchestra',
        'rem': 'R.E.M.',
        'r.e.m.': 'R.E.M.',
        'stp': 'Stone Temple Pilots',
        'lz': 'Led Zeppelin',
        'bto': 'Bachman-Turner Overdrive',

        # Solo artists with common abbreviations
        'ozzy': 'Ozzy Osbourne',
        'bruce': 'Bruce Springsteen',
        'prince': 'Prince',
        'bowie': 'David Bowie',
        'jimi': 'Jimi Hendrix',
        'stevie': 'Stevie Wonder',
        'elton': 'Elton John',

        # Pop/Modern
        'jt': 'Justin Timberlake',
        'bieber': 'Justin Bieber',
        'beyonce': 'Beyoncé',
        'gaga': 'Lady Gaga',
        'bruno': 'Bruno Mars',

        # Hip-hop
        'jay-z': 'JAY-Z',
        'jayz': 'JAY-Z',
        'eminem': 'Eminem',
        'dre': 'Dr. Dre',
        'snoop': 'Snoop Dogg',

        # Country
        'johnny': 'Johnny Cash',
        'willie': 'Willie Nelson',
        'dolly': 'Dolly Parton',

        # Other common variations
        'black keys': 'The Black Keys',
        'killers': 'The Killers',
        'strokes': 'The Strokes',
        'beatles': 'The Beatles',
        'stones': 'The Rolling Stones',
        'rolling stones': 'The Rolling Stones',
        'who': 'The Who',
        'doors': 'The Doors',
        'clash': 'The Clash',
        'cure': 'The Cure',
        'police': 'The Police',
        'eagles': 'Eagles',
        'fleetwood': 'Fleetwood Mac',
        'sabbath': 'Black Sabbath',
        'maiden': 'Iron Maiden',
        'priest': 'Judas Priest',
        'floyd': 'Pink Floyd',
        'zeppelin': 'Led Zeppelin',
        'petty': 'Tom Petty',
        'tom petty': 'Tom Petty and the Heartbreakers',
    }

    def __init__(self, custom_abbreviations: Optional[Dict[str, str]] = None):
        """
        Initialize the normalizer

        Args:
            custom_abbreviations: Additional abbreviations to use
        """
        self.abbreviations = self.ABBREVIATIONS.copy()
        if custom_abbreviations:
            self.abbreviations.update(custom_abbreviations)

    def normalize(self, artist: str) -> str:
        """
        Normalize an artist name by expanding abbreviations

        Args:
            artist: Raw artist name from CSV

        Returns:
            Normalized artist name
        """
        if not artist:
            return artist

        # Clean up the input
        cleaned = artist.strip()

        # Check for exact match (case-insensitive)
        lookup_key = cleaned.lower()
        if lookup_key in self.abbreviations:
            expanded = self.abbreviations[lookup_key]
            logging.debug(f"Expanded '{artist}' to '{expanded}'")
            return expanded

        # Handle "feat." or "/" in artist names
        if '/' in cleaned:
            # Handle collaborations like "Santana / Rob Thomas"
            parts = [p.strip() for p in cleaned.split('/')]
            normalized_parts = [self._normalize_single(p) for p in parts]
            return ' / '.join(normalized_parts)

        if 'feat.' in cleaned.lower() or 'ft.' in cleaned.lower():
            # Keep featuring artists as-is but normalize main artist
            import re
            match = re.match(r'^(.+?)\s*(feat\.|ft\.)\s*(.+)$', cleaned, re.IGNORECASE)
            if match:
                main_artist = self._normalize_single(match.group(1))
                featured = match.group(3)
                return f"{main_artist} feat. {featured}"

        return self._normalize_single(cleaned)

    def _normalize_single(self, artist: str) -> str:
        """
        Normalize a single artist name (no collaborations)

        Args:
            artist: Single artist name

        Returns:
            Normalized name
        """
        lookup_key = artist.lower().strip()
        if lookup_key in self.abbreviations:
            return self.abbreviations[lookup_key]
        return artist.strip()

    def get_search_variants(self, artist: str) -> list:
        """
        Get search variants for an artist name

        Args:
            artist: Artist name to generate variants for

        Returns:
            List of search variants to try
        """
        variants = [self.normalize(artist)]

        # Add original if different from normalized
        if artist != variants[0]:
            variants.append(artist)

        # Handle "The" prefix
        if variants[0].startswith('The '):
            variants.append(variants[0][4:])
        elif not variants[0].startswith('The '):
            # Try with "The" prefix for bands
            variants.append(f"The {variants[0]}")

        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for v in variants:
            if v.lower() not in seen:
                seen.add(v.lower())
                unique_variants.append(v)

        return unique_variants
