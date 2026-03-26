"""
FocusFlow - AI Assistant Routes (FocusBot)
Uses Gemini API to provide chat, PDF summaries, and YouTube summaries.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import io
import PyPDF2
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import os
import logging
from typing import Dict, List, Optional
from auth import get_current_user

# Load .env variables correctly
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["FocusBot AI"])

# Configure Gemini Client
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = None
if not GEMINI_KEY:
    logger.warning("⚠️ GEMINI_API_KEY NOT FOUND IN .ENV")
else:
    # Initialize Client
    client = genai.Client(api_key=GEMINI_KEY)

# Models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[Dict[str, str]] = []

class PDFSummaryRequest(BaseModel):
    text: str = Field(..., min_length=1)

class YTSummaryRequest(BaseModel):
    title: str
    transcript: Optional[str] = None
    url: Optional[str] = None

# --- Helper ---
def call_gemini(prompt: str, system_instruction: str = ""):
    if not client:
        raise HTTPException(status_code=500, detail="AI Service is not configured")

    try:
        # Use the cutting-edge Gemini 3 Flash Preview as requested
        model_name = 'gemini-3-flash-preview'
        full_message = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
        
        response = client.models.generate_content(
            model=model_name,
            contents=full_message
        )
        
        if not response or not response.text:
            return "I am sorry, I couldn't process that. Your message might have been flagged or is empty."
            
        return response.text
    except Exception as e:
        logger.error(f"Gemini 3 API Error: {e}")
        raise HTTPException(status_code=503, detail="Gemini 3 Service is currently unavailable")

# --- Routes ---

@router.post("/chat")
async def chat_with_bot(request: ChatRequest, current_user: Dict = Depends(get_current_user)):
    """General chat with FocusBot"""
    system_prompt = (
        "You are FocusBot, the AI study assistant for FocusFlow. "
        "Your tone is encouraging, intelligent, and focused on student productivity. "
        "Keep your answers concise and provide helpful study tips where appropriate. "
        f"You are talking to {current_user['username']}."
    )
    
    # We could process history here, but for now simple one-shot for speed
    response = call_gemini(request.message, system_instruction=system_prompt)
    return {"message": response}

@router.post("/summarize_pdf")
async def summarize_pdf(request: PDFSummaryRequest, current_user: Dict = Depends(get_current_user)):
    """Summarize PDF content extracted from frontend"""
    prompt = (
        "Please provide a concise summary of the following study material. "
        "Identify the top 3-5 key takeaways. "
        "Material: \n\n" + request.text[:15000] # Limit tokens for flash
    )
    
    summary = call_gemini(prompt, system_instruction="You are an expert academic summarizer.")
    return {"summary": summary}

@router.post("/summarize_yt")
async def summarize_youtube(request: YTSummaryRequest, current_user: Dict = Depends(get_current_user)):
    """Summarize YouTube video based on transcript or metadata"""
    content = request.transcript if request.transcript else f"Video Title: {request.title}"
    prompt = (
        f"The user is watching a video titled: '{request.title}'. "
        "Please summarize the main educational points of this video. "
        "If a transcript is provided below, use it. Otherwise, explain what a video "
        "with this title would likely cover for a student. \n\n"
        "Transcript/Content: \n" + content[:15000]
    )
    
    summary = call_gemini(prompt, system_instruction="You are a helpful study tutor specialized in video summaries.")
    return {"summary": summary}

@router.post("/summarize_upload")
async def summarize_upload(
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user)
):
    """Upload a PDF, extract text locally, and summarize it via AI"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # 1. Read PDF Binary
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        
        # 2. Extract Text (limit for speed/tokens)
        full_text = ""
        max_pages = min(20, len(pdf_reader.pages))
        for i in range(max_pages):
            try:
                page_text = pdf_reader.pages[i].extract_text()
                if page_text:
                    full_text += page_text + "\n"
            except Exception as e:
                print(f"⚠️ Page {i} extraction error: {e}")

        if len(full_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="This PDF appears to be empty or image-based. I can only read PDFs with actual text.")

        # 3. Call Gemini
        print(f"📄 Summarizing PDF: {file.filename} ({len(full_text)} chars)")
        prompt = (
            f"Please summarize the following PDF document titled '{file.filename}'. "
            "Identify the key technical points and create a bulleted list of 5 takeaways. "
            "Content:\n\n" + full_text[:15000]
        )
        
        summary = call_gemini(prompt, system_instruction="You are a brilliant academic tutor.")
        return {"summary": summary, "filename": file.filename}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ PDF Error: {str(e)}")
        logger.error(f"PDF Upload/Summary Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
