# Karaoke Track Downloader

🎵 **Automated system for downloading isolated backing tracks from Karaoke-Version.com**

Downloads individual instrument tracks (bass, guitar, vocals, drums, etc.) from your purchased songs. Each track is saved as a separate MP3 file, organized by song.

Project was inspired by [https://github.com/subdigital/kv-downloader]

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the project
git clone https://github.com/vbrilon/kv-downloader
cd kv-downloader

# Recommend that you set up and activate a virtual environment to run in
python3 -m venv .

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Credentials

Create a `.env` file with your Karaoke-Version.com login:

```bash
KV_USERNAME=your_email@example.com
KV_PASSWORD=your_password
DOWNLOAD_FOLDER=./downloads  # Optional: custom download location
```

⚠️ **Important**: You need a valid account with purchased songs.

### 3. Configure Songs

#### Option A: Generate from CSV (Recommended for multiple songs)

If you have a list of songs, create a CSV file with `Song,Artist` columns:

```csv
Song,Artist
Basket Case,Green Day
Otherside,RHCP
Crazy Train,Ozzy
Bad Moon Rising,CCR
```

Then run the CSV converter to automatically search and generate `songs.yaml`:

```bash
# Basic usage - generates songs_generated.yaml
python csv_to_songs.py list.csv

# With visible browser for debugging
python csv_to_songs.py list.csv --debug

# Preview without writing files
python csv_to_songs.py list.csv --dry-run

# Custom output file
python csv_to_songs.py list.csv --output my_songs.yaml
```

The converter will:
- Search karaoke-version.com for each song
- Expand common abbreviations (RHCP → Red Hot Chili Peppers, GnR → Guns N' Roses, etc.)
- Score matches and include high-confidence results in the YAML
- Generate `unmatched_songs.txt` for songs requiring manual lookup

After reviewing the generated file, rename it to `songs.yaml`.

#### Option B: Manual Configuration

Edit `songs.yaml` directly to specify which songs to download:

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

# Force fresh login (bypass saved session)
python karaoke_automator.py --force-login

# Clear saved session and exit
python karaoke_automator.py --clear-session

# Opt out of the direct-HTTP path and use the legacy Selenium click flow
# (slower; useful for A/B comparison or if the site changes the inline
# mixer init script)
python karaoke_automator.py --legacy-selenium-download
```

The default download path is the **direct-HTTP API** (`basket.php` →
`begin_download.html` → CDN MP3). It is ~2x faster per track than
clicking the UI download button. If the site changes the inline mixer
init script and capture fails, the run automatically falls back to the
legacy Selenium path for that song.

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

### ⚠️ YAML Formatting Requirements

**Critical formatting rules to avoid configuration errors:**

1. **Indentation**: Use exactly **2 spaces** for each level - tabs and inconsistent spacing will break YAML parsing
   ```yaml
   songs:        # No indentation
     - url: "..."  # Exactly 2 spaces
       name: "..." # Exactly 4 spaces (2 levels)
   ```

2. **String Quotes**: Always wrap string values in double quotes to prevent parsing errors
   ```yaml
   # ✅ Correct
   - url: "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
     name: "My_Song"
   
   # ❌ Incorrect (missing quotes)
   - url: https://www.karaoke-version.com/custombackingtrack/artist/song.html
     name: My_Song
   ```

3. **Common Errors**:
   - **Wrong indentation**: `ERROR: string indices must be integers, not 'str'`
   - **Missing quotes**: Unexpected parsing behavior or validation errors
   - **Tabs instead of spaces**: YAML structure corruption

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
- Logs are cleared at each new invocation of the script

### Session Persistence ✅

The script automatically saves your login session after the first successful login. This feature  provides significant time savings:

- **First run**: Performs normal login (~4-14 seconds)
- **Subsequent runs**: Restores saved session (~2-3 seconds) 
- **Session expiry**: Automatically falls back to fresh login after 24 hours
- **Smart validation**: Verifies restored sessions are still valid before proceeding

**Session Management Commands**:
```bash
# Force fresh login (ignore saved session)
python karaoke_automator.py --force-login

# Clear saved session data
python karaoke_automator.py --clear-session
```

**Session Data**: Stored in `.cache/session_data.pkl` (cookies, localStorage, etc.) - safe to delete if needed.

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

**"Force login not working"**
- Update to latest version (fixed bug where `--force-login --debug` didn't properly log out)
- Use `--clear-session` to manually clear saved session data if needed

**"ERROR: string indices must be integers, not 'str'"**
- Check `songs.yaml` for correct indentation (exactly 2 spaces per level)
- Ensure all string values are wrapped in double quotes
- Verify no tabs are used (only spaces for indentation)

**CSV Converter Issues**
- **"No results found"**: Try expanding artist abbreviations manually or check spelling
- **Many partial matches**: Review `unmatched_songs.txt` and verify URLs manually
- **Slow searching**: Rate limiting (2.5s between searches) prevents being blocked
- **Browser timeout**: Use `--debug` to see what's happening in the browser

### Testing

Run the test suite to verify functionality:

```bash
# Run all tests
python tests/run_tests.py

# Run only regression tests (quick verification)
python tests/run_tests.py --regression-only

# Run specific test categories
python tests/run_tests.py --unit-only
python tests/run_tests.py --integration-only
```

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
- **CSV to YAML converter** - batch convert song lists with automatic site searching
- **Real-time progress bar** with track status and timing
- **Automatic file organization** with clean filenames
- **Key adjustment support** (-12 to +12 semitones)
- **Background mode** (headless) or debug mode (visible browser)
- **Session persistence** - saves login state to skip future logins
- **Robust error handling** and session management
- **Smart download sequencing** with proper waiting

---
## 📄 Disclaimer

This was created for **personal use only** 

This complies with Karaoke-Version.com's Terms of Service to the best of my knowledge.
