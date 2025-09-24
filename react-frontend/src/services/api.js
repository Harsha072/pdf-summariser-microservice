const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultOptions = {
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
      },
      ...options
    };

    try {
      const response = await fetch(url, defaultOptions);
      console.log("getting response ",response)
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Network error' }));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
    
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseURL}/upload`, {
      method: 'POST',
      mode: 'cors',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Upload failed' }));
      throw new Error(errorData.error || 'Upload failed');
    }

    return await response.json();
  }

  async generateSummary(docId) {
    return this.makeRequest('/summary', {
      method: 'POST',
      body: JSON.stringify({ doc_id: docId })
    });
  }

  async askQuestion(docId, question) {
    return this.makeRequest('/question', {
      method: 'POST',
      body: JSON.stringify({ 
        doc_id: docId, 
        question: question 
      })
    });
  }

  async checkHealth() {
    return this.makeRequest('/health');
  }
}

// Create singleton instance
const apiClient = new ApiClient();

// Export individual functions for convenience
export const uploadDocument = (file) => apiClient.uploadDocument(file);
export const generateSummary = (docId) => apiClient.generateSummary(docId);
export const askQuestion = (docId, question) => apiClient.askQuestion(docId, question);
export const checkHealth = () => apiClient.checkHealth();

export default apiClient;