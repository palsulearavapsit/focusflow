from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import re
from urllib.parse import urlparse, parse_qs
from config import settings

router = APIRouter()

class YouTubeAnalysisRequest(BaseModel):
    url: str

class YouTubeAnalysisResponse(BaseModel):
    is_study_related: bool
    confidence: float
    title: str
    reason: str

# Keywords to classify as "Study"
STUDY_KEYWORDS = [
    "study", "lecture", "tutorial", "course", "learn", "math", "physics", 
    "chemistry", "biology", "history", "programming", "coding", "python", 
    "java", "exam", "preparation", "guide", "summary", "analysis", "review",
    "lesson", "class", "school", "university", "college", "education",
    "focus", "ambient", "lofi", "music for studying", "calm", "reading"
]

# Keywords to classify as "Distraction"
DISTRACTION_KEYWORDS = [
    "gameplay", "funny", "memes", "prank", "vlog", "challenge", 
    "reaction", "movie", "trailer", "song", "music video", "entertainment",
    "gossip", "highlight", "live", "stream", "show"
]

def extract_video_id(url):
    """
    Examples:
    - http://youtu.be/SA2iWivDJiE
    - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    - http://www.youtube.com/embed/SA2iWivDJiE
    - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    """
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p.get('v', [None])[0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    return None

def get_youtube_title(video_id):
    # Use oEmbed endpoint which is public
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url)
        if response.status_code == 200:
            return response.json().get("title", "")
        return ""
    except Exception as e:
        print(f"Error fetching title: {e}")
        return ""

@router.post("/analyze_youtube", response_model=YouTubeAnalysisResponse)
async def analyze_youtube_video(request: YouTubeAnalysisRequest):
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    title = get_youtube_title(video_id)
    if not title:
        return YouTubeAnalysisResponse(
            is_study_related=True, 
            confidence=0.5,
            title="Unknown Video",
            reason="Could not fetch title, please verify manually."
        )
    
    # --- GEMINI AI INTEGRATION ---
    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            import json

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')

            prompt = f"""
            Analyze if the following YouTube video title is suitable for a 'Study Session'.
            Video Title: "{title}"
            
            Respond in strict JSON format:
            {{
                "is_study": true/false,
                "confidence": 0.0 to 1.0,
                "reason": "Short explanation"
            }}
            
            Criteria:
            - Study related: Lectures, Tutorials, LoFi Music, Ambient Noise, Educational, Documentaries, Coding, Math.
            - Distraction: Gaming, Pranks, Vlogs, Entertainment, Trailers, Music Videos (except LoFi/Classical).
            """
            
            response = model.generate_content(prompt)
            result = json.loads(response.text.replace('```json', '').replace('```', '').strip())
            
            return YouTubeAnalysisResponse(
                is_study_related=result.get('is_study', False),
                confidence=result.get('confidence', 0.8),
                title=title,
                reason=result.get('reason', 'AI Analysis')
            )
            
        except Exception as e:
            print(f"Gemini API Error: {e}")
            # Fallback to keyword matching if Gemini fails
            pass

    # Fallback: Simple Keyword Analysis
    title_lower = title.lower()
    
    score = 0
    reason = "Neutral content"
    
    found_study = [kw for kw in STUDY_KEYWORDS if kw in title_lower]
    if found_study:
        score += 5
        reason = f"Contains study keywords: {', '.join(found_study[:3])}"
        
    found_distraction = [kw for kw in DISTRACTION_KEYWORDS if kw in title_lower]
    if found_distraction:
        score -= 5
        reason = f"Contains entertainment keywords: {', '.join(found_distraction[:3])}"

    return YouTubeAnalysisResponse(
        is_study_related=score >= 0,
        confidence=0.8 if found_study or found_distraction else 0.4,
        title=title,
        reason=reason
    )
