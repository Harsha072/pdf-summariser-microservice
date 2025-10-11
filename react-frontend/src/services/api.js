// Academic Paper Discovery Engine API Client
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
  const headers = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
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
export const discoverPapers = async (query, sources = ['arxiv', 'semantic_scholar'], maxResults = 10) => {
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

export const uploadPaper = async (file, sources = ['arxiv', 'semantic_scholar'], maxResults = 10) => {
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
  const response = await fetch(`${API_BASE_URL}/api/download-paper`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
  
  const response = await fetch(`${API_BASE_URL}/api/paper-details`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
export const discoverPapersWithErrorHandling = async (query, sources = ['arxiv', 'semantic_scholar'], maxResults = 10) => {
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

export const uploadPaperWithErrorHandling = async (file, sources = ['arxiv', 'semantic_scholar'], maxResults = 10) => {
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
    if (!sessionId) {
      return { success: true, has_cache: false, message: 'No session ID' };
    }

    const body = { session_id: sessionId };
    if (query) {
      body.query = query;
    }

    const response = await fetch(`${API_BASE_URL}/api/cache/search-results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return await response.json();
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