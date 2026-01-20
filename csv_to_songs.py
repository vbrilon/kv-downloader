#!/usr/bin/env python3
"""
CSV to songs.yaml Converter

Reads a CSV file with song/artist pairs, searches karaoke-version.com,
and generates a songs.yaml file with matching URLs.

Usage:
    python csv_to_songs.py list.csv
    python csv_to_songs.py list.csv --output my_songs.yaml
    python csv_to_songs.py list.csv --debug     # Visible browser
    python csv_to_songs.py list.csv --dry-run   # Search without writing files
"""

import argparse
import logging
import sys
from pathlib import Path

from packages.browser import ChromeManager
from packages.csv_converter import (
    CSVReader,
    ArtistNormalizer,
    SiteSearcher,
    MatchScorer,
    YAMLWriter,
    ReportGenerator
)
from packages.csv_converter.yaml_writer import SongConfig
from packages.csv_converter.match_scorer import MatchConfidence


def setup_logging(debug: bool = False):
    """Configure logging for the application"""
    level = logging.DEBUG if debug else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s' if debug else '%(message)s'

    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Convert CSV song list to songs.yaml for karaoke-version.com',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python csv_to_songs.py list.csv
    python csv_to_songs.py list.csv --output my_songs.yaml
    python csv_to_songs.py list.csv --debug
    python csv_to_songs.py list.csv --dry-run
        '''
    )

    parser.add_argument(
        'csv_file',
        help='Path to CSV file with Song,Artist columns'
    )

    parser.add_argument(
        '--output', '-o',
        default='songs_generated.yaml',
        help='Output YAML file path (default: songs_generated.yaml)'
    )

    parser.add_argument(
        '--report', '-r',
        default='unmatched_songs.txt',
        help='Unmatched songs report path (default: unmatched_songs.txt)'
    )

    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Run in debug mode with visible browser'
    )

    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Search only, do not write output files'
    )

    parser.add_argument(
        '--high-threshold',
        type=float,
        default=0.85,
        help='Minimum score for high confidence match (default: 0.85)'
    )

    parser.add_argument(
        '--medium-threshold',
        type=float,
        default=0.70,
        help='Minimum score for medium confidence match (default: 0.70)'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    setup_logging(args.debug)

    # Validate input file exists
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        logging.error(f"CSV file not found: {csv_path}")
        sys.exit(1)

    logging.info("=" * 60)
    logging.info("CSV to songs.yaml Converter")
    logging.info("=" * 60)

    # Initialize components
    csv_reader = CSVReader(args.csv_file)
    normalizer = ArtistNormalizer()
    scorer = MatchScorer(
        high_threshold=args.high_threshold,
        medium_threshold=args.medium_threshold
    )
    yaml_writer = YAMLWriter(args.output)
    report_generator = ReportGenerator(args.report)

    # Read CSV
    logging.info(f"\nReading CSV file: {args.csv_file}")
    entries = csv_reader.read()

    if not entries:
        logging.error("No valid entries found in CSV file")
        if csv_reader.errors:
            for error in csv_reader.errors:
                logging.error(f"  {error}")
        sys.exit(1)

    logging.info(f"Found {len(entries)} songs to process")

    # Initialize browser (headless unless debug mode)
    headless = not args.debug
    logging.info(f"\nStarting browser (headless={headless})...")

    chrome_manager = ChromeManager(headless=headless)
    chrome_manager.setup_driver()
    searcher = SiteSearcher(chrome_manager)

    matched_songs = []
    try:
        logging.info("\nSearching for songs...")
        logging.info("-" * 40)

        for i, entry in enumerate(entries, 1):
            logging.info(f"\n[{i}/{len(entries)}] Searching: {entry.song} by {entry.artist}")

            # Normalize artist name for better search
            normalized_artist = normalizer.normalize(entry.artist)
            if normalized_artist != entry.artist:
                logging.info(f"  Artist normalized: {entry.artist} -> {normalized_artist}")

            # Search for the song
            results = searcher.search(entry.song, normalized_artist)

            if not results:
                logging.warning(f"  No results found")
                report_generator.add_unmatched(
                    entry.song,
                    entry.artist,
                    "No search results returned"
                )
                continue

            # Score results and find best match
            result_dicts = [searcher.get_result_as_dict(r) for r in results]
            best_match = scorer.find_best_match(entry.song, normalized_artist, result_dicts)

            if not best_match:
                logging.warning(f"  No acceptable match found")
                report_generator.add_unmatched(
                    entry.song,
                    entry.artist,
                    f"Best result had low confidence"
                )
                continue

            # Handle based on confidence level
            if best_match.confidence == MatchConfidence.HIGH:
                logging.info(f"  HIGH match ({best_match.combined_score:.0%}): {best_match.result_url}")
                matched_songs.append(SongConfig(url=best_match.result_url))

            elif best_match.confidence == MatchConfidence.MEDIUM:
                logging.info(f"  MEDIUM match ({best_match.combined_score:.0%}): {best_match.result_url}")
                logging.info(f"    Found: {best_match.result_song} by {best_match.result_artist}")
                matched_songs.append(SongConfig(url=best_match.result_url))
                report_generator.add_partial_match(best_match)

            else:  # LOW
                logging.warning(f"  LOW match ({best_match.combined_score:.0%}), skipping")
                logging.warning(f"    Best was: {best_match.result_song} by {best_match.result_artist}")
                report_generator.add_low_confidence_match(best_match)

    finally:
        # Always clean up browser
        logging.info("\nClosing browser...")
        chrome_manager.quit()

    # Write outputs
    logging.info("\n" + "=" * 60)
    logging.info("RESULTS")
    logging.info("=" * 60)

    logging.info(f"\nMatched songs: {len(matched_songs)}/{len(entries)}")

    if args.dry_run:
        logging.info("\nDry run mode - not writing files")
        if matched_songs:
            logging.info("\nYAML Preview:")
            logging.info("-" * 40)
            print(yaml_writer.preview(matched_songs))
    else:
        # Write YAML file
        if matched_songs:
            yaml_writer.write(matched_songs)
            logging.info(f"Wrote: {args.output}")

        # Write report if there are issues
        if report_generator.has_issues():
            report_generator.write()
            logging.info(f"Wrote: {args.report}")

    # Summary
    logging.info("\n" + "-" * 40)
    logging.info(report_generator.get_summary())

    if matched_songs:
        logging.info(f"\nNext steps:")
        logging.info(f"  1. Review {args.output}")
        if report_generator.has_issues():
            logging.info(f"  2. Check {args.report} for manual lookups")
        logging.info(f"  3. Rename to songs.yaml and run the downloader")

    sys.exit(0 if matched_songs else 1)


if __name__ == '__main__':
    main()
