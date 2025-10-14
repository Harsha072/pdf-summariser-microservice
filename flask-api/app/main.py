
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
from bs4 import BeautifulSoup
import urllib.parse

# PDF processing imports
import fitz  # PyMuPDF

# Text similarity and processing
from fuzzywuzzy import fuzz

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

# ArXiv API import
arxiv = None
if external_libs.arxiv_available:
    import arxiv

# Get logger from config
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, 
     origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
     methods=['GET', 'POST', 'OPTIONS'], 
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
     supports_credentials=True)

# Handle preflight requests manually for extra compatibility
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = Response()
        response.headers.add("Access-Control-Allow-Origin", request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,X-Requested-With")
        response.headers.add('Access-Control-Allow-Methods', "GET,POST,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
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


# Initialize cache manager
cache_manager = RedisCacheManager(redis_client)


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


class ArxivSearcher:
    """Search arXiv for academic papers"""
    
    def __init__(self):
        self.logger = logger
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search arXiv for papers with improved query handling"""
        if not arxiv:
            self.logger.warning("arXiv library not available")
            return []
        
        try:
            # Clean and optimize query for arXiv
            cleaned_query = self._optimize_arxiv_query(query)
            
            search = arxiv.Search(
                query=cleaned_query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            
            # Use client with better error handling
            client = arxiv.Client(
                page_size=10,  # Smaller page size to reduce server load
                delay_seconds=3,  # Respect rate limits
                num_retries=2  # Fewer retries to avoid long waits
            )
            
            papers = []
            try:
                for result in client.results(search):
                    paper = {
                        "id": result.entry_id.split('/')[-1],
                        "title": result.title,
                        "authors": [str(author) for author in result.authors],
                        "summary": result.summary,
                        "url": result.entry_id,
                        "pdf_url": result.pdf_url,
                        "published": result.published.strftime('%Y-%m-%d') if result.published else None,
                        "categories": result.categories,
                        "source": "arXiv"
                    }
                    papers.append(paper)
                    
                    # Limit results to avoid timeout issues
                    if len(papers) >= max_results:
                        break
                        
            except Exception as iteration_error:
                self.logger.warning(f"ArXiv iteration error (continuing with partial results): {iteration_error}")
            
            self.logger.info(f"Found {len(papers)} papers from arXiv for query: {cleaned_query[:50]}...")
            return papers
            
        except Exception as e:
            self.logger.error(f"arXiv search failed: {e}")
            return []

    def _optimize_arxiv_query(self, query: str) -> str:
        """Optimize query for arXiv search"""
        # Remove question words that don't help search
        stop_words = ['how', 'what', 'why', 'when', 'where', 'can', 'does', 'is', 'are', 'the', 'a', 'an']
        
        # Convert to lowercase and split
        words = query.lower().split()
        
        # Remove stop words but keep important technical terms
        filtered_words = []
        for word in words:
            # Keep the word if it's not a stop word or if it's a technical term
            if word not in stop_words or len(word) > 6:  # Keep longer words even if they're stop words
                filtered_words.append(word)
        
        # If query is still very long, take first 10 words
        if len(filtered_words) > 10:
            filtered_words = filtered_words[:10]
        
        optimized = ' '.join(filtered_words)
        
        # If optimization removed too much, use original
        if len(optimized) < len(query) * 0.3:  # If less than 30% remains
            return query
        
        return optimized


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


class GoogleScholarSearcher:
    """Search Google Scholar using web scraping with better bot detection avoidance"""
    
    def __init__(self):
        self.logger = logger
        self.last_request_time = 0
        self.min_delay = 3  # Minimum 3 seconds between requests
        self.session = requests.Session()
        self.consecutive_failures = 0
        self.max_failures = 3  # Disable after 3 consecutive failures
        
        # Rotate through different realistic headers
        self.headers_list = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
        ]
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search Google Scholar with improved bot detection avoidance"""
        try:
            # Rate limiting - wait if needed
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.min_delay:
                wait_time = self.min_delay - elapsed
                self.logger.info(f"Waiting {wait_time:.1f}s for Google Scholar rate limiting...")
                time.sleep(wait_time)
            
            # Use rotating headers
            headers = self.headers_list[int(time.time()) % len(self.headers_list)]
            
            # Build search URL with additional parameters to look more natural
            params = {
                'q': query,
                'num': min(max_results, 20),  # Google Scholar max per page
                'start': 0,
                'hl': 'en'
            }
            
            search_url = "https://scholar.google.com/scholar?" + urllib.parse.urlencode(params)
            self.logger.info(f"Searching Google Scholar: {query[:50]}...")
            
            response = self.session.get(
                search_url, 
                headers=headers, 
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            self.last_request_time = time.time()
            
            # Handle different response codes
            if response.status_code == 429:
                self.consecutive_failures += 1
                self.logger.warning(f"Google Scholar rate limit (429) - try again later (failure {self.consecutive_failures})")
                if self.consecutive_failures >= self.max_failures:
                    self.logger.error("Google Scholar repeatedly failing - consider using only ArXiv and Semantic Scholar")
                return []
            elif response.status_code == 403:
                self.consecutive_failures += 1
                self.logger.warning(f"Google Scholar blocked request (403) - possible bot detection (failure {self.consecutive_failures})")
                return []
            elif response.status_code != 200:
                self.consecutive_failures += 1
                self.logger.warning(f"Google Scholar returned status {response.status_code} (failure {self.consecutive_failures})")
                return []
            
            # Check for CAPTCHA or block page
            if "captcha" in response.text.lower() or "unusual traffic" in response.text.lower():
                self.logger.warning("Google Scholar detected unusual traffic - CAPTCHA required")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            papers = []
            
            # Try multiple selectors as Google Scholar changes their classes
            result_selectors = [
                'div.gs_r.gs_or.gs_scl',  # Current format
                'div[data-lid]',          # Alternative format
                'div.gs_ri'               # Older format
            ]
            
            results = []
            for selector in result_selectors:
                results = soup.select(selector)
                if results:
                    break
            
            if not results:
                self.logger.warning("No results found - Google Scholar may have changed structure")
                return []
            
            for result in results[:max_results]:
                try:
                    paper = self._parse_scholar_result(result)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    self.logger.warning(f"Failed to parse Google Scholar result: {e}")
                    continue
            
            self.logger.info(f"Found {len(papers)} papers from Google Scholar")
            
            # Reset failure count on success
            if papers:
                self.consecutive_failures = 0
            
            return papers
            
        except requests.exceptions.Timeout:
            self.logger.error("Google Scholar request timed out")
            return []
        except requests.exceptions.ConnectionError:
            self.logger.error("Failed to connect to Google Scholar")
            return []
        except Exception as e:
            self.logger.error(f"Google Scholar search failed: {e}")
            return []
    
    def _parse_scholar_result(self, result) -> Optional[Dict[str, Any]]:
        """Parse individual Google Scholar search result with multiple format support"""
        try:
            # Try multiple title selectors
            title_elem = None
            title_selectors = ['h3.gs_rt', 'h3', '.gs_rt', '[data-lid] h3']
            
            for selector in title_selectors:
                title_elem = result.select_one(selector)
                if title_elem:
                    break
            
            if not title_elem:
                return None
            
            # Clean title text
            title = title_elem.get_text(strip=True)
            
            # Remove citation markers like [PDF], [HTML], etc.
            title = re.sub(r'\[PDF\]|\[HTML\]|\[CITATION\]', '', title).strip()
            
            if not title or len(title) < 10:  # Skip if title too short
                return None
            
            # Extract authors and publication info
            authors = []
            authors_elem = result.select_one('.gs_a')
            if authors_elem:
                authors_text = authors_elem.get_text()
                # Authors are usually before the first dash
                author_part = authors_text.split('-')[0] if '-' in authors_text else authors_text
                authors = [author.strip() for author in author_part.split(',')[:5] if author.strip()]
            
            # Extract summary/snippet
            summary = "No summary available"
            summary_selectors = ['.gs_rs', '.gs_ri .gs_fl', '.gs_ri']
            
            for selector in summary_selectors:
                summary_elem = result.select_one(selector)
                if summary_elem:
                    summary = summary_elem.get_text(strip=True)
                    if len(summary) > 20:  # Only use if substantial content
                        break
            
            # Extract URL
            url = ""
            link_elem = title_elem.find('a')
            if link_elem and link_elem.get('href'):
                url = link_elem.get('href')
                # Handle relative URLs
                if url.startswith('/'):
                    url = 'https://scholar.google.com' + url
            
            # Extract year if available
            year = ""
            if authors_elem:
                year_match = re.search(r'\b(19|20)\d{2}\b', authors_elem.get_text())
                if year_match:
                    year = year_match.group()
            
            return {
                "id": str(uuid.uuid4()),
                "title": title,
                "authors": authors,
                "summary": summary[:500],  # Limit summary length
                "url": url,
                "pdf_url": url,
                "published": year,
                "source": "Google Scholar"
            }
            
        except Exception as e:
            self.logger.debug(f"Error parsing Google Scholar result: {e}")
            return None


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
        
        # Initialize components
        self.research_extractor = ResearchFocusExtractor(openai_client)
        self.arxiv_searcher = ArxivSearcher()
        self.openalex_searcher = OpenAlexSearcher()  # 🚀 NEW: OpenAlex instead of Semantic Scholar
        self.scholar_searcher = GoogleScholarSearcher()
        self.relevance_scorer = RelevanceScorer(openai_client)
        self.duplicate_remover = DuplicateRemover(config.DUPLICATE_THRESHOLD)
        self.pdf_analyzer = PDFAnalyzer(self.research_extractor)
        
        self.logger.info("Academic Paper Discovery Engine initialized")
    
    def extract_search_intent(self, research_input: str) -> Dict[str, Any]:
        """Extract search intent and optimize queries for different academic databases"""
        try:
            if not self.openai_client:
                # Fallback if OpenAI is not available
                return {
                    "arxiv_query": research_input.strip(),
                    "openalex_query": research_input.strip(),
                    "openalex_url_params": f"search={urllib.parse.quote(research_input.strip())}",
                    "primary_keywords": research_input.split()[:5],
                    "research_domain": "Computer Science",
                    "intent_confidence": 0.5
                }
            
            prompt = f"""You are an expert academic search query optimizer. Analyze the user's research question and create optimized search parameters for academic databases.

    User's Research Question: "{research_input}"

    Generate the following optimized search parameters:

    1. ARXIV_QUERY: Technical keyword query for arXiv (remove question words, focus on key technical terms, max 6-8 words)
    2. OPENALEX_QUERY: Natural language query for OpenAlex (preserve meaning, works excellently with full questions and natural language)
    3. OPENALEX_URL_PARAMS: URL-encoded search string ready for OpenAlex API (natural language friendly, focus on key concepts)
    4. PRIMARY_KEYWORDS: 3-5 most important technical keywords/phrases for relevance scoring
    5. RESEARCH_DOMAIN: Specific academic field (e.g., "Computer Science - AI", "Software Engineering", "Machine Learning")
    6. INTENT_CONFIDENCE: Confidence level (0.1-1.0) in understanding the research intent

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
        "arxiv_query": "optimized technical keywords",
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
            required_keys = ['arxiv_query', 'openalex_query', 'openalex_url_params', 'primary_keywords', 'research_domain', 'intent_confidence']
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
            "arxiv_query": ' '.join(keywords),
            "openalex_query": research_input.strip(),
            "openalex_url_params": f"search={urllib.parse.quote(url_query)}",
            "primary_keywords": keywords,
            "research_domain": "Computer Science",
            "intent_confidence": 0.3
        }

    def discover_papers(self, research_input: str, sources: List[str] = None, 
                       max_results: int = 10) -> Dict[str, Any]:
        """Main method to discover relevant academic papers"""
        try:
            if sources is None:
                sources = ["arxiv", "openalex"]
            
            max_results = min(max_results, config.MAX_ALLOWED_RESULTS)
            
            self.logger.info(f"Starting paper discovery for query: {research_input[:100]}...")
            
            # Extract research focus for analysis and scoring
            research_focus = self.research_extractor.extract_research_focus(research_input)
            
            # ✨ NEW: Use AI-powered intent detection to optimize queries for each database
            search_intent = self.extract_search_intent(research_input)
            
            self.logger.info(f"Intent detection - Domain: {search_intent.get('research_domain', 'unknown')}")
            self.logger.info(f"Intent detection - Confidence: {search_intent.get('intent_confidence', 0)}")
            
            # Use optimized queries for each source
            arxiv_query = search_intent.get('arxiv_query', research_input.strip())
            openalex_url_params = search_intent.get('openalex_url_params', f"search={urllib.parse.quote(research_input.strip())}")
            
            self.logger.info(f"ArXiv query: {arxiv_query}")
            self.logger.info(f"OpenAlex URL params: {openalex_url_params}")
            
            # Search multiple sources concurrently with optimized queries
            all_papers = []
            with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
                futures = []
                
                if "arxiv" in sources:
                    futures.append(executor.submit(self.arxiv_searcher.search, arxiv_query, max_results))
                
                if "openalex" in sources:
                    futures.append(executor.submit(self.openalex_searcher.search, openalex_url_params, max_results))
                
                if "google_scholar" in sources:
                    # For Google Scholar, use the original research question as it works well with natural language
                    futures.append(executor.submit(self.scholar_searcher.search, research_input.strip(), max_results))
                
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
                            "Try using only ArXiv and Semantic Scholar sources",
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
                    "arxiv_query": arxiv_query,
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
    
    def analyze_uploaded_paper(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze uploaded paper and find similar research"""
        return self.pdf_analyzer.analyze_research_paper(pdf_path)


# Initialize the discovery engine
discovery_engine = AcademicPaperDiscoveryEngine()


# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Academic Paper Discovery Engine",
        "timestamp": datetime.now().isoformat(),
        "openai_available": openai_client is not None,
        "arxiv_available": arxiv is not None
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
        
        sources = data.get('sources', ["arxiv", "openalex"])
        max_results = min(data.get('max_results', 10), config.MAX_ALLOWED_RESULTS)
        
        logger.info(f"📝 Received discovery request: {research_input[:100]}...")
        
        # 🔍 NEW: Check cache first before making API calls
        cached_result = cache_manager.get_cached_search_results(research_input, sources, max_results)
        if cached_result:
            logger.info(f"✅ Returning cached results for query: {research_input[:50]}...")
            cached_result["from_cache"] = True
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
            # Cache the results for future requests
            try:
                user_id = request.current_user['uid'] if hasattr(request, 'current_user') and request.current_user else None
                cache_manager.cache_search_results(research_input, sources, max_results, result, user_id)
                logger.info(f"✅ Cached search results for query: {research_input[:50]}...")
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
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Discovery endpoint failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "papers": []
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
            sources = request.form.get('sources', 'arxiv,openalex').split(',')
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
            "id": "arxiv", 
            "name": "arXiv", 
            "description": "Open access repository of scientific papers",
            "available": arxiv is not None
        },
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


if __name__ == '__main__':
    logger.info("🔬 Academic Paper Discovery Engine Starting...")
    logger.info("=" * 60)
    logger.info("Available endpoints:")
    logger.info("- POST /api/discover-papers - Discover papers by research query")
    logger.info("- POST /api/upload-paper - Upload paper to find similar research")
    logger.info("- POST /api/download-paper - Download and analyze paper from URL")
    logger.info("- GET /api/health - Health check")
    logger.info("- GET /api/sources - Available search sources")
    logger.info("=" * 60)
    logger.info("🚀 Starting Flask development server...")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
