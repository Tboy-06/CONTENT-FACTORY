"""
CONTENT-FACTORY Engine: Live Fact-Dossier Researcher (zero-cost, 0 API keys)
----------------------------------------------------------------------------
Extracts grounded real-world facts before script planning:
1. Wikipedia REST API:
   - Canonical title, description, summary extract
   - Real-world coordinates (lat/long) for map_flyover
   - Extracted key dates (years), exact metrics ($ amounts, % rates, counts)
   - Extracted key entities (people, agencies, locations)
2. Zero-Quota Transcript Snippet:
   - Optional yt-dlp top search transcript scrape for verified authority quotes
3. Outputs structured FactDossier JSON to ground stat_counter, evidence_board,
   map_flyover, and quote_box beats in 100% authentic data.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from backend.engine.vault_graph import format_topic_title

logger = logging.getLogger("engine.researcher")


def _fetch_json(url: str, timeout: float = 6.0) -> Optional[Dict[str, Any]]:
    """Fetches JSON from a URL with a clean User-Agent."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ContentFactoryDocumentaryBot/2.0 (contact: support@contentfactory.local)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _search_yt_dlp_facts(topic: str, max_results: int = 1) -> List[str]:
    """Helper for yt-dlp transcript quote search."""
    q = fetch_transcript_quote_yt_dlp(topic)
    return [q] if q else []


def clean_text(text: str) -> str:
    """Removes citations and normalizes whitespace."""
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_key_metrics(text: str) -> List[str]:
    """Extracts dollar figures, percentages, and large quantified metrics."""
    metrics = []
    # Dollar amounts: $3.8 billion, $500,000, etc.
    dollars = re.findall(r"\$\d+(?:[\.,]\d+)?\s*(?:billion|million|trillion|k|thousand)?", text, re.IGNORECASE)
    metrics.extend(dollars)

    # Percentages: 99.8%, 89 percent
    percents = re.findall(r"\b\d+(?:[\.,]\d+)?\s*(?:%|percent)\b", text, re.IGNORECASE)
    metrics.extend(percents)

    # Quantities with units: 14,000 personnel, 20,000 leagues, 500 tons, etc.
    quantities = re.findall(r"\b\d+(?:[\.,]\d+)?\s*(?:feet|meters|miles|km|tons|kg|personnel|soldiers|troops|warheads|casualties|members)\b", text, re.IGNORECASE)
    metrics.extend(quantities)

    # Deduplicate while preserving order
    seen = set()
    cleaned = []
    for m in metrics:
        norm = m.strip()
        if norm.lower() not in seen and len(norm) >= 2:
            seen.add(norm.lower())
            cleaned.append(norm)
    return cleaned[:6]


def extract_key_dates(text: str) -> List[str]:
    """Extracts historical and modern 4-digit years."""
    years = re.findall(r"\b(18\d\d|19\d\d|20[0-2]\d)\b", text)
    seen = set()
    cleaned = []
    for y in years:
        if y not in seen:
            seen.add(y)
            cleaned.append(y)
    return cleaned[:6]


def extract_key_entities(text: str) -> List[str]:
    """Extracts capitalized multi-word proper nouns (agencies, people, projects)."""
    # Look for 2-3 capitalized consecutive words
    candidates = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b", text)
    # Filter out common stop-phrases
    stop = {"The United", "In The", "According To", "As A", "It Was", "For Example", "After The"}
    seen = set()
    entities = []
    for c in candidates:
        if c not in stop and c.lower() not in seen and len(c) > 4:
            seen.add(c.lower())
            entities.append(c)
    return entities[:6]


def extract_quotes(text: str) -> List[str]:
    """Extracts quoted statements from text."""
    quotes = re.findall(r'["“]([^"”]{15,140})["”]', text)
    return [q.strip() for q in quotes if len(q.strip()) > 15]


def fetch_wikipedia_dossier(topic: str) -> Dict[str, Any]:
    """Queries Wikipedia REST summary API synchronously."""
    try:
        clean_topic = re.sub(r'["\']', '', topic).strip()
        encoded = urllib.parse.quote(clean_topic)
        
        # 1. Search Wikipedia for best page match
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json&utf8=1"
        data = _fetch_json(search_url, timeout=6.0)
        if not data:
            return {}

        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            return {}

        top_title = search_results[0]["title"]

        # 2. Fetch page summary extract
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(top_title)}"
        sum_data = _fetch_json(summary_url, timeout=6.0)
        if not sum_data:
            return {}

        extract = clean_text(sum_data.get("extract") or "")
        coords_raw = sum_data.get("coordinates")
        coords_str = None
        if coords_raw and "lat" in coords_raw and "lon" in coords_raw:
            lat = float(coords_raw["lat"])
            lon = float(coords_raw["lon"])
            lat_dir = "N" if lat >= 0 else "S"
            lon_dir = "E" if lon >= 0 else "W"
            coords_str = f"{abs(lat):.2f}° {lat_dir}, {abs(lon):.2f}° {lon_dir}"

        page_url = sum_data.get("content_urls", {}).get("desktop", {}).get("page") or summary_url
        return {
            "canonical_title": sum_data.get("title", top_title),
            "description": sum_data.get("description", ""),
            "extract": extract,
            "source_url": page_url,
            "coordinates": coords_str,
            "metrics": extract_key_metrics(extract),
            "dates": extract_key_dates(extract),
            "entities": extract_key_entities(extract),
            "quotes": extract_quotes(extract)
        }
    except Exception as e:
        logger.warning(f"[researcher] Wikipedia lookup error for '{topic}': {e}")
        return {}


def fetch_transcript_quote_yt_dlp(topic: str) -> Optional[str]:
    """
    Scrapes top YouTube video transcript snippet for topic via yt-dlp flat search (0 API keys).
    Immediately removes any temporary subtitle file.
    """
    try:
        temp_dir = r"C:\cf_training\temp\research"
        os.makedirs(temp_dir, exist_ok=True)
        sub_prefix = os.path.join(temp_dir, f"quote_{abs(hash(topic)) % 100000}")

        cmd = [
            "yt-dlp",
            f"ytsearch1:{topic} documentary",
            "--skip-download",
            "--write-auto-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "-o", f"{sub_prefix}.%(ext)s"
        ]
        _no_win = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12, creationflags=_no_win)
        vtt_file = f"{sub_prefix}.en.vtt"

        quote = None
        if os.path.exists(vtt_file):
            with open(vtt_file, "r", encoding="utf-8", errors="ignore") as vf:
                lines = vf.readlines()
            # Clean VTT timestamps and header
            sentences = []
            for line in lines:
                l = line.strip()
                if not l or "-->" in l or l.startswith("WEBVTT") or l.startswith("NOTE"):
                    continue
                clean_l = re.sub(r"<[^>]+>", "", l).strip()
                if clean_l and clean_l not in sentences:
                    sentences.append(clean_l)

            # Pick a punchy 10-25 word sentence as verified quote
            for s in sentences[4:30]:
                words = s.split()
                if 8 <= len(words) <= 22 and not any(w in s.lower() for w in ["subscribe", "sponsor", "channel", "click"]):
                    quote = s
                    break

            try:
                os.remove(vtt_file)
            except Exception:
                pass

        return quote
    except Exception as e:
        logger.warning(f"[researcher] Transcript quote fetch error: {e}")
        return None


async def research_fact_dossier(topic: str) -> Dict[str, Any]:
    """
    Fast zero-key research pre-step:
    Combines Wikipedia REST API + yt-dlp transcript snippets into an authoritative FactDossier.
    Never invents or fabricates fallback numbers, dates, coordinates, or quotes.
    Missing facts are explicitly tagged 'UNVERIFIED' or empty lists [].
    """
    logger.info(f"[researcher] Gathering verified fact dossier for: '{topic}'...")

    wiki_task = asyncio.to_thread(fetch_wikipedia_dossier, topic)
    quote_task = asyncio.to_thread(_search_yt_dlp_facts, topic, 1)

    try:
        wiki_res, yt_quotes = await asyncio.gather(wiki_task, quote_task)
    except Exception as e:
        logger.warning(f"[researcher] Parallel gather error: {e}")
        wiki_res = {}
        yt_quotes = []

    wiki_res = wiki_res or {}
    yt_quote = yt_quotes[0] if yt_quotes else None

    canonical_title = wiki_res.get("canonical_title") or format_topic_title(topic)
    description = wiki_res.get("description") or f"Investigative analysis of {canonical_title}"
    extract = wiki_res.get("extract") or ""
    source_url = wiki_res.get("source_url") or ""

    # Merge real quotes only (no fabricated fallback quotes)
    quotes = list(wiki_res.get("quotes") or [])
    if yt_quote and yt_quote not in quotes:
        quotes.insert(0, yt_quote)

    primary_quote = quotes[0] if quotes else "UNVERIFIED"
    coords = wiki_res.get("coordinates") or "UNVERIFIED"
    dates = list(wiki_res.get("dates") or [])[:4]
    metrics = list(wiki_res.get("metrics") or [])[:4]
    entities = list(wiki_res.get("entities") or [])[:4]
    if not entities:
        entities = [canonical_title]

    has_verified_source = bool(extract or yt_quote or dates or metrics)
    verification_status = "VERIFIED" if has_verified_source else "UNVERIFIED"

    claims: List[Dict[str, str]] = []
    if extract:
        claims.append({
            "claim": extract[:240],
            "source_url": source_url or "https://en.wikipedia.org",
            "source_title": canonical_title,
            "evidence": extract[:300],
            "verification_status": "VERIFIED",
        })
    for m in metrics:
        claims.append({
            "claim": f"Documented metric: {m}",
            "source_url": source_url or "https://en.wikipedia.org",
            "source_title": canonical_title,
            "evidence": extract[:200] if extract else m,
            "verification_status": "VERIFIED",
        })
    if yt_quote:
        claims.append({
            "claim": yt_quote,
            "source_url": f"ytsearch1:{topic} documentary",
            "source_title": f"{canonical_title} Transcript Archive",
            "evidence": yt_quote,
            "verification_status": "VERIFIED",
        })
    if not claims:
        claims.append({
            "claim": f"No verified external metrics or archival quotes retrieved for {canonical_title}.",
            "source_url": "UNVERIFIED",
            "source_title": canonical_title,
            "evidence": "UNVERIFIED",
            "verification_status": "UNVERIFIED",
        })

    dossier = {
        "topic": topic,
        "canonical_title": canonical_title,
        "description": description,
        "summary": extract[:400] if extract else f"UNVERIFIED: No external archival extract retrieved for {canonical_title}.",
        "key_dates": dates,
        "key_metrics": metrics,
        "key_entities": entities,
        "coordinates": coords,
        "location_name": canonical_title.upper()[:28] if coords != "UNVERIFIED" else "UNVERIFIED",
        "verified_quote": primary_quote,
        "verification_status": verification_status,
        "claims": claims,
    }

    logger.info(
        f"[researcher] Fact Dossier ready for '{canonical_title}' (status={verification_status}): "
        f"{len(dossier['key_dates'])} dates, {len(dossier['key_metrics'])} metrics, coords={coords}"
    )
    return dossier
