
import os
import re
import json
import uuid
import time
import logging
import threading
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Flask and web framework imports
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Web scraping imports
import requests
import urllib.parse

# PDF processing imports
import fitz  # PyMuPDF

# Text similarity and processing
from fuzzywuzzy import fuzz

# RAG Components
from vector_database import VectorDatabase
from rag_pipeline import RAGPipelineManager

# Simple Paper Relationships Component
from simple_paper_relationships import SimplePaperRelationships
from citation_data_extractor import CitationDataExtractor

# Import configuration
from config import (
    config, 
    redis_client, 
    firebase_app, 
    firebase_config,
    openai_client,
    FIREBASE_AVAILABLE,
    REDIS_AVAILABLE,
    external_libs
)

# Removed arXiv API import - using OpenAlex only

# Get logger from config
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# CORS configuration - Allow all Vercel domains
# Using regex pattern for Vercel subdomains
CORS(app, 
     origins=r"https://.*\.vercel\.app",  # Regex to match all Vercel deployments
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'], 
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'X-Session-ID', 'Accept', 'Origin'],
     supports_credentials=True,
     max_age=3600)

# Log all incoming requests
@app.before_request
def log_request_info():
    """Log details about each incoming request"""
    logger.info('=' * 80)
    logger.info(f'🔵 Incoming Request: {request.method} {request.path}')
    logger.info(f'🌐 Origin: {request.headers.get("Origin", "No Origin header")}')
    logger.info(f'🔑 Authorization: {"Present" if request.headers.get("Authorization") else "Not present"}')
    logger.info(f'📍 Remote Address: {request.remote_addr}')
    logger.info(f'🔧 User Agent: {request.headers.get("User-Agent", "Unknown")[:100]}')
    if request.method == 'POST':
        logger.info(f'📦 Content-Type: {request.headers.get("Content-Type", "Not specified")}')
    logger.info('=' * 80)

# Add CORS headers to all responses for maximum compatibility
@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    origin = request.headers.get('Origin', '')
    
    # Log origin for debugging (skip health checks and requests without origin)
    if origin:
        logger.info(f"✅ Response to origin: {origin} - Status: {response.status_code}")
    
    # Allow localhost and all Vercel domains
    if (origin.startswith('http://localhost:') or 
        origin.startswith('http://127.0.0.1:') or 
        origin.endswith('.vercel.app')):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,X-Session-ID,Accept,Origin'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS,PATCH'
        logger.info(f"✅ CORS headers added for origin: {origin}")
    elif origin:  # Only warn if there's an origin header that's not allowed
        logger.warning(f"❌ Origin not allowed: {origin}")
    
    return response

# Firebase authentication decorator
def firebase_auth_required(f):
    """Decorator to require Firebase authentication for endpoints"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not firebase_config.is_available():
            return jsonify({'error': 'Authentication not available'}), 503
            
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Verify Firebase token using config
            firebase_auth = firebase_config.get_auth()
            decoded_token = firebase_auth.verify_id_token(token)
            request.current_user = {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture'),
                'provider': decoded_token.get('firebase', {}).get('sign_in_provider', 'unknown')
            }
            
            logger.info(f"🔐 Authenticated user: {request.current_user['email']}")
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated_function

# Optional authentication decorator (works for both authenticated and anonymous users)
def firebase_auth_optional(f):
    """Decorator for optional Firebase authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request.current_user = None  # Default to no user
        
        if not firebase_config.is_available():
            return f(*args, **kwargs)
            
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            try:
                firebase_auth = firebase_config.get_auth()
                decoded_token = firebase_auth.verify_id_token(token[7:])
                request.current_user = {
                    'uid': decoded_token['uid'],
                    'email': decoded_token.get('email'),
                    'name': decoded_token.get('name'),
                    'picture': decoded_token.get('picture'),
                    'provider': decoded_token.get('firebase', {}).get('sign_in_provider', 'unknown')
                }
                logger.info(f"🔐 Authenticated user: {request.current_user['email']}")
            except Exception as e:
                logger.warning(f"Invalid token provided: {e}")
                # Continue as anonymous user
        
        return f(*args, **kwargs)
    
    return decorated_function

# Global processing status tracking
processing_status = {}
status_lock = threading.Lock()


class RedisCacheManager:
    """Redis cache manager for search results and paper details"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.logger = logger
        self.enabled = redis_client is not None
        
        # Cache TTL settings (in seconds)
        self.SEARCH_RESULTS_TTL = 3600  # 1 hour
        self.PAPER_DETAILS_TTL = 7200   # 2 hours
        self.SESSION_TTL = 1800         # 30 minutes
    
    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments"""
        key_parts = [str(arg) for arg in args if arg is not None]
        key_string = "|".join(key_parts)
        # Create a hash for long keys
        import hashlib
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis"""
        return pickle.loads(data)
    
    def cache_search_results(self, query: str, sources: List[str], max_results: int, results: Dict[str, Any], session_id: str = None) -> bool:
        """Cache search results"""
        print(f"🔍 DEBUG: Starting cache operation for query: {query[:50]}...")
        print(f"🔍 DEBUG: Session ID: {session_id}")
        print(f"🔍 DEBUG: Redis enabled: {self.enabled}")
        
        if not self.enabled:
            print("❌ DEBUG: Redis not enabled, skipping cache")
            return False
        
        try:
            cache_key = self._generate_cache_key("search", query, "|".join(sorted(sources)), max_results)
            print(f"🔍 DEBUG: Generated cache key: {cache_key}")
            
            cache_data = {
                "results": results,
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "sources": sources,
                "max_results": max_results,
                "session_id": session_id
            }
            
            serialized_data = self._serialize_data(cache_data)
            print(f"🔍 DEBUG: Serialized data size: {len(serialized_data)} bytes")
            
            # Test Redis connection before caching
            self.redis_client.ping()
            print("🔍 DEBUG: Redis ping successful")
            
            # Cache the data
            result = self.redis_client.setex(cache_key, self.SEARCH_RESULTS_TTL, serialized_data)
            print(f"🔍 DEBUG: setex result: {result}")
            
            # Verify the data was cached
            test_data = self.redis_client.get(cache_key)
            print(f"🔍 DEBUG: Verification - data exists: {test_data is not None}")
            
            # Also cache by session ID if provided
            if session_id:
                session_key = f"session:{session_id}:last_search"
                session_result = self.redis_client.setex(session_key, self.SESSION_TTL, cache_key.encode())
                print(f"🔍 DEBUG: Session cache result: {session_result}")
            
            print("✅ DEBUG: Successfully cached search results")
            self.logger.info(f"Cached search results for query: {query[:50]}...")
            return True
            
        except Exception as e:
            print(f"❌ DEBUG: Cache operation failed: {e}")
            self.logger.error(f"Failed to cache search results: {e}")
            return False
    
    def get_cached_search_results(self, query: str, sources: List[str], max_results: int) -> Optional[Dict[str, Any]]:
        """Retrieve cached search results"""
        print(f"🔍 DEBUG: Looking for cached results for query: {query[:50]}...")
        print(f"🔍 DEBUG: Redis enabled: {self.enabled}")
        
        if not self.enabled:
            print("❌ DEBUG: Redis not enabled, returning None")
            return None
        
        try:
            cache_key = self._generate_cache_key("search", query, "|".join(sorted(sources)), max_results)
            print(f"🔍 DEBUG: Looking for cache key: {cache_key}")
            
            # Test Redis connection
            self.redis_client.ping()
            print("🔍 DEBUG: Redis ping successful")
            
            cached_data = self.redis_client.get(cache_key)
            print(f"🔍 DEBUG: Raw cached data found: {cached_data is not None}")
            
            if cached_data:
                data = self._deserialize_data(cached_data)
                print(f"🔍 DEBUG: Deserialized data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                self.logger.info(f"Retrieved cached search results for query: {query[:50]}...")
                return data
            else:
                print("❌ DEBUG: No cached data found")
            
            return None
            
        except Exception as e:
            print(f"❌ DEBUG: Cache retrieval failed: {e}")
            self.logger.error(f"Failed to retrieve cached search results: {e}")
            return None
    
    def cache_paper_details(self, paper: Dict[str, Any], analysis: Dict[str, Any], session_id: str = None) -> bool:
        """Cache paper details and analysis"""
        if not self.enabled:
            return False
        
        try:
            # Check if paper is None or not a dictionary
            if not paper or not isinstance(paper, dict):
                self.logger.warning("Cannot cache paper details: paper is None or not a dictionary")
                return False
                
            paper_id = paper.get('id') or paper.get('title', 'unknown')
            cache_key = self._generate_cache_key("paper_details", paper_id)
            
            serialized_data = self._serialize_data({
                "paper": paper,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            })
            
            self.redis_client.setex(cache_key, self.PAPER_DETAILS_TTL, serialized_data)
            self.logger.info(f"Cached paper details for: {paper.get('title', 'Unknown')[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache paper details: {e}")
            return False
    
    def get_cached_paper_details(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve cached paper details"""
        if not self.enabled:
            return None
        
        try:
            # Check if paper is None or not a dictionary
            if not paper or not isinstance(paper, dict):
                self.logger.warning("Cannot get cached paper details: paper is None or not a dictionary")
                return None
                
            paper_id = paper.get('id') or paper.get('title', 'unknown')
            cache_key = self._generate_cache_key("paper_details", paper_id)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                data = self._deserialize_data(cached_data)
                self.logger.info(f"Retrieved cached paper details for: {paper.get('title', 'Unknown')[:50]}...")
                return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve cached paper details: {e}")
            return None
    
    def get_session_last_search(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the last search results for a session"""
        if not self.enabled or not session_id:
            return None
        
        try:
            session_key = f"session:{session_id}:last_search"
            search_cache_key = self.redis_client.get(session_key)
            
            if search_cache_key:
                search_cache_key = search_cache_key.decode('utf-8')
                cached_data = self.redis_client.get(search_cache_key)
                
                if cached_data:
                    data = self._deserialize_data(cached_data)
                    self.logger.info(f"Retrieved session search results for session: {session_id}")
                    return data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve session search results: {e}")
            return None
    
    def clear_cache(self, pattern: str = None) -> bool:
        """Clear cache entries matching pattern"""
        if not self.enabled:
            return False
        
        try:
            if pattern:
                keys = self.redis_client.keys(f"*{pattern}*")
                if keys:
                    self.redis_client.delete(*keys)
                    self.logger.info(f"Cleared {len(keys)} cache entries matching pattern: {pattern}")
            else:
                self.redis_client.flushdb()
                self.logger.info("Cleared all cache entries")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False, "message": "Redis not available"}
        
        try:
            info = self.redis_client.info()
            return {
                "enabled": True,
                "connected_clients": info.get('connected_clients', 0),
                "used_memory": info.get('used_memory_human', 'N/A'),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "hit_rate": round(
                    info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)) * 100, 2
                )
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {"enabled": False, "error": str(e)}

    def get_recent_search_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all cached search results for a session"""
        if not self.enabled or not session_id:
            return []
        
        try:
            # Get all cache keys for the session - fix pattern to match key generation
            pattern = f"search:*"
            keys = self.redis_client.keys(pattern)
            
            results = []
            for key in keys:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        data = self._deserialize_data(cached_data)
                        # Check if this result belongs to the session
                        if data.get('session_id') == session_id:
                            results.append({
                                'query': data.get('query', ''),
                                'results': data.get('results', {}),
                                'timestamp': data.get('timestamp'),
                                'sources': data.get('sources', []),
                                'max_results': data.get('max_results', 10)
                            })
                except Exception as e:
                    self.logger.warning(f"Failed to deserialize cached result: {e}")
                    continue
            
            # Sort by timestamp (most recent first)
            results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return results[:5]  # Return last 5 searches
            
        except Exception as e:
            self.logger.error(f"Failed to get recent search results: {e}")
            return []

    def create_session(self) -> str:
        """Create a new session ID"""
        import uuid
        session_id = str(uuid.uuid4())
        
        if not self.enabled:
            return session_id
        
        try:
            # Store session metadata in Redis
            session_key = f"session:{session_id}"
            session_data = {
                'created_at': datetime.utcnow().isoformat(),
                'last_activity': datetime.utcnow().isoformat(),
                'searches_count': 0
            }
            
            serialized_data = self._serialize_data(session_data)
            self.redis_client.setex(session_key, self.SESSION_TTL, serialized_data)
            self.logger.info(f"Created new session: {session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create session in Redis: {e}")
        
        return session_id

    def clear_session_cache(self, session_id: str) -> int:
        """Clear all cache entries for a specific session"""
        if not self.enabled or not session_id:
            return 0
        
        try:
            cleared_count = 0
            
            # Clear search results for this session
            pattern = f"search_results:*"
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        data = self._deserialize_data(cached_data)
                        if data.get('session_id') == session_id:
                            self.redis_client.delete(key)
                            cleared_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to check cache entry: {e}")
                    continue
            
            # Clear paper details for this session
            pattern = f"paper_details:*"
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                try:
                    cached_data = self.redis_client.get(key)
                    if cached_data:
                        data = self._deserialize_data(cached_data)
                        if data.get('session_id') == session_id:
                            self.redis_client.delete(key)
                            cleared_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to check cache entry: {e}")
                    continue
            
            # Clear session metadata
            session_key = f"session:{session_id}"
            if self.redis_client.delete(session_key):
                cleared_count += 1
            
            self.logger.info(f"Cleared {cleared_count} cache entries for session {session_id}")
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"Failed to clear session cache: {e}")
            return 0

    def clear_all_cache(self) -> bool:
        """Clear all cache entries"""
        if not self.enabled:
            return False
        
        try:
            # Clear all cache patterns
            patterns = ["search_results:*", "paper_details:*", "session:*"]
            total_cleared = 0
            
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    total_cleared += deleted
            
            self.logger.info(f"Cleared {total_cleared} total cache entries")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear all cache: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        if not self.enabled:
            return {"enabled": False, "message": "Redis not available"}
        
        try:
            info = self.redis_client.info()
            
            # Get counts for different cache types
            search_keys = len(self.redis_client.keys("search_results:*"))
            paper_keys = len(self.redis_client.keys("paper_details:*"))
            session_keys = len(self.redis_client.keys("session:*"))
            
            return {
                "enabled": True,
                "connected_clients": info.get('connected_clients', 0),
                "used_memory": info.get('used_memory_human', 'N/A'),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "hit_rate": round(
                    info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)) * 100, 2
                ),
                "cache_counts": {
                    "search_results": search_keys,
                    "paper_details": paper_keys,
                    "active_sessions": session_keys,
                    "total_entries": search_keys + paper_keys + session_keys
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {"enabled": False, "error": str(e)}

    def cache_paper_details(self, paper: Dict[str, Any], analysis: Dict[str, Any], session_id: str = None) -> bool:
        """Cache paper analysis results"""
        if not self.enabled:
            return False
        
        try:
            # Check if paper is None or not a dictionary
            if not paper or not isinstance(paper, dict):
                self.logger.warning("Cannot cache paper details: paper is None or not a dictionary")
                return False
                
            # Generate cache key from paper title and authors
            title = paper.get('title', 'unknown')
            authors = paper.get('authors', [])
            author_str = '|'.join([str(auth) for auth in authors[:3] if auth])
            
            cache_key = self._generate_cache_key("paper_details", title, author_str)
            
            cache_data = {
                'paper': paper,
                'analysis': analysis,
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': session_id
            }
            
            serialized_data = self._serialize_data(cache_data)
            success = self.redis_client.setex(cache_key, self.PAPER_DETAILS_TTL, serialized_data)
            
            if success:
                self.logger.info(f"Cached paper analysis: {title[:50]}...")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cache paper details: {e}")
        
        return False

    def get_cached_paper_details(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached paper analysis if available"""
        if not self.enabled:
            return None
        
        try:
            # Check if paper is None or not a dictionary
            if not paper or not isinstance(paper, dict):
                self.logger.warning("Cannot get cached paper details: paper is None or not a dictionary")
                return None
                
            # Generate same cache key as used for caching
            title = paper.get('title', 'unknown')
            authors = paper.get('authors', [])
            author_str = '|'.join([str(auth) for auth in authors[:3] if auth])
            
            cache_key = self._generate_cache_key("paper_details", title, author_str)
            
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                data = self._deserialize_data(cached_data)
                self.logger.info(f"Retrieved cached paper analysis: {title[:50]}...")
                return data
                
        except Exception as e:
            self.logger.error(f"Failed to get cached paper details: {e}")
        
        return None

    # User-specific search history methods for Firebase authentication
    def save_user_search_to_history(self, user_id: str, query: str, results_count: int, sources: List[str]) -> bool:
        """Save search query to user's personal history"""
        if not self.enabled or not user_id:
            return False
        
        try:
            history_key = f"user_history:{user_id}"
            
            search_entry = {
                "query": query,
                "timestamp": datetime.utcnow().isoformat(),
                "results_count": results_count,
                "sources": sources,
                "search_id": str(uuid.uuid4())
            }
            
            # Get existing history (limit to last 100 searches per user)
            existing_history = []
            try:
                history_data = self.redis_client.get(history_key)
                if history_data:
                    existing_history = self._deserialize_data(history_data)
            except:
                existing_history = []
            
            # Add new search to beginning
            existing_history.insert(0, search_entry)
            
            # Keep only last 100 searches per user
            existing_history = existing_history[:100]
            
            # Save back to Redis (expire in 90 days for registered users)
            serialized_history = self._serialize_data(existing_history)
            self.redis_client.setex(history_key, 90 * 24 * 3600, serialized_history)  # 90 days
            
            self.logger.info(f"Saved search to user history: {query[:50]}... for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save user search history: {e}")
            return False

    def get_user_search_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's personal search history"""
        if not self.enabled or not user_id:
            return []
        
        try:
            history_key = f"user_history:{user_id}"
            history_data = self.redis_client.get(history_key)
            
            if history_data:
                history = self._deserialize_data(history_data)
                return history[:limit]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get user search history: {e}")
            return []

    def clear_user_search_history(self, user_id: str) -> bool:
        """Clear all search history for a user"""
        if not self.enabled or not user_id:
            return False
        
        try:
            history_key = f"user_history:{user_id}"
            self.redis_client.delete(history_key)
            self.logger.info(f"Cleared search history for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear user search history: {e}")
            return False

    def delete_search_from_user_history(self, user_id: str, search_id: str) -> bool:
        """Delete specific search from user history"""
        if not self.enabled or not user_id:
            return False
        
        try:
            history_key = f"user_history:{user_id}"
            history_data = self.redis_client.get(history_key)
            
            if history_data:
                history = self._deserialize_data(history_data)
                # Remove search with matching search_id
                original_count = len(history)
                history = [search for search in history if search.get('search_id') != search_id]
                
                if len(history) < original_count:
                    # Save updated history
                    serialized_history = self._serialize_data(history)
                    self.redis_client.setex(history_key, 90 * 24 * 3600, serialized_history)
                    
                    self.logger.info(f"Deleted search from user history: {search_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete search from user history: {e}")
            return False

    def save_search_to_history(self, session_id: str, query: str, results_count: int, sources: List[str]) -> bool:
        """Save search query to session-based search history (for anonymous users)"""
        if not self.enabled or not session_id:
            return False
        
        try:
            history_key = f"session_search_history:{session_id}"
            search_id = hashlib.md5(f"{query}:{int(time.time())}".encode()).hexdigest()[:12]
            
            # Get existing history
            existing_history = self.redis_client.get(history_key)
            history = []
            
            if existing_history:
                try:
                    history = self._deserialize_data(existing_history)
                    if not isinstance(history, list):
                        history = []
                except:
                    history = []
            
            # Create search entry
            search_entry = {
                'search_id': search_id,
                'query': query,
                'results_count': results_count,
                'sources': sources,
                'timestamp': datetime.utcnow().isoformat(),
                'session_id': session_id
            }
            
            # Add to beginning of history
            history.insert(0, search_entry)
            
            # Keep only last 20 searches for session history
            history = history[:20]
            
            # Save back to Redis with 30 minutes TTL (shorter than user history)
            serialized_history = self._serialize_data(history)
            self.redis_client.setex(history_key, 30 * 60, serialized_history)  # 30 minutes
            
            self.logger.info(f"Saved search to session history for session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save search to session history: {e}")
            return False

    def get_session_search_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get session-based search history (for anonymous users)"""
        if not self.enabled or not session_id:
            return []
        
        try:
            history_key = f"session_search_history:{session_id}"
            cached_history = self.redis_client.get(history_key)
            
            if cached_history:
                history = self._deserialize_data(cached_history)
                if isinstance(history, list):
                    return history[:limit]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get session search history: {e}")
            return []

    def clear_session_search_history(self, session_id: str) -> bool:
        """Clear session-based search history (for anonymous users)"""
        if not self.enabled or not session_id:
            return False
        
        try:
            history_key = f"session_search_history:{session_id}"
            self.redis_client.delete(history_key)
            self.logger.info(f"Cleared session search history for session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear session search history: {e}")
            return False

    # 📑 BOOKMARK FUNCTIONALITY
    def save_paper_bookmark(self, user_id: str, paper: Dict[str, Any], session_id: str = None) -> bool:
        """Save a paper to user's bookmarks"""
        if not self.enabled:
            return False
        
        try:
            # Generate unique paper ID using consistent method
            paper_id = generate_paper_id(paper)
            
            # Choose bookmark key based on authentication
            if user_id:
                bookmark_key = f"bookmarks:user:{user_id}"
            elif session_id:
                bookmark_key = f"bookmarks:session:{session_id}"
            else:
                return False
            
            # Save paper details for retrieval
            paper_details_key = f"paper_details:{paper_id}"
            paper_data = {
                **paper,
                'bookmarked_at': datetime.now().isoformat(),
                'paper_id': paper_id
            }
            
            # Add to bookmark set and save paper details
            self.redis_client.sadd(bookmark_key, paper_id)
            self.redis_client.setex(paper_details_key, 2592000, self._serialize_data(paper_data))  # 30 days
            
            # Set bookmark collection expiry
            self.redis_client.expire(bookmark_key, 2592000)  # 30 days
            
            self.logger.info(f"Bookmarked paper: {paper.get('title', 'Unknown')[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save bookmark: {e}")
            return False
    
    def remove_paper_bookmark(self, user_id: str, paper_id: str, session_id: str = None) -> bool:
        """Remove a paper from user's bookmarks"""
        if not self.enabled:
            return False
        
        try:
            # Choose bookmark key based on authentication
            if user_id:
                bookmark_key = f"bookmarks:user:{user_id}"
            elif session_id:
                bookmark_key = f"bookmarks:session:{session_id}"
            else:
                return False
            
            # Remove from bookmark set
            result = self.redis_client.srem(bookmark_key, paper_id)
            self.logger.info(f"Removed bookmark: {paper_id}")
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Failed to remove bookmark: {e}")
            return False
    
    def get_user_bookmarks(self, user_id: str, session_id: str = None) -> List[Dict[str, Any]]:
        """Get all bookmarked papers for a user"""
        if not self.enabled:
            return []
        
        try:
            # Choose bookmark key based on authentication
            if user_id:
                bookmark_key = f"bookmarks:user:{user_id}"
            elif session_id:
                bookmark_key = f"bookmarks:session:{session_id}"
            else:
                return []
            
            # Get all paper IDs in bookmark set
            paper_ids = self.redis_client.smembers(bookmark_key)
            bookmarks = []
            
            for paper_id in paper_ids:
                paper_details_key = f"paper_details:{paper_id.decode() if isinstance(paper_id, bytes) else paper_id}"
                cached_paper = self.redis_client.get(paper_details_key)
                
                if cached_paper:
                    paper_data = self._deserialize_data(cached_paper)
                    bookmarks.append(paper_data)
            
            # Sort by bookmark date (newest first)
            bookmarks.sort(key=lambda x: x.get('bookmarked_at', ''), reverse=True)
            self.logger.info(f"Retrieved {len(bookmarks)} bookmarks")
            return bookmarks
            
        except Exception as e:
            self.logger.error(f"Failed to get bookmarks: {e}")
            return []
    
    def is_paper_bookmarked(self, user_id: str, paper_id: str, session_id: str = None) -> bool:
        """Check if a paper is bookmarked by user"""
        if not self.enabled:
            return False
        
        try:
            # Choose bookmark key based on authentication
            if user_id:
                bookmark_key = f"bookmarks:user:{user_id}"
            elif session_id:
                bookmark_key = f"bookmarks:session:{session_id}"
            else:
                return False
            
            return self.redis_client.sismember(bookmark_key, paper_id)
            
        except Exception as e:
            self.logger.error(f"Failed to check bookmark status: {e}")
            return False


# Initialize cache manager
cache_manager = RedisCacheManager(redis_client)

# 📑 BOOKMARK UTILITY FUNCTIONS
def generate_paper_id(paper: Dict[str, Any]) -> str:
    """Generate a consistent unique ID for a paper"""
    # Use URL as primary identifier, fallback to title+authors
    if paper.get('url'):
        return hashlib.md5(paper['url'].encode()).hexdigest()[:12]
    elif paper.get('id'):
        return hashlib.md5(str(paper['id']).encode()).hexdigest()[:12]
    else:
        # Create ID from title and first author
        title = paper.get('title', 'unknown')[:100]
        authors = paper.get('authors', [])
        first_author = authors[0] if isinstance(authors, list) and authors else 'unknown'
        
        id_string = f"{title}_{first_author}".replace(' ', '_').replace(':', '_')
        return hashlib.md5(id_string.encode()).hexdigest()[:12]


class ResearchFocusExtractor:
    """Extract research focus and keywords from text using AI analysis"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.logger = logger
    
    def extract_research_focus(self, text: str) -> Dict[str, Any]:
        """Extract key research topics and keywords using AI"""
        try:
            # Validate input
            if not text or not isinstance(text, str):
                text = "research analysis"
            
            if not self.openai_client:
                return self._fallback_extraction(text)
            
            # Truncate text to avoid token limits
            text_sample = text[:2000] if len(text) > 2000 else text
            
            prompt = f"""
            Analyze this research text and extract key information for finding relevant academic papers.
            
            Text: {text_sample}
            
            Please provide a JSON response with exactly these keys:
            {{
                "topic": "Main research topic (one sentence)",
                "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
                "domain": "Research field/domain",
                "methodologies": ["method1", "method2"],
                "audience": "graduate"
            }}
            
            Respond only with valid JSON, no additional text.
            """
            
            response = self.openai_client.invoke(prompt)
            
            # Parse JSON response with better error handling
            try:
                if hasattr(response, 'content'):
                    content = str(response.content).strip()
                else:
                    content = str(response).strip()
                    
                result = json.loads(content)
                return self._validate_extraction_result(result)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse OpenAI JSON response: {e}, using fallback")
                return self._fallback_extraction(text)
                
        except Exception as e:
            self.logger.error(f"Research focus extraction failed: {e}")
            return self._fallback_extraction(text)
    
    def _validate_extraction_result(self, result: Dict) -> Dict[str, Any]:
        """Validate and clean extraction result"""
        return {
            "topic": str(result.get("topic", "Research Topic"))[:200],
            "keywords": [str(kw)[:50] for kw in result.get("keywords", [])[:10]],
            "domain": str(result.get("domain", "Computer Science"))[:100],
            "methodologies": [str(m)[:50] for m in result.get("methodologies", [])[:5]],
            "audience": str(result.get("audience", "graduate"))[:20]
        }
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback method when AI is not available"""
        # Extract potential keywords using simple heuristics
        keywords = self._extract_keywords_heuristic(text)
        topic = self._extract_topic_heuristic(text)
        
        return {
            "topic": topic,
            "keywords": keywords,
            "domain": "Computer Science",
            "methodologies": ["analysis", "research"],
            "audience": "graduate"
        }
    
    def _extract_keywords_heuristic(self, text: str) -> List[str]:
        """Extract keywords using simple heuristics"""
        common_academic_terms = [
            "machine learning", "artificial intelligence", "deep learning",
            "neural networks", "data analysis", "algorithm", "optimization",
            "classification", "regression", "clustering", "natural language processing",
            "computer vision", "statistics", "modeling", "prediction"
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for term in common_academic_terms:
            if term in text_lower:
                found_keywords.append(term)
        
        return found_keywords[:8] if found_keywords else ["artificial intelligence", "research"]
    
    def _extract_topic_heuristic(self, text: str) -> str:
        """Extract topic using simple patterns"""
        patterns = [
            r'research on (.+?)(?:\.|,|;|\n)',
            r'study of (.+?)(?:\.|,|;|\n)',
            r'analysis of (.+?)(?:\.|,|;|\n)',
            r'investigation into (.+?)(?:\.|,|;|\n)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:200]
        
        return "Academic Research Topic"



class OpenAlexSearcher:
    """Search OpenAlex for academic papers - better alternative with higher rate limits"""
    
    def __init__(self):
        self.base_url = "https://api.openalex.org/works"
        self.logger = logger
        self.session = requests.Session()
        
        # Add polite headers (OpenAlex requests this)
        self.session.headers.update({
            'User-Agent': 'Academic Paper Discovery Engine (mailto:research@academicpapers.com)',
            'Accept': 'application/json'
        })
    
    def search(self, query_params: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search OpenAlex using optimized query parameters
        
        Args:
            query_params: URL-ready query string from intent extraction OR plain query text
            max_results: Maximum number of results to return
        """
        try:
            self.logger.info(f"🔍 OpenAlex search input: {query_params[:100]}...")
            
            # Build the complete API URL
            search_url = self.build_search_url(query_params, limit=max_results)
            
            response = self.session.get(search_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                self.logger.info(f"✅ OpenAlex found {len(results)} papers")
                
                # Convert OpenAlex format to our standard format
                papers = []
                for work in results:
                    paper = self._convert_openalex_work(work)
                    if paper:
                        papers.append(paper)
                
                return papers
            else:
                self.logger.error(f"OpenAlex API error: {response.status_code} - {response.text[:200]}")
                return []
                
        except Exception as e:
            self.logger.error(f"OpenAlex search failed: {e}")
            return []
    
    def build_search_url(self, query_params: str, limit: int = 10) -> str:
        """
        Build OpenAlex API URL from query parameters
        
        Args:
            query_params: URL-encoded query string from intent extraction
            limit: Number of results
        """
        # Parse existing query params
        params_dict = urllib.parse.parse_qs(query_params) if '=' in query_params else {}
        
        # Extract query from params or use entire string as query
        if 'search' in params_dict:
            search_query = params_dict['search'][0]
        elif 'query' in params_dict:
            search_query = params_dict['query'][0]
        else:
            search_query = query_params
        
        # Build OpenAlex parameters
        params = {
            'search': search_query,
            'per-page': min(limit, 200),  # OpenAlex max per page
            'sort': 'relevance_score:desc',
            'filter': 'type:article',  # Only research articles
            'select': 'id,title,display_name,publication_year,publication_date,doi,open_access,authorships,abstract_inverted_index,concepts,cited_by_count,is_retracted,language,primary_location,locations'
        }
        
        url = f"{self.base_url}?" + urllib.parse.urlencode(params)
        self.logger.info(f"🔍 OpenAlex URL: {url}")
        return url
    
    def _convert_openalex_work(self, work: Dict) -> Optional[Dict[str, Any]]:
        """Convert OpenAlex work format to our standard paper format"""
        try:
            # Extract basic info
            paper_id = work.get('id', '').split('/')[-1] if work.get('id') else str(uuid.uuid4())
            title = work.get('display_name', 'Unknown Title')
            
            # Extract authors
            authors = []
            for authorship in work.get('authorships', []):
                author = authorship.get('author', {})
                author_name = author.get('display_name')
                if author_name:
                    authors.append(author_name)
            
            # Extract abstract from inverted index
            abstract = self._reconstruct_abstract(work.get('abstract_inverted_index', {}))
            
            # Extract publication info
            pub_year = work.get('publication_year')
            pub_date = work.get('publication_date', '')
            
            # Extract URL and DOI
            doi = work.get('doi')
            url = work.get('id', '')  # OpenAlex ID as URL
            
            # Primary location (journal/venue info)
            primary_location = work.get('primary_location', {})
            source_name = primary_location.get('source', {}).get('display_name', 'Unknown Source')
            
            # PDF access
            pdf_url = ''
            open_access = work.get('open_access', {})
            if open_access.get('is_oa'):
                # Look for PDF in locations
                for location in work.get('locations', []):
                    if location.get('pdf_url'):
                        pdf_url = location['pdf_url']
                        break
                
                # Fallback to DOI URL if no direct PDF
                if not pdf_url and doi:
                    pdf_url = f"https://doi.org/{doi}"
            
            # Citation count
            citation_count = work.get('cited_by_count', 0)
            
            # Extract concepts (research topics)
            concepts = []
            for concept in work.get('concepts', [])[:5]:  # Top 5 concepts
                concept_name = concept.get('display_name')
                if concept_name:
                    concepts.append(concept_name)
            
            return {
                "id": paper_id,
                "title": title,
                "authors": authors,
                "summary": abstract,
                "url": url,
                "pdf_url": pdf_url,
                "published": pub_date or str(pub_year) if pub_year else '',
                "citation_count": citation_count,
                "journal": source_name,
                "source": "OpenAlex",
                "concepts": concepts,
                "is_open_access": open_access.get('is_oa', False),
                "doi": doi,
                "language": work.get('language', 'en')
            }
            
        except Exception as e:
            self.logger.warning(f"Error converting OpenAlex work: {e}")
            return None
    
    def _reconstruct_abstract(self, inverted_index: Dict) -> str:
        """Reconstruct abstract from OpenAlex inverted index format"""
        if not inverted_index:
            return "No abstract available"
        
        try:
            # Create word-position pairs
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and reconstruct
            word_positions.sort(key=lambda x: x[0])
            abstract_words = [word for pos, word in word_positions]
            
            # Join words and clean up
            abstract = ' '.join(abstract_words)
            
            # Limit length
            if len(abstract) > 500:
                abstract = abstract[:500] + "..."
            
            return abstract
            
        except Exception as e:
            self.logger.warning(f"Error reconstructing abstract: {e}")
            return "Abstract processing error"


class RelevanceScorer:
    """Score paper relevance using AI analysis"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.logger = logger
    
    def calculate_relevance_score(self, paper: Dict[str, Any], research_focus: Dict[str, Any]) -> float:
        """Calculate relevance score using AI analysis"""
        try:
            # Validate inputs
            if not paper or not research_focus:
                return 25.0
            
            if not self.openai_client:
                return self._heuristic_scoring(paper, research_focus)
            
            # Safe string formatting with defaults
            topic = research_focus.get('topic', 'Unknown topic')
            keywords = research_focus.get('keywords', [])
            domain = research_focus.get('domain', 'Unknown domain')
            
            title = paper.get('title', 'Unknown title')
            summary = paper.get('summary', 'No summary available')
            authors = paper.get('authors', [])
            
            # Ensure all values are strings
            keywords_str = ', '.join([str(kw) for kw in keywords if kw])
            authors_str = ', '.join([str(auth) for auth in authors[:3] if auth])
            
            prompt = f"""
            Rate the relevance of this academic paper to the research focus on a scale of 0-100.
            
            Research Focus:
            - Topic: {topic}
            - Keywords: {keywords_str}
            - Domain: {domain}
            
            Paper:
            - Title: {title}
            - Summary: {str(summary)[:400]}
            - Authors: {authors_str}
            
            Consider:
            1. Topic alignment (40 points)
            2. Keyword matches (30 points)  
            3. Methodological relevance (20 points)
            4. Recency and impact (10 points)
            
            Respond with only a number between 0-100.
            """
            
            response = self.openai_client.invoke(prompt)
            
            # Extract score from response
            if hasattr(response, 'content'):
                score_text = str(response.content).strip()
            else:
                score_text = str(response).strip()
                
            try:
                score_match = re.search(r'\d+\.?\d*', score_text)
                if score_match:
                    score = float(score_match.group())
                    return min(100, max(0, score))
                else:
                    return self._heuristic_scoring(paper, research_focus)
            except:
                return self._heuristic_scoring(paper, research_focus)
                
        except Exception as e:
            self.logger.error(f"Relevance scoring failed: {e}")
            return self._heuristic_scoring(paper, research_focus)
    
    def _heuristic_scoring(self, paper: Dict[str, Any], research_focus: Dict[str, Any]) -> float:
        """Fallback heuristic scoring when AI is not available"""
        try:
            score = 50.0  # Base score
            
            # Safe string handling with None checks
            title = str(paper.get('title', '')).lower() if paper.get('title') else ''
            summary = str(paper.get('summary', '')).lower() if paper.get('summary') else ''
            
            # Safe keyword processing
            raw_keywords = research_focus.get('keywords', []) if research_focus else []
            keywords = [str(kw).lower() for kw in raw_keywords if kw is not None and str(kw).strip()]
            
            # Keyword matching in title (high weight)
            title_matches = sum(1 for kw in keywords if kw and kw in title)
            score += title_matches * 15
            
            # Keyword matching in summary (medium weight)
            summary_matches = sum(1 for kw in keywords if kw and kw in summary)
            score += summary_matches * 5
            
            # Citation count bonus (if available)
            try:
                citation_count = int(paper.get('citation_count', 0))
                if citation_count > 100:
                    score += 10
                elif citation_count > 50:
                    score += 5
            except (ValueError, TypeError):
                pass  # Ignore invalid citation counts
            
            return min(100, max(0, score))
            
        except Exception as e:
            self.logger.error(f"Heuristic scoring failed: {e}")
            return 50.0  # Safe fallback


class DuplicateRemover:
    """Remove duplicate papers based on title similarity"""
    
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.logger = logger
    
    def remove_duplicates(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers based on title similarity"""
        if not papers:
            return papers
        
        unique_papers = []
        seen_titles = []
        
        for paper in papers:
            if not paper or not isinstance(paper, dict):
                continue
                
            title = paper.get('title')
            if not title:
                continue
                
            title = str(title).lower().strip()
            if not title:
                continue
                
            is_duplicate = False
            
            for seen_title in seen_titles:
                try:
                    similarity = fuzz.ratio(title, seen_title) / 100.0
                    if similarity >= self.threshold:
                        is_duplicate = True
                        # Keep the one with higher citation count or more complete info
                        existing_index = seen_titles.index(seen_title)
                        if self._is_better_paper(paper, unique_papers[existing_index]):
                            unique_papers[existing_index] = paper
                        break
                except Exception as e:
                    self.logger.warning(f"Error comparing titles: {e}")
                    continue
            
            if not is_duplicate:
                unique_papers.append(paper)
                seen_titles.append(title)
        
        self.logger.info(f"Removed {len(papers) - len(unique_papers)} duplicate papers")
        return unique_papers
    
    def _is_better_paper(self, paper1: Dict, paper2: Dict) -> bool:
        """Determine which paper is better (more complete/authoritative)"""
        # Prefer papers with citation counts
        citations1 = paper1.get('citation_count', 0)
        citations2 = paper2.get('citation_count', 0)
        
        if citations1 != citations2:
            return citations1 > citations2
        
        # Prefer papers with more complete summaries
        summary1_len = len(paper1.get('summary', ''))
        summary2_len = len(paper2.get('summary', ''))
        
        return summary1_len > summary2_len


class PDFAnalyzer:
    """Analyze PDF files to extract research content"""
    
    def __init__(self, research_extractor: ResearchFocusExtractor):
        self.research_extractor = research_extractor
        self.logger = logger
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            # Extract text from all pages
            for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages
                page = doc.load_page(page_num)
                text += page.get_text()
            
            doc.close()
            return text
            
        except Exception as e:
            self.logger.error(f"PDF text extraction failed: {e}")
            return ""
    
    def analyze_research_paper(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze uploaded research paper"""
        try:
            text = self.extract_text_from_pdf(pdf_path)
            
            if not text or len(text) < 100:
                return {"success": False, "error": "Could not extract meaningful text from PDF"}
            
            # Extract research focus
            research_focus = self.research_extractor.extract_research_focus(text)
            
            return {
                "success": True,
                "research_focus": research_focus,
                "text_length": len(text),
                "extracted_sample": text[:500] + "..." if len(text) > 500 else text
            }
            
        except Exception as e:
            self.logger.error(f"PDF analysis failed: {e}")
            return {"success": False, "error": str(e)}


class AcademicPaperDiscoveryEngine:
    """Main engine for discovering academic papers"""
    
    def __init__(self):
        self.logger = logger
        self.openai_client = openai_client  # Store OpenAI client as instance variable
        
        # Initialize traditional components
        self.research_extractor = ResearchFocusExtractor(openai_client)
        self.openalex_searcher = OpenAlexSearcher()  # Using only OpenAlex
        self.relevance_scorer = RelevanceScorer(openai_client)
        self.duplicate_remover = DuplicateRemover(config.DUPLICATE_THRESHOLD)
        self.pdf_analyzer = PDFAnalyzer(self.research_extractor)
        
        # 🧠 RAG Components
        self.vector_db = VectorDatabase()
        self.rag_pipeline = RAGPipelineManager(openai_client, self.vector_db)
        
        # 🔗 Simple Paper Relationships Component
        self.citation_extractor = CitationDataExtractor(rate_limit_delay=0.1)
        self.paper_relationships = SimplePaperRelationships(self.citation_extractor)
        
        self.logger.info("Academic Paper Discovery Engine initialized with RAG and Citation Network capabilities")
    
    def extract_search_intent(self, research_input: str) -> Dict[str, Any]:
        """Extract search intent and optimize queries for different academic databases"""
        try:
            if not self.openai_client:
                # Fallback if OpenAI is not available
                return {
                    "openalex_query": research_input.strip(),
                    "openalex_url_params": f"search={urllib.parse.quote(research_input.strip())}",
                    "primary_keywords": research_input.split()[:5],
                    "research_domain": "Computer Science",
                    "intent_confidence": 0.5
                }
            
            prompt = f"""You are an expert academic search query optimizer. Analyze the user's research question and create optimized search parameters for OpenAlex academic database.

    User's Research Question: "{research_input}"

    Generate the following optimized search parameters:

    1. OPENALEX_QUERY: Natural language query for OpenAlex (preserve meaning, works excellently with full questions and natural language)
    2. OPENALEX_URL_PARAMS: URL-encoded search string ready for OpenAlex API (natural language friendly, focus on key concepts)
    3. PRIMARY_KEYWORDS: 3-5 most important technical keywords/phrases for relevance scoring
    4. RESEARCH_DOMAIN: Specific academic field (e.g., "Computer Science - AI", "Software Engineering", "Machine Learning")
    5. INTENT_CONFIDENCE: Confidence level (0.1-1.0) in understanding the research intent

    CRITICAL GUIDELINES for OpenAlex queries:
    - OpenAlex works VERY well with natural language queries
    - You can keep question words and natural phrasing - OpenAlex understands context
    - Focus on preserving the research intent and context
    - Remove only unnecessary filler words and conversational phrases
    - OpenAlex understands concepts and relationships extremely well
    - Natural language is preferred over just keywords

    Examples:
    - Input: "How do AI code assistants affect software maintainability?"
    - OpenAlex: "AI code assistants software maintainability impact programming development"
    - Input: "What are the latest advances in quantum computing?"
    - OpenAlex: "latest advances quantum computing recent developments breakthrough"
    - Input: "How does machine learning improve medical diagnosis?"
    - OpenAlex: "machine learning medical diagnosis improvement accuracy healthcare"

    Respond in JSON format:
    {{
        "openalex_query": "natural language research query", 
        "openalex_url_params": "search_ready_query_string",
        "primary_keywords": ["keyword1", "keyword2", "keyword3"],
        "research_domain": "Specific Academic Field",
        "intent_confidence": 0.8
    }}"""            # Use LangChain's ChatOpenAI invoke method
            response = self.openai_client.invoke(prompt)
            
            # LangChain returns the content directly
            result = json.loads(response.content.strip())
            # Validate and enhance the result
            required_keys = ['openalex_query', 'openalex_url_params', 'primary_keywords', 'research_domain', 'intent_confidence']
            if all(key in result for key in required_keys):
                # Ensure URL params are properly formatted for OpenAlex
                if not result['openalex_url_params'].startswith('search='):
                    result['openalex_url_params'] = f"search={result['openalex_url_params']}"
                
                self.logger.info(f"Successfully extracted search intent: {result['research_domain']}")
                return result
            else:
                raise ValueError("Missing required keys in OpenAI response")
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse OpenAI JSON response, using fallback: {e}")
            return self._fallback_intent_extraction_openalex(research_input)
        except AttributeError as e:
            self.logger.warning(f"OpenAI client method error, using fallback: {e}")
            return self._fallback_intent_extraction_openalex(research_input)
        except Exception as e:
            self.logger.warning(f"Intent extraction failed, using fallback: {e}")
            return self._fallback_intent_extraction_openalex(research_input)

    def _fallback_intent_extraction_openalex(self, research_input: str) -> Dict[str, Any]:
        """Fallback method for intent extraction when OpenAI fails - OpenAlex version"""
        import urllib.parse
        
        # Clean the query for URL parameters
        words = research_input.lower().split()
        stop_words = ['how', 'what', 'why', 'when', 'where', 'can', 'does', 'is', 'are', 
                    'the', 'a', 'an', 'i', 'you', 'we', 'they', 'me', 'my', 'your',
                    'want', 'find', 'look', 'search', 'paper', 'papers', 'research']
        
        keywords = [w for w in words if w not in stop_words and len(w) > 2][:6]
        url_query = ' '.join(keywords)
        
        return {
            "openalex_query": research_input.strip(),
            "openalex_url_params": f"search={urllib.parse.quote(url_query)}",
            "primary_keywords": keywords,
            "research_domain": "Computer Science",
            "intent_confidence": 0.3
        }

    def _extract_openalex_work_ids(self, papers: List[Dict]) -> None:
        """Extract OpenAlex work IDs for all papers and add them to the paper dictionary"""
        try:
            import re
            
            for paper in papers:
                if not paper or not isinstance(paper, dict):
                    continue
                
                work_id = None
                
                # Method 1: Check if paper already has an OpenAlex ID
                if paper.get('id') and isinstance(paper['id'], str):
                    if paper['id'].startswith('https://openalex.org/W'):
                        work_id = paper['id'].split('/')[-1]  # Extract W123456789
                    elif paper['id'].startswith('W') and len(paper['id']) > 1:
                        work_id = paper['id']
                
                # Method 2: Check URL field for OpenAlex URLs
                if not work_id and paper.get('url') and isinstance(paper['url'], str):
                    if 'openalex.org/W' in paper['url']:
                        match = re.search(r'openalex\.org/(W\d+)', paper['url'])
                        if match:
                            work_id = match.group(1)
                
                # Method 3: Check source and extract from paper_id
                if not work_id and paper.get('source') == 'openalex' and paper.get('paper_id'):
                    paper_id = str(paper['paper_id'])
                    if paper_id.startswith('W') and len(paper_id) > 1:
                        work_id = paper_id
                    elif paper_id.startswith('https://openalex.org/W'):
                        work_id = paper_id.split('/')[-1]
                
                # Method 4: Try to extract from DOI using OpenAlex API (if we have a DOI)
                if not work_id and paper.get('doi'):
                    try:
                        doi = paper['doi'].replace('https://doi.org/', '').replace('doi:', '').strip()
                        # Format for potential OpenAlex lookup
                        openalex_doi_url = f"https://doi.org/{doi}"
                        
                        # Try to make a quick API call to get OpenAlex work ID
                        response = requests.get(
                            f"https://api.openalex.org/works/{openalex_doi_url}",
                            timeout=5
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('id'):
                                work_id = data['id'].split('/')[-1]
                        
                        # Small delay to respect rate limits
                        time.sleep(0.1)
                    except Exception as e:
                        self.logger.debug(f"Could not fetch OpenAlex ID for DOI {paper.get('doi')}: {e}")
                
                # Add the work_id to the paper
                if work_id:
                    paper['openalex_work_id'] = work_id
                    paper['paper_id'] = work_id  # Also set paper_id for compatibility
                    self.logger.debug(f"Found OpenAlex work ID: {work_id} for paper: {paper.get('title', 'Unknown')[:50]}")
                else:
                    paper['openalex_work_id'] = None  # Keep as None for logic, but handle in formatting
                    self.logger.debug(f"No OpenAlex work ID found for paper: {paper.get('title', 'Unknown')[:50]}")
            
            # Print summary of OpenAlex work IDs found
            papers_with_ids = [p for p in papers if p.get('openalex_work_id')]
            self.logger.info(f"📊 OpenAlex Work IDs: Found {len(papers_with_ids)}/{len(papers)} papers with work IDs")
            
            # Print the discovered work IDs
            if papers_with_ids:
                print(f"\n📋 OPENALEX WORK IDs DISCOVERED ({len(papers_with_ids)}/{len(papers)}):")
                print("=" * 80)
                for i, paper in enumerate(papers_with_ids, 1):
                    work_id = paper.get('openalex_work_id') or 'Unknown'
                    title = (paper.get('title') or 'Unknown Title')[:60]
                    source = paper.get('source') or 'Unknown'
                    print(f"{i:2d}. {work_id} | {source:8s} | {title}")
                print("=" * 80)
            else:
                print("\n⚠️  No OpenAlex Work IDs found for any papers")
                
        except Exception as e:
            self.logger.error(f"Failed to extract OpenAlex work IDs: {e}")

    def discover_papers(self, research_input: str, sources: List[str] = None, 
                       max_results: int = 10) -> Dict[str, Any]:
        """Main method to discover relevant academic papers"""
        try:
            if sources is None:
                sources = ["openalex"]
            
            max_results = min(max_results, config.MAX_ALLOWED_RESULTS)
            
            self.logger.info(f"Starting paper discovery for query: {research_input[:100]}...")
            
            # Extract research focus for analysis and scoring
            research_focus = self.research_extractor.extract_research_focus(research_input)
            
            # ✨ NEW: Use AI-powered intent detection to optimize queries for each database
            search_intent = self.extract_search_intent(research_input)
            
            self.logger.info(f"Intent detection - Domain: {search_intent.get('research_domain', 'unknown')}")
            self.logger.info(f"Intent detection - Confidence: {search_intent.get('intent_confidence', 0)}")
            
            # Use optimized query for OpenAlex
            openalex_url_params = search_intent.get('openalex_url_params', f"search={urllib.parse.quote(research_input.strip())}")
            
            self.logger.info(f"OpenAlex URL params: {openalex_url_params}")
            
            # Search OpenAlex only
            all_papers = []
            with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
                futures = []
                
                if "openalex" in sources:
                    futures.append(executor.submit(self.openalex_searcher.search, openalex_url_params, max_results))
                
                # Collect results
                for future in as_completed(futures):
                    try:
                        papers = future.result()
                        if papers:
                            # Filter out None values and invalid papers
                            valid_papers = [p for p in papers if p and isinstance(p, dict) and p.get('title')]
                            all_papers.extend(valid_papers)
                    except Exception as e:
                        self.logger.error(f"Search source failed: {e}")
            
            # Remove duplicates
            unique_papers = self.duplicate_remover.remove_duplicates(all_papers)
            
            # Extract OpenAlex work IDs for all unique papers
            self._extract_openalex_work_ids(unique_papers)
            
            # Print summary of all unique papers with their OpenAlex work IDs
            print(f"\n📚 ALL UNIQUE PAPERS WITH OPENALEX IDs ({len(unique_papers)} total):")
            print("=" * 100)
            for i, paper in enumerate(unique_papers, 1):
                work_id = paper.get('openalex_work_id') or 'No Work ID'
                title = (paper.get('title') or 'Unknown Title')[:50]
                source = paper.get('source') or 'Unknown'
                authors = ', '.join(paper.get('authors', [])[:2]) or 'Unknown Authors'
                print(f"{i:2d}. [{work_id:12s}] {source:8s} | {title}")
                print(f"     Authors: {authors[:60]}")
                doi = paper.get('doi')
                if doi:
                    print(f"     DOI: {doi}")
                print()
            print("=" * 100)
            
            # Calculate relevance scores with enhanced context from AI intent detection
            for paper in unique_papers:
                try:
                    if paper and isinstance(paper, dict):
                        # Enhance research focus with intent data for better scoring
                        enhanced_research_focus = research_focus.copy()
                        if search_intent.get('primary_keywords'):
                            enhanced_research_focus['ai_keywords'] = search_intent['primary_keywords']
                        if search_intent.get('research_domain'):
                            enhanced_research_focus['ai_domain'] = search_intent['research_domain']
                        
                        paper['relevance_score'] = self.relevance_scorer.calculate_relevance_score(
                            paper, enhanced_research_focus
                        )
                    else:
                        self.logger.warning(f"Skipping invalid paper object: {type(paper)}")
                        if isinstance(paper, dict):
                            paper['relevance_score'] = 25.0  # Default score
                except Exception as e:
                    self.logger.warning(f"Failed to score paper: {e}")
                    if paper and isinstance(paper, dict):
                        paper['relevance_score'] = 25.0  # Default score
            
            # Sort by relevance score safely
            try:
                # Filter out any remaining None values before sorting
                unique_papers = [p for p in unique_papers if p and isinstance(p, dict)]
                unique_papers.sort(key=lambda x: float(x.get('relevance_score', 0)), reverse=True)
            except Exception as e:
                self.logger.warning(f"Failed to sort papers: {e}")
                # Keep original order if sorting fails
            
            # Limit final results
            final_papers = unique_papers[:max_results]
            
            # Add status information based on results
            status_info = {}
            if len(final_papers) == 0:
                if len(all_papers) == 0:
                    # Check if Google Scholar was requested and likely failed
                    google_scholar_requested = "google_scholar" in sources
                    
                    message = "No papers found. This could be due to API rate limits or service unavailability."
                    suggestions = [
                        "Try broader keywords",
                        "Check if your research area exists in academic databases",
                    ]
                    
                    if google_scholar_requested:
                        message += " Google Scholar has strict rate limiting and may block automated requests."
                        suggestions.extend([
                            "Try using only OpenAlex source",
                            "For Google Scholar results, search manually at scholar.google.com",
                            "Wait several minutes before trying Google Scholar again"
                        ])
                    else:
                        suggestions.append("Retry in a few minutes (APIs may be temporarily unavailable)")
                    
                    status_info = {
                        "status": "no_results",
                        "message": message,
                        "suggestions": suggestions
                    }
                else:
                    status_info = {
                        "status": "filtered_out",
                        "message": "Papers were found but filtered out during deduplication."
                    }
            else:
                status_info = {
                    "status": "success",
                    "message": f"Found {len(final_papers)} relevant papers"
                }

            result = {
                "success": len(final_papers) > 0,
                "research_focus": research_focus,
                "papers": final_papers,
                "total_found": len(all_papers),
                "unique_papers": len(unique_papers),
                "final_count": len(final_papers),
                "sources_searched": sources,
                "original_query": research_input,
                "ai_intent_detection": {
                    "openalex_url_params": openalex_url_params,
                    "research_domain": search_intent.get('research_domain', 'unknown'),
                    "intent_confidence": search_intent.get('intent_confidence', 0),
                    "primary_keywords": search_intent.get('primary_keywords', [])
                },
                "status_info": status_info
            }
            
            self.logger.info(f"Discovery completed: {len(final_papers)} papers returned")
            return result
            
        except Exception as e:
            self.logger.error(f"Paper discovery failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "papers": []
            }
    
    def discover_papers_with_rag(self, research_input: str, sources: List[str] = None, 
                               max_results: int = 10, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced paper discovery with RAG-powered recommendations"""
        try:
            self.logger.info(f"🧠 Starting RAG-enhanced discovery for: {research_input[:50]}...")
            
            # Step 1: Perform traditional search to gather papers
            traditional_results = self.discover_papers(research_input, sources, max_results * 2)
            
            if not traditional_results.get('success'):
                self.logger.warning("Traditional search failed, returning error")
                return traditional_results
            
            papers = traditional_results.get('papers', [])
            if not papers:
                self.logger.warning("No papers found from traditional search")
                return traditional_results
            
            self.logger.info(f"Traditional search found {len(papers)} papers")
            
            # Step 2: Index papers in vector database for semantic search
            indexed_count = self.vector_db.add_papers(papers)
            self.logger.info(f"Indexed {indexed_count} papers in vector database")
            
            # Step 3: Get RAG-enhanced recommendations
            rag_results = self.rag_pipeline.get_rag_recommendations(
                user_query=research_input,
                user_context=user_context,
                max_papers=max_results
            )
            
            if rag_results.get('success'):
                # Combine traditional results with RAG enhancements
                enhanced_result = {
                    **traditional_results,
                    'papers': rag_results['recommendations'],
                    'rag_insights': rag_results['rag_insights'],
                    'research_recommendations': rag_results['research_recommendations'],
                    'search_method': 'rag_enhanced',
                    'enhancement_stats': {
                        'vector_db_stats': self.vector_db.get_stats(),
                        'retrieval_stats': rag_results.get('retrieval_stats', {}),
                        'traditional_papers_count': len(papers),
                        'final_recommendations_count': len(rag_results['recommendations'])
                    }
                }
                
                self.logger.info(f"✅ RAG enhancement completed successfully")
                return enhanced_result
                
            else:
                # Fallback to traditional results if RAG fails
                self.logger.warning(f"RAG enhancement failed: {rag_results.get('error')}")
                traditional_results['search_method'] = 'traditional_fallback'
                traditional_results['rag_error'] = rag_results.get('error')
                return traditional_results
                
        except Exception as e:
            self.logger.error(f"RAG-enhanced discovery failed: {e}")
            # Fallback to traditional discovery
            fallback_result = self.discover_papers(research_input, sources, max_results)
            fallback_result['search_method'] = 'traditional_fallback'
            fallback_result['rag_error'] = str(e)
            return fallback_result
    
    def analyze_uploaded_paper(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze uploaded paper and find similar research"""
        return self.pdf_analyzer.analyze_research_paper(pdf_path)


# Initialize the discovery engine
discovery_engine = AcademicPaperDiscoveryEngine()


# API Routes
@app.route('/health', methods=['GET'])
def health_check_simple():
    """Simple health check endpoint for Render"""
    return jsonify({"status": "healthy"}), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Academic Paper Discovery Engine",
        "timestamp": datetime.now().isoformat(),
        "openai_available": openai_client is not None
    })


@app.route('/api/discover-papers', methods=['POST'])
@firebase_auth_optional
def discover_papers_endpoint():
    """API endpoint to discover relevant academic papers"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        research_input = data.get('query', '').strip()
        if not research_input:
            return jsonify({"success": False, "error": "Query is required"}), 400
        
        sources = data.get('sources', ["openalex"])
        max_results = min(data.get('max_results', 10), config.MAX_ALLOWED_RESULTS)
        session_id = data.get('session_id')  # Get session_id from request body
        
        logger.info(f"📝 Received discovery request: {research_input[:100]}...")
        logger.info(f"📋 Session ID: {session_id}")
        
        # 🔍 NEW: Check cache first before making API calls
        cached_result = cache_manager.get_cached_search_results(research_input, sources, max_results)
        if cached_result:
            logger.info(f"✅ Returning cached results for query: {research_input[:50]}...")
            cached_result["from_cache"] = True
            
            # 📑 Add bookmark status to cached papers
            user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
            session_id = request.headers.get('X-Session-ID')
            
            if cached_result.get('papers') and (user_id or session_id):
                for paper in cached_result['papers']:
                    # Generate paper ID for bookmark checking
                    paper_id = generate_paper_id(paper)
                    paper['paper_id'] = paper_id
                    paper['is_bookmarked'] = cache_manager.is_paper_bookmarked(user_id, paper_id, session_id)
            
            # Still save to user history if authenticated
            if hasattr(request, 'current_user') and request.current_user:
                cache_manager.save_user_search_to_history(
                    request.current_user['uid'],
                    research_input,
                    cached_result.get('final_count', 0),
                    sources
                )
            return jsonify(cached_result)
        
        # Call the discovery engine method
        result = discovery_engine.discover_papers(
            research_input=research_input,
            sources=sources,
            max_results=max_results
        )
        
        # 🔄 Cache the fresh results and mark as not from cache
        if result.get('success'):
            result["from_cache"] = False
            
            # 📑 Add bookmark status to each paper
            user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
            session_id = request.headers.get('X-Session-ID')
            
            if result.get('papers') and (user_id or session_id):
                for paper in result['papers']:
                    # Generate paper ID for bookmark checking
                    paper_id = generate_paper_id(paper)
                    paper['paper_id'] = paper_id
                    paper['is_bookmarked'] = cache_manager.is_paper_bookmarked(user_id, paper_id, session_id)
            
            # Cache the results for future requests
            try:
                # Use session_id for caching (fallback to user_id if session_id not provided)
                cache_id = session_id or user_id
                cache_manager.cache_search_results(research_input, sources, max_results, result, cache_id)
                logger.info(f"✅ Cached search results for query: {research_input[:50]}... (cache_id: {cache_id})")
            except Exception as e:
                logger.warning(f"Failed to cache search results: {e}")
        
        # Save search to history if user is authenticated and we have results
        if hasattr(request, 'current_user') and request.current_user and result.get('success'):
            try:
                cache_manager.save_user_search_to_history(
                    request.current_user['uid'],
                    research_input,
                    result.get('final_count', 0),
                    sources
                )
            except Exception as e:
                logger.warning(f"Failed to save search history: {e}")
        
        # 🐛 Debug: Log OpenAlex work IDs being sent to frontend
        if result.get('success') and result.get('papers'):
            work_ids_count = sum(1 for paper in result['papers'] if paper.get('openalex_work_id'))
            logger.info(f"📤 Sending {work_ids_count}/{len(result['papers'])} papers with OpenAlex work IDs to frontend")
            
            # Log a few work IDs for debugging
            for i, paper in enumerate(result['papers'][:3]):  # First 3 papers
                work_id = paper.get('openalex_work_id') or 'None'
                title = (paper.get('title') or 'Unknown')[:40]
                logger.debug(f"   Paper {i+1}: {work_id} | {title}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Discovery endpoint failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "papers": []
        }), 500


@app.route('/api/discover-papers-rag', methods=['POST'])
@firebase_auth_optional
def discover_papers_rag_endpoint():
    """🧠 RAG-enhanced paper discovery endpoint with personalized recommendations"""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        research_input = data.get('query', '').strip()
        if not research_input:
            return jsonify({"success": False, "error": "Query is required"}), 400
        
        sources = data.get('sources', ["openalex"])
        max_results = min(data.get('max_results', 10), config.MAX_ALLOWED_RESULTS)
        
        # Extract user context for personalization
        user_context = {
            'level': data.get('research_level', 'graduate'),
            'field': data.get('field_of_study', 'Computer Science'),
            'interests': data.get('research_interests', []),
            'recent_queries': data.get('recent_queries', [])
        }
        
        logger.info(f"🧠 RAG-enhanced discovery request: {research_input[:100]}...")
        
        # 🔍 Check cache first (same as traditional endpoint)
        cached_result = cache_manager.get_cached_search_results(research_input, sources, max_results)
        if cached_result and not data.get('force_refresh', False):
            logger.info(f"✅ Returning cached results for RAG query: {research_input[:50]}...")
            cached_result["from_cache"] = True
            cached_result["search_method"] = "cached_rag"
            
            # Add bookmark status to cached results
            user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
            session_id = request.headers.get('X-Session-ID')
            
            if cached_result.get('papers') and (user_id or session_id):
                for paper in cached_result['papers']:
                    paper_id = generate_paper_id(paper)
                    paper['paper_id'] = paper_id
                    paper['is_bookmarked'] = cache_manager.is_paper_bookmarked(user_id, paper_id, session_id)
            
            return jsonify(cached_result)
        
        # Call RAG-enhanced discovery engine
        result = discovery_engine.discover_papers_with_rag(
            research_input=research_input,
            sources=sources,
            max_results=max_results,
            user_context=user_context
        )
        
        # 🔄 Cache and enhance results
        if result.get('success'):
            result["from_cache"] = False
            
            # 📑 Add bookmark status to each paper
            user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
            session_id = request.headers.get('X-Session-ID')
            
            if result.get('papers') and (user_id or session_id):
                for paper in result['papers']:
                    paper_id = generate_paper_id(paper)
                    paper['paper_id'] = paper_id
                    paper['is_bookmarked'] = cache_manager.is_paper_bookmarked(user_id, paper_id, session_id)
            
            # Cache the RAG results for future requests
            try:
                cache_manager.cache_search_results(research_input, sources, max_results, result, user_id)
                logger.info(f"✅ Cached RAG search results for query: {research_input[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to cache RAG search results: {e}")
        
        # Save search to history if user is authenticated
        if hasattr(request, 'current_user') and request.current_user and result.get('success'):
            try:
                cache_manager.save_user_search_to_history(
                    request.current_user['uid'],
                    research_input,
                    len(result.get('papers', [])),
                    sources
                )
            except Exception as e:
                logger.warning(f"Failed to save RAG search history: {e}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"RAG discovery endpoint failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "papers": [],
            "search_method": "rag_error"
        }), 500


@app.route('/api/upload-paper', methods=['POST'])
def upload_paper():
    """Upload and analyze a research paper to find similar papers"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"success": False, "error": "Only PDF files are supported"}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(config.TEMP_DIR, f"{uuid.uuid4()}_{filename}")
        file.save(filepath)
        
        try:
            # Analyze the uploaded paper
            analysis_result = discovery_engine.analyze_uploaded_paper(filepath)
            
            if not analysis_result.get('success'):
                return jsonify(analysis_result), 400
            
            # Create research query from analysis
            research_focus = analysis_result['research_focus']
            research_query = f"{research_focus['topic']} {' '.join(research_focus['keywords'][:5])}"
            
            # Get parameters from form data
            sources = request.form.get('sources', 'openalex').split(',')
            max_results = min(int(request.form.get('max_results', config.DEFAULT_MAX_RESULTS)), 
                            config.MAX_ALLOWED_RESULTS)
            
            # Find similar papers
            discovery_result = discovery_engine.discover_papers(research_query, sources, max_results)
            
            # Combine results
            result = {
                "success": True,
                "uploaded_paper_analysis": analysis_result['research_focus'],
                "similar_papers": discovery_result
            }
            
            return jsonify(result)
            
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass  # Ignore cleanup errors
        
    except Exception as e:
        logger.error(f"Paper upload endpoint failed: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/api/download-paper', methods=['POST'])
@firebase_auth_required
def download_paper():
    """Download and analyze a paper from provided URL"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"success": False, "error": "Paper URL is required"}), 400
        
        paper_url = data['url']
        
        # Validate URL
        if not paper_url.startswith(('http://', 'https://')):
            return jsonify({"success": False, "error": "Invalid URL"}), 400
        
        # Download the paper
        response = requests.get(paper_url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Check if it's a PDF
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and not paper_url.lower().endswith('.pdf'):
            return jsonify({"success": False, "error": "URL does not point to a PDF file"}), 400
        
        # Save to temp file
        temp_filename = f"{uuid.uuid4()}_downloaded_paper.pdf"
        temp_filepath = os.path.join(config.TEMP_DIR, temp_filename)
        
        with open(temp_filepath, 'wb') as f:
            f.write(response.content)
        
        try:
            # Analyze the downloaded paper
            analysis_result = discovery_engine.analyze_uploaded_paper(temp_filepath)
            
            return jsonify(analysis_result)
            
        finally:
            # Clean up downloaded file
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass  # Ignore cleanup errors
        
    except requests.RequestException as e:
        logger.error(f"Paper download failed: {e}")
        return jsonify({"success": False, "error": "Failed to download paper"}), 500
    except Exception as e:
        logger.error(f"Paper download endpoint failed: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/api/paper-details', methods=['POST'])
@firebase_auth_required
def get_paper_details():
    """Generate detailed analysis and summary for a specific paper"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        paper = data.get('paper')
        if not paper:
            return jsonify({"success": False, "error": "Paper data is required"}), 400
        
        session_id = data.get('session_id')  # Optional session ID
        
        # Check cache first
        cached_result = cache_manager.get_cached_paper_details(paper)
        if cached_result:
            logger.info(f"Returning cached paper details for: {paper.get('title', 'Unknown')[:50]}...")
            return jsonify({
                "success": True,
                "paper": cached_result["paper"],
                "detailed_analysis": cached_result["analysis"],
                "from_cache": True,
                "cache_timestamp": cached_result.get("timestamp")
            })
        
        # Generate detailed analysis using AI if not in cache
        detailed_analysis = generate_paper_analysis(paper)
        
        # Cache the analysis
        cache_manager.cache_paper_details(paper, detailed_analysis, session_id)
        
        return jsonify({
            "success": True,
            "paper": paper,
            "detailed_analysis": detailed_analysis,
            "from_cache": False
        })
        
    except Exception as e:
        logger.error(f"Paper details endpoint failed: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route('/api/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = cache_manager.get_cache_stats()
        return jsonify({
            "success": True,
            "cache_stats": stats
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get cache statistics"}), 500

@app.route('/api/cache/test', methods=['GET'])
def test_cache():
    """Test Redis cache functionality"""
    try:
        # Test basic Redis operations
        test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
        
        # Test cache operations
        cache_result = cache_manager.cache_search_results(
            "test query", 
            ["test"], 
            5, 
            test_data, 
            "test_session"
        )
        
        retrieve_result = cache_manager.get_cached_search_results("test query", ["test"], 5)
        
        return jsonify({
            "success": True,
            "redis_enabled": cache_manager.enabled,
            "redis_client_available": cache_manager.redis_client is not None,
            "cache_save_success": cache_result,
            "cache_retrieve_success": retrieve_result is not None,
            "retrieved_data": retrieve_result
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e),
            "redis_enabled": cache_manager.enabled,
            "redis_client_available": cache_manager.redis_client is not None
        })


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache (optionally by session ID)"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        if session_id:
            cleared_count = cache_manager.clear_session_cache(session_id)
            return jsonify({
                "success": True,
                "message": f"Cleared {cleared_count} items for session {session_id}",
                "cleared_count": cleared_count
            })
        else:
            cache_manager.clear_all_cache()
            return jsonify({
                "success": True,
                "message": "All cache cleared"
            })
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({"success": False, "error": "Failed to clear cache"}), 500


@app.route('/api/session/new', methods=['POST'])
def create_session():
    """Create a new session ID"""
    try:
        session_id = cache_manager.create_session()
        return jsonify({
            "success": True,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return jsonify({"success": False, "error": "Failed to create session"}), 500


@app.route('/api/debug/cache', methods=['GET'])
def debug_cache():
    """Debug cache operations"""
    try:
        debug_info = {
            "redis_enabled": cache_manager.enabled,
            "redis_connected": False,
            "cache_keys": [],
            "test_cache": None
        }
        
        if cache_manager.redis_client:
            try:
                # Test connection
                cache_manager.redis_client.ping()
                debug_info["redis_connected"] = True
                
                # Get all keys
                keys = cache_manager.redis_client.keys("*")
                debug_info["cache_keys"] = [key.decode() if isinstance(key, bytes) else str(key) for key in keys]
                
                # Test cache operation
                test_key = "test:debug"
                test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
                serialized = cache_manager._serialize_data(test_data)
                
                cache_manager.redis_client.setex(test_key, 60, serialized)
                retrieved = cache_manager.redis_client.get(test_key)
                
                if retrieved:
                    deserialized = cache_manager._deserialize_data(retrieved)
                    debug_info["test_cache"] = "Success - can cache and retrieve"
                else:
                    debug_info["test_cache"] = "Failed - cannot retrieve cached data"
                    
            except Exception as e:
                debug_info["redis_error"] = str(e)
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/cache/search-results', methods=['POST'])
@firebase_auth_optional
def get_cached_search_results():
    """Get cached search results for a session or user"""
    print("calling cached search results")
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        session_id = data.get('session_id')
        query = data.get('query')  # Optional: get specific query results
        
        # Get user ID from Firebase auth (if authenticated)
        user_id = request.current_user['uid'] if request.current_user else None
        
        # Use user_id for authenticated users, session_id for anonymous users
        cache_key_id = user_id or session_id
        
        if not cache_key_id:
            return jsonify({"success": False, "error": "Session ID or authentication required"}), 400
        
        print(f"🔍 DEBUG: Looking for cache with ID: {cache_key_id} (user_id: {user_id}, session_id: {session_id})")
        
        # Get all cached results for the user/session
        if query:
            # For specific query results, we'd need sources and max_results
            # This is not currently implemented properly, so skip for now
            return jsonify({
                "success": True,
                "has_cache": False,
                "message": "Specific query lookup not implemented"
            })
        else:
            # Get the most recent search results for the user/session
            recent_results = cache_manager.get_recent_search_results(cache_key_id)
            if recent_results:
                return jsonify({
                    "success": True,
                    "has_cache": True,
                    "results": recent_results
                })
            else:
                return jsonify({
                    "success": True,
                    "has_cache": False,
                    "message": "No cached search results for this session"
                })
                
    except Exception as e:
        logger.error(f"Error getting cached search results: {str(e)}")
        return jsonify({"success": False, "error": "Failed to get cached results"}), 500


def generate_paper_analysis(paper: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive analysis of a research paper using AI"""
    try:
        title = paper.get('title', 'Unknown Title')
        summary = paper.get('summary', 'No summary available')
        authors = paper.get('authors', [])
        source = paper.get('source', 'Unknown')
        citation_count = paper.get('citation_count', 0)
        published = paper.get('published', 'Unknown')
        
        if not openai_client:
            return generate_fallback_analysis(paper)
        
        # Create comprehensive prompt for AI analysis
        authors_str = ', '.join([str(auth) for auth in authors[:5] if auth])
        
        prompt = f"""
        Provide a comprehensive analysis of this research paper. Generate a detailed summary that would be helpful for graduate students and researchers.
        
        Paper Details:
        - Title: {title}
        - Authors: {authors_str}
        - Source: {source}
        - Published: {published}
        - Citations: {citation_count}
        - Abstract: {summary[:1000]}
        
        Please provide a JSON response with exactly these keys:
        {{
            "brief_summary": "A concise 2-3 sentence summary of the main contribution",
            "detailed_summary": "A comprehensive 4-5 paragraph analysis covering methodology, findings, and significance",
            "key_contributions": ["contribution1", "contribution2", "contribution3"],
            "methodology": "Brief description of the research methodology used",
            "practical_applications": ["application1", "application2", "application3"],
            "strengths": ["strength1", "strength2", "strength3"],
            "limitations": ["limitation1", "limitation2"],
            "target_audience": "Who would benefit from reading this paper",
            "reading_difficulty": "Beginner|Intermediate|Advanced",
            "estimated_reading_time": "15-20 minutes",
            "related_topics": ["topic1", "topic2", "topic3"],
            "impact_score": 85,
            "recommendation": "Why students should or shouldn't read this paper"
        }}
        
        Respond only with valid JSON, no additional text.
        """
        
        response = openai_client.invoke(prompt)
        
        # Parse AI response
        try:
            if hasattr(response, 'content'):
                content = str(response.content).strip()
            else:
                content = str(response).strip()
                
            analysis = json.loads(content)
            return validate_analysis_result(analysis)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI analysis response: {e}")
            return generate_fallback_analysis(paper)
            
    except Exception as e:
        logger.error(f"AI paper analysis failed: {e}")
        return generate_fallback_analysis(paper)


def validate_analysis_result(analysis: Dict) -> Dict[str, Any]:
    """Validate and clean AI analysis result"""
    return {
        "brief_summary": str(analysis.get("brief_summary", "This paper presents research findings in its field."))[:500],
        "detailed_summary": str(analysis.get("detailed_summary", "Detailed analysis not available."))[:2000],
        "key_contributions": [str(c)[:200] for c in analysis.get("key_contributions", [])[:5]],
        "methodology": str(analysis.get("methodology", "Research methodology not specified."))[:500],
        "practical_applications": [str(a)[:200] for a in analysis.get("practical_applications", [])[:5]],
        "strengths": [str(s)[:200] for s in analysis.get("strengths", [])[:5]],
        "limitations": [str(l)[:200] for l in analysis.get("limitations", [])[:3]],
        "target_audience": str(analysis.get("target_audience", "Researchers and graduate students"))[:200],
        "reading_difficulty": str(analysis.get("reading_difficulty", "intermediate"))[:20],
        "estimated_reading_time": str(analysis.get("estimated_reading_time", "20-30 minutes"))[:50],
        "related_topics": [str(t)[:100] for t in analysis.get("related_topics", [])[:5]],
        "impact_score": min(100, max(0, int(analysis.get("impact_score", 75)))),
        "recommendation": str(analysis.get("recommendation", "This paper provides valuable insights for researchers in the field."))[:500]
    }


def generate_fallback_analysis(paper: Dict[str, Any]) -> Dict[str, Any]:
    """Generate basic analysis when AI is not available"""
    title = paper.get('title', 'Unknown Title')
    summary = paper.get('summary', 'No summary available')
    citation_count = paper.get('citation_count', 0)
    source = paper.get('source', 'Unknown')
    
    # Determine impact score based on citations
    if citation_count > 500:
        impact_score = 95
        impact_desc = "highly influential"
    elif citation_count > 100:
        impact_score = 85
        impact_desc = "well-cited"
    elif citation_count > 50:
        impact_score = 75
        impact_desc = "moderately cited"
    else:
        impact_score = 65
        impact_desc = "emerging research"
    
    # Extract basic insights from title and summary
    text_lower = f"{title} {summary}".lower()
    
    # Identify methodology keywords
    methodology = "Not specified"
    if any(term in text_lower for term in ["machine learning", "deep learning", "neural network"]):
        methodology = "Machine learning and neural network approaches"
    elif any(term in text_lower for term in ["statistical", "regression", "analysis"]):
        methodology = "Statistical analysis and modeling"
    elif any(term in text_lower for term in ["experimental", "experiment", "study"]):
        methodology = "Experimental research design"
    elif any(term in text_lower for term in ["survey", "review", "systematic"]):
        methodology = "Literature review and survey methodology"
    
    return {
        "brief_summary": f"This {impact_desc} paper from {source} presents research findings related to the topic of {title[:100]}.",
        "detailed_summary": f"This research paper, published in {source}, explores {title}. {summary[:500]} The work has received {citation_count} citations, indicating its {impact_desc} status in the research community. The paper contributes to the understanding of its field through comprehensive analysis and findings.",
        "key_contributions": [
            "Presents novel research findings in the field",
            "Provides comprehensive analysis of the research topic",
            "Contributes to the existing body of knowledge"
        ],
        "methodology": methodology,
        "practical_applications": [
            "Academic research and further studies",
            "Practical implementation in relevant domains",
            "Educational purposes for students and researchers"
        ],
        "strengths": [
            f"Published in reputable source ({source})",
            f"Has received {citation_count} citations showing impact",
            "Contributes valuable insights to the field"
        ],
        "limitations": [
            "Detailed methodology analysis requires full paper access",
            "Complete evaluation needs comprehensive review"
        ],
        "target_audience": "Graduate students, researchers, and professionals in the field",
        "reading_difficulty": "intermediate",
        "estimated_reading_time": "20-30 minutes",
        "related_topics": [
            "Academic research methodology",
            "Field-specific studies",
            "Research analysis and findings"
        ],
        "impact_score": impact_score,
        "recommendation": f"This {impact_desc} paper is recommended for researchers interested in the topic, offering valuable insights and contributing to field knowledge."
    }


# Firebase Authentication API Endpoints
@app.route('/api/auth/verify', methods=['GET'])
@firebase_auth_required
def verify_token():
    """Verify Firebase ID token and return user info"""
    try:
        user = request.current_user
        
        return jsonify({
            "success": True,
            "user": {
                "uid": user['uid'],
                "email": user['email'],
                "name": user['name'],
                "picture": user['picture'],
                "provider": user['provider']
            },
            "message": "Token verified successfully"
        })
        
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return jsonify({"success": False, "error": "Token verification failed"}), 500

@app.route('/api/user/profile', methods=['GET'])
@firebase_auth_required
def get_user_profile():
    """Get authenticated user's profile with stats"""
    try:
        user = request.current_user
        user_id = user['uid']
        
        # Get user's search history count
        search_history = cache_manager.get_user_search_history(user_id, 100)
        
        # Calculate user stats
        total_searches = len(search_history)
        recent_searches = len([s for s in search_history if s.get('timestamp', '') > (datetime.utcnow() - timedelta(days=7)).isoformat()])
        
        return jsonify({
            "success": True,
            "user": {
                "uid": user_id,
                "email": user['email'],
                "name": user['name'],
                "picture": user['picture'],
                "provider": user['provider'],
                "stats": {
                    "total_searches": total_searches,
                    "recent_searches": recent_searches,
                    "saved_papers": 0,  # Placeholder for future implementation
                    "member_since": "2024"  # Could be stored in Redis if needed
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({"success": False, "error": "Failed to get profile"}), 500

@app.route('/api/user/search-history', methods=['GET'])
@firebase_auth_required
def get_user_search_history():
    """Get authenticated user's search history"""
    try:
        user_id = request.current_user['uid']
        limit = min(int(request.args.get('limit', 20)), 100)
        
        history = cache_manager.get_user_search_history(user_id, limit)
        
        return jsonify({
            "success": True,
            "history": history,
            "count": len(history),
            "user_authenticated": True
        })
        
    except Exception as e:
        logger.error(f"Error getting user search history: {e}")
        return jsonify({"success": False, "error": "Failed to get search history"}), 500

@app.route('/api/user/search-history', methods=['DELETE'])
@firebase_auth_required
def manage_user_search_history():
    """Delete specific search or clear all user history"""
    try:
        data = request.get_json() or {}
        user_id = request.current_user['uid']
        search_id = data.get('search_id')  # Optional: delete specific search
        
        if search_id:
            # Delete specific search
            success = cache_manager.delete_search_from_user_history(user_id, search_id)
            message = "Search deleted from history" if success else "Failed to delete search"
        else:
            # Clear all history
            success = cache_manager.clear_user_search_history(user_id)
            message = "Search history cleared" if success else "Failed to clear history"
        
        return jsonify({
            "success": success,
            "message": message
        })
        
    except Exception as e:
        logger.error(f"Error managing user search history: {e}")
        return jsonify({"success": False, "error": "Failed to manage search history"}), 500

@app.route('/api/user/search-history/repeat', methods=['POST'])
@firebase_auth_required
def repeat_user_search():
    """Repeat a search from user's history"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        user_id = request.current_user['uid']
        search_id = data.get('search_id')
        
        if not search_id:
            return jsonify({"success": False, "error": "Search ID is required"}), 400
        
        # Get search history
        history = cache_manager.get_user_search_history(user_id, 100)
        
        # Find the specific search
        target_search = None
        for search in history:
            if search.get('search_id') == search_id:
                target_search = search
                break
        
        if not target_search:
            return jsonify({"success": False, "error": "Search not found in history"}), 404
        
        # Repeat the search
        query = target_search['query']
        sources = target_search['sources']
        max_results = config.DEFAULT_MAX_RESULTS
        
        # Check cache first
        cached_result = cache_manager.get_cached_search_results(query, sources, max_results)
        if cached_result:
            cached_result["results"]["from_cache"] = True
            return jsonify(cached_result["results"])
        
        # Perform new search
        result = discovery_engine.discover_papers(query, sources, max_results)
        
        # Cache the results and update history
        if result.get("success"):
            cache_manager.cache_search_results(query, sources, max_results, result, user_id)
            results_count = len(result.get('papers', []))
            cache_manager.save_user_search_to_history(user_id, query, results_count, sources)
            result["from_cache"] = False
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error repeating user search: {e}")
        return jsonify({"success": False, "error": "Failed to repeat search"}), 500


# Session-based search history endpoints (for anonymous users)
@app.route('/api/search-history', methods=['GET'])
def get_session_search_history():
    """Get session-based search history for anonymous users"""
    try:
        session_id = request.args.get('session_id')
        limit = int(request.args.get('limit', 20))
        
        if not session_id:
            return jsonify({"success": False, "error": "Session ID is required"}), 400
        
        # Get session search history
        history = cache_manager.get_session_search_history(session_id, limit)
        
        return jsonify({
            "success": True,
            "history": history,
            "count": len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting session search history: {e}")
        return jsonify({"success": False, "error": "Failed to get search history"}), 500


@app.route('/api/search-history', methods=['DELETE'])
def clear_session_search_history():
    """Clear session-based search history for anonymous users"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"success": False, "error": "Session ID is required"}), 400
        
        # Clear session search history
        success = cache_manager.clear_session_search_history(session_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Session search history cleared successfully"
            })
        else:
            return jsonify({"success": False, "error": "Failed to clear search history"}), 500
            
    except Exception as e:
        logger.error(f"Error clearing session search history: {e}")
        return jsonify({"success": False, "error": "Failed to clear search history"}), 500


@app.route('/api/sources', methods=['GET'])
def get_available_sources():
    """Get list of available paper sources"""
    sources = [
        {
            "id": "openalex", 
            "name": "OpenAlex", 
            "description": "Open catalog of scholarly papers with comprehensive metadata",
            "available": True
        },
        {
            "id": "google_scholar", 
            "name": "Google Scholar", 
            "description": "Web search for scholarly literature",
            "available": True
        }
    ]
    
    return jsonify({"sources": sources})


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"success": False, "error": "Internal server error"}), 500


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"success": False, "error": "File too large"}), 413


# 📑 BOOKMARK API ENDPOINTS

@app.route('/api/bookmarks/save', methods=['POST'])
@firebase_auth_optional
def save_bookmark():
    """Save a paper to bookmarks"""
    try:
        data = request.get_json()
        if not data or not data.get('paper'):
            return jsonify({"success": False, "error": "Paper data is required"}), 400
        
        paper = data['paper']
        user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
        session_id = data.get('session_id') or request.headers.get('X-Session-ID')
        
        if not user_id and not session_id:
            return jsonify({"success": False, "error": "User authentication or session ID required"}), 401
        
        success = cache_manager.save_paper_bookmark(user_id, paper, session_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Paper bookmarked successfully",
                "paper_id": paper.get('url') or paper.get('id') or paper.get('title', '')[:100]
            })
        else:
            return jsonify({"success": False, "error": "Failed to save bookmark"}), 500
            
    except Exception as e:
        logger.error(f"Bookmark save failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/bookmarks/remove', methods=['POST'])
@firebase_auth_optional
def remove_bookmark():
    """Remove a paper from bookmarks"""
    try:
        data = request.get_json()
        if not data or not data.get('paper_id'):
            return jsonify({"success": False, "error": "Paper ID is required"}), 400
        
        paper_id = data['paper_id']
        user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
        session_id = data.get('session_id') or request.headers.get('X-Session-ID')
        
        if not user_id and not session_id:
            return jsonify({"success": False, "error": "User authentication or session ID required"}), 401
        
        success = cache_manager.remove_paper_bookmark(user_id, paper_id, session_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Bookmark removed successfully"
            })
        else:
            return jsonify({"success": False, "error": "Bookmark not found or failed to remove"}), 404
            
    except Exception as e:
        logger.error(f"Bookmark removal failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/bookmarks', methods=['GET'])
@firebase_auth_optional
def get_bookmarks():
    """Get all bookmarked papers for the current user"""
    try:
        user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
        session_id = request.args.get('session_id') or request.headers.get('X-Session-ID')
        
        if not user_id and not session_id:
            return jsonify({"success": False, "error": "User authentication or session ID required"}), 401
        
        bookmarks = cache_manager.get_user_bookmarks(user_id, session_id)
        
        return jsonify({
            "success": True,
            "bookmarks": bookmarks,
            "count": len(bookmarks),
            "user_authenticated": user_id is not None
        })
        
    except Exception as e:
        logger.error(f"Get bookmarks failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/bookmarks/check', methods=['POST'])
@firebase_auth_optional
def check_bookmark_status():
    """Check if papers are bookmarked (bulk check)"""
    try:
        data = request.get_json()
        if not data or not data.get('paper_ids'):
            return jsonify({"success": False, "error": "Paper IDs are required"}), 400
        
        paper_ids = data['paper_ids']
        user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
        session_id = data.get('session_id') or request.headers.get('X-Session-ID')
        
        if not user_id and not session_id:
            return jsonify({"success": False, "error": "User authentication or session ID required"}), 401
        
        bookmark_status = {}
        for paper_id in paper_ids:
            bookmark_status[paper_id] = cache_manager.is_paper_bookmarked(user_id, paper_id, session_id)
        
        return jsonify({
            "success": True,
            "bookmark_status": bookmark_status
        })
        
    except Exception as e:
        logger.error(f"Bookmark status check failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# 🔗 SIMPLE PAPER RELATIONSHIPS API ENDPOINTS

@app.route('/api/paper-relationships/<paper_id>', methods=['GET'])
@firebase_auth_optional  
def explore_paper_relationships(paper_id):
    """Simple paper relationship explorer - easy to understand and explain"""
    try:
        # Optional parameters
        max_connections = request.args.get('max_connections', 10, type=int)
        max_connections = min(max(5, max_connections), 20)  # Limit to keep it simple
        
        logger.info(f"🔗 Exploring relationships for paper: {paper_id}")
        
        # Check if this looks like an OpenAlex work ID
        if paper_id.startswith('W') and len(paper_id) > 5:
            logger.info(f"📊 Using OpenAlex work ID for graph building: {paper_id}")
        else:
            logger.info(f"📊 Using legacy paper ID for graph building: {paper_id}")
        
        # Explore paper connections using simplified approach
        connections = discovery_engine.paper_relationships.explore_paper_connections(
            paper_id, max_connections=max_connections
        )
        
        return jsonify(connections)
        
    except Exception as e:
        logger.error(f"Paper relationship exploration failed: {e}")
        return jsonify({
            "success": False, 
            "error": str(e),
            "message": "Failed to explore paper relationships"
        }), 500


@app.route('/api/paper-family-tree', methods=['POST'])
@firebase_auth_optional
def get_paper_family_tree():
    """Get a simple family tree view of paper relationships"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        papers = data.get('papers', [])
        if not papers:
            return jsonify({"success": False, "error": "No papers provided"}), 400
        
        # Extract paper IDs
        paper_ids = []
        for paper in papers[:3]:  # Limit to 3 papers to keep it simple
            paper_id = paper.get('id') or paper.get('url', '') or paper.get('paper_id', '')
            if paper_id:
                paper_ids.append(paper_id)
        
        if not paper_ids:
            return jsonify({"success": False, "error": "No valid paper IDs found"}), 400
        
        logger.info(f"Creating family trees for {len(paper_ids)} papers")
        
        # Create simple family trees for multiple papers
        result = discovery_engine.paper_relationships.explore_multiple_papers(paper_ids)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Family tree generation failed: {e}")
        return jsonify({
            "success": False, 
            "error": str(e),
            "message": "Failed to generate paper family trees"
        }), 500


@app.route('/api/paper-insights/<paper_id>', methods=['GET'])
@firebase_auth_optional
def get_paper_insights(paper_id):
    """Get quick insights about a paper's influence and connections"""
    try:
        logger.info(f"Getting insights for paper: {paper_id}")
        
        # Get paper connections
        connections = discovery_engine.paper_relationships.explore_paper_connections(
            paper_id, max_connections=10
        )
        
        if not connections.get('success'):
            return jsonify(connections), 400
        
        # Extract key insights for quick display
        insights = {
            "success": True,
            "paper_id": paper_id,
            "paper_info": connections.get('paper_info', {}),
            "quick_stats": {
                "foundation_papers": len(connections.get('connections', {}).get('foundation_papers', [])),
                "building_papers": len(connections.get('connections', {}).get('building_papers', [])),
                "influence_score": connections.get('insights', {}).get('influence_score', 0),
                "impact_level": connections.get('insights', {}).get('impact_level', 'unknown')
            },
            "key_insights": connections.get('insights', {}).get('insights', [])[:3],  # Top 3 insights
            "related_authors": connections.get('connections', {}).get('related_authors', [])[:3]
        }
        
        return jsonify(insights)
        
    except Exception as e:
        logger.error(f"Paper insights endpoint failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get paper insights"
        }), 500


@app.route('/api/paper-relationships/features', methods=['GET'])
@firebase_auth_optional
def get_enhanced_features_info():
    """Get information about enhanced paper relationship features"""
    try:
        logger.info("Fetching enhanced features information")
        
        # Get enhanced features demo info
        demo_info = discovery_engine.paper_relationships.get_enhanced_features_demo()
        
        return jsonify({
            "success": True,
            "features": demo_info,
            "timestamp": datetime.now().isoformat(),
            "message": "Enhanced paper relationship features with scholarly+networkx integration"
        })
        
    except Exception as e:
        logger.error(f"Enhanced features info failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get enhanced features information"
        }), 500


# �🧠 VECTOR DATABASE API ENDPOINTS

@app.route('/api/vector-db/stats', methods=['GET'])
def vector_database_stats():
    """Get vector database statistics and persistence info"""
    try:
        # Get database stats from discovery engine
        vector_stats = discovery_engine.vector_db.get_database_stats()
        storage_info = discovery_engine.vector_db.get_persistent_storage_size()
        
        return jsonify({
            "success": True,
            "database_stats": vector_stats,
            "storage_info": storage_info,
            "persistence_enabled": True
        })
        
    except Exception as e:
        logger.error(f"Failed to get vector database stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/vector-db/manual-save', methods=['POST'])
def manual_save_vector_db():
    """Manually trigger vector database save to disk"""
    try:
        discovery_engine.vector_db.manual_save()
        
        return jsonify({
            "success": True,
            "message": "Vector database saved to disk successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to manually save vector database: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/vector-db/clear', methods=['POST'])
def clear_vector_database():
    """Clear vector database (both memory and persistent storage)"""
    try:
        discovery_engine.vector_db.clear_database()
        
        return jsonify({
            "success": True,
            "message": "Vector database cleared successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to clear vector database: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    logger.info("🔬 Academic Paper Discovery Engine Starting...")
    logger.info("=" * 70)
    logger.info("Available endpoints:")
    logger.info("📄 PAPER DISCOVERY:")
    logger.info("- POST /api/discover-papers - Traditional paper discovery")
    logger.info("- POST /api/discover-papers-rag - 🧠 RAG-enhanced discovery")
    logger.info("- POST /api/upload-paper - Upload paper to find similar research")
    logger.info("- POST /api/download-paper - Download and analyze paper from URL")
    logger.info("")
    logger.info("🔗 PAPER RELATIONSHIPS (Simple & Easy to Understand):")
    logger.info("- GET /api/paper-relationships/<paper_id> - Explore paper family tree")
    logger.info("- POST /api/paper-family-tree - Get family trees for multiple papers")
    logger.info("- GET /api/paper-insights/<paper_id> - Quick paper influence insights")
    logger.info("- GET /api/paper-relationships/features - Enhanced features info (scholarly+networkx)")
    logger.info("")
    logger.info("🧠 VECTOR DATABASE:")
    logger.info("- GET /api/vector-db/stats - Database statistics & persistence info")
    logger.info("- POST /api/vector-db/manual-save - Manually save to disk")
    logger.info("- POST /api/vector-db/clear - Clear database & storage")
    logger.info("")
    logger.info("⚙️  SYSTEM:")
    logger.info("- GET /api/health - Health check")
    logger.info("- GET /api/sources - Available search sources")
    logger.info("=" * 70)
    logger.info("🚀 Starting Flask development server...")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
