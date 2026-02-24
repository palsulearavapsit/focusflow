
import json
import requests
from urllib.parse import urlparse, parse_qs
from config import settings

# ── Category maps ──────────────────────────────────────────────────────────
BLOCKED_CATEGORY_IDS = {"17","20","23","24","1","2","15","19","21","22","25"}
YOUTUBE_CATEGORY_MAP = {
    "1":"Film & Animation","2":"Autos & Vehicles","10":"Music",
    "15":"Pets & Animals","17":"Sports","18":"Short Movies",
    "19":"Travel & Events","20":"Gaming","21":"Videoblogging",
    "22":"People & Blogs","23":"Comedy","24":"Entertainment",
    "25":"News & Politics","26":"Howto & Style","27":"Education",
    "28":"Science & Technology","29":"Nonprofits & Activism",
}

STUDY_KEYWORDS = [
    "lecture","tutorial","course","study with me","study session",
    "masterclass","revision","mathematics","maths","math","algebra",
    "calculus","physics","chemistry","biology","programming","coding",
    "python","javascript","data structures","algorithms","machine learning",
    "iit","jee","neet","upsc","gate exam","explained","education",
    "lofi","lo-fi","study music","focus music",
]
DISTRACTION_KEYWORDS = [
    "gameplay","gaming","reaction video","movie review","movie trailer",
    "music video","official song","prank","vlog","daily vlog",
    "funny video","memes","gossip","roast","tiktok","stand-up comedy",
    "talk show","reality show","cricket match","football match",
]

# ── Helpers ────────────────────────────────────────────────────────────────
def get_video_id(url):
    q = urlparse(url)
    if q.hostname == "youtu.be":
        return q.path[1:]
    if q.hostname in ("www.youtube.com", "youtube.com"):
        if q.path == "/watch":
            return parse_qs(q.query).get("v", [None])[0]
    return None


def get_metadata(vid):
    r = requests.get(
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?id={vid}&key={settings.YOUTUBE_API_KEY}&part=snippet",
        timeout=8,
    )
    if r.status_code == 200 and r.json().get("items"):
        s = r.json()["items"][0]["snippet"]
        cat_id = s.get("categoryId", "")
        return (
            s.get("title", ""),
            s.get("description", "")[:400],
            YOUTUBE_CATEGORY_MAP.get(cat_id, "Unknown"),
            cat_id,
        )
    return "", "", "", ""


def gemini_classify(title, description, category):
    from google import genai as google_genai

    client = google_genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = f"""
You are a content moderator for FocusFlow, a student study productivity app.
A student in an active study session wants to play this YouTube video.

Video Details:
- Title: "{title}"
- Category: "{category}"
- Description: "{description if description else 'Not provided'}"

Your job: Decide if this is EDUCATIONAL/STUDY content or ENTERTAINMENT/DISTRACTION content.
If you are not sure, lean towards blocking (is_study = false).

APPROVE (is_study = true):
- Lectures, tutorials, university/school lessons
- Coding/programming tutorials (Python, JS, C++, etc.)
- Math, physics, chemistry, biology, science lessons
- IIT, JEE, NEET, UPSC, GATE or any entrance exam prep
- Academic interviews (professor explaining a concept, student academic guidance)
- Educational documentaries about science/history/technology
- LoFi beats, classical music, white noise for studying

BLOCK (is_study = false):
- Sports matches, highlights, tournaments
- Celebrity/athlete interviews (not academic)
- Movies, TV shows, web series, trailers
- Songs and music videos (NOT LoFi/classical/ambient study music)
- Vlogs, daily life, pranks, challenges, reaction videos
- Gaming, gameplay, esports
- Comedy shows, talk shows, entertainment news

Respond ONLY with this exact JSON (no markdown):
{{"is_study": true, "confidence": 0.95, "reason": "One clear sentence."}}
"""
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = resp.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ── Test Videos ───────────────────────────────────────────────────────────
test_videos = [
    # Educational
    ("https://www.youtube.com/watch?v=rfscVS0vtbw", "Learn Python Full Course"),
    ("https://www.youtube.com/watch?v=aircAruvnKk", "LoFi Study Music"),
    ("https://www.youtube.com/watch?v=HXV3zeQKqGY", "Hindi Alphabets Education"),
    # Non-Educational
    ("https://www.youtube.com/watch?v=kJQP7kiw5Fk", "Despacito Music Video"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),
    ("https://www.youtube.com/watch?v=9bZkp7q19f0", "Gangnam Style Music"),
]

print("=" * 80)
print(f"{'LABEL':<35} {'LAYER':<10} {'VERDICT':<10} {'CONFIDENCE':<12} REASON")
print("=" * 80)

for url, label in test_videos:
    vid = get_video_id(url)
    if not vid:
        print(f"{label:<35} {'ERROR':<10} Invalid URL")
        continue

    title, desc, category, cat_id = get_metadata(vid)
    display = label[:33]

    print(f"\n[{label}]")
    print(f"  Title    : {title}")
    print(f"  Category : {category} (ID: {cat_id})")

    # Layer 1: Category hard-block
    if cat_id in BLOCKED_CATEGORY_IDS:
        cat_label = YOUTUBE_CATEGORY_MAP.get(cat_id, "Non-educational")
        print(f"  Layer    : CATEGORY (hard block)")
        print(f"  Verdict  : BLOCKED  — category '{cat_label}' is not study-suitable")
        continue

    # Layer 2: Gemini AI
    if settings.GEMINI_API_KEY:
        try:
            result = gemini_classify(title, desc, category)
            is_study = result.get("is_study", False)
            conf = result.get("confidence", 0.0)
            reason = result.get("reason", "")
            verdict = "✅ ALLOWED" if is_study else "🚫 BLOCKED"
            print(f"  Layer    : GEMINI AI")
            print(f"  Verdict  : {verdict}")
            print(f"  Confidence: {conf:.0%}")
            print(f"  Reason   : {reason}")
            continue
        except Exception as e:
            print(f"  Gemini error: {e} — falling back to keywords")

    # Layer 3: Keyword fallback
    combined = f"{title} {desc}".lower()
    found_d = [kw for kw in DISTRACTION_KEYWORDS if kw in combined]
    found_s = [kw for kw in STUDY_KEYWORDS if kw in combined]
    print(f"  Layer    : KEYWORD FALLBACK")
    if found_d:
        print(f"  Verdict  : BLOCKED  — distraction signal: {found_d[0]}")
    elif found_s:
        print(f"  Verdict  : ALLOWED  — study signal: {found_s[0]}")
    else:
        print(f"  Verdict  : BLOCKED  — no study signals found")

print("\n" + "=" * 80)
print("Full pipeline test complete.")
