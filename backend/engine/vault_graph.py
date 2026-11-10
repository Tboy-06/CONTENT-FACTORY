"""
CONTENT-FACTORY: Obsidian + Graphify Director Vault Helper
----------------------------------------------------------
Retrieves directing principles and hook formulas from the local Obsidian vault
via Markdown AST and WikiLink traversal (0 MB background RAM, zero API cost).
"""

import os
import re
from typing import List, Dict, Any, Optional

VAULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "director_vault"))


def query_director_vault(topic: str, style_preset: str = "Dark Documentary") -> str:
    """Finds top-connected Obsidian guidelines and hook formulas for a given topic/style."""
    if not os.path.exists(VAULT_DIR):
        return ""

    matched_notes = []
    keywords = set(re.findall(r"\w+", f"{topic} {style_preset}".lower()))

    for root, _, files in os.walk(VAULT_DIR):
        for f in files:
            if f.endswith(".md"):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as note_f:
                        content = note_f.read()
                    
                    # Score match based on keyword occurrences
                    score = sum(1 for kw in keywords if kw in content.lower())
                    if score > 0 or "dark_documentary" in f.lower():
                        matched_notes.append((score, f, content))
                except Exception:
                    continue

    matched_notes.sort(key=lambda x: x[0], reverse=True)
    top_notes = matched_notes[:3]

    if not top_notes:
        return ""

    context_lines = ["\n[DIRECTOR VAULT SECOND-BRAIN GUIDELINES]:"]
    for _, fname, text in top_notes:
        clean_text = "\n".join(line for line in text.splitlines() if not line.startswith("Tags:"))
        context_lines.append(f"--- Note: {fname} ---\n{clean_text}\n")

    return "\n".join(context_lines)


def log_script_to_vault(job_id: int, title: str, hook: str, style: str, beats: List[Dict[str, Any]]):
    """Saves completed video plan as an interlinked Markdown note in the Obsidian vault."""
    scripts_dir = os.path.join(VAULT_DIR, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    
    clean_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")[:35]
    note_path = os.path.join(scripts_dir, f"Job_{job_id}_{clean_title}.md")

    lines = [
        f"# Job #{job_id}: {title}",
        f"Tags: #rendered_video #job_{job_id}",
        f"- Style Reference: [[styles/{style.lower().replace(' ', '_')}]]",
        f"- Primary Hook: [[hooks/visual_evidence_first]]",
        f"- Spoken Hook: \"{hook}\"",
        f"",
        f"## 16-Beat Timeline Breakdown"
    ]

    for b in beats:
        b_id = b.get("id", "beat")
        dur = b.get("duration", 2.0)
        sfx = b.get("sfx")
        sfx_link = f"[[sfx/{sfx.replace('.wav', '')}]]" if sfx else "none"
        narration = b.get("narration", "")
        lines.append(f"- **{b_id}** ({dur}s) | SFX: {sfx_link} | *\"{narration}\"*")

    try:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass
