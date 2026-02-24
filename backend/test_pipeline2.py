import sys, json, requests
from urllib.parse import urlparse, parse_qs
from config import settings

def p(msg=""):
    print(msg, flush=True)

BLOCKED_CATEGORY_IDS = {"17","20","23","24","1","2","15","19","21","22","25"}
YOUTUBE_CATEGORY_MAP = {
    "1":"Film & Animation","2":"Autos & Vehicles","10":"Music",
    "15":"Pets & Animals","17":"Sports","19":"Travel & Events",
    "20":"Gaming","21":"Videoblogging","22":"People & Blogs",
    "23":"Comedy","24":"Entertainment","25":"News & Politics",
    "26":"Howto & Style","27":"Education","28":"Science & Technology",
}
STUDY_KEYWORDS = [
    "lecture","tutorial","course","study with me","revision","mathematics",
    "maths","math","physics","chemistry","biology","programming","coding",
    "python","javascript","data structures","machine learning","iit","jee",
    "neet","upsc","explained","education","lofi","lo-fi","study music","focus music",
]
DISTRACTION_KEYWORDS = [
    "gameplay","gaming","reaction video","movie review","movie trailer",
    "music video","official song","prank","vlog","daily vlog","funny video",
    "memes","gossip","roast","tiktok","stand-up comedy","talk show","reality show",
]

def get_video_id(url):
    q = urlparse(url)
    if q.hostname == "youtu.be": return q.path[1:]
    if q.hostname in ("www.youtube.com","youtube.com"):
        if q.path == "/watch": return parse_qs(q.query).get("v",[None])[0]
    return None

def get_metadata(vid):
    r = requests.get(
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?id={vid}&key={settings.YOUTUBE_API_KEY}&part=snippet", timeout=8)
    if r.status_code==200 and r.json().get("items"):
        s = r.json()["items"][0]["snippet"]
        cat_id = s.get("categoryId","")
        return s.get("title",""), s.get("description","")[:400], \
               YOUTUBE_CATEGORY_MAP.get(cat_id,"Unknown"), cat_id
    return "","","",""

def gemini_classify(title, description, category):
    from google import genai as google_genai
    client = google_genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = (
        f'You are a strict content moderator for FocusFlow, a student study app.\n'
        f'Video Title: "{title}"\nCategory: "{category}"\nDescription: "{description[:300]}"\n\n'
        f'APPROVE only: lectures, tutorials, coding, math/science, exam prep (IIT/JEE/NEET/UPSC), academic content, lofi/study music.\n'
        f'BLOCK: sports, music videos, vlogs, gaming, entertainment, movies, celebrity stuff.\n'
        f'If unsure -> block. Reply ONLY with JSON, no markdown:\n'
        f'{{"is_study": true, "confidence": 0.95, "reason": "One clear sentence."}}'
    )
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = resp.text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)

# --- TEST VIDEOS ---
tests = [
    ("https://www.youtube.com/watch?v=rfscVS0vtbw", "Learn Python Full Course",  "EDUCATIONAL"),
    ("https://www.youtube.com/watch?v=aircAruvnKk", "LoFi Hip Hop Study Music",  "EDUCATIONAL"),
    ("https://www.youtube.com/watch?v=HXV3zeQKqGY", "Hindi Alphabets (Kids Edu)","EDUCATIONAL"),
    ("https://www.youtube.com/watch?v=kJQP7kiw5Fk", "Despacito Music Video",     "NON-EDUCATIONAL"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "Rick Astley Never Gonna",   "NON-EDUCATIONAL"),
    ("https://www.youtube.com/watch?v=9bZkp7q19f0", "Gangnam Style",             "NON-EDUCATIONAL"),
]

p("=" * 78)
p(f"  FocusFlow - YouTube Smart Filter Pipeline Test")
p(f"  Gemini API: {'OK' if settings.GEMINI_API_KEY else 'MISSING'} | YouTube API: {'OK' if settings.YOUTUBE_API_KEY else 'MISSING'}")
p("=" * 78)

for url, label, expected in tests:
    p()
    p(f"  VIDEO    : {label}  [expected: {expected}]")
    vid = get_video_id(url)
    title, desc, category, cat_id = get_metadata(vid)
    p(f"  TITLE    : {title}")
    p(f"  CATEGORY : {category} (ID: {cat_id})")

    # Layer 1 - Category hard block
    if cat_id in BLOCKED_CATEGORY_IDS:
        cat_label = YOUTUBE_CATEGORY_MAP.get(cat_id, "Non-educational")
        p(f"  LAYER    : CATEGORY HARD-BLOCK")
        p(f"  VERDICT  : BLOCKED -- '{cat_label}' category is never study-suitable")
        p("-" * 78)
        continue

    # Layer 2 - Gemini AI
    if settings.GEMINI_API_KEY:
        try:
            result = gemini_classify(title, desc, category)
            is_study = result.get("is_study", False)
            conf     = result.get("confidence", 0.0)
            reason   = result.get("reason", "")
            verdict  = "ALLOWED" if is_study else "BLOCKED"
            p(f"  LAYER    : GEMINI 2.5 FLASH AI")
            p(f"  VERDICT  : {verdict}  ({conf:.0%} confidence)")
            p(f"  REASON   : {reason}")
            p("-" * 78)
            continue
        except Exception as e:
            p(f"  GEMINI ERROR: {str(e)[:150]}")
            p(f"  Falling back to keyword filter...")

    # Layer 3 - Keyword fallback
    combined = f"{title} {desc}".lower()
    found_d = [kw for kw in DISTRACTION_KEYWORDS if kw in combined]
    found_s = [kw for kw in STUDY_KEYWORDS if kw in combined]
    p(f"  LAYER    : KEYWORD FALLBACK")
    if found_d:
        p(f"  VERDICT  : BLOCKED -- distraction keyword: '{found_d[0]}'")
    elif found_s:
        p(f"  VERDICT  : ALLOWED -- study keyword: '{found_s[0]}'")
    else:
        p(f"  VERDICT  : BLOCKED -- no study signals found (default block)")
    p("-" * 78)

p()
p("Pipeline test COMPLETE.")
