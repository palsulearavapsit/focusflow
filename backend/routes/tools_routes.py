from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from urllib.parse import urlparse, parse_qs
from config import settings
from typing import Optional

router = APIRouter()


class YouTubeAnalysisRequest(BaseModel):
    url: str


class YouTubeAnalysisResponse(BaseModel):
    is_study_related: bool
    confidence: float
    title: str
    reason: str
    video_id: Optional[str] = None


# YouTube categories that are ALWAYS study-hostile — block immediately
BLOCKED_CATEGORIES = {
    "17",  # Sports
    "20",  # Gaming
    "23",  # Comedy
    "24",  # Entertainment
    "1",   # Film & Animation
    "10",  # Music  (allow only via Gemini overriding if it's lofi/classical)
}

# Keywords that strongly indicate STUDY content
# Use specific multi-word phrases where possible to avoid false matches
STUDY_KEYWORDS = [
    # Direct study signals
    "lecture", "tutorial", "course", "study with me", "study session",
    "masterclass", "class notes", "revision",
    # Subjects
    "mathematics", "maths", "math", "algebra", "calculus", "geometry",
    "physics", "chemistry", "biology", "history", "geography",
    "programming", "coding", "python", "javascript", "java", "c++",
    "data structures", "algorithms", "machine learning", "deep learning",
    # Exam prep (India-specific + general)
    "iit", "jee", "neet", "upsc", "gate exam", "cat exam",
    "exam prep", "exam preparation", "entrance exam",
    # Academic
    "textbook", "university lecture", "school lesson", "education",
    "explained", "learn python", "learn javascript", "learn math",
    "research", "academic", "thesis", "dissertation",
    # Study music (very specific phrases only)
    "lofi", "lo-fi", "study music", "music for studying",
    "ambient study", "white noise study", "focus music",
    "classical music study", "brown noise",
]

# Keywords that STRONGLY and UNAMBIGUOUSLY indicate distraction content
# Only include words that are SPECIFIC to non-educational content
# and would NOT appear in a genuine study/science/academic video title
DISTRACTION_KEYWORDS = [
    # Sports — specific sport names and match terms
    "tennis match", "cricket match", "football match", "soccer match",
    "basketball game", "sports highlights", "match highlights",
    "tournament highlights", "grand slam", "wimbledon", "fifa",
    "nba highlights", "ipl highlights", "live match", "live score",
    "vs highlights", "epic comeback", "best goals", "best wickets",
    # Gaming
    "gameplay", "gaming", "let's play", "lets play", "walkthrough",
    "speedrun", "playthrough", "game review",
    # Pure entertainment
    "funny video", "memes", "prank", "vlog", "daily vlog",
    "reaction video", "movie review", "movie trailer", "web series",
    "music video", "official music", "official song", "song lyrics",
    "gossip", "roast", "tiktok", "stand-up comedy", "comedy show",
    "talk show", "reality show", "entertainment news",
]

# YouTube category ID → human-readable name map
YOUTUBE_CATEGORY_MAP = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music",
    "15": "Pets & Animals", "17": "Sports", "18": "Short Movies",
    "19": "Travel & Events", "20": "Gaming", "21": "Videoblogging",
    "22": "People & Blogs", "23": "Comedy", "24": "Entertainment",
    "25": "News & Politics", "26": "Howto & Style", "27": "Education",
    "28": "Science & Technology", "29": "Nonprofits & Activism",
}


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats:
    - https://youtu.be/SA2iWivDJiE
    - https://www.youtube.com/watch?v=_oPAwA_Udwc
    - https://www.youtube.com/embed/SA2iWivDJiE
    - https://www.youtube.com/v/SA2iWivDJiE
    """
    query = urlparse(url)
    if query.hostname == "youtu.be":
        return query.path[1:]
    if query.hostname in ("www.youtube.com", "youtube.com"):
        if query.path == "/watch":
            p = parse_qs(query.query)
            return p.get("v", [None])[0]
        if query.path.startswith("/embed/"):
            return query.path.split("/")[2]
        if query.path.startswith("/v/"):
            return query.path.split("/")[2]
    return None


def get_youtube_metadata(video_id: str):
    """
    Fetch video title, description (first 500 chars), category name,
    and raw category ID from YouTube Data API v3.
    Falls back to oEmbed for title-only.
    Returns (title, description, category_name, cat_id).
    """
    title, description, category, cat_id = "", "", "", ""

    # Primary: YouTube Data API v3 (full metadata)
    if settings.YOUTUBE_API_KEY:
        try:
            api_url = (
                f"https://www.googleapis.com/youtube/v3/videos"
                f"?id={video_id}&key={settings.YOUTUBE_API_KEY}&part=snippet"
            )
            resp = requests.get(api_url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("items"):
                    snippet = data["items"][0]["snippet"]
                    title = snippet.get("title", "")
                    description = snippet.get("description", "")[:500]
                    cat_id = snippet.get("categoryId", "")
                    category = YOUTUBE_CATEGORY_MAP.get(cat_id, "")
                    return title, description, category, cat_id
            else:
                print(f"[YouTube API] Error {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            print(f"[YouTube API] Exception: {exc}")

    # Fallback: oEmbed endpoint (public, no API key, title only)
    try:
        oembed_url = (
            f"https://www.youtube.com/oembed"
            f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
        )
        resp = requests.get(oembed_url, timeout=5)
        if resp.status_code == 200:
            title = resp.json().get("title", "")
    except Exception as exc:
        print(f"[oEmbed] Exception: {exc}")

    return title, description, category, cat_id



@router.post("/analyze_youtube", response_model=YouTubeAnalysisResponse)
async def analyze_youtube_video(request: YouTubeAnalysisRequest):
    """
    Strict analyzer: ONLY approves clearly educational YouTube videos.
    Sports, movies, songs, entertainment → always blocked.
    """
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL. Please paste a valid YouTube link.")

    title, description, category, cat_id = get_youtube_metadata(video_id)

    if not title:
        # Can't verify content — block by default (strict mode)
        return YouTubeAnalysisResponse(
            is_study_related=False,
            confidence=0.9,
            title="Unknown Video",
            reason="Could not verify this video. Only confirmed study content is allowed.",
            video_id=video_id,
        )

    # ── LAYER 1: HARD BLOCK by YouTube Category ──────────────────────────
    # These category IDs are NEVER study-suitable. Block immediately.
    BLOCKED_CATEGORY_IDS = {
        "17",  # Sports
        "20",  # Gaming
        "23",  # Comedy
        "24",  # Entertainment
        "1",   # Film & Animation
        "2",   # Autos & Vehicles
        "15",  # Pets & Animals
        "19",  # Travel & Events
        "21",  # Videoblogging / Vlogs
        "22",  # People & Blogs
        "25",  # News & Politics
    }
    if cat_id in BLOCKED_CATEGORY_IDS:
        cat_label = YOUTUBE_CATEGORY_MAP.get(cat_id, "Non-educational")
        return YouTubeAnalysisResponse(
            is_study_related=False,
            confidence=0.99,
            title=title,
            reason=f"Blocked: This video is in the '{cat_label}' category, which is not suitable for studying.",
            video_id=video_id,
        )

    # ── LAYER 2: GEMINI AI — Strict Classification ────────────────────────
    if settings.GEMINI_API_KEY:
        try:
            from google import genai as google_genai
            import json

            client = google_genai.Client(api_key=settings.GEMINI_API_KEY)

            prompt = f"""
You are a content moderator for FocusFlow, a student study productivity app.
A student in an active study session wants to play this YouTube video.

Video Details:
- Title: "{title}"
- Category: "{category if category else 'Unknown'}"
- Description: "{description if description else 'Not provided'}"

Your job: Decide if this is EDUCATIONAL/STUDY content or ENTERTAINMENT/DISTRACTION content.
If you are not sure, lean towards blocking (is_study = false).

✅ APPROVE (is_study = true):
- Lectures, tutorials, university/school lessons
- Coding/programming tutorials (Python, JS, C++, etc.)
- Math, physics, chemistry, biology, science lessons
- IIT, JEE, NEET, UPSC, GATE or any entrance exam prep
- Academic interviews (e.g. professor explaining a concept, student academic guidance)
- Educational documentaries about science/history/technology
- LoFi beats, classical music, white noise for studying
- Any video clearly intended to teach a skill or academic concept

❌ BLOCK (is_study = false):
- Sports matches, highlights, tournaments (tennis, cricket, football etc.)
- Celebrity/athlete interviews (not academic)
- Movies, TV shows, web series, trailers
- Songs and music videos (NOT LoFi/classical/ambient study music)
- Vlogs, daily life, pranks, challenges, reaction videos
- Gaming, gameplay, esports
- Comedy shows, talk shows, entertainment news

KEY DISTINCTION: An academic/educational "interview" (e.g. IIT professor, exam tips, student counseling) is STUDY content.
A celebrity, sports, or entertainment "interview" is NOT study content.

Respond ONLY with this exact JSON (no markdown):
{{"is_study": true, "confidence": 0.95, "reason": "One clear sentence."}}
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            raw = response.text.strip().replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

            return YouTubeAnalysisResponse(
                is_study_related=bool(result.get("is_study", False)),
                confidence=float(result.get("confidence", 0.9)),
                title=title,
                reason=result.get("reason", "AI analysis complete."),
                video_id=video_id,
            )

        except Exception as exc:
            print(f"[Gemini] Error: {exc}")
            # Fall through to keyword fallback

    # ── LAYER 3: KEYWORD FALLBACK — Default is BLOCK ─────────────────────
    # If Gemini fails, we only approve if STRONG study keywords are found
    # AND zero distraction keywords are found. Otherwise → block.
    combined = f"{title} {description}".lower()

    found_study = [kw for kw in STUDY_KEYWORDS if kw in combined]
    found_distraction = [kw for kw in DISTRACTION_KEYWORDS if kw in combined]

    if found_distraction:
        # Any distraction keyword → block, no exceptions
        reason = f"Contains non-study signals: {', '.join(found_distraction[:3])}."
        return YouTubeAnalysisResponse(
            is_study_related=False,
            confidence=0.85,
            title=title,
            reason=reason,
            video_id=video_id,
        )

    if found_study:
        reason = f"Contains study-related signals: {', '.join(found_study[:3])}."
        return YouTubeAnalysisResponse(
            is_study_related=True,
            confidence=0.75,
            title=title,
            reason=reason,
            video_id=video_id,
        )

    # No signals either way → block by default (strict mode)
    return YouTubeAnalysisResponse(
        is_study_related=False,
        confidence=0.7,
        title=title,
        reason="Could not confirm this is study content. Only verified educational videos are allowed.",
        video_id=video_id,
    )
