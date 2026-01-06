from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}
APIRouter, HTTPException, Request, Response, Cookie
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import requests
from emergentintegrations.llm.chat import LlmChat, UserMessage
import hashlib
import hmac
import json

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

# Configuration
BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY')
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Gemini API Keys - Multiple keys for rotation
GEMINI_API_KEYS_STR = os.environ.get('GEMINI_API_KEYS', '')
GEMINI_API_KEYS = [key.strip() for key in GEMINI_API_KEYS_STR.split(',') if key.strip()]
CURRENT_GEMINI_KEY_INDEX = 0

SHOPIER_API_KEY = os.environ.get('SHOPIER_API_KEY')
SHOPIER_CLIENT_SECRET = os.environ.get('SHOPIER_CLIENT_SECRET')
SHOPIER_API_TOKEN = os.environ.get('SHOPIER_API_TOKEN')

# Shopier product mappings
SHOPIER_PRODUCTS = {
    "package_20": {"url": "https://shopier.com/39003278", "product_id": "39003278"},
    "package_50": {"url": "https://shopier.com/42901869", "product_id": "42901869"},
    "package_100": {"url": "https://shopier.com/42901899", "product_id": "42901899"}
}

# Define Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    credits: int = 10  # 5 anonymous + 5 for login
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PropertyAnalysisRequest(BaseModel):
    il: str
    ilce: str
    mahalle: str
    ada: str
    parsel: str

class PropertyAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    analysis: str
    remaining_credits: int
    search_query: str

class SessionExchangeRequest(BaseModel):
    session_id: str

class PaymentPackage(BaseModel):
    name: str
    credits: int
    price: float
    description: str

# Helper Functions
def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host

async def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)) -> Optional[dict]:
    """Get current user from session token (cookie or Authorization header)"""
    # REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    token = session_token
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
    
    if not token:
        return None
    
    session_doc = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session_doc:
        return None
    
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    return user_doc

async def get_or_create_anonymous_session(ip: str) -> dict:
    """Get or create anonymous session based on IP"""
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()
    session = await db.anonymous_sessions.find_one({"ip_hash": ip_hash}, {"_id": 0})
    
    if not session:
        session = {
            "ip_hash": ip_hash,
            "credits_used": 0,
            "analyses": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": datetime.now(timezone.utc).isoformat()
        }
        await db.anonymous_sessions.insert_one(session.copy())
    
    return session

async def search_brave(query: str) -> str:
    """Search using Brave Search API with multiple strategies"""
    try:
        headers = {
            "X-Subscription-Token": BRAVE_API_KEY,
            "Accept": "application/json",
            "Accept-Encoding": "gzip"
        }
        
        all_results = []
        
        # Strategy 1: Direct query with technical terms
        params1 = {
            "q": query,
            "count": 10,
            "search_lang": "tr",
            "country": "tr"
        }
        
        response1 = requests.get(BRAVE_SEARCH_URL, headers=headers, params=params1, timeout=10)
        response1.raise_for_status()
        data1 = response1.json()
        
        if 'web' in data1 and 'results' in data1['web']:
            all_results.extend(data1['web']['results'][:5])
        
        # Strategy 2: Search for belediye imar durum (municipality zoning)
        query_parts = query.split()
        if len(query_parts) >= 5:  # il ilce mahalle ada parsel
            il, ilce, mahalle = query_parts[0], query_parts[1], query_parts[2]
            params2 = {
                "q": f"{il} {ilce} belediyesi imar durumu {mahalle}",
                "count": 10,
                "search_lang": "tr",
                "country": "tr"
            }
            
            response2 = requests.get(BRAVE_SEARCH_URL, headers=headers, params=params2, timeout=10)
            if response2.status_code == 200:
                data2 = response2.json()
                if 'web' in data2 and 'results' in data2['web']:
                    all_results.extend(data2['web']['results'][:5])
        
        # Format results
        results_text = []
        seen_urls = set()
        
        for result in all_results:
            url = result.get('url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                title = result.get('title', '')
                description = result.get('description', '')
                results_text.append(f"Başlık: {title}\nAçıklama: {description}\nURL: {url}\n")
        
        return "\n\n".join(results_text[:10]) if results_text else "Arama sonucu bulunamadı. Farklı bir bölge veya ada-parsel numarası deneyebilirsiniz."
    
    except Exception as e:
        logging.error(f"Brave Search error: {str(e)}")
        return f"Arama hatası: {str(e)}"

async def analyze_with_gemini(property_info: str, search_results: str) -> str:
    """Analyze property using Gemini AI with automatic API key rotation"""
    global CURRENT_GEMINI_KEY_INDEX
    
    if not GEMINI_API_KEYS:
        return "Gemini API anahtarları yapılandırılmamış."
    
    # Try all API keys
    for attempt in range(len(GEMINI_API_KEYS)):
        try:
            current_key = GEMINI_API_KEYS[CURRENT_GEMINI_KEY_INDEX]
            
            logging.info(f"Using Gemini API key #{CURRENT_GEMINI_KEY_INDEX + 1} (Key: ...{current_key[-8:]})")
            
            chat = LlmChat(
                api_key=current_key,
                session_id="property-analysis",
                system_message="Sen bir arsa ve gayrimenkul uzmanısın. Verilen bilgilere dayanarak detaylı imar durumu analizi yapıyorsun. Türkçe ve profesyonel bir dille cevap veriyorsun. Yanıtlarını markdown formatında değil, düz metin olarak ver. ** veya # gibi işaretler kullanma, sadece başlıkları büyük harfle yaz. Teknik detayları (KAK, TAKS, emsal, kat yüksekliği vb.) mutlaka belirt."
            ).with_model("gemini", "gemini-3-flash-preview")
            
            user_message = UserMessage(
                text=f"""Aşağıdaki arsa için DETAYLI imar durumu analizi yap:

Arsa Bilgileri:
{property_info}

İnternetten Bulunan Bilgiler:
{search_results}

ÖNEMLİ: Analiz yaparken aşağıdaki TEKNİK BİLGİLERİ mutlaka ara ve varsa belirt:

1. İMAR DURUMU
   - İmar durumu (imarlı/imarı yok/tarla vb.)
   - İmar planı bilgileri
   - Alan kullanımı (konut/ticaret/karma vb.)

2. YAPILAŞMA KOŞULLARI (Varsa teknik detayları belirt)
   - KAK (Kat Alanı Katsayısı): 
   - TAKS (Taban Alanı Katsayısı):
   - Emsal (İnşaat Emsali):
   - Maksimum Kat Sayısı:
   - Yapı Yüksekliği:
   - İnşaat Alanı:

3. BÖLGE ÖZELLİKLERİ
   - Bölgenin konumu ve özellikleri
   - Çevredeki gelişmeler
   - Ulaşım imkanları

4. DİKKAT EDİLMESİ GEREKEN HUSUSLAR
   - Önemli kısıtlamalar
   - Yasal düzenlemeler
   - Riskler veya fırsatlar

5. GENEL DEĞERLENDİRME
   - Toparlatıcı değerlendirme
   - Yatırım potansiyeli

ÖNEMLİ NOTLAR:
- Eğer KAK, TAKS gibi teknik bilgileri bulamazsan, "Bu bilgiler internette bulunamadı, kesin bilgi için ilgili belediyenin İmar ve Şehircilik Müdürlüğü'ne başvurulmalıdır" şeklinde belirt.
- Yanıtını düz metin olarak ver. Markdown formatı kullanma (**, ##, ### gibi). Başlıkları sadece büyük harfle yaz.
- Temiz ve okunakli bir format kullan."""
            )
            
            response = await chat.send_message(user_message)
            
            # Clean up any remaining markdown symbols
            cleaned_response = response.replace('**', '').replace('##', '').replace('###', '')
            
            logging.info(f"✓ Gemini API key #{CURRENT_GEMINI_KEY_INDEX + 1} successful")
            return cleaned_response
        
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a quota/rate limit error
            if any(keyword in error_str for keyword in ['quota', 'rate limit', 'resource exhausted', '429', 'quota exceeded']):
                logging.warning(f"⚠ Gemini API key #{CURRENT_GEMINI_KEY_INDEX + 1} quota exceeded. Trying next key...")
                
                # Move to next key
                CURRENT_GEMINI_KEY_INDEX = (CURRENT_GEMINI_KEY_INDEX + 1) % len(GEMINI_API_KEYS)
                
                # If we've tried all keys, return error
                if attempt == len(GEMINI_API_KEYS) - 1:
                    logging.error("❌ All Gemini API keys exhausted!")
                    return "Tüm Gemini API anahtarlarının kotası doldu. Lütfen daha sonra tekrar deneyin."
                
                # Try next key
                continue
            else:
                # Other error, log and try next key
                logging.error(f"❌ Gemini API error with key #{CURRENT_GEMINI_KEY_INDEX + 1}: {str(e)}")
                CURRENT_GEMINI_KEY_INDEX = (CURRENT_GEMINI_KEY_INDEX + 1) % len(GEMINI_API_KEYS)
                
                if attempt == len(GEMINI_API_KEYS) - 1:
                    return f"Analiz hatası: {str(e)}"
                
                continue
    
    return "Analiz yapılamadı. Lütfen tekrar deneyin."

# Auth Routes
@api_router.post("/auth/session")
async def exchange_session(request: SessionExchangeRequest, response: Response):
    """Exchange session_id for user data and session_token"""
    try:
        # Call Emergent Auth API
        auth_response = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": request.session_id},
            timeout=10
        )
        auth_response.raise_for_status()
        auth_data = auth_response.json()
        
        # Check if user exists
        user_doc = await db.users.find_one({"email": auth_data["email"]}, {"_id": 0})
        
        if user_doc:
            user_id = user_doc["user_id"]
            # Update user info
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "name": auth_data["name"],
                    "picture": auth_data.get("picture")
                }}
            )
        else:
            # Create new user with 10 credits (5 anonymous + 5 login bonus)
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            user_doc = {
                "user_id": user_id,
                "email": auth_data["email"],
                "name": auth_data["name"],
                "picture": auth_data.get("picture"),
                "credits": 10,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user_doc.copy())
        
        # Create session
        session_token = auth_data["session_token"]
        session_doc = {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.user_sessions.insert_one(session_doc.copy())
        
        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7*24*60*60
        )
        
        # Get fresh user data
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        
        return user
    
    except Exception as e:
        logging.error(f"Session exchange error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/auth/me")
async def get_me(request: Request, session_token: Optional[str] = Cookie(None)):
    """Get current user info"""
    user = await get_current_user(request, session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout user"""
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# Analysis Routes
@api_router.post("/analyze-property", response_model=PropertyAnalysisResponse)
async def analyze_property(request_data: PropertyAnalysisRequest, request: Request, session_token: Optional[str] = Cookie(None)):
    """Analyze property with Brave Search and Gemini AI"""
    try:
        user = await get_current_user(request, session_token)
        
        if user:
            # Authenticated user
            if user['credits'] <= 0:
                raise HTTPException(
                    status_code=403,
                    detail="Krediniz bitti. Lütfen kredi satın alın."
                )
            
            # Create search query
            search_query = f"{request_data.il} {request_data.ilce} {request_data.mahalle} ada {request_data.ada} parsel {request_data.parsel} imar durumu KAK TAKS emsal yapılaşma koşulları"
            
            # Search and analyze
            search_results = await search_brave(search_query)
            property_info = f"İl: {request_data.il}, İlçe: {request_data.ilce}, Mahalle: {request_data.mahalle}, Ada: {request_data.ada}, Parsel: {request_data.parsel}"
            analysis = await analyze_with_gemini(property_info, search_results)
            
            # Update user credits
            new_credits = user['credits'] - 1
            await db.users.update_one(
                {"user_id": user['user_id']},
                {"$set": {"credits": new_credits}}
            )
            
            # Save analysis
            await db.analyses.insert_one({
                "user_id": user['user_id'],
                "property_info": property_info,
                "search_query": search_query,
                "analysis": analysis,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return PropertyAnalysisResponse(
                analysis=analysis,
                remaining_credits=new_credits,
                search_query=search_query
            )
        else:
            # Anonymous user
            ip = get_client_ip(request)
            session = await get_or_create_anonymous_session(ip)
            
            if session['credits_used'] >= 5:
                raise HTTPException(
                    status_code=403,
                    detail="Ücretsiz kullanım hakkınız dolmuştur. Lütfen giriş yapınız."
                )
            
            # Create search query
            search_query = f"{request_data.il} {request_data.ilce} {request_data.mahalle} ada {request_data.ada} parsel {request_data.parsel} imar durumu KAK TAKS emsal yapılaşma koşulları"
            
            # Search and analyze
            search_results = await search_brave(search_query)
            property_info = f"İl: {request_data.il}, İlçe: {request_data.ilce}, Mahalle: {request_data.mahalle}, Ada: {request_data.ada}, Parsel: {request_data.parsel}"
            analysis = await analyze_with_gemini(property_info, search_results)
            
            # Update anonymous session
            new_credits_used = session['credits_used'] + 1
            await db.anonymous_sessions.update_one(
                {"ip_hash": session['ip_hash']},
                {
                    "$set": {
                        "credits_used": new_credits_used,
                        "last_used": datetime.now(timezone.utc).isoformat()
                    },
                    "$push": {
                        "analyses": {
                            "property_info": property_info,
                            "search_query": search_query,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
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

@api_router.get("/credits")
async def get_credits(request: Request, session_token: Optional[str] = Cookie(None)):
    """Get remaining credits"""
    user = await get_current_user(request, session_token)
    
    if user:
        return {
            "remaining_credits": user['credits'],
            "is_authenticated": True
        }
    else:
        ip = get_client_ip(request)
        session = await get_or_create_anonymous_session(ip)
        return {
            "remaining_credits": 5 - session['credits_used'],
            "is_authenticated": False
        }

# Payment Routes
@api_router.get("/payment/packages")
async def get_payment_packages():
    """Get available payment packages"""
    packages = [
        {
            "id": "package_20",
            "name": "Standart Plan",
            "credits": 20,
            "price": 50.0,
            "description": "Küçük projeler için"
        },
        {
            "id": "package_50",
            "name": "Pro Plan",
            "credits": 50,
            "price": 75.0,
            "description": "Orta ölçekli projeler için",
            "popular": True
        },
        {
            "id": "package_100",
            "name": "Uzman Plan",
            "credits": 100,
            "price": 100.0,
            "description": "Büyük projeler için"
        }
    ]
    return packages

@api_router.post("/payment/create")
async def create_payment(package_id: str, request: Request, session_token: Optional[str] = Cookie(None)):
    """Create Shopier payment"""
    user = await get_current_user(request, session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Giriş yapmalısınız")
    
    # Get package details
    packages_response = await get_payment_packages()
    package = next((p for p in packages_response if p['id'] == package_id), None)
    
    if not package:
        raise HTTPException(status_code=404, detail="Paket bulunamadı")
    
    # Create payment URL (Shopier integration)
    # Note: Shopier API is webhook-based, actual implementation would need Shopier API endpoint
    payment_url = f"https://www.shopier.com/payment?amount={package['price']}&user_id={user['user_id']}&package_id={package_id}"
    
    return {
        "payment_url": payment_url,
        "package": package
    }

@api_router.post("/payment/webhook")
async def payment_webhook(request: Request):
    """Handle Shopier OSB (Otomatik Sipariş Bildirimi) webhook"""
    try:
        # Shopier OSB credentials
        OSB_USERNAME = "778002c5c84cec73b28e5dc61252b7c7"
        OSB_KEY = "8464992188fb72b30d314d7087bf1538"
        
        # Get form data (Shopier sends as form-encoded)
        form_data = await request.form()
        
        logging.info(f"=== SHOPIER OSB WEBHOOK RECEIVED ===")
        logging.info(f"Form data keys: {list(form_data.keys())}")
        
        # Check required parameters
        if 'res' not in form_data or 'hash' not in form_data:
            logging.error("Missing parameters: res or hash")
            return {"status": "error", "message": "missing parameter"}
        
        res = form_data['res']
        received_hash = form_data['hash']
        
        # Verify hash (HMAC-SHA256)
        import base64
        calculated_hash = hmac.new(
            OSB_KEY.encode(),
            (res + OSB_USERNAME).encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash != received_hash:
            logging.error(f"Hash mismatch! Calculated: {calculated_hash}, Received: {received_hash}")
            return {"status": "error", "message": "invalid hash"}
        
        # Decode base64 JSON
        json_data = base64.b64decode(res).decode('utf-8')
        data = json.loads(json_data)
        
        logging.info(f"Decoded order data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Extract order information
        email = data.get('email')
        orderid = data.get('orderid')
        price = float(data.get('price', 0))
        buyername = data.get('buyername')
        buyersurname = data.get('buyersurname')
        istest = data.get('istest', 0)
        currency = data.get('currency', 0)  # 0=TL, 1=USD, 2=EUR
        
        logging.info(f"Order: {orderid}, Email: {email}, Price: {price} TL, Test: {istest}")
        
        # Skip test orders in production
        if istest == 1:
            logging.info("Test order - processing anyway for development")
        
        # Check if order already processed
        existing_payment = await db.payments.find_one({"order_id": orderid}, {"_id": 0})
        if existing_payment:
            logging.warning(f"Order already processed: {orderid}")
            return Response(content="success", media_type="text/plain")
        
        # Find user by email
        if not email:
            logging.error("No email in order data")
            return Response(content="success", media_type="text/plain")
        
        user_doc = await db.users.find_one({"email": email}, {"_id": 0})
        if not user_doc:
            logging.warning(f"User not found with email: {email}")
            return Response(content="success", media_type="text/plain")
        
        user_id = user_doc['user_id']
        logging.info(f"Found user: {user_id}")
        
        # Determine package and credits from price
        credits_to_add = 0
        package_id = None
        
        if 48 <= price <= 52:  # 50 TL
            credits_to_add = 20
            package_id = "package_20"
        elif 73 <= price <= 77:  # 75 TL
            credits_to_add = 50
            package_id = "package_50"
        elif 98 <= price <= 102:  # 100 TL
            credits_to_add = 100
            package_id = "package_100"
        
        logging.info(f"Package: {package_id}, Credits to add: {credits_to_add}")
        
        if credits_to_add > 0:
            # Add credits to user
            result = await db.users.update_one(
                {"user_id": user_id},
                {"$inc": {"credits": credits_to_add}}
            )
            
            logging.info(f"Credits update: {result.modified_count} user(s) updated")
            
            # Save payment record
            await db.payments.insert_one({
                "user_id": user_id,
                "package_id": package_id,
                "credits": credits_to_add,
                "amount": price,
                "status": "completed",
                "order_id": orderid,
                "buyer_email": email,
                "buyer_name": f"{buyername} {buyersurname}",
                "is_test": istest,
                "shopier_data": data,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            # Verify credits
            updated_user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "credits": 1})
            logging.info(f"✓✓✓ SUCCESS! User {user_id} ({email}) now has {updated_user.get('credits', 0)} credits")
            
            # Shopier expects "success" response
            return Response(content="success", media_type="text/plain")
        else:
            logging.warning(f"Unknown package amount: {price}")
            return Response(content="success", media_type="text/plain")
    
    except Exception as e:
        logging.error(f"❌ SHOPIER OSB ERROR: {str(e)}", exc_info=True)
        return Response(content="error", media_type="text/plain")

@api_router.get("/")
async def root():
    return {"message": "parseldeğer.com API"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()