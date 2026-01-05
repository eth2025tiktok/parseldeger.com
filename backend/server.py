from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import requests
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Brave Search API Configuration
BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY')
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Define Models
class PropertyAnalysisRequest(BaseModel):
    il: str
    ilce: str
    mahalle: str
    ada: str
    parsel: str
    session_id: Optional[str] = None

class PropertyAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    analysis: str
    remaining_credits: int
    search_query: str

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    session_id: str
    credits_used: int = 0
    analyses: List[dict] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Brave Search Function
async def search_brave(query: str) -> str:
    """Search using Brave Search API and return relevant results"""
    try:
        headers = {
            "X-Subscription-Token": BRAVE_API_KEY,
            "Accept": "application/json",
            "Accept-Encoding": "gzip"
        }
        
        params = {
            "q": query,
            "count": 10,
            "search_lang": "tr",
            "country": "tr"
        }
        
        response = requests.get(BRAVE_SEARCH_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract relevant information from search results
        results_text = []
        if 'web' in data and 'results' in data['web']:
            for result in data['web']['results'][:5]:  # Top 5 results
                title = result.get('title', '')
                description = result.get('description', '')
                url = result.get('url', '')
                results_text.append(f"Başlık: {title}\nAçıklama: {description}\nURL: {url}\n")
        
        return "\n\n".join(results_text) if results_text else "Arama sonucu bulunamadı."
    
    except Exception as e:
        logging.error(f"Brave Search error: {str(e)}")
        return f"Arama hatası: {str(e)}"

# Gemini Analysis Function
async def analyze_with_gemini(property_info: str, search_results: str) -> str:
    """Analyze property using Gemini AI"""
    try:
        chat = LlmChat(
            api_key=GEMINI_API_KEY,
            session_id="property-analysis",
            system_message="Sen bir arsa ve gayrimenkul uzmanısın. Verilen bilgilere dayanarak detaylı imar durumu analizi yapıyorsun. Türkçe ve profesyonel bir dille cevap veriyorsun."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        user_message = UserMessage(
            text=f"""Aşağıdaki arsa için imar durumu analizi yap:

Arsa Bilgileri:
{property_info}

İnternetten Bulunan Bilgiler:
{search_results}

Lütfen aşağıdaki konularda detaylı analiz yap:
1. İmar durumu (varsa)
2. Bölge özellikleri
3. Yapılaşma koşulları (varsa)
4. Dikkat edilmesi gereken hususlar
5. Genel değerlendirme

Analizi Türkçe, açık ve anlaşılır bir dilde yap."""
        )
        
        response = await chat.send_message(user_message)
        return response
    
    except Exception as e:
        logging.error(f"Gemini analysis error: {str(e)}")
        return f"Analiz hatası: {str(e)}"

# Get or create user session
async def get_or_create_session(session_id: Optional[str]) -> dict:
    """Get existing session or create new one"""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    session = await db.user_sessions.find_one({"session_id": session_id}, {"_id": 0})
    
    if not session:
        session = {
            "session_id": session_id,
            "credits_used": 0,
            "analyses": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": datetime.now(timezone.utc).isoformat()
        }
        await db.user_sessions.insert_one(session.copy())
    
    return session

# Routes
@api_router.get("/")
async def root():
    return {"message": "ArsaEkspertizAI API"}

@api_router.post("/analyze-property", response_model=PropertyAnalysisResponse)
async def analyze_property(request: PropertyAnalysisRequest):
    """Analyze property with Brave Search and Gemini AI"""
    try:
        # Get or create session
        session = await get_or_create_session(request.session_id)
        
        # Check credits
        if session['credits_used'] >= 5:
            raise HTTPException(
                status_code=403,
                detail="Ücretsiz kullanım hakkınız dolmuştur. Lütfen giriş yapınız."
            )
        
        # Create search query
        search_query = f"{request.il} {request.ilce} {request.mahalle} ada {request.ada} parsel {request.parsel} imar durumu"
        
        # Search with Brave
        search_results = await search_brave(search_query)
        
        # Create property info
        property_info = f"İl: {request.il}, İlçe: {request.ilce}, Mahalle: {request.mahalle}, Ada: {request.ada}, Parsel: {request.parsel}"
        
        # Analyze with Gemini
        analysis = await analyze_with_gemini(property_info, search_results)
        
        # Update session
        new_credits_used = session['credits_used'] + 1
        analysis_record = {
            "property_info": property_info,
            "search_query": search_query,
            "analysis": analysis,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.user_sessions.update_one(
            {"session_id": session['session_id']},
            {
                "$set": {
                    "credits_used": new_credits_used,
                    "last_used": datetime.now(timezone.utc).isoformat()
                },
                "$push": {"analyses": analysis_record}
            }
        )
        
        return PropertyAnalysisResponse(
            analysis=analysis,
            remaining_credits=5 - new_credits_used,
            search_query=search_query
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analiz hatası: {str(e)}")

@api_router.get("/remaining-credits/{session_id}")
async def get_remaining_credits(session_id: str):
    """Get remaining credits for a session"""
    session = await get_or_create_session(session_id)
    return {
        "remaining_credits": 5 - session['credits_used'],
        "total_credits": 5
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()