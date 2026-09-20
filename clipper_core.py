import os
import sys
import json
import re
import math
import subprocess
import tempfile
import urllib.request
from pathlib import Path

# Ensure nodejs is in PATH for yt-dlp JS runtime
NODE_PATH = r"C:\Program Files\nodejs"
if os.path.exists(NODE_PATH) and NODE_PATH not in os.environ.get("PATH", ""):
    os.environ["PATH"] = NODE_PATH + ";" + os.environ.get("PATH", "")

import imageio_ffmpeg
import yt_dlp

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.path.join(WORKSPACE_DIR, "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    import shutil
    try:
        shutil.copyfile(imageio_ffmpeg.get_ffmpeg_exe(), FFMPEG)
    except Exception:
        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Add workspace directory to PATH so yt-dlp and ffmpeg are universally discoverable
if WORKSPACE_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = WORKSPACE_DIR + ";" + os.environ.get("PATH", "")


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

def analyze_video(url):
    """Extract metadata, chapters, and identify the top viral 30-40s moments using YouTube's heatmap."""
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    duration = info.get("duration") or 0
    title = info.get("title") or "Unknown Video"
    uploader = info.get("uploader") or info.get("channel") or "Unknown Creator"
    thumbnail = info.get("thumbnail") or ""
    chapters = info.get("chapters") or []
    heatmap = info.get("heatmap") or []
    
    # Calculate viral moments
    viral_moments = []
    
    # If video is already 40 seconds or less, the entire video is a candidate
    if duration <= 40:
        viral_moments.append({
            "id": 1,
            "title": "Full Viral Highlight",
            "start_time": 0.0,
            "end_time": float(duration),
            "start_fmt": "00:00",
            "end_fmt": format_time(duration),
            "duration": int(duration),
            "virality_score": 98,
            "hook_badge": "🔥 FULL CLIP"
        })
    elif heatmap and len(heatmap) > 5:
        # YouTube provides an array of points with start_time, end_time, and value (0.0 to 1.0)
        # Find peak windows of 30-40 seconds
        max_val = max((pt.get("value", 0) for pt in heatmap), default=1.0) or 1.0
        
        # Target 35s golden duration
        window_size = min(35.0, float(duration))
        step = max(5.0, duration / 50.0)
        candidates = []
        
        t = 0.0
        while t + window_size <= duration:
            # Calculate average heatmap value in this window
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
                if max(cand["start_time"], s["start_time"]) < min(cand["end_time"], s["end_time"]):
                    overlap = True
                    break
            if not overlap:
                selected.append(cand)
            if len(selected) >= 5:
                break
                
        # Format selected viral moments
        for i, mom in enumerate(selected):
            start = mom["start_time"]
            end = mom["end_time"]
            virality_pct = int(min(99, max(68, (mom["score"] / max_val) * 98)))
            
            # Find closest chapter title if any
            chap_title = ""
            for ch in chapters:
                if ch.get("start_time", 0) <= start <= ch.get("end_time", duration):
                    chap_title = ch.get("title", "")
                    break
            
            label = chap_title if chap_title else f"High-Retention Moment #{i+1}"
            
            viral_moments.append({
                "id": i + 1,
                "title": label,
                "start_time": start,
                "end_time": end,
                "start_fmt": format_time(start),
                "end_fmt": format_time(end),
                "duration": int(end - start),
                "virality_score": virality_pct,
                "hook_badge": "🔥 TOP VIRAL PEAK" if i == 0 else ("🚀 HIGH ENGAGEMENT" if i == 1 else "⚡ AUDIENCE HOOK")
            })
    else:
        # Fallback if no heatmap: use chapters or strategic points (20%, 40%, 65%, 80% of video)
        if chapters and len(chapters) >= 2:
            for i, ch in enumerate(chapters[:5]):
                ch_start = ch.get("start_time", 0)
                ch_end = ch.get("end_time", ch_start + 35)
                clip_start = ch_start
                clip_end = min(ch_start + 35, duration)
                if clip_end - clip_start >= 15:
                    viral_moments.append({
                        "id": i + 1,
                        "title": ch.get("title") or f"Key Chapter #{i+1}",
                        "start_time": clip_start,
                        "end_time": clip_end,
                        "start_fmt": format_time(clip_start),
                        "end_fmt": format_time(clip_end),
                        "duration": int(clip_end - clip_start),
                        "virality_score": 95 - (i * 4),
                        "hook_badge": "🔥 CHAPTER HOOK" if i == 0 else "⚡ KEY TOPIC"
                    })
        else:
            # Sample interval fallback
            sample_points = [0.15, 0.35, 0.55, 0.75]
            for i, frac in enumerate(sample_points):
                start = max(0.0, min(float(duration) - 35.0, float(duration) * frac))
                end = min(float(duration), start + 35.0)
                if end > start:
                    viral_moments.append({
                        "id": i + 1,
                        "title": f"Strategic Moment #{i+1}",
                        "start_time": start,
                        "end_time": end,
                        "start_fmt": format_time(start),
                        "end_fmt": format_time(end),
                        "duration": int(end - start),
                        "virality_score": 92 - (i * 5),
                        "hook_badge": "🔥 VIRAL HIGHLIGHT" if i == 0 else "⚡ ENGAGING MOMENT"
                    })

                    
    return {
        "url": url,
        "title": title,
        "uploader": uploader,
        "duration": duration,
        "duration_fmt": format_time(duration),
        "thumbnail": thumbnail,
        "viral_moments": viral_moments,
        "has_subtitles": bool(info.get("subtitles") or info.get("automatic_captions"))
    }

_whisper_model = None

def get_whisper_model():
    """Lazy load Whisper tiny model for fast local transcription."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
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

    # Fallback to YouTube timedtext
    try:
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'extractor_args': {'youtube': {'player_client': ['web', 'android']}}
        }
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

def generate_ass_subtitles(cues, style="hormozi", top_hook=""):
    """Generate Advanced SubStation Alpha (ASS) file with animated highlight styles."""
    # Using universally available Windows fonts (Impact, Arial Black, Arial)
    styles_def = {
        "hormozi": """Style: ViralSub,Impact,68,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,50,50,420,1""",
        "mrbeast": """Style: ViralSub,Arial Black,72,&H0000FF00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,105,105,0,0,1,7,4,2,50,50,420,1""",
        "cyber": """Style: ViralSub,Arial Black,68,&H00FFFF00,&H000000FF,&H00000000,&H80FF0080,-1,0,0,0,100,100,0,0,1,6,4,2,50,50,420,1""",
        "clean": """Style: ViralSub,Arial,62,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,50,50,420,1"""
    }
    
    selected_style = styles_def.get(style, styles_def["hormozi"])
    
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
        """Style: HookHeader,Impact,64,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,8,40,40,160,1""",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    
    def to_ass_time(sec):
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        cs = int((s - int(s)) * 100)
        return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"

    # Top hook banner event (displays for entire video if provided)
    if top_hook:
        clean_hook = top_hook.replace("{", "").replace("}", "").upper()
        ass_lines.append(f"Dialogue: 1,0:00:00.00,0:01:00.00,HookHeader,,0,0,0,,{{\\c&H0000FFFF}}{clean_hook}")
        
    if not cues:
        # If no speech detected, render engaging hook captions throughout clip
        ass_lines.append(f"Dialogue: 0,0:00:00.50,0:00:06.00,ViralSub,,0,0,0,,{{\\c&H0000FFFF}}WAIT FOR IT{{\\c&H00FFFFFF}} 😱")
        ass_lines.append(f"Dialogue: 0,0:00:06.00,0:00:15.00,ViralSub,,0,0,0,,WATCH TILL THE {{\\c&H0000FF00}}END{{\\c&H00FFFFFF}} 🔥")
        ass_lines.append(f"Dialogue: 0,0:00:15.00,0:00:35.00,ViralSub,,0,0,0,,{{\\c&H0000FFFF}}DON'T MISS THIS{{\\c&H00FFFFFF}} ⚡")
        return "\n".join(ass_lines)
        
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
        
        # Color highlight active word
        highlight_color = "&H0000FFFF" if style == "hormozi" else ("&H0000FF00" if style == "mrbeast" else "&H00FFFF00")
        if len(words_text) == 1:
            styled_text = f"{{\\c{highlight_color}}}{words_text[0]}{{\\c&H00FFFFFF}}"
        elif len(words_text) == 2:
            styled_text = f"{words_text[0]} {{\\c{highlight_color}}}{words_text[1]}{{\\c&H00FFFFFF}}"
        else:
            styled_text = f"{words_text[0]} {{\\c{highlight_color}}}{words_text[1]}{{\\c&H00FFFFFF}} {words_text[2]}"
            
        ass_lines.append(
            f"Dialogue: 0,{to_ass_time(c_start)},{to_ass_time(c_end)},ViralSub,,0,0,0,,{styled_text}"
        )
            
    return "\n".join(ass_lines)


def generate_short(url, start_time, end_time, layout="blur", subtitle_style="hormozi", top_hook="WAIT TILL THE END 😱", copyright_shield=True, output_dir="output"):
    """
    Downloads targeted 30-40s section, frames to 9:16 vertical, generates animated subtitles,
    applies copyright shields, and renders final 1080x1920 MP4 video.
    """
    os.makedirs(output_dir, exist_ok=True)
    start_sec = parse_time(start_time)
    end_sec = parse_time(end_time)
    clip_duration = end_sec - start_sec
    
    if clip_duration <= 0 or clip_duration > 65:
        end_sec = start_sec + 35
        clip_duration = 35
        
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

    # Step 1: Download ONLY the targeted section using yt-dlp
    sec_start_fmt = format_time(start_sec)
    sec_end_fmt = format_time(end_sec)
    
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'outtmpl': raw_clip_path,
        'download_ranges': yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
        'force_keyframes_at_cuts': True,
        'ffmpeg_location': FFMPEG,
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        
    if not os.path.exists(raw_clip_path) or os.path.getsize(raw_clip_path) < 1000:
        # Fallback if download_ranges with format merger had an issue: try direct stream extraction
        fallback_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': raw_clip_path,
            'download_ranges': yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
            'ffmpeg_location': FFMPEG,
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(fallback_opts) as ydl:
            ydl.download([url])


    # Step 2: Fetch and format subtitles using local AI speech recognition (Whisper)
    cues = fetch_subtitles_for_range(url, start_sec, end_sec, media_path=raw_clip_path)
    ass_content = generate_ass_subtitles(cues, style=subtitle_style, top_hook=top_hook)
    with open(ass_sub_path, "w", encoding="utf-8") as f:
        f.write(ass_content)


    # Step 3: Compose FFmpeg filter graph
    # Layouts:
    # 1. 'blur': Blurred ambient fill (Opus Clip style)
    # 2. 'crop': Full 9:16 center crop
    # 3. 'split': Split-screen layout
    
    # Subtitle path formatted for FFmpeg filter on Windows
    sub_arg = os.path.abspath(ass_sub_path).replace("\\", "/").replace(":", "\\:")
    
    if layout == "crop":
        video_filter = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
        )
    elif layout == "split":
        video_filter = (
            f"[0:v]split=2[top][bot];"
            f"[top]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[vtop];"
            f"[bot]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,boxblur=15:5[vbot];"
            f"[vtop][vbot]vstack,"
        )
    else: # default 'blur'
        video_filter = (
            f"[0:v]split=2[main][blur];"
            f"[blur]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
            f"[main]scale=1080:608[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        )
        
    # Copyright shield visual tweaks (subtle saturation + contrast + vignette)
    if copyright_shield:
        video_filter += "eq=contrast=1.03:saturation=1.04:brightness=0.01,"
        
    # Burn in subtitles
    video_filter += f"subtitles='{sub_arg}'[outv]"
    
    # Audio filters: Copyright shield pitch shift (1.015x) + aresample
    if copyright_shield:
        audio_filter = "asetrate=44100*1.015,aresample=44100"
    else:
        audio_filter = "anull"

    cmd = [
        FFMPEG, "-y",
        "-i", raw_clip_path,
        "-filter_complex", video_filter,
        "-map", "[outv]",
        "-map", "0:a?",
        "-af", audio_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        final_output_path
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {proc.stderr[-500:]}")
        
    # Cleanup raw clip
    if os.path.exists(raw_clip_path):
        try:
            os.remove(raw_clip_path)
        except Exception:
            pass
            
    # Auto-generate viral title and tags
    yt_title = f"{top_hook.replace('😱', '').strip()} That Changed Everything 🤯 #Shorts"
    yt_description = (
        f"The most viral moment from this video! 🔥\n\n"
        f"Watch till the end for the key takeaway. Subscribe for daily high-value shorts!\n\n"
        f"#Shorts #viral #trending #podcast #mindset #motivation"
    )
    yt_tags = ["#Shorts", "#viral", "#trending", "#youtubeshorts", "#clips"]
    
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
