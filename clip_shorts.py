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
    parser = argparse.ArgumentParser(description="Convert long YouTube videos or local video files into viral 9:16 Shorts")
    parser.add_argument("--url", "--file", "--input", dest="source", required=True, help="YouTube video URL or local video file path")
    parser.add_argument("--batch", action="store_true", help="Batch generate multiple shorts (default 4-5 shorts)")
    parser.add_argument("--count", type=int, default=5, help="Number of viral shorts to generate (default: 5)")
    parser.add_argument("--peak", type=int, default=1, help="Single viral moment peak rank to clip (1 to 10, default: 1)")
    parser.add_argument("--start", help="Custom start time (e.g. 14:20)")
    parser.add_argument("--end", help="Custom end time (e.g. 14:55)")
    parser.add_argument("--duration", type=int, default=35, help="Target duration in seconds (15-60s, default: 35s)")
    parser.add_argument("--layout", choices=["blur", "crop", "split"], default="blur", help="9:16 Layout (default: blur)")
    parser.add_argument("--style", choices=["hormozi", "mrbeast", "cyber", "clean"], default="hormozi", help="Subtitle style")
    parser.add_argument("--hook", default="WAIT TILL THE END 😱", help="Top hook banner text")
    parser.add_argument("--no-shield", action="store_true", help="Disable copyright shield audio pitch shift")
    parser.add_argument("--output-dir", default="output", help="Directory to save generated Shorts")
    
    args = parser.parse_args()
    
    print("\n🔍 Analyzing video and retention dynamics...")
    if clipper_core.is_local_path(args.source):
        analysis = clipper_core.analyze_local_video(args.source, target_duration=args.duration, min_moments=args.count)
    else:
        analysis = clipper_core.analyze_video(args.source, target_duration=args.duration, min_moments=args.count)
    
    print(f"🎬 Video: {analysis['title']}")
    print(f"👤 Channel: {analysis['uploader']}")
    print(f"⏱️ Duration: {analysis['duration_fmt']}")
    print(f"🔥 Detected {len(analysis['viral_moments'])} Viral Moments (0-60s):")
    
    for m in analysis["viral_moments"]:
        print(f"   [{m['id']}] {m['hook_badge']} ({m['virality_score']}% Viral Score) -> {m['start_fmt']} to {m['end_fmt']} ({m['duration']}s): {m['title']}")
        
    if args.batch:
        selected_clips = analysis["viral_moments"][:args.count]
        print(f"\n⚡ Batch generating top {len(selected_clips)} viral shorts in 9:16 vertical...")
        batch_res = clipper_core.generate_shorts_batch(
            url=args.source,
            clips=selected_clips,
            layout=args.layout,
            subtitle_style=args.style,
            copyright_shield=not args.no_shield,
            output_dir=args.output_dir
        )
        print("\n=======================================================")
        print(f"✅ {batch_res['total_generated']} SHORTS BATCH GENERATED SUCCESSFULLY!")
        if batch_res.get('zip_path'):
            print(f"📦 ZIP Archive: {batch_res['zip_path']}")
        for r in batch_res["results"]:
            if r.get("status") == "success":
                print(f"  • [{r['id']}] {r['video_filename']} ({r['duration']}s, {r['file_size_mb']}MB) -> Title: {r['suggested_title']}")
        print("=======================================================\n")
        return

    start_time = args.start
    end_time = args.end
    
    if not start_time:
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
        
    print(f"\n🚀 Extracting targeted segment and rendering 9:16 Short...")
    print(f"   Layout: {args.layout} | Subtitles: {args.style} | Copyright Shield: {not args.no_shield}")
    
    result = clipper_core.generate_short(
        url=args.source,
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
