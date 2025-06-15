"""Progress tracking and display for karaoke track downloads"""

import time
import os
import threading
import logging


class ProgressTracker:
    """Track and display download progress for tracks"""
    
    def __init__(self):
        """Initialize progress tracker"""
        self.tracks = []
        self.current_song = ""
        self.lock = threading.Lock()
        self._display_thread = None
        self._stop_display = False
    
    def start_song(self, song_name, track_list):
        """Initialize progress tracking for a new song"""
        with self.lock:
            self.current_song = song_name
            self.tracks = []
            
            for track in track_list:
                self.tracks.append({
                    'name': track['name'],
                    'index': track['index'],
                    'status': 'pending',
                    'progress': 0,
                    'file_size': 0,
                    'downloaded': 0,
                    'start_time': None,
                    'end_time': None
                })
        
        # Start display thread
        self._stop_display = False
        self._display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self._display_thread.start()
        
        self._update_display()
    
    def update_track_status(self, track_index, status, progress=None, downloaded=None, file_size=None):
        """Update status of a specific track"""
        with self.lock:
            for track in self.tracks:
                # Handle both string and integer track indexes
                if str(track['index']) == str(track_index):
                    track['status'] = status
                    if progress is not None:
                        track['progress'] = min(100, max(0, progress))
                    if downloaded is not None:
                        track['downloaded'] = downloaded
                    if file_size is not None:
                        track['file_size'] = file_size
                    if status == 'downloading' and track['start_time'] is None:
                        track['start_time'] = time.time()
                    elif status in ['completed', 'failed'] and track['end_time'] is None:
                        track['end_time'] = time.time()
                    break
        
        self._update_display()
    
    def finish_song(self):
        """Complete progress tracking for current song"""
        self._stop_display = True
        if self._display_thread:
            self._display_thread.join(timeout=1)
        self._final_display()
    
    def _display_loop(self):
        """Background thread to update display periodically"""
        while not self._stop_display:
            time.sleep(0.5)  # Update every 500ms
            if not self._stop_display:
                self._update_display()
    
    def _update_display(self):
        """Update the progress display"""
        with self.lock:
            # Clear screen and show progress
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(f"🎵 Downloading: {self.current_song}")
            print("=" * 80)
            
            completed = sum(1 for t in self.tracks if t['status'] == 'completed')
            failed = sum(1 for t in self.tracks if t['status'] == 'failed')
            total = len(self.tracks)
            
            print(f"Progress: {completed}/{total} completed, {failed} failed\n")
            
            for track in self.tracks:
                self._display_track_progress(track)
    
    def _display_track_progress(self, track):
        """Display progress for a single track"""
        name = track['name'][:30].ljust(30)  # Truncate/pad name to 30 chars
        status = track['status']
        progress = track['progress']
        
        # Status icon
        if status == 'pending':
            icon = "⏳"
            status_text = "Pending"
        elif status == 'isolating':
            icon = "🎛️"
            status_text = "Isolating"
        elif status == 'downloading':
            icon = "⬇️"
            status_text = "Downloading"
        elif status == 'processing':
            icon = "⚙️"
            status_text = "Processing"
        elif status == 'completed':
            icon = "✅"
            status_text = "Completed"
        elif status == 'failed':
            icon = "❌"
            status_text = "Failed"
        else:
            icon = "❓"
            status_text = status.title()
        
        # Progress bar
        if status == 'downloading' and progress > 0:
            bar_width = 20
            filled = int(bar_width * progress / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            progress_text = f"[{bar}] {progress:3.0f}%"
        elif status == 'completed':
            bar = "█" * 20
            progress_text = f"[{bar}] 100%"
        else:
            bar = "░" * 20
            progress_text = f"[{bar}]   - "
        
        # File size info
        if track['file_size'] > 0:
            size_mb = track['file_size'] / (1024 * 1024)
            downloaded_mb = track['downloaded'] / (1024 * 1024)
            size_text = f"{downloaded_mb:.1f}/{size_mb:.1f} MB"
        else:
            size_text = ""
        
        # Time info
        time_text = ""
        if track['start_time'] and status == 'downloading':
            elapsed = time.time() - track['start_time']
            time_text = f"({elapsed:.0f}s)"
        elif track['start_time'] and track['end_time']:
            duration = track['end_time'] - track['start_time']
            time_text = f"({duration:.0f}s)"
        
        print(f"{icon} {name} {status_text:<12} {progress_text} {size_text:<12} {time_text}")
    
    def _final_display(self):
        """Show final summary"""
        with self.lock:
            completed = [t for t in self.tracks if t['status'] == 'completed']
            failed = [t for t in self.tracks if t['status'] == 'failed']
            
            print(f"\n🎉 Download Summary for: {self.current_song}")
            print("-" * 50)
            print(f"✅ Completed: {len(completed)}")
            print(f"❌ Failed: {len(failed)}")
            print(f"📊 Success Rate: {len(completed)/len(self.tracks)*100:.1f}%")
            
            if failed:
                print("\nFailed tracks:")
                for track in failed:
                    print(f"  ❌ {track['name']}")
            
            total_time = 0
            if completed:
                for track in completed:
                    if track['start_time'] and track['end_time']:
                        total_time += track['end_time'] - track['start_time']
                avg_time = total_time / len(completed)
                print(f"\n⏱️ Average download time: {avg_time:.1f}s per track")
            
            print()