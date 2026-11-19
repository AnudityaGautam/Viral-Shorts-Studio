# 🎬 Viral Shorts Studio

> **Transform long-format YouTube videos (podcasts, interviews, streams, lectures) into high-engagement, viral 9:16 vertical YouTube Shorts in seconds.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Hardware%20Accelerated-green)
![Whisper](https://img.shields.io/badge/AI-faster--whisper-purple)

---

## ✨ Features

- 📁 **Dual Video Input (Online & Local Files)**:
  - 🔗 **Copy-Paste Video URLs**: YouTube podcasts, interviews, lectures, and live streams.
  - 📂 **Local Video Files**: Upload, browse, or drag & drop files (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.m4v`, `.ts`).
  - 📋 **Global Clipboard Paste (Ctrl+V)**: Paste copied files or URLs directly anywhere on the page.
  - ⚡ **Direct PC Path**: Paste local file paths on your PC for instant 0s loading without re-uploading.
- ⚡ **Viral Moments & Attention Hook AI Engine**:
  - Scans retention graphs, audio energy peaks, and curiosity patterns to detect top 4–6 viral moments (15–60s).
  - Categorizes hooks with psychological drivers (*The Harsh Truth*, *Wait For The End*, *99% Get This Wrong*, *Insider Secret*).
- 📌 **Customizable 2–3 Line Viral Top Header Card**:
  - Pinned high-contrast viral header banner (e.g. Line 1: `THE HARSH TRUTH ⚠️`, Line 2: `THAT NOBODY ADMITS...`, Line 3: `WAIT FOR THE END 🧠`).
  - 1-click viral preset chips + real-time live preview box.
- ✨ **Super Advanced 3D Kinetic Subtitles**:
  - Multi-layer 3D extruded drop shadows, depth bevels, and isometric tilt (`Impact`, `Arial Black`).
  - Word-by-word kinetic 3D scale pop animations (`\fscx125` / `\fscy125`).
  - 5 High-Conversion Styles: **3D Hormozi Kinetic (Yellow)**, **3D MrBeast Wobble (Lime Green)**, **3D Cyber Synthwave (Cyan/Magenta)**, **3D Fire & Gold**, **3D Comic Punch**, and **Modern Clean**.
- 🔊 **Viral Meme Sound Effects (SFX)**:
  - Built-in audio mixing for viral punchlines: **Vine Boom**, **Whoosh Transition**, **Bell Ding**, and **Pop**.
  - Injected seamlessly at opening hook (0.25s) with volume balancing.
  - Interactive "Test Sound" audio player in Studio UI.
- 🔍 **Dynamic Camera Zooms & Rhythmic Punch-Ins**:
  - Cinematic 0.3s fade-in transition.
  - Automatic 1.12x visual pattern interrupt punch-in every 4.5s to reset viewer attention span and boost completion rate.
- 💎 **Studio Master Quality Render Pipeline**:
  - Visually lossless **CRF 17** encoding with **Lanczos** anti-aliased scaling.
  - **EBU R128 Loudness Normalization** (`-14 LUFS`) for punchy, mobile-optimized audio matching YouTube Shorts / TikTok algorithmic standards.
- 📱 **9:16 Vertical Framing Modes**:
  - **Blurred Ambient Fill** (Opus Clip / Vmaker style)
  - **Smart Center Crop** (Full 1080x1920 portrait)
  - **Split-Screen Stacking** (Dual layout for interviews and podcasts)
- 🛡️ **Copyright Evasion Shield**:
  - Audio pitch/tempo micro-shift (1.5%) to bypass ContentID acoustic matching.
  - Visual frame color and contrast micro-tuning.
- 📦 **Batch Generation & ZIP Export**:
  - Generate all 4–5 viral shorts simultaneously with a single click.
  - Download individual 1080x1920 MP4s or download everything packaged in a `.zip` archive.
- 🚀 **Publishing Pack Generator**:
  - Auto-generated high-CTR titles, viral descriptions, and `#Shorts` tags with 1-click copy.
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
