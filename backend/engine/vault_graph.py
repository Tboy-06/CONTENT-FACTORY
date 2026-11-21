"""
CONTENT-FACTORY Engine: Live Vault-RAG & Director Second Brain (BM25)
---------------------------------------------------------------------
Retrieves proven viral hooks, editing rules, and storytelling frameworks
from D:\\CONTENT-FACTORY\\director_vault\\ and C:\\cf_training\\dataset.jsonl
using fast pure-Python BM25 scoring (0 MB VRAM, 0 API keys, sub-50ms execution).

Features:
- 5-House Knowledge Architecture (HOUSE_1 to HOUSE_5)
- 5-Genre Physics Filtering (crime_doc, comedy_skit, action_hype, movie_cinema, viral_edu)
- Obsidian Map-of-Content (MOC) Dashboard Synchronization
- Anti-Contamination Genre Boosting (prevents crime_doc rules from leaking into comedy_skit/action_hype)
"""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

VAULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "director_vault"))
HOUSES_DIR = os.path.join(VAULT_DIR, "houses")
DATASET_FILE = r"C:\cf_training\dataset.jsonl"
STATE_FILE = r"C:\cf_training\harvest_state.json"

GENRES = ["crime_doc", "comedy_skit", "action_hype", "movie_cinema", "viral_edu"]
HOUSES = [
    "HOUSE_1_HOOK_PSYCHOLOGY",
    "HOUSE_2_SCREENWRITER_ARC",
    "HOUSE_3_VISUAL_DIRECTOR",
    "HOUSE_4_SOUND_AND_CUT_EDITOR",
    "HOUSE_5_COPILOT_AND_REFLEXION"
]

GENRE_EDITING_PHYSICS = {
    "crime_doc": {
        "pacing_cpm": "18-24 CPM (2.5s - 3.3s interval)",
        "camera": "cosine_in, pan_right, dolly_vertigo",
        "filter": "teal_split, hard_bw, amber",
        "motion_type": "declassified_scan, evidence_board, map_flyover, quote_box",
        "sfx": "thud.wav, whoosh.wav, click.wav",
        "audio_rules": "Archival radio voice filter (300Hz-3200Hz bandpass), dialogue -14 LUFS, music ducking -16dB.",
        "hook_focus": "Curiosity gap, classified document reveal, unsolved anomaly."
    },
    "comedy_skit": {
        "pacing_cpm": "25-35 CPM jump-cuts (1.7s - 2.4s interval)",
        "camera": "snap_zoom (1.35x sudden punch-in on punchlines), cosine_in",
        "filter": "skit_warm (bright, saturated)",
        "motion_type": "red_slam_word, quote_box, treated_image",
        "sfx": "click.wav, whoosh.wav",
        "audio_rules": "0.3s comedic dead-air pause (pause_before: 0.3) right before twist punchline lines.",
        "hook_focus": "Relatable absurdity, dramatic overreaction, comedic premise subversion."
    },
    "action_hype": {
        "pacing_cpm": "40-55 CPM (1.0s - 1.8s beat cuts)",
        "camera": "camera_shake (handheld impact shake), dolly_vertigo, snap_zoom",
        "filter": "action_crush (high-contrast crushed blacks)",
        "motion_type": "red_slam_word, treated_image, stat_counter",
        "sfx": "thud.wav, whoosh.wav",
        "audio_rules": "Heavy bass thud/impact on reveals, rapid whoosh transitions, sidechain ducking -18dB.",
        "hook_focus": "High-velocity danger, immediate physical threat, adrenaline countdown."
    },
    "movie_cinema": {
        "pacing_cpm": "12-18 CPM (3.3s - 5.0s interval)",
        "camera": "orbital, rack_focus_bokeh, cosine_in, cosine_out",
        "filter": "cinema_scope (35mm film grain, anamorphic teal/amber)",
        "motion_type": "2.35:1 widescreen anamorphic letterbox bars, minimal text overlays, treated_image",
        "sfx": "whoosh.wav, none",
        "audio_rules": "Orchestral swell, atmospheric environmental room tone, subtle cinematic sound design.",
        "hook_focus": "Atmospheric mystery, philosophical dilemma, grand cinematic scale."
    },
    "viral_edu": {
        "pacing_cpm": "28-38 CPM (1.8s - 2.5s visual switches)",
        "camera": "cosine_in, snap_zoom",
        "filter": "teal_split, amber",
        "motion_type": "stat_counter, workflow_stepper, 3_item_list",
        "sfx": "click.wav, whoosh.wav, thud.wav",
        "audio_rules": "Punchy compressed vocal presence (-14 LUFS), kinetic text sound sync.",
        "hook_focus": "Counter-intuitive metric, 'How X really works', high-value actionable insight."
    }
}

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she",
    "should", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself"
}


ACRONYMS = {
    "CIA", "FBI", "AI", "USA", "UK", "CEO", "NASA", "NFT", "LLM", "GPU", "CPU",
    "API", "NSA", "KGB", "MI6", "UN", "EU", "SEC", "IRS", "FDA", "DOD", "DOJ",
    "UFO", "UAP", "AGI", "DARPA", "NATO", "OPEC", "SWIFT", "DNA", "RNA",
}

_MINOR_TITLE_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "nor", "of", "on", "or", "the", "to", "with"}


def format_topic_title(topic: str) -> str:
    """
    Formats a topic into clean title case while preserving uppercase acronyms
    (e.g. 'CIA', 'FBI', 'AI', 'NASA', 'LLM') instead of Python .title() mangling 'CIA' -> 'Cia'.
    """
    if not topic or not topic.strip():
        return "Untitled Subject"
    words = topic.strip().split()
    out: List[str] = []
    for idx, word in enumerate(words):
        prefix_m = re.match(r"^([^a-zA-Z0-9]*)(.*?)([^a-zA-Z0-9]*)$", word)
        if not prefix_m:
            out.append(word)
            continue
        lead, core, trail = prefix_m.groups()
        if not core:
            out.append(word)
            continue
        upper_core = core.upper()
        if upper_core in ACRONYMS:
            out.append(f"{lead}{upper_core}{trail}")
        elif idx > 0 and core.lower() in _MINOR_TITLE_WORDS:
            out.append(f"{lead}{core.lower()}{trail}")
        elif core.isupper() and len(core) <= 4:
            out.append(f"{lead}{core}{trail}")
        else:
            out.append(f"{lead}{core.capitalize()}{trail}")
    return " ".join(out)


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase word tokens, filtering out stop-words."""
    words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    return [w for w in words if w not in STOP_WORDS]


def detect_genre(topic: str, prompt: str = "") -> str:
    """Canonical 5-genre detector shared across planner.py and vault_graph.py."""
    t = f"{topic} {prompt}".lower()
    if any(k in t for k in ["comedy", "skit", "funny", "humor", "joke", "prank", "hilarious", "parody", "laugh", "meme", "awkward", "roast"]):
        return "comedy_skit"
    if any(k in t for k in ["action", "hype", "battle", "supercar", "fight", "war", "explosive", "military", "chase", "combat", "strike", "beast", "workout", "gym", "explosion", "speed", "anime"]):
        return "action_hype"
    if any(k in t for k in ["movie", "cinema", "cinematic", "film", "hollywood", "35mm", "anamorphic", "drama", "scene", "trailer", "screenplay", "monologue", "widescreen"]):
        return "movie_cinema"
    if any(k in t for k in ["crime", "cia", "kgb", "fbi", "conspiracy", "scandal", "murder", "heist", "classified", "secret", "submarine", "azorian", "espionage", "investigation"]):
        return "crime_doc"
    if any(k in t for k in ["how to", "tutorial", "guide", "explained", "explain", "learn", "study", "tips", "hacks", "science", "facts", "step by step", "breakdown", "money", "why", "tech", "code", "crypto", "business", "economy", "ai", "system", "psychology"]):
        return "viral_edu"
    return "crime_doc"


class BM25Corpus:
    """Lightweight in-memory BM25 indexer with Genre & House Anti-Contamination Boosting."""
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 1.0
        self.df: Dict[str, int] = {}
        self.n_docs: int = 0

    def add_doc(
        self,
        doc_id: str,
        category: str,
        title: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        tokens = tokenize(f"{title} {text}")
        doc_len = len(tokens)
        self.docs.append({
            "id": doc_id,
            "category": category,
            "title": title,
            "text": text,
            "tokens": tokens,
            "length": doc_len,
            "metadata": metadata or {}
        })

    def build(self):
        self.n_docs = len(self.docs)
        if self.n_docs == 0:
            return
        total_len = sum(d["length"] for d in self.docs)
        self.avg_doc_len = total_len / max(1, self.n_docs)
        self.df = {}
        for d in self.docs:
            unique_tokens = set(d["tokens"])
            for t in unique_tokens:
                self.df[t] = self.df.get(t, 0) + 1

    def query(
        self,
        query_str: str,
        category: Optional[str] = None,
        genre: Optional[str] = None,
        house: Optional[str] = None,
        top_k: int = 4
    ) -> List[Tuple[float, Dict[str, Any]]]:
        if self.n_docs == 0:
            return []
        q_tokens = tokenize(query_str)
        if not q_tokens:
            return []

        target_genre = genre.lower() if genre and genre != "auto" else None
        target_house = house.upper() if house else None

        scored = []
        for d in self.docs:
            if category and d["category"] != category:
                continue

            doc_meta = d.get("metadata", {})
            doc_genre = (doc_meta.get("genre") or "").lower()
            doc_house = (doc_meta.get("house") or "").upper()

            # Strict cross-genre anti-contamination filter
            if target_genre:
                # If document belongs to a specific different genre, skip or penalize heavily
                if doc_genre and doc_genre != "auto" and doc_genre != target_genre:
                    continue

            score = 0.0
            doc_tokens = d["tokens"]
            doc_len = d["length"]

            tf: Dict[str, int] = {}
            for t in doc_tokens:
                tf[t] = tf.get(t, 0) + 1

            for qt in q_tokens:
                if qt in tf:
                    doc_freq = self.df.get(qt, 1)
                    idf = math.log(1.0 + (self.n_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                    term_tf = tf[qt]
                    denom = term_tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                    score += idf * ((term_tf * (self.k1 + 1.0)) / max(0.001, denom))

            if score <= 0.0:
                continue

            # Multiplier boosts (Genre + House + Real-World Viral Telemetry):
            if target_genre and doc_genre == target_genre:
                score *= 3.0
            if target_house and doc_house and target_house in doc_house:
                score *= 2.0
            view_count = int(doc_meta.get("view_count") or 0)
            if view_count > 100:
                score *= (1.0 + 0.15 * math.log10(view_count))

            scored.append((score, d))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]


# Global cached BM25 corpus instance
_cached_corpus: Optional[BM25Corpus] = None
_last_build_time: float = 0.0
_last_dataset_mtime: float = -1.0


def get_vault_corpus() -> BM25Corpus:
    """Builds or returns cached BM25 index over director_vault and dataset.jsonl (reloads only when mtime changes)."""
    global _cached_corpus, _last_build_time, _last_dataset_mtime
    import time
    now = time.time()
    current_ds_mtime = os.path.getmtime(DATASET_FILE) if os.path.exists(DATASET_FILE) else -1.0
    if _cached_corpus is not None:
        if (now - _last_build_time) < 60.0:
            return _cached_corpus
        if current_ds_mtime == _last_dataset_mtime and (now - _last_build_time) < 600.0:
            return _cached_corpus

    corpus = BM25Corpus()

    # 1. Ingest Markdown notes from director_vault/
    if os.path.exists(VAULT_DIR):
        for sub in ["houses", "hooks", "techniques", "styles", "sfx", "mistakes"]:
            sub_dir = os.path.join(VAULT_DIR, sub)
            if not os.path.exists(sub_dir):
                continue
            for f in os.listdir(sub_dir):
                if f.endswith(".md"):
                    fp = os.path.join(sub_dir, f)
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as n_f:
                            content = n_f.read()

                        m_title = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
                        title = m_title.group(1).strip() if m_title else f.replace(".md", "").replace("_", " ")

                        # Extract frontmatter genre / house if present
                        m_genre = re.search(r"genre:\s*([a-zA-Z0-9_-]+)", content, re.IGNORECASE)
                        doc_genre = m_genre.group(1).lower() if m_genre else detect_genre(content[:300])

                        m_house = re.search(r"house:\s*([a-zA-Z0-9_-]+)", content, re.IGNORECASE)
                        doc_house = m_house.group(1).upper() if m_house else None

                        corpus.add_doc(
                            doc_id=f"{sub}/{f}",
                            category=sub,
                            title=title,
                            text=content,
                            metadata={
                                "file": f,
                                "source": "vault",
                                "genre": doc_genre,
                                "house": doc_house
                            }
                        )
                    except Exception:
                        pass

    # 2. Ingest structured records from C:\cf_training\dataset.jsonl
    if os.path.exists(DATASET_FILE):
        try:
            with open(DATASET_FILE, "r", encoding="utf-8", errors="ignore") as d_f:
                for line_idx, line in enumerate(d_f):
                    line_s = line.strip()
                    if not line_s:
                        continue
                    try:
                        rec = json.loads(line_s)
                        resp_str = str(rec.get("output") or rec.get("response") or "")
                        prompt_str = str(rec.get("instruction") or rec.get("input") or rec.get("prompt") or "")
                        
                        rec_house = rec.get("house")
                        rec_genre = rec.get("genre") or "auto"
                        rec_sub = rec.get("sub_room")
                        out_obj = rec.get("output") if isinstance(rec.get("output"), dict) else {}
                        rec_views = int(out_obj.get("view_count") or 0)

                        corpus.add_doc(
                            doc_id=f"dataset_row_{line_idx}",
                            category="dataset",
                            title=f"Training Example #{line_idx} ({rec_genre})",
                            text=f"{prompt_str} {resp_str[:400]}",
                            metadata={
                                "source": "dataset",
                                "house": rec_house,
                                "genre": rec_genre,
                                "sub_room": rec_sub,
                                "view_count": rec_views,
                                "output": resp_str
                            }
                        )
                    except Exception:
                        pass
        except Exception:
            pass

    corpus.build()
    _cached_corpus = corpus
    _last_build_time = now
    _last_dataset_mtime = current_ds_mtime
    return corpus


def query_director_vault(
    topic: str,
    genre: str = "auto",
    house: Optional[str] = None,
    top_k: int = 4
) -> str:
    """
    Live Vault-RAG Retriever & Second Brain Context Engine:
    Queries director_vault and dataset.jsonl using BM25 scoring.
    Strictly boosts and filters by active genre to prevent cross-genre contamination
    (e.g., crime_doc classified documents never leak into comedy_skit or action_hype).
    """
    corpus = get_vault_corpus()
    resolved_genre = detect_genre(topic) if (not genre or genre == "auto") else genre.lower()
    if resolved_genre not in GENRES:
        resolved_genre = "crime_doc"

    physics = GENRE_EDITING_PHYSICS.get(resolved_genre, GENRE_EDITING_PHYSICS["crime_doc"])
    query_str = f"{topic} {resolved_genre}"

    # Query matching notes/records: Composite 5-House Retrieval when house is None or "ALL"
    matches: List[Tuple[float, Dict[str, Any]]] = []
    if not house or house.upper() == "ALL":
        seen_ids = set()
        for h_target in ["HOUSE_1", "HOUSE_2", "HOUSE_3", "HOUSE_4"]:
            h_hits = corpus.query(query_str, genre=resolved_genre, house=h_target, top_k=1)
            for sc, d in h_hits:
                if d["id"] not in seen_ids:
                    seen_ids.add(d["id"])
                    matches.append((sc, d))
    if len(matches) < top_k:
        extra = corpus.query(query_str, genre=resolved_genre, house=house, top_k=top_k)
        seen_ids = {d["id"] for _, d in matches}
        for sc, d in extra:
            if d["id"] not in seen_ids and len(matches) < top_k:
                seen_ids.add(d["id"])
                matches.append((sc, d))
    if not matches and corpus.n_docs > 0:
        matches = corpus.query(query_str, genre=resolved_genre, top_k=top_k)

    sections = [
        f"\n[OBSIDIAN SECOND BRAIN RAG — ACTIVE GENRE: {resolved_genre.upper()}]:",
        f"• EDITING PHYSICS FOR {resolved_genre.upper()}:",
        f"  - Target Pacing: {physics['pacing_cpm']}",
        f"  - Allowed Cameras: {physics['camera']}",
        f"  - Allowed Color Grades: {physics['filter']}",
        f"  - Allowed Motion Cards: {physics['motion_type']}",
        f"  - Allowed SFX: {physics['sfx']}",
        f"  - Audio Mastering Rules: {physics['audio_rules']}",
        f"  - Hook Focus: {physics['hook_focus']}"
    ]

    # Ingest retrieved Obsidian principles & distilled few-shot examples
    if matches:
        sections.append("\n• RETRIEVED CURATED PRINCIPLES & FEW-SHOT EXAMPLES:")
        for score, doc in matches[:4]:
            t = doc["title"]
            text_preview = doc["text"][:450].replace("\n", " ").strip()
            sections.append(f"  - [[{t}]]: \"{text_preview}\"")

    # Ingest learned editorial mistakes (Reflexion Reinforcement Learning)
    try:
        from backend.engine.reflexion import get_learned_mistakes
        learned_mistakes = get_learned_mistakes(query_topic=f"{topic} {resolved_genre}", limit=3)
        if learned_mistakes:
            sections.append("\n• LEARNED EDITORIAL MISTAKES TO AVOID:")
            for mr in learned_mistakes:
                occ = mr.get("occurrences", 1)
                lesson = mr.get("lesson", "")
                cat = mr.get("category", "editorial")
                sections.append(f"  - [AVOID ({cat}, caught {occ}x)]: {lesson}")
    except Exception:
        pass

    return "\n".join(sections) + "\n"


def sync_obsidian_house_dashboards() -> Dict[str, Any]:
    """
    Synchronizes the 5 Obsidian Map-of-Content (MOC) dashboards and Master Index:
    - director_vault/houses/00_SECOND_BRAIN_INDEX.md
    - director_vault/houses/HOUSE_1_HOOK_PSYCHOLOGY.md
    - director_vault/houses/HOUSE_2_SCREENWRITER_ARC.md
    - director_vault/houses/HOUSE_3_VISUAL_DIRECTOR.md
    - director_vault/houses/HOUSE_4_SOUND_AND_CUT_EDITOR.md
    - director_vault/houses/HOUSE_5_COPILOT_AND_REFLEXION.md

    D: DRIVE GUARD: Exactly 6 markdown files created on D: (< 100 KB total).
    Raw harvested dataset rows remain strictly on C:\\cf_training\\dataset.jsonl.
    """
    os.makedirs(HOUSES_DIR, exist_ok=True)

    state: Dict[str, Any] = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    total_records = state.get("total_records", 0)
    target_total = state.get("target_total", 100000)
    houses_state = state.get("houses", {})

    # 1. Generate 00_SECOND_BRAIN_INDEX.md
    index_md = [
        "---",
        "title: CONTENT-FACTORY Second Brain Master Index",
        "type: map_of_content",
        "tags: [second-brain, moc, knowledge-architecture, director-vault]",
        f"total_records: {total_records}",
        f"target_total: {target_total}",
        "---",
        "",
        "# 🧠 CONTENT-FACTORY Director Second Brain",
        "",
        "Welcome to the **100,000-Quota Knowledge Architecture** powering the AI Director.",
        "This vault contains the curated directing physics, viral hooks, pacing rules, and self-healing mistakes.",
        "",
        "## 🏛️ The 5 Knowledge Houses (20,000 Hard Cap Each)",
        "",
        "| House | Focus | Live Quota | Status | Dashboard |",
        "|---|---|---|---|---|",
    ]

    house_descriptions = {
        "HOUSE_1_HOOK_PSYCHOLOGY": "First 3-Second Viral Retention Formulas (Curiosity, Negative Bias, Shock)",
        "HOUSE_2_SCREENWRITER_ARC": "5-Genre Screenplay Arcs, CPM Cadence, and Multi-Act Narrative Structure",
        "HOUSE_3_VISUAL_DIRECTOR": "Motion HUD Cards, 3D Shaders, Color Grades, and Dynamic Camera Moves",
        "HOUSE_4_SOUND_AND_CUT_EDITOR": "Multi-Voice Dialogue, SFX Placement, Cut Velocity, and LUFS Mastering",
        "HOUSE_5_COPILOT_AND_REFLEXION": "AI Director Studio Chat Commands, Reflexion Auto-Healing, and Mistake Logs"
    }

    for h_name in HOUSES:
        h_data = houses_state.get(h_name, {})
        cnt = h_data.get("count", 0)
        tgt = h_data.get("target", 20000)
        st = h_data.get("status", "OPEN")
        badge = "🟢 OPEN" if st == "OPEN" else "🔒 FULL"
        index_md.append(f"| **{h_name}** | {house_descriptions[h_name]} | `{cnt:,} / {tgt:,}` | {badge} | [[{h_name}]] |")

    index_md.extend([
        "",
        "---",
        "",
        "## 🎬 5-Genre Studio Editing Matrix",
        "",
        "| Genre | Target Pacing | Signature Camera Move | Color Grade | Audio Profile |",
        "|---|---|---|---|---|",
        "| **🕵️ Crime Doc** | 18-24 CPM (2.5s-3.3s) | `cosine_in`, `pan_right` | `teal_split`, `hard_bw` | Archival Radio (300Hz-3200Hz), -14 LUFS |",
        "| **😂 Comedy Skit** | 25-35 CPM jump-cuts | `snap_zoom` (1.35x punch) | `skit_warm` | 0.3s comedic dead-air pause before punchline |",
        "| **🔥 Action Hype** | 40-55 CPM (1.0s-1.8s) | `camera_shake` (impact) | `action_crush` | Heavy bass thud impact, riser sweeps |",
        "| **🎬 Movie Cinema** | 12-18 CPM | `orbital`, `rack_focus_bokeh` | `cinema_scope` | 2.35:1 anamorphic letterbox, room tone |",
        "| **⚡ Viral Edu** | 28-38 CPM | `cosine_in` punch-in | `teal_split`, `amber` | Crisp compressed voice, stat counters |",
        "",
        "---",
        "",
        "## 🔗 Vault Cross-Links",
        "- Viral Hooks: [[hooks/visual_evidence_first]] | [[hooks/curiosity_gap_formula]]",
        "- Editing Techniques: [[techniques/vox_style_documentary]] | [[techniques/snap_zoom_pacing]]",
        "- Sound Design: [[sfx/thud]] | [[sfx/whoosh]] | [[sfx/click]]",
        "- Learned Mistakes: [[mistakes/pacing_monotony]] | [[mistakes/typography_overflow]]",
        ""
    ])

    with open(os.path.join(HOUSES_DIR, "00_SECOND_BRAIN_INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_md))

    # 2. Generate HOUSE_1_HOOK_PSYCHOLOGY.md
    h1_data = houses_state.get("HOUSE_1_HOOK_PSYCHOLOGY", {})
    h1_subs = h1_data.get("sub_rooms", {})
    h1_md = [
        "---",
        "title: House 1 - Hook Psychology",
        "house: HOUSE_1_HOOK_PSYCHOLOGY",
        "type: moc_house",
        "target_quota: 20000",
        f"current_quota: {h1_data.get('count', 0)}",
        "tags: [house-1, hooks, retention, second-brain]",
        "---",
        "",
        "# 🪝 HOUSE 1: Hook Psychology & 3-Second Retention",
        "",
        "Upstream: [[00_SECOND_BRAIN_INDEX]]",
        "",
        "House 1 specializes in the first 3 seconds of video execution. Viewers make a subconscious decision to swipe or stay within 800ms.",
        "",
        "## 📊 Sub-Room Quota Allocation (4,000 records each)",
        "| Sub-Room | Focus | Quota | Status |",
        "|---|---|---|---|",
        f"| `curiosity_gap` | Incomplete information gap forcing viewer closure | `{h1_subs.get('curiosity_gap', {}).get('count', 0):,} / 4,000` | {h1_subs.get('curiosity_gap', {}).get('status', 'OPEN')} |",
        f"| `negative_bias` | Loss aversion and existential warning openings | `{h1_subs.get('negative_bias', {}).get('count', 0):,} / 4,000` | {h1_subs.get('negative_bias', {}).get('status', 'OPEN')} |",
        f"| `counter_intuitive` | Challenging common sense with shocking facts | `{h1_subs.get('counter_intuitive', {}).get('count', 0):,} / 4,000` | {h1_subs.get('counter_intuitive', {}).get('status', 'OPEN')} |",
        f"| `visual_shock` | Bold visual anomaly shown before any speech | `{h1_subs.get('visual_shock', {}).get('count', 0):,} / 4,000` | {h1_subs.get('visual_shock', {}).get('status', 'OPEN')} |",
        f"| `title_thumbnail_ab` | High-CTR headline packaging and curiosity pairings | `{h1_subs.get('title_thumbnail_ab', {}).get('count', 0):,} / 4,000` | {h1_subs.get('title_thumbnail_ab', {}).get('status', 'OPEN')} |",
        "",
        "## 📜 Curated Directing Rules",
        "- **Rule 1.1:** Never start with \"In this video...\" or greeting the audience.",
        "- **Rule 1.2:** Drop a heavy `thud.wav` or `record_scratch` on frame 1 with visual motion.",
        "- **Rule 1.3:** For `comedy_skit`, open with high-tension absurdity; for `crime_doc`, open with declassified evidence.",
        ""
    ]
    with open(os.path.join(HOUSES_DIR, "HOUSE_1_HOOK_PSYCHOLOGY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(h1_md))

    # 3. Generate HOUSE_2_SCREENWRITER_ARC.md
    h2_data = houses_state.get("HOUSE_2_SCREENWRITER_ARC", {})
    h2_subs = h2_data.get("sub_rooms", {})
    h2_md = [
        "---",
        "title: House 2 - Screenwriter Arc",
        "house: HOUSE_2_SCREENWRITER_ARC",
        "type: moc_house",
        "target_quota: 20000",
        f"current_quota: {h2_data.get('count', 0)}",
        "tags: [house-2, screenwriting, narrative, 5-genre, second-brain]",
        "---",
        "",
        "# ✍️ HOUSE 2: Screenwriter Arc & 5-Genre Narrative",
        "",
        "Upstream: [[00_SECOND_BRAIN_INDEX]]",
        "",
        "House 2 governs the story circle, multi-act architecture, and tempo rules across the 5 core genres.",
        "",
        "## 📊 Sub-Room Quota Allocation (4,000 records each)",
        "| Genre / Sub-Room | Target CPM | Quota | Status |",
        "|---|---|---|---|",
        f"| `crime_doc` | 18-24 CPM | `{h2_subs.get('crime_doc', {}).get('count', 0):,} / 4,000` | {h2_subs.get('crime_doc', {}).get('status', 'OPEN')} |",
        f"| `comedy_skit` | 25-35 CPM | `{h2_subs.get('comedy_skit', {}).get('count', 0):,} / 4,000` | {h2_subs.get('comedy_skit', {}).get('status', 'OPEN')} |",
        f"| `action_hype` | 40-55 CPM | `{h2_subs.get('action_hype', {}).get('count', 0):,} / 4,000` | {h2_subs.get('action_hype', {}).get('status', 'OPEN')} |",
        f"| `movie_cinema` | 12-18 CPM | `{h2_subs.get('movie_cinema', {}).get('count', 0):,} / 4,000` | {h2_subs.get('movie_cinema', {}).get('status', 'OPEN')} |",
        f"| `viral_edu` | 28-38 CPM | `{h2_subs.get('viral_edu', {}).get('count', 0):,} / 4,000` | {h2_subs.get('viral_edu', {}).get('status', 'OPEN')} |",
        "",
        "## 📜 Genre Narrative Frameworks",
        "- **Crime Doc:** 4 Acts (1: Inciting Anomaly -> 2: Hidden Suspects -> 3: Breakthrough Raid -> 4: Modern Aftermath).",
        "- **Comedy Skit:** 3 Beats (Setup -> Escalation -> Twist Snap-Zoom Punchline).",
        "- **Action Hype:** 6 Beats (High Velocity Breach -> Accelerating Threat -> Climax Collision).",
        ""
    ]
    with open(os.path.join(HOUSES_DIR, "HOUSE_2_SCREENWRITER_ARC.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(h2_md))

    # 4. Generate HOUSE_3_VISUAL_DIRECTOR.md
    h3_data = houses_state.get("HOUSE_3_VISUAL_DIRECTOR", {})
    h3_subs = h3_data.get("sub_rooms", {})
    h3_md = [
        "---",
        "title: House 3 - Visual Director",
        "house: HOUSE_3_VISUAL_DIRECTOR",
        "type: moc_house",
        "target_quota: 20000",
        f"current_quota: {h3_data.get('count', 0)}",
        "tags: [house-3, visual-director, camera-moves, motion-cards, second-brain]",
        "---",
        "",
        "# 🎨 HOUSE 3: Visual Director & Camera Physics",
        "",
        "Upstream: [[00_SECOND_BRAIN_INDEX]]",
        "",
        "House 3 governs motion graphics, GLSL depth shaders, camera moves, and color grading filters.",
        "",
        "## 📊 Sub-Room Quota Allocation (4,000 records each)",
        "| Sub-Room | Focus | Quota | Status |",
        "|---|---|---|---|",
        f"| `depth_3d_shaders` | Ray-marched OpenGL GLSL shaders & DepthFlow displacement | `{h3_subs.get('depth_3d_shaders', {}).get('count', 0):,} / 4,000` | {h3_subs.get('depth_3d_shaders', {}).get('status', 'OPEN')} |",
        f"| `motion_hud_cards` | Pillow 60fps 2D cards (steppers, counters, declassified scans) | `{h3_subs.get('motion_hud_cards', {}).get('count', 0):,} / 4,000` | {h3_subs.get('motion_hud_cards', {}).get('status', 'OPEN')} |",
        f"| `color_grade_lighting` | Ev1 color grading LUTs (teal_split, hard_bw, skit_warm, etc.) | `{h3_subs.get('color_grade_lighting', {}).get('count', 0):,} / 4,000` | {h3_subs.get('color_grade_lighting', {}).get('status', 'OPEN')} |",
        f"| `broll_composition` | Pexels/archival shot framing, golden ratio, subject eye-lines | `{h3_subs.get('broll_composition', {}).get('count', 0):,} / 4,000` | {h3_subs.get('broll_composition', {}).get('status', 'OPEN')} |",
        "",
        "## ⚙️ Strict Engine Enums",
        "- **Valid Cameras:** `cosine_in`, `cosine_out`, `snap_zoom`, `camera_shake`, `orbital`, `dolly_vertigo`, `rack_focus_bokeh`, `pan_right`",
        "- **Valid Filters:** `teal_split`, `hard_bw`, `amber`, `skit_warm`, `action_crush`, `cinema_scope`",
        "- **Valid Motion Types:** `treated_image`, `declassified_scan`, `evidence_board`, `map_flyover`, `stat_counter`, `red_slam_word`, `workflow_stepper`, `3_item_list`, `quote_box`",
        ""
    ]
    with open(os.path.join(HOUSES_DIR, "HOUSE_3_VISUAL_DIRECTOR.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(h3_md))

    # 5. Generate HOUSE_4_SOUND_AND_CUT_EDITOR.md
    h4_data = houses_state.get("HOUSE_4_SOUND_AND_CUT_EDITOR", {})
    h4_subs = h4_data.get("sub_rooms", {})
    h4_md = [
        "---",
        "title: House 4 - Sound & Cut Editor",
        "house: HOUSE_4_SOUND_AND_CUT_EDITOR",
        "type: moc_house",
        "target_quota: 20000",
        f"current_quota: {h4_data.get('count', 0)}",
        "tags: [house-4, sound-design, audio-mastering, cut-velocity, second-brain]",
        "---",
        "",
        "# 🔊 HOUSE 4: Sound Design & Cut Velocity",
        "",
        "Upstream: [[00_SECOND_BRAIN_INDEX]]",
        "",
        "House 4 rules sound design, voice isolation, dynamic ducking, and millisecond-accurate cut pacing.",
        "",
        "## 📊 Sub-Room Quota Allocation (4,000 records each)",
        "| Sub-Room | Focus | Quota | Status |",
        "|---|---|---|---|",
        f"| `cut_velocity_cpm` | Cut velocity rhythms, J-cuts, L-cuts, and match cuts | `{h4_subs.get('cut_velocity_cpm', {}).get('count', 0):,} / 4,000` | {h4_subs.get('cut_velocity_cpm', {}).get('status', 'OPEN')} |",
        f"| `multi_voice_archival` | Speaker panning, radio EQ bandpass, and voiceover layering | `{h4_subs.get('multi_voice_archival', {}).get('count', 0):,} / 4,000` | {h4_subs.get('multi_voice_archival', {}).get('status', 'OPEN')} |",
        "",
        "## 🎚️ Audio Mastering Standards",
        "- **Dialogue Level:** Loudness-normalized to `-14.0 LUFS`.",
        "- **Sidechain Ducking:** Music ducks `-16dB` whenever speech is present.",
        "- **Valid SFX Enums:** `thud.wav`, `whoosh.wav`, `click.wav`, `none`.",
        "- **Comedic Pause:** `0.3s` silence injected before twist beats via FFmpeg `adelay`.",
        ""
    ]
    with open(os.path.join(HOUSES_DIR, "HOUSE_4_SOUND_AND_CUT_EDITOR.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(h4_md))

    # 6. Generate HOUSE_5_COPILOT_AND_REFLEXION.md
    h5_data = houses_state.get("HOUSE_5_COPILOT_AND_REFLEXION", {})
    h5_subs = h5_data.get("sub_rooms", {})
    h5_md = [
        "---",
        "title: House 5 - Copilot & Reflexion",
        "house: HOUSE_5_COPILOT_AND_REFLEXION",
        "type: moc_house",
        "target_quota: 20000",
        f"current_quota: {h5_data.get('count', 0)}",
        "tags: [house-5, copilot, reflexion, self-healing, mistakes, second-brain]",
        "---",
        "",
        "# 🤖 HOUSE 5: Director Copilot & Reflexion Healing",
        "",
        "Upstream: [[00_SECOND_BRAIN_INDEX]]",
        "",
        "House 5 powers the interactive AI Director Chat Drawer (`DirectorChatDrawer.tsx`), action schema execution, and reinforcement learning from mistakes.",
        "",
        "## 📊 Sub-Room Quota Allocation (4,000 records each)",
        "| Sub-Room | Focus | Quota | Status |",
        "|---|---|---|---|",
        f"| `director_chat_commands` | Natural language editing requests mapped to copilot actions | `{h5_subs.get('director_chat_commands', {}).get('count', 0):,} / 4,000` | {h5_subs.get('director_chat_commands', {}).get('status', 'OPEN')} |",
        f"| `reflexion_mistake_fixes` | Ground-truth editorial corrections (bad state -> healed state) | `{h5_subs.get('reflexion_mistake_fixes', {}).get('count', 0):,} / 4,000` | {h5_subs.get('reflexion_mistake_fixes', {}).get('status', 'OPEN')} |",
        "",
        "## 🛠️ Valid Copilot Action Schemas",
        "- `modify_timeline_beats`: Updates specific beat parameters (`beat_updates`).",
        "- `recut_genre`: Re-renders entire video into new genre physics (`target_genre`).",
        "- `slice_viral_shorts`: Extracts high-retention snippet into a standalone short.",
        "- `clone_reference_style`: Clones pacing/style of uploaded reference video.",
        "- `edit_uploaded_video`: Trims silences, grades footage, and burns kinetic subtitles.",
        ""
    ]
    with open(os.path.join(HOUSES_DIR, "HOUSE_5_COPILOT_AND_REFLEXION.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(h5_md))

    return {
        "status": "synced",
        "houses_dir": HOUSES_DIR,
        "files_generated": [
            "00_SECOND_BRAIN_INDEX.md",
            "HOUSE_1_HOOK_PSYCHOLOGY.md",
            "HOUSE_2_SCREENWRITER_ARC.md",
            "HOUSE_3_VISUAL_DIRECTOR.md",
            "HOUSE_4_SOUND_AND_CUT_EDITOR.md",
            "HOUSE_5_COPILOT_AND_REFLEXION.md"
        ]
    }


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
