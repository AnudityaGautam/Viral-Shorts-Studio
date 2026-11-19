import os
import sys
import json
import re
import math
import time
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

def run_cancellable_subprocess(cmd, cancel_check=None, timeout=None):
    """
    Execute subprocess command while actively checking for cooperative cancellation.
    If cancel_check returns True, immediately terminates and kills the running process.
    """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    start_time = time.time()
    while True:
        if cancel_check and cancel_check():
            try:
                proc.terminate()
                proc.wait(timeout=1.5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            raise RuntimeError("Operation cancelled by user (process terminated)")
            
        ret = proc.poll()
        if ret is not None:
            stdout, stderr = proc.communicate()
            return subprocess.CompletedProcess(cmd, ret, stdout, stderr)
            
        if timeout and (time.time() - start_time) > timeout:
            try:
                proc.kill()
            except Exception:
                pass
            raise subprocess.TimeoutExpired(cmd, timeout)
            
        time.sleep(0.15)

# Ensure nodejs is in PATH for yt-dlp JS runtime (Windows fallbacks; Linux typically has node in PATH)
if sys.platform == "win32":
    WIN_NODE_PATHS = [
        r"C:\Program Files\nodejs",
        r"C:\Program Files (x86)\nodejs",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\node"),
        os.path.expandvars(r"%APPDATA%\npm")
    ]
    for np in WIN_NODE_PATHS:
        if os.path.exists(np) and np not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = np + os.pathsep + os.environ.get("PATH", "")

import shutil
import imageio_ffmpeg
import yt_dlp

def get_ydl_base_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
    }
    node_bin = shutil.which("node")
    if not node_bin and sys.platform == "win32":
        for cand in [r"C:\Program Files\nodejs\node.exe", r"C:\Program Files (x86)\nodejs\node.exe"]:
            if os.path.exists(cand):
                node_bin = cand
                break
    if node_bin:
        opts['js_runtimes'] = {'node': {}}

    # Optional proxy and cookies configuration from environment
    proxy = os.environ.get("YTDLP_PROXY") or os.environ.get("HTTP_PROXY")
    if proxy:
        opts['proxy'] = proxy

    cookies_path = os.environ.get("YTDLP_COOKIES_FILE")
    if cookies_path and os.path.exists(cookies_path):
        opts['cookiefile'] = cookies_path

    return opts

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_ffmpeg_executable():
    """
    Detect FFmpeg binary in a cross-platform manner.
    Priority order:
    1. FFMPEG_PATH environment variable (custom override).
    2. System PATH (shutil.which('ffmpeg')) - standard for Linux/Docker/apt and installed Windows.
    3. Windows local workspace executable (ffmpeg.exe).
    4. imageio-ffmpeg bundled binary fallback.
    """
    custom_path = os.environ.get("FFMPEG_PATH")
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    if sys.platform == "win32":
        local_exe = os.path.join(WORKSPACE_DIR, "ffmpeg.exe")
        if os.path.isfile(local_exe):
            return local_exe

    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass

    return "ffmpeg"

FFMPEG = get_ffmpeg_executable()

# Add workspace directory and binary directory to PATH in a cross-platform manner
path_parts = os.environ.get("PATH", "").split(os.pathsep)
if WORKSPACE_DIR not in path_parts:
    os.environ["PATH"] = WORKSPACE_DIR + os.pathsep + os.environ.get("PATH", "")
if os.path.isabs(FFMPEG):
    ffmpeg_dir = os.path.dirname(FFMPEG)
    if ffmpeg_dir not in path_parts:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


def format_time(seconds):
    """Format seconds to MM:SS or HH:MM:SS."""
    seconds = int(round(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def parse_time(timestr):
    """Parse MM:SS or HH:MM:SS or float seconds string."""
    if isinstance(timestr, (int, float)):
        return float(timestr)
    parts = timestr.strip().split(":")
    if len(parts) == 1:
        return float(parts[0])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return 0.0

VIRAL_HOOK_PRESETS = [
    {
        "badge": "⚠️ THE HARSH TRUTH",
        "line1": "THE HARSH TRUTH ⚠️",
        "line2": "THAT NOBODY WANTS TO ADMIT...",
        "line3": "WAIT FOR THE END 🧠",
        "type": "harsh_truth",
        "attention_driver": "Psychological Pattern Interrupt & Truth Bomb",
        "default_sfx": "vine_boom"
    },
    {
        "badge": "🤯 WAIT FOR THE END",
        "line1": "WAIT FOR THE END 🤯",
        "line2": "THE PUNCHLINE WILL SHOCK YOU",
        "line3": "DON'T MISS THIS PART 🔥",
        "type": "curiosity_twist",
        "attention_driver": "Peak Curiosity & Retention Loop",
        "default_sfx": "vine_boom"
    },
    {
        "badge": "🛑 99% GET THIS WRONG",
        "line1": "99% OF PEOPLE GET THIS WRONG 🛑",
        "line2": "ARE YOU MAKING THIS MISTAKE?",
        "line3": "LISTEN VERY CAREFULLY 👂",
        "type": "mistake_warning",
        "attention_driver": "Loss Aversion & Ego Trigger",
        "default_sfx": "ding"
    },
    {
        "badge": "🤫 NOBODY TALKS ABOUT THIS",
        "line1": "NOBODY TALKS ABOUT THIS 🤫",
        "line2": "THE SECRET TO GETTING AHEAD",
        "line3": "PAY CLOSE ATTENTION ⚡",
        "type": "insider_secret",
        "attention_driver": "Exclusive Insider Advantage",
        "default_sfx": "whoosh"
    },
    {
        "badge": "⚡ THIS CHANGED EVERYTHING",
        "line1": "THIS CHANGED EVERYTHING ⚡",
        "line2": "THE 1 HABIT THAT FIXES YOUR LIFE",
        "line3": "WATCH TILL THE CLIMAX 🚀",
        "type": "breakthrough",
        "attention_driver": "Transformation & Dopamine Spike",
        "default_sfx": "pop"
    },
    {
        "badge": "💎 HIGH VALUE LESSON",
        "line1": "REMEMBER THIS FOREVER 💎",
        "line2": "IF YOU WANT TO WIN IN 2026",
        "line3": "SAVE THIS CLIP 📌",
        "type": "actionable_tip",
        "attention_driver": "High Utility Value & Save Trigger",
        "default_sfx": "ding"
    }
]

HOOK_TEMPLATES = [f"{p['line1']}\n{p['line2']}" for p in VIRAL_HOOK_PRESETS]

BADGE_TEMPLATES = [p["badge"] for p in VIRAL_HOOK_PRESETS]

def is_local_path(target):
    """Check if the given target string is a local video file path."""
    if not target or not isinstance(target, str):
        return False
    clean = target.strip().strip('"').strip("'")
    if clean.startswith("file://"):
        clean = urllib.parse.unquote(urllib.parse.urlparse(clean).path)
        if sys.platform == "win32" and clean.startswith("/") and len(clean) > 2 and clean[2] == ":":
            clean = clean[1:]
    if clean.startswith("http://") or clean.startswith("https://"):
        return False
    if os.path.exists(clean) and os.path.isfile(clean):
        return True
    if os.path.exists(os.path.join(WORKSPACE_DIR, clean)) and os.path.isfile(os.path.join(WORKSPACE_DIR, clean)):
        return True
    if os.path.exists(os.path.join(WORKSPACE_DIR, "uploads", clean)) and os.path.isfile(os.path.join(WORKSPACE_DIR, "uploads", clean)):
        return True
    if os.path.exists(os.path.join(WORKSPACE_DIR, "output", clean)) and os.path.isfile(os.path.join(WORKSPACE_DIR, "output", clean)):
        return True
    # Check common video extensions if path looks like a filename
    _, ext = os.path.splitext(clean.lower())
    if ext in [".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".ts", ".wmv", ".flv", ".3gp"]:
        return True
    return False

def resolve_local_path(target):
    """Resolve a target string or relative path to absolute local file path."""
    clean = target.strip().strip('"').strip("'")
    if clean.startswith("file://"):
        clean = urllib.parse.unquote(urllib.parse.urlparse(clean).path)
        if sys.platform == "win32" and clean.startswith("/") and len(clean) > 2 and clean[2] == ":":
            clean = clean[1:]
    if os.path.isabs(clean) and os.path.exists(clean):
        return clean
    candidates = [
        clean,
        os.path.join(WORKSPACE_DIR, clean),
        os.path.join(WORKSPACE_DIR, "uploads", clean),
        os.path.join(WORKSPACE_DIR, "output", clean),
        os.path.join(WORKSPACE_DIR, "uploads", os.path.basename(clean)),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return os.path.abspath(c)
    return clean

def get_local_video_info(file_path):
    """Probe local video metadata (duration, resolution) and generate a thumbnail."""
    abs_path = resolve_local_path(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Local video file not found: {file_path}")
    
    cmd = [FFMPEG, "-i", abs_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    duration = 0.0
    dur_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)', proc.stderr)
    if dur_match:
        h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
        duration = h * 3600 + m * 60 + s
        
    width = 1920
    height = 1080
    res_match = re.search(r'Stream.*Video:.* (\d{3,5})x(\d{3,5})', proc.stderr)
    if res_match:
        width = int(res_match.group(1))
        height = int(res_match.group(2))
        
    # Generate a thumbnail at 10% of the video or 5 seconds in
    safe_basename = re.sub(r'[^\w\-_\.]', '_', os.path.splitext(os.path.basename(abs_path))[0])
    thumb_filename = f"thumb_{safe_basename}.jpg"
    thumb_out = os.path.join(WORKSPACE_DIR, "output", thumb_filename)
    os.makedirs(os.path.join(WORKSPACE_DIR, "output"), exist_ok=True)
    
    thumb_sec = min(5.0, duration * 0.1) if duration > 5 else 0.5
    if not os.path.exists(thumb_out) or os.path.getsize(thumb_out) == 0:
        thumb_cmd = [
            FFMPEG, "-y",
            "-ss", str(thumb_sec),
            "-i", abs_path,
            "-frames:v", "1",
            "-q:v", "2",
            thumb_out
        ]
        subprocess.run(thumb_cmd, capture_output=True, text=True)
        
    file_size_mb = round(os.path.getsize(abs_path) / (1024 * 1024), 1)
    title = os.path.splitext(os.path.basename(abs_path))[0].replace("_", " ").replace("-", " ").title()
    
    return {
        "file_path": abs_path,
        "filename": os.path.basename(abs_path),
        "title": title,
        "duration": duration,
        "width": width,
        "height": height,
        "file_size_mb": file_size_mb,
        "thumbnail_url": f"/output/{thumb_filename}" if os.path.exists(thumb_out) else ""
    }

def analyze_local_video(file_path, target_duration=35, min_moments=5):
    """
    Analyze local uploaded video file, detect duration and generate 4-6 viral 15-60s clip candidates.
    """
    target_duration = max(15.0, min(60.0, float(target_duration)))
    min_moments = max(4, min(10, int(min_moments)))
    
    meta = get_local_video_info(file_path)
    duration = meta["duration"]
    abs_path = meta["file_path"]
    title = meta["title"]
    
    viral_moments = []
    
    if duration <= target_duration or duration <= 20:
        p = VIRAL_HOOK_PRESETS[0]
        viral_moments.append({
            "id": 1,
            "title": f"Full Highlight - {title}",
            "start_time": 0.0,
            "end_time": float(duration),
            "start_fmt": "00:00",
            "end_fmt": format_time(duration),
            "duration": int(duration),
            "virality_score": 99,
            "hook_badge": p["badge"],
            "top_hook": f"{p['line1']}\n{p['line2']}",
            "hook_line1": p["line1"],
            "hook_line2": p["line2"],
            "hook_line3": p["line3"],
            "attention_point": p["attention_driver"],
            "recommended_sfx": p["default_sfx"]
        })
    else:
        # Divide into high-retention intervals across the video
        count = min_moments
        step = (duration - target_duration) / max(1, count - 1)
        
        for i in range(count):
            start = round(i * step, 1)
            end = round(min(duration, start + target_duration), 1)
            dur = int(end - start)
            
            p = VIRAL_HOOK_PRESETS[i % len(VIRAL_HOOK_PRESETS)]
            score = max(78, int(99 - (i * 2.8)))
            
            moment_label = f"Key Viral Moment #{i+1} ({format_time(start)} - {format_time(end)})"
            if i == 0:
                moment_label = f"Opening Attention Hook & High Energy Intro"
            elif i == 1:
                moment_label = f"Peak Retention Climax & Key Insight"
            elif i == 2:
                moment_label = f"The Harsh Truth & Contrarian Take"
            elif i == count - 1:
                moment_label = f"Powerful Conclusion & Call To Action"
                
            viral_moments.append({
                "id": i + 1,
                "title": moment_label,
                "start_time": start,
                "end_time": end,
                "start_fmt": format_time(start),
                "end_fmt": format_time(end),
                "duration": dur,
                "virality_score": score,
                "hook_badge": p["badge"],
                "top_hook": f"{p['line1']}\n{p['line2']}",
                "hook_line1": p["line1"],
                "hook_line2": p["line2"],
                "hook_line3": p["line3"],
                "attention_point": p["attention_driver"],
                "recommended_sfx": p["default_sfx"]
            })
            
    return {
        "url": abs_path,
        "is_local": True,
        "file_path": abs_path,
        "title": title,
        "uploader": f"Local File ({meta['file_size_mb']} MB)",
        "duration": duration,
        "duration_fmt": format_time(duration),
        "thumbnail": meta["thumbnail_url"],
        "viral_moments": viral_moments,
        "target_duration": int(target_duration),
        "total_moments": len(viral_moments),
        "has_subtitles": True
    }


def analyze_video(url, target_duration=35, min_moments=5):
    """
    Extract metadata, chapters, and identify at least 4-5 viral moments around 0-60s using YouTube's heatmap or smart chapter/interval detection.
    """
    target_duration = max(15.0, min(60.0, float(target_duration)))
    min_moments = max(4, min(10, int(min_moments)))
    
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        'skip_download': True,
        'extract_flat': False,
    })
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    duration = float(info.get("duration") or 0)
    title = info.get("title") or "Unknown Video"
    uploader = info.get("uploader") or info.get("channel") or "Unknown Creator"
    thumbnail = info.get("thumbnail") or ""
    chapters = info.get("chapters") or []
    heatmap = info.get("heatmap") or []
    
    viral_moments = []
    
    # If video is already very short (<= target_duration)
    if duration <= target_duration:
        p = VIRAL_HOOK_PRESETS[0]
        viral_moments.append({
            "id": 1,
            "title": "Full Viral Highlight",
            "start_time": 0.0,
            "end_time": float(duration),
            "start_fmt": "00:00",
            "end_fmt": format_time(duration),
            "duration": int(duration),
            "virality_score": 99,
            "hook_badge": p["badge"],
            "top_hook": f"{p['line1']}\n{p['line2']}",
            "hook_line1": p["line1"],
            "hook_line2": p["line2"],
            "hook_line3": p["line3"],
            "attention_point": p["attention_driver"],
            "recommended_sfx": p["default_sfx"]
        })
    elif heatmap and len(heatmap) > 5:
        max_val = max((pt.get("value", 0) for pt in heatmap), default=1.0) or 1.0
        window_size = min(target_duration, duration)
        step = max(3.0, duration / 80.0)
        candidates = []
        
        t = 0.0
        while t + window_size <= duration:
            vals = [
                pt.get("value", 0) for pt in heatmap
                if pt.get("start_time", 0) >= t and pt.get("end_time", 0) <= t + window_size
            ]
            avg_score = (sum(vals) / len(vals)) if vals else 0.0
            candidates.append({
                "start_time": t,
                "end_time": t + window_size,
                "score": avg_score
            })
            t += step
            
        # Sort by score descending and select non-overlapping top peaks
        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = []
        for cand in candidates:
            overlap = False
            for s in selected:
                # Max overlap allowed: up to 8 seconds or 20%
                overlap_dur = max(0.0, min(cand["end_time"], s["end_time"]) - max(cand["start_time"], s["start_time"]))
                if overlap_dur > 8.0:
                    overlap = True
                    break
            if not overlap:
                selected.append(cand)
            if len(selected) >= min_moments:
                break
                
        # If we couldn't get min_moments due to strict overlap, relax overlap to reach min_moments
        if len(selected) < min_moments:
            for cand in candidates:
                if cand not in selected:
                    overlap_dur = max(
                        [max(0.0, min(cand["end_time"], s["end_time"]) - max(cand["start_time"], s["start_time"])) for s in selected],
                        default=0.0
                    )
                    if overlap_dur < window_size * 0.5:
                        selected.append(cand)
                if len(selected) >= min_moments:
                    break

        for i, mom in enumerate(selected):
            start = mom["start_time"]
            end = mom["end_time"]
            virality_pct = int(min(99, max(75, (mom["score"] / max_val) * 98)))
            
            chap_title = ""
            for ch in chapters:
                if ch.get("start_time", 0) <= start <= ch.get("end_time", duration):
                    chap_title = ch.get("title", "")
                    break
            
            p = VIRAL_HOOK_PRESETS[i % len(VIRAL_HOOK_PRESETS)]
            label = chap_title if chap_title else f"Heatmap Retention Peak #{i+1}"
            
            viral_moments.append({
                "id": i + 1,
                "title": label,
                "start_time": start,
                "end_time": end,
                "start_fmt": format_time(start),
                "end_fmt": format_time(end),
                "duration": int(end - start),
                "virality_score": virality_pct,
                "hook_badge": p["badge"],
                "top_hook": f"{p['line1']}\n{p['line2']}",
                "hook_line1": p["line1"],
                "hook_line2": p["line2"],
                "hook_line3": p["line3"],
                "attention_point": p["attention_driver"],
                "recommended_sfx": p["default_sfx"]
            })

    # Supplementary moments if we have fewer than min_moments
    if len(viral_moments) < min_moments and duration > target_duration:
        if chapters and len(chapters) >= 2:
            existing_starts = [m["start_time"] for m in viral_moments]
            for ch in chapters:
                ch_start = float(ch.get("start_time", 0))
                clip_start = ch_start
                clip_end = min(ch_start + target_duration, duration)
                if clip_end - clip_start >= 15:
                    if not any(abs(clip_start - es) < 15 for es in existing_starts):
                        idx = len(viral_moments)
                        p = VIRAL_HOOK_PRESETS[idx % len(VIRAL_HOOK_PRESETS)]
                        viral_moments.append({
                            "id": idx + 1,
                            "title": ch.get("title") or f"Chapter Moment #{idx+1}",
                            "start_time": clip_start,
                            "end_time": clip_end,
                            "start_fmt": format_time(clip_start),
                            "end_fmt": format_time(clip_end),
                            "duration": int(clip_end - clip_start),
                            "virality_score": max(78, 96 - (idx * 2)),
                            "hook_badge": p["badge"],
                            "top_hook": f"{p['line1']}\n{p['line2']}",
                            "hook_line1": p["line1"],
                            "hook_line2": p["line2"],
                            "hook_line3": p["line3"],
                            "attention_point": p["attention_driver"],
                            "recommended_sfx": p["default_sfx"]
                        })
                        existing_starts.append(clip_start)
                if len(viral_moments) >= min_moments:
                    break

        if len(viral_moments) < min_moments:
            needed_now = min_moments - len(viral_moments)
            fractions = [(k + 1) / (needed_now + 2) for k in range(needed_now + 2)]
            for frac in fractions:
                start = max(0.0, min(duration - target_duration, duration * frac))
                end = min(duration, start + target_duration)
                if end - start >= 15:
                    if not any(abs(start - m["start_time"]) < 15 for m in viral_moments):
                        idx = len(viral_moments)
                        p = VIRAL_HOOK_PRESETS[idx % len(VIRAL_HOOK_PRESETS)]
                        viral_moments.append({
                            "id": idx + 1,
                            "title": f"Strategic Moment #{idx+1}",
                            "start_time": start,
                            "end_time": end,
                            "start_fmt": format_time(start),
                            "end_fmt": format_time(end),
                            "duration": int(end - start),
                            "virality_score": max(76, 94 - (idx * 3)),
                            "hook_badge": p["badge"],
                            "top_hook": f"{p['line1']}\n{p['line2']}",
                            "hook_line1": p["line1"],
                            "hook_line2": p["line2"],
                            "hook_line3": p["line3"],
                            "attention_point": p["attention_driver"],
                            "recommended_sfx": p["default_sfx"]
                        })
                if len(viral_moments) >= min_moments:
                    break
                    
    return {
        "url": url,
        "title": title,
        "uploader": uploader,
        "duration": duration,
        "duration_fmt": format_time(duration),
        "thumbnail": thumbnail,
        "viral_moments": viral_moments,
        "target_duration": int(target_duration),
        "total_moments": len(viral_moments),
        "has_subtitles": bool(info.get("subtitles") or info.get("automatic_captions"))
    }

_whisper_model = None

def get_whisper_model():
    """Lazy load Whisper model for local transcription (configurable via env vars)."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            model_size = os.environ.get("WHISPER_MODEL", "tiny").strip() or "tiny"
            device = os.environ.get("WHISPER_DEVICE", "cpu").strip() or "cpu"
            compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"
            _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except Exception as e:
            print("[Whisper] Failed to load WhisperModel:", e)
            _whisper_model = False
    return _whisper_model

def extract_subtitles_whisper(media_path):
    """Transcribe video audio locally using Whisper AI with word-level timestamps."""
    model = get_whisper_model()
    if not model:
        return []
        
    try:
        segments, _ = model.transcribe(media_path, word_timestamps=True)
        cues = []
        for segment in segments:
            if segment.words:
                for w in segment.words:
                    word_clean = w.word.strip()
                    if word_clean:
                        cues.append({
                            "start": max(0.0, float(w.start)),
                            "end": max(float(w.start) + 0.1, float(w.end)),
                            "text": word_clean
                        })
            else:
                text_clean = segment.text.strip()
                if text_clean:
                    cues.append({
                        "start": max(0.0, float(segment.start)),
                        "end": max(float(segment.start) + 0.5, float(segment.end)),
                        "text": text_clean
                    })
        return cues
    except Exception as e:
        print("[Whisper] Error transcribing clip:", e)
        return []

def fetch_subtitles_for_range(url, start_time, end_time, media_path=None):
    """
    Primary: Local AI speech recognition (Whisper) on the downloaded clip.
    Fallback: YouTube caption extraction.
    """
    if media_path and os.path.exists(media_path):
        print(f"[Subtitles] Running AI Speech Recognition on {media_path}...")
        whisper_cues = extract_subtitles_whisper(media_path)
        if whisper_cues:
            print(f"[Subtitles] AI transcribed {len(whisper_cues)} words successfully!")
            return whisper_cues

    # Fallback to YouTube timedtext for online URLs
    if not is_local_path(url) and (url.startswith("http://") or url.startswith("https://")):
        try:
            ydl_opts = get_ydl_base_opts()
            ydl_opts.update({
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'extractor_args': {'youtube': {'player_client': ['web', 'android']}}
            })
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            captions = info.get("subtitles", {}).get("en") or info.get("automatic_captions", {}).get("en")
            if captions:
                sub_url = captions[0].get("url")
                if sub_url:
                    req = urllib.request.Request(sub_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        content = resp.read().decode('utf-8', errors='ignore')
                    if "events" in content:
                        data = json.loads(content)
                        cues = []
                        for ev in data.get("events", []):
                            t_start = (ev.get("tStartMs") or 0) / 1000.0
                            t_dur = (ev.get("dDurationMs") or 0) / 1000.0
                            t_end = t_start + t_dur
                            if t_end >= start_time and t_start <= end_time:
                                parts = [s.get("utf8", "").strip() for s in ev.get("segs", []) if s.get("utf8", "").strip()]
                                txt = " ".join(parts).strip()
                                if txt:
                                    cues.append({
                                        "start": max(0.0, t_start - start_time),
                                        "end": max(0.5, t_end - start_time),
                                        "text": txt
                                    })
                        if cues:
                            return cues
        except Exception as e:
            print("[Subtitles] Online caption fallback error:", e)
            
    return []

def generate_ass_subtitles(cues, style="3d_hormozi", top_hook="", header_lines=None):
    """
    Generate Advanced SubStation Alpha (ASS) file with:
    - 3D Extruded kinetic animated subtitles (Hormozi, MrBeast, Cyber, FireGold, Comic)
    - Pinned 2-3 line viral top header banner (e.g. "The Harsh Truth", "Wait for the End")
    """
    # 3D styles with deep layered extrusion, shadow offsets, and perspective
    styles_def = {
        "3d_hormozi": """Style: ViralSub,Impact,72,&H0000FFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,7,5,2,50,50,420,1""",
        "hormozi": """Style: ViralSub,Impact,72,&H0000FFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,7,5,2,50,50,420,1""",
        "3d_mrbeast": """Style: ViralSub,Arial Black,74,&H0000FF00,&H000000FF,&H00000000,&H90000000,-1,0,0,0,102,102,0,0,1,8,6,2,50,50,420,1""",
        "mrbeast": """Style: ViralSub,Arial Black,74,&H0000FF00,&H000000FF,&H00000000,&H90000000,-1,0,0,0,102,102,0,0,1,8,6,2,50,50,420,1""",
        "3d_cyber": """Style: ViralSub,Arial Black,70,&H00FFFF00,&H000000FF,&H001a0520,&H90FF0080,-1,0,0,0,100,100,0,0,1,7,6,2,50,50,420,1""",
        "cyber": """Style: ViralSub,Arial Black,70,&H00FFFF00,&H000000FF,&H001a0520,&H90FF0080,-1,0,0,0,100,100,0,0,1,7,6,2,50,50,420,1""",
        "3d_firegold": """Style: ViralSub,Impact,74,&H0000D7FF,&H000000FF,&H00001033,&H90000000,-1,0,0,0,102,102,0,0,1,7,6,2,50,50,420,1""",
        "3d_comic": """Style: ViralSub,Arial Black,72,&H00FFFFFF,&H000000FF,&H00000000,&H901010A0,-1,0,0,0,104,104,0,0,1,8,5,2,50,50,420,1""",
        "clean": """Style: ViralSub,Arial,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,50,50,420,1"""
    }
    
    style_key = style.lower()
    selected_style = styles_def.get(style_key, styles_def.get(f"3d_{style_key}", styles_def["3d_hormozi"]))
    
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        selected_style,
        """Style: HookLine1,Impact,48,&H0000C8FF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,7,4,8,30,30,120,1""",
        """Style: HookLine2,Arial Black,58,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,8,4,8,30,30,185,1""",
        """Style: HookLine3,Arial Black,42,&H00FFFF00,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,6,3,8,30,30,255,1""",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    
    def to_ass_time(sec):
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        cs = int((s - int(s)) * 100)
        return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"

    # Parse 2-3 Line Viral Header Banner (Pinned Top)
    parsed_lines = []
    if header_lines:
        if isinstance(header_lines, list):
            parsed_lines = [str(l).strip() for l in header_lines if str(l).strip()]
        elif isinstance(header_lines, str):
            parsed_lines = [l.strip() for l in header_lines.split("\n") if l.strip()]
    elif top_hook:
        if "\n" in top_hook:
            parsed_lines = [l.strip() for l in top_hook.split("\n") if l.strip()]
        elif " | " in top_hook:
            parsed_lines = [l.strip() for l in top_hook.split(" | ") if l.strip()]
        else:
            parsed_lines = [top_hook.strip()]

    # Limit to top 3 lines
    parsed_lines = parsed_lines[:3]

    if len(parsed_lines) == 1:
        clean_line = parsed_lines[0].replace("{", "").replace("}", "").upper()
        ass_lines.append(f"Dialogue: 2,0:00:00.00,0:02:00.00,HookLine2,,0,0,0,,{{\\an8\\pos(540,150)\\c&H0000FFFF\\3c&H00000000\\bord7\\shad4\\fs56\\b1}}{clean_line}")
    elif len(parsed_lines) == 2:
        l1 = parsed_lines[0].replace("{", "").replace("}", "").upper()
        l2 = parsed_lines[1].replace("{", "").replace("}", "").upper()
        ass_lines.append(f"Dialogue: 2,0:00:00.00,0:02:00.00,HookLine1,,0,0,0,,{{\\an8\\pos(540,135)\\c&H0000C8FF\\3c&H00000000\\bord7\\shad4\\fs48\\b1}}{l1}")
        ass_lines.append(f"Dialogue: 2,0:00:00.00,0:02:00.00,HookLine2,,0,0,0,,{{\\an8\\pos(540,195)\\c&H00FFFFFF\\3c&H00000000\\bord7\\shad4\\fs56\\b1}}{l2}")
    elif len(parsed_lines) >= 3:
        l1 = parsed_lines[0].replace("{", "").replace("}", "").upper()
        l2 = parsed_lines[1].replace("{", "").replace("}", "").upper()
        l3 = parsed_lines[2].replace("{", "").replace("}", "").upper()
        ass_lines.append(f"Dialogue: 2,0:00:00.00,0:02:00.00,HookLine1,,0,0,0,,{{\\an8\\pos(540,120)\\c&H0000C8FF\\3c&H00000000\\bord7\\shad4\\fs44\\b1}}{l1}")
        ass_lines.append(f"Dialogue: 2,0:00:00.00,0:02:00.00,HookLine2,,0,0,0,,{{\\an8\\pos(540,175)\\c&H00FFFFFF\\3c&H00000000\\bord7\\shad4\\fs54\\b1}}{l2}")
        ass_lines.append(f"Dialogue: 2,0:00:00.00,0:02:00.00,HookLine3,,0,0,0,,{{\\an8\\pos(540,240)\\c&H00FFFF00\\3c&H00000000\\bord6\\shad3\\fs40\\b1}}{l3}")
        
    if not cues:
        # If no speech detected, render engaging 3D hook captions throughout clip
        ass_lines.append(f"Dialogue: 0,0:00:00.50,0:00:06.00,ViralSub,,0,0,0,,{{\\t(0,75,\\fscx124\\fscy124)\\t(75,160,\\fscx100\\fscy100)\\c&H0000FFFF}}WAIT FOR IT{{\\c&H00FFFFFF}} 😱")
        ass_lines.append(f"Dialogue: 0,0:00:06.00,0:00:15.00,ViralSub,,0,0,0,,{{\\t(0,75,\\fscx124\\fscy124)\\t(75,160,\\fscx100\\fscy100)}}WATCH TILL THE {{\\c&H0000FF00}}END{{\\c&H00FFFFFF}} 🔥")
        ass_lines.append(f"Dialogue: 0,0:00:15.00,0:00:35.00,ViralSub,,0,0,0,,{{\\t(0,75,\\fscx124\\fscy124)\\t(75,160,\\fscx100\\fscy100)\\c&H0000FFFF}}DON'T MISS THIS{{\\c&H00FFFFFF}} ⚡")
        return "\n".join(ass_lines)
        
    # Color palette & kinetic 3D pop based on active style
    if "mrbeast" in style_key:
        active_color = "&H0000FF00"  # Electric Green
        accent_color = "&H0000FFFF"  # Yellow
        pop_in = "\\t(0,60,\\frz-4\\fscx125\\fscy125)\\t(60,130,\\frz2\\fscx106\\fscy106)\\t(130,190,\\frz0\\fscx100\\fscy100)"
    elif "cyber" in style_key:
        active_color = "&H00FFFF00"  # Neon Cyan
        accent_color = "&H00FF00FF"  # Hot Magenta
        pop_in = "\\frx10\\fry-6\\t(0,75,\\fscx122\\fscy122)\\t(75,150,\\fscx100\\fscy100)"
    elif "firegold" in style_key:
        active_color = "&H0000D7FF"  # Golden Amber
        accent_color = "&H000066FF"  # Flame Orange
        pop_in = "\\t(0,70,\\fscx126\\fscy126)\\t(70,150,\\fscx100\\fscy100)"
    elif "comic" in style_key:
        active_color = "&H00FFFFFF"  # Crisp White
        accent_color = "&H002222FF"  # Bold Crimson Red
        pop_in = "\\frz-3\\t(0,70,\\fscx125\\fscy125)\\t(70,150,\\fscx100\\fscy100)"
    else: # 3d_hormozi default
        active_color = "&H0000FFFF"  # Vibrant Yellow
        accent_color = "&H0000C8FF"  # Warm Gold
        pop_in = "\\t(0,75,\\fscx124\\fscy124)\\t(75,160,\\fscx100\\fscy100)"

    # Group words into punchy 2-3 word phrases for maximum viral retention
    chunk_size = 3
    i = 0
    while i < len(cues):
        chunk = cues[i:i + chunk_size]
        i += chunk_size
        
        c_start = chunk[0]["start"]
        c_end = chunk[-1]["end"]
        # Ensure minimum visible duration of 0.7s so words don't flash too quickly
        c_end = max(c_start + 0.7, c_end)
        
        words_text = [c["text"].upper().replace("{", "").replace("}", "") for c in chunk]
        
        # 3D animated highlight on active word
        if len(words_text) == 1:
            styled_text = f"{{{pop_in}\\c{active_color}\\xshad4\\yshad5}}{words_text[0]}{{\\c&H00FFFFFF\\xshad2\\yshad2\\fscx100\\fscy100}}"
        elif len(words_text) == 2:
            styled_text = f"{words_text[0]} {{{pop_in}\\c{active_color}\\xshad4\\yshad5}}{words_text[1]}{{\\c&H00FFFFFF\\xshad2\\yshad2\\fscx100\\fscy100}}"
        else:
            styled_text = f"{words_text[0]} {{{pop_in}\\c{active_color}\\xshad4\\yshad5}}{words_text[1]}{{\\c&H00FFFFFF\\xshad2\\yshad2\\fscx100\\fscy100}} {words_text[2]}"
            
        ass_lines.append(
            f"Dialogue: 0,{to_ass_time(c_start)},{to_ass_time(c_end)},ViralSub,,0,0,0,,{styled_text}"
        )
            
    return "\n".join(ass_lines)


def check_audio_stream_exists(video_path):
    """Probe if video file contains a valid audio stream."""
    try:
        cmd = [FFMPEG, "-i", video_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return "Audio:" in res.stderr
    except Exception:
        return True


def generate_short(
    url,
    start_time,
    end_time,
    layout="blur",
    subtitle_style="3d_hormozi",
    top_hook="WAIT TILL THE END 😱",
    header_lines=None,
    sfx_enabled=True,
    sfx_hook="vine_boom",
    dynamic_zoom=True,
    high_quality=True,
    copyright_shield=True,
    output_dir="output",
    custom_title=None,
    progress_callback=None,
    cancel_check=None
):
    """
    Super Advanced 9:16 Shorts Generation:
    - Downloads/cuts targeted 15-60s clip with 1080p source prioritization
    - Frames to 9:16 portrait (Blurred background, Smart Center Crop, or Split Screen)
    - 3D Extruded kinetic animated subtitles (Hormozi, MrBeast, Cyber, FireGold, Comic)
    - Customizable 2-3 line viral top header card (e.g. "The Harsh Truth", "Wait for the End")
    - Viral Meme Sound Effects (Vine Boom, Whoosh, Ding, Pop) mixed into opening hook
    - Dynamic camera zoom & rhythmic punch-ins to maintain audience attention
    - Studio Master Quality (CRF 17, Lanczos scaling, EBU R128 loudness normalization)
    """
    if cancel_check and cancel_check():
        raise RuntimeError("Job was cancelled by user")

    if progress_callback:
        progress_callback("Initializing segment extraction", 5)

    os.makedirs(output_dir, exist_ok=True)
    start_sec = parse_time(start_time)
    end_sec = parse_time(end_time)
    clip_duration = end_sec - start_sec
    
    if clip_duration <= 0:
        clip_duration = 35.0
        end_sec = start_sec + 35.0
    elif clip_duration > 60:
        end_sec = start_sec + 60.0
        clip_duration = 60.0
        
    clip_id = f"short_{int(start_sec)}_{int(end_sec)}_{int(clip_duration)}s"
    raw_clip_path = os.path.join(output_dir, f"{clip_id}_raw.mp4")
    final_output_path = os.path.join(output_dir, f"{clip_id}.mp4")
    ass_sub_path = os.path.join(output_dir, f"{clip_id}.ass")
    
    # Clean up previous partials if any
    for p in [raw_clip_path, final_output_path, ass_sub_path]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    if progress_callback:
        progress_callback("Extracting video segment", 15)

    # Step 1: Extract targeted section (Direct local cut or YouTube download)
    downloaded = False
    
    # Method 0: Direct local video cutting
    if is_local_path(url):
        local_source = resolve_local_path(url)
        print(f"[Studio] Cutting segment from local video: {local_source} ({start_sec}s -> {end_sec}s)")
        cmd = [
            FFMPEG, "-y",
            "-ss", str(start_sec), "-to", str(end_sec),
            "-i", local_source,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-c:a", "aac", "-b:a", "256k",
            "-movflags", "+faststart",
            raw_clip_path
        ]
        proc = run_cancellable_subprocess(cmd, cancel_check=cancel_check, timeout=120)
        if proc.returncode == 0 and os.path.exists(raw_clip_path) and os.path.getsize(raw_clip_path) > 1000:
            downloaded = True
        else:
            print(f"[Studio] Local cut stderr: {proc.stderr}")

    # Method A: Direct stream URL seek with FFmpeg (fastest & high reliability for YouTube)
    if not downloaded:
        try:
            ydl_opts = get_ydl_base_opts()
            ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            req_formats = info.get("requested_formats") or []
            if len(req_formats) >= 2:
                v_url = req_formats[0].get("url")
                a_url = req_formats[1].get("url")
                if v_url and a_url:
                    cmd = [
                        FFMPEG, "-y",
                        "-ss", str(start_sec), "-to", str(end_sec), "-i", v_url,
                        "-ss", str(start_sec), "-to", str(end_sec), "-i", a_url,
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                        "-c:a", "aac", "-b:a", "256k",
                        "-movflags", "+faststart",
                        raw_clip_path
                    ]
                    proc = run_cancellable_subprocess(cmd, cancel_check=cancel_check, timeout=120)
                    if proc.returncode == 0 and os.path.exists(raw_clip_path) and os.path.getsize(raw_clip_path) > 10000:
                        downloaded = True
            elif info.get("url"):
                direct_url = info.get("url")
                cmd = [
                    FFMPEG, "-y",
                    "-ss", str(start_sec), "-to", str(end_sec), "-i", direct_url,
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "256k",
                    "-movflags", "+faststart",
                    raw_clip_path
                ]
                proc = run_cancellable_subprocess(cmd, cancel_check=cancel_check, timeout=120)
                if proc.returncode == 0 and os.path.exists(raw_clip_path) and os.path.getsize(raw_clip_path) > 10000:
                    downloaded = True
        except Exception as e:
            print(f"[Download] Direct stream seek notice: {e}. Trying standard yt-dlp downloader...")

    # Method B: yt-dlp range download fallback
    if not downloaded and not is_local_path(url):
        ydl_opts = get_ydl_base_opts()
        ydl_opts.update({
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            'outtmpl': raw_clip_path,
            'download_ranges': yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
            'force_keyframes_at_cuts': True,
            'ffmpeg_location': FFMPEG,
        })
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"[Download] Range download warning: {e}. Trying fallback...")
            
    # Check if download succeeded or if a different extension was generated
    if not os.path.exists(raw_clip_path) or os.path.getsize(raw_clip_path) < 1000:
        base_dir = os.path.dirname(raw_clip_path)
        base_prefix = os.path.splitext(os.path.basename(raw_clip_path))[0]
        for fname in os.listdir(base_dir):
            if fname.startswith(base_prefix) and not fname.endswith(".ass") and not fname.endswith(".part"):
                cand = os.path.join(base_dir, fname)
                if os.path.getsize(cand) > 10000:
                    raw_clip_path = cand
                    break

    if not os.path.exists(raw_clip_path) or os.path.getsize(raw_clip_path) < 1000:
        raise RuntimeError("Failed to obtain video segment. Please check the video source and timestamp range.")

    if cancel_check and cancel_check():
        raise RuntimeError("Job was cancelled by user")

    if progress_callback:
        progress_callback("Transcribing speech with Whisper AI", 40)

    # Step 2: Fetch and format 3D animated subtitles & multi-line viral header
    cues = fetch_subtitles_for_range(url, start_sec, end_sec, media_path=raw_clip_path)
    ass_content = generate_ass_subtitles(
        cues,
        style=subtitle_style,
        top_hook=top_hook,
        header_lines=header_lines
    )
    with open(ass_sub_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    if cancel_check and cancel_check():
        raise RuntimeError("Job was cancelled by user")

    if progress_callback:
        progress_callback("Rendering 9:16 vertical video & mixing audio", 65)

    # Step 3: Compose Advanced FFmpeg Video & Audio Graph
    sub_arg = os.path.abspath(ass_sub_path).replace("\\", "/").replace(":", "\\:")
    
    # 9:16 Framing
    if layout == "crop":
        base_video_filter = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920"
        )
    elif layout == "split":
        base_video_filter = (
            f"[0:v]split=2[top][bot];"
            f"[top]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[vtop];"
            f"[bot]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,boxblur=18:5[vbot];"
            f"[vtop][vbot]vstack"
        )
    else: # default 'blur'
        base_video_filter = (
            f"[0:v]split=2[main][blur];"
            f"[blur]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=26:6[bg];"
            f"[main]scale=1080:608[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )

    # Dynamic camera zoom & rhythmic punch-ins
    if dynamic_zoom:
        zoom_filter = (
            f",fade=t=in:st=0:d=0.3:color=black,"
            f"crop=w='if(between(mod(t,6),2.2,4.4),1080/1.12,1080)':"
            f"h='if(between(mod(t,6),2.2,4.4),1920/1.12,1920)':"
            f"x='(in_w-out_w)/2':y='(in_h-out_h)/2',scale=1080:1920"
        )
        base_video_filter += zoom_filter

    if copyright_shield:
        base_video_filter += ",eq=contrast=1.04:saturation=1.05:brightness=0.01"

    video_filter = f"{base_video_filter},subtitles='{sub_arg}'[outv]"

    # Audio Handling & Viral Meme SFX Mixing
    has_audio = check_audio_stream_exists(raw_clip_path)
    
    sfx_path = None
    if sfx_enabled and sfx_hook and sfx_hook.lower() != "none":
        candidate_sfx = os.path.join(WORKSPACE_DIR, "assets", "sfx", f"{sfx_hook.lower()}.wav")
        if os.path.exists(candidate_sfx):
            sfx_path = candidate_sfx
            print(f"[Studio] Injecting viral meme SFX ({sfx_hook}) at hook entry!")

    cmd = [FFMPEG, "-y", "-i", raw_clip_path]
    
    if sfx_path and has_audio:
        cmd.extend(["-i", sfx_path])
        # Mix SFX at 250ms with 0.85 volume
        audio_filter = "[1:a]adelay=250|250,volume=0.85[sfx];[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=2"
    elif has_audio:
        audio_filter = "[0:a]anull"
    else:
        # If no audio track exists, generate silence
        audio_filter = "aevalsrc=0:d=60"

    if copyright_shield and has_audio:
        audio_filter += ",asetrate=44100*1.015,aresample=44100"

    if high_quality and has_audio:
        audio_filter += ",loudnorm=I=-14:LRA=7:TP=-1.5"

    audio_filter += "[outa]"

    full_filter = f"{video_filter};{audio_filter}"

    cmd.extend([
        "-filter_complex", full_filter,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "medium" if high_quality else "veryfast",
        "-crf", "17" if high_quality else "20",
        "-sws_flags", "lanczos+accurate_rnd" if high_quality else "bicubic",
        "-c:a", "aac",
        "-b:a", "256k" if high_quality else "192k",
        "-movflags", "+faststart",
        final_output_path
    ])
    
    proc = run_cancellable_subprocess(cmd, cancel_check=cancel_check, timeout=300)
    if proc.returncode != 0:
        print(f"[FFmpeg] Advanced render notice, retrying with fallback audio: {proc.stderr[-300:]}")
        # Fallback without complex audio mix if anything failed
        cmd_fallback = [
            FFMPEG, "-y",
            "-i", raw_clip_path,
            "-filter_complex", video_filter,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            final_output_path
        ]
        proc = run_cancellable_subprocess(cmd_fallback, cancel_check=cancel_check, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg error: {proc.stderr[-500:]}")
        
    # Cleanup raw clip
    if os.path.exists(raw_clip_path):
        try:
            os.remove(raw_clip_path)
        except Exception:
            pass

    if cancel_check and cancel_check():
        raise RuntimeError("Job was cancelled by user")

    if progress_callback:
        progress_callback("Finalizing MP4 video & metadata", 95)
            
    # Auto-generate viral title and tags
    clean_hook = re.sub(r'[^\w\s]', '', top_hook.split("\n")[0] if "\n" in top_hook else top_hook).strip()
    if custom_title and len(custom_title.strip()) > 2 and "Moment" not in custom_title:
        yt_title = f"{custom_title.strip()} - {clean_hook} 🤯 #Shorts"
    else:
        yt_title = f"{clean_hook} That Changed Everything 🤯 #Shorts"
        
    yt_description = (
        f"The most viral moment from this video! 🔥\n\n"
        f"Watch till the end for the key takeaway. Subscribe for daily high-value shorts!\n\n"
        f"#Shorts #viral #trending #podcast #mindset #motivation"
    )
    yt_tags = ["#Shorts", "#viral", "#trending", "#youtubeshorts", "#clips", f"#{clean_hook.replace(' ', '')}"]
    
    return {
        "status": "success",
        "video_filename": os.path.basename(final_output_path),
        "video_path": os.path.abspath(final_output_path),
        "file_size_mb": round(os.path.getsize(final_output_path) / (1024 * 1024), 2),
        "duration": int(clip_duration),
        "suggested_title": yt_title,
        "suggested_description": yt_description,
        "suggested_tags": yt_tags
    }


def create_zip_bundle(video_paths, zip_filename="viral_shorts_pack.zip", output_dir="output"):
    """Bundle multiple generated MP4 shorts into a single downloadable ZIP archive."""
    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, zip_filename)
    if os.path.exists(zip_path):
        try:
            os.remove(zip_path)
        except Exception:
            pass
            
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for vp in video_paths:
            if vp and os.path.exists(vp):
                zf.write(vp, arcname=os.path.basename(vp))
    return zip_path


def generate_shorts_batch(
    url,
    clips,
    layout="blur",
    subtitle_style="3d_hormozi",
    header_lines=None,
    sfx_enabled=True,
    sfx_hook="vine_boom",
    dynamic_zoom=True,
    high_quality=True,
    copyright_shield=True,
    output_dir="output",
    progress_callback=None,
    cancel_check=None
):
    """
    Batch generate multiple (4-5+) 9:16 vertical shorts with:
    - 3D Subtitles
    - Multi-line viral headers
    - Viral Meme SFX
    - Dynamic camera zooms
    - Studio master quality
    """
    os.makedirs(output_dir, exist_ok=True)
    results = []
    total = len(clips)
    
    for idx, clip in enumerate(clips):
        if cancel_check and cancel_check():
            print(f"[Batch] Cancellation detected, aborting at clip {idx + 1}/{total}")
            break

        title = clip.get("title") or f"Short #{idx + 1}"
        start_time = clip.get("start_time") or clip.get("start_fmt") or "00:00"
        end_time = clip.get("end_time") or clip.get("end_fmt") or "00:35"
        
        # Individual clip hook or batch default
        clip_hook = clip.get("top_hook") or HOOK_TEMPLATES[idx % len(HOOK_TEMPLATES)]
        clip_headers = clip.get("header_lines") or header_lines
        if not clip_headers and clip.get("hook_line1") and clip.get("hook_line2"):
            clip_headers = [clip.get("hook_line1"), clip.get("hook_line2")]
            if clip.get("hook_line3"):
                clip_headers.append(clip.get("hook_line3"))
                
        clip_sfx = clip.get("recommended_sfx") or sfx_hook
        
        def sub_progress(stage, pct):
            if progress_callback:
                clip_base = int((idx / max(1, total)) * 85)
                clip_span = max(1, int((1.0 / max(1, total)) * 85))
                total_pct = min(90, clip_base + int((pct / 100.0) * clip_span))
                progress_callback(f"Short {idx + 1}/{total} ({title}): {stage}", total_pct)

        if progress_callback:
            sub_progress("Starting clip generation", 5)

        print(f"\n[Batch] Processing Short {idx + 1}/{total}: '{title}' ({start_time} -> {end_time}) [3D Style: {subtitle_style}, SFX: {clip_sfx}]")
        
        try:
            res = generate_short(
                url=url,
                start_time=start_time,
                end_time=end_time,
                layout=layout,
                subtitle_style=subtitle_style,
                top_hook=clip_hook,
                header_lines=clip_headers,
                sfx_enabled=sfx_enabled,
                sfx_hook=clip_sfx,
                dynamic_zoom=dynamic_zoom,
                high_quality=high_quality,
                copyright_shield=copyright_shield,
                output_dir=output_dir,
                custom_title=title,
                progress_callback=sub_progress,
                cancel_check=cancel_check
            )
            res["id"] = clip.get("id", idx + 1)
            res["title"] = title
            res["virality_score"] = clip.get("virality_score", 92)
            res["hook_badge"] = clip.get("hook_badge", BADGE_TEMPLATES[min(idx, len(BADGE_TEMPLATES)-1)])
            res["attention_point"] = clip.get("attention_point", "High viewer engagement & retention hook")
            res["download_url"] = f"/output/{res['video_filename']}"
            results.append(res)
        except Exception as e:
            print(f"[Batch] Error generating Short #{idx + 1}: {e}")
            results.append({
                "id": clip.get("id", idx + 1),
                "title": title,
                "status": "error",
                "error": str(e)
            })
        
    valid_paths = [r["video_path"] for r in results if r.get("status") == "success" and os.path.exists(r.get("video_path", ""))]
    zip_path = None
    if valid_paths and not (cancel_check and cancel_check()):
        if progress_callback:
            progress_callback("Packaging batch ZIP archive", 95)
        zip_path = create_zip_bundle(valid_paths, zip_filename="viral_shorts_pack.zip", output_dir=output_dir)
    
    return {
        "status": "success",
        "total_requested": total,
        "total_generated": len(valid_paths),
        "results": results,
        "zip_path": zip_path,
        "zip_filename": os.path.basename(zip_path) if zip_path else None,
        "zip_download_url": f"/output/{os.path.basename(zip_path)}" if zip_path else None
    }
