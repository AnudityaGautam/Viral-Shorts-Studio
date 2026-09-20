#!/usr/bin/env python3
"""
Viral Shorts Clipper - CLI Tool
Automatically extracts viral 30-40s clips from long YouTube videos into 9:16 vertical Shorts.
Usage:
    py clip_shorts.py --url "https://www.youtube.com/watch?v=..."
    py clip_shorts.py --url "https://www.youtube.com/watch?v=..." --peak 1 --layout blur --style hormozi
"""

import argparse
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import clipper_core


def main():
    parser = argparse.ArgumentParser(description="Convert long YouTube videos into viral 9:16 Shorts")
    parser.add_argument("--url", required=True, help="YouTube video URL (podcast, interview, long video)")
    parser.add_argument("--peak", type=int, default=1, help="Viral moment peak rank to clip (1 to 5, default: 1)")
    parser.add_argument("--start", help="Custom start time (e.g. 14:20)")
    parser.add_argument("--end", help="Custom end time (e.g. 14:55)")
    parser.add_argument("--duration", type=int, default=35, help="Duration in seconds if only start is given (default: 35s)")
    parser.add_argument("--layout", choices=["blur", "crop", "split"], default="blur", help="9:16 Layout (default: blur)")
    parser.add_argument("--style", choices=["hormozi", "mrbeast", "cyber", "clean"], default="hormozi", help="Subtitle style")
    parser.add_argument("--hook", default="WAIT TILL THE END 😱", help="Top hook banner text")
    parser.add_argument("--no-shield", action="store_true", help="Disable copyright shield audio pitch shift")
    parser.add_argument("--output-dir", default="output", help="Directory to save generated Shorts")
    
    args = parser.parse_args()
    
    print("\n🔍 Analyzing video and YouTube retention heatmap...")
    analysis = clipper_core.analyze_video(args.url)
    
    print(f"🎬 Video: {analysis['title']}")
    print(f"👤 Channel: {analysis['uploader']}")
    print(f"⏱️ Duration: {analysis['duration_fmt']}")
    print(f"🔥 Detected {len(analysis['viral_moments'])} Viral Moments:")
    
    for m in analysis["viral_moments"]:
        print(f"   [{m['id']}] {m['hook_badge']} ({m['virality_score']}% Viral Score) -> {m['start_fmt']} to {m['end_fmt']} ({m['duration']}s): {m['title']}")
        
    start_time = args.start
    end_time = args.end
    
    if not start_time:
        # Pick chosen peak
        chosen = None
        for m in analysis["viral_moments"]:
            if m["id"] == args.peak:
                chosen = m
                break
        if not chosen and analysis["viral_moments"]:
            chosen = analysis["viral_moments"][0]
            
        start_time = chosen["start_fmt"]
        end_time = chosen["end_fmt"]
        print(f"\n✨ Selected Peak #{chosen['id']}: {start_time} -> {end_time} ({chosen['title']})")
    elif not end_time:
        start_sec = clipper_core.parse_time(start_time)
        end_time = clipper_core.format_time(start_sec + args.duration)
        
    print(f"\n🚀 Downloading targeted 30-40s segment and rendering 9:16 Short...")
    print(f"   Layout: {args.layout} | Subtitles: {args.style} | Copyright Shield: {not args.no_shield}")
    
    result = clipper_core.generate_short(
        url=args.url,
        start_time=start_time,
        end_time=end_time,
        layout=args.layout,
        subtitle_style=args.style,
        top_hook=args.hook,
        copyright_shield=not args.no_shield,
        output_dir=args.output_dir
    )
    
    print("\n=======================================================")
    print("✅ 9:16 SHORT GENERATED SUCCESSFULLY!")
    print(f"📁 Saved to: {result['video_path']}")
    print(f"📊 Size: {result['file_size_mb']} MB | Duration: {result['duration']} seconds")
    print(f"📝 Viral Title: {result['suggested_title']}")
    print(f"🏷️ Tags: {' '.join(result['suggested_tags'])}")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
