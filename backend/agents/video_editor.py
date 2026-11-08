from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.agents import BaseAgent, AgentResult, Tool, Job
from backend.agents.llm_client import get_gemini_client
from backend.vault import add_asset, get_latest_asset, log_event
from backend.config import get_settings
from backend.tools.nuzky_engine import (
    build_nuzky_project,
    save_nuzky_project,
    render_with_nuzky_or_ffmpeg,
    build_opencut_timeline,
)

settings = get_settings()
gemini = get_gemini_client()


class VideoEditorAgent(BaseAgent):
    def __init__(self):
        tools = [
            Tool(
                name="assemble_ffmpeg",
                description="Assemble video from images, audio, captions using FFmpeg",
                parameters={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "integer"},
                        "shot_list": {"type": "array"},
                        "audio_path": {"type": "string"},
                        "output_path": {"type": "string"},
                        "aspect_ratio": {"type": "string", "enum": ["9:16", "16:9", "1:1"], "default": "9:16"},
                        "captions": {"type": "array", "items": {"type": "object"}},
                        "music_path": {"type": "string", "description": "Optional background music"},
                    },
                    "required": ["job_id", "shot_list", "audio_path", "output_path"],
                },
                handler=self._assemble_ffmpeg,
            ),
            Tool(
                name="generate_tts",
                description="Generate TTS audio from script text",
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "output_path": {"type": "string"},
                        "voice": {"type": "string", "default": "en-US-AriaNeural"},
                    },
                    "required": ["text", "output_path"],
                },
                handler=self._generate_tts,
            ),
            Tool(
                name="generate_captions",
                description="Generate caption timeline from script",
                parameters={
                    "type": "object",
                    "properties": {
                        "captions": {"type": "array", "items": {"type": "object"}},
                        "output_path": {"type": "string"},
                    },
                    "required": ["captions", "output_path"],
                },
                handler=self._generate_captions,
            ),
            Tool(
                name="build_flow_prompt_pack",
                description="Generate premium Flow/Veo prompt pack for manual generation",
                parameters={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "integer"},
                        "character_bible": {"type": "object"},
                        "shot_list": {"type": "array"},
                        "style_guide": {"type": "object"},
                    },
                    "required": ["job_id", "character_bible", "shot_list", "style_guide"],
                },
                handler=self._build_flow_prompt_pack,
            ),
            Tool(
                name="apply_retention_pacing",
                description="Adjust shot timing based on retention curve data",
                parameters={
                    "type": "object",
                    "properties": {
                        "shot_list": {"type": "array"},
                        "retention_curve": {"type": "object"},
                    },
                    "required": ["shot_list", "retention_curve"],
                },
                handler=self._apply_retention_pacing,
            ),
        ]
        super().__init__(agent_id="video_editor", tools=tools)

    def _create_llm_client(self):
        return gemini

    async def _run_impl(self, job: Job, context: Dict[str, Any]) -> AgentResult:
        # Get required assets
        shot_list_asset = await get_latest_asset(job.id, "shot_list")
        scripts = await get_latest_asset(job.id, "script")

        if not shot_list_asset:
            return AgentResult(success=False, error="No shot list found")
        if not scripts:
            return AgentResult(success=False, error="No script found")

        shot_list = shot_list_asset.metadata_json.get("shots", [])
        script = scripts.metadata_json

        await log_event("INFO", self.agent_id, f"Video editing for job {job.id}", {"job_id": job.id, "shots": len(shot_list)})

        # Determine video engine
        engine = settings.video_engine  # "ffmpeg" or "veo"

        if engine == "veo":
            # Premium path: generate Flow prompt pack
            character_bible_asset = await get_latest_asset(job.id, "character_bible")
            style_guide_asset = await get_latest_asset(job.id, "style_guide")

            if character_bible_asset and style_guide_asset:
                prompt_pack = await self.call_tool(
                    "build_flow_prompt_pack",
                    job_id=job.id,
                    character_bible=character_bible_asset.metadata_json,
                    shot_list=shot_list_asset.metadata_json.get("shots", []),
                    style_guide=style_guide_asset.metadata_json,
                )
                await add_asset(job_id=job.id, asset_type="flow_prompt_pack", path=f"video/flow_prompt_pack_{job.id}.md", metadata=prompt_pack)
                return AgentResult(
                    success=True,
                    output={"premium": True, "prompt_pack": prompt_pack, "message": "Flow prompt pack generated. Use /premium <job_id> to retrieve."},
                )

        # Free path: FFmpeg assembly
        # 1. Generate TTS audio
        full_text = " ".join([beat.get("text", "") for beat in script.get("beats", [])])
        audio_path = f"temp/audio_{job.id}.mp3"
        os.makedirs(os.path.dirname(audio_path) or ".", exist_ok=True)

        tts_result = await self.call_tool("generate_tts", text=full_text, output_path=audio_path)
        if not tts_result.get("success"):
            return AgentResult(success=False, error=f"TTS failed: {tts_result.get('error')}")

        # 2. Generate captions file
        captions_path = f"temp/captions_{job.id}.srt"
        captions = script.get("captions", [])
        cap_result = await self.call_tool("generate_captions", captions=captions, output_path=captions_path)

        # 3. Fetch/generate images for shots
        image_paths = await self._prepare_shot_images(job.id, shot_list)

        # 4. Generate OpenCut timeline & Nuzky project bundle
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare shot list with populated image paths
        enriched_shot_list = []
        for i, shot in enumerate(shot_list):
            enriched = dict(shot)
            if i < len(image_paths):
                enriched["image_path"] = image_paths[i]
            enriched_shot_list.append(enriched)

        # Build and save Nuzky Project
        nuzky_proj = build_nuzky_project(
            job_id=job.id,
            name=f"Job_{job.id}_Cut",
            shot_list=enriched_shot_list,
            audio_path=audio_path,
            captions=captions,
            aspect_ratio="9:16",
        )
        nuzky_project_path = f"{output_dir}/project_{job.id}.nuzky"
        save_nuzky_project(nuzky_proj, nuzky_project_path)
        await add_asset(job_id=job.id, asset_type="nuzky_project", path=nuzky_project_path, metadata=nuzky_proj)

        # Build and save OpenCut Timeline
        opencut_timeline = build_opencut_timeline(
            job_id=job.id,
            shot_list=enriched_shot_list,
            audio_path=audio_path,
            captions=captions,
        )
        opencut_path = f"{output_dir}/opencut_{job.id}.json"
        with open(opencut_path, "w", encoding="utf-8") as f:
            json.dump(opencut_timeline, f, indent=2)
        await add_asset(job_id=job.id, asset_type="opencut_timeline", path=opencut_path, metadata=opencut_timeline)

        # 5. Assemble video using Nuzky or FFmpeg
        output_path = f"{output_dir}/video_{job.id}_9x16.mp4"
        rendered = False
        duration = 0.0

        if engine == "nuzky":
            rendered = await render_with_nuzky_or_ffmpeg(
                project_path=nuzky_project_path,
                output_mp4_path=output_path,
                preset="reels",
                audio_fallback_path=audio_path,
                image_fallback_path=image_paths[0] if image_paths else None,
            )

        if not rendered:
            asm_result = await self.call_tool(
                "assemble_ffmpeg",
                job_id=job.id,
                shot_list=enriched_shot_list,
                audio_path=audio_path,
                output_path=output_path,
                aspect_ratio="9:16",
                captions=captions,
            )
            if not asm_result.get("success"):
                return AgentResult(success=False, error=f"Assembly failed: {asm_result.get('error')}")
            duration = asm_result.get("duration", 0)
        else:
            duration = float(sum(s.get("duration", 3.0) for s in enriched_shot_list)) if enriched_shot_list else float(len(shot_list) * 3)

        # Save video asset
        await add_asset(job_id=job.id, asset_type="video", path=output_path, metadata={
            "aspect_ratio": "9:16",
            "duration": duration,
            "engine": engine,
            "shots": len(shot_list),
            "nuzky_project": nuzky_project_path,
            "opencut_timeline": opencut_path,
        })

        # Also generate 16:9 and 1:1 versions
        for ar in ["16:9", "1:1"]:
            ar_path = f"{output_dir}/video_{job.id}_{ar.replace(':', 'x')}.mp4"
            ar_result = await self.call_tool(
                "assemble_ffmpeg",
                job_id=job.id,
                shot_list=enriched_shot_list,
                audio_path=audio_path,
                output_path=ar_path,
                aspect_ratio=ar,
                captions=captions,
            )
            if ar_result.get("success"):
                await add_asset(job_id=job.id, asset_type="video", path=ar_path, metadata={
                    "aspect_ratio": ar,
                    "duration": ar_result.get("duration"),
                    "engine": engine,
                })

        return AgentResult(
            success=True,
            output={
                "video_path": output_path,
                "nuzky_project": nuzky_project_path,
                "opencut_timeline": opencut_path,
                "engine": engine,
                "aspect_ratios": ["9:16", "16:9", "1:1"],
            },
        )

    async def _prepare_shot_images(self, job_id: int, shot_list: List[Dict]) -> List[str]:
        """Fetch or generate images for each shot. Download reference videos if needed."""
        image_paths = []
        for i, shot in enumerate(shot_list):
            if shot.get("type") == "reference_video":
                url = shot.get("reference_url")
                vid_path = f"temp/ref_{job_id}_{i}.mp4"
                os.makedirs(os.path.dirname(vid_path) or ".", exist_ok=True)
                if not os.path.exists(vid_path):
                    cmd = ["yt-dlp", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", "-o", vid_path, url]
                    subprocess.run(cmd, capture_output=True)
                image_paths.append(vid_path)
            else:
                placeholder_path = f"temp/shot_{job_id}_{i}.jpg"
                os.makedirs(os.path.dirname(placeholder_path) or ".", exist_ok=True)
                color = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFBE0B", "#A0E7E5", "#B4F8C8"][i % 6]
                cmd = [
                    "ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d={shot.get('duration', 4)}",
                    "-vframes", "1", placeholder_path
                ]
                subprocess.run(cmd, capture_output=True)
                image_paths.append(placeholder_path)
        return image_paths

    async def _generate_tts(self, text: str, output_path: str, voice: str = "en-US-AriaNeural") -> Dict[str, Any]:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return {"success": True, "path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _generate_captions(self, captions: List[Dict], output_path: str) -> Dict[str, Any]:
        try:
            srt_content = ""
            for i, cap in enumerate(captions, 1):
                start = cap.get("start", 0)
                end = cap.get("end", start + 3)
                text = cap.get("text", "")
                srt_content += f"{i}\n{self._format_srt_time(start)} --> {self._format_srt_time(end)}\n{text}\n\n"

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            return {"success": True, "path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_srt_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    async def _assemble_ffmpeg(
        self,
        job_id: int,
        shot_list: List[Dict],
        audio_path: str,
        output_path: str,
        aspect_ratio: str = "9:16",
        captions: Optional[List[Dict]] = None,
        music_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            # Parse aspect ratio
            if aspect_ratio == "9:16":
                width, height = 1080, 1920
            elif aspect_ratio == "16:9":
                width, height = 1920, 1080
            else:
                width, height = 1080, 1080

            # Build filter complex
            filter_parts = []
            input_parts = []
            total_duration = 0

            # Add audio input
            input_parts.extend(["-i", audio_path])

            # For each shot, add image/video input and build filter
            for i, shot in enumerate(shot_list):
                if shot.get("type") == "reference_video":
                    img_path = f"temp/ref_{job_id}_{i}.mp4"
                    # Add video input (no loop)
                    input_parts.extend(["-i", img_path])
                else:
                    provided_path = shot.get("image_path")
                    if provided_path and os.path.exists(provided_path):
                        img_path = provided_path
                    else:
                        img_path = f"temp/shot_{job_id}_{i}.jpg"
                        if not os.path.exists(img_path):
                            os.makedirs("temp", exist_ok=True)
                            color = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFBE0B", "#A0E7E5", "#B4F8C8"][i % 6]
                            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d={shot.get('duration', 4)}", "-vframes", "1", img_path], capture_output=True)
                    input_parts.extend(["-loop", "1", "-t", str(shot.get("duration", 4)), "-i", img_path])

            # Build video filter chain
            video_filters = []
            for i, shot in enumerate(shot_list):
                if shot.get("type") == "reference_video":
                    # Remix transformations: hflip, zoom 1.1x, speedup 1.05x, hue shift
                    video_filters.append(
                        f"[{i+1}:v]hflip,scale=iw*1.1:ih*1.1,crop=iw/1.1:ih/1.1,setpts=PTS/1.05,hue=s=1.2,"
                        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                        f"setsar=1,format=yuv420p[v{i}]"
                    )
                else:
                    video_filters.append(
                        f"[{i+1}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                        f"setsar=1,format=yuv420p[v{i}]"
                    )

            # Concatenate videos
            concat_inputs = "".join([f"[v{i}]" for i in range(len(shot_list))])
            video_filters.append(f"{concat_inputs}concat=n={len(shot_list)}:v=1:a=0[vout]")

            # Caption filter if provided
            if captions:
                # Generate ASS subtitle file for advanced styling
                ass_path = f"temp/captions_{job_id}.ass"
                self._generate_ass_captions(captions, ass_path, width, height)
                video_filters.append(f"[vout]ass={ass_path}[vfinal]")
                final_video = "[vfinal]"
            else:
                final_video = "[vout]"

            filter_complex = ";".join(video_filters)

            # Build command
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                *input_parts,
                "-filter_complex", filter_complex,
                "-map", final_video,
                "-map", "0:a",  # audio from first input
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                "-movflags", "+faststart",
                output_path
            ]

            # Add music if provided
            if music_path and os.path.exists(music_path):
                cmd.insert(-2, "-i")
                cmd.insert(-2, music_path)
                # Mix audio: main audio + background music at lower volume
                # This would need filter_complex adjustment

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                return {"success": False, "error": result.stderr}

            # Get duration
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", output_path],
                capture_output=True, text=True
            )
            duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0

            return {"success": True, "path": output_path, "duration": duration}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "FFmpeg timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_ass_captions(self, captions: List[Dict], output_path: str, width: int, height: int) -> None:
        """Generate ASS subtitle file with styling."""
        header = f"""[Script Info]
Title: Captions
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{height//20},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,20,20,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        for cap in captions:
            start = self._format_ass_time(cap.get("start", 0))
            end = self._format_ass_time(cap.get("end", cap.get("start", 0) + 3))
            text = cap.get("text", "").replace("\n", "\\N")
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events))

    def _format_ass_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

    async def _build_flow_prompt_pack(self, job_id: int, character_bible: Dict, shot_list: List[Dict], style_guide: Dict) -> Dict[str, Any]:
        # Delegate to Art Director's method (would import or duplicate)
        from backend.agents.art_director import ArtDirectorAgent
        art = ArtDirectorAgent()
        return await art._generate_flow_prompts(character_bible, shot_list, style_guide)

    async def _apply_retention_pacing(self, shot_list: List[Dict], retention_curve: Dict) -> Dict[str, Any]:
        """Adjust shot durations based on retention data."""
        time_points = retention_curve.get("time_points", [])
        retention_values = retention_curve.get("retention_values", [])

        if not time_points or not retention_values:
            return {"adjusted": shot_list, "note": "No retention data"}

        # Find drop points (where retention drops >10%)
        drops = []
        for i in range(1, len(retention_values)):
            if retention_values[i-1] - retention_values[i] > 10:
                drops.append(time_points[i])

        adjusted = []
        for shot in shot_list:
            adjusted_shot = shot.copy()
            # If shot overlaps with drop point, shorten it
            for drop in drops:
                if shot["time_start"] <= drop <= shot["time_end"]:
                    # Shorten to just before drop
                    new_end = drop
                    adjusted_shot["time_end"] = new_end
                    adjusted_shot["duration"] = new_end - shot["time_start"]
                    break
            adjusted.append(adjusted_shot)

        return {"adjusted": adjusted, "drops_detected": drops}