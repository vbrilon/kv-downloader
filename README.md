# Karaoke Track Downloader

🎵 **Automated system for downloading isolated backing tracks from Karaoke-Version.com**

Automatically downloads individual instrument tracks (bass, guitar, vocals, drums, etc.) from your purchased songs on Karaoke-Version.com. Each track is saved as a separate MP3 file, organized by song.

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download this project
git clone <repository-url>
cd kv

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Setup Your Credentials

Create a `.env` file in the project folder with your Karaoke-Version.com login:

```bash
KV_USERNAME=your_email@example.com
KV_PASSWORD=your_password
```

⚠️ **Important**: You need a valid Karaoke-Version.com account with purchased songs.

### 3. Configure Your Songs

Edit the `songs.yaml` file to specify which songs to download:

```yaml
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
    name: "The_Middle"
    description: "Jimmy Eat World - The Middle"
    key: 0  # Optional: Pitch adjustment in semitones (-12 to +12)
  
  - url: "https://www.karaoke-version.com/custombackingtrack/taylor-swift/shake-it-off.html"
    name: "Shake_It_Off" 
    description: "Taylor Swift - Shake It Off"
    key: 2  # Raise pitch by 2 semitones
```

💡 **How to get song URLs**: Go to your purchased song on Karaoke-Version.com and copy the URL from your browser.

🎵 **Key Adjustment**: The optional `key` field adjusts pitch from -12 to +12 semitones. Use positive numbers to raise pitch, negative to lower it.

### 4. Run the Downloader

```bash
# Normal usage (runs in background with progress bar)
python karaoke_automator.py

# Debug mode (shows browser window + verbose logging)
python karaoke_automator.py --debug

# Demo the progress bar (see what it looks like)
python demo_progress.py
```

---

## ⚙️ Configuration Options

### Debug Mode

The script runs in **background mode** by default (no browser window). Use the `--debug` flag when you need to see what's happening:

```bash
# Normal mode (recommended for regular use)
python karaoke_automator.py

# Debug mode (use when troubleshooting)
python karaoke_automator.py --debug
```

**Debug mode provides:**
- ✅ **Visible browser window** - See exactly what the automation is doing
- ✅ **Detailed file logging** - All debug info saved to `logs/debug.log`
- ✅ **Clean progress bar** - Console shows only progress bar and critical messages
- ✅ **Element inspection** - Shows which page elements are being found/used
- ✅ **Error details** - More detailed error messages for troubleshooting

**Logging locations:**
- **Debug mode**: Detailed logs → `logs/debug.log`, Progress bar → console
- **Normal mode**: Standard logs → `logs/automation.log` + console

### Progress Bar

The automation includes a **real-time progress bar** that shows:

```
🎵 Downloading: Taylor Swift - Shake It Off
================================================================================
Progress: 3/6 completed, 0 failed

✅ Bass               Completed    [████████████████████] 100%    (3s)
✅ Guitar             Completed    [████████████████████] 100%    (3s)  
⬇️ Drums              Downloading  [████████████░░░░░░░░]  60%    (2s)
⏳ Piano              Pending      [░░░░░░░░░░░░░░░░░░░░]   -      
⏳ Vocals             Pending      [░░░░░░░░░░░░░░░░░░░░]   -      
⏳ Backing Vocals     Pending      [░░░░░░░░░░░░░░░░░░░░]   -      
```

**Progress bar shows:**
- ✅ **Track status**: Pending → Isolating → Processing → Downloading → Completed/Failed
- ✅ **Visual progress bars**: Real-time download progress with Unicode blocks
- ✅ **Download percentages**: Shows % complete for each track
- ✅ **Time tracking**: How long each track takes to download
- ✅ **Summary stats**: Completed vs failed tracks at the top
- ✅ **Download sequencing**: Waits for each download to start before proceeding

**Try the demo:**
```bash
python demo_progress.py
```

### Programmatic Usage

If using the automation in your own code:

```python
from karaoke_automator import KaraokeVersionAutomator

# Background mode with progress bar (default)
automator = KaraokeVersionAutomator(headless=True, show_progress=True)

# Visible browser for debugging
automator = KaraokeVersionAutomator(headless=False, show_progress=True)

# Disable progress bar for simple logging
automator = KaraokeVersionAutomator(headless=True, show_progress=False)
```

### Download Location

Files are automatically organized in the `downloads/` folder:

```
downloads/
├── Jimmy Eat World - The Middle/
│   ├── bass_isolated.mp3
│   ├── guitar_isolated.mp3
│   ├── drums_isolated.mp3
│   └── vocals_isolated.mp3
├── Taylor Swift - Shake It Off/
│   ├── piano_isolated.mp3
│   └── synth_isolated.mp3
```

### Credentials Storage

Store your login credentials in the `.env` file (never committed to git):

```bash
# Required
KV_USERNAME=your_email@example.com
KV_PASSWORD=your_password

# Optional - customize download location
DOWNLOAD_FOLDER=./my_custom_downloads
```

### Song Configuration Options

Each song in `songs.yaml` supports these fields:

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `url` | ✅ | Direct link to song page | `"https://www.karaoke-version.com/custombackingtrack/artist/song.html"` |
| `name` | ✅ | Directory name for downloads | `"My_Song"` |
| `description` | ❌ | Human-readable song info | `"Artist - Song Title"` |
| `key` | ❌ | Pitch adjustment (-12 to +12 semitones) | `2` (raise 2 semitones), `-3` (lower 3 semitones) |

**Key Adjustment Examples:**
- `key: 0` - No pitch change (default)
- `key: 2` - Raise pitch by 2 semitones (e.g., C to D)
- `key: -1` - Lower pitch by 1 semitone (e.g., C to B)
- `key: 12` - Raise by full octave
- `key: -12` - Lower by full octave

---

## 🎛️ Advanced Usage

### Download Specific Tracks with Custom Settings

```python
from karaoke_automator import KaraokeVersionAutomator

# Initialize
automator = KaraokeVersionAutomator(headless=True)
automator.login()

# Get available tracks for a song
song_url = "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
tracks = automator.get_available_tracks(song_url)

# Setup mixer controls
automator.track_handler.ensure_intro_count_enabled(song_url)  # Enable intro count
automator.track_handler.adjust_key(song_url, 3)  # Raise key by 3 semitones

# Find and download specific instruments
bass_track = [t for t in tracks if 'bass' in t['name'].lower()][0]
automator.solo_track(bass_track, song_url)
automator.track_handler.download_current_mix(song_url, "bass_isolated")

# Switch to guitar (mixer settings persist)
guitar_track = [t for t in tracks if 'guitar' in t['name'].lower()][0]
automator.solo_track(guitar_track, song_url)
automator.track_handler.download_current_mix(song_url, "guitar_isolated")
```

### Available Track Types

Each song typically includes 10-15 tracks:
- **Rhythm section**: Bass, drums, percussion
- **Guitars**: Acoustic, electric (clean/distorted), lead/rhythm
- **Keys**: Piano, synths, organ
- **Vocals**: Lead vocals, backing vocals
- **Other**: Click track, strings, brass (varies by song)

### Force Re-login

If you need to switch accounts or refresh your session:

```python
automator.login(force_relogin=True)
```

---

## 🛠️ Troubleshooting

### Common Issues

**"Login failed"**
- Check your username/password in the `.env` file
- Make sure you have an active Karaoke-Version.com account
- Try running with `--debug` to see what's happening

**"No tracks found"**
- Make sure the song URL is correct and you own the song
- Verify you're logged in with the right account
- Check that the song has backing tracks available

**"Download failed"**
- Make sure you have enough disk space
- Check your internet connection
- Try running with `--debug` to see browser activity

**"Browser not opening" / "ChromeDriver issues"**
- Make sure Chrome is installed on your system
- Try updating Chrome to the latest version
- **macOS users**: Install ChromeDriver via Homebrew: `brew install chromedriver`
- **macOS users**: If getting "unexpectedly exited" error: `xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver`
- Test Chrome setup: `python test_chrome_quick.py`

### Getting Help

If you encounter issues:

1. **Run in debug mode** first: `python karaoke_automator.py --debug`
2. **Check the logs** in the `logs/` folder for detailed information
3. **Test with one song** before running multiple songs
4. **Verify your account** works on the website manually

---

## 🔧 Technical Details

### System Requirements
- **Python 3.8+**
- **Chrome browser** (latest version recommended)
- **Internet connection**
- **Karaoke-Version.com account** with purchased songs

### Performance
- **Login time**: ~4-14 seconds (optimized on repeat use)
- **Track discovery**: Instant (finds all available tracks)
- **Download speed**: Depends on your internet connection
- **Background mode**: Runs without visual interference

### File Safety
- **Duplicate prevention**: Automatically removes old downloads before new ones
- **Age protection**: Only removes files less than 1 hour old
- **Organized storage**: Each song gets its own folder
- **Backup friendly**: Clear folder structure for easy backup

### Download Sequencing
- **Smart waiting**: Monitors filesystem to detect when downloads actually start
- **Proper sequencing**: Won't initiate next download until previous one begins
- **Timeout protection**: Max 60-second wait per download with progress updates
- **File organization**: Automatically moves downloads from default location to song folders
- **Clean filenames**: Removes unwanted suffixes like "_Custom_Backing_Track"

### Privacy & Security
- **Local credentials**: Login details stored only in your `.env` file
- **No data collection**: Script runs entirely on your computer
- **Respect rate limits**: Built-in delays prevent overloading the website
- **Session management**: Handles login/logout automatically

---

## 📄 Legal Notice

This tool is for **personal use only** with songs you have legally purchased from Karaoke-Version.com. 

- ✅ Use with your own purchased songs
- ✅ Backup your legally owned content
- ❌ Do not share downloaded tracks
- ❌ Do not use for commercial purposes
- ❌ Respect Karaoke-Version.com's Terms of Service

---

## 🎉 Enjoy Your Music!

You now have isolated tracks for practice, remixing, or karaoke performance. Each instrument is saved separately so you can:

- **Practice along** with just the backing tracks
- **Learn parts** by isolating specific instruments
- **Create remixes** with individual track elements
- **Perform karaoke** with professional backing tracks

Have fun making music! 🎵