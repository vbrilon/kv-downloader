"""
Performance Baseline Testing System
A/B configuration testing to isolate performance regression sources
"""

import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from ..utils import get_profiler


@dataclass
class ConfigurationBaseline:
    """Configuration baseline for A/B testing"""
    name: str
    description: str
    
    # Track Management Timing (PRIMARY SUSPECTS)
    solo_activation_delay: float
    solo_activation_delay_simple: float  
    solo_activation_delay_complex: float
    
    # Download Management Timing (CRITICAL PATH)
    download_monitoring_initial_wait: int
    download_check_interval: int
    download_max_wait: int
    
    # Other timing parameters
    between_tracks_pause: float
    webdriver_default_timeout: int


# Pre-defined configuration baselines
BASELINE_CONFIGURATIONS = {
    "current": ConfigurationBaseline(
        name="current",
        description="Current configuration with performance optimizations (suspected regression source)",
        solo_activation_delay=12.0,
        solo_activation_delay_simple=15.0,
        solo_activation_delay_complex=21.0,
        download_monitoring_initial_wait=30,
        download_check_interval=5,
        download_max_wait=90,
        between_tracks_pause=0.5,
        webdriver_default_timeout=10
    ),
    
    "pre_optimization": ConfigurationBaseline(
        name="pre_optimization", 
        description="Pre-optimization baseline (before 2x regression)",
        solo_activation_delay=5.0,
        solo_activation_delay_simple=5.0,
        solo_activation_delay_complex=5.0,
        download_monitoring_initial_wait=0,
        download_check_interval=2,
        download_max_wait=300,
        between_tracks_pause=2.0,
        webdriver_default_timeout=10
    ),
    
    "solo_only": ConfigurationBaseline(
        name="solo_only",
        description="Test solo activation delay impact only",
        solo_activation_delay=5.0,  # Revert to original
        solo_activation_delay_simple=5.0,  # Revert to original
        solo_activation_delay_complex=5.0,  # Revert to original
        download_monitoring_initial_wait=30,  # Keep current
        download_check_interval=5,  # Keep current
        download_max_wait=90,  # Keep current
        between_tracks_pause=0.5,
        webdriver_default_timeout=10
    ),
    
    "download_only": ConfigurationBaseline(
        name="download_only",
        description="Test download monitoring impact only",
        solo_activation_delay=12.0,  # Keep current
        solo_activation_delay_simple=15.0,  # Keep current
        solo_activation_delay_complex=21.0,  # Keep current
        download_monitoring_initial_wait=0,  # Revert to original
        download_check_interval=2,  # Revert to original
        download_max_wait=300,  # Revert to original
        between_tracks_pause=0.5,
        webdriver_default_timeout=10
    )
}


class PerformanceBaselineTester:
    """
    A/B performance testing system for configuration comparison
    """
    
    def __init__(self):
        self.results = {}
        self.current_baseline = None
        self.test_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = Path("logs/performance/baselines")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Store original configuration values
        self._original_config = {}
        
    def list_available_baselines(self) -> Dict[str, str]:
        """List all available configuration baselines"""
        return {name: config.description for name, config in BASELINE_CONFIGURATIONS.items()}
    
    @contextmanager
    def baseline_configuration(self, baseline_name: str):
        """
        Context manager for temporarily applying a baseline configuration
        Automatically restores original configuration when exiting
        """
        if baseline_name not in BASELINE_CONFIGURATIONS:
            raise ValueError(f"Unknown baseline: {baseline_name}. Available: {list(BASELINE_CONFIGURATIONS.keys())}")
        
        baseline = BASELINE_CONFIGURATIONS[baseline_name]
        self.current_baseline = baseline_name
        
        logging.info(f"🔄 Applying baseline configuration: {baseline_name}")
        logging.info(f"   Description: {baseline.description}")
        
        try:
            # Apply baseline configuration
            self._apply_baseline_configuration(baseline)
            yield baseline
            
        finally:
            # Restore original configuration
            self._restore_original_configuration()
            self.current_baseline = None
            logging.info(f"✅ Restored original configuration")
    
    def _apply_baseline_configuration(self, baseline: ConfigurationBaseline):
        """Apply a baseline configuration by modifying the config module"""
        # Import config module dynamically to modify it
        from packages.configuration import config
        
        # Store original values for restoration
        config_changes = {
            'SOLO_ACTIVATION_DELAY': baseline.solo_activation_delay,
            'SOLO_ACTIVATION_DELAY_SIMPLE': baseline.solo_activation_delay_simple,
            'SOLO_ACTIVATION_DELAY_COMPLEX': baseline.solo_activation_delay_complex,
            'DOWNLOAD_MONITORING_INITIAL_WAIT': baseline.download_monitoring_initial_wait,
            'DOWNLOAD_CHECK_INTERVAL': baseline.download_check_interval,
            'DOWNLOAD_MAX_WAIT': baseline.download_max_wait,
            'BETWEEN_TRACKS_PAUSE': baseline.between_tracks_pause,
            'WEBDRIVER_DEFAULT_TIMEOUT': baseline.webdriver_default_timeout
        }
        
        # Store originals if not already stored
        if not self._original_config:
            for key in config_changes:
                if hasattr(config, key):
                    self._original_config[key] = getattr(config, key)
        
        # Apply new configuration
        for key, value in config_changes.items():
            if hasattr(config, key):
                old_value = getattr(config, key)
                setattr(config, key, value)
                logging.debug(f"   {key}: {old_value} → {value}")
        
        # Log summary of key changes
        logging.info(f"   Solo delays: {baseline.solo_activation_delay}s/{baseline.solo_activation_delay_simple}s/{baseline.solo_activation_delay_complex}s")
        logging.info(f"   Download monitoring: {baseline.download_monitoring_initial_wait}s initial wait, {baseline.download_check_interval}s intervals")
    
    def _restore_original_configuration(self):
        """Restore original configuration values"""
        if not self._original_config:
            return
            
        from packages.configuration import config
        
        for key, original_value in self._original_config.items():
            if hasattr(config, key):
                setattr(config, key, original_value)
                logging.debug(f"   Restored {key} to {original_value}")
    
    def run_baseline_test(self, baseline_name: str, test_songs: List[str] = None, max_tracks_per_song: int = 3) -> Dict:
        """
        Run a complete baseline test with the specified configuration
        
        Args:
            baseline_name: Name of baseline configuration to test
            test_songs: List of song URLs to test (uses config if None)
            max_tracks_per_song: Maximum tracks to download per song for testing
            
        Returns:
            Dictionary containing timing results and performance metrics
        """
        if baseline_name not in BASELINE_CONFIGURATIONS:
            raise ValueError(f"Unknown baseline: {baseline_name}")
        
        baseline = BASELINE_CONFIGURATIONS[baseline_name]
        
        # Ensure profiling is enabled
        profiler = get_profiler()
        if not profiler.enabled:
            logging.warning("⚠️ Profiler not enabled - baseline test will not collect detailed timing data")
        
        logging.info(f"🚀 Starting baseline test: {baseline_name}")
        logging.info(f"   Description: {baseline.description}")
        
        test_start_time = time.time()
        
        with self.baseline_configuration(baseline_name) as config:
            # Import and run automator with current baseline
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from karaoke_automator import KaraokeVersionAutomator
            
            try:
                # Create automator with profiling enabled
                automator = KaraokeVersionAutomator(
                    headless=True,  # Use headless for consistent timing
                    show_progress=False,  # Disable progress display for cleaner logs
                    enable_profiling=True
                )
                
                # Load songs configuration
                songs = automator.load_songs_config()
                if test_songs:
                    # Filter to test songs only
                    songs = [song for song in songs if song['url'] in test_songs]
                
                if not songs:
                    logging.error("No songs available for baseline testing")
                    return None
                
                # Limit tracks per song for faster testing
                test_results = self._run_limited_automation_test(
                    automator, 
                    songs, 
                    max_tracks_per_song=max_tracks_per_song,
                    baseline_name=baseline_name
                )
                
                test_duration = time.time() - test_start_time
                
                # Collect profiling data
                performance_data = {
                    'baseline_name': baseline_name,
                    'baseline_description': baseline.description,
                    'configuration': asdict(config),
                    'test_duration': test_duration,
                    'songs_tested': len(songs),
                    'max_tracks_per_song': max_tracks_per_song,
                    'test_timestamp': datetime.now().isoformat(),
                    'test_results': test_results
                }
                
                # Add profiling report if available
                if profiler.enabled:
                    performance_data['profiling_report'] = profiler.generate_performance_report()
                    performance_data['detailed_timing'] = profiler.timing_data
                
                # Store results
                self.results[baseline_name] = performance_data
                
                # Save results to file
                self._save_baseline_results(baseline_name, performance_data)
                
                logging.info(f"✅ Baseline test completed: {baseline_name}")
                logging.info(f"   Total duration: {test_duration:.2f}s")
                logging.info(f"   Songs tested: {len(songs)}")
                
                return performance_data
                
            except Exception as e:
                logging.error(f"❌ Baseline test failed for {baseline_name}: {e}")
                return None
            finally:
                # Clean up automator resources
                if 'automator' in locals() and automator:
                    try:
                        if hasattr(automator, 'chrome_manager') and automator.chrome_manager:
                            automator.chrome_manager.quit()
                    except Exception as cleanup_e:
                        logging.debug(f"Cleanup error: {cleanup_e}")
    
    def _run_limited_automation_test(self, automator, songs: List[Dict], max_tracks_per_song: int, baseline_name: str) -> Dict:
        """Run limited automation test for baseline comparison"""
        test_results = {
            'songs_processed': 0,
            'tracks_processed': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'errors': []
        }
        
        # Setup automation session
        if not automator.login():
            test_results['errors'].append("Login failed")
            return test_results
        
        # Process each song with limited tracks
        for song in songs:
            try:
                logging.info(f"📊 Testing song: {song.get('name', 'Unknown')}")
                
                # Get available tracks
                tracks = automator.get_available_tracks(song['url'])
                if not tracks:
                    test_results['errors'].append(f"No tracks found for {song['url']}")
                    continue
                
                # Limit tracks for testing
                test_tracks = tracks[:max_tracks_per_song]
                logging.info(f"   Testing {len(test_tracks)} of {len(tracks)} tracks")
                
                # Process limited tracks
                song_key = song.get('key', 0)
                for track in test_tracks:
                    try:
                        track_start_time = time.time()
                        
                        # Solo the track
                        if automator.solo_track(track, song['url']):
                            # Attempt download (simplified for testing)
                            success = automator.download_manager.download_current_mix(
                                song['url'],
                                automator.sanitize_filename(track['name']),
                                cleanup_existing=False,
                                song_folder=song.get('name'),
                                key_adjustment=song_key,
                                track_index=track['index']
                            )
                            
                            if success:
                                test_results['successful_downloads'] += 1
                            else:
                                test_results['failed_downloads'] += 1
                                
                            test_results['tracks_processed'] += 1
                            
                        else:
                            test_results['failed_downloads'] += 1
                            test_results['errors'].append(f"Failed to solo track {track['name']}")
                            
                        track_duration = time.time() - track_start_time
                        logging.info(f"   Track {track['name']}: {track_duration:.2f}s")
                        
                    except Exception as track_e:
                        test_results['failed_downloads'] += 1
                        test_results['errors'].append(f"Track {track['name']} error: {str(track_e)}")
                        logging.error(f"Track processing error: {track_e}")
                
                # Clear solos after song
                automator.clear_all_solos(song['url'])
                test_results['songs_processed'] += 1
                
            except Exception as song_e:
                test_results['errors'].append(f"Song {song['url']} error: {str(song_e)}")
                logging.error(f"Song processing error: {song_e}")
        
        return test_results
    
    def _save_baseline_results(self, baseline_name: str, performance_data: Dict):
        """Save baseline test results to file"""
        filename = self.results_dir / f"baseline_{baseline_name}_{self.test_session_id}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(performance_data, f, indent=2, default=str)
            
            logging.info(f"📁 Baseline results saved: {filename}")
            
        except Exception as e:
            logging.error(f"Failed to save baseline results: {e}")
    
    def compare_baselines(self, baseline_names: List[str]) -> str:
        """Generate comparison report between baselines"""
        if not all(name in self.results for name in baseline_names):
            missing = [name for name in baseline_names if name not in self.results]
            logging.error(f"Missing baseline results: {missing}")
            return "Cannot generate comparison - missing baseline results"
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("📊 BASELINE PERFORMANCE COMPARISON")
        report_lines.append("=" * 80)
        
        # Summary table
        report_lines.append("\n🕒 TIMING SUMMARY")
        report_lines.append("-" * 60)
        
        for baseline_name in baseline_names:
            result = self.results[baseline_name]
            config = result['configuration']
            
            report_lines.append(f"\n{baseline_name.upper()}:")
            report_lines.append(f"  Description: {result['baseline_description']}")
            report_lines.append(f"  Total Duration: {result['test_duration']:.2f}s")
            report_lines.append(f"  Songs/Tracks: {result['songs_tested']}/{result['test_results']['tracks_processed']}")
            report_lines.append(f"  Success Rate: {result['test_results']['successful_downloads']}/{result['test_results']['tracks_processed']}")
            
            # Key configuration differences
            report_lines.append(f"  Solo Delays: {config['solo_activation_delay']}s/{config['solo_activation_delay_simple']}s/{config['solo_activation_delay_complex']}s")
            report_lines.append(f"  Download: {config['download_monitoring_initial_wait']}s initial, {config['download_check_interval']}s intervals")
        
        # Performance differential analysis
        if len(baseline_names) == 2:
            baseline1, baseline2 = baseline_names
            duration1 = self.results[baseline1]['test_duration']
            duration2 = self.results[baseline2]['test_duration']
            
            if duration1 > 0:
                speed_ratio = duration2 / duration1
                report_lines.append(f"\n📈 PERFORMANCE DIFFERENTIAL")
                report_lines.append("-" * 40)
                report_lines.append(f"{baseline2} vs {baseline1}: {speed_ratio:.2f}x speed")
                
                if speed_ratio < 1:
                    improvement = (1 - speed_ratio) * 100
                    report_lines.append(f"{baseline2} is {improvement:.1f}% faster than {baseline1}")
                else:
                    regression = (speed_ratio - 1) * 100
                    report_lines.append(f"{baseline2} is {regression:.1f}% slower than {baseline1}")
        
        return "\n".join(report_lines)
    
    def generate_recommendations(self) -> str:
        """Generate performance optimization recommendations based on baseline testing"""
        if not self.results:
            return "No baseline results available for recommendations"
        
        recommendations = []
        recommendations.append("🎯 PERFORMANCE OPTIMIZATION RECOMMENDATIONS")
        recommendations.append("=" * 50)
        
        # Analyze results to generate recommendations
        fastest_baseline = min(self.results.keys(), key=lambda k: self.results[k]['test_duration'])
        slowest_baseline = max(self.results.keys(), key=lambda k: self.results[k]['test_duration'])
        
        if fastest_baseline != slowest_baseline:
            fast_config = BASELINE_CONFIGURATIONS[fastest_baseline]
            slow_config = BASELINE_CONFIGURATIONS[slowest_baseline]
            
            recommendations.append(f"\n✅ FASTEST: {fastest_baseline}")
            recommendations.append(f"❌ SLOWEST: {slowest_baseline}")
            
            # Solo activation analysis
            if (fast_config.solo_activation_delay_simple < slow_config.solo_activation_delay_simple):
                recommendations.append(f"\n🎵 SOLO ACTIVATION OPTIMIZATION:")
                recommendations.append(f"  Reduce solo delays from {slow_config.solo_activation_delay_simple}s to {fast_config.solo_activation_delay_simple}s")
                recommendations.append(f"  Potential impact: Major performance improvement for track isolation")
            
            # Download monitoring analysis  
            if (fast_config.download_monitoring_initial_wait < slow_config.download_monitoring_initial_wait):
                recommendations.append(f"\n💾 DOWNLOAD MONITORING OPTIMIZATION:")
                recommendations.append(f"  Reduce initial wait from {slow_config.download_monitoring_initial_wait}s to {fast_config.download_monitoring_initial_wait}s")
                recommendations.append(f"  Potential impact: Faster download detection and processing")
        
        return "\n".join(recommendations)


# Convenience functions for easy testing
def run_ab_test(baseline_a: str = "pre_optimization", baseline_b: str = "current", max_tracks: int = 2) -> str:
    """
    Run A/B test between two baselines and return comparison report
    
    Args:
        baseline_a: First baseline to test
        baseline_b: Second baseline to test  
        max_tracks: Maximum tracks per song for faster testing
        
    Returns:
        Formatted comparison report
    """
    tester = PerformanceBaselineTester()
    
    logging.info(f"🔬 Starting A/B test: {baseline_a} vs {baseline_b}")
    
    # Run both baseline tests
    result_a = tester.run_baseline_test(baseline_a, max_tracks_per_song=max_tracks)
    result_b = tester.run_baseline_test(baseline_b, max_tracks_per_song=max_tracks)
    
    if result_a and result_b:
        comparison = tester.compare_baselines([baseline_a, baseline_b])
        recommendations = tester.generate_recommendations()
        
        return f"{comparison}\n\n{recommendations}"
    else:
        return "A/B test failed - check logs for details"


def list_baselines() -> None:
    """List all available baseline configurations"""
    tester = PerformanceBaselineTester()
    baselines = tester.list_available_baselines()
    
    print("📋 AVAILABLE BASELINE CONFIGURATIONS")
    print("=" * 50)
    for name, description in baselines.items():
        print(f"{name:15}: {description}")


def quick_regression_test() -> str:
    """Quick regression test comparing current vs pre-optimization"""
    return run_ab_test("pre_optimization", "current", max_tracks=1)