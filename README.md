# 🎬 Viral Shorts Studio

> **Transform long-format YouTube videos (podcasts, interviews, streams, lectures) into high-engagement, viral 9:16 vertical YouTube Shorts in seconds.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Hardware%20Accelerated-green)
![Whisper](https://img.shields.io/badge/AI-faster--whisper-purple)

---

## ✨ Features

- ⚡ **YouTube Heatmap AI**: Scans YouTube's viewer retention graph to automatically detect peak 30–40s viral highlights with retention scores.
- 🎯 **Targeted Partial Downloads**: Uses `yt-dlp` to download *only* the chosen 30–40s section in 1080p rather than downloading gigabytes.
- 📱 **9:16 Vertical Video Engine**:
  - **Blurred Ambient Background** (Opus Clip / Vmaker style)
  - **Smart Center Crop** (Full 1080x1920 portrait)
  - **Split-Screen** (Dual layout for interviews and podcasts)
- 💬 **Subtitles of Virality (Whisper AI)**:
  - Local AI speech-to-text with exact word-by-word timestamps.
  - Animated karaoke active highlights (Alex Hormozi Yellow, MrBeast Pop Green, Cyber Neon).
  - High-impact universal typography (`Impact`, `Arial Black`).
- 🛡️ **Copyright Evasion Shield**:
  - Audio pitch/tempo micro-shift (1.5%) to bypass ContentID acoustic matching.
  - Visual frame color and contrast tuning.
- 🚀 **Publishing Pack Generator**:
  - Auto-generated high-CTR YouTube titles, descriptions, and `#Shorts` tags with 1-click copy.
- 💻 **Multiple Interfaces**:
  - Full local Web Studio UI (`http://localhost:5000`)
  - 1-Click Windows Launcher (`Launch_Shorts_Studio.bat`)
  - Standalone Terminal CLI (`clip_shorts.py`)

---

## 🚀 Quick Start

### 1. Installation

Clone this repository:
```bash
git clone https://github.com/AnudityaGautam/Viral-Shorts-Studio.git
cd Viral-Shorts-Studio
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launching the Studio

#### Option A: 1-Click Launcher (Windows)
Double-click **`Launch_Shorts_Studio.bat`**. It will start the server and open the studio in your browser!

#### Option B: Python Server
```bash
python server.py
```
Open **`http://localhost:5000`** in your browser.

#### Option C: Terminal CLI
```bash
# Auto-clip the #1 top viral peak as a 9:16 Short with Hormozi subtitles
python clip_shorts.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --peak 1 --layout blur --style hormozi

# Custom timestamp clipping
python clip_shorts.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --start 14:20 --end 14:55 --hook "WAIT TILL THE END 😱"
```

---

## 🛠️ Tech Stack

- **Backend**: Python 3, `yt-dlp`, `imageio-ffmpeg`, `faster-whisper`
- **Frontend**: Vanilla JavaScript (ES6+), Semantic HTML5, Modern CSS3 with Glassmorphism
- **Video Processing**: FFmpeg (Hardware accelerated, `libx264`, `subtitles` filter)
- **Speech Recognition**: OpenAI Whisper (`faster-whisper` CT2 engine)

---

## 📄 License

MIT License. Free to use for personal and commercial content creation.
