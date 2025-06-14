# Karaoke-Version.com Track Automation

Automated system for downloading isolated backing tracks from Karaoke-Version.com using Python and Selenium. The system can log in, discover tracks, and isolate individual instruments for download.

## 🎯 Project Status: 90% Complete

### ✅ **Fully Working Features**
- **Authentication** - Login with live credentials (`frm_login`, `frm_password`, `sbm`)
- **Track Discovery** - Automatically finds all  available tracks per song
- **Track Isolation** - Solo button functionality to isolate individual instruments
- **Session Management** - Maintains login state throughout automation
- **Modular Architecture** - Clean, testable, reusable components

### 🔄 **In Progress**
- **Download Process** - Framework implemented, needs download button discovery

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Chrome browser
- Karaoke-Version.com account with track access

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd kv

# Create and activate virtual environment
python -m venv venv
source bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Create `.env` file:**
```bash
KV_USERNAME=your_email@example.com
KV_PASSWORD=your_password
```

2. **Configure songs in `songs.yaml`:**
```yaml
songs:
  - url: "https://www.karaoke-version.com/custombackingtrack/artist/song.html"
    name: "Song_Directory_Name"
    description: "Artist - Song Title"
```

### Usage

```python
from karaoke_automator import KaraokeVersionAutomator

# Initialize and login
automator = KaraokeVersionAutomator()
automator.login()

# Discover tracks for a song
song_url = "https://www.karaoke-version.com/custombackingtrack/chappell-roan/pink-pony-club.html"
tracks = automator.get_available_tracks(song_url)

# Solo specific instruments
guitar_track = [t for t in tracks if 'guitar' in t['name'].lower()][0]
automator.solo_track(guitar_track, song_url)

# Switch to vocals
vocal_track = [t for t in tracks if 'vocal' in t['name'].lower()][0]
automator.solo_track(vocal_track, song_url)

# Clear all solos (unmute everything)
automator.clear_all_solos(song_url)
```

## 🎛️ Track Isolation Features

### Available Tracks (Example: "Pink Pony Club")
1. Intro count Click
2. Electronic Drum Kit
3. Percussion
4. Synth Bass
5. **Lead Electric Guitar**
6. Piano
7. Synth Pad
8. Synth Keys 1
9. Synth Keys 2
10. **Backing Vocals**
11. **Lead Vocal**

### Solo Button Functionality
- **Mutually Exclusive**: Solo buttons automatically mute all other tracks
- **Instant Switching**: No delays when changing between instruments
- **Visual Feedback**: Active solo buttons show 'active' state
- **State Management**: Can detect and clear all active solos

## 🏗️ Architecture

### Modular Components

```
karaoke_automator.py
├── KaraokeVersionLogin      # Authentication logic
├── KaraokeVersionTracker    # Track discovery & isolation
└── KaraokeVersionAutomator  # Main coordinator
```

### Key Classes

- **`KaraokeVersionLogin`** - Handles all login functionality
  - `login()` - Complete login workflow
  - `is_logged_in()` - Check login status
  - `click_login_link()` - Navigate to login form
  - `fill_login_form()` - Fill credentials and submit

- **`KaraokeVersionTracker`** - Manages track operations
  - `discover_tracks()` - Find all available tracks
  - `solo_track()` - Isolate specific track
  - `clear_all_solos()` - Unmute all tracks
  - `verify_song_access()` - Check authentication

- **`KaraokeVersionAutomator`** - Main interface
  - Coordinates all functionality
  - Provides simple API for automation
  - Manages WebDriver lifecycle

## 🧪 Testing

### Unit Tests
```bash
# Run all unit tests
python -m pytest tests/test_*.py -v

# Expected: 18+ tests passing
```

### Live Testing
```bash
# Test login with real credentials
python tests/test_modular_login.py

# Test solo button functionality
python tests/test_solo_functionality.py

# Test complete workflow
python tests/test_updated_automation.py
```

### Manual Testing
```bash
# Inspect login form structure
python tests/inspect_login_form.py

# Inspect solo button selectors
python tests/inspect_solo_buttons.py
```

## 🔧 Technical Details

### Discovered Selectors (Verified Working)

#### Login
- **Login Link**: `//a[contains(text(), 'Log in')]`
- **Username**: `name="frm_login"`
- **Password**: `name="frm_password"`
- **Submit**: `name="sbm"`
- **Success**: "My Account" text in header

#### Track Control
- **Track Elements**: `.track[data-index='0-10']`
- **Track Names**: `.track__caption`
- **Solo Buttons**: `button.track__solo`

### Performance Metrics
- **Login Time**: ~14 seconds
- **Track Discovery**: Instant (11 tracks found)
- **Solo Switching**: Immediate response
- **Session Management**: Persistent throughout automation

## 📁 Project Structure

```
kv/
├── karaoke_automator.py     # Main modular automation system
├── main.py                  # Original automation script (still functional)
├── config.py                # Configuration management
├── songs.yaml               # Song URL configuration
├── .env                     # Credentials (not in git)
├── requirements.txt         # Python dependencies
├── tests/                   # Test suite
│   ├── test_*.py           # Unit tests
│   ├── inspect_*.py        # Site inspection tools
│   └── README.md           # Test documentation
├── downloads/               # Downloaded files (gitignored)
├── logs/                    # Automation logs (gitignored)
└── docs/                    # Additional documentation
```

## 🛡️ Security & Best Practices

- **Credentials**: Stored in `.env` file (gitignored)
- **Rate Limiting**: Built-in delays between operations
- **Error Handling**: Comprehensive throughout
- **Session Management**: Automatic re-authentication
- **Virtual Environment**: Isolated dependencies

## 🐛 Troubleshooting

### Common Issues

1. **Login Fails**
   - Verify credentials in `.env` file
   - Check if site structure changed
   - Run `python tests/inspect_login_form.py`

2. **Tracks Not Found**
   - Ensure logged in first
   - Verify song URL is accessible
   - Check track discovery: `python tests/test_solo_functionality.py`

3. **Solo Buttons Not Working**
   - Inspect with: `python tests/inspect_solo_buttons.py`
   - Verify track elements have `data-index` attributes

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚧 Known Limitations

1. **Download Implementation**: Framework exists but needs download button discovery
2. **Site Changes**: Selectors may need updates if site structure changes
3. **Rate Limits**: Respect site's terms of service
4. **Browser Dependencies**: Requires Chrome and ChromeDriver

## 🤝 Contributing

1. Always activate virtual environment: `source bin/activate`
2. Run tests before committing: `python -m pytest tests/ -v`
3. Update selectors if site changes
4. Add new functionality to modular components

## 📄 License

This project is for educational and personal use only. Respect Karaoke-Version.com's terms of service.

## 🔗 Related Files

- **`CLAUDE.md`** - Detailed project documentation and discoveries
- **`strategy.md`** - Implementation strategy and progress tracking
- **`tests/README.md`** - Test suite documentation

---

**Status**: Production-ready for authentication, track discovery, and track isolation. Download implementation in progress.
