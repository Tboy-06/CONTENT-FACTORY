"""
CONTENT-FACTORY Engine: Universal CLI Controller (factory_cli)
--------------------------------------------------------------
The unified command-line entrypoint for OpenCode, Antigravity, or developers:
Usage:
  python backend/factory_cli.py create --topic "How the CIA used cats as spies"
  python backend/factory_cli.py cache --clear
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.engine.planner import plan_documentary, save_manifest
from backend.engine.audio_subs import process_manifest_audio
from backend.engine.assembler import render_beat_pass1, assemble_final_pass2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("factory_cli")


async def run_pipeline(topic: str, voice: str = "en-US-ChristopherNeural") -> str:
    job_id = int(time.time()) % 100000
    job_dir = os.path.abspath(f"jobs/{job_id}")
    output_mp4 = os.path.abspath(f"output/documentary_{job_id}_9x16.mp4")

    print(f"\n[CONTENT-FACTORY] Launching Documentary Engine for Job #{job_id}")
    print(f"Topic: '{topic}'")
    print(f"Voice: {voice}")

    # Step 1: Planning
    print("\n[Step 1/4] Planning 8-Sentence Documentary Beat Sheet...")
    manifest = await plan_documentary(topic, job_id)
    manifest_path = save_manifest(manifest, job_dir)
    print(f"  [OK] Manifest written with {len(manifest['sentences'])} sentences and 16 visual beats")

    # Step 2: Voice & Captions
    print("\n[Step 2/4] Synthesizing Voiceover & Generating Word Karaoke Subtitles...")
    manifest = await process_manifest_audio(manifest, job_dir, voice=voice)
    save_manifest(manifest, job_dir)
    print(f"  [OK] Audio synthesized ({manifest['total_duration']:.2f}s total duration)")
    print(f"  [OK] Word-synced .ASS captions compiled")

    # Step 3: Pass 1 Beat Rendering
    print("\n[Step 3/4] Rendering Pass 1 Kinetic Motion Cards & Treated Visual Beats...")
    all_beats = []
    for s in manifest.get("sentences", []):
        all_beats.extend(s.get("beats", []))

    for idx, beat in enumerate(all_beats):
        await render_beat_pass1(beat, job_dir)
        print(f"  [OK] Beat {idx+1}/{len(all_beats)}: [{beat.get('type')}] -> {beat.get('duration')}s")

    # Step 4: Pass 2 Master Assembly
    print("\n[Step 4/4] Executing Pass 2 Final Multi-Track Assembly...")
    success = await assemble_final_pass2(manifest, job_dir, output_mp4)

    if success and os.path.exists(output_mp4):
        size_mb = os.path.getsize(output_mp4) / (1024 * 1024)
        print("\n========================================================")
        print("DOCUMENTARY SHORT GENERATED SUCCESSFULLY!")
        print(f"Output Video: {output_mp4}")
        print(f"Size: {size_mb:.2f} MB  |  Format: 1080x1920 (9:16 Vertical)")
        print(f"Duration: {manifest['total_duration']:.2f} seconds")
        print("========================================================\n")
        return output_mp4
    else:
        print("\n[ERROR] Master assembly failed. Check logs.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="CONTENT-FACTORY Terminal Controller")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create", help="Create a documentary video from a topic")
    create_parser.add_argument("--topic", type=str, required=True, help="Topic of the documentary")
    create_parser.add_argument("--voice", type=str, default="en-US-ChristopherNeural", help="Edge-TTS voice")

    cache_parser = subparsers.add_parser("cache", help="Manage temporary storage")
    cache_parser.add_argument("--clear", action="store_true", help="Clear temporary files")

    args = parser.parse_args()

    if args.command == "create":
        asyncio.run(run_pipeline(args.topic, args.voice))
    elif args.command == "cache" and args.clear:
        import shutil
        if os.path.exists("temp"):
            shutil.rmtree("temp", ignore_errors=True)
            os.makedirs("temp", exist_ok=True)
        print("[OK] Temporary cache cleared.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
