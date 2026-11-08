from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agents import BaseAgent, AgentResult, Tool, Job
from backend.agents.llm_client import get_gemini_client
from backend.vault import add_asset, get_latest_asset, create_character_bible, log_event
from backend.config import get_settings

settings = get_settings()
gemini = get_gemini_client()


class ArtDirectorAgent(BaseAgent):
    def __init__(self):
        tools = [
            Tool(
                name="build_character_bible",
                description="Create a comprehensive character bible from script and style guide",
                parameters={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "integer"},
                        "character_name": {"type": "string"},
                        "style_guide_id": {"type": "integer"},
                    },
                    "required": ["job_id", "character_name", "style_guide_id"],
                },
                handler=self._build_character_bible,
            ),
            Tool(
                name="generate_shot_list",
                description="Generate detailed shot list from script beats",
                parameters={
                    "type": "object",
                    "properties": {
                        "script": {"type": "object"},
                        "style_guide": {"type": "object"},
                        "character_bible": {"type": "object"},
                    },
                    "required": ["script", "style_guide"],
                },
                handler=self._generate_shot_list,
            ),
            Tool(
                name="generate_flow_prompts",
                description="Generate Flow/Veo prompts for character references and scenes",
                parameters={
                    "type": "object",
                    "properties": {
                        "character_bible": {"type": "object"},
                        "shot_list": {"type": "array"},
                        "style_guide": {"type": "object"},
                    },
                    "required": ["character_bible", "shot_list", "style_guide"],
                },
                handler=self._generate_flow_prompts,
            ),
            Tool(
                name="fetch_reference_images",
                description="Fetch reference images from Pexels for visual direction",
                parameters={
                    "type": "object",
                    "properties": {
                        "queries": {"type": "array", "items": {"type": "string"}},
                        "per_query": {"type": "integer", "default": 3},
                    },
                    "required": ["queries"],
                },
                handler=self._fetch_reference_images,
            ),
        ]
        super().__init__(agent_id="art_director", tools=tools)

    def _create_llm_client(self):
        return gemini

    async def _run_impl(self, job: Job, context: Dict[str, Any]) -> AgentResult:
        # Get script and style guide assets
        scripts = await get_latest_asset(job.id, "script")
        style_guides = await get_latest_asset(job.id, "style_guide")

        if not scripts:
            return AgentResult(success=False, error="No script asset found")
        if not style_guides:
            return AgentResult(success=False, error="No style guide asset found")

        script = scripts.metadata_json
        style_guide = style_guides.metadata_json
        mode = job.config.get("mode", "Generate from Scratch")
        reference_url = job.config.get("referenceUrl")

        await log_event("INFO", self.agent_id, f"Art direction for job {job.id}", {"job_id": job.id})

        if mode == "Remix & Spin (Copyright Bypass)" and reference_url:
            # For Remix & Spin, the visual is just the transformed reference video
            shot_list = {
                "shots": [
                    {
                        "shot_number": 1,
                        "type": "reference_video",
                        "reference_url": reference_url,
                        "duration": 60, # Will be adjusted by VideoEditor
                        "description": "Original video to be transformed"
                    }
                ]
            }
            await add_asset(job_id=job.id, asset_type="shot_list", path=f"art/shot_list_{job.id}.json", metadata=shot_list)
            return AgentResult(success=True, output={"shot_count": 1, "shots": shot_list["shots"]})

        # Build character bible
        char_bible_result = await self.call_tool(
            "build_character_bible",
            job_id=job.id,
            character_name=script.get("main_character", "Protagonist"),
            style_guide_id=style_guide.get("style_guide_id", 1),
        )

        # Generate shot list
        shot_list_result = await self.call_tool(
            "generate_shot_list",
            script=script,
            style_guide=style_guide,
            character_bible=char_bible_result,
        )

        # Generate Flow prompts
        flow_prompts_result = await self.call_tool(
            "generate_flow_prompts",
            character_bible=char_bible_result,
            shot_list=shot_list_result.get("shots", []),
            style_guide=style_guide,
        )

        # Fetch reference images
        image_queries = self._extract_image_queries(script, shot_list_result)
        ref_images_result = await self.call_tool("fetch_reference_images", queries=image_queries, per_query=2)

        # Save all as assets
        await add_asset(job_id=job.id, asset_type="character_bible", path=f"art/character_bible_{job.id}.json", metadata=char_bible_result)
        await add_asset(job_id=job.id, asset_type="shot_list", path=f"art/shot_list_{job.id}.json", metadata=shot_list_result)
        await add_asset(job_id=job.id, asset_type="flow_prompts", path=f"art/flow_prompts_{job.id}.json", metadata=flow_prompts_result)
        await add_asset(job_id=job.id, asset_type="reference_images", path=f"art/ref_images_{job.id}.json", metadata=ref_images_result)

        return AgentResult(
            success=True,
            output={
                "character_bible": char_bible_result,
                "shot_list": shot_list_result,
                "flow_prompts": flow_prompts_result,
                "reference_images": ref_images_result,
            },
        )

    def _extract_image_queries(self, script: Dict, shot_list_result: Dict) -> List[str]:
        queries = []
        # Add character-based queries
        main_char = script.get("main_character", "person")
        queries.append(f"{main_char} character design")
        queries.append(f"{main_char} turnaround")
        # Add scene-based queries
        for beat in script.get("beats", [])[:5]:
            visual = beat.get("visual_cue", "")
            if visual:
                queries.append(visual[:80])
        return queries[:10]

    async def _build_character_bible(self, job_id: int, character_name: str, style_guide_id: int) -> Dict[str, Any]:
        from backend.vault.repository import create_character_bible, get_session
        from backend.vault.models import StyleGuide
        from sqlalchemy import select

        # Get style guide
        async with get_session() as session:
            result = await session.execute(select(StyleGuide).where(StyleGuide.id == style_guide_id))
            guide = result.scalar_one_or_none()

        if not guide:
            return {"error": "Style guide not found"}

        extracted = guide.extracted_json
        char_design = extracted.get("character_design", {})
        visual_style = extracted.get("visual_style", {})

        # Build comprehensive character prompt
        prompt = f"""
        {char_design.get('style', 'cartoon')} character design for "{character_name}":
        - Style: {char_design.get('style', 'cartoon')}
        - Proportions: {char_design.get('proportions', 'normal')}
        - Key features: {', '.join(char_design.get('key_features', ['expressive face', 'distinctive silhouette']))}
        - Color palette: {', '.join(visual_style.get('color_palette', ['#FF6B6B', '#4ECDC4']))}
        - Consistency markers: {', '.join(char_design.get('consistency_markers', ['color scheme', 'silhouette']))}
        - Lighting: {visual_style.get('lighting', 'soft natural')}
        - Camera style: {visual_style.get('camera_style', 'static')}
        """

        # Save to vault
        bible = await create_character_bible(
            name=f"{character_name}_{job_id}",
            prompt=prompt.strip(),
            reference_images={"style_guide_id": style_guide_id, "extracted": extracted},
            style_guide_id=style_guide_id,
        )

        return {
            "character_bible_id": bible.id,
            "name": character_name,
            "prompt": prompt.strip(),
            "style_guide_id": style_guide_id,
            "visual_traits": {
                "style": char_design.get("style"),
                "proportions": char_design.get("proportions"),
                "key_features": char_design.get("key_features"),
                "color_palette": visual_style.get("color_palette"),
                "consistency_markers": char_design.get("consistency_markers"),
            },
        }

    async def _generate_shot_list(self, script: Dict, style_guide: Dict, character_bible: Dict) -> Dict[str, Any]:
        beats = script.get("beats", [])
        visual_style = style_guide.get("analysis", {}).get("visual_style", {})
        pacing = style_guide.get("analysis", {}).get("pacing", {})
        scene_structure = style_guide.get("analysis", {}).get("scene_structure", {})

        shots = []
        cumulative_time = 0.0

        for i, beat in enumerate(beats):
            beat_time = beat.get("time", "0-5s")
            # Parse time range
            try:
                start_str, end_str = beat_time.replace("s", "").split("-")
                start = float(start_str)
                end = float(end_str)
                duration = end - start
            except Exception:
                start = cumulative_time
                duration = 4.0
                end = start + duration

            shot = {
                "shot_number": i + 1,
                "beat_index": i,
                "time_start": start,
                "time_end": end,
                "duration": duration,
                "text": beat.get("text", ""),
                "visual_cue": beat.get("visual_cue", ""),
                "scene_type": self._classify_scene_type(beat, i, len(beats)),
                "camera": visual_style.get("camera_style", "static"),
                "lighting": visual_style.get("lighting", "natural"),
                "composition": visual_style.get("composition_rules", ["centered"])[0],
                "transition": scene_structure.get("transition_style", "cut"),
                "text_overlay": beat.get("text", "")[:100] if i < 3 else "",
                "character_present": True,
                "flow_prompt": self._generate_shot_flow_prompt(beat, visual_style, character_bible, i, len(beats)),
            }
            shots.append(shot)
            cumulative_time = end

        # Add intro/outro if missing
        if shots and shots[0]["shot_number"] != 1:
            shots.insert(0, self._make_intro_shot(script, visual_style, character_bible))

        return {
            "shots": shots,
            "total_duration": cumulative_time,
            "style_guide_id": style_guide.get("style_guide_id"),
            "character_bible_id": character_bible.get("character_bible_id"),
        }

    def _classify_scene_type(self, beat: Dict, index: int, total: int) -> str:
        text = beat.get("text", "").lower()
        if index == 0:
            return "intro"
        elif index == total - 1:
            return "cta"
        elif any(w in text for w in ["problem", "issue", "struggle", "wrong"]):
            return "problem"
        elif any(w in text for w in ["solution", "answer", "fix", "how to"]):
            return "solution"
        elif any(w in text for w in ["demo", "show", "example", "proof"]):
            return "demo"
        return "content"

    def _make_intro_shot(self, script: Dict, visual_style: Dict, character_bible: Dict) -> Dict:
        return {
            "shot_number": 0,
            "beat_index": -1,
            "time_start": 0,
            "time_end": 2.5,
            "duration": 2.5,
            "text": script.get("hook", "Hook text"),
            "visual_cue": "Main character appears, engaging direct address",
            "scene_type": "intro",
            "camera": visual_style.get("camera_style", "static"),
            "lighting": visual_style.get("lighting", "bright"),
            "composition": visual_style.get("composition_rules", ["centered"])[0],
            "transition": "none",
            "text_overlay": script.get("hook", "")[:80],
            "character_present": True,
            "flow_prompt": f"Intro shot: {character_bible.get('name', 'Character')} appears on screen, {visual_style.get('lighting', 'bright')} lighting, {visual_style.get('composition_rules', ['centered'])[0]} composition, direct eye contact with camera, engaging smile",
        }

    def _generate_shot_flow_prompt(self, beat: Dict, visual_style: Dict, character_bible: Dict, index: int, total: int) -> str:
        visual = beat.get("visual_cue", "")
        scene_type = self._classify_scene_type(beat, index, total)
        char_name = character_bible.get("name", "Character")

        base = f"{char_name}, {visual_style.get('style', 'cartoon')} style, {visual_style.get('lighting', 'natural')} lighting"

        if scene_type == "intro":
            return f"{base}, direct address to camera, engaging expression, {visual_style.get('composition_rules', ['centered'])[0]} composition"
        elif scene_type == "problem":
            return f"{base}, concerned expression, close-up shot, dramatic tension"
        elif scene_type == "solution":
            return f"{base}, confident expression, medium shot, positive energy, solution reveal"
        elif scene_type == "demo":
            return f"{base}, demonstrating action, screen capture style, clear visual hierarchy"
        elif scene_type == "cta":
            return f"{base}, direct eye contact, warm smile, inviting gesture, call to action"
        else:
            return f"{base}, {visual}, {visual_style.get('camera_style', 'static')} camera"

    async def _generate_flow_prompts(self, character_bible: Dict, shot_list: List[Dict], style_guide: Dict) -> Dict[str, Any]:
        char_traits = character_bible.get("visual_traits", {})
        char_prompt_base = f"""
        {char_traits.get('style', 'cartoon')} character, {char_traits.get('proportions', 'normal')} proportions,
        key features: {', '.join(char_traits.get('key_features', []))},
        color palette: {', '.join(char_traits.get('color_palette', []))},
        consistency markers: {', '.join(char_traits.get('consistency_markers', []))}
        """

        # Character reference prompts for Flow
        char_refs = {
            "character_sheet": f"Character turnaround sheet: {char_prompt_base}. Front, 3/4, side, back views. Clean line art, flat colors, reference sheet style.",
            "expressions": f"Character expression sheet: {char_prompt_base}. 8 expressions: happy, surprised, thinking, concerned, excited, neutral, sad, confident. Same character design, consistent proportions.",
            "poses": f"Character pose sheet: {char_prompt_base}. 6 poses: standing neutral, sitting, walking, pointing/gesturing, typing/working, celebrating. Consistent proportions and colors.",
        }

        # Scene prompts for Veo
        scene_prompts = []
        for shot in shot_list:
            if shot.get("flow_prompt"):
                scene_prompts.append({
                    "shot_number": shot["shot_number"],
                    "duration_sec": shot["duration"],
                    "prompt": f"{shot['flow_prompt']}. {style_guide.get('analysis', {}).get('visual_style', {}).get('camera_style', 'static')} camera, {style_guide.get('analysis', {}).get('visual_style', {}).get('transition_style', 'cut')} transition.",
                    "aspect_ratio": "9:16",
                })

        # Premium prompt pack (Markdown for manual Flow use)
        prompt_pack = self._build_prompt_pack_markdown(char_refs, scene_prompts, character_bible, style_guide)

        return {
            "character_references": char_refs,
            "scene_prompts": scene_prompts,
            "prompt_pack_markdown": prompt_pack,
            "character_bible_id": character_bible.get("character_bible_id"),
        }

    def _build_prompt_pack_markdown(self, char_refs: Dict, scene_prompts: List[Dict], character_bible: Dict, style_guide: Dict) -> str:
        char_name = character_bible.get("name", "Character")
        visual = style_guide.get("analysis", {}).get("visual_style", {})

        md = f"""# Flow/Veo Prompt Pack — {char_name}

## Character Reference Prompts (Nano Banana / Imagen 3)

### Character Sheet (Turnaround)
```
{char_refs['character_sheet']}
```

### Expressions (8)
```
{char_refs['expressions']}
```

### Poses (6)
```
{char_refs['poses']}
```

---

## Scene Prompts (Veo 3 / Flow)

"""
        for sp in scene_prompts:
            md += f"""### Shot {sp['shot_number']} ({sp['duration_sec']}s, {sp['aspect_ratio']})
```
{sp['prompt']}
```

"""
        md += f"""
---

## Style Guide Summary
- **Visual Style**: {visual.get('style', 'cartoon')}
- **Color Palette**: {', '.join(visual.get('color_palette', []))}
- **Lighting**: {visual.get('lighting', 'natural')}
- **Camera**: {visual.get('camera_style', 'static')}
- **Composition**: {', '.join(visual.get('composition_rules', ['centered']))}
- **Transitions**: {visual.get('transition_style', 'cut')}
- **Text Overlay**: {style_guide.get('analysis', {}).get('scene_structure', {}).get('text_overlay_style', 'minimal')}

## Platform Specs
| Platform | Duration | Aspect | Hook At | Loop At |
|----------|----------|--------|---------|---------|
| TikTok | 15-60s | 9:16 | 0s | 15s |
| YouTube Shorts | 15-60s | 9:16 | 0s | 15s |
| Instagram Reels | 15-30s | 9:16 | 0s | 15s |

## Usage
1. Generate character references in Nano Banana/Imagen 3 using prompts above
2. Use character images as reference in Flow for Veo scene generation
3. Generate each scene with corresponding prompt
4. Download clips, assemble in editor
"""
        return md

    async def _fetch_reference_images(self, queries: List[str], per_query: int = 3) -> Dict[str, Any]:
        # Placeholder - would use Pexels API
        return {"queries": queries, "per_query": per_query, "status": "placeholder - implement with Pexels API"}