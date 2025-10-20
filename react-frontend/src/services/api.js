// Academic Paper Discovery Engine API Client
import { v4 as uuidv4 } from 'uuid';
import { auth } from '../config/firebase';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Session management
let sessionId = null;

// Get or create session ID
const getSessionId = () => {
  if (!sessionId) {
    sessionId = localStorage.getItem('paper_discovery_session_id');
  }
  return sessionId;
};

// Get Firebase auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem('firebase_token');
  console.log('🔑 Auth token status:', token ? 'Present' : 'Missing');
  
  const headers = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
    console.log('🔐 Added Authorization header to request');
    console.log('📋 Full headers object:', headers);
  } else {
    console.warn('⚠️ No Firebase token found in localStorage');
  }
  
  return headers;
};

// Function to handle API calls with automatic token refresh
const authenticatedFetch = async (url, options = {}) => {
  try {
    // First attempt with current token
    const response = await fetch(url, {
      ...options,
      headers: {
        ...getAuthHeaders(),
        ...(options.headers || {})
      }
    });

    // If unauthorized and we have a refresh function available, try refreshing token
    if (response.status === 401) {
      console.log('🔄 Token expired, attempting refresh...');
      
      // Try to get fresh token from Firebase
      const currentUser = auth.currentUser;
      if (currentUser) {
        try {
          const newToken = await currentUser.getIdToken(true);
          localStorage.setItem('firebase_token', newToken);
          console.log('✅ Token refreshed successfully');
          
          // Retry the request with new token
          const retryResponse = await fetch(url, {
            ...options,
            headers: {
              ...getAuthHeaders(),
              ...(options.headers || {})
            }
          });
          
          return retryResponse;
        } catch (tokenError) {
          console.error('❌ Token refresh failed:', tokenError);
          // Clear invalid token
          localStorage.removeItem('firebase_token');
          throw new Error('Authentication failed. Please sign in again.');
        }
      } else {
        console.warn('⚠️ No current user found for token refresh');
        throw new Error('Please sign in to access this feature.');
      }
    }

    return response;
  } catch (error) {
    console.error('🚨 API request failed:', error);
    throw error;
  }
};

// Create new session
export const createSession = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/session/new`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await response.json();
    if (data.success) {
      sessionId = data.session_id;
      localStorage.setItem('paper_discovery_session_id', sessionId);
      return sessionId;
    }
    throw new Error('Failed to create session');
  } catch (error) {
    console.error('Session creation failed:', error);
    return null;
  }
};

// Export individual API functions for the Academic Paper Discovery Engine
export const discoverPapers = async (query, sources = ['openalex'], maxResults = 10) => {
  let currentSessionId = getSessionId();
  if (!currentSessionId) {
    currentSessionId = await createSession();
  }
  
  const response = await fetch(`${API_BASE_URL}/api/discover-papers`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ 
      query, 
      sources, 
      max_results: maxResults,
      session_id: currentSessionId
    })
  });
  return response.json();
};

export const uploadPaper = async (file, sources = ['openalex'], maxResults = 10) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('sources', sources.join(','));
  formData.append('max_results', maxResults.toString());
  
  const response = await fetch(`${API_BASE_URL}/api/upload-paper`, {
    method: 'POST',
    body: formData
  });
  return response.json();
};

export const healthCheck = async () => {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  return response.json();
};

export const getAvailableSources = async () => {
  const response = await fetch(`${API_BASE_URL}/api/sources`);
  return response.json();
};

// Download and analyze paper from URL
export const downloadPaper = async (url) => {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/download-paper`, {
    method: 'POST',
    body: JSON.stringify({ url })
  });
  return response.json();
};

// Get detailed paper analysis with AI-generated summary
export const getPaperDetails = async (paper) => {
  let currentSessionId = getSessionId();
  if (!currentSessionId) {
    currentSessionId = await createSession();
  }
  
  const response = await authenticatedFetch(`${API_BASE_URL}/api/paper-details`, {
    method: 'POST',
    body: JSON.stringify({ 
      paper,
      session_id: currentSessionId
    })
  });
  return response.json();
};

// Helper function with error handling
const handleApiResponse = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Network error' }));
    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
  }
  return response.json();
};

// Enhanced API functions with better error handling
export const discoverPapersWithErrorHandling = async (query, sources = ['openalex'], maxResults = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/discover-papers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, sources, max_results: maxResults })
    });
    return await handleApiResponse(response);
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

export const uploadPaperWithErrorHandling = async (file, sources = ['openalex'], maxResults = 10) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('sources', sources.join(','));
    formData.append('max_results', maxResults.toString());
    
    const response = await fetch(`${API_BASE_URL}/api/upload-paper`, {
      method: 'POST',
      body: formData
    });
    return await handleApiResponse(response);
  } catch (error) {
    console.error('Upload Error:', error);
    throw error;
  }
};

// Test connection to backend
export const testConnection = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      timeout: 5000
    });
    return response.ok;
  } catch (error) {
    console.error('Connection test failed:', error);
    return false;
  }
};

// Cache management functions
export const getCacheStats = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/cache/stats`);
    return await response.json();
  } catch (error) {
    console.error('Failed to get cache stats:', error);
    return { success: false, error: error.message };
  }
};

export const clearCache = async (sessionOnly = false) => {
  try {
    const body = sessionOnly ? { session_id: getSessionId() } : {};
    const response = await fetch(`${API_BASE_URL}/api/cache/clear`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to clear cache:', error);
    return { success: false, error: error.message };
  }
};

// Get cached search results for the current session
export const getCachedSearchResults = async (query = null) => {
  try {
    const sessionId = getSessionId();
    console.log('🔍 Getting cached results - Session ID:', sessionId);
    
    if (!sessionId) {
      console.log('⚠️ No session ID found');
      return { success: true, has_cache: false, message: 'No session ID' };
    }

    const body = { session_id: sessionId };
    if (query) {
      body.query = query;
    }
    
    console.log('📤 Sending cache request with body:', body);

    const response = await fetch(`${API_BASE_URL}/api/cache/search-results`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(body)
    });
    
    const result = await response.json();
    console.log('📥 Cache response:', result);
    return result;
  } catch (error) {
    console.error('Failed to get cached search results:', error);
    return { success: false, error: error.message };
  }
};

// Session management
export const getCurrentSessionId = () => getSessionId();

export const clearLocalSession = () => {
  sessionId = null;
  localStorage.removeItem('paper_discovery_session_id');
};

// Get API base URL for debugging
export const getApiBaseUrl = () => API_BASE_URL;

// Firebase Authentication API functions
export const authAPI = {
  // Verify Firebase token
  verifyToken: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      return await response.json();
    } catch (error) {
      console.error('Token verification failed:', error);
      throw error;
    }
  },

  // Get user profile
  getUserProfile: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/user/profile`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to get user profile:', error);
      throw error;
    }
  },

  // Get user search history
  getUserSearchHistory: async (limit = 20) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/user/search-history?limit=${limit}`, {
        method: 'GET',
        headers: getAuthHeaders(),
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to get user search history:', error);
      throw error;
    }
  },

  // Delete user search history
  deleteUserSearchHistory: async (searchId = null) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/user/search-history`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
        body: JSON.stringify({ search_id: searchId }),
      });
      return await response.json();  
    } catch (error) {
      console.error('Failed to delete user search history:', error);
      throw error;
    }
  },

  // Repeat search from history
  repeatUserSearch: async (searchId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/user/search-history/repeat`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ search_id: searchId }),
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to repeat user search:', error);
      throw error;
    }
  }
};

// Default export for backward compatibility
export default {
  discoverPapers,
  uploadPaper,
  healthCheck,
  getAvailableSources,
  downloadPaper,
  getPaperDetails,
  testConnection,
  getApiBaseUrl,
  createSession,
  getCacheStats,
  clearCache,
  getCachedSearchResults,
  getCurrentSessionId,
  clearLocalSession,
  // Firebase Authentication APIs
  authAPI
};

// Search History APIs
export const getUserSearchHistory = async (limit = 20) => {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/user/search-history?limit=${limit}`, {
    method: 'GET'
  });
  return response.json();
};

export const getSessionSearchHistory = async (sessionId, limit = 20) => {
  const response = await fetch(`${API_BASE_URL}/api/search-history?session_id=${sessionId}&limit=${limit}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return response.json();
};

export const clearUserSearchHistory = async () => {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/user/search-history`, {
    method: 'DELETE'
  });
  return response.json();
};

export const clearSessionSearchHistory = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/api/search-history`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId
    }),
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return response.json();
};