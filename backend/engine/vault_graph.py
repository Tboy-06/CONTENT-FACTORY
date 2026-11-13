"""
CONTENT-FACTORY Engine: Live Vault-RAG & Director Second Brain (BM25)
---------------------------------------------------------------------
Retrieves proven viral hooks, editing rules, and storytelling frameworks
from D:\\CONTENT-FACTORY\\director_vault\\ and C:\\cf_training\\dataset.jsonl
using fast pure-Python BM25 scoring (0 MB VRAM, 0 API keys, sub-50ms execution).
"""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

VAULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "director_vault"))
DATASET_FILE = r"C:\cf_training\dataset.jsonl"

# Common English stop-words to ignore in BM25 tokenization
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


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase word tokens, filtering out stop-words."""
    words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    return [w for w in words if w not in STOP_WORDS]


class BM25Corpus:
    """Lightweight in-memory BM25 indexer."""
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 1.0
        self.df: Dict[str, int] = {}
        self.n_docs: int = 0

    def add_doc(self, doc_id: str, category: str, title: str, text: str, metadata: Optional[Dict[str, Any]] = None):
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

    def query(self, query_str: str, category: Optional[str] = None, top_k: int = 3) -> List[Tuple[float, Dict[str, Any]]]:
        if self.n_docs == 0:
            return []
        q_tokens = tokenize(query_str)
        if not q_tokens:
            return []

        scored = []
        for d in self.docs:
            if category and d["category"] != category:
                continue

            score = 0.0
            doc_tokens = d["tokens"]
            doc_len = d["length"]

            # Compute term frequencies in document
            tf: Dict[str, int] = {}
            for t in doc_tokens:
                tf[t] = tf.get(t, 0) + 1

            for qt in q_tokens:
                if qt in tf:
                    doc_freq = self.df.get(qt, 1)
                    # Standard BM25 IDF
                    idf = math.log(1.0 + (self.n_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                    term_tf = tf[qt]
                    denom = term_tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                    score += idf * ((term_tf * (self.k1 + 1.0)) / max(0.001, denom))

            if score > 0.0:
                scored.append((score, d))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]


# Global cached BM25 corpus instance
_cached_corpus: Optional[BM25Corpus] = None
_last_build_time: float = 0.0


def get_vault_corpus() -> BM25Corpus:
    """Builds or returns cached BM25 index over director_vault and dataset.jsonl."""
    global _cached_corpus, _last_build_time
    # Rebuild if cache is empty or older than 60 seconds (picks up new harvester outputs)
    import time
    now = time.time()
    if _cached_corpus is not None and (now - _last_build_time) < 60.0:
        return _cached_corpus

    corpus = BM25Corpus()

    # 1. Ingest Markdown notes from director_vault/
    if os.path.exists(VAULT_DIR):
        for sub in ["hooks", "techniques", "styles", "sfx"]:
            sub_dir = os.path.join(VAULT_DIR, sub)
            if not os.path.exists(sub_dir):
                continue
            for f in os.listdir(sub_dir):
                if f.endswith(".md"):
                    fp = os.path.join(sub_dir, f)
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as n_f:
                            content = n_f.read()
                        
                        # Extract title
                        m_title = re.search(r"^#\s*(.+)$", content, re.MULTILINE)
                        title = m_title.group(1).strip() if m_title else f.replace(".md", "").replace("_", " ")

                        corpus.add_doc(
                            doc_id=f"{sub}/{f}",
                            category=sub,
                            title=title,
                            text=content,
                            metadata={"file": f, "source": "vault"}
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
                        resp_str = rec.get("response", "")
                        resp_data = json.loads(resp_str) if resp_str.startswith("{") else {}
                        
                        prompt_str = rec.get("prompt", "")
                        title = resp_data.get("title") or prompt_str[:50]
                        hook = resp_data.get("hook", "")
                        rules = resp_data.get("rules", [])

                        cat = "hooks" if hook else ("techniques" if rules else "styles")
                        corpus.add_doc(
                            doc_id=f"dataset_row_{line_idx}",
                            category=cat,
                            title=title,
                            text=f"{prompt_str} {hook} {' '.join(rules) if isinstance(rules, list) else rules}",
                            metadata={"hook": hook, "rules": rules, "source": "dataset"}
                        )
                    except Exception:
                        pass
        except Exception:
            pass

    corpus.build()
    _cached_corpus = corpus
    _last_build_time = now
    return corpus


def query_director_vault(topic: str, style_preset: str = "Dark Documentary") -> str:
    """
    Live Vault-RAG Retriever:
    Queries director_vault and dataset.jsonl using BM25 scoring for:
    1. Top matching viral hook formula (from hooks/)
    2. Top matching pacing & cutting technique (from techniques/)
    3. Top matching storytelling structure (from styles/)
    Formats findings into an authoritative Director System Prompt injection.
    """
    corpus = get_vault_corpus()
    if corpus.n_docs == 0:
        return ""

    query_str = f"{topic} {style_preset}"

    top_hooks = corpus.query(query_str, category="hooks", top_k=2)
    top_techs = corpus.query(query_str, category="techniques", top_k=2)
    top_styles = corpus.query(query_str, category="styles", top_k=1)

    # Fallback to general search if category queries yielded 0
    if not top_hooks and not top_techs:
        general_matches = corpus.query(query_str, top_k=3)
        if not general_matches:
            return ""
        top_hooks = [m for m in general_matches if m[1]["category"] == "hooks"][:1]
        top_techs = [m for m in general_matches if m[1]["category"] == "techniques"][:1]
        top_styles = [m for m in general_matches if m[1]["category"] == "styles"][:1]

    sections = ["\n[HARVESTED DIRECTOR VAULT & VIRAL DATASET RAG - USE THESE FORMULAS]:"]

    # 1. Top Hook Pattern
    if top_hooks:
        score, doc = top_hooks[0]
        sections.append(f"• VIRAL HOOK FORMULA (Source: {doc['title']}):")
        # Extract opening or primary hook from note text
        m_open = re.search(r'Primary Opening:\s*"([^"]+)"', doc["text"])
        m_hook = re.search(r'### Curiosity Gap\s*>\s*"([^"]+)"', doc["text"])
        m_ds_hook = doc.get("metadata", {}).get("hook")
        hook_candidate = (m_open.group(1) if m_open else None) or (m_hook.group(1) if m_hook else None) or m_ds_hook
        if hook_candidate:
            sections.append(f"  - Model Opening Hook: \"{hook_candidate[:140]}\"")
        sections.append("  - Visual Pacing: Rapid punch-in zoom (1.2x) on Beat 1 with heavy thud.wav SFX.")

    # 2. Top Editing & Pacing Rules
    if top_techs:
        score, doc = top_techs[0]
        sections.append(f"• EDITING & PACING CADENCE (Source: {doc['title']}):")
        m_cad = re.search(r'Cut Frequency:\s*([^\n]+)', doc["text"])
        if m_cad:
            sections.append(f"  - Rhythm: {m_cad.group(1).strip()}")
        else:
            sections.append("  - Rhythm: Rapid cut cadence every 2.0s - 2.8s (~24 cuts/min).")
        # Extract rules
        rules = doc.get("metadata", {}).get("rules")
        if rules and isinstance(rules, list):
            for r in rules[:2]:
                sections.append(f"  - Rule: {r}")
        else:
            sections.append("  - Rule: Alternate every 2 beats between kinetic motion cards and 3D treated imagery.")
            sections.append("  - Rule: Pre-roll whoosh SFX 3 frames before transitions, drop heavy thud on reveal.")

    # 3. Storytelling Structure
    if top_styles:
        score, doc = top_styles[0]
        sections.append(f"• NARRATIVE ARCHITECTURE (Source: {doc['title']}):")
        sections.append("  - Structure: 4 Acts (1: Inciting Anomaly -> 2: Hidden Catalyst -> 3: Breakthrough -> 4: Modern Takeaway).")

    return "\n".join(sections) + "\n"


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
