# Karaoke Track Downloader

🎵 **Automated system for downloading isolated backing tracks from Karaoke-Version.com**

Downloads individual instrument tracks (bass, guitar, vocals, drums, etc.) from your purchased songs. Each track is saved as a separate MP3 file, organized by song.

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the project
git clone https://github.com/vbrilon/kv-downloader
cd kv-downloader

# Recommend that you set up and activate a virtual environment to run in

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Credentials

Create a `.env` file with your Karaoke-Version.com login:

```bash
KV_USERNAME=your_email@example.com
KV_PASSWORD=your_password
```

⚠️ **Important**: You need a valid account with purchased songs.

### 3. Configure Songs

Edit `songs.yaml` to specify which songs to download:

```yaml
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/jimmy-eat-world/the-middle.html"
    description: "Jimmy Eat World - The Middle"
    key: 0  # Optional: Pitch adjustment (-12 to +12 semitones)
  
  - url: "https://www.karaoke-version.com/custombackingtrack/taylor-swift/shake-it-off.html"
    name: "Shake_It_Off"  # Optional: override auto-extracted folder name
    key: "+2"  # Raise pitch by 2 semitones (supports multiple formats)
```

💡 **Get URLs**: Copy the URL from your purchased song page on Karaoke-Version.com.

### 4. Run the Downloader

```bash
# Normal mode (headless, with progress bar)
python karaoke_automator.py

# Debug mode (visible browser, detailed logging)
python karaoke_automator.py --debug
```

---

## 📁 Download Organization

Files are organized in the `downloads/` folder:

```
downloads/
├── Jimmy Eat World - The Middle/
│   ├── Bass.mp3
│   ├── Lead Electric Guitar.mp3
│   ├── Electronic Drum Kit.mp3
│   └── Lead Vocal.mp3
├── Taylor Swift - Shake It Off/
│   ├── Piano.mp3
│   └── Synth Keys 1(+2).mp3  # Shows key adjustment
```

## ⚙️ Configuration

### Song Options

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `url` | ✅ | Song page URL | `"https://www.karaoke-version.com/custombackingtrack/artist/song.html"` |
| `name` | ❌ | Custom folder name (auto-extracted if omitted) | `"My_Song"` |
| `description` | ❌ | Song description | `"Artist - Song Title"` |
| `key` | ❌ | Pitch adjustment (-12 to +12 semitones) | `2`, `"+3"`, `"-2"` |

### Key Adjustment Formats

The `key` field supports multiple input formats for flexibility:

```yaml
# Integer format (most common)
key: 2      # Raise 2 semitones
key: -3     # Lower 3 semitones  
key: 0      # No change

# String format with explicit sign
key: "+2"   # Raise 2 semitones
key: "-3"   # Lower 3 semitones
key: "+0"   # No change

# String format without sign (treated as positive)
key: "2"    # Raise 2 semitones
key: "5"    # Raise 5 semitones
```

**Range**: -12 to +12 semitones (1 octave). Values outside this range default to 0.

### Debug Mode

Use `--debug` flag for troubleshooting:
- Shows visible browser window
- Saves detailed logs to `logs/debug.log`
- Displays element inspection info

### Environment Variables

```bash
# .env file
KV_USERNAME=your_email@example.com
KV_PASSWORD=your_password
DOWNLOAD_FOLDER=./downloads  # Optional: custom download location
```

---

## 🛠️ Troubleshooting

### Common Issues

**"Login failed"**
- Check credentials in `.env` file
- Verify account works on website manually

**"SONG NOT PURCHASED" error**
- Purchase the song on Karaoke-Version.com first
- Script will skip unpurchased songs and continue

**"ChromeDriver issues"**
- Install/update Chrome browser
- **macOS**: `brew install chromedriver`
- **macOS**: If quarantine error: `xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver`

### Getting Help

1. Always activate virtual environment: `source bin/activate`
2. Run debug mode: `python karaoke_automator.py --debug`
3. Check logs in `logs/` folder
4. Test with one song first
5. Verify account works on website

---

## 🔧 Technical Details

### Requirements
- Python 3.8+
- Chrome browser (latest version)
- Internet connection
- Karaoke-Version.com account with purchased songs

### Features
- **Real-time progress bar** with track status and timing
- **Automatic file organization** with clean filenames
- **Key adjustment support** (-12 to +12 semitones)
- **Background mode** (headless) or debug mode (visible browser)
- **Robust error handling** and session management
- **Smart download sequencing** with proper waiting

### Performance
- Login: ~4-14 seconds (optimized on repeat use)
- Track discovery: Instant
- Download speed: Depends on internet connection
- Supports 10-15 tracks per song typically

---

## 📄 Legal Notice

**Personal use only** with songs you have legally purchased from Karaoke-Version.com.

- ✅ Use with your purchased songs
- ✅ Backup your legally owned content
- ❌ Do not share downloaded tracks
- ❌ Do not use commercially
- ❌ Respect Karaoke-Version.com's Terms of Service

---

## 🎉 Enjoy Your Music!

Use your isolated tracks for:
- **Practice** with backing tracks
- **Learning** specific instrument parts
- **Remixing** with individual elements
- **Karaoke** with professional backing tracks

Have fun making music! 🎵
