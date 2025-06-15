"""Comprehensive final statistics reporting for karaoke automation"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Any
import json


class StatsReporter:
    """Track and report comprehensive statistics across all songs and tracks"""
    
    def __init__(self):
        """Initialize stats reporter"""
        self.session_start_time = time.time()
        self.songs_data = []
        self.total_tracks_attempted = 0
        self.total_tracks_completed = 0
        self.total_tracks_failed = 0
        self.total_download_time = 0
        self.errors_encountered = []
        
    def start_song(self, song_name: str, song_url: str, track_count: int):
        """Record the start of a new song processing"""
        song_data = {
            'name': song_name,
            'url': song_url,
            'start_time': time.time(),
            'end_time': None,
            'track_count': track_count,
            'tracks': [],
            'completed_tracks': 0,
            'failed_tracks': 0,
            'total_download_time': 0,
            'status': 'in_progress'
        }
        self.songs_data.append(song_data)
        logging.info(f"📊 Stats: Started tracking song '{song_name}' with {track_count} tracks")
        
    def record_track_start(self, song_name: str, track_name: str, track_index: int):
        """Record the start of a track download"""
        song_data = self._get_current_song_data(song_name)
        if song_data:
            track_data = {
                'name': track_name,
                'index': track_index,
                'start_time': time.time(),
                'end_time': None,
                'status': 'in_progress',
                'download_time': 0,
                'error_message': None,
                'file_size': 0
            }
            song_data['tracks'].append(track_data)
            self.total_tracks_attempted += 1
            
    def record_track_completion(self, song_name: str, track_name: str, success: bool, 
                              error_message: str = None, file_size: int = 0):
        """Record the completion of a track download"""
        song_data = self._get_current_song_data(song_name)
        track_data = self._get_track_data(song_data, track_name) if song_data else None
        
        if track_data:
            track_data['end_time'] = time.time()
            track_data['download_time'] = track_data['end_time'] - track_data['start_time']
            track_data['status'] = 'completed' if success else 'failed'
            track_data['error_message'] = error_message
            track_data['file_size'] = file_size
            
            # Update song-level stats
            if success:
                song_data['completed_tracks'] += 1
                self.total_tracks_completed += 1
            else:
                song_data['failed_tracks'] += 1
                self.total_tracks_failed += 1
                if error_message:
                    self.errors_encountered.append({
                        'song': song_name,
                        'track': track_name,
                        'error': error_message,
                        'timestamp': time.time()
                    })
            
            song_data['total_download_time'] += track_data['download_time']
            self.total_download_time += track_data['download_time']
            
            logging.debug(f"📊 Stats: Track '{track_name}' {'completed' if success else 'failed'} "
                         f"in {track_data['download_time']:.1f}s")
    
    def finish_song(self, song_name: str):
        """Mark a song as completed and calculate final stats"""
        song_data = self._get_current_song_data(song_name)
        if song_data:
            song_data['end_time'] = time.time()
            song_data['total_time'] = song_data['end_time'] - song_data['start_time']
            
            # Determine overall song status
            if song_data['failed_tracks'] == 0:
                song_data['status'] = 'completed'
            elif song_data['completed_tracks'] > 0:
                song_data['status'] = 'partial'
            else:
                song_data['status'] = 'failed'
                
            logging.info(f"📊 Stats: Finished song '{song_name}' - "
                        f"{song_data['completed_tracks']}/{song_data['track_count']} tracks completed "
                        f"in {song_data['total_time']:.1f}s")
    
    def generate_final_report(self) -> str:
        """Generate comprehensive final statistics report"""
        session_duration = time.time() - self.session_start_time
        
        # Calculate overall statistics
        total_songs = len(self.songs_data)
        completed_songs = sum(1 for s in self.songs_data if s['status'] == 'completed')
        partial_songs = sum(1 for s in self.songs_data if s['status'] == 'partial')
        failed_songs = sum(1 for s in self.songs_data if s['status'] == 'failed')
        
        success_rate = (self.total_tracks_completed / self.total_tracks_attempted * 100) if self.total_tracks_attempted > 0 else 0
        avg_track_time = (self.total_download_time / self.total_tracks_completed) if self.total_tracks_completed > 0 else 0
        
        # Build the report
        report_lines = []
        report_lines.append("🎉 KARAOKE AUTOMATION - FINAL STATISTICS REPORT")
        report_lines.append("=" * 80)
        
        # Session Overview
        report_lines.append("\n📊 SESSION OVERVIEW")
        report_lines.append("-" * 40)
        report_lines.append(f"⏱️  Total Session Time: {self._format_duration(session_duration)}")
        report_lines.append(f"🎵 Songs Processed: {total_songs}")
        report_lines.append(f"🎼 Tracks Attempted: {self.total_tracks_attempted}")
        report_lines.append(f"✅ Tracks Completed: {self.total_tracks_completed}")
        report_lines.append(f"❌ Tracks Failed: {self.total_tracks_failed}")
        report_lines.append(f"📈 Overall Success Rate: {success_rate:.1f}%")
        report_lines.append(f"⚡ Average Track Time: {avg_track_time:.1f}s")
        
        # Song Summary
        report_lines.append("\n🎵 SONG SUMMARY")
        report_lines.append("-" * 40)
        report_lines.append(f"✅ Fully Completed: {completed_songs}")
        report_lines.append(f"⚠️  Partially Completed: {partial_songs}")
        report_lines.append(f"❌ Failed: {failed_songs}")
        
        # Detailed Song Results
        report_lines.append("\n📋 DETAILED SONG RESULTS")
        report_lines.append("-" * 40)
        
        for song in self.songs_data:
            status_icon = {"completed": "✅", "partial": "⚠️", "failed": "❌"}.get(song['status'], "❓")
            song_duration = song.get('total_time', 0)
            
            report_lines.append(f"\n{status_icon} {song['name']}")
            report_lines.append(f"   📊 Tracks: {song['completed_tracks']}/{song['track_count']} completed")
            report_lines.append(f"   ⏱️  Time: {self._format_duration(song_duration)}")
            report_lines.append(f"   🔗 URL: {song['url']}")
            
            # Show failed tracks if any
            failed_tracks = [t for t in song['tracks'] if t['status'] == 'failed']
            if failed_tracks:
                report_lines.append(f"   ❌ Failed tracks:")
                for track in failed_tracks:
                    error_msg = track.get('error_message', 'Unknown error')
                    report_lines.append(f"      • {track['name']}: {error_msg}")
        
        # Performance Insights
        report_lines.append("\n⚡ PERFORMANCE INSIGHTS")
        report_lines.append("-" * 40)
        
        if self.songs_data:
            # Find fastest and slowest tracks
            all_completed_tracks = []
            for song in self.songs_data:
                all_completed_tracks.extend([t for t in song['tracks'] if t['status'] == 'completed'])
            
            if all_completed_tracks:
                fastest_track = min(all_completed_tracks, key=lambda t: t['download_time'])
                slowest_track = max(all_completed_tracks, key=lambda t: t['download_time'])
                
                report_lines.append(f"🚀 Fastest Download: {fastest_track['name']} ({fastest_track['download_time']:.1f}s)")
                report_lines.append(f"🐌 Slowest Download: {slowest_track['name']} ({slowest_track['download_time']:.1f}s)")
            
            # Calculate efficiency metrics
            overhead_time = session_duration - self.total_download_time
            efficiency = (self.total_download_time / session_duration * 100) if session_duration > 0 else 0
            
            report_lines.append(f"📊 Download Time: {self._format_duration(self.total_download_time)}")
            report_lines.append(f"⚙️  Overhead Time: {self._format_duration(overhead_time)}")
            report_lines.append(f"📈 Efficiency: {efficiency:.1f}% (download time / total time)")
        
        # Error Summary
        if self.errors_encountered:
            report_lines.append("\n🚨 ERROR SUMMARY")
            report_lines.append("-" * 40)
            
            # Group errors by type
            error_types = {}
            for error in self.errors_encountered:
                error_msg = error['error']
                if error_msg in error_types:
                    error_types[error_msg] += 1
                else:
                    error_types[error_msg] = 1
            
            for error_msg, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                report_lines.append(f"❌ {error_msg}: {count} occurrences")
        
        # Final Summary
        report_lines.append("\n🎯 FINAL SUMMARY")
        report_lines.append("-" * 40)
        
        if success_rate >= 90:
            report_lines.append("🎉 EXCELLENT! Automation performed exceptionally well.")
        elif success_rate >= 75:
            report_lines.append("👍 GOOD! Automation performed well with minor issues.")
        elif success_rate >= 50:
            report_lines.append("⚠️  MODERATE! Automation had significant issues but completed some tracks.")
        else:
            report_lines.append("❌ POOR! Automation encountered major problems.")
        
        report_lines.append(f"📊 {self.total_tracks_completed}/{self.total_tracks_attempted} tracks successfully downloaded")
        report_lines.append(f"⏱️  Total session completed in {self._format_duration(session_duration)}")
        
        return "\n".join(report_lines)
    
    def save_detailed_report(self, output_file: str = "automation_stats.json"):
        """Save detailed statistics to JSON file"""
        try:
            stats_data = {
                'session_metadata': {
                    'start_time': self.session_start_time,
                    'end_time': time.time(),
                    'duration': time.time() - self.session_start_time,
                    'total_tracks_attempted': self.total_tracks_attempted,
                    'total_tracks_completed': self.total_tracks_completed,
                    'total_tracks_failed': self.total_tracks_failed,
                    'success_rate': (self.total_tracks_completed / self.total_tracks_attempted * 100) if self.total_tracks_attempted > 0 else 0,
                    'total_download_time': self.total_download_time
                },
                'songs': self.songs_data,
                'errors': self.errors_encountered
            }
            
            with open(output_file, 'w') as f:
                json.dump(stats_data, f, indent=2, default=str)
            
            logging.info(f"📊 Detailed statistics saved to: {output_file}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save statistics report: {e}")
            return False
    
    def _get_current_song_data(self, song_name: str) -> Dict[str, Any]:
        """Get the data for the current song"""
        for song in reversed(self.songs_data):  # Search from most recent
            if song['name'] == song_name:
                return song
        return None
    
    def _get_track_data(self, song_data: Dict[str, Any], track_name: str) -> Dict[str, Any]:
        """Get the data for a specific track within a song"""
        if not song_data:
            return None
        for track in reversed(song_data['tracks']):  # Search from most recent
            if track['name'] == track_name:
                return track
        return None
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            remaining_seconds = seconds % 60
            return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"