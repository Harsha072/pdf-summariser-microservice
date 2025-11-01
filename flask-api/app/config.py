"""
Configuration module for Academic Paper Discovery Engine
Handles all application configuration including Firebase, Redis, OpenAI, and general settings.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from root directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Main application configuration"""
    
    # Application Settings
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', 4))
    DEFAULT_MAX_RESULTS = int(os.getenv('DEFAULT_MAX_RESULTS', 10))
    MAX_ALLOWED_RESULTS = int(os.getenv('MAX_ALLOWED_RESULTS', 20))
    DUPLICATE_THRESHOLD = float(os.getenv('DUPLICATE_THRESHOLD', 0.85))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', 16777216))  # 16MB
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', 0.3))
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', 1000))
    
    # Create temp directory
    os.makedirs(TEMP_DIR, exist_ok=True)


class RedisConfig:
    """Redis configuration and client initialization"""
    
    def __init__(self):
        self.enabled = os.getenv('ENABLE_REDIS', 'true').lower() == 'true'
        self.client = None
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis client with proper error handling"""
        if not self.enabled:
            logger.info("🔒 Redis caching disabled via ENABLE_REDIS=false")
            return
        
        try:
            import redis
            self.REDIS_AVAILABLE = True
        except ImportError:
            logger.warning("📦 Redis library not available. Install with: pip install redis")
            self.REDIS_AVAILABLE = False
            return
        
        if not self.REDIS_AVAILABLE:
            return
        
        try:
            # Check for Redis URL first (production platforms)
            redis_url = os.getenv('REDIS_URL')
            
            if redis_url:
                # Parse Redis URL (production platforms like Redis Cloud, Heroku, Railway)
                self.client = redis.from_url(
                    redis_url,
                    decode_responses=False,
                    socket_timeout=10,
                    socket_connect_timeout=10,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                logger.info(f"🔗 Connecting to Redis via URL: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
            else:
                # Individual configuration with SSL and password support
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_password = os.getenv('REDIS_PASSWORD')
                redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
                redis_db = int(os.getenv('REDIS_DB', 0))
                
                logger.info(f"🔗 Connecting to Redis: {redis_host}:{redis_port} (SSL: {redis_ssl})")
                
                self.client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    db=redis_db,
                    decode_responses=False,
                    socket_timeout=10,
                    socket_connect_timeout=10,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    ssl=redis_ssl,
                    ssl_cert_reqs=None if redis_ssl else None
                )
            
            # Test connection
            logger.info("🔍 Testing Redis connection...")
            self.client.ping()
            logger.info("✅ Redis client initialized successfully - Caching ENABLED")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.info("📝 Application will continue without caching.")
            logger.info("🔧 Debug info:")
            logger.info(f"   - REDIS_HOST: {os.getenv('REDIS_HOST', 'not set')}")
            logger.info(f"   - REDIS_PORT: {os.getenv('REDIS_PORT', 'not set')}")
            logger.info(f"   - REDIS_PASSWORD: {'set' if os.getenv('REDIS_PASSWORD') else 'not set'}")
            logger.info(f"   - REDIS_SSL: {os.getenv('REDIS_SSL', 'not set')}")
            logger.info(f"   - REDIS_URL: {'set' if os.getenv('REDIS_URL') else 'not set'}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available and connected"""
        return self.client is not None


class FirebaseConfig:
    """Firebase configuration and initialization"""
    
    def __init__(self):
        self.app = None
        self.available = False
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            import firebase_admin
            from firebase_admin import credentials, auth as firebase_auth
            self.FIREBASE_AVAILABLE = True
            self.firebase_admin = firebase_admin
            self.firebase_auth = firebase_auth
        except ImportError:
            logger.warning("⚠️ Firebase Admin SDK not available. Install with: pip install firebase-admin")
            self.FIREBASE_AVAILABLE = False
            return
        
        if not self.FIREBASE_AVAILABLE:
            return
        
        try:
            # Option 1: Using service account key file
            service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                self.app = firebase_admin.initialize_app(cred)
                logger.info("✅ Firebase Admin SDK initialized with service account file")
                self.available = True
            
            # Option 2: Using service account JSON from environment variable
            elif os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON'):
                import json
                service_account_info = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON'))
                cred = credentials.Certificate(service_account_info)
                self.app = firebase_admin.initialize_app(cred)
                logger.info("✅ Firebase Admin SDK initialized with environment JSON")
                self.available = True
            
            else:
                logger.warning("⚠️ Firebase service account not configured - auth features disabled")
                logger.info("💡 Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON environment variable")
                
        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
            self.app = None
            self.available = False
    
    def is_available(self) -> bool:
        """Check if Firebase is available and initialized"""
        return self.available and self.app is not None
    
    def get_auth(self):
        """Get Firebase Auth instance"""
        if self.is_available():
            return self.firebase_auth
        return None


class OpenAIConfig:
    """OpenAI configuration and client initialization"""
    
    def __init__(self):
        self.client = None
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client"""
        try:
            from langchain_openai import ChatOpenAI
            
            api_key = Config.OPENAI_API_KEY
            if api_key and api_key.strip():
                self.client = ChatOpenAI(
                    api_key=api_key,
                    model_name=Config.OPENAI_MODEL,
                    temperature=Config.OPENAI_TEMPERATURE,
                    max_tokens=Config.OPENAI_MAX_TOKENS
                )
                logger.info("✅ OpenAI client initialized successfully")
            else:
                logger.warning("⚠️ OpenAI API key not found. AI features will use fallback methods.")
                logger.info("💡 Set OPENAI_API_KEY environment variable to enable AI features")
                
        except ImportError:
            logger.warning("⚠️ OpenAI library not available. Install with: pip install langchain-openai")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if OpenAI client is available"""
        return self.client is not None


class ExternalLibrariesConfig:
    """Configuration for checking external library availability"""
    
    def __init__(self):
        # Removed arXiv - using only OpenAlex
        pass


# Initialize all configurations
config = Config()
redis_config = RedisConfig()
firebase_config = FirebaseConfig()
openai_config = OpenAIConfig()
external_libs = ExternalLibrariesConfig()

# Export convenience variables for backward compatibility
redis_client = redis_config.client
firebase_app = firebase_config.app
openai_client = openai_config.client
FIREBASE_AVAILABLE = firebase_config.is_available()
REDIS_AVAILABLE = redis_config.is_available()

# Log configuration summary
logger.info("=" * 60)
logger.info("🔬 Academic Paper Discovery Engine - Configuration Summary")
logger.info("=" * 60)
logger.info(f"🔧 Debug Mode: {config.DEBUG}")
logger.info(f"📁 Temp Directory: {config.TEMP_DIR}")
logger.info(f"🤖 OpenAI Available: {openai_config.is_available()}")
logger.info(f"🔥 Firebase Available: {firebase_config.is_available()}")
logger.info(f"📊 Redis Available: {redis_config.is_available()}")
# Removed arXiv logging - using only OpenAlex
logger.info("=" * 60)